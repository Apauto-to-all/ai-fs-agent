from typing import List
from pydantic import BaseModel, Field
from ai_fs_agent.llm import llm_manager
from structured_output_prompt import generate_structured_prompt


class TagListModel(BaseModel):
    """LLM 结构化输出：文件内容主题标签列表"""

    tags: List[str] = Field(default_factory=list, description="主题标签列表")


class TaggingLLM:
    """
    文本打标签（主题抽取）LLM 封装：
    - 提供系统提示词
    - 提供结构化输出模型
    - 对外暴露 structured_prompt 与 model_with_structure
    """

    def __init__(self):
        self.llm = llm_manager.get_by_role("fast")
        self.model_with_structure = self.llm.with_structured_output(TagListModel)
        self.system_prompt = (
            "你是一个专业的文本语义主题抽取助手，专为文件分类和检索生成标签。\n"
            "- 首先判断文件类型（如 '文本'、'图像'、'视频' 等），并将其作为第一个标签。\n"
            "- 输出紧凑、抽象且信息量高的标签，便于文件夹分类和聚类。\n"
            "- 优先选择通用主题词，避免具体人名、地名、情节细节或氛围描述。\n"
            "- 不要重复、不要冗长；每个标签不超过4个字。\n"
            "- 最多输出10个标签，聚焦核心主题。\n"
            "- 示例：对于童话故事，输出 ['文本', '童话', '动物', '成长', '家庭' ……]；对于科幻小说，输出 ['文本', '科幻', '未来', '伦理', '危机' ……]。"
        ).strip()
        self.structured_output_prompt = generate_structured_prompt(TagListModel)
