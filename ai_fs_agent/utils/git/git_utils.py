import codecs
from typing import Any, Dict

from ai_fs_agent.utils.git.git_history import RecentCommit


def _normalize_path_display(v) -> str:
    """
    将 Git 的 core.quotepath 转义（如 "\346\265\213\350\257\225txt"）转换为可读 UTF-8。
    同时处理 bytes 路径。
    """
    if isinstance(v, (bytes, bytearray)):
        return v.decode("utf-8", errors="replace")
    s = str(v or "")
    if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
        s = s[1:-1]
    if "\\" in s:
        try:
            s1 = codecs.decode(s, "unicode_escape")  # 解析 \ooo/\xHH 等
            return s1.encode("latin-1", errors="ignore").decode(
                "utf-8", errors="replace"
            )
        except Exception:
            return s
    return s


def summarize_commit(commit: RecentCommit, max_files: int = 5) -> Dict[str, Any]:
    """
    将单个 RecentCommit 压缩为适合 AI 消费的概要信息（非列表）。
    返回字段：
    - short_id: 短哈希（便于展示）
    - date: 提交时间（优先 committer_date，其次 author date）
    - message: 提交标题（首行）
    - summary: 中文一句话概要（整合统计与文件示例）
    """
    # 统计信息
    total_files = (
        commit.files_changed
        if isinstance(commit.files_changed, int)
        else len(getattr(commit, "files", []) or [])
    )
    insertions = commit.insertions if isinstance(commit.insertions, int) else 0
    deletions = commit.deletions if isinstance(commit.deletions, int) else 0

    # 文件示例（最多 max_files 条）
    n = max_files if isinstance(max_files, int) and max_files > 0 else 0
    shown_files = commit.files[:n] if getattr(commit, "files", None) else []
    status_map = {"M": "修改", "A": "新增", "D": "删除", "R": "重命名", "C": "复制"}
    examples = []
    for f in shown_files:
        path_display = _normalize_path_display(getattr(f, "path", ""))
        status = status_map.get(
            getattr(f, "status", ""), getattr(f, "status", "") or "变更"
        )
        examples.append(f"{path_display}（{status}）")
    summary = f"改动{total_files}个文件，+{insertions} -{deletions}"
    if examples:
        summary += "；其中：" + "、".join(examples)
        if total_files > len(examples):
            summary += " 等"

    return {
        "short_id": commit.short_id,
        "date": (commit.committer_date or commit.date),
        "message": commit.message,
        "summary": summary,
    }


__all__ = ["summarize_commit", "_normalize_path_display"]
