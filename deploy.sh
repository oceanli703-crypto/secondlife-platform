#!/bin/bash

# 第二人生平台 - 部署脚本

echo "🚀 开始部署第二人生平台..."

# 创建数据目录
mkdir -p data

# 停止旧服务
echo "📦 停止旧服务..."
docker-compose down 2>/dev/null || true

# 构建并启动
echo "🔨 构建服务..."
docker-compose build

echo "▶️  启动服务..."
docker-compose up -d

# 等待服务启动
sleep 3

# 检查状态
echo "✅ 检查服务状态..."
docker-compose ps

echo ""
echo "🎉 部署完成！"
echo "📍 访问地址: http://localhost"
echo "📚 API文档: http://localhost/api/docs"
echo ""
echo "查看日志: docker-compose logs -f"
