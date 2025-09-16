import logging
import traceback

logger = logging.getLogger(__name__)

import os
import platform
import subprocess
import shutil
from typing import Optional, List
from pydantic import BaseModel, Field
from ai_fs_agent.utils.workspace import get_workspace_root
from ai_fs_agent.config import user_config


class EnsureRepoResult(BaseModel):
    created: bool = Field(..., description="是否新初始化了仓库")
    root: str = Field(..., description="仓库根目录绝对路径")
    branch: str = Field(..., description="当前分支名，可能为 'HEAD'（未出生）")


class GitRepo:
    """
    以“仓库实例”为中心管理 Git：
    - 工作路径动态来自 _root()，不在实例中持久化
    - 所有 Git 命令统一在 _root() 下执行，禁止自定义 cwd
    - 仅关注“工作目录自身”的 Git 仓库，忽略父目录或子目录的仓库
    - ensure(): 保证可用仓库（仅在工作目录内初始化）
    - has_changes(): 是否存在未提交改动
    - commit_all(): 提交全部改动
    - get_head(): 获取 HEAD 提交
    """

    def __init__(
        self,
        default_branch: str = "main",
        user_name: Optional[str] = None,
        user_email: Optional[str] = None,
        prefer_nested: bool = True,
    ) -> None:
        self.default_branch = default_branch
        self.user_name = user_name
        self.user_email = user_email
        self.prefer_nested = prefer_nested

    # ---------- 内部工具 ----------

    def _workspace_dir(self) -> str:
        """
        动态获取当前工作目录；当配置不合法时抛出 RuntimeError。
        """
        try:
            return str(get_workspace_root())
        except ValueError as e:
            raise RuntimeError(f"工作目录无效：{e}") from e

    def _check_git_available(self) -> None:
        """检查 git 可用性，若不可用则抛出异常。"""
        if shutil.which("git") is None:
            user_config.use_git = False  # 自动禁用 Git 功能
            raise RuntimeError("未找到 git 可执行文件，请先安装并确保在 PATH 中。")

    def _run_git(self, args: List[str], check: bool = True) -> str:
        """
        运行 git 子命令并返回 stdout（去掉末尾换行）。
        所有命令一律在 _root() 下执行，禁止自定义 cwd。
        """
        self._check_git_available()
        # 关键修复：统一剔除每个参数的首尾空白，避免意外的换行/空格导致引用解析失败
        safe_args = [a.strip() if isinstance(a, str) else a for a in args]
        result = subprocess.run(
            ["git", *safe_args],
            cwd=self._workspace_dir(),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if check and result.returncode != 0:
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            msg = f"git {' '.join(safe_args)} 失败: {stderr or stdout or result.returncode}"
            logger.error(msg)
            raise RuntimeError(msg)
        return (result.stdout or "").strip()

    def _has_git_here(self, path: str) -> bool:
        """判断指定路径（工作目录）是否已是 Git 仓库（仅关注该目录自身）。"""
        return os.path.isdir(os.path.join(path, ".git"))

    def _ensure_local_user_config(self) -> None:
        """
        确保工作根目录对应仓库配置了本地 user.name/user.email（不污染父/全局）。
        通过 `git -C <root> config --local ...` 显式指定仓库路径，避免修改父目录或其它仓库。
        """
        root = self._workspace_dir()  # 明确工作根路径

        # 读取工作根仓库的本地配置（允许失败返回空）
        name = self._run_git(
            ["-C", root, "config", "--local", "user.name"], check=False
        )
        email = self._run_git(
            ["-C", root, "config", "--local", "user.email"], check=False
        )
        if name and email:
            return

        name = (self.user_name or "ai-fs-agent").strip()
        email = (self.user_email or "ai-fs-agent@local").strip()
        # 显式针对工作根仓库写入本地配置（不会影响父仓库或全局配置）
        self._run_git(["-C", root, "config", "--local", "user.name", name], check=True)
        self._run_git(
            ["-C", root, "config", "--local", "user.email", email], check=True
        )

    def _ensure_windows_settings(self) -> None:
        """Windows 行尾策略，减少 CRLF/Unix 差异带来的噪音。"""
        if platform.system().lower().startswith("win"):
            try:
                self._run_git(
                    ["config", "--local", "core.autocrlf", "true"], check=True
                )
            except RuntimeError:
                logger.debug("设置 core.autocrlf 失败（可忽略）", exc_info=True)

    # ---------- 公共 API ----------

    def ensure(self) -> EnsureRepoResult:
        """
        确保工作目录是一个可用的 Git 仓库（路径动态来自 _root）。
        仅在工作目录自身初始化（不复用父仓库），并设置本地配置。
        """
        ws = self._workspace_dir()
        created = False
        # 只关注工作目录自身是否已是仓库；若不是，则在此初始化
        if not self._has_git_here(ws):
            try:
                self._run_git(["init", "-b", self.default_branch], check=True)
            except RuntimeError:
                # 兼容旧版 Git（不支持 -b）
                self._run_git(["init"], check=True)
                self._run_git(["checkout", "-B", self.default_branch], check=True)
            created = True

        root = ws  # 仓库根即工作目录自身

        # 本地用户信息与 Windows 设置
        self._ensure_local_user_config()
        self._ensure_windows_settings()

        # 当前分支（允许“未出生 HEAD”时失败，回退为 'HEAD'）
        branch = (
            self._run_git(["rev-parse", "--abbrev-ref", "HEAD"], check=False) or "HEAD"
        )

        return EnsureRepoResult(created=created, root=root, branch=branch)

    def has_changes(self) -> bool:
        """
        是否存在未提交的改动（工作区或暂存区）。
        """
        self.ensure()
        out = self._run_git(["status", "--porcelain"], check=True)
        return len(out.strip()) > 0

    def commit_all(self, message: str, allow_empty: bool = False) -> Optional[str]:
        """
        提交全部改动并返回 commit id（没有改动且不允许空提交时返回 None）。
        """
        self.ensure()

        # 暂存全部
        self._run_git(["add", "-A"], check=True)

        # 无变化且不允许空提交
        if not self.has_changes() and not allow_empty:
            return None

        args = ["commit", "-m", message]
        if allow_empty:
            args.append("--allow-empty")
        self._run_git(args, check=True)

        return self.get_head(short=False)

    def get_head(self, short: bool = True) -> str:
        """
        获取当前 HEAD 提交哈希。
        """
        self.ensure()
        if short:
            return self._run_git(["rev-parse", "--short", "HEAD"], check=True)
        return self._run_git(["rev-parse", "HEAD"], check=True)

    def rollback_to(self, commit: str, clean_untracked: bool = False) -> str:
        """
        回退（重置）到指定提交。

        参数
        - commit: 目标提交引用，可为完整/短哈希，或相对引用（如 "HEAD~1", "HEAD^"）。
        - clean_untracked: 是否清理未跟踪文件与空目录（git clean -fd）。默认 False。

        行为
        - 执行 `git reset --hard <commit>` 回到指定版本；
        - 若 clean_untracked=True，再执行 `git clean -fd` 清理未跟踪文件/目录；
        - 返回回退后的 HEAD 提交哈希（完整哈希）。

        注意
        - reset --hard 会丢弃工作区与暂存区的未提交改动（对被 Git 跟踪的文件）；
        - 未跟踪文件默认不会删除，除非显式设置 clean_untracked=True；
        - 若 <commit> 无效或超出历史，底层会抛出 RuntimeError
        """
        self.ensure()
        # 先解析为完整哈希，保证短哈希不唯一时及时失败
        full = self._run_git(["rev-parse", "--verify", commit], check=True)
        # 回退到目标提交（丢弃工作区与暂存区更改）
        self._run_git(["reset", "--hard", full], check=True)
        # 可选：清理未跟踪文件/目录
        if clean_untracked:
            self._run_git(["clean", "-fd"], check=True)
        return full

    def undo_last(self) -> str:
        """
        单步撤销：将当前 HEAD 撤销到“上一次指针位置”（HEAD@{1}）。
        多次调用会在两点之间来回切换。
        返回撤销后的完整提交哈希。
        """
        self.ensure()
        target = self._run_git(["rev-parse", "--verify", "HEAD@{1}"], check=True)
        self._run_git(["reset", "--hard", target], check=True)
        return target


_git_repo = GitRepo()
# git退回操作添加一个人工验证，可以参考loacl_config_tools文件，
