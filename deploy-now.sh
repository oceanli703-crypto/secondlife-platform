#!/bin/bash
# 第二人生平台 - 一键外网部署脚本

set -e

echo "🚀 第二人生平台 - 一键外网部署"
echo "================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目目录
PROJECT_DIR="/root/.openclaw/workspace/secondlife"
cd "$PROJECT_DIR"

echo -e "${GREEN}✅${NC} 当前目录: $(pwd)"
echo ""

# 检查git
echo "📦 检查环境..."
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ 未安装git${NC}"
    exit 1
fi
echo -e "${GREEN}✅${NC} git已安装"

# 获取GitHub信息
echo ""
echo "================================"
echo "📝 GitHub配置"
echo "================================"
echo ""

read -p "请输入GitHub用户名: " GITHUB_USER
read -p "请输入仓库名 [secondlife-platform]: " REPO_NAME
REPO_NAME=${REPO_NAME:-secondlife-platform}

echo ""
echo -e "${YELLOW}提示:${NC} 如果您启用了2FA，需要使用Personal Access Token代替密码"
echo -e "${YELLOW}提示:${NC} 访问 https://github.com/settings/tokens 创建Token"
echo ""

# 配置远程仓库
echo "🔗 配置远程仓库..."
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"

echo ""
echo "🚀 推送代码到GitHub..."
echo "================================"

if git push -u origin master 2>&1 || git push -u origin main 2>&1; then
    echo ""
    echo -e "${GREEN}✅ 代码推送成功！${NC}"
    echo ""
    echo "🌐 仓库地址: https://github.com/$GITHUB_USER/$REPO_NAME"
    echo ""
else
    echo ""
    echo -e "${RED}❌ 推送失败${NC}"
    echo ""
    echo "可能原因:"
    echo "  1. GitHub仓库不存在"
    echo "  2. 用户名/密码错误"
    echo "  3. 需要Personal Access Token（如果启用了2FA）"
    echo ""
    echo "手动创建仓库:"
    echo "  1. 访问 https://github.com/new"
    echo "  2. Repository name: $REPO_NAME"
    echo "  3. 点击 Create repository"
    echo ""
    exit 1
fi

# 生成部署指南
echo ""
echo "================================"
echo "📋 下一步：部署到Render"
echo "================================"
echo ""
echo "1. 访问 https://render.com"
echo "2. 点击 'New +' → 'Web Service'"
echo "3. 选择 'Build and deploy from a Git repository'"
echo "4. 连接GitHub仓库: $REPO_NAME"
echo "5. 配置:"
echo "   - Name: secondlife-api"
echo "   - Runtime: Python 3"
echo "   - Build Command: pip install -r backend/requirements.txt"
echo "   - Start Command: cd backend && uvicorn app.main:app --host 0.0.0.0 --port \$PORT"
echo "   - Plan: Free"
echo "6. 点击 'Create Web Service'"
echo ""
echo "================================"
echo "📋 下一步：部署到Vercel"
echo "================================"
echo ""
echo "1. 访问 https://vercel.com"
echo "2. 点击 'Add New Project'"
echo "3. 导入GitHub仓库: $REPO_NAME"
echo "4. 配置:"
echo "   - Framework Preset: Other"
echo "   - Root Directory: frontend"
echo "5. 点击 'Deploy'"
echo ""
echo "================================"
echo "🎉 部署准备完成！"
echo "================================"
echo ""
echo "预计外网地址:"
echo "  后端: https://secondlife-api.onrender.com"
echo "  前端: https://$REPO_NAME-$GITHUB_USER.vercel.app"
echo ""
echo "完成部署后:"
echo "  1. 测试注册/登录功能"
echo "  2. 测试发布任务功能"
echo "  3. 开始使用平台"
echo ""
