"""
Web API 安全控制模块

为敏感管理接口提供最小化访问控制：
- 本机回环请求默认放行（便于本地运维）
- 远程请求必须携带管理员令牌
"""

import os
from typing import Optional

from fastapi import HTTPException, Request


ADMIN_TOKEN_ENV = "NANORKT_ADMIN_TOKEN"
ADMIN_TOKEN_HEADER = "X-Admin-Token"


def _is_loopback_client(host: Optional[str]) -> bool:
    """判断请求是否来自本机回环地址。"""
    return host in {"127.0.0.1", "::1", "localhost"}


def ensure_api_access(request: Request) -> None:
    """
    校验敏感管理接口访问权限。

    规则：
    1. 回环地址访问直接放行；
    2. 非回环访问必须通过请求头携带有效管理员令牌。
    """
    client_host = request.client.host if request.client else None
    if _is_loopback_client(client_host):
        return

    expected_token = os.getenv(ADMIN_TOKEN_ENV, "").strip()
    provided_token = request.headers.get(ADMIN_TOKEN_HEADER, "").strip()

    if expected_token and provided_token == expected_token:
        return

    raise HTTPException(
        status_code=403,
        detail=(
            "访问被拒绝：远程管理接口需要管理员令牌。"
            f"请设置环境变量 {ADMIN_TOKEN_ENV} 并在请求头中携带 {ADMIN_TOKEN_HEADER}。"
        ),
    )
