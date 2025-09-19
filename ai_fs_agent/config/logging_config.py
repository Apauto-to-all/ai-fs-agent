# 日志管理
import logging, os, datetime
from logging.handlers import TimedRotatingFileHandler
from ai_fs_agent.config.paths_config import LOGS_DIR

is_dev = True  # 是否为开发模式，True表示开发模式，False表示生产模式

# 开发模式格式
dev_format = "%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s"
# 生产模式格式
prod_format = "%(asctime)s %(levelname)s %(message)s"


def setup_logging() -> None:
    # 日志记录器初始化
    logging.basicConfig(
        level=logging.DEBUG if is_dev else logging.INFO,
        # level=logging.INFO,
        format=dev_format if is_dev else prod_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            TimedRotatingFileHandler(
                filename=os.path.join(
                    LOGS_DIR, datetime.datetime.now().strftime("%Y-%m-%d") + ".log"
                ),
                when="midnight",  # 每天午夜创建一个新的日志文件
                interval=1,  # 间隔1天
                backupCount=365,  # 保留最近365天的日志文件
                encoding="utf-8",
            ),
            # logging.StreamHandler(),
        ],
    )

    logging.info(f"日志记录器初始化完成！")
