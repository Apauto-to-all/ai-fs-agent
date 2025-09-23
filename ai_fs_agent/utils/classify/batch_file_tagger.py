import logging
import traceback

logger = logging.getLogger(__name__)

from typing import List, Iterable
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field

from ai_fs_agent.utils.ingest.file_content_model import FileContentModel
from ai_fs_agent.utils.ingest.file_loader import FileLoader
from ai_fs_agent.utils.classify.tagging_llm import TaggingLLM, TagListModel
from ai_fs_agent.utils.classify.image_llm import ImageLLM
from ai_fs_agent.utils.classify.tag_service import TagCacheService, TagRecord


class PreparedFileSample(BaseModel):
    file_content_model: FileContentModel
    cache_record: TagRecord  # 初始可能为空 tags=[]


class FileTaggingResult(BaseModel):
    file_path: str = Field(..., description="原始文件路径")
    tags: List[str] = Field(default_factory=list, description="主题标签列表")


class BatchFileTagger:
    """文件批量打标签，传入文件路径列表，自动对图像（调用图像理解模型进行描述）和文本文件进行打标签"""

    # TODO：优化文件分类功能，
    # 1、自主可控性不强，不能手动给文件打标签
    # 2、分类规则质量不稳定，分类规则让AI单独进行管理，并提供分类规则模版便于可控

    def __init__(self, max_concurrency: int = 5):
        """max_concurrency: LLM 并发数限制，防止过载"""
        self.loader = FileLoader()
        self.tagging_llm: TaggingLLM = None
        self.image_llm: ImageLLM = None
        self.cache = TagCacheService()
        self.max_concurrency = max_concurrency

    # -------- 外部主入口 --------
    def batch_tag_files(self, file_paths: List[str]) -> List[FileTaggingResult]:
        """对一批文件进行主题标签抽取"""
        samples = self._load_and_prepare_samples(file_paths)
        uncached = [s for s in samples if not s.cache_record.tags]

        if uncached:
            # 分离图像文件并处理描述
            image_samples = [
                s for s in uncached if s.file_content_model.file_type == "image"
            ]
            # 储存无缓存描述的图像文件
            image_samples_no_desc = []
            for s in image_samples:
                if s.cache_record.file_description:
                    # 有缓存描述，使用缓存描述
                    s.file_content_model.content = s.cache_record.file_description
                    # 缓存描述也作为归一化文本用于标签提取
                    s.file_content_model.normalized_text_for_tagging = (
                        s.cache_record.file_description
                    )
                else:
                    # 无缓存描述，添加到待处理列表
                    image_samples_no_desc.append(s)

            # 处理无描述的图像文件
            if image_samples_no_desc:
                self._process_images_batch(image_samples_no_desc)

            # 批量给所有文件打标签
            self._process_tags_batch(uncached)

        return self._assemble_results(samples)

    # -------- 步骤函数 --------
    def _load_and_prepare_samples(
        self, file_paths: Iterable[str]
    ) -> List[PreparedFileSample]:
        """读取文件，查询缓存"""
        result: List[PreparedFileSample] = []
        for path in file_paths:
            # 对于不支持的文件类型进行跳过
            try:
                file_content_model = self.loader.load_file(path)
            except ValueError as ve:
                # 文件不支持
                logger.warning(f"文件不支持：{path}，错误信息：{ve}")
                continue
            except Exception as e:
                logger.debug(traceback.format_exc())
                logger.error(f"加载文件失败：{path}，错误信息：{e}")
                continue
            # 查询缓存
            cache_record = self.cache.get_or_init_record(
                file_content_model.normalized_text_for_id
            )
            result.append(
                PreparedFileSample(
                    file_content_model=file_content_model,
                    cache_record=cache_record,
                )
            )
        return result

    def _process_images_batch(self, image_samples: List[PreparedFileSample]):
        """
        批量处理图像文件，生成图像描述或内容
        :param image_samples: 图像文件样本列表
        """
        if not image_samples:
            return
        # 构建请求
        if self.image_llm is None:
            self.image_llm = ImageLLM()
        messages_batch = []
        sys_msg = SystemMessage(content=self.image_llm.system_prompt)
        # TODO：对图像进行压缩处理，减少Token消耗
        for s in image_samples:
            human_msg = HumanMessage(
                content=[
                    {
                        "type": "image_url",
                        "image_url": {"url": s.file_content_model.image_base64},
                    },
                ]
            )
            messages_batch.append([sys_msg, human_msg])
        # 批量调用图像模型
        model = self.image_llm.llm
        # 批量生成文本描述，更新FileContentModel的content和normalized_text_for_tagging字段
        image_responses = model.batch(
            messages_batch,
            config={"max_concurrency": self.max_concurrency},
        )
        # 更新图像FileContentModel的content字段
        # 将图像描述写入cache_record.file_description
        updated = 0
        for s, resp in zip(image_samples, image_responses):
            if not resp:
                continue
            s.file_content_model.content = resp.content
            s.file_content_model.normalized_text_for_tagging = resp.content
            s.cache_record.file_description = resp.content
            self.cache.update_file_description(s.cache_record, resp.content)
            updated += 1
        if updated:
            self.cache.flush()

    def _process_tags_batch(self, uncached_samples: List[PreparedFileSample]):
        """
        批量处理未命中缓存的文件
        :param uncached_samples: 未命中缓存的文件样本列表
        """
        if not uncached_samples:
            return
        # 初始化 LLM
        if self.tagging_llm is None:
            self.tagging_llm = TaggingLLM()
        sys_msg = SystemMessage(content=self.tagging_llm.system_prompt)
        messages_batch = []
        for s in uncached_samples:
            human_msg = HumanMessage(
                content=(
                    f"【文件名】{s.file_content_model.file_path}\n"
                    f"{s.file_content_model.normalized_text_for_tagging}\n"
                    f"{self.tagging_llm.structured_output_prompt}"
                )
            )
            messages_batch.append([sys_msg, human_msg])

        model = self.tagging_llm.model_with_structure
        tag_responses: List[TagListModel] = model.batch(
            messages_batch,
            config={"max_concurrency": self.max_concurrency},
        )

        # 将新标签写入缓存
        updated = 0
        for sample, resp in zip(uncached_samples, tag_responses):
            if not resp:
                continue
            sample.cache_record.tags = resp.tags
            self.cache.update_tags(sample.cache_record, resp.tags)
            updated += 1
        if updated:
            self.cache.flush()

    def _assemble_results(
        self, samples: List[PreparedFileSample]
    ) -> List[FileTaggingResult]:
        """汇总所有样本的最终标签结果"""
        return [
            FileTaggingResult(
                file_path=s.file_content_model.file_path, tags=s.cache_record.tags
            )
            for s in samples
        ]
