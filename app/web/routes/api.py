"""
API 路由模块

本模块定义所有 RESTful API 端点，包括：
- 串口管理 API
- 系统状态 API
- 配置管理 API
- 服务控制 API

所有 API 使用 /api 前缀。
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
import serial.tools.list_ports

from app.core.config import Config
from app.web.services import get_manager
from app.web.utils import dot_to_nested, get_system_status


# 创建路由器
router = APIRouter(prefix="/api", tags=["api"])
logger = logging.getLogger(__name__)


def _redact_sensitive_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    脱敏配置中的敏感字段，避免通过接口泄露明文凭据。
    """
    redacted = dict(config_data)
    ntrip = redacted.get("ntrip")
    if isinstance(ntrip, dict):
        ntrip_copy = dict(ntrip)
        ntrip_copy["password"] = ""
        redacted["ntrip"] = ntrip_copy
    return redacted


def _preserve_existing_password(
    existing_config: Dict[str, Any],
    new_config: Dict[str, Any]
) -> None:
    """
    当请求未提供新密码（或提供空密码）时，保留旧密码。

    这样可以避免前端不回显密码时，用户保存其他配置导致密码被意外清空。
    """
    ntrip_config = new_config.get("ntrip")
    if not isinstance(ntrip_config, dict):
        return

    new_password = ntrip_config.get("password")
    if new_password not in (None, ""):
        return

    existing_ntrip = existing_config.get("ntrip")
    if not isinstance(existing_ntrip, dict):
        ntrip_config.pop("password", None)
        return

    existing_password = existing_ntrip.get("password")
    if existing_password:
        ntrip_config["password"] = existing_password
    else:
        ntrip_config.pop("password", None)


# ============================================================================
# 串口管理 API
# ============================================================================

@router.get("/serial-ports", summary="获取可用串口列表")
async def get_serial_ports() -> Dict[str, List[str]]:
    """
    获取当前系统可用的串口列表
    
    Returns:
        包含 ports 列表的字典
    
    Example Response:
        {"ports": ["/dev/ttyUSB0", "/dev/ttyUSB1"]}
    """
    try:
        ports = [p.device for p in serial.tools.list_ports.comports()]
        ports.sort()  # 按名称排序
        return {"ports": ports}
    except Exception as e:
        logger.error(f"获取串口列表失败: {e}")
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )


# ============================================================================
# 系统状态 API
# ============================================================================

@router.get("/system", summary="获取系统状态")
async def get_system_status_api() -> Dict[str, Any]:
    """
    获取树莓派系统状态信息
    
    包括 CPU 温度、内存使用、运行时间等。
    
    Returns:
        系统状态字典
    
    Example Response:
        {
            "cpu_temp": 45.2,
            "memory_total": 4294967296,
            "memory_available": 2147483648,
            "memory_percent": 50.0,
            "uptime_str": "5天 12小时 30分",
            "hardware": "Raspberry Pi 4 Model B",
            "system": "Linux-5.10.0-rpi"
        }
    """
    return get_system_status()


@router.get("/status", summary="获取服务状态")
async def get_service_status() -> Dict[str, Any]:
    """
    获取 RTK 服务运行状态
    
    Returns:
        服务状态字典
    """
    manager = get_manager()
    return {
        "running": manager.is_running(),
        "details": manager.get_status()
    }


# ============================================================================
# 配置管理 API
# ============================================================================

@router.get("/config", summary="获取当前配置")
async def get_config() -> Dict[str, Any]:
    """
    获取当前配置文件内容
    
    Returns:
        完整的配置字典
    """
    config = Config()
    return _redact_sensitive_config(config.to_dict())


@router.post("/config", summary="更新配置")
async def update_config(request: Request) -> JSONResponse:
    """
    更新配置文件
    
    接受扁平格式（点号分隔）或嵌套格式的配置数据。
    
    Request Body Example:
        {"serial.port": "/dev/ttyUSB0", "serial.baudrate": 115200}
        或
        {"serial": {"port": "/dev/ttyUSB0", "baudrate": 115200}}
    
    Returns:
        操作结果
    """
    try:
        data = await request.json()
        
        # 将点号分隔的扁平键转换为嵌套结构
        nested_data = dot_to_nested(data)
        
        config = Config()
        _preserve_existing_password(config.to_dict(), nested_data)
        success = config.save(nested_data)
        
        if success:
            logger.info("配置已保存")
            return JSONResponse({
                "success": True,
                "message": "配置已保存"
            })
        else:
            raise HTTPException(
                status_code=500,
                detail="配置保存失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新配置失败: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )


# ============================================================================
# 服务控制 API
# ============================================================================

@router.post("/control", summary="控制服务启停")
async def control_service(request: Request) -> JSONResponse:
    """
    控制 RTK 服务的启动和停止
    
    Request Body:
        {"action": "start"} 或 {"action": "stop"}
    
    Returns:
        操作结果
    """
    try:
        data = await request.json()
        action = data.get("action")
        manager = get_manager()
        
        if action == "start":
            if manager.is_running():
                return JSONResponse({
                    "success": False,
                    "message": "服务已在运行中"
                })
            
            manager.start_service()
            return JSONResponse({
                "success": True,
                "message": "服务已启动"
            })
            
        elif action == "stop":
            if not manager.is_running():
                return JSONResponse({
                    "success": False,
                    "message": "服务未在运行"
                })
            
            manager.stop_service()
            return JSONResponse({
                "success": True,
                "message": "服务已停止"
            })
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"未知动作: {action}，支持 'start' 或 'stop'"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"控制服务失败: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
