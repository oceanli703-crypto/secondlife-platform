#!/bin/bash
# 第二人生平台 - 自动部署脚本 (Ocean Li)

set -e

echo "🚀 第二人生平台 - 自动部署"
echo "================================"
echo ""

PROJECT_DIR="/root/.openclaw/workspace/secondlife"
cd "$PROJECT_DIR"

# GitHub配置
GITHUB_USER="oceanli703"
GITHUB_EMAIL="oceanli703@gmail.com"
REPO_NAME="secondlife-platform"

echo "📋 配置信息:"
echo "  GitHub用户: $GITHUB_USER"
echo "  邮箱: $GITHUB_EMAIL"
echo "  仓库: $REPO_NAME"
echo ""

# 配置git
git config user.email "$GITHUB_EMAIL"
git config user.name "Ocean Li"

# 检查是否有未提交的更改
if [ -n "$(git status --porcelain)" ]; then
    echo "📦 提交最新更改..."
    git add .
    git commit -m "Update deployment configs - $(date '+%Y-%m-%d %H:%M:%S')" 2>/dev/null || true
fi

# 配置远程仓库
echo "🔗 配置远程仓库..."
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/$GITHUB_USER/$REPO_NAME.git"

echo ""
echo "📤 准备推送代码到GitHub..."
echo "================================"
echo ""
echo "⚠️  注意: 您需要先在GitHub创建仓库"
echo ""
echo "快速创建:"
echo "  1. 访问: https://github.com/new"
echo "  2. Repository name: $REPO_NAME"
echo "  3. Visibility: Public 或 Private"
echo "  4. 勾选: Add a README file"
echo "  5. 点击: Create repository"
echo ""
read -p "仓库已创建? (按Enter继续): "

echo ""
echo "🚀 推送代码..."
if git push -u origin master 2>/dev/null || git push -u origin main 2>/dev/null; then
    echo ""
    echo "✅ 代码推送成功!"
    echo ""
    echo "🌐 仓库地址: https://github.com/$GITHUB_USER/$REPO_NAME"
    echo ""
    
    # 生成Render和Vercel的快速链接
    echo "================================"
    echo "📋 下一步: 部署到Render"
    echo "================================"
    echo ""
    echo "快速链接:"
    echo "  https://dashboard.render.com/select-repo?type=web"
    echo ""
    echo "步骤:"
    echo "  1. 点击 'New Web Service'"
    echo "  2. 选择 GitHub 登录"
    echo "  3. 选择仓库: $REPO_NAME"
    echo "  4. 配置:"
    echo "     Name: secondlife-api"
    echo "     Runtime: Python 3"
    echo "     Build: pip install -r backend/requirements.txt"
    echo "     Start: cd backend && uvicorn app.main:app --host 0.0.0.0 --port \$PORT"
    echo ""
    
    echo "================================"
    echo "📋 下一步: 部署到Vercel"
    echo "================================"
    echo ""
    echo "快速链接:"
    echo "  https://vercel.com/new"
    echo ""
    echo "步骤:"
    echo "  1. 导入GitHub仓库: $REPO_NAME"
    echo "  2. Framework Preset: Other"
    echo "  3. Root Directory: frontend"
    echo "  4. 点击 Deploy"
    echo ""
    
    echo "================================"
    echo "🎉 准备就绪!"
    echo "================================"
    echo ""
    echo "预期外网地址:"
    echo "  后端: https://secondlife-api.onrender.com"
    echo "  前端: https://secondlife-platform.vercel.app"
    echo ""
else
    echo ""
    echo "❌ 推送失败"
    echo ""
    echo "可能原因:"
    echo "  1. GitHub仓库不存在 - 请先创建"
    echo "  2. 需要登录凭证"
    echo ""
    echo "手动推送命令:"
    echo "  cd $PROJECT_DIR"
    echo "  git push -u origin master"
    echo ""
fi
