# AGENTS.md

## Cursor Cloud specific instructions

### 项目概述

NanoRTK 是一个轻量级 RTK 基站管理软件，基于 FastAPI + 纯静态前端。唯一需要运行的服务是 FastAPI Web 服务器（端口 8000）。

### 启动开发服务器

```bash
python3 run_web.py
```

服务启动后访问 http://localhost:8000 即可打开 Web 管理界面。

### 注意事项

- 系统 Python 为 `python3`（非 `python`），所有命令需使用 `python3`。
- 项目无数据库依赖，配置存储在 `config.yaml` 文件中。
- 串口设备（GNSS 接收机）和 NTRIP Caster 是硬件/外部服务依赖，在开发环境中不可用，不影响 Web 应用正常运行。
- 前端为纯静态文件（`static/` 目录），无需构建步骤。

### Lint / 测试 / 构建

- **Lint**: `black --check app/ run_web.py`（格式检查）；`mypy app/`（类型检查）
- **Test**: `pytest`（当前仓库无测试文件，框架已安装可用）
- **Build**: 无构建步骤，纯 Python + 静态资源
- **Run**: `python3 run_web.py`（启动 uvicorn 开发服务器，端口 8000）

### API 测试示例

```bash
curl http://localhost:8000/api/system
curl http://localhost:8000/api/config
curl http://localhost:8000/api/serial-ports
curl -X POST http://localhost:8000/api/config -H "Content-Type: application/json" -d '{"serial":{"port":"/dev/ttyUSB0","baudrate":115200},...}'
```
