"""
向量检索器：
- 从本地 FAISS 索引加载；
- 输入查询关键词，返回 top-k 条原始文本内容（不做任何拼装或改写）。
"""

from typing import List
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from ai_fs_agent.llm import llm_manager
from ai_fs_agent.config import RAG_INDEX_DIR


class VectorRetriever:
    """
    用于从本地 FAISS 索引进行向量检索，只返回命中文本内容。
    使用方式：
        retriever = VectorRetriever()
        results = retriever.search("关键字", k=5)
    """

    def __init__(self) -> None:
        """
        使用全局配置的 RAG_INDEX_DIR 作为索引所在目录（应包含 FAISS 索引文件）
        """
        self.index_dir = str(RAG_INDEX_DIR)
        self.embeddings: OpenAIEmbeddings = llm_manager.get_by_role("embedding")
        # 允许反序列化加载本地索引（仅用于受信任环境）
        self.vs: FAISS = FAISS.load_local(
            self.index_dir,
            self.embeddings,
            allow_dangerous_deserialization=True,
        )

    def search(self, query: str, k: int = 5) -> List[str]:
        """
        :param query: 查询关键词/问题
        :param k: 返回结果数量
        :return: 命中文档的原始文本内容列表（按相似度从高到低）
        """
        retriever = self.vs.as_retriever(search_kwargs={"k": k})
        docs = retriever.get_relevant_documents(query)
        return [d.page_content for d in docs]
