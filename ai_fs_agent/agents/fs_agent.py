from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from ai_fs_agent.llm import llm_manager
from ai_fs_agent.tools.fs_tools import fs_tools_list

checkpointer = InMemorySaver()


def build_fs_agent():
    """构建可调用 fs_tools 的 Agent。支持文件操作。"""

    system_prompt = "你是文件助手（fs_agent），能在工作目录下，调用工具对本地文件系统进行操作，输出应简洁明了。"

    agent = create_agent(
        name="fs_agent",
        model=llm_manager.get_by_role("fast"),
        tools=fs_tools_list,
        prompt=system_prompt,
        checkpointer=checkpointer,
    )

    return agent
