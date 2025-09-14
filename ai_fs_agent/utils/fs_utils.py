from pathlib import Path
from typing import Optional, Union, Dict, Any
import logging
from ai_fs_agent.config import user_config

logger = logging.getLogger(__name__)


def _check_workspace_dir(workspace_dir: Optional[Union[Path, str]] = None) -> str:
    root_raw = workspace_dir
    # 配置检查
    if root_raw is None:
        return "工作区目录未配置"
    if isinstance(root_raw, Path):
        root = root_raw
    elif isinstance(root_raw, str):
        # 去除前后空白
        root_raw = root_raw.strip()
        # 去除可能的引号
        root_raw = root_raw.strip('"').strip("'")
        root = Path(root_raw)
    else:
        return f"工作区目录类型不支持: {type(root_raw).__name__}"

    # 路径合法性检查
    if not root.is_absolute():
        return "工作区目录必须是绝对路径"
    if not root.exists():
        return "工作区目录不存在"
    if root.is_file():
        return "工作区目录不是文件夹"

    return ""  # 正常


def _root() -> Path:
    root = user_config.workspace_dir
    err = _check_workspace_dir(root)
    if err:
        raise ValueError(err)
    return Path(root).expanduser().resolve()


def _ensure_in_root(p: Path) -> Path:
    """确保路径在工作区内，并返回绝对规范化路径。"""
    root = _root()
    p = (root / p).resolve() if not p.is_absolute() else p.resolve()
    if root not in p.parents and p != root:
        raise ValueError(f"路径越界: {p}，请使用相对路径")
    return p


def _rel(p: Path) -> str:
    """返回相对工作区根的路径（统一使用 posix 分隔符）。"""
    root = _root()
    return p.resolve().relative_to(root).as_posix()


def _format_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    return f"{size:.2f} {units[unit_index]}"


def _stat_entry(p: Path) -> Dict[str, Any]:
    st = p.stat()
    return {
        "path": _rel(p),
        "type": "dir" if p.is_dir() else "file",
        "size": _format_size(st.st_size),
    }
