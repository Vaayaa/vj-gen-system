#!/bin/bash
# Madmom Audio Analysis Web - 启动脚本
# 使用方式: ./start.sh [port]

set -e

PORT=${1:-5001}
VENV_DIR=~/.virtualenvs/madmom-web
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 检查虚拟环境
if [ ! -d "$VENV_DIR" ]; then
    echo "创建虚拟环境..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install flask flask-cors librosa madmom 'setuptools<75'
fi

# 启动 Flask 服务
cd "$SCRIPT_DIR"
echo "启动 Madmom 音频分析服务..."
"$VENV_DIR/bin/python" app.py --port "$PORT"

