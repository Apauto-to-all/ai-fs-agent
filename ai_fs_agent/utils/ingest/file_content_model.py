from pydantic import BaseModel, Field, model_validator
from typing import Optional, Literal
from ai_fs_agent.utils.ingest.text_processor import TextProcessor

processor = TextProcessor()


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
    # 用于标识化文本（创建content_id）
    normalized_text: Optional[str] = Field(
        default=None, description="归一化文本，用于标识化文本内容"
    )
    """归一化文本，用于标识化文本"""
    # 归一化文本，用于标签生成
    normalized_text_for_tagging: Optional[str] = Field(
        default=None, description="归一化文本，用于标签生成"
    )
    """归一化文本，用于标签生成"""

    @model_validator(mode="before")
    @classmethod
    def set_normalized_fields(cls, data):
        """自动计算归一化文本字段"""
        # 转换为字典以便修改
        if not isinstance(data, dict):
            data = data.dict()

        # 如果 normalized_text 已经设置值，则不重新计算
        if data.get("normalized_text") is None:
            file_type = data.get("file_type", "text")
            content = data.get("content", "")
            image_base64 = data.get("image_base64")

            if file_type == "text":
                # 对于文本文件，使用split_for_tag_cache方法
                # 标识化文本只需要前中后三段拼接，不需要保持语义完整性
                sections = processor.split_for_tag_cache(content)
                normalized = sections.front + sections.middle + sections.back
            elif file_type == "image" and image_base64:
                # 对于图像文件，也进行3段切割
                sections = processor.split_for_tag_cache(image_base64)
                normalized = sections.front + sections.middle + sections.back
            else:
                # 其他文件类型，抛出错误
                raise ValueError(f"不支持的文件类型：{file_type}")

            data["normalized_text"] = normalized

        # 如果 normalized_text_for_tagging 已经设置值，则不重新计算
        if data.get("normalized_text_for_tagging") is None:
            file_type = data.get("file_type", "text")
            content = data.get("content", "")

            if file_type == "text":
                # 对于文本文件，使用split_for_labeling方法
                # 标签生成文本需要保持语义完整性，使用递归分割
                sections = processor.split_for_labeling(content)
                normalized = (
                    f"【开头内容】{sections.front}\n"
                    f"【中间内容】{sections.middle}\n"
                    f"【结尾内容】{sections.back}\n"
                )
            elif file_type == "image":
                # 对于图像文件，直接使用图像描述
                normalized = content
            else:
                # 其他文件类型，抛出错误
                raise ValueError(f"不支持的文件类型：{file_type}")

            data["normalized_text_for_tagging"] = normalized

        return data
