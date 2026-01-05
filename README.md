# RTK 基站项目

精简版 RTK 基站项目，用于读取串口数据并转发到 NTRIP Caster。

## 功能特性

- 串口数据读取（支持自定义串口和波特率）
- 千寻 MC280M 接收机自动初始化（RTCM3 输出，1Hz 频率）
- NTRIP Caster 客户端，支持数据转发
- 配置文件支持（YAML 格式）
- 自动断线重连机制
- 基站坐标配置支持

## 安装依赖

### 方式一：使用虚拟环境（推荐）

使用提供的脚本自动创建虚拟环境并安装依赖：

```bash
./setup_venv.sh
```

或者手动创建：

```bash
# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境（macOS/Linux）
source .venv/bin/activate

# 激活虚拟环境（Windows）
.venv\Scripts\activate

# 升级 pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

### 方式二：直接安装（不推荐）

```bash
pip install -r requirements.txt
```

**注意**：建议使用虚拟环境，避免与系统 Python 环境冲突。

## 配置

编辑 `config.yaml` 文件，配置串口和 NTRIP Caster 信息：

```yaml
# 串口配置
serial:
  port: /dev/ttyUSB0        # 串口设备路径
  baudrate: 115200          # 波特率

# NTRIP Caster 配置
ntrip:
  host: your-ntrip-caster.com    # NTRIP Caster 主机地址
  port: 2101                     # NTRIP Caster 端口
  mountpoint: your_mountpoint    # 挂载点名称
  username: your_username         # 用户名
  password: your_password         # 密码

# 重连配置
reconnect:
  max_retries: 5      # 最大重试次数
  retry_delay: 5.0    # 重试延迟（秒）

# 基站坐标配置
base_station:
  latitude: 31.359491017   # 纬度 (度)
  longitude: 120.714529933 # 经度 (度)
  altitude: 51.6990        # 高程 (米)
  enable_arp_average: 0     # 是否启用 ARP 平均 (0: 否, 1: 是)
```

## 运行

### 激活虚拟环境（如果使用）

```bash
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate     # Windows
```

### 启动服务

```bash
python main.py
```

程序启动后会：
1. 连接串口设备
2. 初始化千寻 MC280M 接收机（配置波特率、RTCM 输出、基站坐标）
3. 连接到 NTRIP Caster
4. 开始读取串口数据并转发到 NTRIP

### 停止服务

按 `Ctrl+C` 优雅退出，程序会自动清理资源。

## 项目结构

```
.
├── main.py              # 主程序
├── serial_reader.py     # 串口读取模块
├── ntrip_client.py      # NTRIP 客户端模块
├── qianxun_init.py      # 千寻接收机初始化模块
├── config.py            # 配置读取模块
├── config.yaml          # 配置文件
├── requirements.txt     # 依赖列表
├── setup_venv.sh        # 虚拟环境设置脚本
└── README.md           # 说明文档
```

## 千寻 MC280M 初始化

程序启动时会自动初始化千寻 MC280M 接收机：

- 配置串口波特率为 115200
- 配置基站坐标（如果配置文件中提供了坐标）
- 开启 RTCM3 消息输出（MSM4 格式）
- 设置输出频率为 1Hz

支持的 RTCM 消息类型：
- 1005: 基站坐标
- 1074: GPS MSM4
- 1084: GLONASS MSM4
- 1094: Galileo MSM4
- 1114: QZSS MSM4
- 1124: BDS MSM4

## 依赖说明

- `pyserial>=3.5` - 串口通信
- `pyyaml>=6.0` - YAML 配置文件解析
- `requests>=2.31.0` - HTTP 请求（用于 NTRIP 客户端）

## 注意事项

- 确保串口设备权限正确（可能需要 sudo 或添加用户到 dialout 组）
- 根据实际情况修改配置文件中的 NTRIP Caster 信息
- 程序支持 Ctrl+C 优雅退出
- 初始化命令使用千寻步光协议（QXCFGMSG、QXCFGPRT、QXCFGMODE）
- 对于固定基站，建议将 `enable_arp_average` 设置为 0
- 如果串口连接失败或 NTRIP 连接失败，程序会自动重试（根据配置的重连参数）

## 日志

程序使用 Python logging 模块输出日志，日志级别为 DEBUG，格式为：

```
2026-01-05 12:00:00 - module_name - LEVEL - message
```

所有调试输出都通过 logging 实现，便于问题排查和监控。

## 故障排除

### 串口连接失败

- 检查串口设备路径是否正确
- 检查串口设备权限（可能需要 `sudo` 或添加用户到 `dialout` 组）
- 确认串口设备未被其他程序占用

### NTRIP 连接失败

- 检查网络连接
- 验证 NTRIP Caster 配置信息（主机、端口、挂载点、用户名、密码）
- 查看日志输出了解详细错误信息

### 接收机初始化失败

- 确认串口连接正常
- 检查接收机是否支持千寻步光协议
- 查看日志输出了解初始化过程中的错误
