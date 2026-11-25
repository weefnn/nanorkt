"""
Web 安全工具模块

提供 API 访问控制相关的工具函数：
- 本机回环地址免鉴权
- 非本机请求必须通过 Basic Auth 验证
"""

import base64
import hmac
import os
from typing import Optional, Tuple

from fastapi import HTTPException, Request


_LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}
_AUTH_REALM = 'Basic realm="NanoRTK API"'


def _is_loopback(host: Optional[str]) -> bool:
    """判断请求来源是否为本机回环地址。"""
    return bool(host) and host in _LOOPBACK_HOSTS


def _parse_basic_auth(header_value: Optional[str]) -> Optional[Tuple[str, str]]:
    """
    解析 HTTP Basic Authorization 头。

    Args:
        header_value: Authorization 头的值

    Returns:
        (username, password) 元组；解析失败时返回 None
    """
    if not header_value:
        return None

    scheme, _, encoded = header_value.partition(" ")
    if scheme.lower() != "basic" or not encoded:
        return None

    try:
        decoded = base64.b64decode(encoded.strip()).decode("utf-8")
    except Exception:
        return None

    username, sep, password = decoded.partition(":")
    if not sep:
        return None

    return username, password


def require_api_access(request: Request) -> None:
    """
    API 访问控制：
    - 本机回环地址：允许直接访问
    - 非本机地址：必须通过 Basic Auth
      (NANORTK_WEB_USERNAME / NANORTK_WEB_PASSWORD)
    """
    client_host = request.client.host if request.client else None
    if _is_loopback(client_host):
        return

    expected_user = os.getenv("NANORTK_WEB_USERNAME")
    expected_password = os.getenv("NANORTK_WEB_PASSWORD")
    if not expected_user or not expected_password:
        raise HTTPException(
            status_code=403,
            detail=(
                "远程访问已禁用：请在服务端设置 "
                "NANORTK_WEB_USERNAME 和 NANORTK_WEB_PASSWORD"
            ),
        )

    credentials = _parse_basic_auth(request.headers.get("Authorization"))
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="需要 Basic 认证",
            headers={"WWW-Authenticate": _AUTH_REALM},
        )

    user, password = credentials
    is_valid = hmac.compare_digest(user, expected_user) and hmac.compare_digest(
        password, expected_password
    )
    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail="认证失败",
            headers={"WWW-Authenticate": _AUTH_REALM},
        )
