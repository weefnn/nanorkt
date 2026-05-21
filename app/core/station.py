"""
RTK 基站主类模块

本模块包含 RTK 基站的核心业务逻辑，负责协调串口读取、
接收机初始化和 NTRIP 数据上传。

功能特性：
- 串口数据读取与转发
- NTRIP Caster 连接管理
- 自动重连机制
- 信号处理

使用方法：
    >>> from app.core import RTKBaseStation
    >>> 
    >>> station = RTKBaseStation()
    >>> station.start()  # 阻塞运行
    >>> # 或使用 Ctrl+C 停止
"""

import logging
import signal
import sys
from typing import Optional

from app.core.config import Config
from app.core.logging_config import setup_logging
from app.core.exceptions import (
    NanoRTKError,
    SerialConnectionError,
    NTRIPConnectionError,
)
from app.drivers import SerialReader, NTRIPServer, QianxunInitializer


class RTKBaseStation:
    """
    RTK 基站主类
    
    负责管理 RTK 基站的完整生命周期，包括：
    - 配置加载
    - 串口连接和数据读取
    - 接收机初始化
    - NTRIP 数据上传
    - 错误处理和重连
    
    Attributes:
        config: 配置管理器
        serial_reader: 串口读取器
        ntrip_server: NTRIP Server（基站端）
        is_running: 服务运行状态
    
    Example:
        >>> station = RTKBaseStation()
        >>> try:
        ...     station.start()
        ... except KeyboardInterrupt:
        ...     station.stop()
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化 RTK 基站
        
        Args:
            config_path: 配置文件路径
        """
        # 设置日志
        # setup_logging()  # 移至 main() 中调用，避免 Web 模式下重置日志配置
        
        self.logger = logging.getLogger(__name__)
        self.config = Config(config_path)
        
        self.serial_reader: Optional[SerialReader] = None
        self.ntrip_server: Optional[NTRIPServer] = None
        self.is_running = False
        
        # 统计信息
        self._bytes_received = 0
        self._bytes_sent = 0
    
    def setup_serial(self) -> bool:
        """
        设置串口连接
        
        Returns:
            设置是否成功
        """
        serial_config = self.config.get_serial_config()
        self.serial_reader = SerialReader(
            port=serial_config.port,
            baudrate=serial_config.baudrate
        )
        
        try:
            return self.serial_reader.connect()
        except SerialConnectionError as e:
            self.logger.error(f"串口设置失败: {e}")
            return False
    
    def setup_ntrip(self) -> bool:
        """
        设置 NTRIP Server
        
        Returns:
            设置是否成功
        """
        ntrip_config = self.config.get_ntrip_config()
        self.ntrip_server = NTRIPServer(
            host=ntrip_config.host,
            port=ntrip_config.port,
            mountpoint=ntrip_config.mountpoint,
            username=ntrip_config.username,
            password=ntrip_config.password
        )
        
        try:
            return self.ntrip_server.connect()
        except NTRIPConnectionError as e:
            self.logger.error(f"NTRIP Server 设置失败: {e}")
            return False
    
    def initialize_receiver(self) -> bool:
        """
        初始化 GNSS 接收机
        
        Returns:
            初始化是否成功
        """
        if not self.serial_reader or not self.serial_reader.serial:
            self.logger.error("串口未连接，无法初始化接收机")
            return False
        
        self.logger.info("初始化千寻 MC280M 接收机...")
        
        initializer = QianxunInitializer(self.serial_reader.serial)
        serial_config = self.config.get_serial_config()
        base_station_config = self.config.get_base_station_config()
        
        # 将 Pydantic 模型转换为字典
        bs_dict = {
            "latitude": base_station_config.latitude,
            "longitude": base_station_config.longitude,
            "altitude": base_station_config.altitude,
            "enable_arp_average": base_station_config.enable_arp_average,
        }
        
        return initializer.initialize(
            baudrate=serial_config.baudrate,
            rtcm_rate=1,
            base_station_config=bs_dict
        )
    
    def on_serial_data(self, data: bytes) -> None:
        """
        串口数据回调处理
        
        接收到串口数据后，转发到 NTRIP Caster。
        
        Args:
            data: 从串口读取的二进制数据
        """
        self._bytes_received += len(data)
        
        if not self.ntrip_server:
            return
        
        # 发送数据到 NTRIP
        if self.ntrip_server.send_data(data):
            self._bytes_sent += len(data)
        else:
            # 发送失败，尝试重连
            self.logger.warning("NTRIP 发送失败，尝试重连...")
            reconnect_config = self.config.get_reconnect_config()
            
            if self.ntrip_server.reconnect(
                max_retries=reconnect_config.max_retries,
                retry_delay=reconnect_config.retry_delay
            ):
                # 重连成功后重试发送
                self.ntrip_server.send_data(data)
            else:
                self.logger.error("NTRIP 重连失败")
    
    def start(self) -> bool:
        """
        启动 RTK 基站服务
        
        这是一个阻塞方法，会持续运行直到调用 stop() 或收到中断信号。
        
        Returns:
            服务是否正常启动
        """
        self.logger.info("启动 RTK 基站服务...")
        
        try:
            # 1. 设置串口
            if not self.setup_serial():
                self.logger.error("串口连接失败，退出")
                return False
            
            # 2. 初始化接收机
            if not self.initialize_receiver():
                self.logger.warning("接收机初始化可能未完全成功，继续运行...")
            
            # 3. 设置 NTRIP 客户端
            if not self.setup_ntrip():
                self.logger.warning("NTRIP 初始连接失败，尝试重连...")
                reconnect_config = self.config.get_reconnect_config()
                
                if not self.ntrip_server.reconnect(
                    max_retries=reconnect_config.max_retries,
                    retry_delay=reconnect_config.retry_delay
                ):
                    self.logger.error("NTRIP 连接失败，退出")
                    return False
            
            self.is_running = True
            self.logger.info("RTK 基站服务已启动")
            
            # 4. 开始读取串口数据
            self.serial_reader.read_data(self.on_serial_data)
            return True
        except KeyboardInterrupt:
            self.logger.info("收到中断信号，正在停止...")
            return True
        except NanoRTKError as e:
            self.logger.error(f"RTK 服务错误: {e}")
            return False
        except Exception as e:
            self.logger.error(f"RTK 服务异常: {e}")
            return False
        finally:
            self.stop()
    
    def stop(self) -> None:
        """
        停止 RTK 基站服务
        
        安全地停止所有组件并释放资源。
        """
        self.logger.info("停止 RTK 基站服务...")
        self.is_running = False
        
        if self.serial_reader:
            self.serial_reader.stop()
        
        if self.ntrip_server:
            self.ntrip_server.disconnect()
        
        self.logger.info("RTK 基站服务已停止")
        self.logger.info(
            f"统计: 接收 {self._bytes_received} 字节, 发送 {self._bytes_sent} 字节"
        )
    
    def get_status(self) -> dict:
        """
        获取服务状态
        
        Returns:
            包含服务状态信息的字典
        """
        return {
            "is_running": self.is_running,
            "bytes_received": self._bytes_received,
            "bytes_sent": self._bytes_sent,
            "serial_connected": (
                self.serial_reader.is_connected() if self.serial_reader else False
            ),
            "ntrip_connected": (
                self.ntrip_server.is_connected if self.ntrip_server else False
            ),
            "ntrip_stats": (
                self.ntrip_server.get_stats() if self.ntrip_server else None
            ),
        }


def _signal_handler(sig, frame):
    """信号处理函数"""
    sys.exit(0)


def main():
    """
    RTK 基站命令行入口
    
    直接运行基站服务，用于独立部署模式。
    """
    # 注册信号处理
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    
    # 配置日志
    setup_logging(level="INFO")

    # 创建并启动服务
    station = RTKBaseStation()
    station.start()


if __name__ == "__main__":
    main()
