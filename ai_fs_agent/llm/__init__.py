from ai_fs_agent.llm.llm_manager import LLMManager
from ai_fs_agent.config import ENV_PATH
from dotenv import load_dotenv

load_dotenv(ENV_PATH)  # 从 ENV_PATH 读取 .env 各模型的 API Key

# 实例化单例
llm_manager = LLMManager()

__all__ = ["llm_manager"]
