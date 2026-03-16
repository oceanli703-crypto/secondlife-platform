# 第二人生平台 - 外网部署完成报告

## 📊 部署状态

**本地代码**: ✅ 已准备完毕
**部署配置**: ✅ 已生成（Render + Vercel）
**Git仓库**: ✅ 已初始化并提交

## 🚀 一键部署

执行以下命令开始部署：

```bash
/root/.openclaw/workspace/secondlife/deploy-now.sh
```

或：

```bash
cd /root/.openclaw/workspace/secondlife
bash deploy-now.sh
```

## 📋 部署步骤

### 第一步：执行部署脚本（2分钟）

```bash
bash /root/.openclaw/workspace/secondlife/deploy-now.sh
```

脚本会：
1. 检查环境
2. 询问GitHub用户名和仓库名
3. 推送代码到GitHub

### 第二步：部署后端到Render（5分钟）

1. 访问 https://render.com
2. 用GitHub账号登录
3. 点击 **New +** → **Web Service**
4. 选择 **Build and deploy from a Git repository**
5. 连接你的GitHub仓库 `secondlife-platform`
6. 填写配置：
   - **Name**: `secondlife-api`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
7. 点击 **Create Web Service**
8. 等待部署完成（显示 ✅ Live）
9. 记录域名：`https://secondlife-api-xxxxx.onrender.com`

### 第三步：部署前端到Vercel（3分钟）

1. 访问 https://vercel.com
2. 用GitHub账号登录
3. 点击 **Add New Project**
4. 导入GitHub仓库 `secondlife-platform`
5. 配置：
   - **Framework Preset**: `Other`
   - **Root Directory**: `frontend`
6. 点击 **Deploy**
7. 等待部署完成
8. 记录域名：`https://secondlife-platform-xxxx.vercel.app`

### 第四步：验证部署（2分钟）

1. 访问前端域名
2. 点击 **注册** 创建测试账号
3. 登录后发布测试任务
4. 确认功能正常

## 🌐 预期外网地址

部署完成后，您将获得：

| 服务 | 地址示例 |
|------|----------|
| 前端 | `https://secondlife-platform-xxx.vercel.app` |
| 后端 | `https://secondlife-api-xxx.onrender.com` |
| API文档 | `https://secondlife-api-xxx.onrender.com/api/docs` |

## ⚠️ 注意事项

### 免费版限制
- **Render免费版**：15分钟无访问会休眠，唤醒需30秒
- **Vercel免费版**：有带宽限制（适合初期）
- **数据持久化**：SQLite数据在Render重启后会重置

### 解决方案
如需数据持久化，建议：
1. 升级到Render付费版（$7/月）
2. 或改用Railway（免费版支持持久化）
3. 或使用PostgreSQL数据库

## 🛠️ 配置文件说明

已生成的部署配置文件：

| 文件 | 用途 |
|------|------|
| `render.yaml` | Render平台配置 |
| `vercel.json` | Vercel平台配置 |
| `Dockerfile` | Docker容器配置 |
| `.github/workflows/deploy.yml` | 自动部署工作流 |
| `deploy-now.sh` | 一键部署脚本 |

## 📞 故障排查

### 问题1：推送代码失败
**解决**：检查GitHub用户名和密码，如启用2FA需使用Personal Access Token

### 问题2：Render部署失败
**解决**：检查Build Command和Start Command是否正确

### 问题3：前端无法连接后端
**解决**：确认`frontend/index.html`中的`API_BASE`已改为Render地址

## ✅ 部署检查清单

- [ ] 代码已推送到GitHub
- [ ] Render后端部署成功
- [ ] Vercel前端部署成功
- [ ] 注册功能测试通过
- [ ] 登录功能测试通过
- [ ] 发布任务功能测试通过
- [ ] 任务列表功能测试通过

## 🎉 完成

部署完成后，您将拥有一个外网可访问的「第二人生」平台！

可以开始：
1. 推广获客
2. 寻找种子用户
3. 运营平台

---

**部署时间**：约10分钟  
**难度**：⭐⭐☆☆☆（简单）  
**成本**：免费
