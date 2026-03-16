#!/usr/bin/env python3
"""
第二人生平台 - 外网部署助手
一键部署到 Render + Vercel
"""

import subprocess
import os
import sys
import json

PROJECT_DIR = "/root/.openclaw/workspace/secondlife"

def run(cmd, cwd=None):
    """执行命令"""
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr

def check_git():
    """检查git"""
    success, _, _ = run("git --version")
    return success

def init_git():
    """初始化git仓库"""
    os.chdir(PROJECT_DIR)
    
    # 检查是否已初始化
    if os.path.exists(".git"):
        print("✅ Git仓库已存在")
        return True
    
    print("📁 初始化Git仓库...")
    run("git init")
    run("git config user.email 'deploy@secondlife.com'")
    run("git config user.name 'Deploy Bot'")
    
    # 创建.gitignore
    gitignore_content = """__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
pip-log.txt
.cache
*.log
.git
.mypy_cache
.pytest_cache

# 数据库
*.db
*.sqlite
*.sqlite3

# 环境变量
.env
.env.local
"""
    with open(".gitignore", "w") as f:
        f.write(gitignore_content)
    
    print("✅ Git仓库初始化完成")
    return True

def prepare_code():
    """准备代码"""
    os.chdir(PROJECT_DIR)
    
    print("📦 准备部署代码...")
    
    # 添加所有文件
    run("git add .")
    
    # 提交
    success, _, _ = run("git commit -m 'Deploy: Second Life Platform v1.0'")
    if success:
        print("✅ 代码已提交")
    else:
        print("ℹ️  没有新变更需要提交")
    
    return True

def show_instructions():
    """显示部署说明"""
    print("""
================================
🚀 外网部署方案（免费）
================================

推荐方案: Render(后端) + Vercel(前端)

【第一步】推送代码到GitHub
--------------------------------
1. 在GitHub创建新仓库:
   https://github.com/new
   
   设置:
   - Repository name: secondlife-platform
   - Visibility: Private (推荐)
   - 勾选: Add a README file

2. 推送代码:
   cd /root/.openclaw/workspace/secondlife
   git remote add origin https://github.com/你的用户名/secondlife-platform.git
   git branch -M main
   git push -u origin main

【第二步】部署后端到Render
--------------------------------
1. 访问: https://render.com
2. 注册/登录账号（可用GitHub账号）
3. 点击: New + → Web Service
4. 选择: Build and deploy from a Git repository
5. 连接GitHub仓库: secondlife-platform
6. 配置:
   - Name: secondlife-api
   - Runtime: Python 3
   - Build Command: pip install -r backend/requirements.txt
   - Start Command: cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT
   - Plan: Free
7. 点击: Create Web Service
8. 等待部署完成（约3-5分钟）
9. 记录分配的域名: https://secondlife-api-xxxxx.onrender.com

【第三步】部署前端到Vercel
--------------------------------
1. 访问: https://vercel.com
2. 注册/登录账号（可用GitHub账号）
3. 点击: Add New Project
4. 导入GitHub仓库: secondlife-platform
5. 配置:
   - Framework Preset: Other
   - Root Directory: frontend
6. 点击: Deploy
7. 等待部署完成（约1-2分钟）

【第四步】修改API地址
--------------------------------
1. 在前端代码中找到API地址配置
2. 将 localhost:8000 改为 Render 的域名
3. 重新部署前端

【第五步】验证
--------------------------------
1. 访问Vercel提供的域名
2. 测试注册/登录功能
3. 测试发布任务功能

================================
💡 注意事项
================================

1. 免费版限制:
   - Render免费版15分钟无访问会休眠
   - 唤醒需要约30秒
   - 适合演示和测试

2. 数据持久化:
   - 当前使用SQLite
   - Render免费版重启会丢失数据
   - 如需持久化，建议:
     a) 升级到Render付费版
     b) 或改用Railway（免费版支持持久化）

3. 自定义域名:
   - Render和Vercel都支持
   - 在Dashboard中添加即可

================================
📚 参考文档
================================

详细说明: /root/.openclaw/workspace/secondlife/DEPLOYMENT_EXTERNAL.md

================================
""")

def main():
    print("🚀 第二人生平台 - 外网部署助手")
    print("=" * 40)
    print()
    
    # 检查git
    if not check_git():
        print("❌ 未安装git，请先安装")
        sys.exit(1)
    print("✅ git已安装")
    print()
    
    # 初始化git
    if not init_git():
        print("❌ Git初始化失败")
        sys.exit(1)
    
    # 准备代码
    if not prepare_code():
        print("❌ 代码准备失败")
        sys.exit(1)
    
    # 显示说明
    show_instructions()
    
    print("🎉 准备完成！请按照上述步骤操作。")

if __name__ == "__main__":
    main()
