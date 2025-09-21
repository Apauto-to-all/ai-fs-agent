from ai_fs_agent.llm import llm_manager


class ImageLLM:
    """
    图像理解 LLM 封装：
    - 使用视觉模型分析图像并生成文本描述
    """

    def __init__(self):
        # 使用 vision 角色的模型进行图像理解
        self.llm = llm_manager.get_by_role("vision")
        self.system_prompt = """
角色：专业图像内容分析助手。
任务：对给定的图像进行简洁分析，生成准确的文字描述。
要求：
1. 客观描述主要物体、场景和动作
2. 对图像，进行详细的描述
3. 避免主观判断和情感词汇
4. 重点突出可用于分类的关键信息

只输出描述文本，不要添加解释或评论。
"""
