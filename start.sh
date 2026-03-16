#!/bin/bash
# Render启动脚本 - 确保正确启动

echo "🚀 启动第二人生后端服务..."
echo "📍 当前目录: $(pwd)"
echo "📋 Python版本: $(python --version)"

# 设置环境变量
export PORT=${PORT:-8000}

echo "🔧 端口: $PORT"

# 启动服务
cd backend
exec uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1 --log-level info
