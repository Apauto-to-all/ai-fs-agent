from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from ai_fs_agent.llm import llm_manager
from ai_fs_agent.tools.loacl_config_tools import config_tools_list

checkpointer = InMemorySaver()


def build_local_config_agent():
    """配置管理 Agent，可以管理本地项目配置，如工作区目录等。"""

    system_prompt = "你是配置助手（config_agent），仅负责管理项目配置，可以调用工具对项目配置进行管理，输出应简洁明了。"

    agent = create_agent(
        name="config_agent",
        model=llm_manager.get_by_role("fast"),
        tools=config_tools_list,
        prompt=system_prompt,
        checkpointer=checkpointer,
    )

    return agent
