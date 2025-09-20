from typing import Any, Dict
from langchain.tools import tool

from ai_fs_agent.config import user_config


@tool("rag_query")
def rag_query(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    RAG 搜索工具：传入查询关键词 query，返回 top_k 条相关文本内容
    返回：{ok, results?[], error?}
    """
    # 配置开关判断
    if not user_config.use_rag:
        return {"ok": False, "error": "RAG 功能已被配置为禁用"}

    try:
        from ai_fs_agent.utils.rag.vector_retriever import VectorRetriever

        retriever = VectorRetriever()
        results = retriever.search(query=query, k=int(top_k))
        return {"ok": True, "results": results}
    except Exception as e:
        return {"ok": False, "error": " RAG 查询失败，请检查配置或索引是否存在"}
