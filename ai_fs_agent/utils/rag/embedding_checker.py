"""
Embedding模型配置检查器：
- 检查是否已配置有效的embedding模型
- 提供统一的检测接口，供其他模块调用
"""


def check_embedding_config() -> bool:
    """
    检查是否已配置embedding模型
    返回：True表示已配置，False表示未配置
    """
    try:
        # 尝试获取embedding模型，如果失败说明未配置
        from ai_fs_agent.llm import llm_manager

        llm_manager.get_by_role("embedding")
        return True
    except Exception:
        return False
