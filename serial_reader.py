"""串口读取模块"""
import serial
import logging
from typing import Optional, Callable


class SerialReader:
    """串口数据读取类"""
    
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 115200):
        """
        初始化串口读取器
        
        Args:
            port: 串口设备路径
            baudrate: 波特率
        """
        self.port = port
        self.baudrate = baudrate
        self.serial: Optional[serial.Serial] = None
        self.is_running = False
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> bool:
        """
        连接串口
        
        Returns:
            连接是否成功
        """
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=1
            )
            self.logger.info(f"串口连接成功: {self.port} @ {self.baudrate}")
            return True
        except Exception as e:
            self.logger.error(f"串口连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开串口连接"""
        if self.serial and self.serial.is_open:
            self.serial.close()
            self.logger.info("串口已断开")
    
    def read_data(self, callback: Callable[[bytes], None]):
        """
        读取串口数据并回调
        
        Args:
            callback: 数据回调函数，接收 bytes 类型数据
        """
        if not self.serial or not self.serial.is_open:
            if not self.connect():
                return
        
        self.is_running = True
        self.logger.info("开始读取串口数据")
        
        try:
            while self.is_running:
                if self.serial.in_waiting > 0:
                    data = self.serial.read(self.serial.in_waiting)
                    if data:
                        callback(data)
        except Exception as e:
            self.logger.error(f"读取串口数据错误: {e}")
            self.is_running = False
        finally:
            self.is_running = False
    
    def stop(self):
        """停止读取"""
        self.is_running = False
        self.disconnect()

