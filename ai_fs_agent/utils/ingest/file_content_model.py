from pydantic import BaseModel, Field
from typing import Optional, Literal


class FileContentModel(BaseModel):
    """文件内容模型"""

    file_path: str = Field(..., description="文件路径，相对与工作目录的路径")
    """文件路径，相对与工作目录的路径"""
    file_type: Literal["text", "image"] = Field(
        default="text", description="文件类型：text或image"
    )
    """文件类型：text或image"""
    content: str = Field(
        default="", description="文本内容（文本文件）或图像描述（图像文件）"
    )
    """文本内容（文本文件）或图像描述（图像文件）"""
    image_base64: Optional[str] = Field(
        default=None, description="图像base64编码（图像文件）"
    )
    """图像base64编码（图像文件）"""
