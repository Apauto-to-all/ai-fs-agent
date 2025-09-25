import logging
import base64
from pathlib import Path
from ai_fs_agent.utils.path_safety import (
    ensure_in_workspace,
    is_path_excluded,
    rel_to_workspace,
)
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
    IMAGE_EXTS = {
        ".jpg",
        ".jpeg",
        ".jpe",
        ".png",
        ".bmp",
        ".tif",
        ".tiff",
        ".webp",
        ".heic",
    }
    PDF_EXTS = {".pdf"}
    # TODO: 扩展文件类型支持和智能文件夹处理
    # 1. 新增文件类型支持：
    #    - 压缩文件：zip, rar, 7z（提取内容列表和元数据，或联网搜索）
    #    - 可执行文件：exe, dll（读取版本信息和数字签名，或联网搜索）
    #    - 安装包：msi, deb, rpm（解析包信息，或联网搜索）
    # 2. 文件夹智能识别：
    #    - 软件目录：含有exe和dll文件的程序文件夹（联网搜索获取软件描述）
    #    - 项目目录：基于特征文件（package.json, requirements.txt等）识别项目类型
    # TODO: 实现LLM联网搜索功能，使用支持联网搜索的模型
    # - 对于无法直接读取的文件类型（exe、dll、zip等），通过文件名和路径在线搜索获取描述信息
    # - 对于文件夹，分析目录结构和关键文件特征，生成内容摘要
    # - 提供用户手动输入描述的接口作为备选方案
    # - 搜索结果需缓存避免重复请求，提升性能

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
        elif ext in self.OFFICE_EXTS:
            return self._read_office_file(abs_p)
        elif ext in self.IMAGE_EXTS:
            return self._read_image_file(abs_p)
        elif ext in self.PDF_EXTS:
            return self._read_pdf_file(abs_p)

        raise ValueError(f"暂不支持的文件类型: {ext} ({path})")

    # ---------- 各类型具体读取 ----------

    def _read_text_file(self, path: Path) -> FileContentModel:
        """读取纯文本文件，返回 FileContentModel 对象"""
        # 多编码回退策略，尽量读出文本
        encodings = ["utf-8", "gbk", "gb2312", "latin-1", "cp1252"]
        content = ""

        for encoding in encodings:
            try:
                with open(path, "r", encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        if not content:
            raise Exception(f"无法解码文本文件: {path}")

        return FileContentModel(
            file_path=rel_to_workspace(path), file_type="text", content=content
        )

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

    def _read_pdf_file(self, path: Path) -> FileContentModel:
        """读取PDF文件,提取文本内容,封装为 FileContentModel 对象"""
        import pdfplumber

        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"

        return FileContentModel(
            file_path=rel_to_workspace(path),
            file_type="text",
            content=text,
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
                ".jpe": "image/jpeg",
                ".png": "image/png",
                ".bmp": "image/bmp",
                ".tif": "image/tiff",
                ".tiff": "image/tiff",
                ".webp": "image/webp",
                ".heic": "image/heic",
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
