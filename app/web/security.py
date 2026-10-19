"""
Web API 安全访问控制。

策略：
1. 回环地址（本机）请求直接放行，便于本机运维。
2. 非本机请求必须携带管理员令牌。
"""

import ipaddress
import os
import secrets
from typing import Optional

from fastapi import HTTPException, Request, status


ADMIN_TOKEN_ENV = "NANORKT_ADMIN_TOKEN"
ADMIN_TOKEN_HEADER = "X-Admin-Token"


def _is_loopback_address(host: Optional[str]) -> bool:
    """判断来源是否为本机回环地址。"""
    if not host:
        return False
    if host == "localhost":
        return True

    # 某些 IPv6 地址可能包含 scope id（例如 ::1%lo0）
    host_without_scope = host.split("%", 1)[0]
    try:
        return ipaddress.ip_address(host_without_scope).is_loopback
    except ValueError:
        return False


def ensure_api_access(request: Request) -> None:
    """
    校验敏感 API 的访问权限。

    非回环请求要求提供管理员令牌，否则返回 403。
    """
    client_host = request.client.host if request.client else None
    if _is_loopback_address(client_host):
        return

    expected_token = os.getenv(ADMIN_TOKEN_ENV, "").strip()
    provided_token = (
        request.headers.get(ADMIN_TOKEN_HEADER)
        or request.query_params.get("token", "").strip()
    )

    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"远程访问已禁用。请设置环境变量 {ADMIN_TOKEN_ENV}，"
                f"并在请求头 {ADMIN_TOKEN_HEADER} 中携带管理员令牌。"
            ),
        )

    if not provided_token or not secrets.compare_digest(provided_token, expected_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理员令牌无效",
        )
