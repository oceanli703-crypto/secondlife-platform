#!/bin/bash
# 一键外网访问 - ngrok方案

echo "🌐 第二人生平台 - 外网访问配置"
echo "================================"
echo ""

# 检查本地服务
echo "📡 检查本地服务..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ 后端服务正常 (端口8000)"
else
    echo "❌ 后端服务未启动，正在启动..."
    cd /root/.openclaw/workspace/secondlife
    python3 sl_service.py start
    sleep 3
fi

if curl -s -o /dev/null http://localhost:8080; then
    echo "✅ 前端服务正常 (端口8080)"
else
    echo "❌ 前端服务未启动，正在启动..."
    cd /root/.openclaw/workspace/secondlife/frontend
    nohup python3 -m http.server 8080 > /tmp/fe.log 2>&1 &
    sleep 2
fi

echo ""
echo "🔧 安装ngrok..."

# 安装ngrok
if ! command -v ngrok &> /dev/null; then
    curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
    echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | tee /etc/apt/sources.list.d/ngrok.list > /dev/null
    apt update && apt install -y ngrok 2>/dev/null || pip install pyngrok
fi

echo ""
echo "🚀 启动ngrok隧道..."
echo ""
echo "================================"
echo "正在创建外网访问地址..."
echo "================================"
echo ""

# 启动ngrok（后台运行）
nohup ngrok http 8080 --log=stdout > /tmp/ngrok.log 2>&1 &
echo "⏳ 等待ngrok启动（约10秒）..."
sleep 10

# 获取外网地址
URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys,json; data=json.load(sys.stdin); print([t['public_url'] for t in data['tunnels'] if 'https' in t['public_url']][0])" 2>/dev/null)

if [ -n "$URL" ]; then
    echo ""
    echo "✅ 外网访问地址已生成！"
    echo ""
    echo "================================"
    echo "🌐 平台外网地址"
    echo "================================"
    echo ""
    echo "  前端页面: $URL"
    echo "  后端API:  http://localhost:8000 (本地)"
    echo ""
    echo "================================"
    echo "⚠️  注意"
    echo "================================"
    echo ""
    echo "  • 此地址有效期约8小时"
    echo "  • 停止后重新运行脚本可获得新地址"
    echo "  • 如需永久地址，请使用Render+Vercel部署"
    echo ""
    echo "查看ngrok状态: http://localhost:4040"
    echo ""
else
    echo "❌ 获取外网地址失败"
    echo "请检查: http://localhost:4040"
fi
