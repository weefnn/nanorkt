"""NTRIP 客户端模块"""
import socket
import logging
import base64
import time
from typing import Optional


class NTRIPClient:
    """NTRIP Caster 客户端"""
    
    def __init__(self, host: str, port: int, mountpoint: str, 
                 username: str = '', password: str = ''):
        """
        初始化 NTRIP 客户端
        
        Args:
            host: NTRIP Caster 主机地址
            port: NTRIP Caster 端口
            mountpoint: 挂载点名称
            username: 用户名（可选）
            password: 密码（可选）
        """
        self.host = host
        self.port = port
        self.mountpoint = mountpoint
        self.username = username
        self.password = password
        self.socket: Optional[socket.socket] = None
        self.is_connected = False
        self.logger = logging.getLogger(__name__)
    
    def connect(self) -> bool:
        """
        连接到 NTRIP Caster
        
        Returns:
            连接是否成功
        """
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            
            # 构建 NTRIP 请求
            request = self._build_request()
            self.socket.sendall(request.encode('utf-8'))
            
            # 接收响应
            response = self.socket.recv(1024).decode('utf-8')
            
            if 'ICY 200 OK' in response or '200 OK' in response:
                self.is_connected = True
                self.logger.info(f"NTRIP 连接成功: {self.host}:{self.port}/{self.mountpoint}")
                return True
            else:
                self.logger.error(f"NTRIP 连接失败: {response}")
                self.disconnect()
                return False
                
        except Exception as e:
            self.logger.error(f"NTRIP 连接错误: {e}")
            self.disconnect()
            return False
    
    def _build_request(self) -> str:
        """构建 NTRIP 请求字符串"""
        auth = ''
        if self.username and self.password:
            credentials = f"{self.username}:{self.password}"
            auth = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            auth = f"Authorization: Basic {auth}\r\n"
        
        request = (
            f"SOURCE {self.password} /{self.mountpoint}\r\n"
            f"Source-Agent: NTRIP Client\r\n"
            f"\r\n"
            f"User-Agent: NTRIP Client\r\n"
            f"{auth}"
            f"Accept: */*\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        )
        return request
    
    def send_data(self, data: bytes) -> bool:
        """
        发送数据到 NTRIP Caster
        
        Args:
            data: 要发送的二进制数据
            
        Returns:
            发送是否成功
        """
        if not self.is_connected or not self.socket:
            return False
        
        try:
            self.socket.sendall(data)
            return True
        except Exception as e:
            self.logger.error(f"发送数据错误: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.is_connected = False
        self.logger.info("NTRIP 连接已断开")
    
    def reconnect(self, max_retries: int = 5, retry_delay: float = 5.0) -> bool:
        """
        重连 NTRIP Caster
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            
        Returns:
            重连是否成功
        """
        self.disconnect()
        
        for attempt in range(max_retries):
            self.logger.info(f"尝试重连 ({attempt + 1}/{max_retries})...")
            if self.connect():
                return True
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
        
        return False

