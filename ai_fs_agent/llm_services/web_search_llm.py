"""
联网搜索 LLM 服务

专门用于处理需要联网搜索的查询，获取最新实时信息。
基于支持联网搜索的模型实现。
"""

from typing import List, Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from ai_fs_agent.llm import llm_manager
from ai_fs_agent.utils.ingest.file_content_model import FileContentModel


class WebSearchLLM:
    """
    联网搜索 LLM 服务：
    - 使用支持联网搜索的模型处理需要联网搜索的查询
    - 提供批量联网搜索功能
    - 专注于GitHub等代码托管平台的搜索
    """

    def __init__(self):
        """
        初始化联网搜索 LLM 服务

        使用 web_search 角色的模型进行联网搜索
        """
        self.llm = llm_manager.get_by_role("web_search")
        self.system_prompt = """
角色：软件信息搜索助手

任务：基于软件名称，通过联网搜索获取软件的实用信息

搜索策略：
1. 首先在GitHub平台搜索软件信息
2. 如果在GitHub上找到相关信息，优先使用GitHub上的项目描述、README文档等
3. 如果在GitHub上搜索不到相关信息，则进行常规的互联网搜索
4. 不要在搜索结果中提及是否在GitHub上找到信息，直接提供软件描述即可

核心要求：
1. 提供软件的基本描述、主要功能和典型使用场景
2. 包含软件的主要特点和优势
3. 说明软件适合的用户群体
4. 如果在GitHub上找到信息，可以包含项目的star数、许可证等关键信息
5. 保持信息实用且易于理解

输出格式：
- 使用标准的Markdown格式输出
- 完整描述软件的基本信息和核心功能
- 包含软件的主要特点和适用场景
- 语言自然流畅，信息量适中
- 避免提及搜索过程或是否在GitHub上找到信息
- 避免过于技术性的术语和复杂细节
""".strip()

    def search_batch_files(
        self, file_content_models: List[FileContentModel], max_concurrency: int = 5
    ) -> List[AIMessage]:
        """
        批量处理软件相关文件内容搜索

        Args:
            file_content_models: 文件内容模型列表，包含文件路径和内容信息
            max_concurrency: 最大并发数，默认为5以避免API限制

        Returns:
            List[AIMessage]: 包含软件搜索结果的响应消息列表

        Note:
            - 专注于软件相关内容的搜索，自动提取关键信息进行联网搜索
            - 优先在GitHub等平台搜索软件项目信息
            - 由于联网搜索涉及外部API调用，建议控制并发数以避免速率限制
        """
        sys_msg = SystemMessage(content=self.system_prompt)
        # 准备批量消息，基于文件内容生成搜索查询
        messages_batch = [
            [
                sys_msg,
                HumanMessage(
                    content=f"文件: {file_model.file_path}\n类型: {file_model.file_type}"
                ),
            ]
            for file_model in file_content_models
        ]
        # 批量调用联网搜索模型
        search_responses = self.llm.batch(
            messages_batch,
            config={"max_concurrency": max_concurrency},
        )
        return search_responses
