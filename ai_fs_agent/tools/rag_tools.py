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

    # 检查embedding模型是否已配置
    try:
        from ai_fs_agent.utils.rag.embedding_checker import check_embedding_config

        if not check_embedding_config():
            user_config.use_rag = False
            return {
                "ok": False,
                "error": "未配置embedding模型，自动禁止 RAG 配置。请先配置有效的embedding模型后，再启用 RAG 配置",
            }
    except Exception:
        return {"ok": False, "error": "检查embedding模型配置失败"}

    try:
        from ai_fs_agent.utils.rag.vector_retriever import VectorRetriever

        retriever = VectorRetriever()
        results = retriever.search(query=query, k=int(top_k))
        if results:
            return {"ok": True, "results": results}
        else:
            return {
                "ok": False,
                "error": "无法找到相关内容，相似度度过低的内容不会返回，请优化搜索关键词",
            }
    except Exception as e:
        return {"ok": False, "error": " RAG 查询失败，请检查配置或索引是否存在"}
