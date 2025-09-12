import json
import time
from typing import List

from openai import RateLimitError
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage,
    SystemMessage,
    BaseMessage,
)

from ai_fs_agent.agents.fs_agent import build_fs_agent


def format_tool_message_content(content: str) -> str:
    """尝试把工具返回的 JSON 美化；不是 JSON 则原样返回。"""
    try:
        data = json.loads(content)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        return content


def print_ai_tool_calls(msg: AIMessage):
    """打印 AIMessage 中的 tool_calls（模型规划阶段）"""
    if not getattr(msg, "tool_calls", None):
        return
    print("  ↳ 规划的工具调用:")
    for i, tc in enumerate(msg.tool_calls, 1):
        name = tc.get("name") or tc.get("function", {}).get("name")
        # OpenAI 风格 arguments 可能是 JSON 字符串
        args = tc.get("args") or tc.get("function", {}).get("arguments")
        if isinstance(args, str):
            try:
                args_obj = json.loads(args)
                args = json.dumps(args_obj, ensure_ascii=False)
            except Exception:
                pass
        print(f"     [{i}] {name} args={args}")


def print_messages(messages: List[BaseMessage], since: int = 0):
    """增量打印从 since 位置之后的新消息。"""
    new_msgs = messages[since:]
    for m in new_msgs:
        if isinstance(m, SystemMessage):
            print(f"[System] {m.content}")
        elif isinstance(m, HumanMessage):
            print(f"[User] {m.content}")
        elif isinstance(m, AIMessage):
            # 可能是中间（带 tool_calls）或最终回答
            if getattr(m, "tool_calls", None):
                print("[AI(plan)] (触发工具调用，内容可能为空或简要)")
                if m.content:
                    print(f"  说明: {m.content}")
                print_ai_tool_calls(m)
            else:
                print(f"[AI] {m.content}")
        elif isinstance(m, ToolMessage):
            print("[Tool Result]")
            pretty = format_tool_message_content(m.content)
            print(pretty)
        else:
            # 兜底
            type_name = getattr(m, "type", m.__class__.__name__)
            print(f"[{type_name}] {getattr(m, 'content', str(m))}")


def main():
    """
    交互式连续对话：
    - 展示每轮：用户输入 -> (AI 规划+tool_calls) -> 工具结果 -> AI 最终回答
    - 通过 thread_id 维持上下文
    """
    print("欢迎使用文件助手聊天机器人！输入 'exit' 或 'quit' 退出。")

    agent = build_fs_agent()  # 若需要调试细节可在内部加 verbose
    config = {"configurable": {"thread_id": "chat_session"}}

    prev_len = 0  # 已打印消息数量

    while True:
        try:
            user_input = input("\n你: ").strip()
            if user_input.lower() in ("exit", "quit"):
                print("再见！")
                break
            if not user_input:
                continue

            start = time.time()
            response = agent.invoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config=config,
            )
            cost = time.time() - start

            # 打印增量消息
            msgs = response.get("messages", [])
            print_messages(msgs, since=prev_len)
            prev_len = len(msgs)

            print(f"(本轮耗时 {cost:.2f}s，总消息数 {prev_len})")

        except RateLimitError as e:
            print(f"[RateLimit] {e}，等待 5s 重试...")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n用户中断，再见！")
            break
        except Exception as e:
            print(f"[Error] {e}")


if __name__ == "__main__":
    main()
