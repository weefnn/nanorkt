"""
Web 服务启动配置模块。

用于集中管理监听地址和端口，避免默认暴露高权限控制接口。
"""

import logging
import os


def get_server_bind_config() -> tuple[str, int]:
    """
    获取 Web 服务监听配置。

    默认仅监听本机回环地址，避免在未配置鉴权时暴露控制接口。
    如需局域网访问，可显式设置 NANORTK_WEB_HOST=0.0.0.0。
    """
    host = os.getenv("NANORTK_WEB_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port_text = os.getenv("NANORTK_WEB_PORT", "8000").strip() or "8000"

    try:
        port = int(port_text)
    except ValueError:
        logging.warning("无效端口配置 NANORTK_WEB_PORT=%s，回退到 8000", port_text)
        port = 8000

    if host == "0.0.0.0":
        logging.warning(
            "Web 控制台已配置为对外监听（0.0.0.0）。请确保网络隔离或反向代理鉴权。"
        )

    return host, port
