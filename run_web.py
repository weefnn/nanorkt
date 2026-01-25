#!/usr/bin/env python3
"""
NanoRTK Web 应用启动脚本

使用方式：
    python run_web.py
    
或者：
    ./run_web.py  (需要先执行 chmod +x run_web.py)
"""

import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 导入并运行主函数
from app.web.app import main

if __name__ == "__main__":
    main()
