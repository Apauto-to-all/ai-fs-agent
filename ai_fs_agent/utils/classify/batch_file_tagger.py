import logging

logger = logging.getLogger(__name__)

from typing import List, Iterable, Tuple
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from ai_fs_agent.utils.ingest.file_loader import FileLoader
from ai_fs_agent.utils.ingest.text_processor import TextProcessor
from ai_fs_agent.utils.classify.tagging_llm import TaggingLLM, TagListModel
from ai_fs_agent.utils.classify.tag_service import TagCacheService, TagRecord


class PreparedFileSample(BaseModel):
    file_path: str = Field(..., description="原始文件路径")
    normalized_text: str = Field(..., description="归一化文本")
    cache_record: TagRecord  # 初始可能为空 tags=[]


class FileTaggingResult(BaseModel):
    file_path: str = Field(..., description="原始文件路径")
    tags: List[str] = Field(default_factory=list, description="主题标签列表")


class BatchFileTagger:
    """
    文件批量打标签编排：
    1) 读取与裁剪
    2) 归一化组装文本
    3) 查询缓存 / 近似复用
    4) 收集未命中样本 -> LLM 批量
    5) 写回缓存
    6) 汇总输出
    """

    def __init__(self, max_concurrency: int = 5):
        """max_concurrency: LLM 并发数限制，防止过载"""
        self.loader = FileLoader()
        self.processor = TextProcessor()
        self.tagging_llm = TaggingLLM()
        self.cache = TagCacheService()
        self.max_concurrency = max_concurrency

    # -------- 外部主入口 --------
    def batch_tag_files(
        self, file_paths: List[str], max_total_chars: int = 1500
    ) -> List[FileTaggingResult]:
        """对一批文件进行主题标签抽取"""
        samples = self._load_and_prepare_samples(file_paths, max_total_chars)
        cached, uncached = self._split_cached_and_uncached(samples)

        if uncached:
            requests = self._build_llm_requests(uncached)
            responses = self._run_llm_batch(requests)
            self._persist_new_tags(uncached, responses)

        return self._assemble_results(samples)

    # -------- 步骤函数 --------
    def _load_and_prepare_samples(
        self, file_paths: Iterable[str], max_total_chars: int
    ) -> List[PreparedFileSample]:
        """读取文件，裁剪归一化，查询缓存"""
        result: List[PreparedFileSample] = []
        for path in file_paths:
            try:
                raw = self.loader.load_text(path)[0].page_content
            except Exception as e:
                logger.error(f"读取文件失败 {path}: {e}")
                continue
            sections = self.processor.split_for_labeling(raw, max_total_chars)
            normalized = (
                f"【开头内容】{sections.front}\n"
                f"【中间内容】{sections.middle}\n"
                f"【结尾内容】{sections.back}\n"
            )
            cache_record = self.cache.get_or_create_empty(raw)
            result.append(
                PreparedFileSample(
                    file_path=path,
                    normalized_text=normalized,
                    cache_record=cache_record,
                )
            )
        return result

    def _split_cached_and_uncached(
        self, samples: List[PreparedFileSample]
    ) -> Tuple[List[PreparedFileSample], List[PreparedFileSample]]:
        """根据缓存记录是否已有标签，拆分为已命中与未命中两组"""
        cached = [s for s in samples if s.cache_record.tags]
        uncached = [s for s in samples if not s.cache_record.tags]
        return cached, uncached

    def _build_llm_requests(self, samples: List[PreparedFileSample]):
        """构建 LLM 批量请求"""
        sys_msg = SystemMessage(content=self.tagging_llm.system_prompt)
        reqs = []
        for s in samples:
            human_msg = HumanMessage(
                content=(
                    f"【文件名】{s.file_path}\n"
                    f"{s.normalized_text}\n"
                    f"{self.tagging_llm.structured_output_prompt}"
                )
            )
            reqs.append([sys_msg, human_msg])
        return reqs

    def _run_llm_batch(self, requests) -> List[TagListModel | None]:
        """调用 LLM 批量处理"""
        model = self.tagging_llm.model_with_structure
        try:
            responses = model.batch(
                requests,
                config={"max_concurrency": self.max_concurrency},
            )
            return responses
        except Exception as e:
            logger.error(f"LLM 批处理失败: {e}")
            return [None] * len(requests)

    def _persist_new_tags(
        self,
        uncached_samples: List[PreparedFileSample],
        responses: List[TagListModel | None],
    ):
        """将新标签写入缓存"""
        updated = 0
        for sample, resp in zip(uncached_samples, responses):
            if not resp:
                continue
            tags = resp.tags
            self.cache.update_tags(sample.cache_record, tags)
            updated += 1
        if updated:
            self.cache.flush()
            logger.info(f"新增标签写入缓存：{updated} 条")

    def _assemble_results(
        self, samples: List[PreparedFileSample]
    ) -> List[FileTaggingResult]:
        """汇总所有样本的最终标签结果"""
        return [
            FileTaggingResult(file_path=s.file_path, tags=s.cache_record.tags)
            for s in samples
        ]
