"""
Web API 安全控制模块。

提供远程访问鉴权与请求来源判断能力。
"""

import os
from typing import Optional

from fastapi import HTTPException, Request


ADMIN_TOKEN_HEADER = "X-Admin-Token"
ADMIN_TOKEN_ENV = "NANORKT_ADMIN_TOKEN"


def _extract_client_ip(request: Request) -> str:
    """
    提取客户端来源 IP。

    优先读取 X-Forwarded-For（取第一个地址），否则回退到 request.client.host。
    """
    forwarded_for = request.headers.get("x-forwarded-for", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return ""


def _is_loopback(host: str) -> bool:
    """
    判断是否为本机回环来源。
    """
    if not host:
        return False
    return host in {"127.0.0.1", "::1", "localhost"}


def _get_expected_admin_token() -> Optional[str]:
    """
    读取服务端配置的管理 token。
    """
    token = os.getenv(ADMIN_TOKEN_ENV, "").strip()
    return token or None


def ensure_api_access(request: Request) -> None:
    """
    校验 API 访问权限。

    规则：
    - 回环地址请求默认放行；
    - 非回环请求必须提供匹配的 X-Admin-Token。
    """
    client_ip = _extract_client_ip(request)
    if _is_loopback(client_ip):
        return

    expected_token = _get_expected_admin_token()
    provided_token = request.headers.get(ADMIN_TOKEN_HEADER, "").strip()

    if not expected_token or not provided_token or provided_token != expected_token:
        raise HTTPException(status_code=403, detail="forbidden")
