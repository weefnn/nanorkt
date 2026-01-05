#!/bin/bash
# 创建 Python 虚拟环境并安装依赖

set -e

echo "=========================================="
echo "RTK 基站项目 - 虚拟环境设置"
echo "=========================================="
echo ""

# 检查 Python 版本
echo "检查 Python 版本..."
python3 --version

# 创建虚拟环境
echo ""
echo "创建虚拟环境..."
if [ -d ".venv" ]; then
    echo "虚拟环境已存在，跳过创建"
else
    python3 -m venv .venv
    echo "虚拟环境创建成功"
fi

# 激活虚拟环境并升级 pip
echo ""
echo "升级 pip..."
./.venv/bin/pip install --upgrade pip --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org

# 安装依赖
echo ""
echo "安装项目依赖..."
./.venv/bin/pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org -r requirements.txt

# 显示已安装的包
echo ""
echo "=========================================="
echo "已安装的包："
echo "=========================================="
./.venv/bin/pip list

echo ""
echo "=========================================="
echo "虚拟环境设置完成！"
echo "=========================================="
echo ""
echo "使用方法："
echo "  激活虚拟环境: source .venv/bin/activate"
echo "  退出虚拟环境: deactivate"
echo "  或直接使用: ./.venv/bin/python <脚本>"
echo ""

