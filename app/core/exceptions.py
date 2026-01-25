"""
NanoRTK 自定义异常模块

本模块定义了 NanoRTK 系统中使用的所有自定义异常类。
使用自定义异常可以实现更精确的错误处理和更友好的错误信息。

异常层次结构：
    NanoRTKError (基础异常)
    ├── SerialConnectionError (串口连接异常)
    ├── NTRIPConnectionError (NTRIP 连接异常)
    ├── ConfigurationError (配置异常)
    └── ReceiverInitError (接收机初始化异常)
"""


class NanoRTKError(Exception):
    """
    NanoRTK 基础异常类
    
    所有 NanoRTK 相关的异常都应继承此类。
    这允许调用者可以捕获所有 NanoRTK 相关异常，
    也可以捕获特定类型的异常。
    
    Attributes:
        message: 错误描述信息
        details: 额外的错误详情（可选）
    
    Example:
        >>> try:
        ...     raise NanoRTKError("发生错误", details={"code": 500})
        ... except NanoRTKError as e:
        ...     print(f"错误: {e.message}")
    """
    
    def __init__(self, message: str, details: dict = None):
        """
        初始化异常
        
        Args:
            message: 错误描述信息
            details: 额外的错误详情字典（可选）
        """
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        """返回异常的字符串表示"""
        if self.details:
            return f"{self.message} - 详情: {self.details}"
        return self.message


class SerialConnectionError(NanoRTKError):
    """
    串口连接异常
    
    当串口连接、读取或写入操作失败时抛出此异常。
    
    常见场景：
    - 串口设备不存在
    - 串口被其他程序占用
    - 串口参数配置错误
    - 读写超时
    
    Attributes:
        port: 串口设备路径
        baudrate: 波特率（可选）
    
    Example:
        >>> raise SerialConnectionError(
        ...     "无法打开串口",
        ...     port="/dev/ttyUSB0",
        ...     baudrate=115200
        ... )
    """
    
    def __init__(self, message: str, port: str = None, baudrate: int = None, **kwargs):
        """
        初始化串口连接异常
        
        Args:
            message: 错误描述信息
            port: 串口设备路径
            baudrate: 波特率
            **kwargs: 其他详情参数
        """
        details = kwargs.get("details", {})
        if port:
            details["port"] = port
        if baudrate:
            details["baudrate"] = baudrate
        super().__init__(message, details=details)
        self.port = port
        self.baudrate = baudrate


class NTRIPConnectionError(NanoRTKError):
    """
    NTRIP 连接异常
    
    当 NTRIP Caster 连接、认证或数据传输失败时抛出此异常。
    
    常见场景：
    - 无法连接到 NTRIP Caster 服务器
    - 认证失败（用户名/密码错误）
    - 挂载点不存在
    - 连接超时或断开
    
    Attributes:
        host: NTRIP Caster 主机地址
        port: NTRIP Caster 端口
        mountpoint: 挂载点名称（可选）
    
    Example:
        >>> raise NTRIPConnectionError(
        ...     "NTRIP 认证失败",
        ...     host="ntrip.example.com",
        ...     port=2101,
        ...     mountpoint="RTCM32"
        ... )
    """
    
    def __init__(
        self, 
        message: str, 
        host: str = None, 
        port: int = None, 
        mountpoint: str = None,
        **kwargs
    ):
        """
        初始化 NTRIP 连接异常
        
        Args:
            message: 错误描述信息
            host: NTRIP Caster 主机地址
            port: NTRIP Caster 端口
            mountpoint: 挂载点名称
            **kwargs: 其他详情参数
        """
        details = kwargs.get("details", {})
        if host:
            details["host"] = host
        if port:
            details["port"] = port
        if mountpoint:
            details["mountpoint"] = mountpoint
        super().__init__(message, details=details)
        self.host = host
        self.port = port
        self.mountpoint = mountpoint


class ConfigurationError(NanoRTKError):
    """
    配置异常
    
    当配置文件读取、解析或验证失败时抛出此异常。
    
    常见场景：
    - 配置文件不存在
    - 配置文件格式错误（YAML 语法错误）
    - 必需的配置项缺失
    - 配置值不合法
    
    Attributes:
        config_key: 出错的配置键名（可选）
        config_file: 配置文件路径（可选）
    
    Example:
        >>> raise ConfigurationError(
        ...     "配置项缺失",
        ...     config_key="ntrip.host",
        ...     config_file="config.yaml"
        ... )
    """
    
    def __init__(
        self, 
        message: str, 
        config_key: str = None, 
        config_file: str = None,
        **kwargs
    ):
        """
        初始化配置异常
        
        Args:
            message: 错误描述信息
            config_key: 出错的配置键名
            config_file: 配置文件路径
            **kwargs: 其他详情参数
        """
        details = kwargs.get("details", {})
        if config_key:
            details["config_key"] = config_key
        if config_file:
            details["config_file"] = config_file
        super().__init__(message, details=details)
        self.config_key = config_key
        self.config_file = config_file


class ReceiverInitError(NanoRTKError):
    """
    接收机初始化异常
    
    当 GNSS 接收机（如千寻 MC280M）初始化失败时抛出此异常。
    
    常见场景：
    - 接收机无响应
    - 命令发送失败
    - 配置命令未被确认
    - 固件版本不兼容
    
    Attributes:
        command: 失败的命令（可选）
        receiver_type: 接收机型号（可选）
    
    Example:
        >>> raise ReceiverInitError(
        ...     "接收机初始化超时",
        ...     command="QXCFGPRT",
        ...     receiver_type="MC280M"
        ... )
    """
    
    def __init__(
        self, 
        message: str, 
        command: str = None, 
        receiver_type: str = None,
        **kwargs
    ):
        """
        初始化接收机初始化异常
        
        Args:
            message: 错误描述信息
            command: 失败的命令
            receiver_type: 接收机型号
            **kwargs: 其他详情参数
        """
        details = kwargs.get("details", {})
        if command:
            details["command"] = command
        if receiver_type:
            details["receiver_type"] = receiver_type
        super().__init__(message, details=details)
        self.command = command
        self.receiver_type = receiver_type
