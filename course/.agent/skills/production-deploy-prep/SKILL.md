---
name: Production Deployment Protocol
description: 步骤 3：打包发布。合并前端静态资源与后端中间件，生成包含 PM2 守护配置的独立部署包。
---

# 📦 阶段 3：生产环境打包与部署准备 (Make it Deployable)

目标：将 Vite 编译的静态网页和 `middleware.cjs` 融为一体，生成可以直接放进云服务器并由 PM2 运行的生产包。

## 📋 执行清单 (SOP)

### [ ] 0. 预检：Web API 兼容性检查 (HTTP 环境适配)
- 如果目标服务器可能通过非安全上下文 (HTTP 或非 localhost 的 IP) 访问：
  - 必须全局检索项目中是否使用了仅限安全环境的 Web API (如 `crypto.randomUUID()`)。
  - 对于 `crypto.randomUUID()`，请替换为安全的通用回退方案。例如：
    ```javascript
    // 替换为：
    const id = Date.now().toString(36) + Math.random().toString(36).substring(2);
    ```

### [ ] 1. 补充中间件的静态资源服务 (`middleware.cjs`)
- 打开 `middleware.cjs`，在**所有的 API 路由定义完毕的最底部**，添加以下代码：
\`\`\`javascript
const path = require('path');

// 生产环境：托管 Vite 构建的 dist 目录
app.use(express.static(path.join(__dirname, 'dist')));

// SPA 路由回退：确保 React 路由刷新不报 404
app.get('*', (req, res) => {
    res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

// 优先使用环境变量端口 (如云服务器的 80)
const PORT = process.env.PORT || 3005;
// 注意修改 app.listen 使用 PORT 变量
\`\`\`

### [ ] 2. 自动化打包组装
- 执行 `npm run build`，确保生成前端 `dist` 目录。
- 创建名为 `dist_bundle` 的最终部署文件夹。
- 将前端生成的 `dist` 文件夹完整拷贝到 `dist_bundle/dist`。
- 将 `middleware.cjs` 拷贝到 `dist_bundle/middleware.cjs`。
- **必须将环境配置 `.env.local` 拷贝到 `dist_bundle/.env.local`** (代理鉴权强依赖此文件)。

### [ ] 3. 生成生产级配置文件
- 在 `dist_bundle` 目录下生成线上专属的 `package.json`：
\`\`\`json
{
  "name": "jewelry-ai-studio-prod",
  "main": "middleware.cjs",
  "dependencies": { "express": "^4.21.0", "cors": "^2.8.5", "dotenv": "^16.4.5" }
}
\`\`\`
- 在 `dist_bundle` 目录下生成 `ecosystem.config.js`，为 PM2 准备守护配置 (注意：后缀必须是 .js，不能是 .cjs，否则默认的 pm2 start 会无法识别)：
\`\`\`javascript
module.exports = {
  apps: [{
    name: "jewelry-ai-studio",
    script: "./middleware.cjs",
    env: { NODE_ENV: "production", PORT: 80 }
  }]
};
\`\`\`