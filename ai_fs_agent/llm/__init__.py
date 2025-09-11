from ai_fs_agent.llm.llm_manager import ModelManager
from ai_fs_agent.config import ENV_PATH
from dotenv import load_dotenv

load_dotenv(ENV_PATH)  # 从 ENV_PATH 读取 .env 各模型的 API Key

# 实例化单例
model_manager = ModelManager()

__all__ = ["model_manager"]
