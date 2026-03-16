#!/bin/bash
# GitHub Token推送脚本

echo "🔐 GitHub 认证推送"
echo "=================="
echo ""
echo "为了安全推送代码，需要使用 GitHub Personal Access Token"
echo ""
echo "获取Token步骤:"
echo "  1. 访问: https://github.com/settings/tokens"
echo "  2. 点击: Generate new token (classic)"
echo "  3. 选择有效期: No expiration"
echo "  4. 勾选权限: repo (完整仓库访问)"
echo "  5. 点击: Generate token"
echo "  6. 复制生成的token（只显示一次）"
echo ""
read -s -p "请输入GitHub Token: " TOKEN
echo ""
echo ""

# 使用token推送
cd /root/.openclaw/workspace/secondlife
git remote remove origin 2>/dev/null || true
git remote add origin "https://oceanli703:$TOKEN@github.com/oceanli703/secondlife-platform.git"
git branch -M main

if git push -u origin main; then
    echo ""
    echo "✅ 推送成功!"
    echo ""
    echo "🌐 仓库地址: https://github.com/oceanli703/secondlife-platform"
else
    echo ""
    echo "❌ 推送失败"
fi
