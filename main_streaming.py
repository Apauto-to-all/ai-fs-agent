import json
import time
from openai import RateLimitError
from langchain_core.messages import AIMessageChunk, ToolMessage
from ai_fs_agent.agents import build_supervisor_agent


def format_tool_message_content(content: str) -> str:
    """尝试把工具返回的 JSON 美化；不是 JSON 则原样返回。"""
    try:
        data = json.loads(content)
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        return content


def main():
    """
    交互式连续对话（流式输出）：
    - 每轮：用户输入 -> (AI 规划+tool_calls，流式) -> 工具结果 -> AI 最终回答（流式）
    - 通过 thread_id 维持上下文
    """
    print("欢迎使用文件助手（流式）！输入 'exit' 或 'quit' 退出。")

    agent = build_supervisor_agent()
    config = {"configurable": {"thread_id": "1"}}

    while True:
        try:
            user_input = input("\n你: ").strip()
            if user_input.lower() in ("exit", "quit"):
                print("再见！")
                break
            if not user_input:
                continue

            is_use_tool = False
            is_ai_output = False
            start = time.time()

            for token, _ in agent.stream(
                {"messages": [{"role": "user", "content": user_input}]},
                stream_mode="messages",
                config=config,
            ):
                if isinstance(token, AIMessageChunk):
                    if not token.content:
                        # 空内容，表示AI已经回答完毕
                        if is_ai_output:
                            print("\n=== AI回答完成 ===")
                            is_ai_output = False

                    # 规划阶段：工具调用参数流式输出
                    tool_call_chunks = token.tool_call_chunks
                    if tool_call_chunks:
                        if not is_use_tool:
                            print("\n=== 触发工具调用 ===")
                            is_use_tool = True
                        if tool_call_chunks[-1].get("name"):
                            print(
                                f"工具名: {tool_call_chunks[-1]['name']}\n调用参数: ",
                                end="",
                                flush=True,
                            )
                        print(tool_call_chunks[-1].get("args", ""), end="", flush=True)

                    # 工具调用完成（本次规划结束）
                    elif token.response_metadata.get("finish_reason") == "tool_calls":
                        is_use_tool = False
                        print("\n=== 工具调用完成 ===")

                    # 最终回答内容流式输出
                    elif token.content:
                        if not is_ai_output:
                            print("\n=== AI 回答 ===")
                            is_ai_output = True
                        print(token.content.strip(), end="", flush=True)

                    # 本轮最终回答结束
                    elif token.response_metadata.get("finish_reason") == "stop":
                        print("\n=== 本轮对话结束 ===\n")

                    else:
                        print(f"\n[未知 AIMessageChunk] {token}\n")

                elif isinstance(token, ToolMessage):
                    # 工具执行结果
                    tool_name = token.name
                    tool_output = token.content
                    print(f"\n=== 工具 {tool_name} 调用结果 ===")
                    print(format_tool_message_content(tool_output))
                    print("=== 工具结果输出完成 ===")

            cost = time.time() - start
            print(f"(本轮耗时 {cost:.2f}s)")

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
