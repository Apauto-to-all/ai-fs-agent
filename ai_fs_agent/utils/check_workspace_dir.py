from pathlib import Path
from typing import Optional


def _check_workspace_dir(workspace_dir: Optional[Path] = None) -> str:
    root_raw = workspace_dir
    # 配置检查
    if root_raw is None:
        return "工作区目录未配置"
    if isinstance(root_raw, Path):
        root = root_raw
    elif isinstance(root_raw, str):
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
