import logging
import traceback

logger = logging.getLogger(__name__)

from typing import Optional, List, Dict, Any, Literal
from langchain.tools import tool
from ai_fs_agent.utils.fs.fs_query import _fs_query_operator
from ai_fs_agent.utils.fs.fs_apply import _fs_apply_operator


@tool("fs_query")
def _fs_query(
    op: Literal["list", "search", "read", "stat"],
    items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    文件系统只读查询：list/search/stat/read
    - 作用域：仅工作目录内（仅允许相对路径，不允许越界到工作目录外）
    - 返回：{ ok, results, errors }

    参数：
    - op: 'list'|'search'|'stat'|'read'（必填）
    - items: 操作参数列表，支持以下参数：
        - path: 目标路径，仅支持相对路径（默认 '.'，list/search/stat/read 使用）
        - pattern: 过滤模式，使用glob模式，比如`*.py`（仅 list/search 使用）
        - max_items: 最大返回项数（默认 200，list/search 使用）
        - max_bytes: 最大读取字节数（默认 2KB，read 使用）

    glob模式语法说明，理解用户的要求，合理使用：
    - `*`：匹配任意数量字符（不含路径分隔符）
    - `?`：匹配单个字符
    - `[seq]`：匹配序列中的任一字符（如 [abc] 匹配 a/b/c）
    - `**`：递归匹配子目录（用于跨目录搜索）
    - 示例：`*.txt`（当前目录 .txt 文件）、`**/*.txt`（所有子目录 .txt 文件）、`**/*.{txt,md,py}`（多种扩展名）、`src/**/*.py`（src 下所有 .py 文件）

    模式：
    - list: 列出 path 目录下的文件或文件夹信息（非递归），可配 pattern 过滤
    - search: 在 path 下，搜索匹配的文件/目录，需提供 pattern，递归搜索需要在 pattern 里用 `**` 表示
    - read: 读取 path 指定的文本内容（按 UTF-8 尝试解码；超限截断）
    - stat: 查看 path 指定的文件/目录属性（大小、类型、mtime 等）

    示例
    单个操作：items=[{...}]；多个操作：items=[{...}, {...}, ...]
    - 列目录：{ op:"list", items:[{path:"."}] }
    - 读文件：{ op:"read", items:[{path:"docs/readme.md", max_bytes:1000}, {path:"docs/another.md", max_bytes:1000}, {...}] }
    - 查文件：{ op:"search", items:[{path:".", pattern:"*.py", max_items:100}] }
    - 看属性：{ op:"stat", items:[{path:"src"}, {path:"data/input.csv"}, {...}] }
    - 递归搜索：{ op:"search", items:[{path:"文档", pattern:"**/*.txt", max_items:200}] }
    """
    DEFAULT_PATH = "."
    DEFAULT_MAX_ITEMS = 200
    DEFAULT_MAX_BYTES = 2 * 1024

    try:
        if not isinstance(items, list):
            return {
                "ok": False,
                "results": [],
                "errors": [{"error": "items 必须为对象数组"}],
            }
        if len(items) == 0:
            return {
                "ok": False,
                "results": [],
                "errors": [{"error": "items 不能为空"}],
            }

        results: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        for idx, it in enumerate(items):
            if not isinstance(it, dict):
                errors.append(
                    {"index": idx, "ok": False, "op": op, "error": "item 必须为对象"}
                )
                continue

            ipath = it.get("path", DEFAULT_PATH)
            ipattern = it.get("pattern")
            imax_items = it.get("max_items", DEFAULT_MAX_ITEMS)
            imax_bytes = it.get("max_bytes", DEFAULT_MAX_BYTES)

            # 基础校验
            err: Optional[str] = None
            if op == "search":
                if not ipath:
                    err = "search 需要 path"
                elif not ipattern:
                    err = "search 需要 pattern"
            elif op in ("stat", "read"):
                if not ipath:
                    err = f"{op} 需要 path"

            if err:
                errors.append({"index": idx, "ok": False, "op": op, "error": err})
                continue

            r = _fs_query_operator.run(op, ipath, ipattern, imax_items, imax_bytes)
            entry = {"index": idx, **r}
            (results if r.get("ok") else errors).append(entry)

        return {
            "ok": len(errors) == 0,
            "results": results,
            "errors": errors,
        }
    except Exception:
        logger.error(traceback.format_exc())
        return {
            "ok": False,
            "results": [],
            "errors": [{"error": "fs_query 工具执行失败"}],
        }


@tool("fs_apply")
def _fs_apply(
    op: Optional[Literal["write", "mkdir", "move", "copy", "delete"]],
    items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    文件系统变更：write/mkdir/move/copy/delete
    - 作用域：仅工作目录内（仅允许相对路径，不允许越界到工作目录外）
    - 返回：{ ok, results, errors }

    参数：
    - op: 'write'|'mkdir'|'move'|'copy'|'delete'（必填）
    - items: 操作参数列表，支持以下参数：
        - path: 目标路径，仅支持相对路径（默认 '.'，write/mkdir/delete 使用）
        - content: 写入内容（write 使用）
        - src/dst: 源/目标路径（move/copy 使用）
        - recursive: 是否递归删除（默认 false，delete 使用）

    模式：
    - write: 将 content 写入到 path；如果目标存在，自动重命名防止覆盖
    - mkdir: 创建目录；自动创建缺失的父级目录
    - move:  将 src 移动到 dst；目标存在自动重命名，防止覆盖
    - copy:  将 src 复制到 dst；目标存在自动重命名，防止覆盖
    - delete: 删除 path；可以删除文件或空目录，递归删除需设 recursive

    示例
    单个操作：items=[{...}]；多个操作：items=[{...}, {...}, ...]
    - 写文件：{ op:"write", items:[{ path:"out/a.txt", content:"hello" }] }
    - 建目录：{ op:"mkdir", items:[{ path:"logs/archive" }] }
    - 移动：  { op:"move",  items:[{ src:"a.txt", dst:"b.txt" }] }
    - 复制：  { op:"copy",  items:[{ src:"src/app.py", dst:"bak/app.py" }] }
    - 删除：  { op:"delete", items:[{ path:"tmp/cache", recursive:false }] }
    - 批量：  { op:"copy",  items:[{ src:"a.txt", dst:"b.txt" }, { src:"README.md", dst:"build/README.md" }] }
    """
    DEFAULT_PATH = "."
    DEFAULT_RECURSIVE = False

    try:
        if not isinstance(items, list):
            return {
                "ok": False,
                "results": [],
                "errors": [{"error": "items 必须为对象数组"}],
            }
        if len(items) == 0:
            return {
                "ok": False,
                "results": [],
                "errors": [{"error": "items 不能为空"}],
            }

        results: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        for idx, it in enumerate(items):
            if not isinstance(it, dict):
                errors.append(
                    {"index": idx, "ok": False, "op": op, "error": "item 必须为对象"}
                )
                continue

            ipath = it.get("path", DEFAULT_PATH)
            icontent = it.get("content", "")
            isrc = it.get("src", None)
            idst = it.get("dst", None)
            irecursive = bool(it.get("recursive", DEFAULT_RECURSIVE))

            r = _fs_apply_operator.run(
                op=op,
                path=ipath,
                content=icontent,
                src=isrc,
                dst=idst,
                recursive=irecursive,
            )
            entry = {"index": idx, **r}
            (results if r.get("ok") else errors).append(entry)

        return {
            "ok": len(errors) == 0,
            "results": results,
            "errors": errors,
        }
    except Exception:
        logger.error(traceback.format_exc())
        return {
            "ok": False,
            "results": [],
            "errors": [{"error": "fs_apply 工具执行失败"}],
        }


# 导出给 Agent 使用
fs_tools_list = [_fs_query, _fs_apply]
