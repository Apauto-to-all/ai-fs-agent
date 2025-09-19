from ai_fs_agent.config.paths_config import (
    LLM_CONFIG_PATH,
    ENV_PATH,
    USER_CONFIG_PATH,
    RAG_INDEX_DIR,
    bootstrap_paths,
)
from ai_fs_agent.config.logging_config import setup_logging
from ai_fs_agent.config.user_config import UserConfig


def _init_app() -> UserConfig:
    """应用初始化入口：路径/文件自举、日志装配、加载用户配置"""
    bootstrap_paths()
    setup_logging()
    import logging

    logger = logging.getLogger(__name__)

    logger.info(
        "ai-fs-agent v0.1.0 启动 - 基于大模型的文件系统智能体，借助大模型实现对文件/文件夹的智能管理。"
    )
    if USER_CONFIG_PATH.exists():
        return UserConfig.model_validate_json(
            USER_CONFIG_PATH.read_text(encoding="utf-8")
        )
    # 创建默认配置并保存
    default_config = UserConfig()
    default_config._save_to_file()
    return default_config


user_config = _init_app()
"""用户配置实例，包含所有用户配置的值"""


__all__ = [
    "LLM_CONFIG_PATH",
    "ENV_PATH",
    "user_config",
]
