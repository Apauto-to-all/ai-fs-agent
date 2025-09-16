from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from ai_fs_agent.llm import llm_manager
from ai_fs_agent.tools.git_tools import git_tools_list

checkpointer = InMemorySaver()


def build_git_agent():
    """Git 管理 Agent：支持查询最近提交与按引用回退。"""
    system_prompt = """
角色：
- Git 助手（git_agent）。

目标：
- 使用提供的 Git 工具在当前工作目录内执行：
  1) 查询最近的提交信息
  2) 按提交引用回退

约束与安全：
- 回退属于危险操作，仅在用户明确要求时调用；必要时简要提示风险

工具使用策略：
- 只调用提供的两种工具：git_recent_commits、git_rollback
- 尽量减少调用次数；能一次说清就不要多轮探测

输出风格：
- 要点式、简短
""".strip()

    agent = create_agent(
        name="git_agent",
        model=llm_manager.get_by_role("fast"),
        tools=git_tools_list,
        prompt=system_prompt,
        checkpointer=checkpointer,
    )

    return agent
