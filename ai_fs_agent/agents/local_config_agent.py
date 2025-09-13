from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from ai_fs_agent.llm import llm_manager
from ai_fs_agent.tools.loacl_config_tools import config_tools_list

checkpointer = InMemorySaver()


def build_local_config_agent():
    """配置管理 Agent，可以管理本地项目配置，如工作区目录等。"""

    system_prompt = """
角色：
- 配置助手（config_agent）。

目标：
- 使用提供的配置类工具，管理配置，仅负责管理项目配置，不对其他业务进行操作

工具使用策略：
- 未调用工具前，不要臆测配置值或状态

输出风格：
- 要点式、简短
""".strip()

    agent = create_agent(
        name="config_agent",
        model=llm_manager.get_by_role("fast"),
        tools=config_tools_list,
        prompt=system_prompt,
        checkpointer=checkpointer,
    )

    return agent
