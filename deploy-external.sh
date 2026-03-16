#!/bin/bash
# 第二人生平台 - 一键外网部署脚本

echo "🚀 第二人生平台 - 外网部署助手"
echo "================================"
echo ""

# 检查git
echo "📦 检查环境..."
if ! command -v git &> /dev/null; then
    echo "❌ 未安装git，请先安装"
    exit 1
fi
echo "✅ git已安装"

# 进入项目目录
cd /root/.openclaw/workspace/secondlife

# 初始化git（如果没有）
if [ ! -d ".git" ]; then
    echo "📁 初始化Git仓库..."
    git init
    git config user.email "deploy@secondlife.com"
    git config user.name "Deploy Bot"
fi

# 创建.gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
pip-log.txt
pip-delete-this-directory.txt
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis

# 数据库
*.db
*.sqlite
*.sqlite3

# 环境变量
.env
.env.local

# 日志
*.log
/tmp/
EOF

echo "✅ .gitignore已创建"

# 添加所有文件
echo "📤 准备提交代码..."
git add .
git commit -m "Deploy: Second Life Platform v1.0" 2>/dev/null || echo "✅ 代码已是最新"

echo ""
echo "================================"
echo "📋 下一步操作："
echo "================================"
echo ""
echo "1️⃣  在GitHub创建新仓库:"
echo "   访问: https://github.com/new"
echo "   仓库名: secondlife-platform"
echo "   选择: Private (私密)"
echo ""
echo "2️⃣  推送代码到GitHub:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/secondlife-platform.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "3️⃣  部署到Render (后端):"
echo "   访问: https://render.com"
echo "   点击: New → Web Service"
echo "   选择: Build from GitHub"
echo "   配置:"
echo "     - Name: secondlife-api"
echo "     - Runtime: Python"
echo "     - Build: pip install -r backend/requirements.txt"
echo "     - Start: cd backend && uvicorn app.main:app --host 0.0.0.0 --port \$PORT"
echo ""
echo "4️⃣  部署到Vercel (前端):"
echo "   访问: https://vercel.com"
echo "   点击: Add New Project"
echo "   导入: frontend文件夹"
echo "   修改: index.html中的API_BASE地址"
echo ""
echo "📖 详细说明见: DEPLOYMENT_EXTERNAL.md"
echo ""

# 询问是否自动推送
read -p "是否需要自动执行git命令推送代码? (y/n): " answer

if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
    echo ""
    read -p "请输入GitHub用户名: " username
    read -p "请输入仓库名 (默认: secondlife-platform): " repo
    repo=${repo:-secondlife-platform}
    
    echo ""
    echo "🚀 推送代码到GitHub..."
    git remote remove origin 2>/dev/null
    git remote add origin "https://github.com/$username/$repo.git"
    git branch -M main
    
    if git push -u origin main; then
        echo ""
        echo "✅ 推送成功!"
        echo ""
        echo "🌐 仓库地址: https://github.com/$username/$repo"
        echo ""
        echo "接下来请:"
        echo "1. 访问 https://render.com 部署后端"
        echo "2. 访问 https://vercel.com 部署前端"
    else
        echo ""
        echo "❌ 推送失败，可能原因:"
        echo "   - GitHub仓库不存在，请先创建"
        echo "   - 未配置SSH密钥或登录凭证"
        echo ""
        echo "手动推送命令:"
        echo "   git remote add origin https://github.com/$username/$repo.git"
        echo "   git push -u origin main"
    fi
fi

echo ""
echo "================================"
echo "🎉 部署助手完成!"
echo "================================"
