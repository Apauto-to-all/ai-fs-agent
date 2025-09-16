from pathlib import Path
from typing import Dict, Any, Optional

from langchain.tools import tool
from ai_fs_agent.config import user_config  # 直接引用用户配置（自动持久化）
from ai_fs_agent.utils.workspace import check_workspace_dir


@tool("check_workspace")
def check_workspace() -> Dict[str, Any]:
    """检查当前设置的工作目录是否正常"""
    try:
        err = check_workspace_dir(user_config.workspace_dir)
        if err:
            return {"ok": False, "error": err}

        return {"ok": True, "message": "工作目录正常"}
    except Exception as e:
        return {"ok": False, "error": "工具报错，检测失败"}


@tool("set_workspace_dir")
def set_workspace_dir(path: str) -> Dict[str, Any]:
    """设置项目的工作目录。传入绝对路径参数 path。"""
    try:
        err = check_workspace_dir(path)
        if err:
            return {"ok": False, "error": err}

        # 成功，提醒用户进行二次确认
        max_attempts = 5
        for i in range(max_attempts):
            print(
                f"请确认是否将工作目录设置为：{path}？（y or n，其他输入为自定义路径）"
            )
            confirm = input("请输入 (y/n/自定义路径)：").strip()
            if confirm.lower() == "y":
                pass

            elif confirm.lower() == "n":
                return {"ok": False, "message": "用户已取消设置工作目录"}

            elif confirm == "":
                print("输入不能为空，请重新输入。")
                continue

            else:
                err = check_workspace_dir(confirm)
                if err:
                    print(f"错误：{err}，无效路径: {confirm} 请重新输入")
                else:
                    path = confirm
                continue

            user_config.workspace_dir = Path(path.strip()).expanduser()
            return {
                "ok": True,
                "message": "工作目录已设置，最终路径隐藏（保护隐私）",
            }

        # 循环结束但未成功
        return {
            "ok": False,
            "error": f"用户输错 {max_attempts} 次，已取消操作，提醒用户正常输入",
        }
    except Exception:
        return {"ok": False, "error": "工具报错，设置失败"}


@tool("check_git_enabled")
def check_git_enabled() -> Dict[str, Any]:
    """检查是否启用了 Git 管理功能"""
    try:
        return {
            "ok": True,
            "message": "Git 功能已启用" if user_config.use_git else "Git 功能已禁用",
        }
    except Exception:
        return {"ok": False, "error": "工具报错，检测失败"}


@tool("set_git_enabled")
def set_git_enabled(enable: bool) -> Dict[str, Any]:
    """
    开启或关闭 Git 管理功能。
    - 参数：
      - enable: True 开启，False 关闭
    """
    try:
        # 二次确认，避免误操作
        text = "开启" if enable else "关闭"

        max_attempts = 5
        for _ in range(max_attempts):
            print(f"请确认是否{ text } Git 功能？(y/n)")
            confirm = input("请输入 (y/n)：").strip().lower()
            if confirm == "y":
                pass
            elif confirm == "n":
                return {"ok": False, "message": "用户已取消操作"}
            else:
                print("输入无效")

            user_config.use_git = bool(enable)
            extra = (
                "已关闭 Git 功能，提醒用户手动清理，工作目录下的 Git 相关的文件和文件夹，比如 .git/"
                if not enable
                else "已开启 Git 功能。首次执行 Git 相关操作时，将在工作目录内自动初始化独立仓库。"
            )
            return {"ok": True, "message": extra}

        # 循环结束但未成功
        return {
            "ok": False,
            "error": f"用户输错 {max_attempts} 次，已取消操作，提醒用户正常输入",
        }
    except Exception:
        return {"ok": False, "error": "工具报错，设置失败"}


# 便于代理批量注册（追加导出）
config_tools_list = [
    set_workspace_dir,
    check_workspace,
    check_git_enabled,
    set_git_enabled,
]
