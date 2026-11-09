"""
Web 管理接口安全工具

提供管理接口访问控制与配置脱敏辅助函数。
"""

import copy
import ipaddress
import os
from typing import Any, Dict

from fastapi import HTTPException, Request


ADMIN_TOKEN_ENV = "NANORKT_ADMIN_TOKEN"
ADMIN_TOKEN_HEADER = "X-Admin-Token"
ADMIN_TOKEN_QUERY = "token"


def _is_loopback_request(request: Request) -> bool:
    """判断请求是否来自本机回环地址。"""
    client_host = request.client.host if request.client else ""
    if not client_host:
        return False

    try:
        return ipaddress.ip_address(client_host).is_loopback
    except ValueError:
        return client_host in {"localhost"}


def ensure_api_access(request: Request) -> None:
    """
    管理接口访问控制

    - 本机回环请求直接放行；
    - 远程请求必须提供正确的管理员令牌。
    """
    if _is_loopback_request(request):
        return

    expected_token = os.getenv(ADMIN_TOKEN_ENV, "").strip()
    if not expected_token:
        raise HTTPException(
            status_code=403,
            detail=f"远程访问被拒绝：未配置 {ADMIN_TOKEN_ENV}"
        )

    provided_token = (
        request.headers.get(ADMIN_TOKEN_HEADER)
        or request.query_params.get(ADMIN_TOKEN_QUERY)
        or ""
    )

    if provided_token != expected_token:
        raise HTTPException(status_code=403, detail="管理员令牌无效")


def mask_sensitive_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """对配置中的敏感字段做脱敏处理。"""
    masked = copy.deepcopy(config_data)
    ntrip_config = masked.get("ntrip")
    if isinstance(ntrip_config, dict) and "password" in ntrip_config:
        ntrip_config["password"] = ""
    return masked


def drop_empty_password(update_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    移除空密码更新，避免前端空值把现有密码覆盖掉。
    """
    ntrip_config = update_data.get("ntrip")
    if isinstance(ntrip_config, dict) and ntrip_config.get("password") == "":
        ntrip_config.pop("password", None)
        if not ntrip_config:
            update_data.pop("ntrip", None)
    return update_data
