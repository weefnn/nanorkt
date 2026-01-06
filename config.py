"""配置文件读取模块"""
import yaml  # type: ignore
import logging
from typing import Dict, Any
from pathlib import Path


class Config:
    """配置管理类"""
    
    def __init__(self, config_path: str = 'config.yaml'):
        """
        初始化配置
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.logger = logging.getLogger(__name__)
        self.data: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> bool:
        """
        加载配置文件
        
        Returns:
            加载是否成功
        """
        try:
            if not self.config_path.exists():
                self.logger.warning(f"配置文件不存在: {self.config_path}")
                return False
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.data = yaml.safe_load(f) or {}
            
            self.logger.info(f"配置文件加载成功: {self.config_path}")
            return True
        except Exception as e:
            self.logger.error(f"加载配置文件错误: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键（如 'serial.port'）
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_serial_config(self) -> Dict[str, Any]:
        """获取串口配置"""
        return {
            'port': self.get('serial.port', '/dev/ttyUSB0'),
            'baudrate': self.get('serial.baudrate', 115200)
        }
    
    def get_ntrip_config(self) -> Dict[str, Any]:
        """获取 NTRIP 配置"""
        return {
            'host': self.get('ntrip.host', ''),
            'port': self.get('ntrip.port', 2101),
            'mountpoint': self.get('ntrip.mountpoint', ''),
            'username': self.get('ntrip.username', ''),
            'password': self.get('ntrip.password', '')
        }
    
    def get_reconnect_config(self) -> Dict[str, Any]:
        """获取重连配置"""
        return {
            'max_retries': self.get('reconnect.max_retries', 5),
            'retry_delay': self.get('reconnect.retry_delay', 5.0)
        }

    def get_base_station_config(self) -> Dict[str, Any]:
        """获取基站坐标配置"""
        return {
            'latitude': self.get('base_station.latitude', 0.0),
            'longitude': self.get('base_station.longitude', 0.0),
            'altitude': self.get('base_station.altitude', 0.0),
            'enable_arp_average': self.get('base_station.enable_arp_average', 0)
        }

    def save(self, new_config: Dict[str, Any]) -> bool:
        """
        保存配置到文件 (包含类型转换)
        """
        try:
            # 1. 更新内存中的配置
            # 使用 deep update 策略防止覆盖整个 section
            for section, values in new_config.items():
                if section in self.data and isinstance(self.data[section], dict) and isinstance(values, dict):
                    self.data[section].update(values)
                else:
                    self.data[section] = values
            
            # 2. 强制类型转换 (清洗数据)
            # Serial
            if 'serial' in self.data:
                if 'baudrate' in self.data['serial']:
                    self.data['serial']['baudrate'] = int(self.data['serial']['baudrate'])
            # NTRIP
            if 'ntrip' in self.data:
                if 'port' in self.data['ntrip']:
                    self.data['ntrip']['port'] = int(self.data['ntrip']['port'])
            # Reconnect
            if 'reconnect' in self.data:
                if 'max_retries' in self.data['reconnect']:
                    self.data['reconnect']['max_retries'] = int(self.data['reconnect']['max_retries'])
                if 'retry_delay' in self.data['reconnect']:
                    self.data['reconnect']['retry_delay'] = float(self.data['reconnect']['retry_delay'])
            # Base Station
            if 'base_station' in self.data:
                for key in ['latitude', 'longitude', 'altitude']:
                    if key in self.data['base_station']:
                        self.data['base_station'][key] = float(self.data['base_station'][key])
                if 'enable_arp_average' in self.data['base_station']:
                    self.data['base_station']['enable_arp_average'] = int(self.data['base_station']['enable_arp_average'])
            
            # 3. 写入文件
            with open(self.config_path, 'w', encoding='utf-8') as f:
                # default_flow_style=False 保持 YAML 的块状格式，更易读
                yaml.safe_dump(self.data, f, default_flow_style=False, allow_unicode=True)
            
            self.logger.info(f"配置文件保存成功: {self.config_path}")
            return True
        except Exception as e:
            self.logger.error(f"保存配置文件错误: {e}")
            return False
        