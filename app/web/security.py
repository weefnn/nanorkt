"""
Web API 安全工具

提供管理接口访问控制与敏感配置脱敏能力。
"""

from __future__ import annotations

import copy
import hmac
import os
from ipaddress import ip_address
from typing import Any, Dict

from fastapi import HTTPException, Request


MASKED_PASSWORD = "********"


def _is_loopback_host(host: str) -> bool:
    """判断客户端地址是否为本机回环地址。"""
    if not host:
        return False

    if host == "localhost":
        return True

    try:
        return ip_address(host.split("%", 1)[0]).is_loopback
    except ValueError:
        return False


def ensure_api_access(request: Request) -> None:
    """
    校验管理 API 访问权限。

    - 回环地址默认允许访问；
    - 非回环访问必须携带匹配的 X-Admin-Token。
    """
    client_host = request.client.host if request.client else ""
    if _is_loopback_host(client_host):
        return

    expected_token = os.getenv("NANORKT_ADMIN_TOKEN", "").strip()
    if not expected_token:
        raise HTTPException(
            status_code=403,
            detail="远程访问已禁用：请配置 NANORKT_ADMIN_TOKEN"
        )

    provided_token = request.headers.get("X-Admin-Token", "").strip()
    if not provided_token or not hmac.compare_digest(provided_token, expected_token):
        raise HTTPException(status_code=401, detail="未授权访问")


def mask_config_for_display(config: Dict[str, Any]) -> Dict[str, Any]:
    """返回用于展示的配置副本，敏感字段以掩码替代。"""
    sanitized = copy.deepcopy(config)
    ntrip = sanitized.get("ntrip")
    if isinstance(ntrip, dict) and ntrip.get("password"):
        ntrip["password"] = MASKED_PASSWORD
    return sanitized
