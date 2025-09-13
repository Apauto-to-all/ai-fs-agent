from pathlib import Path
from typing import Dict, Any, Optional

from langchain.tools import tool
from ai_fs_agent.config import user_config  # 直接引用用户配置（自动持久化）
from ai_fs_agent.utils.check_workspace_dir import _check_workspace_dir


@tool("check_workspace_dir")
def check_workspace_dir() -> Dict[str, Any]:
    """检查当前设置的工作区目录是否正常。"""
    try:
        err = _check_workspace_dir(user_config.workspace_dir)
        if err:
            return {"ok": False, "error": err}

        return {"ok": True, "message": "工作区目录正常"}
    except Exception as e:
        return {"ok": False, "error": "工具报错，检测失败"}


@tool("set_workspace_dir")
def set_workspace_dir() -> Dict[str, Any]:
    """设置项目的工作区（交互式），引导用户输入工作区目录"""
    try:
        max_attempts = 5
        for i in range(max_attempts):
            path = input("请输入工作区目录的绝对路径：").strip()
            if not path:
                print("路径不能为空，请重新输入。")
                continue
            err = _check_workspace_dir(path)
            if err:
                print(f"无效路径: {err} 请重新输入。")
                continue

            # 成功，设置并返回
            user_config.workspace_dir = path
            return {"ok": True, "message": "工作区目录已设置"}

        # 循环结束但未成功
        return {
            "ok": False,
            "error": f"用户输错 {max_attempts} 次，提醒用户输入正常路径",
        }
    except KeyboardInterrupt:
        return {"ok": False, "error": "用户取消输入"}
    except Exception as e:
        return {"ok": False, "error": "工具报错，设置失败，提醒用户输入正常路径"}


# 便于代理批量注册
config_tools_list = [set_workspace_dir, check_workspace_dir]
