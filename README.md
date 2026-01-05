# RTK 基站项目

精简版 RTK 基站项目，用于读取串口数据并转发到 NTRIP Caster。

## 功能特性

- 串口数据读取（支持 /dev/ttyUSB0，115200 波特率）
- 千寻 MC280M 接收机自动初始化（RTCM3 输出，1Hz 频率）
- NTRIP Caster 客户端，支持数据转发
- 配置文件支持（YAML 格式）
- 自动断线重连机制
- **Web 界面控制**（基于 FastAPI + Streamlit）
- **RESTful API** 接口，支持配置管理和服务控制

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
serial:
  port: /dev/ttyUSB0
  baudrate: 115200

ntrip:
  host: your-ntrip-caster.com
  port: 2101
  mountpoint: your_mountpoint
  username: your_username
  password: your_password

reconnect:
  max_retries: 5
  retry_delay: 5.0
```

## 运行

### 方式一：命令行运行（传统方式）

如果使用虚拟环境，先激活：

```bash
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate     # Windows
```

然后运行：

```bash
python main.py
```

### 方式二：Web 界面运行（推荐）

如果使用虚拟环境，先激活：

```bash
source .venv/bin/activate  # macOS/Linux
# 或
.venv\Scripts\activate     # Windows
```

启动 Web 服务（同时启动 FastAPI 和 Streamlit）：

```bash
python start_web.py
```

或者使用便捷脚本：

```bash
./run.sh
```

或者分别启动：

```bash
# 终端 1: 启动 FastAPI 后端
./start_api.sh
# 或
.venv/bin/python -m uvicorn api:app --host 0.0.0.0 --port 8000

# 终端 2: 启动 Streamlit 前端
./start_ui.sh
# 或
.venv/bin/streamlit run web_ui.py --server.port 8501
```

**提示**：所有启动脚本已自动检测并使用 `.venv` 虚拟环境。

启动后访问：
- **Web 界面**: http://localhost:8501
- **API 文档**: http://localhost:8000/docs

## 项目结构

```
.
├── main.py              # 主程序
├── api.py               # FastAPI 后端 API
├── web_ui.py            # Streamlit Web 界面
├── serial_reader.py     # 串口读取模块
├── ntrip_client.py      # NTRIP 客户端模块
├── qianxun_init.py      # 千寻接收机初始化模块
├── config.py            # 配置读取模块
├── config.yaml          # 配置文件
├── requirements.txt     # 依赖列表
├── start_web.py         # 一键启动 Web 服务
├── start_api.sh         # 启动 FastAPI 脚本
├── start_ui.sh          # 启动 Streamlit 脚本
└── README.md           # 说明文档
```

## 千寻 MC280M 初始化

程序启动时会自动初始化千寻 MC280M 接收机：
- 配置串口波特率为 115200
- 开启 RTCM3 消息输出（MSM4 格式）
- 设置输出频率为 1Hz

支持的 RTCM 消息类型：
- 1005: 基站坐标
- 1074: GPS MSM4
- 1084: GLONASS MSM4
- 1094: Galileo MSM4
- 1114: QZSS MSM4
- 1124: BDS MSM4

## Web 界面功能

### 配置管理
- 可视化编辑所有配置项（串口、NTRIP、重连、基站坐标）
- 实时保存配置到 YAML 文件
- 配置验证和错误提示

### 服务控制
- 一键启动/停止 RTK 基站服务
- 实时显示服务运行状态
- 显示串口和 NTRIP 连接状态

### 状态监控
- 实时监控服务运行状态
- 显示连接信息
- 支持自动刷新

## API 接口

FastAPI 提供了以下 RESTful API：

- `GET /api/config` - 获取当前配置
- `POST /api/config` - 更新配置
- `GET /api/status` - 获取服务状态
- `POST /api/service/start` - 启动服务
- `POST /api/service/stop` - 停止服务
- `GET /api/health` - 健康检查

访问 http://localhost:8000/docs 查看完整的 API 文档。

## 注意事项

- 确保串口设备权限正确（可能需要 sudo 或添加用户到 dialout 组）
- 根据实际情况修改配置文件中的 NTRIP Caster 信息
- 程序支持 Ctrl+C 优雅退出
- 初始化命令使用千寻步光协议（QXCFGMSG、QXCFGPRT）
- Web 界面需要先启动 FastAPI 后端才能正常工作
- 修改配置后建议重启服务以应用新配置

