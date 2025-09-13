from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from ai_fs_agent.llm import llm_manager
from ai_fs_agent.tools.loacl_config_tools import config_tools_list

checkpointer = InMemorySaver()


def build_local_config_agent():
    """
    配置管理 Agent：当前仅提供 set_workspace_dir 工具。
    行为要求：
    - 当检测到工作区未设置或无效时，主动引导调用 set_workspace_dir。
    """
    system_prompt = "你是配置助手，仅负责管理本地项目配置。当需要设置或修复工作区目录时，请调用 set_workspace_dir 工具。"
    agent = create_agent(
        model=llm_manager.get_by_role("fast"),
        tools=config_tools_list,
        prompt=system_prompt,
        checkpointer=checkpointer,
    )
    return agent
