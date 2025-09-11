from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

# 工具：统一从 fs_tools 导入
from ai_fs_agent.tools import fs_tools_list

# LLM创建
from ai_fs_agent.llm import llm_manager

checkpointer = InMemorySaver()


def build_fs_agent():
    """
    构建可调用 fs_tools 的 Agent。
    """
    system_prompt = (
        "你是文件助手。"
        "在对文件执行写、删、移等操作时要谨慎，必要时先列目录确认。"
        "输出应简洁明了。"
    )

    agent = create_agent(
        model=llm_manager.get_by_role("fast"),
        tools=fs_tools_list,
        prompt=system_prompt,
        checkpointer=checkpointer,
    )
    return agent
