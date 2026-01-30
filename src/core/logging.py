"""日志配置"""

import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    """设置日志"""
    logger = logging.getLogger("rag_agent")
    logger.setLevel(getattr(logging, level.upper()))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)

    return logger


logger = setup_logging()
