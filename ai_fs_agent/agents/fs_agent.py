from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from ai_fs_agent.llm import llm_manager
from ai_fs_agent.tools.fs_tools import fs_tools_list

checkpointer = InMemorySaver()


def build_fs_agent():
    """构建可调用 fs_tools 的 Agent。支持文件操作。"""

    system_prompt = """
角色：
- 文件助手（fs_agent）。

目标：
- 在当前工作目录内，使用提供的文件系统工具完成用户请求

约束：
- 你无法看到工作目录路径，只能使用相对路径调用工具

工具使用策略：
- 未调用工具前，不要臆测工具结果

输出风格：
- 要点式、简短
""".strip()
    agent = create_agent(
        name="fs_agent",
        model=llm_manager.get_by_role("fast"),
        tools=fs_tools_list,
        prompt=system_prompt,
        checkpointer=checkpointer,
    )

    return agent
