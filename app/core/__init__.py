"""
NanoRTK 核心模块

本模块包含 RTK 基站的核心业务逻辑：
- Config: 配置管理
- RTKBaseStation: 基站主类（需要单独导入以避免循环导入）
- 自定义异常类
- 日志配置
"""

from app.core.config import Config
from app.core.exceptions import (
    NanoRTKError,
    SerialConnectionError,
    NTRIPConnectionError,
    ConfigurationError,
)
from app.core.logging_config import setup_logging

# RTKBaseStation 需要单独导入以避免循环导入:
# from app.core.station import RTKBaseStation

__all__ = [
    "Config",
    "NanoRTKError",
    "SerialConnectionError",
    "NTRIPConnectionError",
    "ConfigurationError",
    "setup_logging",
]
