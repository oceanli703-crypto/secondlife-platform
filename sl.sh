#!/bin/bash
# 第二人生平台 - 管理脚本

BACKEND_DIR="/root/.openclaw/workspace/secondlife/backend"
FRONTEND_DIR="/root/.openclaw/workspace/secondlife/frontend"

case "$1" in
  start)
    echo "🚀 启动第二人生平台..."
    cd $BACKEND_DIR && python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/sl.log 2>&1 &
    cd $FRONTEND_DIR && python3 -m http.server 8080 > /tmp/fe.log 2>&1 &
    sleep 2
    echo "✅ 服务已启动"
    echo "  后端: http://localhost:8000"
    echo "  前端: http://localhost:8080"
    ;;
  stop)
    echo "🛑 停止服务..."
    pkill -f "uvicorn.*secondlife" 2>/dev/null
    pkill -f "http.server 8080" 2>/dev/null
    echo "✅ 服务已停止"
    ;;
  status)
    echo "📊 服务状态:"
    curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "  后端: 未运行"
    curl -s -o /dev/null -w "  前端: %{http_code}\n" http://localhost:8080/ 2>/dev/null || echo "  前端: 未运行"
    ;;
  logs)
    echo "📜 后端日志:"
    tail -20 /tmp/sl.log
    ;;
  *)
    echo "用法: $0 {start|stop|status|logs}"
    exit 1
    ;;
esac
