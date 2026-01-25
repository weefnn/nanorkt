"""
页面路由模块

本模块定义页面渲染相关的路由。
不使用 Jinja2 模板，直接返回静态 HTML 文件。
"""

import logging
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse


# 获取静态文件目录路径
_project_dir = Path(__file__).parent.parent.parent.parent
_static_dir = _project_dir / "static"

# 创建路由器
router = APIRouter(tags=["pages"])
logger = logging.getLogger(__name__)


@router.get("/", response_class=FileResponse, summary="控制面板首页")
async def index() -> FileResponse:
    """
    返回控制面板首页
    
    直接返回静态 index.html 文件，配置通过 API 加载。
    
    Returns:
        FileResponse: index.html 文件
    """
    index_path = _static_dir / "index.html"
    return FileResponse(str(index_path), media_type="text/html")
