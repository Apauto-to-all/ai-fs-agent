import logging
import traceback

logger = logging.getLogger(__name__)

from typing import List, Optional
from pydantic import BaseModel, Field
from ai_fs_agent.utils.git.git_repo import _git_repo


class CommitFileChange(BaseModel):
    path: str = Field(..., description="新路径（相对于仓库根）")
    status: str = Field(..., description="变更状态代码，如 A/M/D/R/C 等（取首字母）")
    insertions: Optional[int] = Field(
        None, description="新增行数（无法统计/二进制为 None）"
    )
    deletions: Optional[int] = Field(
        None, description="删除行数（无法统计/二进制为 None）"
    )
    old_path: Optional[str] = Field(None, description="重命名/复制时的旧路径")
    similarity: Optional[int] = Field(
        None, description="R/C 变更的相似度百分比，如 85 表示 85%"
    )
    binary: Optional[bool] = Field(
        None, description="是否为二进制文件（numstat 无法统计时为 True）"
    )


class RecentCommit(BaseModel):
    commit_id: str = Field(..., description="提交完整哈希")
    short_id: str = Field(..., description="提交短哈希")
    tree_id: str = Field(..., description="树对象哈希（对应快照）")
    parent_ids: List[str] = Field(default_factory=list, description="父提交哈希列表")
    author_name: str = Field(..., description="作者姓名")
    author_email: str = Field(..., description="作者邮箱")
    date: str = Field(..., description="作者时间（ISO-8601）")
    committer_name: str = Field(..., description="提交者姓名")
    committer_email: str = Field(..., description="提交者邮箱")
    committer_date: str = Field(..., description="提交时间（ISO-8601）")
    refs: List[str] = Field(
        default_factory=list, description="关联引用（分支/标签/HEAD 等装饰）"
    )
    message: str = Field(..., description="提交标题（首行）")
    body: str = Field("", description="提交正文（可多行）")
    is_merge: bool = Field(False, description="是否为合并提交（父提交数>1）")
    files: List[CommitFileChange] = Field(
        default_factory=list, description="本次提交涉及的文件变更明细"
    )
    files_changed: int = Field(0, description="变更的文件数")
    insertions: int = Field(0, description="总新增行数（无法统计的文件不计入）")
    deletions: int = Field(0, description="总删除行数（无法统计的文件不计入）")


