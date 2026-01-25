"""
NanoRTK Web 应用模块

本模块包含 Web 管理界面相关组件：
- FastAPI 应用主体
- API 路由
- 页面路由
- 服务层（RTK 管理器）
- 工具函数
"""

from app.web.app import create_app

__all__ = [
    "create_app",
]
