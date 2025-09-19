import logging
import traceback

logger = logging.getLogger(__name__)

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from ai_fs_agent.config.paths_config import USER_CONFIG_PATH


class UserConfig(BaseModel):
    workspace_dir: Optional[Path] = Field(
        default=None,
        description="工作目录，用于智能体进行文件和文件夹的智能管理操作；若未设置，提醒用户设置",
    )
    use_git: bool = Field(
        default=True,
        description="是否使用 Git 管理工作目录；若未安装 Git 或显式设为 False，则禁用 Git 功能",
    )
    use_rag: bool = Field(
        default=True,
        description="是否使用 RAG（Retrieval-Augmented Generation）功能；用于文件搜索和问答",
    )

    def _save_to_file(self):
        """保存设置到文件"""
        try:
            USER_CONFIG_PATH.write_text(
                self.model_dump_json(by_alias=True, indent=4), encoding="utf-8"
            )
            logger.info("配置已保存到文件")
        except Exception as e:
            logger.error(f"保存设置失败: {e}")

    def __setattr__(self, name, value):
        """一旦修改模型字段，立刻写回文件（仅在值真正改变时）"""
        try:
            # 检查对象是否已初始化，避免初始化时的异常
            if hasattr(self, name) and getattr(self, name, None) == value:
                return  # 值未改变，无需保存
            super().__setattr__(name, value)
            self._save_to_file()
        except Exception as e:
            logger.error(f"修改字段 {name} 失败: {e}")
