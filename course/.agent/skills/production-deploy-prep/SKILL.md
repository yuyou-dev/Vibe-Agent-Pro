---
name: Production Deployment Protocol
description: 全栈 Node.js (Vite + BFF) 应用打包、PM2 配置及云服务器 80 端口部署的标准化工作流。
version: 2.0.0
---

# 🚀 生产环境部署协议（云服务器）

本协议定义了将集成 AI 的 Web 应用部署到 Linux 云服务器（如 Ubuntu/CentOS）的标准流程。它采用 **单体部署** 策略，将前端和后端中间件打包到一个目录中，由 PM2 管理，并直接运行在 80 端口上。

## 核心架构 (Core Architecture)

*   **BFF 模式 (Backend for Frontend)**: 不要仅通过 Nginx 直接提供前端服务。使用 Node.js 中间件 (`middleware_prod.cjs`) 来：
    1.  提供静态前端资源 (Vite `dist`)。
    2.  安全地处理 API 请求（隐藏 `AUTH_SECRET` 等敏感信息）。
    3.  管理 CORS 和上游 API 签名。
*   **统一打包**: 所有部署产物合并到一个文件夹中（例如 `dist_bundle/project-name`）。
*   **进程管理**: 使用 **PM2** 进行后台守护、日志管理和自动重启。
*   **80 端口**: 应用直接绑定 80 端口，提供标准 HTTP 访问。

---

## 🛠️ 步骤 1：项目准备（本地）

### 1.1 生产环境中间件 (`middleware_prod.cjs`)
创建一个专用的生产环境入口文件。它绝不能包含 `vite` 开发服务器的逻辑。
*   **静态文件**: 使用 `express.static(__dirname)` 来提供打包后的资源。
*   **API 路由**: 挂载与开发环境相同的 API 逻辑，但确保路径匹配生产环境 URL 结构（例如 `/app-name/api`）。
*   **兼容性**: 确保代码严格兼容 Node.js（如果 Node 版本 < 15.x，请避免使用 `crypto.randomUUID`）。

### 1.2 打包脚本 (`scripts/bundle.cjs`)
自动化打包过程。该脚本应执行以下操作：
1.  **清理**: 删除旧的打包文件。
2.  **构建**: 运行 `vite build`（确保 `vite.config.ts` 中的 `base` 路径与部署子路径匹配）。
3.  **复制**: 将 `dist/` 资源和 `middleware_prod.cjs` 移动到打包文件夹。
4.  **生成配置**:
    *   **package.json**: 生产环境专用（依赖项：`express`, `cors`, `dotenv`, `pm2`）。
    *   **ecosystem.config.cjs**: PM2 配置文件。

### 1.3 PM2 配置 (`ecosystem.config.cjs`)
生态系统文件模板：
```javascript
module.exports = {
  apps: [{
    name: "project-name",
    script: "./middleware_prod.cjs",
    env: {
      NODE_ENV: "production",
      PORT: 80 // 标准 HTTP 端口
    }
  }]
};
```

---

## 📦 步骤 2：执行打包

在本地运行打包脚本：
```bash
node scripts/bundle.cjs
```
**输出**: 在 `dist_bundle/project-name` 下生成经过检查的部署目录。

---

## ☁️ 步骤 3：服务器部署

### 3.1 上传
将打包好的目录传输到服务器（例如 `/www/wwwroot/` 或用户主目录）。
```bash
scp -r dist_bundle/project-name user@server:/path/to/deploy
```

### 3.2 环境变量配置
**关键**: 必须在服务器上的部署目录内手动创建 `.env` 文件。
```bash
cd /path/to/deploy/project-name
nano .env
```
*   `AUTH_SECRET`: [你的密钥]
*   `TARGET_BASE_URL`: [上游 API 地址]

### 3.3 安装与启动
使用 `npm` 安装生产依赖并通过 PM2 启动。
```bash
# 1. 安装依赖
npm install

# 2. 释放 80 端口（如果通过 fuser 检测到被占用）
sudo fuser -k 80/tcp

# 3. 使用 PM2 启动（后台守护模式）
npm start
# (注意: 'npm start' 应在 package.json 中配置为 'pm2 start ecosystem.config.cjs --no-daemon')
```

---

## 🔍 扩展性与最佳实践

1.  **目录结构**:
    *   如果由多个应用共存，请务必使用命名空间目录（如 `/project-a`, `/project-b`）。
    *   如果需要多个应用同时使用 80 端口，请使用 Nginx 反向代理（此时 PM2 的 PORT 应改为 3000+，并配置 proxy_pass）。
    *   **当前协议**: 假设是 **80 端口单应用独占** 的专用服务器部署。

2.  **Node 版本兼容性**:
    *   除非确定服务器运行的是 Node v15.6.0+，否则避免使用 `crypto.randomUUID()` 等新 API。
    *   建议使用 Polyfill 或辅助函数（如 `Math.random` 组合）以获得最大兼容性。

3.  **进程管理**:
    *   **查看日志**: `pm2 logs project-name`
    *   **重启**: `pm2 restart project-name`
    *   **停止**: `pm2 stop project-name`
    *   **开机自启**: 运行 `pm2 startup` 以确保服务器重启后应用自动启动。

4.  **安全性**:
    *   绝不要将 `.env` 或 `dist_bundle` 提交到 Git 仓库。
    *   在转发请求到昂贵的上游 API 之前，中间件必须验证签名/令牌。

---

## 🚨 故障排查

*   **错误: `EADDRINUSE: address already in use :::80`**
    *   **解决方法**: `sudo fuser -k 80/tcp` (杀掉占用 80 端口的进程)。
*   **错误: `crypto.randomUUID is not a function`**
    *   **解决方法**: 服务器 Node 版本较旧。请在代码中替换为自定义 ID 生成器。
*   **错误: 504 Gateway Timeout**
    *   **解决方法**: 检查 `.env` 中的 `TARGET_BASE_URL`，并确保中间件中的 `upstream` 超时设置足够长（AI 生成通常需要 60秒以上）。
