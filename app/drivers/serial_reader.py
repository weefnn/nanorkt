"""
串口读取模块

本模块提供串口数据读取功能，用于从 GNSS 接收机读取 RTCM 数据。
支持上下文管理器模式，确保串口资源正确释放。

功能特性：
- 自动连接和重连
- 非阻塞数据读取
- 回调函数支持
- 上下文管理器支持

使用方法：
    >>> from app.drivers import SerialReader
    >>> 
    >>> # 使用上下文管理器
    >>> with SerialReader("/dev/ttyUSB0", 115200) as reader:
    ...     reader.read_data(callback=my_callback)
    >>> 
    >>> # 手动管理
    >>> reader = SerialReader("/dev/ttyUSB0", 115200)
    >>> reader.connect()
    >>> reader.read_data(callback=my_callback)
    >>> reader.disconnect()
"""

import logging
import threading
import time
from typing import Callable, Optional

import serial

from app.core.exceptions import SerialConnectionError


class SerialReader:
    """
    串口数据读取类
    
    负责管理与 GNSS 接收机的串口连接，读取 RTCM 数据并通过回调函数传递。
    
    Attributes:
        port: 串口设备路径
        baudrate: 波特率
        serial: pyserial Serial 对象
        is_running: 数据读取是否正在运行
    
    Example:
        >>> def on_data(data: bytes):
        ...     print(f"收到 {len(data)} 字节数据")
        >>> 
        >>> reader = SerialReader("/dev/ttyUSB0", 115200)
        >>> if reader.connect():
        ...     reader.read_data(on_data)
    """
    
    # 默认读取超时（秒）
    DEFAULT_TIMEOUT = 1.0
    
    # 数据读取间隔（秒）
    READ_INTERVAL = 0.01
    
    def __init__(
        self, 
        port: str = "/dev/ttyUSB0", 
        baudrate: int = 115200,
        timeout: float = DEFAULT_TIMEOUT
    ):
        """
        初始化串口读取器
        
        Args:
            port: 串口设备路径，如 /dev/ttyUSB0 或 COM3
            baudrate: 波特率，默认 115200
            timeout: 读取超时时间（秒），默认 1.0
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial: Optional[serial.Serial] = None
        self.is_running = False
        self.logger = logging.getLogger(__name__)
        self._serial_lock = threading.RLock()
    
    def __enter__(self) -> "SerialReader":
        """上下文管理器入口"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器出口"""
        self.disconnect()
    
    def connect(self) -> bool:
        """
        连接串口
        
        尝试打开串口连接。如果连接已存在，先断开再重连。
        
        Returns:
            连接是否成功
        
        Raises:
            SerialConnectionError: 连接失败时抛出（如设备不存在或被占用）
        """
        try:
            # 先断开旧连接，避免串口对象在多线程下被并发访问
            self.disconnect()

            serial_obj = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            with self._serial_lock:
                self.serial = serial_obj
            
            self.logger.info(f"串口连接成功: {self.port} @ {self.baudrate}")
            return True
            
        except serial.SerialException as e:
            error_msg = f"串口连接失败: {e}"
            self.logger.error(error_msg)
            raise SerialConnectionError(
                error_msg,
                port=self.port,
                baudrate=self.baudrate
            )
        except Exception as e:
            error_msg = f"串口连接错误: {e}"
            self.logger.error(error_msg)
            return False
    
    def disconnect(self) -> None:
        """
        断开串口连接
        
        安全地关闭串口连接，释放系统资源。
        """
        with self._serial_lock:
            serial_obj = self.serial
            self.serial = None

        if serial_obj and serial_obj.is_open:
            try:
                serial_obj.close()
                self.logger.info(f"串口已断开: {self.port}")
            except Exception as e:
                self.logger.warning(f"断开串口时发生错误: {e}")
    
    def is_connected(self) -> bool:
        """
        检查串口是否已连接
        
        Returns:
            True 如果串口已连接且打开
        """
        with self._serial_lock:
            serial_obj = self.serial
        return serial_obj is not None and serial_obj.is_open
    
    def read_data(self, callback: Callable[[bytes], None]) -> None:
        """
        读取串口数据并通过回调函数传递
        
        这是一个阻塞方法，会持续读取数据直到调用 stop() 方法。
        
        Args:
            callback: 数据回调函数，接收 bytes 类型数据
        
        Raises:
            SerialConnectionError: 串口未连接或读取错误
        """
        if not self.is_connected():
            if not self.connect():
                raise SerialConnectionError(
                    "无法建立串口连接",
                    port=self.port,
                    baudrate=self.baudrate
                )
        
        self.is_running = True
        self.logger.info(f"开始读取串口数据: {self.port}")
        
        try:
            while self.is_running:
                with self._serial_lock:
                    serial_obj = self.serial

                if not serial_obj or not serial_obj.is_open:
                    break

                waiting = serial_obj.in_waiting
                if waiting > 0:
                    data = serial_obj.read(waiting)
                    if data:
                        callback(data)
                else:
                    # 无数据时短暂休眠，避免 CPU 空转
                    time.sleep(self.READ_INTERVAL)
                    
        except serial.SerialException as e:
            if not self.is_running:
                self.logger.debug("串口读取已停止")
                return
            self.logger.error(f"读取串口数据错误: {e}")
            self.is_running = False
            raise SerialConnectionError(
                f"串口读取错误: {e}",
                port=self.port,
                baudrate=self.baudrate
            )
        except Exception as e:
            if self.is_running:
                self.logger.error(f"读取串口数据异常: {e}")
            self.is_running = False
        finally:
            self.is_running = False
    
    def write_data(self, data: bytes) -> bool:
        """
        向串口写入数据
        
        Args:
            data: 要写入的二进制数据
        
        Returns:
            写入是否成功
        """
        if not self.is_connected():
            self.logger.error("串口未连接，无法写入数据")
            return False
        
        with self._serial_lock:
            serial_obj = self.serial

        if not serial_obj or not serial_obj.is_open:
            self.logger.error("串口未连接，无法写入数据")
            return False
        
        try:
            serial_obj.write(data)
            serial_obj.flush()
            return True
        except Exception as e:
            self.logger.error(f"写入串口数据错误: {e}")
            return False
    
    def stop(self) -> None:
        """
        停止数据读取
        
        设置停止标志并断开连接。
        """
        self.logger.info("正在停止串口读取...")
        self.is_running = False
        self.disconnect()
