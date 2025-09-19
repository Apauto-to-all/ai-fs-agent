"""
向量索引构建器：
- 传入文本列表，按批次向量化（默认每批 10 条），构建本地 FAISS 索引。
- 索引每次调用都会从空开始构建并保存到 index_dir。
- 依赖项目内 llm_manager 提供的 embedding（已在配置中禁用了 check_embedding_ctx_length）。
"""

from typing import Iterable, List, Optional

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

from ai_fs_agent.llm import llm_manager
from ai_fs_agent.config import RAG_INDEX_DIR


class VectorIndexBuilder:
    """
    用于将一批纯文本向量化并保存到本地 FAISS 索引。
    使用方式：
        builder = VectorIndexBuilder()
        builder.build(texts)
    """

    def __init__(self) -> None:
        """
        使用全局配置的 RAG_INDEX_DIR 作为索引保存目录
        """
        self.index_dir = str(RAG_INDEX_DIR)
        self.embeddings: OpenAIEmbeddings = llm_manager.get_by_role("embedding")
        self._vs: Optional[FAISS] = None

    def build(self, texts: List[str], batch_size: int = 10) -> None:
        """
        从零开始构建索引并保存到本地。
        :param texts: 纯文本列表，每个元素将成为一个可检索的文档片段
        """
        if batch_size <= 0:
            raise ValueError("batch_size 必须为正整数")

        if not texts:
            raise ValueError("texts 不能为空")

        self._vs = None  # 每次重建
        for batch in self._iter_batches(texts, batch_size):
            if self._vs is None:
                # 第一批：创建索引
                self._vs = FAISS.from_texts(batch, self.embeddings)
            else:
                # 追加后续批
                self._vs.add_texts(batch)

        # 持久化到本地目录
        assert self._vs is not None
        self._vs.save_local(self.index_dir)

    @staticmethod
    def _iter_batches(items: Iterable[str], batch_size: int) -> Iterable[List[str]]:
        """将可迭代对象切分为固定大小的批次。"""
        batch: List[str] = []
        for it in items:
            batch.append(it)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch
