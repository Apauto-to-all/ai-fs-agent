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
            "角色：专业文件主题标签抽取助手。"
            "任务：依据给定文本内容生成用于分类与检索的高层语义标签列表。"
            "输出要求："
            "1. 输出严格为标签列表（由外部结构化解析，不添加解释、前后缀、编号、额外字段）。"
            "2. 按重要性由高到低排序。"
            "3. 首个标签必须为文件类型，取自固定集合：['文本','图像','视频','音频','代码','表格','演示','网页','压缩','其他'……]。无法可靠判断时使用 '未知'。"
            "4. 总数 3-10 个；内容极少或噪声时可降至 1-3 个。"
            "5. 每个标签 2-4 个汉字，不含标点、空格、引号、数字序号、emoji。"
            "6. 用抽象/通用概念：主题、体裁、领域、核心议题；避免：具体人名、地名、时间、情节细节、情绪/氛围词、格式性词（如 '文章', '文件'）。"
            "7. 语义去重：同义/近义择最常用（如 '科幻' 而非 '科幻小说'，'成长' 而非 '成长经历'）。"
            "8. 只使用简体中文；源文本含多语种时仍输出中文标签（专有英文术语可保留，如 'AI'）。"
            "9. 不输出：解释、分析、理由、空标签、重复标签、过细粒度概念。"
            "10. 若文本包含多个主题，优先抽取最能区分类别的上位概念。"
            "边界策略："
            "- 极短/噪声/无法判定：文件类型 + 1~2 个最高层通用概念。"
            "- 如果内容为代码：类型用 '代码'，并给语言/领域（如 '算法','网络','数据处理'）。"
            "- 若内容主要是表格结构：类型 '表格'；演示文稿：'演示'；压缩包内聚合描述不足：'压缩'。"
            "正例："
            "童话故事：['文本','童话','成长','家庭','动物']"
            "科幻短篇：['文本','科幻','未来','伦理','危机']"
            "含机器学习模型描述的技术文档：['文本','技术','机器学习','模型','优化']"
            "Python 源码实现图搜索：['代码','算法','图','搜索','路径']"
            "反例（不要这样）："
            "['这是一个故事', '有一只小猫', '很温暖']  # 含句子/细节/情绪"
            "['文本','科幻小说','科幻','未来']          # 语义重复"
            "['文本','人物','地点','时间']             # 过于空泛"
            "['文本','成长经历','家庭关系发展']         # 过长"
            "只输出标签数组（不要多余文字）"
        ).strip()
        self.structured_output_prompt = generate_structured_prompt(TagListModel)
