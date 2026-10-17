"""
Web 安全访问控制模块

默认仅允许本机（loopback）访问敏感 API。
如需远程访问，可设置环境变量 NANORTK_API_TOKEN，
并在请求中附带 X-API-Token 或 Authorization: Bearer <token>。
"""

from __future__ import annotations

import hmac
import ipaddress
import os
from typing import Optional

from fastapi import HTTPException, Request


API_TOKEN_ENV = "NANORTK_API_TOKEN"


def _is_loopback_host(host: Optional[str]) -> bool:
    """
    检查客户端地址是否为本机回环地址。
    """
    if not host:
        return False

    # 常见 hostname 快速判断
    if host in {"localhost", "ip6-localhost"}:
        return True

    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _extract_token(request: Request) -> str:
    """
    从请求头提取访问令牌。
    """
    header_token = request.headers.get("x-api-token", "").strip()
    if header_token:
        return header_token

    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[len("Bearer ") :].strip()

    return ""


def ensure_api_access(request: Request) -> None:
    """
    校验敏感 API 的访问权限。

    规则：
    1. 本机回环地址直接放行；
    2. 非回环地址需提供与 NANORTK_API_TOKEN 匹配的令牌。
    """
    client_host = request.client.host if request.client else None
    if _is_loopback_host(client_host):
        return

    expected_token = os.getenv(API_TOKEN_ENV, "").strip()
    provided_token = _extract_token(request)

    if expected_token and provided_token and hmac.compare_digest(
        provided_token, expected_token
    ):
        return

    raise HTTPException(
        status_code=403,
        detail=(
            "Access denied. Remote access requires API token. "
            f"Set {API_TOKEN_ENV} and send it via X-API-Token or Bearer token."
        ),
    )
