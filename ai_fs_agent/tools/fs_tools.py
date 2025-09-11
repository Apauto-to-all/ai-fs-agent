import logging
import traceback

logger = logging.getLogger(__name__)

from pathlib import Path
from typing import Optional, List, Dict, Any
import shutil
from langchain.tools import tool
from ai_fs_agent.config import user_config

FS_ROOT = user_config.workspace_dir


def _root_path_check():
    root_raw = FS_ROOT
    # 配置检查
    if root_raw is None:
        raise ValueError("工作区根目录未配置")
    if isinstance(root_raw, Path):
        root = root_raw
    elif isinstance(root_raw, str):
        root = Path(root_raw)
    else:
        raise TypeError(f"工作区根目录类型不支持: {type(root_raw).__name__}")

    # 路径合法性检查
    if not root.is_absolute():
        raise ValueError("工作区根目录必须是绝对路径")
    if not root.exists():
        raise ValueError(f"工作区根目录不存在")
    if root.is_file():
        raise ValueError(f"工作区根目录不是文件夹")


def _ensure_in_root(p: Path) -> Path:
    _root_path_check()  # 确保 FS_ROOT 已正确配置
    p = (FS_ROOT / p).resolve() if not p.is_absolute() else p.resolve()
    if FS_ROOT not in p.parents and p != FS_ROOT:
        raise ValueError(f"路径越界: {p}，请使用相对路径")
    return p


def _format_size(size_bytes: int) -> str:
    """将字节大小转换为人类可读的单位（B, KB, MB, GB, TB）。"""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    return f"{size:.2f} {units[unit_index]}"


def _stat_entry(p: Path) -> Dict[str, Any]:
    st = p.stat()
    return {
        "path": str(p.relative_to(FS_ROOT)),
        "type": "dir" if p.is_dir() else "file",
        "size": _format_size(st.st_size),
    }


@tool("list_dir")
def list_dir(
    path: str = ".", pattern: Optional[str] = None, max_items: int = 200
) -> Dict[str, Any]:
    """列出指定目录的内容，支持可选的 glob 模式过滤。
    注意：路径必须在工作区根目录内，使用相对路径如 '.'（当前目录）或 'subfolder'。
    避免使用绝对路径（如 'C:\\'）或系统根 '/'
    示例：path='.' 列出根目录；path='subfolder' 列出子目录。
    """
    try:
        base = _ensure_in_root(Path(path))
        if not base.exists():
            return {"ok": False, "error": f"不存在: {path}"}
        if not base.is_dir():
            return {"ok": False, "error": f"非目录: {path}"}
        items = list(base.glob(pattern)) if pattern else list(base.iterdir())
        items = items[:max_items]
        return {"ok": True, "items": [_stat_entry(p) for p in items]}
    except (ValueError, TypeError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"读取目录失败: {e}")
        return {"ok": False, "error": "读取目录失败"}


@tool("read_file")
def read_file(
    path: str, max_bytes: int = 2 * 1024 * 1024, encoding: str = "utf-8"
) -> Dict[str, Any]:
    """读取文本文件，默认最多读取 2MB，超过则截断。
    注意：路径必须在工作区根目录内，使用相对路径如 'file.txt' 或 'subfolder/file.txt'。
    示例：path='script.py' 读取根目录下的文件。
    """
    try:
        p = _ensure_in_root(Path(path))
        if not p.exists():
            return {"ok": False, "error": f"不存在: {path}"}
        if p.is_dir():
            return {"ok": False, "error": f"非文件: {path}"}
        size = p.stat().st_size
        with p.open("rb") as f:
            data = f.read(max_bytes)
        text = data.decode(encoding, errors="replace")
        root = Path(FS_ROOT).expanduser().resolve()
        return {
            "ok": True,
            "path": str(p.relative_to(root)),
            "size": size,
            "truncated": size > len(data),
            "content": text,
        }
    except (ValueError, TypeError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"读取文件失败: {e}")
        return {"ok": False, "error": "读取文件失败"}


@tool("write_file")
def write_file(
    path: str, content: str, overwrite: bool = False, encoding: str = "utf-8"
) -> Dict[str, Any]:
    """写入文本文件，默认不覆盖已存在文件。
    注意：使用相对路径如 'newfile.txt' 或 'subfolder/newfile.txt'。父目录会自动创建。
    示例：path='notes.txt' 在根目录创建文件；path='docs/todo.txt', overwrite=True 在子目录创建文件，覆盖同名文件。
    """
    try:
        p = _ensure_in_root(Path(path))
        if p.exists() and not overwrite:
            return {
                "ok": False,
                "error": f"目标已存在: {path}（设置 overwrite=True 覆盖）",
            }
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding=encoding, newline="") as f:
            f.write(content)
        root = Path(FS_ROOT).expanduser().resolve()
        return {"ok": True, "path": str(p.relative_to(root))}
    except (ValueError, TypeError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"写入文件失败: {e}")
        return {"ok": False, "error": "写入文件失败"}


