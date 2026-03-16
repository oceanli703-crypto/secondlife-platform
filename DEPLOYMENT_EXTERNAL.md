# 第二人生平台 - 外网部署指南

## 方案一：Render + Vercel（推荐，免费）

### 1. 部署后端到 Render

**步骤:**
1. 访问 https://render.com 注册账号
2. 点击 "New +" → "Blueprint"
3. 连接 GitHub 仓库（需要先推送到GitHub）
4. Render 会自动识别 `render.yaml` 配置
5. 等待部署完成（约3-5分钟）
6. 获得外网地址：`https://secondlife-api-xxxxx.onrender.com`

**注意:**
- 免费版15分钟无访问会休眠，下次访问需等待30秒唤醒
- 数据库使用SQLite，文件存储在临时目录（重启会重置）
- 如需持久化，需升级到付费版或使用PostgreSQL

### 2. 部署前端到 Vercel

**步骤:**
1. 访问 https://vercel.com 注册账号
2. 导入前端文件夹 `secondlife/frontend`
3. Vercel 自动识别 `vercel.json` 配置
4. 等待部署完成
5. 获得外网地址：`https://secondlife-xxxxx.vercel.app`

### 3. 修改前端API地址

在 `frontend/index.html` 中找到:
```javascript
const API_BASE = 'http://localhost:8000';
```

修改为 Render 提供的后端地址:
```javascript
const API_BASE = 'https://secondlife-api-xxxxx.onrender.com';
```

重新部署前端。

---

## 方案二：Railway（推荐，免费，支持SQLite持久化）

**步骤:**
1. 访问 https://railway.app 注册账号
2. 新建 Project → Deploy from GitHub repo
3. 选择后端代码目录
4. 添加环境变量 `SECRET_KEY`（随机字符串）
5. 部署完成后获得外网地址

**优点:**
- SQLite数据持久化
- 比Render更稳定

---

## 方案三：临时方案 - ngrok（5分钟搞定）

如果只是想临时演示，可以用ngrok：

```bash
# 安装ngrok
pip install pyngrok

# 启动隧道
ngrok http 8000
```

会获得类似 `https://xxxx.ngrok-free.app` 的公网地址，有效期8小时。

---

## 推荐的快速部署流程

### 第一步：创建GitHub仓库

```bash
cd /root/.openclaw/workspace/secondlife
git init
git add .
git commit -m "Initial commit"
# 然后在GitHub创建仓库并推送
```

### 第二步：部署后端（Render）

1. 登录 https://render.com
2. New → Web Service
3. 连接GitHub仓库
4. 配置:
   - Name: secondlife-api
   - Runtime: Python
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. 添加环境变量:
   - `SECRET_KEY`: 随机字符串（如 `openssl rand -base64 32`）
6. 创建服务

### 第三步：部署前端（Vercel）

1. 登录 https://vercel.com
2. Add New Project
3. 导入GitHub仓库
4. 根目录设置为 `frontend`
5. Framework Preset: Other
6. 修改 `index.html` 中的 `API_BASE` 为Render的地址
7. 部署

---

## 预计完成时间

- GitHub推送: 5分钟
- Render部署: 5分钟
- Vercel部署: 3分钟
- 总用时: **约15分钟**

---

## 部署后验证

1. 访问前端地址，应能看到登录页面
2. 注册测试账号
3. 发布测试任务
4. 确认后端API响应正常

---

## 注意事项

1. **免费版限制**:
   - Render免费版有休眠机制
   - Vercel免费版有带宽限制
   - 适合MVP验证，生产环境建议升级

2. **数据持久化**:
   - 当前使用SQLite，数据存储在服务器
   - Render免费版重启会丢失数据
   - 建议升级到PostgreSQL或使用Railway

3. **自定义域名**:
   - Render和Vercel都支持自定义域名
   - 在Dashboard中添加自定义域名即可
