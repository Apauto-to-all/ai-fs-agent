"""
向量检索器：
- 从本地 Chroma 索引加载；
- 输入查询关键词，返回 top-k 条原始文本内容（不做任何拼装或改写）。
"""

from typing import List
from langchain_chroma import Chroma  # 更新导入
from langchain_openai import OpenAIEmbeddings
from ai_fs_agent.llm import llm_manager
from ai_fs_agent.config import RAG_INDEX_DIR


class VectorRetriever:
    """
    用于从本地 Chroma 索引进行向量检索，只返回命中文本内容。
    使用方式：
        retriever = VectorRetriever()
        results = retriever.search("关键字", k=5)
    """

    def __init__(self) -> None:
        """
        使用全局配置的 RAG_INDEX_DIR 作为索引所在目录（应包含 Chroma 索引文件）
        """
        self.index_dir = str(RAG_INDEX_DIR)
        self.embeddings: OpenAIEmbeddings = llm_manager.get_by_role("embedding")
        # 加载本地索引
        self.vs: Chroma = Chroma(
            persist_directory=self.index_dir, embedding_function=self.embeddings
        )

    def search(self, query: str, k: int = 5) -> List[str]:
        """
        :param query: 查询关键词/问题
        :param k: 返回结果数量
        :return: 命中文档的原始文本内容列表（按相似度从高到低）
        """
        retriever = self.vs.as_retriever(search_kwargs={"k": k})
        # 更新为 invoke 方法
        docs = retriever.invoke(query)
        return [d.page_content for d in docs]

    # 如果需要返回元组（文本, 分数）
    def search_with_scores(self, query: str, k: int = 5) -> List[tuple[str, float]]:
        """
        :return: 列表，每个元素为 (文本内容, 相似度分数)
        """
        results_with_scores = self.vs.similarity_search_with_score(query, k=k)
        return [(doc.page_content, score) for doc, score in results_with_scores]
