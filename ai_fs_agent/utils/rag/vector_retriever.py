"""
向量检索器：
- 从本地 Chroma 索引加载；
- 输入查询关键词，返回 top-k 条原始文本内容（不做任何拼装或改写）。
"""

from typing import List
from langchain_chroma import Chroma
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

    def search(self, query: str, k: int = 5, score_threshold: float = 1.5) -> List[str]:
        """
        :param query: 查询关键词/问题
        :param k: 返回结果数量
        :param score_threshold: 相似度分数阈值，默认 1.5，score 越小越相似
        :return: 命中文档的原始文本内容列表（按相似度从高到低）
        """
        retriever = self.vs.similarity_search_with_score(query=query, k=k)
        # score 越小越相似，保留 score <= score_threshold
        filtered = [
            doc.page_content
            for doc, score in retriever
            if score is not None and score <= score_threshold
        ]
        return filtered
