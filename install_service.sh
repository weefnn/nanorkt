#!/bin/bash

# 确保脚本以 root 权限运行
if [ "$EUID" -ne 0 ]; then 
  echo "请使用 sudo 运行此脚本"
  exit 1
fi

echo "=========================================="
echo "NanoRTK 服务自动安装程序"
echo "=========================================="

# 1. 获取当前目录和实际用户
PROJECT_DIR=$(pwd)
REAL_USER=${SUDO_USER:-$USER}

echo "检测到安装路径: $PROJECT_DIR"
echo "检测到运行用户: $REAL_USER"

# 2. 生成最终的 .service 文件
SERVICE_NAME="nanorkt.service"
TARGET_PATH="/etc/systemd/system/$SERVICE_NAME"

echo "正在生成服务文件..."
# 读取模板，替换占位符，写入系统目录
sed -e "s|{{PROJECT_DIR}}|$PROJECT_DIR|g" \
    -e "s|{{USER}}|$REAL_USER|g" \
    nanorkt.service.template > $TARGET_PATH

echo "服务文件已生成: $TARGET_PATH"

# 3. 重新加载 Systemd 并启用服务
echo "正在注册服务..."
systemctl daemon-reload
systemctl enable $SERVICE_NAME

echo "正在尝试启动服务..."
systemctl restart $SERVICE_NAME

# 4. 检查状态
echo "=========================================="
echo "安装完成！服务状态如下："
systemctl status $SERVICE_NAME --no-pager

echo ""
echo "常用命令："
echo "  停止服务: sudo systemctl stop $SERVICE_NAME"
echo "  查看日志: journalctl -u $SERVICE_NAME -f"
echo "=========================================="