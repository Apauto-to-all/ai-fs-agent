from pathlib import Path
from typing import Optional, Union
from ai_fs_agent.config import user_config


def check_workspace_dir(workspace_dir: Optional[Union[Path, str]] = None) -> str:
    """
    检查工作目录配置是否合法，并返回错误信息字符串。

    参数
    - workspace_dir: 可为 pathlib.Path 或 str。
      - 为 None 时表示未配置，将返回错误说明；
      - 为 str 时会自动去除首尾空白与引号；
      - 最终将被解析为 Path 对象进行进一步合法性校验。

    校验规则
    - 必须是绝对路径（Path.is_absolute() 为 True）；
    - 路径必须存在；
    - 路径必须为目录而非文件。

    返回
    - str: 若合法，返回空字符串 ""；
           若不合法，返回对应的错误信息（中文），包括但不限于：
           - "工作目录未配置"
           - "工作目录必须是绝对路径"
           - "工作目录不存在"
           - "工作目录不是文件夹"
           - "工作目录类型不支持: <类型名>"

    设计说明
    - 本函数仅返回错误文本，不抛异常，便于调用端根据需要自行决定抛出异常或提示用户。
    """
    root_raw = workspace_dir
    # 配置检查
    if root_raw is None:
        return "工作目录未配置"
    if isinstance(root_raw, Path):
        root = root_raw
    elif isinstance(root_raw, str):
        # 去除前后空白与可能的引号
        root_raw = root_raw.strip()
        root_raw = root_raw.strip('"').strip("'")
        root = Path(root_raw)
    else:
        return f"工作目录类型不支持: {type(root_raw).__name__}"

    # 路径合法性检查
    if not root.is_absolute():
        return "工作目录必须是绝对路径"
    if not root.exists():
        return "工作目录不存在"
    if root.is_file():
        return "工作目录不是文件夹"

    return ""  # 正常


def get_workspace_root() -> Path:
    """
    获取工作目录根路径，确保其存在且为绝对路径。

    来源
    - 从全局配置 user_config.workspace_dir 读取当前工作目录。

    行为
    - 调用 check_workspace_dir 进行合法性检查；
    - 若检查失败，抛出 ValueError，并将错误文本作为异常信息；
    - 若检查通过，返回展开用户目录（expanduser）并标准化（resolve）的绝对路径。

    返回
    - Path: 规范化后的工作目录根路径（绝对路径）。

    异常
    - ValueError: 当配置为空、非绝对路径、路径不存在或为文件时抛出。

    示例
    - root = _root()  # Path('E:/workspace/project')
    """
    # 从配置中获取工作目录
    root = user_config.workspace_dir
    err = check_workspace_dir(root)
    if err:
        raise ValueError(err)
    return Path(root).expanduser().resolve()
