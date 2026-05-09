"""
RTK 服务管理器模块

本模块提供 RTK 基站服务的管理功能，包括启动、停止和状态监控。
使用单例模式确保全局只有一个服务实例。

功能特性：
- 服务生命周期管理
- 线程安全的启动/停止
- 状态查询接口

使用方法：
    >>> from app.web.services import get_manager
    >>> 
    >>> manager = get_manager()
    >>> manager.start_service()
    >>> print(manager.is_running())
    >>> manager.stop_service()
"""

import logging
import threading
from typing import Optional

from app.core.station import RTKBaseStation


# 全局管理器实例（单例）
_manager: Optional["RTKManager"] = None
_lock = threading.Lock()


class RTKManager:
    """
    RTK 基站服务管理器
    
    采用单例模式，管理 RTK 基站服务的生命周期。
    服务在独立线程中运行，不阻塞主线程。
    
    Attributes:
        station: RTK 基站实例
        thread: 服务运行线程
    
    Example:
        >>> manager = get_manager()
        >>> manager.start_service()
        >>> # ... 服务运行中 ...
        >>> manager.stop_service()
    
    Note:
        请使用 get_manager() 函数获取管理器实例，而不是直接实例化。
    """
    
    # 线程停止超时（秒）
    STOP_TIMEOUT = 5.0
    
    def __init__(self):
        """
        初始化管理器
        
        Note:
            不建议直接调用，请使用 get_manager() 获取实例。
        """
        self.station: Optional[RTKBaseStation] = None
        self.thread: Optional[threading.Thread] = None
        self._running = False
        self._run_token = 0
        self._state_lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
    
    def start_service(self) -> bool:
        """
        启动 RTK 服务
        
        在后台线程中启动 RTK 基站服务。
        如果服务已在运行，则忽略此调用。
        
        Returns:
            启动是否成功发起（不代表服务已完全启动）
        """
        with self._state_lock:
            if self._running:
                self.logger.warning("服务已在运行中")
                return False
            
            station = RTKBaseStation()
            self._run_token += 1
            run_token = self._run_token
            
            thread = threading.Thread(
                target=self._run_station,
                args=(run_token, station),
                name="RTKStationThread",
                daemon=True
            )
            
            self.station = station
            self.thread = thread
            self._running = True
        
        try:
            thread.start()
        except Exception as e:
            self.logger.error(f"启动服务线程失败: {e}")
            with self._state_lock:
                if self._run_token == run_token:
                    self._running = False
                    self.station = None
                    self.thread = None
            return False
        
        self.logger.info("RTK 服务启动请求已发送")
        return True
    
    def _run_station(self, run_token: int, station: RTKBaseStation) -> None:
        """
        在线程中运行 RTK 基站
        
        这是内部方法，不应直接调用。
        """
        try:
            station.start()
        except Exception as e:
            self.logger.error(f"RTK 服务运行异常: {e}")
        finally:
            with self._state_lock:
                if self._run_token == run_token:
                    self._running = False
                    self.station = None
                    self.thread = None
    
    def stop_service(self) -> bool:
        """
        停止 RTK 服务
        
        安全地停止服务并等待线程结束。
        
        Returns:
            停止是否成功
        """
        with self._state_lock:
            if not self._running:
                self.logger.warning("服务未在运行")
                return False
            
            station = self.station
            thread = self.thread
            run_token = self._run_token
        
        if station:
            station.stop()
        
        if thread and thread.is_alive():
            thread.join(timeout=self.STOP_TIMEOUT)
        
        with self._state_lock:
            if self._run_token != run_token:
                return False
            
            if thread and thread.is_alive():
                self.logger.warning("服务线程未能在超时时间内停止")
                return False
            
            self._running = False
            self.station = None
            self.thread = None
        
        self.logger.info("RTK 服务已停止")
        return True
    
    def is_running(self) -> bool:
        """
        检查服务是否在运行
        
        Returns:
            True 如果服务正在运行
        """
        with self._state_lock:
            return self._running
    
    def get_status(self) -> dict:
        """
        获取详细的服务状态
        
        Returns:
            包含服务状态的字典
        """
        with self._state_lock:
            running = self._running
            thread = self.thread
            station = self.station
        
        status = {
            "running": running,
            "thread_alive": thread.is_alive() if thread else False,
        }
        
        if station:
            status.update(station.get_status())
        
        return status


def get_manager() -> RTKManager:
    """
    获取 RTK 管理器单例
    
    线程安全地获取全局管理器实例。
    
    Returns:
        RTKManager 单例实例
    
    Example:
        >>> manager = get_manager()
        >>> manager.start_service()
    """
    global _manager
    
    if _manager is None:
        with _lock:
            # 双重检查锁定
            if _manager is None:
                _manager = RTKManager()
    
    return _manager


def reset_manager() -> None:
    """
    重置管理器实例
    
    仅用于测试目的。会停止当前运行的服务。
    
    Warning:
        此函数仅用于测试，生产环境中不应调用。
    """
    global _manager
    
    with _lock:
        if _manager is not None:
            if _manager.is_running():
                _manager.stop_service()
            _manager = None
