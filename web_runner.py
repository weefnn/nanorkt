"""
Web 运行器 - RTK 基站 Web 控制界面
"""
import logging
import threading
import asyncio
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, WebSocket, BackgroundTasks, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import socketio
from socketio import AsyncServer
import serial.tools.list_ports
import uvicorn
import psutil
import platform
import subprocess
import time
import os

# 导入项目模块
from main import RTKBaseStation
from config import Config

# 全局管理器单例
_manager = None

class RTKManager:
    """RTK 基站管理器（单例）"""
    
    def __init__(self):
        self.station: Optional[RTKBaseStation] = None
        self.thread: Optional[threading.Thread] = None
        self._running = False
    
    def start_service(self):
        """启动 RTK 服务"""
        if self._running:
            logging.warning("服务已在运行中")
            return
        
        # 创建 RTKBaseStation 实例
        self.station = RTKBaseStation()
        # 创建线程运行 station.start（注意：start 是阻塞方法）
        self.thread = threading.Thread(target=self._run_station, daemon=True)
        self.thread.start()
        self._running = True
        logging.info("RTK 服务启动")
    
    def _run_station(self):
        """在线程中运行 RTKBaseStation.start"""
        try:
            if self.station:
                self.station.start()
        except Exception as e:
            logging.error(f"RTK 服务运行异常: {e}")
        finally:
            self._running = False
            self.station = None
    
    def stop_service(self):
        """停止 RTK 服务"""
        if not self._running:
            logging.warning("服务未在运行")
            return
        
        if self.station:
            self.station.stop()
        
        # 等待线程结束（超时 5 秒）
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
        
        self._running = False
        self.station = None
        logging.info("RTK 服务已停止")
    
    def is_running(self) -> bool:
        """检查服务是否在运行"""
        return self._running

def get_manager() -> RTKManager:
    """获取管理器单例"""
    global _manager
    if _manager is None:
        _manager = RTKManager()
    return _manager

# Socket.IO 服务器
sio = AsyncServer(async_mode='asgi', cors_allowed_origins='*')
app_loop = None  # 全局事件循环，在 startup 中设置

# FastAPI 应用
app = FastAPI(title="RTKBase Web Runner", version="1.0.0")

# 模板引擎
templates = Jinja2Templates(directory="templates")

# 静态文件（可选）
app.mount("/static", StaticFiles(directory="static"), name="static")

# Socket.IO 日志处理器
class SocketIOHandler(logging.Handler):
    """将日志通过 Socket.IO 实时推送到前端"""
    
    def emit(self, record):
        try:
            log_entry = self.format(record)
            global app_loop
            if app_loop is not None:
                # 通过事件循环异步发射日志事件
                asyncio.run_coroutine_threadsafe(
                    sio.emit('log', {
                        'level': record.levelname,
                        'message': log_entry,
                        'timestamp': record.created
                    }),
                    app_loop
                )
        except Exception:
            pass  # 避免日志处理器本身崩溃

def dot_to_nested(flat: Dict[str, Any]) -> Dict[str, Any]:
    """
    将点号分隔的扁平字典转换为嵌套字典。
    例如 {'serial.port': 'ttyUSB0'} -> {'serial': {'port': 'ttyUSB0'}}
    """
    result = {}
    for key, value in flat.items():
        parts = key.split('.')
        target = result
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value
    return result

def get_system_status():
    """获取树莓派系统状态信息"""
    status = {}
    
    # CPU 温度
    cpu_temp = None
    try:
        # 尝试 vcgencmd 命令（树莓派专用）
        output = subprocess.check_output(['vcgencmd', 'measure_temp'], universal_newlines=True)
        # 输出示例：temp=42.5'C
        cpu_temp = float(output.strip().split('=')[1].replace("'C", ""))
    except (subprocess.CalledProcessError, FileNotFoundError, IndexError, ValueError):
        try:
            # 读取 thermal 文件（通用 Linux）
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                cpu_temp = float(f.read().strip()) / 1000.0
        except (IOError, ValueError):
            cpu_temp = None
    
    status['cpu_temp'] = cpu_temp
    
    # 内存信息
    mem = psutil.virtual_memory()
    status['memory_total'] = mem.total
    status['memory_available'] = mem.available
    status['memory_percent'] = mem.percent
    
    # 运行时间
    uptime_seconds = time.time() - psutil.boot_time()
    days = int(uptime_seconds // (24 * 3600))
    hours = int((uptime_seconds % (24 * 3600)) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    status['uptime_days'] = days
    status['uptime_hours'] = hours
    status['uptime_minutes'] = minutes
    status['uptime_str'] = f"{days}天 {hours}小时 {minutes}分"
    
    # 硬件版本
    hardware = ''
    try:
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('Model'):
                    hardware = line.split(':')[-1].strip()
                    break
    except IOError:
        pass
    if not hardware:
        hardware = platform.machine()
    status['hardware'] = hardware
    
    # 系统版本
    status['system'] = platform.platform()
    
    return status

# 应用启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时设置日志处理器"""
    global app_loop
    app_loop = asyncio.get_event_loop()
    # 添加 Socket.IO 处理器到根日志器
    root_logger = logging.getLogger()
    io_handler = SocketIOHandler()
    io_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    root_logger.addHandler(io_handler)
    logging.info("Web 运行器已启动，日志实时推送已启用")

# 路由
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """渲染控制页面"""
    config = Config()
    # 获取当前配置
    config_data = {
        'serial': config.get_serial_config(),
        'ntrip': config.get_ntrip_config(),
        'reconnect': config.get_reconnect_config(),
        'base_station': config.get_base_station_config()
    }
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "config": config_data, "running": get_manager().is_running()}
    )

@app.get("/api/serial-ports")
async def get_serial_ports():
    """获取当前可用串口列表"""
    try:
        ports = [p.device for p in serial.tools.list_ports.comports()]
        # 按名称排序，方便查找
        ports.sort()
        return {"ports": ports}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/system")
async def get_system_status_api():
    """获取系统状态信息"""
    status = get_system_status()
    return status

@app.post("/api/config")
async def update_config(request: Request):
    """更新配置文件"""
    try:
        data = await request.json()
        # 将点号分隔的扁平键转换为嵌套结构
        nested_data = dot_to_nested(data)
        config = Config()
        success = config.save(nested_data)
        if success:
            return JSONResponse({"success": True, "message": "配置已保存"})
        else:
            raise HTTPException(status_code=500, detail="配置保存失败")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/control")
async def control_service(request: Request):
    """控制服务启停"""
    try:
        data = await request.json()
        action = data.get('action')
        manager = get_manager()
        
        if action == 'start':
            manager.start_service()
            return JSONResponse({"success": True, "message": "服务已启动"})
        elif action == 'stop':
            manager.stop_service()
            return JSONResponse({"success": True, "message": "服务已停止"})
        else:
            raise HTTPException(status_code=400, detail="未知动作，支持 'start' 或 'stop'")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket 日志流（备用）"""
    await websocket.accept()
    # 简单实现：可以推送日志，但 Socket.IO 已经处理了
    await websocket.send_json({"message": "WebSocket 日志通道已连接"})
    try:
        while True:
            await websocket.receive_text()
    except:
        pass

# 集成 Socket.IO 到 FastAPI
app_asgi = socketio.ASGIApp(sio, app)

# 主入口
if __name__ == "__main__":
    uvicorn.run(app_asgi, host="0.0.0.0", port=8000, log_level="info")