"""
NanoRTK Web 路由模块

本模块包含所有 HTTP 路由定义：
- api: RESTful API 端点
- pages: 页面渲染路由
"""

from app.web.routes.api import router as api_router
from app.web.routes.pages import router as pages_router

__all__ = [
    "api_router",
    "pages_router",
]
