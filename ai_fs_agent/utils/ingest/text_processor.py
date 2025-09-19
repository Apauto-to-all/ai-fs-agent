import re
from typing import List
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    CharacterTextSplitter,
)
from pydantic import BaseModel, Field


class ThreePartSections(BaseModel):
    front: str = Field(default="")
    middle: str = Field(default="")
    back: str = Field(default="")


class TextProcessor:
    """
    文本预处理与分割工具：
    - 归一化：大小写、空白、可选去标点
    - 分割：使用 LangChain 的 TextSplitter（字符、递归字符、Markdown）
    """

    # ---------- 归一化 ----------

    def normalize(
        self,
        text: str,
        lower: bool = False,
        squeeze_ws: bool = True,
        strip: bool = True,
        remove_punct: bool = False,
        remove_digits: bool = False,
    ) -> str:
        """
        文本归一化：大小写、空白、标点、数字处理。
        优化：合并正则，添加输入验证和扩展功能。
        """
        if not isinstance(text, str):
            return ""  # 处理非字符串输入
        t = text
        # 小写转换（优先，避免影响后续正则）
        if lower:
            t = t.lower()
        # 合并正则：去除标点和数字（可选）
        if remove_punct or remove_digits:
            pattern = ""
            if remove_punct:
                pattern += r"[^\w\s]"  # 标点
            if remove_digits:
                pattern += r"|\d+"  # 数字
            if pattern:
                try:
                    t = re.sub(pattern, " ", t)
                except re.error:
                    pass  # 正则错误时跳过
        # 压缩空白
        if squeeze_ws:
            t = re.sub(r"\s+", " ", t)
        # 去除首尾空白
        if strip:
            t = t.strip()
        return t

    # ---------- 分割（使用 LangChain）----------
    def split_for_tag_cache(self, text: str) -> ThreePartSections:
        """
        快速切割文本为前、中、后三段，使用 CharacterTextSplitter 按长度分割。
        总字符数约 max_total_chars，适合大文本快速处理。
        返回 LabelingSections 实例。
        """
        # 先 normalize 文本（压缩空白、去除首尾空白）
        normalized_text = self.normalize(text, squeeze_ws=True, strip=True)
        # 设置最大字符数
        max_total_chars = 1500
        # 短文本：直接三等分
        if len(normalized_text) <= max_total_chars:
            third = len(normalized_text) // 3
            front = normalized_text[:third]
            middle = normalized_text[third : 2 * third]
            back = normalized_text[2 * third :]
            return ThreePartSections(front=front, middle=middle, back=back)
        # 使用 CharacterTextSplitter 按固定长度分割
        chunk_size = max_total_chars // 3
        splitter = CharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=0,  # 无重叠，快速
        )
        chunks = splitter.split_text(normalized_text)
        # 获取前、中、后块
        total = len(chunks)
        front = chunks[0] if total > 0 else ""
        middle = chunks[total // 2] if total > 1 else ""
        back = chunks[-1] if total >= 1 else ""

        return ThreePartSections(front=front, middle=middle, back=back)

    def split_for_labeling(
        self, text: str, max_total_chars: int = 1500
    ) -> ThreePartSections:
        """
        按文本结构切割文本，获取前中后各1个部分，用于打标签。
        使用 RecursiveCharacterTextSplitter，按段落和句子递归分割。
        返回 LabelingSections 实例
        总字符数（前+中+后）约 max_total_chars
        支持中英文混合文本。
        """
        # 先 normalize 文本（压缩空白、去除首尾空白）
        normalized_text = self.normalize(text, squeeze_ws=True, strip=True)
        # 短文本：直接三等分，确保总字符数 = 实际长度
        if len(normalized_text) < max_total_chars:
            third = len(normalized_text) // 3
            front = normalized_text[:third]
            middle = normalized_text[third : 2 * third]
            back = normalized_text[2 * third :]
            return ThreePartSections(front=front, middle=middle, back=back)
        # 动态 计算 chunk_size，确保前中后总字符数约为 max_total_chars
        dynamic_chunk_size = max_total_chars // 3
        chunks = self.split_into_chunks(
            text, chunk_size=dynamic_chunk_size, chunk_overlap=50
        )
        # 获取前、中、后块
        total = len(chunks)
        front = chunks[0] if total > 0 else ""
        middle = chunks[total // 2] if total > 1 else ""
        back = chunks[-1] if total >= 1 else ""

        return ThreePartSections(front=front, middle=middle, back=back)

    def split_into_chunks(
        self,
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 50,
    ) -> List[str]:
        """
        使用 RecursiveCharacterTextSplitter 切割文本，返回所有切割片段列表。
        支持中英文混合文本，按段落、句子、词、字符递归分割。
        :param text: 原始文本
        :param chunk_size: 每个片段的最大字符数
        :param chunk_overlap: 片段间重叠字符数
        :return: 切割后的文本片段列表
        """
        if not isinstance(text, str) or not text.strip():
            return []
        # 先归一化文本（压缩空白、去除首尾空白）
        normalized_text = self.normalize(text, squeeze_ws=True, strip=True)
        # 创建 RecursiveCharacterTextSplitter
        splitter = RecursiveCharacterTextSplitter(
            separators=[
                "\n\n",  # 段落（双换行）
                "\n",  # 单换行
                "。",  # 中文句号
                ".",  # 英文句号
                "！",  # 中文感叹号
                "!",  # 英文感叹号
                "？",  # 中文问号
                "?",  # 英文问号
                ";",  # 分号（中英文通用）
                "；",  # 中文分号
                " ",  # 空格（词分隔）
                "",  # 字符级（兜底）
            ],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        # 切割文本并返回片段列表
        chunks = splitter.split_text(normalized_text)
        return chunks
