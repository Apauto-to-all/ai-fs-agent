from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from ai_fs_agent.llm import llm_manager
from ai_fs_agent.tools.delegate_tools import delete_agent_tools

checkpointer = InMemorySaver()


def build_supervisor_agent():
    """
    使用 create_supervisor 构建主管 Agent：负责根据用户意图在各子 Agent 之间进行路由调用。
    成员代理：fs_agent（文件管理）、config_agent（配置管理）。
    """
    system_prompt = (
        "你是主管，在一个基于大模型的文件系统智能体项目中担任核心协调角色。"
        "你的职责：\n"
        "1) 读懂用户意图并选择调用适当的子代理；\n"
        "2) 只在需要时调用子代理；能直接回答的问题，直接给出答案；\n"
        "3) 子代理列表：\n"
        "   - fs_agent: 文件/目录相关，可以进行通用文件操作，如列目录、读写文件、移动或删除；\n"
        "   - config_agent: 项目配置相关，可以管理工作目录等配置内容，如校验或更新配置；\n"
        "4) 将子代理结果整合为简洁明确的答复。\n"
        "记住，你是这个智能体的协调者，确保所有操作安全、准确，并遵循项目的智能管理原则。"
    )

    # 创建主管
    supervisor_agent = create_agent(
        name="supervisor_agent",
        tools=delete_agent_tools,
        model=llm_manager.get_by_role("default"),
        prompt=system_prompt,
        checkpointer=checkpointer,
    )

    return supervisor_agent
