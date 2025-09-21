import logging
import base64
from pathlib import Path
from ai_fs_agent.utils.path_safety import (
    ensure_in_workspace,
    is_path_excluded,
    rel_to_workspace,
)
from langchain_community.document_loaders import TextLoader
from ai_fs_agent.utils.ingest.file_content_model import FileContentModel

logger = logging.getLogger(__name__)


class FileLoader:
    """
    通用文件加载器：
    - 纯文本：.txt .md .csv .json .yaml/.yml .toml ...
    - Office 文档：.docx .xlsx .pptx
    - 图片：.jpg .jpeg .png .gif .bmp .tiff (转换为base64编码)
    - 其他格式：后续可扩展

    不支持或未安装依赖时，会抛出友好异常。
    """

    TEXT_EXTS = {".txt", ".md", ".csv", ".tsv", ".json", ".yaml", ".yml", ".toml"}
    OFFICE_EXTS = {".docx", ".xlsx", ".pptx"}
    IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg"}

    def load_file(self, path: str) -> FileContentModel:
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
        if ext in self.IMAGE_EXTS:
            return self._read_image_file(abs_p)
        raise ValueError(f"暂不支持的文件类型: {ext} ({path})")

    # ---------- 各类型具体读取 ----------

    def _read_text_file(self, path: Path) -> FileContentModel:
        """读取纯文本文件，返回 FileContentModel 对象"""
        # 多编码回退策略，尽量读出文本
        try:
            documents = TextLoader(file_path=path, encoding="utf-8").load()
            content = documents[0].page_content if documents else ""
            return FileContentModel(
                file_path=rel_to_workspace(path), file_type="text", content=content
            )
        except Exception as e:
            raise Exception(f"读取文本文件失败: {path}: {e}")

    def _read_office_file(self, path: Path) -> FileContentModel:
        """读取 Office 文档，返回 Markdown 格式内容，封装为 FileContentModel 对象"""
        from markitdown import MarkItDown

        md = MarkItDown()
        result = md.convert(path)
        return FileContentModel(
            file_path=rel_to_workspace(path),
            file_type="text",
            content=result.text_content,
        )

    def _read_image_file(self, path: Path) -> FileContentModel:
        """读取图片文件，转换为base64编码，封装为 FileContentModel 对象"""
        try:
            # 读取图片文件并转换为base64
            with open(path, "rb") as image_file:
                image_data = image_file.read()
                base64_encoded = base64.b64encode(image_data).decode("utf-8")
            # 根据文件扩展名确定MIME类型
            ext = path.suffix.lower()
            mime_types = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".bmp": "image/bmp",
                ".tiff": "image/tiff",
                ".webp": "image/webp",
                ".svg": "image/svg+xml",
            }
            mime_type = mime_types.get(ext, "image/jpeg")  # 默认为jpeg

            # 创建data URL格式的base64字符串
            data_url = f"data:{mime_type};base64,{base64_encoded}"

            return FileContentModel(
                file_path=rel_to_workspace(path),
                file_type="image",
                content="",  # 对于图片文件，content 为空
                image_base64=data_url,
            )

        except Exception as e:
            logger.error(f"图片base64编码失败 {path}: {e}")
            raise Exception(f"读取图片文件失败: {path}: {e}")
