import logging
import traceback

logger = logging.getLogger(__name__)
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, Literal
from ai_fs_agent.utils.fs.fs_utils import _ensure_in_root, _rel
from send2trash import send2trash


class FsApplyOperator:
    """变更：write/mkdir/move/copy/delete（单次，不支持批量）。"""

    def _one(
        self,
        op: str,
        path: Optional[str],
        content: Optional[str],
        src: Optional[str],
        dst: Optional[str],
        overwrite: bool,
        recursive: bool,
        encoding: str,
    ) -> Dict[str, Any]:
        try:
            if op not in {"write", "mkdir", "move", "copy", "delete"}:
                return {"op": op, "ok": False, "error": f"不支持的操作: {op}"}

            if op in {"write", "mkdir", "delete"}:
                if not path:
                    return {"op": op, "ok": False, "error": f"{op} 需要提供 path"}
                p = _ensure_in_root(Path(path))

            if op in {"move", "copy"}:
                if not src or not dst:
                    return {
                        "op": op,
                        "ok": False,
                        "error": f"{op} 需要提供 src 和 dst",
                    }
                s = _ensure_in_root(Path(src))
                d = _ensure_in_root(Path(dst))

            if op == "write":
                if content is None:
                    return {
                        "op": "write",
                        "ok": False,
                        "error": "write 需要提供 content",
                    }
                if p.exists() and not overwrite:
                    return {
                        "op": "write",
                        "ok": False,
                        "error": f"目标已存在: {path}（设置 overwrite=True 覆盖）",
                    }
                p.parent.mkdir(parents=True, exist_ok=True)
                with p.open("w", encoding=encoding, newline="") as f:
                    f.write(content)
                return {"op": "write", "ok": True, "path": _rel(p)}

            if op == "mkdir":
                p.mkdir(parents=True, exist_ok=True)
                return {"op": "mkdir", "ok": True, "path": _rel(p)}

            if op == "move":
                if not s.exists():
                    return {"op": "move", "ok": False, "error": f"源不存在: {src}"}
                if d.exists():
                    if not overwrite:
                        return {
                            "op": "move",
                            "ok": False,
                            "error": f"目标已存在: {dst}（设置 overwrite=True 覆盖）",
                        }
                    shutil.rmtree(d) if d.is_dir() else d.unlink()
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(s), str(d))
                return {"op": "move", "ok": True, "from": _rel(s), "to": _rel(d)}

            if op == "copy":
                if not s.exists():
                    return {"op": "copy", "ok": False, "error": f"源不存在: {src}"}
                if d.exists():
                    if not overwrite:
                        return {
                            "op": "copy",
                            "ok": False,
                            "error": f"目标已存在: {dst}（设置 overwrite=True 覆盖）",
                        }
                    shutil.rmtree(d) if d.is_dir() else d.unlink()
                d.parent.mkdir(parents=True, exist_ok=True)
                if s.is_dir():
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)
                return {"op": "copy", "ok": True, "from": _rel(s), "to": _rel(d)}

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
                return {"op": "delete", "ok": True, "path": _rel(p)}

            return {"op": op, "ok": False, "error": f"未知操作: {op}"}

        except (ValueError, TypeError) as e:
            return {"op": op, "ok": False, "error": str(e)}
        except Exception:
            logger.error(traceback.format_exc())
            return {"op": op, "ok": False, "error": "子操作执行失败"}

    def run(
        self,
        op: Optional[Literal["write", "mkdir", "move", "copy", "delete"]],
        path: Optional[str],
        content: Optional[str],
        src: Optional[str],
        dst: Optional[str],
        overwrite: bool,
        recursive: bool,
    ) -> Dict[str, Any]:
        encoding: str = "utf-8"
        try:
            if op is None:
                return {"ok": False, "error": "缺少操作类型 op"}
            return self._one(
                op, path, content, src, dst, overwrite, recursive, encoding
            )
        except (ValueError, TypeError) as e:
            return {"op": op, "ok": False, "error": str(e)}
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f"fs_apply 执行失败: {e}")
            return {"op": op, "ok": False, "error": "fs_apply 执行失败"}


_fs_apply_operator = FsApplyOperator()
