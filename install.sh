#!/bin/bash
# ============================================================================
# NanoRTK 一键安装脚本
# 
# 功能：
#   1. 创建 Python 虚拟环境
#   2. 安装项目依赖
#   3. 安装 systemd 服务（可选）
#
# 使用方法：
#   ./install.sh          # 仅安装虚拟环境和依赖
#   sudo ./install.sh     # 安装虚拟环境、依赖并注册系统服务
# ============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的信息
info() {
    echo -e "${BLUE}[信息]${NC} $1"
}

success() {
    echo -e "${GREEN}[成功]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

error() {
    echo -e "${RED}[错误]${NC} $1"
}

# 分隔线
separator() {
    echo "============================================"
}

# ============================================================================
# 主程序
# ============================================================================

separator
echo -e "${GREEN}NanoRTK 一键安装程序${NC}"
separator
echo ""

# 获取脚本所在目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PROJECT_DIR="$SCRIPT_DIR"
info "项目目录: $PROJECT_DIR"

# 检测是否以 root 权限运行
IS_ROOT=false
if [ "$EUID" -eq 0 ]; then
    IS_ROOT=true
    REAL_USER=${SUDO_USER:-$USER}
    info "检测到 root 权限，将同时安装系统服务"
    info "实际用户: $REAL_USER"
else
    info "普通用户模式，仅安装虚拟环境和依赖"
fi
echo ""

# ============================================================================
# 步骤 1: 检查 Python 版本
# ============================================================================

separator
info "步骤 1/4: 检查 Python 环境"
separator

if ! command -v python3 &> /dev/null; then
    error "未找到 Python3，请先安装 Python 3.9+"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
info "Python 版本: $PYTHON_VERSION"

# 检查版本是否 >= 3.9
MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 9 ]); then
    error "需要 Python 3.9 或更高版本"
    exit 1
fi
success "Python 版本检查通过"
echo ""

# ============================================================================
# 步骤 2: 创建虚拟环境
# ============================================================================

separator
info "步骤 2/4: 创建虚拟环境"
separator

if [ -d ".venv" ]; then
    warn "虚拟环境已存在，跳过创建"
else
    info "正在创建虚拟环境..."
    python3 -m venv .venv
    success "虚拟环境创建成功"
fi
echo ""

# ============================================================================
# 步骤 3: 安装依赖
# ============================================================================

separator
info "步骤 3/4: 安装项目依赖"
separator

info "升级 pip..."
./.venv/bin/pip install --upgrade pip \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    -q

info "安装项目依赖..."
./.venv/bin/pip install \
    --trusted-host pypi.org \
    --trusted-host pypi.python.org \
    --trusted-host files.pythonhosted.org \
    -r requirements.txt

success "依赖安装完成"

# 显示已安装的包
echo ""
info "已安装的包："
./.venv/bin/pip list --format=columns | head -20
echo ""

# ============================================================================
# 步骤 4: 安装系统服务（仅 root 用户）
# ============================================================================

separator
info "步骤 4/4: 安装系统服务"
separator

if [ "$IS_ROOT" = true ]; then
    SERVICE_NAME="nanorkt.service"
    TARGET_PATH="/etc/systemd/system/$SERVICE_NAME"
    
    info "生成服务配置文件..."
    
    # 直接生成服务文件（不依赖模板）
    cat > $TARGET_PATH << EOF
[Unit]
Description=NanoRTK Base Station Web Service
After=network.target

[Service]
User=$REAL_USER
Group=$REAL_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/.venv/bin/python $PROJECT_DIR/run_web.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    success "服务文件已生成: $TARGET_PATH"
    
    info "注册服务..."
    systemctl daemon-reload
    systemctl enable $SERVICE_NAME
    
    info "启动服务..."
    systemctl restart $SERVICE_NAME
    
    # 等待服务启动
    sleep 2
    
    echo ""
    separator
    success "服务安装完成！"
    separator
    echo ""
    systemctl status $SERVICE_NAME --no-pager || true
    
    echo ""
    info "常用命令："
    echo "  启动服务: sudo systemctl start $SERVICE_NAME"
    echo "  停止服务: sudo systemctl stop $SERVICE_NAME"
    echo "  重启服务: sudo systemctl restart $SERVICE_NAME"
    echo "  查看状态: sudo systemctl status $SERVICE_NAME"
    echo "  查看日志: journalctl -u $SERVICE_NAME -f"
else
    warn "未使用 root 权限运行，跳过服务安装"
    echo ""
    info "如需安装系统服务，请运行："
    echo "  sudo ./install.sh"
fi

echo ""

# ============================================================================
# 完成
# ============================================================================

separator
success "安装完成！"
separator
echo ""
info "使用方法："
echo ""
echo "  方式一：手动运行（推荐调试时使用）"
echo "    source .venv/bin/activate"
echo "    python run_web.py"
echo ""
echo "  方式二：使用虚拟环境 Python"
echo "    ./.venv/bin/python run_web.py"
echo ""
if [ "$IS_ROOT" = true ]; then
    echo "  方式三：系统服务（已安装）"
    echo "    服务会开机自启，访问 http://树莓派IP:8000"
    echo ""
fi
info "Web 管理界面地址: http://localhost:8000"
echo ""
