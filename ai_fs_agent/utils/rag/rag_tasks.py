from huey import SqliteHuey
import tempfile, os
from typing import List
from ai_fs_agent.utils.rag.batch_index_builder import BatchIndexBuilder

# 创建 Huey 实例
huey = SqliteHuey(
    name="rag_tasks",
    filename=os.path.join(tempfile.gettempdir(), "rag_tasks_huey.db"),
)

# 创建 BatchIndexBuilder 实例
batch_index_builder = BatchIndexBuilder()


@huey.task()
def build_rag_index(files: List[str]):
    """异步任务：构建 RAG 索引"""
    batch_index_builder.batch_build_index(files)
