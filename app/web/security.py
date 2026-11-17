"""
Web API 安全辅助模块

提供轻量的管理接口访问控制：
- 回环地址（本机）默认放行，便于本地调试；
- 非回环地址必须携带并匹配管理令牌。
"""

import ipaddress
import os
import secrets
from typing import Optional

from fastapi import HTTPException, Request


def _get_client_host(request: Request) -> Optional[str]:
    """获取客户端主机地址。"""
    if request.client:
        return request.client.host
    return None


def _is_loopback(host: Optional[str]) -> bool:
    """判断主机是否为回环地址。"""
    if not host:
        return False

    if host == "localhost":
        return True

    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def ensure_api_access(request: Request) -> None:
    """
    校验管理接口访问权限。

    规则：
    - 回环地址请求直接放行；
    - 远程请求要求 `X-Admin-Token` 与环境变量 `NANORKT_ADMIN_TOKEN` 完全匹配。
    """
    client_host = _get_client_host(request)
    if _is_loopback(client_host):
        return

    expected_token = os.getenv("NANORKT_ADMIN_TOKEN", "").strip()
    if not expected_token:
        raise HTTPException(
            status_code=403,
            detail="远程管理已禁用：请配置 NANORKT_ADMIN_TOKEN"
        )

    provided_token = request.headers.get("X-Admin-Token", "")
    if not provided_token or not secrets.compare_digest(provided_token, expected_token):
        raise HTTPException(status_code=403, detail="未授权访问")
