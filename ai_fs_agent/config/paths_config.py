import logging
import traceback

logger = logging.getLogger(__name__)
from pathlib import Path
from ai_fs_agent.config.templates import MODEL_CONFIG_TEMPLATE, ENV_TEMPLATE


# 项目根目录（基于当前文件位置向上推导）
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 子目录路径
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# 文件路径
LLM_CONFIG_PATH = CONFIG_DIR / "llm_models.toml"
ENV_PATH = CONFIG_DIR / ".env"
USER_CONFIG_PATH = CONFIG_DIR / "user_config.json"


def ensure_directories() -> None:
    """确保所有必要目录存在"""
    for d in [CONFIG_DIR, DATA_DIR, LOGS_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def ensure_files() -> None:
    """确保所有必要文件存在，如果不存在则创建模板"""
    # .env
    if not ENV_PATH.exists():
        ENV_PATH.write_text(ENV_TEMPLATE, encoding="utf-8")

    # llm_models.toml
    if not LLM_CONFIG_PATH.exists():
        LLM_CONFIG_PATH.write_text(MODEL_CONFIG_TEMPLATE, encoding="utf-8")


def bootstrap_paths() -> None:
    """显式调用：创建目录与基础文件。"""
    ensure_directories()
    ensure_files()
