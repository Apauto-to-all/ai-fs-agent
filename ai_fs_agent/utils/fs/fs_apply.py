import logging
import traceback

logger = logging.getLogger(__name__)
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Literal
from send2trash import send2trash
from datetime import datetime
from ai_fs_agent.utils.path_safety import (
    ensure_in_workspace,
    rel_to_workspace,
    is_path_excluded,
)
from ai_fs_agent.utils.git.git_repo import _git_repo
from ai_fs_agent.config import user_config


class FsApplyOperator:
    """变更：write/mkdir/move/copy/delete"""

    def _generate_unique_name(self, d: Path) -> Path:
        """生成唯一目标名称，如果目标存在，添加后缀 (1), (2) 等"""
        if not d.exists():
            return d
        stem = d.stem  # 文件名无扩展名
        suffix = d.suffix  # 扩展名
        counter = 1
        new_d = d
        while new_d.exists():
            new_name = f"{stem}({counter}){suffix}"
            new_d = d.parent / new_name
            counter += 1
        return new_d

    def _one(
        self,
        op: Optional[Literal["write", "mkdir", "move", "copy", "delete"]],
        path: Optional[str] = ".",
        content: Optional[str] = "",
        src: Optional[str] = None,
        dst: Optional[str] = None,
        recursive: bool = False,
        encoding: str = "utf-8",
    ) -> Dict[str, Any]:
        try:
            if op not in {"write", "mkdir", "move", "copy", "delete"}:
                return {"op": op, "ok": False, "error": f"不支持的操作: {op}"}

            if op in {"write", "mkdir", "delete"}:
                if not path:
                    return {"op": op, "ok": False, "error": f"{op} 需要提供 path"}
                p = ensure_in_workspace(Path(path))
                # 若目标位于排除列表，禁止更改
                if is_path_excluded(p):
                    return {"op": op, "ok": False, "error": "禁止AI更改该文件或目录"}

            if op in {"move", "copy"}:
                if not src or not dst:
                    return {
                        "op": op,
                        "ok": False,
                        "error": f"{op} 需要提供 src 和 dst",
                    }
                s = ensure_in_workspace(Path(src))
                d = ensure_in_workspace(Path(dst))
                # 源或目标任一位于排除列表时，禁止操作
                if is_path_excluded(s) or is_path_excluded(d):
                    return {"op": op, "ok": False, "error": "禁止AI更改该文件或目录"}

            if op == "write":
                if content is None:
                    return {
                        "op": "write",
                        "ok": False,
                        "error": "write 需要提供 content",
                    }
                # 若目标存在，禁止覆盖，统一重命名
                p = self._generate_unique_name(p)
                p.parent.mkdir(parents=True, exist_ok=True)
                with p.open("w", encoding=encoding, newline="") as f:
                    f.write(content)
                return {"op": "write", "ok": True, "path": rel_to_workspace(p)}

            if op == "mkdir":
                p.mkdir(parents=True, exist_ok=True)
                return {"op": "mkdir", "ok": True, "path": rel_to_workspace(p)}

            if op == "move":
                if not s.exists():
                    return {"op": "move", "ok": False, "error": f"源不存在: {src}"}
                # 禁止覆盖，统一重命名目标
                d = self._generate_unique_name(d)
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(s), str(d))
                return {
                    "op": "move",
                    "ok": True,
                    "from": rel_to_workspace(s),
                    "to": rel_to_workspace(d),
                }

            if op == "copy":
                if not s.exists():
                    return {"op": "copy", "ok": False, "error": f"源不存在: {src}"}
                # 禁止覆盖，统一重命名目标
                d = self._generate_unique_name(d)
                d.parent.mkdir(parents=True, exist_ok=True)
                if s.is_dir():
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
                return {
                    "op": "copy",
                    "ok": True,
                    "from": rel_to_workspace(s),
                    "to": rel_to_workspace(d),
                }

            if op == "delete":
                if not p.exists():
                    return {"op": "delete", "ok": False, "error": f"不存在: {path}"}

                # 保留原有安全语义：非递归时不允许删除“非空目录”
                if p.is_dir() and not recursive:
                    try:
                        next(p.iterdir())  # 有内容则会取到第一个条目
                        return {
                            "op": "delete",
                            "ok": False,
                            "error": f"目录非空: {path}（设置 recursive=True 递归删除至回收站）",
                        }
                    except StopIteration:
                        # 空目录，允许删除
                        pass

                # 统一使用系统回收站删除，目录/文件均支持
                send2trash(str(p))
                return {"op": "delete", "ok": True, "path": rel_to_workspace(p)}

            return {"op": op, "ok": False, "error": f"未知操作: {op}"}

        except (ValueError, TypeError) as e:
            return {"op": op, "ok": False, "error": str(e)}
        except Exception:
            logger.error(traceback.format_exc())
            return {"op": op, "ok": False, "error": "文件操作执行失败"}

    def _format_commit_message(
        self,
        op: str,
        result: Dict[str, Any],
    ) -> str:
        """
        统一的提交信息格式：
        - 写文件:   AI：write path="a/b.txt"
        - 新建目录: AI：mkdir path="a/b"
        - 移动:     AI：move from="a/b.txt" to="c/d.txt"
        - 复制:     AI：copy from="a/b.txt" to="c/d.txt"
        - 删除:     AI：delete path="a/b.txt"
        """
        # 前缀
        prefix = f"AI："
        if op in ("write", "mkdir", "delete"):
            p = result.get("path") or ""
            if op == "write":
                return f"{prefix}写入文件：{p}"
            elif op == "mkdir":
                return f"{prefix}新建目录：{p}"
            elif op == "delete":
                return f"{prefix}删除：{p}"

        if op in ("move", "copy"):
            src = result.get("from") or ""
            dst = result.get("to") or ""
            if op == "move":
                return f"{prefix}移动：{src} -> {dst}"
            elif op == "copy":
                return f"{prefix}复制：{src} -> {dst}"

        return f"{prefix}{op}"

    def run(
        self,
        op: Optional[Literal["write", "mkdir", "move", "copy", "delete"]],
        path: Optional[str] = ".",
        content: Optional[str] = "",
        src: Optional[str] = None,
        dst: Optional[str] = None,
        recursive: bool = False,
        is_use_git: bool = True,
    ) -> Dict[str, Any]:
        encoding: str = "utf-8"
        try:
            if op is None:
                return {"ok": False, "error": "缺少操作类型 op"}

            try:
                if user_config.use_git and is_use_git:
                    # 如果有变化，就提交一次
                    _git_repo.commit_all(
                        message=f"Human：保存变更（{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}）"
                    )
            except Exception as e:
                pass  # 忽略提交失败，继续执行变更

            result = self._one(
                op=op,
                path=path,
                content=content,
                src=src,
                dst=dst,
                recursive=recursive,
                encoding=encoding,
            )

            try:
                # 启用 + 成功  > 进行一次 Git 提交
                if user_config.use_git and result.get("ok", False) and is_use_git:
                    _git_repo.commit_all(
                        message=self._format_commit_message(op, result)
                    )
            except Exception as e:
                pass  # 忽略提交失败

            return result
        except (ValueError, TypeError) as e:
            return {"op": op, "ok": False, "error": str(e)}
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f"fs_apply 执行失败: {e}")
            return {"op": op, "ok": False, "error": "fs_apply 执行失败"}


_fs_apply_operator = FsApplyOperator()
