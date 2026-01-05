"""千寻 MC280M 接收机初始化模块"""
import time
import logging
import serial


class QianxunInitializer:
    """千寻接收机初始化类"""
    
    def __init__(self, serial_port: serial.Serial):
        """
        初始化千寻配置器
        
        Args:
            serial_port: 已打开的串口对象
        """
        self.serial = serial_port
        self.logger = logging.getLogger(__name__)
    
    def send_command(self, command: str, wait_response: bool = True, timeout: float = 2.0) -> bool:
        """
        发送命令到接收机
        
        Args:
            command: NMEA 格式的命令字符串（不含校验和）
            wait_response: 是否等待响应
            timeout: 超时时间（秒）
            
        Returns:
            命令是否发送成功
        """
        try:
            # 计算校验和
            checksum = self._calculate_checksum(command)
            # 构建完整命令：$命令*校验和\r\n
            # full_command = f"${command}*{checksum:02X}\r\n"
            full_command = f"${command}\r\n"
            
            self.logger.debug(f"发送命令: {full_command.strip()}")
            self.serial.write(full_command.encode('utf-8'))
            self.serial.flush()
            
            if wait_response:
                time.sleep(0.1)  # 等待响应
                # 读取响应（简单实现，实际可能需要更复杂的解析）
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if self.serial.in_waiting > 0:
                        response = self.serial.read(self.serial.in_waiting).decode('utf-8', errors='ignore')
                        self.logger.debug(f"收到响应: {response.strip()}")
                        # 检查是否有 ACK 响应（QX 消息通常返回 $QXACK...）
                        if 'QXACK' in response or 'ACK' in response:
                            return True
                        break
                    time.sleep(0.05)
            
            return True
        except Exception as e:
            self.logger.error(f"发送命令失败: {e}")
            return False
    
    def _calculate_checksum(self, command: str) -> int:
        """
        计算 NMEA 校验和
        
        Args:
            command: 命令字符串（不含 $ 和 *）
            
        Returns:
            校验和值
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
        # QXCFGPRT 命令格式：QXCFGPRT,port,reserved,baudrate,...
        # 简化版本，仅设置波特率
        # 注意：实际协议可能需要更多参数，这里使用简化版本
        command = f"QXCFGPRT,1,0,{baudrate},8,1,0"
        self.logger.info(f"配置波特率为 {baudrate}")
        return self.send_command(command)
    
    def configure_rtcm_output(self, rate: int = 1) -> bool:
        """
        配置 RTCM3 消息输出
        
        Args:
            rate: 输出频率（Hz），1 表示 1Hz
            
        Returns:
            配置是否成功
        """
        self.logger.info(f"配置 RTCM3 输出，频率: {rate}Hz")
        
        # 基站默认 RTCM MSM4 消息类型（根据协议文档）
        rtcm_messages = [
            (1005, rate),  # Stationary RTK Reference Station ARP
            (1074, rate),  # GPS MSM4
            (1084, rate),  # GLONASS MSM4
            (1094, rate),  # Galileo MSM4
            (1114, rate),  # QZSS MSM4
            (1124, rate),  # BDS MSM4
        ]
        
        success = True
        for msg_id, msg_rate in rtcm_messages:
            # QXCFGMSG 命令格式：QXCFGMSG,class,id,rate
            # class=5 表示 RTCM3 消息
            command = f"QXCFGMSG,5,{msg_id},{msg_rate}"
            if not self.send_command(command):
                self.logger.warning(f"配置 RTCM 消息 {msg_id} 失败")
                success = False
            time.sleep(0.1)  # 命令间隔
        
        time.sleep(1.0)
        command = "$QXCFGPRT,0,0,,115200,h00000005,h00000004"
        self.send_command(command)

        return success

    def configure_base_station_coordinates(self, latitude: float, longitude: float, altitude: float, enable_arp_average: int = 0) -> bool:
        """
        配置基站坐标 (QXCFGLLH 命令)

        Args:
            latitude: 纬度 (度)
            longitude: 经度 (度)
            altitude: 高程 (米)
            enable_arp_average: 是否启用 ARP 平均模式 (1: 启用, 0: 禁用)

        Returns:
            配置是否成功
        """
        # QXCFGLLH 命令格式：QXCFGLLH,lat,lon,alt,type,height,reserved,reserved,enable
        # type: 0=固定点, 1=移动点
        # height: 0=椭球高, 1=海拔高 (协议通常要求海拔高)
        # 这里简化为固定点，海拔高，不使用保留字段
        # command = f"QXCFGMODE,{latitude},{longitude},{altitude},0,1,0,0,{enable_arp_average}"
        if enable_arp_average == 1:
            command = "$QXCFGMODE,0,1,TW,60,2.5,3.5,10.0"
        else:
            command = f"QXCFGMODE,0,1,,{latitude},{longitude},{altitude},"
        self.logger.info(f"配置基站坐标: {latitude}, {longitude}, {altitude}, ARP 平均: {enable_arp_average}")
        return self.send_command(command)


    def initialize(self, baudrate: int = 115200, rtcm_rate: int = 1, base_station_config: dict = None) -> bool:
        """
        初始化接收机：配置波特率和 RTCM 输出
        
        Args:
            baudrate: 目标波特率
            rtcm_rate: RTCM 输出频率（Hz）
            
        Returns:
            初始化是否成功
        """
        self.logger.info("开始初始化千寻 MC280M 接收机...")
        
        # 1. 配置波特率
        if not self.configure_baudrate(baudrate):
            self.logger.warning("波特率配置可能失败，继续执行...")
        
        time.sleep(0.5)  # 等待配置生效
        
        # 2. 配置基站坐标 (新增)
        if base_station_config:
            lat = base_station_config.get('latitude')
            lon = base_station_config.get('longitude')
            alt = base_station_config.get('altitude')
            arp_avg = base_station_config.get('enable_arp_average')
            if lat is not None and lon is not None and alt is not None:
                if not self.configure_base_station_coordinates(lat, lon, alt, arp_avg):
                    self.logger.error("基站坐标配置失败")
                    return False
                time.sleep(0.5) # 等待配置生效
            else:
                self.logger.warning("基站坐标配置不完整，跳过配置基站坐标。")



        # 2. 配置 RTCM 输出
        if not self.configure_rtcm_output(rtcm_rate):
            self.logger.error("RTCM 输出配置失败")
            return False
        
        time.sleep(0.5)  # 等待配置生效
        
        self.logger.info("千寻 MC280M 接收机初始化完成")
        return True

