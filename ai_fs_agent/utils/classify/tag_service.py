import logging
from datetime import datetime
import hashlib
from typing import Dict, Optional, List
from pydantic import BaseModel, Field
from simhash import Simhash
from ai_fs_agent.config.paths_config import TAGS_CACHE_PATH

logger = logging.getLogger(__name__)


class TagRecord(BaseModel):
    """文本内容对应的标签缓存记录"""

    content_id: str = Field(..., description="内容哈希ID（基于文本内容）")
    """内容哈希ID，用于唯一标识文本内容"""
    simhash64: Optional[int] = Field(default=None, description="SimHash 64位指纹")
    """SimHash 64位指纹，用于快速比较文本内容的相似度"""
    tags: List[str] = Field(default_factory=list, description="标签列表")
    """标签列表"""
    file_description: Optional[str] = Field(
        default=None,
        description="文件内容描述（适用于图像、视频、可执行文件等非文本文件）",
    )
    """文件内容描述，适用于图像、视频、可执行文件等非文本文件"""
    ts: datetime = Field(default_factory=datetime.now, description="入库时间")
    """标签缓存记录的创建时间"""


class TagCacheModel(BaseModel):
    cache: Dict[str, TagRecord] = Field(
        default_factory=dict, description="content_id -> TagRecord"
    )

    def save(self):
        try:
            TAGS_CACHE_PATH.write_text(
                self.model_dump_json(by_alias=True, indent=4), encoding="utf-8"
            )
            logger.debug("标签缓存已写入文件")
        except Exception as e:
            logger.error(f"保存标签缓存失败: {e}")


class TagCacheService:
    """
    基于文本内容的标签缓存：
    - 精确命中：blake2b(content)
    - 近似命中：SimHash（海明距离 <= 阈值）
    - 不负责生成；只负责：查询 / 存储 / 近似复用
    """

    def __init__(self, simhash_hamming_threshold: int = 8):
        if TAGS_CACHE_PATH.exists():
            self.cache_model = TagCacheModel.model_validate_json(
                TAGS_CACHE_PATH.read_text(encoding="utf-8")
            )
        else:
            self.cache_model = TagCacheModel()
            self.cache_model.save()
        self._simhash_hamming_threshold = simhash_hamming_threshold

    # -------- 公共接口 --------
    def get_or_init_record(self, normalized: str, use_approx: bool = True) -> TagRecord:
        """根据文本内容获取或初始化标签记录（不含标签）
        Args:
            normalized: 归一化的文本内容，用于标识
            use_approx: 是否启用近似复用，默认为True
        """
        cid = self._text_hash(normalized)
        hit = self.get_by_id(cid)
        if hit:
            return hit
        sh = self._simhash64(normalized)

        # 根据参数决定是否进行近似复用
        tags = []
        file_description = None

        if use_approx:
            approx = self._find_by_simhash(sh, self._simhash_hamming_threshold)
            if approx:
                # 近似复用
                tags = approx.tags
                file_description = approx.file_description

        # 创建记录
        record = TagRecord(
            content_id=cid,
            simhash64=sh,
            tags=tags,
            file_description=file_description,
        )

        self.cache_model.cache[cid] = record
        return record

    def get_by_id(self, content_id: str) -> Optional[TagRecord]:
        """根据内容ID精确查询标签记录"""
        rec = self.cache_model.cache.get(content_id)
        if not rec:
            return None
        return rec.model_copy()

    def update_tags(self, record: TagRecord, tags: List[str]):
        """更新标签记录的标签列表，并写回缓存"""
        record.tags = tags
        record.ts = datetime.now()
        self.cache_model.cache[record.content_id] = record

    def update_file_description(self, record: TagRecord, file_description: str):
        """更新标签记录的文件描述（适用于图像、视频、可执行文件等非文本文件），并写回缓存"""
        record.file_description = file_description
        record.ts = datetime.now()
        self.cache_model.cache[record.content_id] = record

    def flush(self):
        """将缓存写回文件"""
        self.cache_model.save()

    # -------- 内部方法 --------
    def _text_hash(self, text: str) -> str:
        """基于文本内容计算 blake2b 哈希，作为内容ID"""
        h = hashlib.blake2b(digest_size=32)
        h.update(text.encode("utf-8", errors="ignore"))
        return h.hexdigest()

    def _simhash64(self, text: str, n: int = 3) -> int:
        """计算文本的 SimHash 64位指纹，基于 n-gram 分词"""
        if len(text) < n:
            feats = [text]
        else:
            feats = [text[i : i + n] for i in range(len(text) - n + 1)]
        return Simhash(feats).value

    def _find_by_simhash(self, sh: int, max_hamming: int) -> Optional[TagRecord]:
        """基于 SimHash 指纹，查找近似记录（海明距离 <= max_hamming）"""
        best: Optional[TagRecord] = None
        best_dist = 65
        for rec in self.cache_model.cache.values():
            if rec.simhash64 is None:
                continue
            x = sh ^ rec.simhash64
            d = x.bit_count()
            if d < best_dist:
                best_dist = d
                best = rec
                if d == 0:
                    break
        if best and best_dist <= max_hamming:
            return best
        return None
