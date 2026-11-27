"""
Web 管理接口安全控制模块。

策略：
- 回环地址（127.0.0.1 / ::1）默认放行，便于本机运维。
- 非回环地址必须提供管理员令牌（X-Admin-Token）。
"""

import hmac
import ipaddress
import os

from fastapi import HTTPException, Request


def _extract_client_ip(request: Request) -> str:
    """提取客户端 IP，优先使用反向代理转发头。"""
    forwarded = request.headers.get("x-forwarded-for", "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()

    if request.client and request.client.host:
        return request.client.host

    return ""


def _is_loopback(client_ip: str) -> bool:
    """判断客户端是否为回环地址。"""
    if not client_ip:
        return False

    try:
        return ipaddress.ip_address(client_ip).is_loopback
    except ValueError:
        return False


def ensure_api_access(request: Request) -> None:
    """
    校验管理接口访问权限。

    Raises:
        HTTPException: 鉴权失败时抛出 403
    """
    client_ip = _extract_client_ip(request)
    if _is_loopback(client_ip):
        return

    expected_token = os.getenv("NANORKT_ADMIN_TOKEN", "").strip()
    provided_token = request.headers.get("X-Admin-Token", "").strip()

    if not expected_token:
        raise HTTPException(
            status_code=403,
            detail="远程访问已禁用：请设置 NANORKT_ADMIN_TOKEN 后重试"
        )

    if not provided_token or not hmac.compare_digest(provided_token, expected_token):
        raise HTTPException(status_code=403, detail="管理员令牌无效")
