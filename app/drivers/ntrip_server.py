"""
NTRIP Server 模块

本模块提供 NTRIP Server 功能，用于将 RTK 基站的 RTCM 数据上传到 NTRIP Caster 服务器。
支持自动重连和连接状态监控。

NTRIP 协议角色说明：
- NTRIP Server：基站角色，向 Caster 推送 RTCM 数据（本模块实现）
- NTRIP Client：移动站角色，从 Caster 拉取 RTCM 数据
- NTRIP Caster：中心服务器，接收 Server 数据并分发给 Client

本模块实现 NTRIP Server（SOURCE 模式），用于基站上传差分数据。

功能特性：
- 自动重连机制
- 连接状态枚举
- 数据发送统计
- 心跳检测（可选）

使用方法：
    >>> from app.drivers import NTRIPServer
    >>> 
    >>> server = NTRIPServer(
    ...     host="ntrip.example.com",
    ...     port=2101,
    ...     mountpoint="RTCM32",
    ...     username="user",
    ...     password="pass"
    ... )
    >>> 
    >>> if server.connect():
    ...     server.send_data(rtcm_bytes)
    ...     server.disconnect()
"""

import base64
import logging
import socket
import time
from enum import Enum
from typing import Optional

from app.core.exceptions import NTRIPConnectionError


class ConnectionState(Enum):
    """
    连接状态枚举
    
    表示 NTRIP Server 的当前连接状态。
    """
    DISCONNECTED = "disconnected"  # 已断开
    CONNECTING = "connecting"      # 正在连接
    CONNECTED = "connected"        # 已连接
    RECONNECTING = "reconnecting"  # 正在重连
    ERROR = "error"                # 错误状态


