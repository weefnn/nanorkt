"""
千寻 MC280M 接收机驱动模块

本模块提供千寻 MC280M GNSS 接收机的初始化和配置功能。
支持配置波特率、RTCM 输出和基站坐标。

千寻 MC280M 特性：
- 支持 GPS/GLONASS/Galileo/BDS 多星座
- 支持 RTCM3.2 输出
- 支持基站模式（固定坐标或 ARP 平均）
- 使用 QX 私有 NMEA 命令配置

命令格式：
- 所有命令以 "$" 开头
- 命令格式：$命令名,参数1,参数2,...
- 部分命令返回 $QXACK 确认

使用方法：
    >>> from app.drivers import QianxunInitializer
    >>> 
    >>> # 需要先建立串口连接
    >>> import serial
    >>> ser = serial.Serial("/dev/ttyUSB0", 115200)
    >>> 
    >>> initializer = QianxunInitializer(ser)
    >>> initializer.initialize(baudrate=115200, rtcm_rate=1)
"""

import logging
import time
from typing import Optional

import serial

from app.core.exceptions import ReceiverInitError


class QianxunInitializer:
    """
    千寻 MC280M 接收机初始化类
    
    用于配置千寻 GNSS 接收机的各项参数。
    
    Attributes:
        serial: pyserial Serial 对象
    
    Example:
        >>> ser = serial.Serial("/dev/ttyUSB0", 115200)
        >>> init = QianxunInitializer(ser)
        >>> init.initialize(
        ...     baudrate=115200,
        ...     rtcm_rate=1,
        ...     base_station_config={
        ...         "latitude": 39.9,
        ...         "longitude": 116.4,
        ...         "altitude": 50.0,
        ...         "enable_arp_average": 0
        ...     }
        ... )
    """
    
    # 命令响应超时（秒）
    COMMAND_TIMEOUT = 2.0
    
    # 命令间隔（秒）
    COMMAND_INTERVAL = 0.1
    
    # 配置生效等待时间（秒）
    CONFIG_WAIT_TIME = 0.5
    
    # 标准 RTCM MSM4 消息类型
    RTCM_MESSAGES = [
        (1005, "RTK Reference Station ARP"),       # 基站坐标
        (1074, "GPS MSM4"),                        # GPS 观测数据
        (1084, "GLONASS MSM4"),                    # GLONASS 观测数据
        (1094, "Galileo MSM4"),                    # Galileo 观测数据
        (1114, "QZSS MSM4"),                       # QZSS 观测数据
        (1124, "BDS MSM4"),                        # 北斗观测数据
    ]
    
    def __init__(self, serial_port: serial.Serial):
        """
        初始化千寻配置器
        
        Args:
            serial_port: 已打开的串口对象
        """
        self.serial = serial_port
        self.logger = logging.getLogger(__name__)
    
    def send_command(
        self, 
        command: str, 
        wait_response: bool = True,
        timeout: float = COMMAND_TIMEOUT
    ) -> bool:
        """
        发送命令到接收机
        
        Args:
            command: NMEA 格式的命令字符串（不含 $ 前缀，除非已包含）
            wait_response: 是否等待响应
            timeout: 超时时间（秒）
        
        Returns:
            命令是否发送成功
        
        Raises:
            ReceiverInitError: 命令发送失败
        """
        try:
            # 构建完整命令
            if not command.startswith("$"):
                full_command = f"${command}\r\n"
            else:
                full_command = f"{command}\r\n"
            
            self.logger.debug(f"发送命令: {full_command.strip()}")
            self.serial.write(full_command.encode("utf-8"))
            self.serial.flush()
            
            if wait_response:
                return self._wait_for_response(timeout)
            
            return True
            
        except serial.SerialException as e:
            raise ReceiverInitError(
                f"命令发送失败: {e}",
                command=command,
                receiver_type="MC280M"
            )
        except Exception as e:
            self.logger.error(f"发送命令异常: {e}")
            return False
    
    def _wait_for_response(self, timeout: float) -> bool:
        """
        等待接收机响应
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            是否收到有效响应
        """
        time.sleep(0.1)  # 短暂等待响应
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.serial.in_waiting > 0:
                response = self.serial.read(self.serial.in_waiting).decode(
                    "utf-8", errors="ignore"
                )
                self.logger.debug(f"收到响应: {response.strip()}")
                
                # 检查 ACK 响应
                if "QXACK" in response or "ACK" in response:
                    return True
                break
            time.sleep(0.05)
        
        return True  # 即使没有 ACK，也认为命令已发送
    
    def _calculate_checksum(self, command: str) -> int:
        """
        计算 NMEA 校验和
        
        Args:
            command: 命令字符串（不含 $ 和 *）
        
        Returns:
            校验和值（0-255）
        """
        checksum = 0
        for char in command:
            checksum ^= ord(char)
        return checksum
    
    def configure_baudrate(self, baudrate: int = 115200) -> bool:
        """
        配置串口波特率
        
        Args:
            baudrate: 目标波特率
        
        Returns:
            配置是否成功
        """
        self.logger.info(f"配置波特率: {baudrate}")
        
        # QXCFGPRT 命令格式：QXCFGPRT,port,reserved,baudrate,databits,stopbits,parity
        command = f"QXCFGPRT,1,0,{baudrate},8,1,0"
        return self.send_command(command)
    
    def configure_rtcm_output(self, rate: int = 1, baudrate: int = 115200) -> bool:
        """
        配置 RTCM3 消息输出
        
        Args:
            rate: 输出频率（Hz），1 表示 1Hz
            baudrate: 串口波特率，需与接收机当前端口配置一致
        
        Returns:
            配置是否成功
        """
        self.logger.info(f"配置 RTCM3 输出，频率: {rate}Hz")
        
        success = True
        for msg_id, msg_name in self.RTCM_MESSAGES:
            # QXCFGMSG 命令格式：QXCFGMSG,class,id,rate
            # class=5 表示 RTCM3 消息
            command = f"QXCFGMSG,5,{msg_id},{rate}"
            
            if not self.send_command(command):
                self.logger.warning(f"配置 RTCM 消息失败: {msg_id} ({msg_name})")
                success = False
            
            time.sleep(self.COMMAND_INTERVAL)
        
        # 配置端口输出格式
        time.sleep(1.0)
        # 必须使用当前工作波特率，避免与上一步配置不一致导致串口失联
        port_cmd = f"QXCFGPRT,0,0,,{baudrate},h00000005,h00000004"
        self.send_command(port_cmd)
        
        return success
    
    def configure_base_station_coordinates(
        self, 
        latitude: float, 
        longitude: float, 
        altitude: float,
        enable_arp_average: int = 0
    ) -> bool:
        """
        配置基站坐标
        
        Args:
            latitude: 纬度（度）
            longitude: 经度（度）
            altitude: 海拔高度（米）
            enable_arp_average: 是否启用 ARP 平均模式（0=否, 1=是）
        
        Returns:
            配置是否成功
        
        Note:
            - enable_arp_average=0: 使用固定坐标
            - enable_arp_average=1: 使用 ARP 平均模式自动计算坐标
        """
        if enable_arp_average == 1:
            # ARP 平均模式
            command = "QXCFGMODE,0,1,TW,60,2.5,3.5,10.0"
            self.logger.info("配置基站模式: ARP 平均")
        else:
            # 固定坐标模式
            command = f"QXCFGMODE,0,1,,{latitude},{longitude},{altitude},"
            self.logger.info(
                f"配置基站坐标: lat={latitude}, lon={longitude}, alt={altitude}"
            )
        
        return self.send_command(command)
    
    def initialize(
        self, 
        baudrate: int = 115200, 
        rtcm_rate: int = 1,
        base_station_config: Optional[dict] = None
    ) -> bool:
        """
        完整初始化接收机
        
        按顺序执行：波特率配置、基站坐标配置、RTCM 输出配置。
        
        Args:
            baudrate: 目标波特率
            rtcm_rate: RTCM 输出频率（Hz）
            base_station_config: 基站配置字典，包含 latitude, longitude, 
                                 altitude, enable_arp_average
        
        Returns:
            初始化是否完全成功
        
        Example:
            >>> init.initialize(
            ...     baudrate=115200,
            ...     rtcm_rate=1,
            ...     base_station_config={
            ...         "latitude": 39.9,
            ...         "longitude": 116.4,
            ...         "altitude": 50.0,
            ...         "enable_arp_average": 0
            ...     }
            ... )
        """
        self.logger.info("开始初始化千寻 MC280M 接收机...")
        
        # 1. 配置波特率
        if not self.configure_baudrate(baudrate):
            self.logger.warning("波特率配置可能失败，继续执行...")
        
        time.sleep(self.CONFIG_WAIT_TIME)
        
        # 2. 配置基站坐标
        if base_station_config:
            lat = base_station_config.get("latitude")
            lon = base_station_config.get("longitude")
            alt = base_station_config.get("altitude")
            arp_avg = base_station_config.get("enable_arp_average", 0)
            
            if lat is not None and lon is not None and alt is not None:
                if not self.configure_base_station_coordinates(lat, lon, alt, arp_avg):
                    self.logger.error("基站坐标配置失败")
                    return False
                time.sleep(self.CONFIG_WAIT_TIME)
            else:
                self.logger.warning("基站坐标配置不完整，跳过")
        
        # 3. 配置 RTCM 输出
        if not self.configure_rtcm_output(rtcm_rate, baudrate):
            self.logger.error("RTCM 输出配置失败")
            return False
        
        time.sleep(self.CONFIG_WAIT_TIME)
        
        self.logger.info("千寻 MC280M 接收机初始化完成")
        return True
    
    def reset(self) -> bool:
        """
        重置接收机到出厂设置
        
        Returns:
            重置是否成功
        
        Warning:
            此操作会清除所有配置！
        """
        self.logger.warning("正在重置接收机到出厂设置...")
        return self.send_command("QXRESET")
