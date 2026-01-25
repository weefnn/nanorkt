"""
NanoRTK 统一日志配置模块

本模块提供统一的日志配置，确保整个应用使用一致的日志格式和级别。

功能特性：
- 统一的日志格式（时间戳、模块名、级别、消息）
- 可配置的日志级别
- 支持控制台和文件输出
- 支持 Socket.IO 实时日志推送

使用方法：
    >>> from app.core.logging_config import setup_logging
    >>> setup_logging()  # 使用默认配置
    >>> setup_logging(level="INFO")  # 指定日志级别
"""

import logging
import logging.config
from typing import Optional


# 默认日志格式
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 日志配置字典
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": DEFAULT_FORMAT,
            "datefmt": DEFAULT_DATE_FORMAT,
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
            "datefmt": DEFAULT_DATE_FORMAT,
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {
        "level": "DEBUG",
        "handlers": ["console"],
    },
    "loggers": {
        # 降低第三方库的日志级别
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "uvicorn.error": {
            "level": "INFO",
            "handlers": ["console"],
            "propagate": False,
        },
        "uvicorn.access": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": False,
        },
        "socketio": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": False,
        },
        "engineio": {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}


def setup_logging(
    level: str = "DEBUG",
    log_file: Optional[str] = None,
    enable_detailed: bool = False
) -> None:
    """
    配置全局日志系统
    
    此函数应在应用启动时调用一次，配置整个应用的日志行为。
    
    Args:
        level: 日志级别，可选值: DEBUG, INFO, WARNING, ERROR, CRITICAL
        log_file: 日志文件路径（可选），如果提供则同时输出到文件
        enable_detailed: 是否启用详细格式（包含文件名和行号）
    
    Example:
        >>> # 基本使用
        >>> setup_logging()
        
        >>> # 生产环境配置
        >>> setup_logging(level="INFO", log_file="/var/log/nanorkt.log")
        
        >>> # 调试配置
        >>> setup_logging(level="DEBUG", enable_detailed=True)
    """
    config = LOGGING_CONFIG.copy()
    
    # 设置日志级别
    config["root"]["level"] = level.upper()
    
    # 设置格式器
    if enable_detailed:
        config["handlers"]["console"]["formatter"] = "detailed"
    
    # 添加文件处理器
    if log_file:
        config["handlers"]["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": level.upper(),
            "formatter": "detailed" if enable_detailed else "standard",
            "filename": log_file,
            "maxBytes": 10 * 1024 * 1024,  # 10 MB
            "backupCount": 5,
            "encoding": "utf-8",
        }
        config["root"]["handlers"].append("file")
    
    # 应用配置
    logging.config.dictConfig(config)
    
    # 记录日志系统初始化完成
    logger = logging.getLogger(__name__)
    logger.debug(f"日志系统已初始化 - 级别: {level.upper()}")
    if log_file:
        logger.debug(f"日志文件: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志记录器
    
    这是一个便捷函数，等同于 logging.getLogger(name)。
    
    Args:
        name: 日志记录器名称，通常使用 __name__
    
    Returns:
        配置好的日志记录器实例
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("这是一条日志消息")
    """
    return logging.getLogger(name)