class GitHistory:
    """
    提交历史查询工具：仅负责读取历史信息，不执行写操作。
    - 工作路径固定为 get_workspace_root()
    - 内置 _run_git 与可用性检查，避免对 GitRepo 产生依赖
    """

    # 统一的 pretty 格式（记录之间以 0x1e 分隔，字段以 0x1f 分隔）
    _LOG_FMT = "%H%x1f%h%x1f%T%x1f%P%x1f%an%x1f%ae%x1f%ad%x1f%cn%x1f%ce%x1f%cd%x1f%D%x1f%s%x1f%B%x1e"

    def _ensure_repo_and_head(self) -> bool:
        """
        确保仓库就绪；返回是否存在提交（HEAD 可用）。
        """
        _git_repo.ensure()
        try:
            _git_repo._run_git(["rev-parse", "--verify", "HEAD"], check=True)
            return True
        except Exception:
            return False

    def _parse_log_raw(self, raw: str) -> List[RecentCommit]:
        """
        将 git log 的 raw 字符串解析为 RecentCommit 列表（不含文件明细）。
        """
        commits: List[RecentCommit] = []
        if not raw:
            return commits
        for rec in raw.split("\x1e"):
            rec = rec.rstrip()
            if not rec:
                continue
            parts = rec.split("\x1f")
            # 至少应包含我们定义的 13 段（最后一段是 %B，可能为空）
            if len(parts) < 13:
                continue
            (
                full,
                short,
                tree,
                parents_s,
                an,
                ae,
                ad,
                cn,
                ce,
                cd,
                deco,
                subject,
                body,
            ) = parts[:13]

            parent_ids = (
                [p.strip() for p in parents_s.split() if p.strip()] if parents_s else []
            )
            refs = [d.strip() for d in deco.split(",") if d.strip()] if deco else []

            commits.append(
                RecentCommit(
                    commit_id=full.strip(),
                    short_id=short.strip(),
                    tree_id=tree.strip(),
                    parent_ids=parent_ids,
                    author_name=an.strip(),
                    author_email=ae.strip(),
                    date=ad.strip(),
                    committer_name=cn.strip(),
                    committer_email=ce.strip(),
                    committer_date=cd.strip(),
                    refs=refs,
                    message=(subject or "").strip(),
                    body=(body or "").rstrip("\n"),
                    is_merge=len(parent_ids) > 1,
                )
            )
        return commits

    def _fill_commit_files(self, commit: RecentCommit) -> None:
        """
        补全单个提交的文件变更明细与汇总统计。
        """
        show_out = _git_repo._run_git(
            [
                "show",
                "--pretty=format:",
                "--name-status",
                "--numstat",
                commit.commit_id.strip(),
            ],
            check=True,
        )
        status_map: dict[str, dict] = {}
        num_map: dict[str, dict] = {}

        for line in show_out.splitlines():
            line = line.strip()
            if not line:
                continue
            cols = line.split("\t")

            # 解析 name-status（包含 Rxxx/Cxxx）
            code = cols[0] if cols else ""
            if code and (code[0] in "AMDCRTU" or code in ("T", "U")):
                status = code[0]  # R085 -> R
                sim = None
                digits = "".join(ch for ch in code if ch.isdigit())
                if status in ("R", "C") and digits:
                    try:
                        sim = int(digits)
                    except ValueError:
                        sim = None

                if status in ("R", "C") and len(cols) >= 3:
                    old_path, new_path = cols[1], cols[2]
                    status_map[new_path] = {
                        "status": status,
                        "old_path": old_path,
                        "similarity": sim,
                    }
                elif len(cols) >= 2:
                    path = cols[1]
                    status_map[path] = {
                        "status": status,
                        "old_path": None,
                        "similarity": sim,
                    }
                continue

            # 解析 numstat：ins \t del \t path 或 - \t - \t path（二进制）
            if len(cols) == 3:
                ins_s, del_s, path = cols
                binary = ins_s == "-" or del_s == "-"
                ins = None if binary else (int(ins_s) if ins_s.isdigit() else None)
                deL = None if binary else (int(del_s) if del_s.isdigit() else None)
                num_map[path] = {
                    "insertions": ins,
                    "deletions": deL,
                    "binary": True if binary else None,
                }

        files: List[CommitFileChange] = []
        paths = set(status_map) | set(num_map)
        total_ins = 0
        total_del = 0
        for p in sorted(paths):
            st_info = status_map.get(p, {})
            num_info = num_map.get(p, {})
            ins = num_info.get("insertions")
            deL = num_info.get("deletions")
            if isinstance(ins, int):
                total_ins += ins
            if isinstance(deL, int):
                total_del += deL
            files.append(
                CommitFileChange(
                    path=p,
                    status=st_info.get("status", "?"),
                    insertions=ins,
                    deletions=deL,
                    old_path=st_info.get("old_path"),
                    similarity=st_info.get("similarity"),
                    binary=num_info.get("binary"),
                )
            )

        commit.files = files
        commit.files_changed = len(files)
        commit.insertions = total_ins
        commit.deletions = total_del

    # ---------- 公共 API ----------
    def recent_commits(self, limit: int = 5) -> List[RecentCommit]:
        """
        获取最近 limit 个提交的完整信息（含作者/提交者、主题与正文、父提交、树哈希、引用、文件变更等）。
        """
        if not self._ensure_repo_and_head():
            return []

        # 基本元信息
        raw = _git_repo._run_git(
            [
                "log",
                "-n",
                str(limit),
                "--date=iso-strict",
                "--decorate=full",
                f"--pretty=format:{self._LOG_FMT}",
            ],
            check=True,
        )

        commits = self._parse_log_raw(raw)

        # 文件明细
        for c in commits:
            self._fill_commit_files(c)

        return commits

    def commit_details(self, ref: str) -> RecentCommit:
        """
        获取指定提交（ref）的完整详细信息（统一复用 recent_commits 的解析流程）。
        支持：完整/短哈希、相对引用（如 HEAD~1、HEAD^）。
        """
        if not isinstance(ref, str) or not ref.strip():
            raise ValueError("ref 必须为非空字符串")

        _git_repo.ensure()
        full = _git_repo._run_git(["rev-parse", "--verify", ref.strip()], check=True)

        raw = _git_repo._run_git(
            [
                "log",
                "-1",
                "--date=iso-strict",
                "--decorate=full",
                f"--pretty=format:{self._LOG_FMT}",
                full,
            ],
            check=True,
        )

        commits = self._parse_log_raw(raw)
        if not commits:
            raise RuntimeError(f"无法解析提交信息: {full}")

        commit = commits[0]
        self._fill_commit_files(commit)
        return commit


_git_history = GitHistory()
