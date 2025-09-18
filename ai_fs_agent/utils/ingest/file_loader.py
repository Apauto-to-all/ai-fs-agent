import logging
from pathlib import Path
from ai_fs_agent.utils.path_safety import ensure_in_workspace, is_path_excluded

logger = logging.getLogger(__name__)


class FileLoader:
    """
    通用文件加载器：
    - 纯文本：.txt .md .csv .json .yaml/.yml .toml ...
    - Office 文档：.docx .xlsx .pptx
    - 其他格式：后续可扩展

    不支持或未安装依赖时，会抛出友好异常。
    """

    TEXT_EXTS = {
        ".txt",
        ".md",
        ".csv",
        ".tsv",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
    }
    OFFICE_EXTS = {".docx", ".xlsx", ".pptx"}

    def load_text(self, path: str) -> str:
        """
        根据扩展名自动选择解析器，返回utf-8字符串（尽量保留原格式换行）。
        传入路径可为相对路径，会自动转换为工作区内的绝对路径。
        """
        # 路径安全检查：确保在工作区内，且不被排除
        p = Path(path)
        abs_p = ensure_in_workspace(p)
        if is_path_excluded(abs_p):
            raise ValueError(f"路径被排除: {path} (位于排除目录下)")

        ext = abs_p.suffix.lower()
        if ext in self.TEXT_EXTS:
            return self._read_text_file(abs_p)
        if ext in self.OFFICE_EXTS:
            return self._read_office_file(abs_p)
        raise ValueError(f"暂不支持的文件类型: {ext} ({path})")

    # ---------- 各类型具体读取 ----------

    def _read_text_file(self, path: Path) -> str:
        """读取纯文本文件，返回字符串"""
        # 多编码回退策略，尽量读出文本
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            raise Exception(f"读取文本文件失败: {path}: {e}")

    def _read_office_file(self, path: Path) -> str:
        """读取 Office 文档，返回 Markdown 格式内容"""
        from markitdown import MarkItDown

        md = MarkItDown()
        result = md.convert(path)
        return result.text_content
