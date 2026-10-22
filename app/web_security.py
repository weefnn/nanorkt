"""
Web 安全相关辅助函数。

保持该模块无第三方依赖，便于在轻量测试环境中直接验证。
"""

from copy import deepcopy
from typing import Any, Dict


def mask_sensitive_config(config_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    脱敏配置中的敏感字段，避免通过 API 返回明文密码。
    """
    masked = deepcopy(config_data)
    ntrip_cfg = masked.get("ntrip")
    if isinstance(ntrip_cfg, dict) and "password" in ntrip_cfg:
        ntrip_cfg["password"] = ""
    return masked


def drop_empty_password(update_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    移除空密码更新，防止前端留空时覆盖已有密码。
    """
    sanitized = deepcopy(update_data)
    ntrip_cfg = sanitized.get("ntrip")

    if isinstance(ntrip_cfg, dict):
        password = ntrip_cfg.get("password")
        if isinstance(password, str) and not password.strip():
            ntrip_cfg.pop("password", None)

        if not ntrip_cfg:
            sanitized.pop("ntrip", None)

    return sanitized
