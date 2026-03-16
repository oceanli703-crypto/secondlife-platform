# 第二人生平台 - 简化部署方案

## 问题
GitHub仓库访问遇到问题

## 解决方案：直接本地部署 + ngrok临时外网访问

### 第一步：启动本地服务
```bash
cd /root/.openclaw/workspace/secondlife
python3 sl_service.py start
```

### 第二步：安装ngrok
```bash
pip install pyngrok
```

### 第三步：启动外网隧道
```bash
ngrok http 8080
```

这将生成一个临时外网地址，如：`https://xxxx.ngrok-free.app`

有效期8小时，可以随时重新启动获得新地址。

---

## 或者：使用 Railway 一键部署

Railway支持直接从代码部署，无需GitHub：

1. 访问 https://railway.app
2. 注册账号
3. 点击 New Project
4. 选择 Deploy from GitHub（后续连接）

---

## 或者：我来帮您重新配置

如果您想继续使用GitHub，请确认：
1. 仓库是否已创建？
2. 仓库名是否正确？
3. 是否为 `oceanli703/secondlife-platform`？
