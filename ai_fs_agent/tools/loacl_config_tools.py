from pathlib import Path
from typing import Dict, Any, Optional

from langchain.tools import tool
from ai_fs_agent.config import user_config  # 直接引用用户配置（自动持久化）


def _validate_dir(p: Path) -> Optional[str]:
    if not p.is_absolute():
        return "工作区目录必须是绝对路径"
    if not p.exists():
        return "工作区目录不存在"
    if not p.is_dir():
        return "工作区目录应为文件夹"
    return None


@tool("check_workspace_dir")
def check_workspace_dir() -> Dict[str, Any]:
    """检查当前设置的工作区目录是否正常。"""
    try:
        if user_config.workspace_dir is None:
            return {"ok": False, "error": "工作区目录未设置"}

        err = _validate_dir(user_config.workspace_dir)
        if err:
            return {"ok": False, "error": err}

        return {"ok": True, "message": "工作区目录正常"}
    except Exception as e:
        return {"ok": False, "error": "检测失败"}


@tool("set_workspace_dir")
def set_workspace_dir() -> Dict[str, Any]:
    """设置项目的工作区（交互式），引导用户输入工作区目录"""
    try:
        while True:
            path = input("请输入工作区根目录的绝对路径（按下 Ctrl+C 取消）：").strip()
            if not path:
                print("路径不能为空，请重新输入。")
                continue
            candidate = Path(path).expanduser().resolve()
            err = _validate_dir(candidate)
            if err:
                print(f"无效路径: {err} 请重新输入。")
                continue
            break

        # 运行期赋值：UserConfig.__setattr__ 会自动写入 USER_CONFIG_PATH
        user_config.workspace_dir = candidate

        return {"ok": True, "m": "工作区目录已设置"}
    except KeyboardInterrupt:
        return {"ok": False, "error": "用户取消输入"}
    except Exception as e:
        return {"ok": False, "error": "设置失败，提醒用户输入正常路径"}


# 便于代理批量注册
config_tools_list = [set_workspace_dir, check_workspace_dir]
