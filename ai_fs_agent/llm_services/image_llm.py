from typing import List, Optional
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from ai_fs_agent.llm import llm_manager
from ai_fs_agent.utils.ingest.file_content_model import FileContentModel


class ImageLLM:
    """
    图像理解 LLM 封装：
    - 使用视觉模型分析图像并生成文本描述
    - 提供批量图像处理功能
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

    def process_images_batch(
        self, image_file_content: List[FileContentModel], max_concurrency: int = 5
    ) -> list[AIMessage]:
        """
        批量处理图像文件，生成图像描述
        :param image_file_content: 图像文件模型列表，每个模型需要包含 image_base64 字段
        :param max_concurrency: 最大并发数
        :return: 图像描述列表，每个元素为 AIMessage 类型，包含图像的描述文本
        """
        sys_msg = SystemMessage(content=self.system_prompt)
        messages_batch = []
        # TODO：对图像进行压缩处理，减少Token消耗
        for s in image_file_content:
            human_msg = HumanMessage(
                content=[
                    {
                        "type": "image_url",
                        "image_url": {"url": s.image_base64},
                    },
                ]
            )
            messages_batch.append([sys_msg, human_msg])
        # 批量调用图像模型
        image_responses = self.llm.batch(
            messages_batch,
            config={"max_concurrency": max_concurrency},
        )
        return image_responses
