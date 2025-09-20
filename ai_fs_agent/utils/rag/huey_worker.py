import subprocess

# 全局变量：跟踪消费者进程
_consumer_process = None


def start_huey_consumer_via_command():
    """启动 Huey 消费者（通过命令行，指定当前环境，在新终端中）"""
    global _consumer_process
    if _consumer_process is None or _consumer_process.poll() is not None:
        try:
            cmd = [
                "huey_consumer",  # 使用模块方式运行 huey_consumer
                "ai_fs_agent.utils.rag.rag_tasks.huey",
            ]
            _consumer_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            print("Huey 消费者已在后台运行，如果需要关闭，请手动终止进程或关闭终端")
        except Exception as e:
            print(f"启动消费者失败: {e}")
    else:
        print("Huey 消费者已在运行，无需重新启动")
