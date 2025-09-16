from pathlib import Path
from typing import Dict, Any
from ai_fs_agent.utils.path_safety import rel_to_workspace


def format_size(size_bytes: int) -> str:
    """
    将字节数格式化为易读的字符串（带单位，四舍五入到两位小数）。

    参数
    - size_bytes: 整数，字节数（>= 0）。

    单位
    - 依次在 ["B", "KB", "MB", "GB", "TB"] 中选择最合适的单位；
    - 每 1024 进阶一级。

    返回
    - str: 形如 "0 B", "1.23 KB", "4.56 MB" 等。

    示例
    - format_size(0) -> "0 B"
    - format_size(1536) -> "1.50 KB"
    """
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    return f"{size:.2f} {units[unit_index]}"


def stat_entry(p: Path) -> Dict[str, Any]:
    """
    获取文件或目录的关键信息并以字典形式返回。

    参数
    - p: 目标路径。需指向一个已存在的文件或目录。
         注意：函数不会自动进行工作目录边界校验，若用于外部输入路径，建议先调用 ensure_in_workspace。

    行为
    - 调用 p.stat() 获取底层文件系统信息；
    - 字段 path：返回相对工作目录根路径（POSIX 风格），通过 rel_to_workspace 生成；
    - 字段 type：'dir' 或 'file'；
    - 字段 size：人类可读的大小字符串（目录大小为其自身 stat().st_size 值的格式化结果）。

    返回
    - Dict[str, Any]: 例如 {"path": "data/file.txt", "type": "file", "size": "1.23 KB"}。

    异常
    - FileNotFoundError / PermissionError / OSError: 由 p.stat() 传播；
    - ValueError: 当 p 不在工作目录下且调用 rel_to_workspace 引发异常时传播。

    示例
    - info = stat_entry(ensure_in_workspace(Path("data/readme.md")))
    - info == {"path": "data/readme.md", "type": "file", "size": "2.34 KB"}
    """
    st = p.stat()
    return {
        "path": rel_to_workspace(p),
        "type": "dir" if p.is_dir() else "file",
        "size": format_size(st.st_size),
    }
