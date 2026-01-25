"""
FastAPI Web 应用模块

本模块是 NanoRTK Web 界面的主入口，包含：
- FastAPI 应用实例创建
- Socket.IO 集成
- 路由注册
- 静态文件服务
- 实时日志推送

运行方式：
    python -m app.web.app

或作为模块导入：
    from app.web import create_app
    app = create_app()
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
import socketio
import uvicorn

from app.core.logging_config import setup_logging
from app.web.routes import api_router, pages_router


from collections import deque

# ============================================================================
# 全局变量
# ============================================================================

# Socket.IO 服务器
sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")

# 事件循环引用
_app_loop: Optional[asyncio.AbstractEventLoop] = None

# 日志缓冲区 (存储最近 100 条日志)
log_buffer = deque(maxlen=100)


# ============================================================================
# Socket.IO 日志处理器
# ============================================================================

class SocketIOLogHandler(logging.Handler):
    """
    Socket.IO 日志处理器
    
    将日志消息实时推送到前端，并存入缓冲区。
    """
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        发送日志记录
        
        Args:
            record: 日志记录对象
        """
        try:
            log_entry = self.format(record)
            
            # 构建日志对象
            data = {
                "level": record.levelname,
                "message": log_entry,
                "timestamp": record.created
            }
            
            # 存入缓冲区
            log_buffer.append(data)
            
            global _app_loop
            if _app_loop is not None:
                # 通过事件循环异步发送日志
                asyncio.run_coroutine_threadsafe(
                    sio.emit("log", data),
                    _app_loop
                )
        except Exception:
            pass  # 避免日志处理器本身导致崩溃


# ============================================================================
# 应用工厂
# ============================================================================

from contextlib import asynccontextmanager

def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例
    
    配置路由、静态文件和事件处理器。
    
    Returns:
        配置好的 FastAPI 应用
    
    Example:
        >>> app = create_app()
        >>> import uvicorn
        >>> uvicorn.run(app, host="0.0.0.0", port=8000)
    """
    
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """应用生命周期管理器"""
        global _app_loop
        _app_loop = asyncio.get_running_loop()
        
        # 添加 Socket.IO 日志处理器
        root_logger = logging.getLogger()
        io_handler = SocketIOLogHandler()
        io_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        root_logger.addHandler(io_handler)
        
        # 将日志处理器添加到 uvicorn 日志记录器
        for logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
            logger = logging.getLogger(logger_name)
            logger.addHandler(io_handler)
            
        logging.info("Web 应用已启动，日志实时推送已启用")
        
        yield
        
        # 因为 Python logging 模块会自动处理 cleanup，
        # 这里不需要手动移除 handler，避免复杂化
        pass

    # 创建应用
    app = FastAPI(
        title="NanoRTK Admin",
        description="RTK 基站 Web 管理界面",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # 获取静态文件目录路径 (项目根目录/static)
    project_dir = Path(__file__).parent.parent.parent
    static_dir = project_dir / "static"
    
    # 注册路由
    app.include_router(api_router)
    app.include_router(pages_router)
    
    # 挂载静态文件
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    
    # WebSocket 日志端点（备用）
    @app.websocket("/ws/logs")
    async def websocket_logs(websocket: WebSocket):
        """
        WebSocket 日志流（备用通道）
        
        主要使用 Socket.IO，此端点作为备用。
        """
        await websocket.accept()
        await websocket.send_json({"message": "WebSocket 日志通道已连接"})
        
        try:
            while True:
                await websocket.receive_text()
        except Exception:
            pass
    
    return app


def create_asgi_app() -> socketio.ASGIApp:
    """
    创建带有 Socket.IO 的 ASGI 应用
    
    Returns:
        集成了 Socket.IO 的 ASGI 应用
    """
    app = create_app()
    return socketio.ASGIApp(sio, app)

# ============================================================================
# Socket.IO 事件处理
# ============================================================================

@sio.event
async def connect(sid, environ):
    """客户端连接事件"""
    logging.debug(f"Socket.IO 客户端连接: {sid}")
    
    # 发送最近的日志历史
    for log_data in log_buffer:
        await sio.emit("log", log_data, room=sid)


@sio.event
async def disconnect(sid):
    """客户端断开事件"""
    logging.debug(f"Socket.IO 客户端断开: {sid}")


# ============================================================================
# 主入口
# ============================================================================

def main():
    """
    Web 应用命令行入口
    
    启动 uvicorn 服务器运行 Web 应用。
    """
    # 设置日志
    setup_logging(level="INFO")
    
    # 创建应用
    asgi_app = create_asgi_app()
    
    # 启动服务器
    uvicorn.run(
        asgi_app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


if __name__ == "__main__":
    main()
