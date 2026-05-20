"""
NanoRTK 配置管理模块

本模块提供配置文件的读取、验证和管理功能。
使用 Pydantic 进行数据验证，确保配置值的类型和范围正确。

配置文件格式 (config.yaml):
    serial:
        port: /dev/ttyUSB0
        baudrate: 115200
    
    ntrip:
        host: ntrip.example.com
        port: 2101
        mountpoint: RTCM32
        username: user
        password: pass
    
    reconnect:
        max_retries: 5
        retry_delay: 5.0
    
    base_station:
        latitude: 39.9
        longitude: 116.4
        altitude: 50.0
        enable_arp_average: 0

使用方法：
    >>> from app.core.config import Config
    >>> config = Config()
    >>> serial_cfg = config.get_serial_config()
    >>> print(serial_cfg.port)
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Type

import yaml  # type: ignore
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.exceptions import ConfigurationError


# ============================================================================
# Pydantic 配置模型
# ============================================================================

class SerialConfig(BaseModel):
    """
    串口配置模型
    
    Attributes:
        port: 串口设备路径，如 /dev/ttyUSB0 或 COM3
        baudrate: 波特率，默认 115200
    """
    port: str = Field(default="/dev/ttyUSB0", description="串口设备路径")
    baudrate: int = Field(default=115200, ge=9600, le=921600, description="波特率")
    
    @field_validator("baudrate")
    @classmethod
    def validate_baudrate(cls, v: int) -> int:
        """验证波特率是否为标准值"""
        standard_baudrates = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
        if v not in standard_baudrates:
            logging.getLogger(__name__).warning(
                f"波特率 {v} 不是标准值，可能导致通信问题"
            )
        return v


class NTRIPConfig(BaseModel):
    """
    NTRIP Caster 配置模型
    
    Attributes:
        host: NTRIP Caster 服务器地址
        port: NTRIP Caster 端口，默认 2101
        mountpoint: 挂载点名称
        username: 认证用户名
        password: 认证密码
    """
    host: str = Field(default="", description="NTRIP Caster 主机地址")
    port: int = Field(default=2101, ge=1, le=65535, description="端口号")
    mountpoint: str = Field(default="", description="挂载点名称")
    username: str = Field(default="", description="用户名")
    password: str = Field(default="", description="密码")


class ReconnectConfig(BaseModel):
    """
    重连配置模型
    
    Attributes:
        max_retries: 最大重试次数
        retry_delay: 重试间隔（秒）
    """
    max_retries: int = Field(default=5, ge=1, le=100, description="最大重试次数")
    retry_delay: float = Field(default=5.0, ge=0.1, le=300.0, description="重试间隔(秒)")


class BaseStationConfig(BaseModel):
    """
    基站坐标配置模型
    
    Attributes:
        latitude: 纬度（度）
        longitude: 经度（度）
        altitude: 海拔高度（米）
        enable_arp_average: 是否启用 ARP 平均模式
    """
    latitude: float = Field(default=0.0, ge=-90.0, le=90.0, description="纬度(度)")
    longitude: float = Field(default=0.0, ge=-180.0, le=180.0, description="经度(度)")
    altitude: float = Field(default=0.0, ge=-1000.0, le=10000.0, description="海拔高度(米)")
    enable_arp_average: int = Field(default=0, ge=0, le=1, description="启用ARP平均(0/1)")


class AppConfig(BaseModel):
    """
    应用完整配置模型
    
    包含所有子配置的顶级配置类。
    
    Attributes:
        serial: 串口配置
        ntrip: NTRIP 配置
        reconnect: 重连配置
        base_station: 基站配置
    """
    serial: SerialConfig = Field(default_factory=SerialConfig)
    ntrip: NTRIPConfig = Field(default_factory=NTRIPConfig)
    reconnect: ReconnectConfig = Field(default_factory=ReconnectConfig)
    base_station: BaseStationConfig = Field(default_factory=BaseStationConfig)


# ============================================================================
# 配置管理类
# ============================================================================

class Config:
    """
    配置管理类
    
    负责加载、验证和保存配置文件。支持点号分隔的嵌套键访问。
    
    Attributes:
        config_path: 配置文件路径
        data: 原始配置数据字典
        app_config: 经过验证的配置对象
    
    Example:
        >>> config = Config("config.yaml")
        >>> serial_cfg = config.get_serial_config()
        >>> print(f"串口: {serial_cfg.port}, 波特率: {serial_cfg.baudrate}")
        
        >>> # 使用点号访问嵌套值
        >>> host = config.get("ntrip.host")
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，默认为当前目录的 config.yaml
        
        Raises:
            ConfigurationError: 配置文件格式错误或验证失败
        """
        self.config_path = Path(config_path)
        self.logger = logging.getLogger(__name__)
        self.data: Dict[str, Any] = {}
        self.app_config: Optional[AppConfig] = None
        self.load()
    
    def load(self) -> bool:
        """
        加载并验证配置文件
        
        Returns:
            加载是否成功
        
        Raises:
            ConfigurationError: 配置文件格式错误
        """
        try:
            if not self.config_path.exists():
                self.logger.warning(f"配置文件不存在: {self.config_path}，使用默认配置")
                self.data = {}
                self.app_config = AppConfig()
                return True
            
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.data = yaml.safe_load(f) or {}
            
            # 使用 Pydantic 验证配置
            try:
                self.app_config = AppConfig(**self.data)
                self.logger.info(f"配置文件加载成功: {self.config_path}")
                return True
            except ValidationError as e:
                # 保留有效配置节，仅对非法节回退默认值，避免单个字段错误导致整份配置失效
                self.logger.error(f"配置验证失败，将按节回退默认值: {e}")
                self.app_config = AppConfig(
                    serial=self._load_section("serial", SerialConfig),
                    ntrip=self._load_section("ntrip", NTRIPConfig),
                    reconnect=self._load_section("reconnect", ReconnectConfig),
                    base_station=self._load_section("base_station", BaseStationConfig),
                )
                return False
            
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"YAML 格式错误: {e}",
                config_file=str(self.config_path)
            )
        except Exception as e:
            self.logger.error(f"加载配置文件错误: {e}")
            # 使用默认配置
            self.app_config = AppConfig()
            return False

    def _load_section(self, section: str, model_class: Type[BaseModel]) -> BaseModel:
        """
        按配置节加载并验证
        
        当单个配置节验证失败时，仅该节回退为默认值。
        """
        raw_section = self.data.get(section, {})
        
        if not isinstance(raw_section, dict):
            self.logger.warning(f"配置节 {section} 格式错误（应为对象），使用默认值")
            return model_class()
        
        try:
            return model_class(**raw_section)
        except ValidationError as e:
            self.logger.warning(f"配置节 {section} 验证失败，使用默认值: {e}")
            return model_class()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号分隔的嵌套键）
        
        Args:
            key: 配置键，如 "serial.port" 或 "ntrip.host"
            default: 默认值
        
        Returns:
            配置值，如果不存在则返回默认值
        
        Example:
            >>> config.get("serial.port", "/dev/ttyUSB0")
            '/dev/ttyUSB0'
        """
        keys = key.split(".")
        value = self.data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_serial_config(self) -> SerialConfig:
        """
        获取串口配置
        
        Returns:
            SerialConfig 配置对象
        """
        return self.app_config.serial if self.app_config else SerialConfig()
    
    def get_ntrip_config(self) -> NTRIPConfig:
        """
        获取 NTRIP 配置
        
        Returns:
            NTRIPConfig 配置对象
        """
        return self.app_config.ntrip if self.app_config else NTRIPConfig()
    
    def get_reconnect_config(self) -> ReconnectConfig:
        """
        获取重连配置
        
        Returns:
            ReconnectConfig 配置对象
        """
        return self.app_config.reconnect if self.app_config else ReconnectConfig()
    
    def get_base_station_config(self) -> BaseStationConfig:
        """
        获取基站坐标配置
        
        Returns:
            BaseStationConfig 配置对象
        """
        return self.app_config.base_station if self.app_config else BaseStationConfig()
    
    def save(self, new_config: Dict[str, Any]) -> bool:
        """
        保存配置到文件
        
        使用深度合并策略更新配置，避免覆盖整个配置节。
        自动进行类型转换以确保数据类型正确。
        
        Args:
            new_config: 要更新的配置字典
        
        Returns:
            保存是否成功
        
        Example:
            >>> config.save({"serial": {"baudrate": 9600}})
        """
        try:
            # 深度合并配置
            for section, values in new_config.items():
                if section in self.data and isinstance(self.data[section], dict) and isinstance(values, dict):
                    self.data[section].update(values)
                else:
                    self.data[section] = values
            
            # 类型转换和清洗
            self._sanitize_config()
            
            # 重新验证配置
            self.app_config = AppConfig(**self.data)
            
            # 写入文件
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(self.data, f, default_flow_style=False, allow_unicode=True)
            
            self.logger.info(f"配置文件保存成功: {self.config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"保存配置文件错误: {e}")
            return False
    
    def _sanitize_config(self) -> None:
        """
        清洗和类型转换配置数据
        
        确保配置值的类型正确，避免 YAML 解析导致的类型问题。
        """
        # 串口配置
        if "serial" in self.data:
            if "baudrate" in self.data["serial"]:
                self.data["serial"]["baudrate"] = int(self.data["serial"]["baudrate"])
        
        # NTRIP 配置
        if "ntrip" in self.data:
            if "port" in self.data["ntrip"]:
                self.data["ntrip"]["port"] = int(self.data["ntrip"]["port"])
        
        # 重连配置
        if "reconnect" in self.data:
            if "max_retries" in self.data["reconnect"]:
                self.data["reconnect"]["max_retries"] = int(self.data["reconnect"]["max_retries"])
            if "retry_delay" in self.data["reconnect"]:
                self.data["reconnect"]["retry_delay"] = float(self.data["reconnect"]["retry_delay"])
        
        # 基站配置
        if "base_station" in self.data:
            for key in ["latitude", "longitude", "altitude"]:
                if key in self.data["base_station"]:
                    self.data["base_station"][key] = float(self.data["base_station"][key])
            if "enable_arp_average" in self.data["base_station"]:
                self.data["base_station"]["enable_arp_average"] = int(
                    self.data["base_station"]["enable_arp_average"]
                )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将配置导出为字典
        
        Returns:
            完整的配置字典
        """
        if self.app_config:
            return self.app_config.model_dump()
        return {}
