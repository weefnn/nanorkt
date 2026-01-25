"""
Web 工具函数模块

本模块包含 Web 应用中使用的通用工具函数。

功能：
- 配置数据转换
- 系统状态获取
- 数据格式化
"""

import logging
import platform
import subprocess
import time
from typing import Any, Dict

import psutil


def dot_to_nested(flat: Dict[str, Any]) -> Dict[str, Any]:
    """
    将点号分隔的扁平字典转换为嵌套字典
    
    Args:
        flat: 扁平字典，如 {"serial.port": "ttyUSB0", "serial.baudrate": 115200}
    
    Returns:
        嵌套字典，如 {"serial": {"port": "ttyUSB0", "baudrate": 115200}}
    
    Example:
        >>> flat = {"ntrip.host": "example.com", "ntrip.port": 2101}
        >>> dot_to_nested(flat)
        {"ntrip": {"host": "example.com", "port": 2101}}
    """
    result: Dict[str, Any] = {}
    
    for key, value in flat.items():
        parts = key.split(".")
        target = result
        
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        
        target[parts[-1]] = value
    
    return result


def get_system_status() -> Dict[str, Any]:
    """
    获取系统状态信息
    
    收集树莓派（或其他 Linux 系统）的状态信息，包括：
    - CPU 温度
    - 内存使用情况
    - 系统运行时间
    - 硬件和系统版本
    
    Returns:
        包含系统状态的字典
    
    Example:
        >>> status = get_system_status()
        >>> print(f"CPU 温度: {status['cpu_temp']}°C")
        >>> print(f"内存使用: {status['memory_percent']}%")
    """
    logger = logging.getLogger(__name__)
    status: Dict[str, Any] = {}
    
    # ========== CPU 温度 ==========
    cpu_temp = None
    
    # 方法1: 尝试 vcgencmd 命令（树莓派专用）
    try:
        output = subprocess.check_output(
            ["vcgencmd", "measure_temp"],
            universal_newlines=True,
            timeout=2
        )
        # 输出示例：temp=42.5'C
        cpu_temp = float(output.strip().split("=")[1].replace("'C", ""))
    except (subprocess.CalledProcessError, FileNotFoundError, 
            IndexError, ValueError, subprocess.TimeoutExpired):
        pass
    
    # 方法2: 读取 thermal 文件（通用 Linux）
    if cpu_temp is None:
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                cpu_temp = float(f.read().strip()) / 1000.0
        except (IOError, ValueError):
            pass
    
    # 方法3: macOS 暂不支持
    if cpu_temp is None:
        logger.debug("无法获取 CPU 温度（可能不是树莓派）")
    
    status["cpu_temp"] = cpu_temp
    
    # ========== 内存信息 ==========
    mem = psutil.virtual_memory()
    status["memory_total"] = mem.total
    status["memory_available"] = mem.available
    status["memory_percent"] = mem.percent
    
    # ========== 运行时间 ==========
    uptime_seconds = time.time() - psutil.boot_time()
    days = int(uptime_seconds // (24 * 3600))
    hours = int((uptime_seconds % (24 * 3600)) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    
    status["uptime_days"] = days
    status["uptime_hours"] = hours
    status["uptime_minutes"] = minutes
    status["uptime_str"] = f"{days}天 {hours}小时 {minutes}分"
    
    # ========== 硬件版本 ==========
    hardware = ""
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("Model"):
                    hardware = line.split(":")[-1].strip()
                    break
    except IOError:
        pass
    
    if not hardware:
        hardware = platform.machine()
    
    status["hardware"] = hardware
    
    # ========== 系统版本 ==========
    status["system"] = platform.platform()
    
    return status


def format_bytes(size: int) -> str:
    """
    将字节数格式化为人类可读的字符串
    
    Args:
        size: 字节数
    
    Returns:
        格式化的字符串，如 "1.5 MB"
    
    Example:
        >>> format_bytes(1536)
        "1.5 KB"
        >>> format_bytes(1048576)
        "1.0 MB"
    """
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(size) < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} PB"
