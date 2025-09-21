"""
批量索引构建器：
- 接收文件路径列表，加载文本内容，切割文本片段。
- 使用 VectorIndexBuilder 进行向量化并构建索引。
"""

from typing import List, Iterable

from ai_fs_agent.utils.ingest.file_loader import FileLoader
from ai_fs_agent.utils.ingest.text_processor import TextProcessor
from ai_fs_agent.utils.rag.index_builder import VectorIndexBuilder


class BatchIndexBuilder:
    """
    文件批量索引构建编排：
    1) 加载文件内容
    2) 切割文本片段
    3) 组装文本列表（每段首行加文件路径）
    4) 调用 VectorIndexBuilder 构建索引
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """chunk_size: 文本切割块大小；chunk_overlap: 块重叠大小"""
        self.loader = FileLoader()
        self.processor = TextProcessor()
        self.index_builder = VectorIndexBuilder()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def batch_build_index(self, file_paths: List[str], batch_size: int = 10) -> None:
        """
        对一批文件进行索引构建。
        :param file_paths: 文件路径列表
        """
        texts = self._load_and_split_texts(file_paths)
        if not texts:
            return
        self.index_builder.build(texts, batch_size=batch_size)  # 默认批大小 10，可调整

    def _load_and_split_texts(self, file_paths: Iterable[str]) -> List[str]:
        """加载文件，切割文本，返回文本片段列表（每段首行加路径）"""
        texts: List[str] = []
        for path in file_paths:
            try:
                raw_text = self.loader.load_file(path).content
            except ValueError as e:
                print(f"⚠️ 加载文件失败: {path}，跳过。错误: {e}")
                continue
            if not raw_text.strip():
                continue
            # 使用 split_into_chunks 切割文本
            chunks = self.processor.split_into_chunks(
                raw_text,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
            )
            for chunk in chunks:
                # 每段首行加文件路径，便于检索
                text = f"文件路径【{path}】\n{chunk}"
                texts.append(text)

        return texts
