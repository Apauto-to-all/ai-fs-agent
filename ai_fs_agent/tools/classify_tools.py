from datetime import datetime
import logging
import traceback
from typing import Any, Dict, List
import threading

from langchain.tools import tool

from ai_fs_agent.config import user_config
from ai_fs_agent.utils.classify.batch_file_tagger import BatchFileTagger
from ai_fs_agent.config.paths_config import CLASSIFY_RULES_PATH
from ai_fs_agent.utils.fs.fs_apply import _fs_apply_operator
from ai_fs_agent.utils.fs.fs_query import _fs_query_operator
from ai_fs_agent.utils.git.git_repo import _git_repo

logger = logging.getLogger(__name__)


@tool("classify_get_tags")
def classify_get_tags() -> Dict[str, Any]:
    """
    获取未分类文件的标签
    - 返回：{ ok, results?[], message?, error? }
    """
    try:
        # 读取工作目录下的文件
        list_file_dir = _fs_query_operator.run(op="list", path=".")
        if not list_file_dir.get("ok"):
            return {
                "ok": False,
                "error": "无法列出工作目录下的文件",
            }
        if not list_file_dir.get("data"):
            return {
                "ok": True,
                "message": "所有文件均已分类，无需处理（只会对工作目录下的文件进行分类处理，不包含子目录）",
            }
        unclassified_files: List[str] = [
            f.get("path")
            for f in list_file_dir.get("data", {})
            if f.get("type") == "file"
        ]
        if unclassified_files:
            tagger = BatchFileTagger(max_concurrency=5)
            results = tagger.batch_tag_files(unclassified_files)

            return {
                "ok": True,
                "results": [
                    {"file_path": res.file_path, "tags": res.tags} for res in results
                ],
            }
        else:
            return {
                "ok": True,
                "message": "所有文件均已分类，无需处理（只会对工作目录下的文件进行分类处理，不包含子目录）",
            }
    except Exception as e:
        logger.debug(traceback.format_exc())
        logger.error(e)
        return {
            "ok": False,
            "error": "classify_get_labels 执行失败",
        }


@tool("classify_get_rules")
def classify_get_rules() -> Dict[str, Any]:
    """
    获取分类规则，在进行文件分类前，先获取当前的分类规则
    - 返回：{ ok, rules?, error? }
    """
    try:
        if not CLASSIFY_RULES_PATH.exists():
            return {
                "ok": False,
                "error": "“分类规则”文件不存在，需要进行自动生成",
            }
        # 使用 Path 读取，默认 UTF-8
        content = CLASSIFY_RULES_PATH.read_text(encoding="utf-8")
        return {
            "ok": True,
            "rules": content,
        }
    except Exception as e:
        logger.debug(traceback.format_exc())
        logger.error(e)
        return {
            "ok": False,
            "error": f"读取“分类规则”失败，提醒用户手动检查“分类规则”（{CLASSIFY_RULES_PATH}）文件",
        }


@tool("classify_update_rules")
def classify_update_rules(new_rules: str) -> Dict[str, Any]:
    """
    更新“分类规则”，如果已存在“旧分类规则”，“新规则”（new_rules）要保留“旧规则”内容
    可以对旧规则进行整理和优化，但不能直接去除旧规则，以防影响已分类的文件
    - 参数：new_rules (字符串，MD 格式的规则内容)
    - 返回：{ ok, message?, error? }
    """
    try:
        # 使用 Path.write_text() 写入，默认 UTF-8
        CLASSIFY_RULES_PATH.write_text(new_rules, encoding="utf-8")
        return {
            "ok": True,
            "message": "分类规则已更新",
        }
    except Exception as e:
        logger.debug(traceback.format_exc())
        logger.error(e)
        return {
            "ok": False,
            "error": f"更新“分类规则”失败，请提醒用户手动检查“分类规则”（{CLASSIFY_RULES_PATH}）文件",
        }


@tool("classify_move_files")
def classify_move_files(files_to_move: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    批量移动文件到目标路径
    - 作用域：仅工作目录内（仅允许相对路径，不允许越界到工作目录外）
    - 返回：{ ok, message?, error? }

    参数：
    - files_to_move: 操作参数列表，每个 dict 支持以下参数：
        - src: 源路径（必填，相对路径）
        - dst: 目标路径（必填，相对路径）

    模式：
    - 移动：将 src 移动到 dst；如果目标存在，程序会自动重命名，不必担心覆盖

    示例：
    - 单个移动：files_to_move=[{"src": "a.txt", "dst": "文档/a.txt"}]
    - 批量移动：files_to_move=[{"src": "b.txt", "dst": "文档/b.txt"}, {"src": "README.md", "dst": "文档/README.md"}]
    """
    try:
        # 先提交一次，保存当前状态
        try:
            if user_config.use_git:
                # 如果有变化，就提交一次
                _git_repo.commit_all(
                    message=f"Human：保存变更（{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}）"
                )
        except Exception as e:
            pass  # 忽略提交失败，继续执行变更

        moved_files = []
        failed_files = []
        rag_files = []
        for file_info in files_to_move:
            src = file_info.get("src")
            dst = file_info.get("dst")
            if not src or not dst:
                failed_files.append(f"无效参数: {file_info}")
                continue
            # 进行分类移动时，不进行 Git 提交，统一在最后提交
            move_result = _fs_apply_operator.run(
                op="move", src=src, dst=dst, is_use_git=False
            )
            if move_result.get("ok"):
                moved_files.append(f"{src} -> {dst}")
                rag_files.append(dst)  # 记录移动后的文件路径，后续进行 RAG 索引
            else:
                failed_files.append(
                    f"{src} -> {dst}: {move_result.get('error', '未知错误')}"
                )

        # 文件分类完成后，进行一次 Git 提交
        try:
            if user_config.use_git:
                commit_message = f"AI：对文件进行分类\n" + "\n".join(moved_files)
                _git_repo.commit_all(message=commit_message)
        except Exception as e:
            pass  # 忽略提交失败

        # 判断是否需要进行对文档RAG索引
        try:
            if user_config.use_rag and rag_files:
                from ai_fs_agent.utils.rag.batch_index_builder import BatchIndexBuilder

                def _run_rag_index(files: List[str]) -> None:
                    try:
                        logger.info(f"后台启动 RAG 索引构建，文件数: {len(files)}")
                        b = BatchIndexBuilder()
                        b.batch_build_index(files)
                        logger.info("后台 RAG 索引构建完成")
                    except Exception as e:
                        logger.debug(traceback.format_exc())
                        logger.error(e)
                        logger.error("后台 RAG 索引构建失败")

                # 启动守护线程在后台执行索引构建，不阻塞主线程
                t = threading.Thread(
                    target=_run_rag_index, args=(rag_files,), daemon=True
                )
                t.start()
        except Exception:
            pass  # 忽略 RAG 索引失败

        return {
            "ok": True,
            "message": f"批量移动完成: {moved_files}",
            "error": f"部分文件移动失败: {failed_files}" if failed_files else None,
        }
    except Exception as e:
        logger.debug(traceback.format_exc())
        logger.error(e)
        return {
            "ok": False,
            "error": "移动文件进行分类操作失败",
        }


classify_tools_list = [
    classify_get_tags,
    classify_get_rules,
    classify_update_rules,
    classify_move_files,
]