@tool("move_path")
def move_path(src: str, dst: str, overwrite: bool = False) -> Dict[str, Any]:
    """移动或重命名文件/目录，支持覆盖选项。
    示例：src='old.txt', dst='new.txt' 重命名文件。
    """
    try:
        s, d = _ensure_in_root(Path(src)), _ensure_in_root(Path(dst))
        if not s.exists():
            return {"ok": False, "error": f"源不存在: {src}"}
        if d.exists():
            if not overwrite:
                return {
                    "ok": False,
                    "error": f"目标已存在: {dst}（设置 overwrite=True 覆盖）",
                }
            shutil.rmtree(d) if d.is_dir() else d.unlink()
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(s), str(d))
        return {
            "ok": True,
            "moved": {
                "from": str(s.relative_to(FS_ROOT)),
                "to": str(d.relative_to(FS_ROOT)),
            },
        }
    except (ValueError, TypeError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"移动路径失败: {e}")
        return {"ok": False, "error": "移动路径失败"}


@tool("copy_path")
def copy_path(src: str, dst: str, overwrite: bool = False) -> Dict[str, Any]:
    """复制文件或目录，支持覆盖。
    示例：src='file.txt', dst='backup/file.txt' 复制文件。
    """
    try:
        s, d = _ensure_in_root(Path(src)), _ensure_in_root(Path(dst))
        if not s.exists():
            return {"ok": False, "error": f"源不存在: {src}"}
        if d.exists():
            if not overwrite:
                return {
                    "ok": False,
                    "error": f"目标已存在: {dst}（设置 overwrite=True 覆盖）",
                }
            shutil.rmtree(d) if d.is_dir() else d.unlink()
        d.parent.mkdir(parents=True, exist_ok=True)
        if s.is_dir():
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)
        root = Path(FS_ROOT).expanduser().resolve()
        return {
            "ok": True,
            "copied": {
                "from": str(s.relative_to(root)),
                "to": str(d.relative_to(root)),
            },
        }
    except (ValueError, TypeError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"复制失败: {e}")
        return {"ok": False, "error": "复制失败"}


@tool("make_dir")
def make_dir(path: str, exist_ok: bool = True) -> Dict[str, Any]:
    """创建目录（递归）。
    注意：路径必须在工作区根目录内，使用相对路径如 'newdir' 或 'parent/newdir'。
    示例：path='logs' 在根目录创建目录。
    """
    try:
        p = _ensure_in_root(Path(path))
        p.mkdir(parents=True, exist_ok=exist_ok)
        root = Path(FS_ROOT).expanduser().resolve()
        return {"ok": True, "path": str(p.relative_to(root))}
    except FileExistsError:
        return {"ok": False, "error": f"目录已存在: {path}"}
    except (ValueError, TypeError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"创建目录失败: {e}")
        return {"ok": False, "error": "创建目录失败"}


@tool("delete_path")
def delete_path(path: str, recursive: bool = False) -> Dict[str, Any]:
    """删除文件或目录；目录默认要求为空，recursive=True 递归删除。
    避免绝对路径，否则会因越界而失败。删除操作不可逆，请谨慎。
    示例：path='temp.txt' 删除文件；path='tempdir', recursive=True 删除目录。
    """
    try:
        p = _ensure_in_root(Path(path))
        if not p.exists():
            return {"ok": False, "error": f"不存在: {path}"}
        if p.is_dir():
            if recursive:
                shutil.rmtree(p)
            else:
                try:
                    p.rmdir()
                except OSError:
                    return {
                        "ok": False,
                        "error": f"目录非空: {path}（设置 recursive=True 递归删除）",
                    }
        else:
            p.unlink()
        return {"ok": True}
    except (ValueError, TypeError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"删除失败: {e}")
        return {"ok": False, "error": "删除失败"}


@tool("search_glob")
def search_glob(
    path: str = ".", pattern: str = "**/*", max_items: int = 500
) -> Dict[str, Any]:
    """使用 glob 模式搜索文件/目录。
    注意：起始路径必须在工作区根目录内，使用相对路径如 '.' 或 'subfolder'。
    示例：path='.', pattern='*.py' 搜索根目录下的 Python 文件。
    """
    try:
        base = _ensure_in_root(Path(path))
        if not base.exists():
            return {"ok": False, "error": f"不存在: {path}"}
        results: List[Dict[str, Any]] = []
        for p in base.glob(pattern):
            try:
                results.append(_stat_entry(p))
            except Exception:
                continue
            if len(results) >= max_items:
                break
        return {"ok": True, "items": results}
    except (ValueError, TypeError) as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        logger.error(traceback.format_exc())
        logger.error(f"搜索失败: {e}")
        return {"ok": False, "error": "搜索失败"}


fs_tools_list = [
    list_dir,
    read_file,
    write_file,
    move_path,
    copy_path,
    make_dir,
    delete_path,
    search_glob,
]
