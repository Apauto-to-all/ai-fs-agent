from typing import Optional, List, Dict, Any
import json
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from ai_fs_agent.agents.fs_agent import build_fs_agent
from ai_fs_agent.agents.local_config_agent import build_local_config_agent
from ai_fs_agent.agents.git_agent import build_git_agent
from ai_fs_agent.agents.classify_agent import build_classify_agent

# 子 Agent 注册表：新增分类等子 Agent 时在此补充
AGENT_REGISTRY = {
    "fs_agent": build_fs_agent,
    "config_agent": build_local_config_agent,
    "git_agent": build_git_agent,
    "classify_agent": build_classify_agent,
}


def _last_ai_text(messages: List[Any]) -> str:
    for m in reversed(messages):
        if isinstance(m, AIMessage):
            return m.content or ""
    return ""


@tool("delegate_to_agent", return_direct=False)
def delegate_to_agent(
    agent: str,
    instruction: str,
) -> str:
    """
    将一个清晰的子任务委托给指定子 Agent 执行（隔离上下文）
    - agent: 目标子 Agent 名称（'fs_agent' | 'config_agent' | 'git_agent' | 'classify_agent'）
    - instruction: 明确的任务说明（子 Agent 需要做什么）
    """
    if agent not in AGENT_REGISTRY:
        return json.dumps(
            {"status": "error", "error": f"未注册的子 Agent: {agent}"},
            ensure_ascii=False,
        )

    view_messages = [
        HumanMessage(content=instruction),
    ]

    # 构建并调用目标子 Agent
    sub_agent = AGENT_REGISTRY[agent]()

    result = sub_agent.invoke({"messages": view_messages})
    msgs: List[Any] = result.get("messages", [])
    final_text = _last_ai_text(msgs)

    return {
        "status": "ok",
        "agent": agent,
        "final": final_text,
    }
