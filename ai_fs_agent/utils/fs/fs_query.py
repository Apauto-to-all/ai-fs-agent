import logging
import traceback

logger = logging.getLogger(__name__)
from pathlib import Path
from typing import Optional, Dict, Any, Literal
from ai_fs_agent.utils.path_safety import (
    ensure_in_workspace,
    rel_to_workspace,
    is_path_excluded,
)
from ai_fs_agent.utils.file_info import stat_entry


class FsQueryOperator:
    """只读查询：list/search/stat/read"""

    def _one(
        self,
        op: Optional[Literal["list", "search", "stat", "read"]],
        path: str = ".",
        pattern: Optional[str] = None,
        max_items: int = 500,
        max_bytes: int = 2 * 1024,
        encoding: str = "utf-8",
    ) -> Dict[str, Any]:
        try:
            if op not in {"list", "search", "stat", "read"}:
                return {"ok": False, "op": op, "error": f"不支持的操作: {op}"}

            base = ensure_in_workspace(Path(path))

            # 禁止访问 排除列表 中的路径
            if is_path_excluded(base):
                return {"ok": False, "op": op, "error": "禁止AI访问该文件或目录"}

            if op == "list":
                if not base.exists():
                    return {"ok": False, "op": op, "error": f"不存在: {path}"}
                if not base.is_dir():
                    return {"ok": False, "op": op, "error": f"非目录: {path}"}
                items_ = list(base.glob(pattern)) if pattern else list(base.iterdir())
                # 排除 排除列表 中的路径
                items_ = [p for p in items_ if not is_path_excluded(p)]
                items_ = items_[: max(0, max_items)]
                return {"ok": True, "op": op, "data": [stat_entry(p) for p in items_]}

            if op == "search":
                if not base.exists():
                    return {"ok": False, "op": op, "error": f"不存在: {path}"}
                if not pattern:
                    return {"ok": False, "op": op, "error": "search 需要提供 pattern"}
                results = []
                for p in base.glob(pattern):
                    # 跳过 排除列表 中的路径
                    if is_path_excluded(p):
                        continue
                    try:
                        results.append(stat_entry(p))
                    except Exception:
                        continue
                    if len(results) >= max(0, max_items):
                        break
                return {"ok": True, "op": op, "data": results}

            if op == "stat":
                if not base.exists():
                    return {"ok": False, "op": op, "error": f"不存在: {path}"}
                return {"ok": True, "op": op, "data": stat_entry(base)}

            if op == "read":
                if not base.exists():
                    return {"ok": False, "op": op, "error": f"不存在: {path}"}
                if base.is_dir():
                    return {"ok": False, "op": op, "error": f"非文件: {path}"}
                size = base.stat().st_size
                with base.open("rb") as f:
                    data = f.read(max_bytes)
                text = data.decode(encoding, errors="replace")
                return {
                    "ok": True,
                    "op": op,
                    "data": {
                        "path": rel_to_workspace(base),
                        "size": size,
                        "truncated": (
                            f"内容被截断，取前{len(data)}字节，如果用户要求读取更多，请调整 max_bytes"
                            if size > len(data)
                            else "内容完整，未被截断"
                        ),
                        "content": text,
                    },
                }

            return {"ok": False, "op": op, "error": f"未知操作: {op}"}
        except (ValueError, TypeError) as e:
            return {"ok": False, "op": op, "error": str(e)}
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error(f"fs_query 执行失败: {e}")
            return {"ok": False, "op": op, "error": "子项执行失败"}

    def run(
        self,
        op: Optional[Literal["list", "search", "stat", "read"]],
        path: str = ".",
        pattern: Optional[str] = None,
        max_items: int = 200,
        max_bytes: int = 2 * 1024,
    ) -> Dict[str, Any]:
        encoding: str = "utf-8"
        try:
            if op is None:
                return {"ok": False, "error": "缺少操作类型 op"}
            return self._one(
                op=op,
                path=path,
                pattern=pattern,
                max_items=max_items,
                max_bytes=max_bytes,
                encoding=encoding,
            )
        except (ValueError, TypeError) as e:
            return {"ok": False, "op": op, "error": str(e)}
        except Exception:
            logger.error(traceback.format_exc())
            return {"ok": False, "op": op, "error": "fs_query 执行失败"}


_fs_query_operator = FsQueryOperator()
