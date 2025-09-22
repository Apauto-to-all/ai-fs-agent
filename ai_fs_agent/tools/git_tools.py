import logging
import traceback

logger = logging.getLogger(__name__)

from typing import Any, Dict, List
import json
from langchain.tools import tool
from ai_fs_agent.utils.git import _git_repo, _git_history
from ai_fs_agent.utils.git.git_utils import summarize_commit
from ai_fs_agent.config import user_config


@tool("git_recent_commits")
def git_recent_commits(limit: int = 5) -> Dict[str, Any]:
    """
    查询最近的提交信息
    - 参数：
      - limit: 返回数量，默认为 5，最小 1，最大 20
    - 返回：
      - { ok, commits?: [...], error?: str }
    """
    try:
        if not user_config.use_git:
            return {"ok": False, "error": "Git 功能被禁用"}

        # 约束 limit 在 [1, 20]
        try:
            limit = int(limit)
        except Exception:
            limit = 5
        if limit < 1:
            limit = 1
        if limit > 20:
            limit = 20

        commits = _git_history.recent_commits(limit=limit)
        return {"ok": True, "commits": [summarize_commit(c) for c in commits]}
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"ok": False, "error": "获取提交历史失败，工具调用失败"}


@tool("git_rollback")
def git_rollback(commit: str, clean_untracked: bool = False) -> Dict[str, Any]:
    """
    回退到指定提交
    - 参数：
      - commit: 提交引用（完整/短哈希，或相对引用如 HEAD~N、HEAD^）
      - clean_untracked: 是否执行 git clean -fd，默认 False
    - 返回：
      - { ok, message?, error? }
    """
    try:
        if not user_config.use_git:
            return {"ok": False, "error": "Git 功能被禁用"}

        commit = commit.strip()
        if not isinstance(commit, str) or not commit:
            return {
                "ok": False,
                "error": "commit 必须为非空字符串（提交哈希/短哈希/HEAD~N 等）",
            }

        # 人物干预
        max_attempts = 5
        details = summarize_commit(_git_history.commit_details(commit))
        print("即将回退到以下提交：")
        print(json.dumps(details, ensure_ascii=False, indent=2))

        for i in range(max_attempts):
            confirm = input("请输入 (y/n)：").strip()
            if confirm.lower() == "y":
                # 用户确认，执行回退操作
                head = _git_repo.rollback_to(
                    commit, clean_untracked=bool(clean_untracked)
                )
                return {"ok": True, "message": f"已回退，head：{head}"}
            elif confirm.lower() == "n":
                return {"ok": False, "message": "用户已取消回退操作"}
            else:
                print("输入无效，请输入 y 或 n。")
                continue

        # 循环结束但未成功
        return {
            "ok": False,
            "error": f"用户输错 {max_attempts} 次，已取消操作，提醒用户正常输入",
        }
    except Exception as e:
        logger.error(traceback.format_exc())
        return {"ok": False, "error": "获取提交历史失败，工具调用失败"}


# 仅导出这两个工具
git_tools_list = [git_recent_commits, git_rollback]
