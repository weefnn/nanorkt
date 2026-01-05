"""主程序"""
import logging
import signal
import sys
from serial_reader import SerialReader
from ntrip_client import NTRIPClient
from config import Config
from qianxun_init import QianxunInitializer


class RTKBaseStation:
    """RTK 基站主类"""
    
    def __init__(self):
        """初始化 RTK 基站"""
        self.setup_logging()
        self.config = Config()
        self.serial_reader: SerialReader = None
        self.ntrip_client: NTRIPClient = None
        self.is_running = False
        self.logger = logging.getLogger(__name__)
    
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def setup_serial(self):
        """设置串口"""
        serial_config = self.config.get_serial_config()
        self.serial_reader = SerialReader(
            port=serial_config['port'],
            baudrate=serial_config['baudrate']
        )
    
    def setup_ntrip(self):
        """设置 NTRIP 客户端"""
        ntrip_config = self.config.get_ntrip_config()
        self.ntrip_client = NTRIPClient(
            host=ntrip_config['host'],
            port=ntrip_config['port'],
            mountpoint=ntrip_config['mountpoint'],
            username=ntrip_config['username'],
            password=ntrip_config['password']
        )
    
    def on_serial_data(self, data: bytes):
        """
        串口数据回调
        
        Args:
            data: 串口读取的二进制数据
        """
        if not self.ntrip_client:
            return
        
        # 发送数据到 NTRIP
        if not self.ntrip_client.send_data(data):
            # 发送失败，尝试重连
            self.logger.warning("NTRIP 发送失败，尝试重连...")
            reconnect_config = self.config.get_reconnect_config()
            if self.ntrip_client.reconnect(
                max_retries=reconnect_config['max_retries'],
                retry_delay=reconnect_config['retry_delay']
            ):
                # 重连成功后重试发送
                self.ntrip_client.send_data(data)
            else:
                self.logger.error("NTRIP 重连失败")
    
    def start(self):
        """启动服务"""
        self.logger.info("启动 RTK 基站服务...")
        
        # 设置串口
        self.setup_serial()
        if not self.serial_reader.connect():
            self.logger.error("串口连接失败，退出")
            return False
        
        # 初始化千寻接收机
        self.logger.info("初始化千寻 MC280M 接收机...")
        initializer = QianxunInitializer(self.serial_reader.serial)
        serial_config = self.config.get_serial_config()
        base_station_config = self.config.get_base_station_config() # 新增：获取基站坐标配置

        if not initializer.initialize(
            baudrate=serial_config['baudrate'],
            rtcm_rate=1,  # 1Hz 输出频率
            base_station_config=base_station_config
        ):
            self.logger.warning("接收机初始化可能未完全成功，继续运行...")
        
        # 设置 NTRIP 客户端
        self.setup_ntrip()
        reconnect_config = self.config.get_reconnect_config()
        if not self.ntrip_client.connect():
            self.logger.warning("NTRIP 初始连接失败，尝试重连...")
            if not self.ntrip_client.reconnect(
                max_retries=reconnect_config['max_retries'],
                retry_delay=reconnect_config['retry_delay']
            ):
                self.logger.error("NTRIP 连接失败，退出")
                self.serial_reader.disconnect()
                return False
        
        self.is_running = True
        self.logger.info("RTK 基站服务已启动")
        
        # 开始读取串口数据
        try:
            self.serial_reader.read_data(self.on_serial_data)
        except KeyboardInterrupt:
            self.logger.info("收到中断信号，正在停止...")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """停止服务"""
        self.logger.info("停止 RTK 基站服务...")
        self.is_running = False
        
        if self.serial_reader:
            self.serial_reader.stop()
        
        if self.ntrip_client:
            self.ntrip_client.disconnect()
        
        self.logger.info("RTK 基站服务已停止")


def signal_handler(sig, frame):
    """信号处理"""
    sys.exit(0)


def main():
    """主函数"""
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 创建并启动服务
    station = RTKBaseStation()
    station.start()


if __name__ == '__main__':
    main()