class NTRIPServer:
    """
    NTRIP Server（基站端）
    
    实现 NTRIP 协议的 SOURCE 模式，将基站的 RTCM 数据上传到 NTRIP Caster。
    
    注意：在 NTRIP 协议中，基站向 Caster 推送数据的角色称为 "NTRIP Server"，
    而不是 "Client"。移动站从 Caster 拉取数据的角色才是 "NTRIP Client"。
    
    Attributes:
        host: NTRIP Caster 服务器地址
        port: NTRIP Caster 端口
        mountpoint: 挂载点名称
        username: 认证用户名
        password: 认证密码
        state: 当前连接状态
    
    Example:
        >>> server = NTRIPServer("ntrip.example.com", 2101, "RTCM32", "user", "pass")
        >>> try:
        ...     server.connect()
        ...     server.send_data(data)
        ... finally:
        ...     server.disconnect()
    """
    
    # 默认连接超时（秒）
    DEFAULT_TIMEOUT = 10
    
    # 默认 Socket 缓冲区大小
    BUFFER_SIZE = 4096
    
    def __init__(
        self, 
        host: str, 
        port: int, 
        mountpoint: str,
        username: str = "", 
        password: str = ""
    ):
        """
        初始化 NTRIP Server
        
        Args:
            host: NTRIP Caster 服务器地址
            port: NTRIP Caster 端口，默认 2101
            mountpoint: 挂载点名称
            username: 认证用户名（可选）
            password: 认证密码（可选）
        """
        self.host = host
        self.port = port
        self.mountpoint = mountpoint
        self.username = username
        self.password = password
        
        self._socket: Optional[socket.socket] = None
        self._state = ConnectionState.DISCONNECTED
        self._bytes_sent = 0
        self._last_send_time: Optional[float] = None
        
        self.logger = logging.getLogger(__name__)
    
    @property
    def state(self) -> ConnectionState:
        """获取当前连接状态"""
        return self._state
    
    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._state == ConnectionState.CONNECTED
    
    @property
    def bytes_sent(self) -> int:
        """获取已发送的字节数"""
        return self._bytes_sent
    
    def connect(self, timeout: float = DEFAULT_TIMEOUT) -> bool:
        """
        连接到 NTRIP Caster
        
        建立 TCP 连接并发送 NTRIP SOURCE 请求。
        
        Args:
            timeout: 连接超时时间（秒）
        
        Returns:
            连接是否成功
        
        Raises:
            NTRIPConnectionError: 连接失败时抛出
        """
        self._state = ConnectionState.CONNECTING
        
        try:
            # 创建 socket
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(timeout)
            
            # 连接服务器
            self.logger.info(f"正在连接 NTRIP Caster: {self.host}:{self.port}")
            self._socket.connect((self.host, self.port))
            
            # 发送 NTRIP SOURCE 请求（基站上传模式）
            request = self._build_source_request()
            self._socket.sendall(request.encode("utf-8"))
            
            # 接收响应
            response = self._socket.recv(self.BUFFER_SIZE).decode("utf-8")
            
            # 验证响应
            if "ICY 200 OK" in response or "200 OK" in response:
                self._state = ConnectionState.CONNECTED
                self._bytes_sent = 0
                self.logger.info(
                    f"NTRIP Server 连接成功: {self.host}:{self.port}/{self.mountpoint}"
                )
                return True
            else:
                self._state = ConnectionState.ERROR
                self.logger.error(f"NTRIP 连接被拒绝: {response.strip()}")
                self.disconnect()
                return False
                
        except socket.timeout:
            self._state = ConnectionState.ERROR
            error_msg = f"NTRIP 连接超时: {self.host}:{self.port}"
            self.logger.error(error_msg)
            self.disconnect()
            raise NTRIPConnectionError(
                error_msg,
                host=self.host,
                port=self.port,
                mountpoint=self.mountpoint
            )
        except socket.error as e:
            self._state = ConnectionState.ERROR
            error_msg = f"NTRIP 连接错误: {e}"
            self.logger.error(error_msg)
            self.disconnect()
            raise NTRIPConnectionError(
                error_msg,
                host=self.host,
                port=self.port,
                mountpoint=self.mountpoint
            )
        except Exception as e:
            self._state = ConnectionState.ERROR
            self.logger.error(f"NTRIP 连接异常: {e}")
            self.disconnect()
            return False
    
    def _build_source_request(self) -> str:
        """
        构建 NTRIP SOURCE 请求
        
        SOURCE 请求用于基站向 Caster 推送数据，格式为：
        SOURCE <password> /<mountpoint>
        
        Returns:
            NTRIP SOURCE 请求字符串
        """
        # 构建认证头
        auth_header = ""
        if self.username and self.password:
            credentials = f"{self.username}:{self.password}"
            auth_b64 = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
            auth_header = f"Authorization: Basic {auth_b64}\r\n"
        
        # 构建 SOURCE 请求
        # 注意：SOURCE 请求的密码直接在请求行中
        request = (
            f"SOURCE {self.password} /{self.mountpoint}\r\n"
            f"Source-Agent: NanoRTK/2.0\r\n"
            f"\r\n"
            f"User-Agent: NanoRTK/2.0\r\n"
            f"{auth_header}"
            f"Accept: */*\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        )
        return request
    
    def send_data(self, data: bytes) -> bool:
        """
        发送 RTCM 数据到 NTRIP Caster
        
        Args:
            data: 要发送的 RTCM 二进制数据
        
        Returns:
            发送是否成功
        """
        if not self.is_connected or not self._socket:
            self.logger.warning("NTRIP Server 未连接，无法发送数据")
            return False
        
        try:
            self._socket.sendall(data)
            self._bytes_sent += len(data)
            self._last_send_time = time.time()
            return True
        except socket.error as e:
            self.logger.error(f"NTRIP 发送数据错误: {e}")
            self._state = ConnectionState.ERROR
            return False
        except Exception as e:
            self.logger.error(f"NTRIP 发送数据异常: {e}")
            self._state = ConnectionState.ERROR
            return False
    
    def disconnect(self) -> None:
        """
        断开 NTRIP 连接
        
        安全地关闭 socket 连接。
        """
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            finally:
                self._socket = None
        
        self._state = ConnectionState.DISCONNECTED
        self.logger.info("NTRIP Server 连接已断开")
    
    def reconnect(
        self, 
        max_retries: int = 5, 
        retry_delay: float = 5.0
    ) -> bool:
        """
        重连 NTRIP Caster
        
        尝试重新建立连接，支持多次重试。
        
        Args:
            max_retries: 最大重试次数
            retry_delay: 重试间隔（秒）
        
        Returns:
            重连是否成功
        """
        self._state = ConnectionState.RECONNECTING
        self.disconnect()
        
        for attempt in range(max_retries):
            self.logger.info(f"NTRIP Server 重连尝试 ({attempt + 1}/{max_retries})...")
            
            try:
                if self.connect():
                    return True
            except NTRIPConnectionError:
                pass  # 继续重试
            
            if attempt < max_retries - 1:
                self.logger.info(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
        
        self._state = ConnectionState.ERROR
        self.logger.error(f"NTRIP Server 重连失败，已达最大重试次数: {max_retries}")
        return False
    
    def get_stats(self) -> dict:
        """
        获取连接统计信息
        
        Returns:
            包含连接状态和发送统计的字典
        """
        return {
            "state": self._state.value,
            "host": self.host,
            "port": self.port,
            "mountpoint": self.mountpoint,
            "bytes_sent": self._bytes_sent,
            "last_send_time": self._last_send_time,
        }
