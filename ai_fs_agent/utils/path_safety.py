from pathlib import Path
from ai_fs_agent.utils.workspace import get_workspace_root

DEFAULT_EXCLUDED_NAMES = {".git"}


def is_path_excluded(p: Path) -> bool:
    """
    判断路径是否位于“排除列表”中（自身或任一父级名称命中）。
    仅使用默认名称集 DEFAULT_EXCLUDED_NAMES。
    """
    names = {s.lower() for s in DEFAULT_EXCLUDED_NAMES}
    try:
        for part in p.parts:
            if part.lower() in names:
                return True
        return False
    except Exception:
        return True


def ensure_in_workspace(p: Path) -> Path:
    """
    确保给定路径位于工作目录根路径内，并返回该路径的绝对规范化路径。

    参数
    - p: 目标路径。可以为相对路径或绝对路径。
         - 若为相对路径，则以工作目录根为基准进行拼接；
         - 无论输入为何种形式，最终都会进行 resolve() 以去除符号链接与冗余路径段。

    行为
    - 将 p 规范化为绝对路径；
    - 校验该绝对路径是否在工作目录根路径下（允许等于根路径本身）;
    - 若越界（不在根路径之下），抛出 ValueError。

    返回
    - Path: 规范化后的绝对路径（位于工作目录内）。

    异常
    - ValueError: 当目标路径越界时，抛出 "路径越界: <绝对路径>，请使用相对路径"。

    设计说明
    - 该函数用于写入/读取等需要强约束“工作目录边界”的场景；
    - 使用 resolve() 以处理 .. / 符号链接等情况，从而增强安全性与可预测性。

    示例
    - abs_p = ensure_in_workspace(Path("data/file.txt"))
    # 返回：Path('E:/workspace/project/data/file.txt')
    - abs_p = ensure_in_workspace(Path("E:/workspace/project/data/file.txt"))
    # 返回：Path('E:/workspace/project/data/file.txt')
    """
    root = get_workspace_root()
    p = (root / p).resolve() if not p.is_absolute() else p.resolve()
    if root not in p.parents and p != root:
        raise ValueError(f"路径越界: {p}，请使用相对路径")
    return p


def rel_to_workspace(p: Path) -> str:
    """
    获取目标路径相对于工作目录根的相对路径（统一使用 POSIX 分隔符'/'）。

    参数
    - p: 目标路径。可以为相对或绝对路径。函数内部会先规范化，再计算相对路径。

    行为
    - 调用 get_workspace_root() 获取根路径；
    - 使用 Path.resolve() 规范化 p；
    - 使用 Path.relative_to(root) 计算相对路径，并转换为 POSIX 格式字符串（as_posix）。

    返回
    - str: 相对工作目录根的 POSIX 风格路径字符串。

    异常
    - ValueError: 当 p 不在工作目录根路径下时，Path.relative_to 会抛出异常。
      一般情况下，调用此函数前应保证 p 已通过 ensure_in_workspace 校验。

    设计说明
    - 隐藏工作目录的绝对路径信息，避免在日志/对外输出中泄露本机目录结构。

    示例
    - _rel(Path("E:/workspace/project/data/file.txt")) -> "data/file.txt"
    """
    root = get_workspace_root()
    return p.resolve().relative_to(root).as_posix()
