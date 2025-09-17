import logging
import traceback

logger = logging.getLogger(__name__)

from datetime import datetime
import hashlib
from typing import Dict, Optional, List
from pydantic import BaseModel, Field
from simhash import Simhash
from ai_fs_agent.config.paths_config import LABEL_CACHE_PATH


class LabelResult(BaseModel):
    """仅基于文本内容的标签结果（结构化输出）"""

    content_id: str = Field(..., description="内容哈希ID（内容变则变，路径无关）")
    simhash64: Optional[int] = Field(default=None, description="SimHash 64 位指纹")
    labels: List[str] = Field(
        default_factory=list, description="多标签，主标签应出现在首位"
    )
    ts: datetime = Field(default_factory=datetime.now, description="结果时间")


class LabelCacheModel(BaseModel):
    """管理 label_cache 的 BaseModel，自动保存到文件"""

    label_cache: Dict[str, LabelResult] = Field(
        default_factory=dict, description="标签缓存字典"
    )

    def _save_to_file(self):
        """保存缓存到文件"""
        try:
            LABEL_CACHE_PATH.write_text(
                self.model_dump_json(by_alias=True, indent=4), encoding="utf-8"
            )
            logger.info("文件标签缓存，已保存到文件")
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")


class ContentLabelService:
    """
    仅基于文本内容进行打标签的服务（彻底移除文件路径读取相关功能）。
    主要方法：label_content(text)：传入文本 -> 计算 content_id -> 查缓存 -> 规则判定 -> 返回结果并缓存
    """

    def __init__(self):
        if not LABEL_CACHE_PATH.exists():
            self.label_cache_model = LabelCacheModel()
            self.label_cache_model._save_to_file()
        else:
            self.label_cache_model = LabelCacheModel.model_validate_json(
                LABEL_CACHE_PATH.read_text(encoding="utf-8")
            )

        # 近似匹配阈值（可调）：≤8 视为近重复，直接复用标签
        self._simhash_hamming_threshold = 8

    # 公开 API -----------------------

    def label_content(self, text: str) -> LabelResult:
        """
        仅基于文本进行打标签（不访问文件系统）。
        返回 LabelResult（并将结果写入本地缓存）。
        """
        cid = self._text_hash(text)

        # 1) 精确命中缓存
        cached = self.get_label_by_id(cid)
        if cached:
            return cached

        # 2) 近似复用：SimHash 查找近重复内容（小改动沿用旧标签）
        sh = self._simhash64(text)
        approx = self._find_by_simhash(sh, self._simhash_hamming_threshold)
        if approx:
            # 复用旧标签，但为新 content_id 建立缓存记录；保留本次 simhash
            res = LabelResult(content_id=cid, simhash64=sh, labels=approx.labels)
            self.label_cache_model.label_cache[cid] = res
            self.label_cache_model._save_to_file()
            return res

        # 3) TODO：调用大模型生成标签（此处占位）
        labels = ["未分类"]

        res = LabelResult(content_id=cid, simhash64=sh, labels=labels)
        self.label_cache_model.label_cache[cid] = res
        self.label_cache_model._save_to_file()
        return res

    def get_label_by_id(self, content_id: str) -> Optional[LabelResult]:
        hit = self.label_cache_model.label_cache.get(content_id)
        if not hit:
            return None
        # 返回副本，防止外部修改内部对象
        return hit.model_copy()

    # 内部实现 -----------------------

    def _text_hash(self, text: str) -> str:
        """对文本计算 blake2b 哈希作为 content_id"""
        h = hashlib.blake2b(digest_size=32)
        h.update(text.encode("utf-8", errors="ignore"))
        return h.hexdigest()

    def _simhash64(self, text: str, n: int = 3) -> int:
        """计算 64 位 SimHash 指纹"""
        if len(text) < n:
            return [text]
        feats = [text[i : i + n] for i in range(len(text) - n + 1)]
        return Simhash(feats).value  # 64-bit int

    def _find_by_simhash(self, sh: int, max_hamming: int) -> Optional[LabelResult]:
        """
        在现有缓存中用 SimHash 近似查找一个“最相似”的已标注样本。
        说明：当前为线性扫描，缓存量较小时开销极小；规模变大可换 LSH/HNSW。
        """
        best: Optional[LabelResult] = None
        best_dist = 65  # 大于 64 保证首次替换
        for item in self.label_cache_model.label_cache.values():
            if item.simhash64 is None:
                continue
            # 计算64位整数的海明距离
            x = sh ^ item.simhash64
            d = x.bit_count() if hasattr(x, "bit_count") else bin(x).count("1")
            if d < best_dist:
                best_dist = d
                best = item
                if best_dist == 0:
                    break
        if best and best_dist <= max_hamming:
            return best
        return None
