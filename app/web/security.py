"""
Web API 安全校验模块

策略：
- 本机回环请求（127.0.0.1/::1/localhost）默认放行。
- 远程请求必须提供 X-Admin-Token，且与 NANORKT_ADMIN_TOKEN 一致。
"""

import ipaddress
import os
import secrets

from fastapi import HTTPException, Request


def _extract_client_host(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return ""


def _is_loopback_host(host: str) -> bool:
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
    校验敏感管理接口访问权限。
    """
    host = _extract_client_host(request)
    if _is_loopback_host(host):
        return

    expected = os.getenv("NANORKT_ADMIN_TOKEN", "")
    provided = request.headers.get("x-admin-token", "")

    if not expected:
        raise HTTPException(
            status_code=403,
            detail="远程访问已禁用：未配置 NANORKT_ADMIN_TOKEN"
        )

    if not provided or not secrets.compare_digest(provided, expected):
        raise HTTPException(status_code=403, detail="无效的管理令牌")
