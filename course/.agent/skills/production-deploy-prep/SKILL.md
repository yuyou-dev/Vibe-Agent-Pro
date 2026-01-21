---
name: Production Deployment Prep
description: 自动编译前端并打包 Node.js 中间件，以备生产环境部署。
version: 1.0.1
---

# 生产环境部署准备 (Production Deployment Prep)

该 Skill 自动执行将应用准备为生产状态的过程。它主要执行两个任务：

1.  **构建前端**: 将 React/Vite 前端应用编译为静态资源 (`dist/`)，并确保其指向生产环境的中间件 URL。
2.  **打包中间件**: 将 Node.js 中间件打包为独立的、可部署单元 (`middleware_deploy/`)，包含其专属的 `package.json` 和配置。

## 前置条件

-   项目必须包含 `middleware.cjs` (或已配置的服务端文件)。
-   已安装 `npm` 或 `yarn`。

## 配置 (项目级)

为了避免在 Skill 中硬编码敏感信息，您必须在项目根目录下配置 `.env.production` 文件。**请勿将此文件提交到代码仓库。**

**`.env.production` 必需变量**:

```ini
# 前端配置
VITE_API_BASE_URL=https://api.your-domain.com/subpath

# 中间件配置 (可选 - 若存在将自动复制到部署包)
PORT=3005
TARGET_BASE_URL=https://api.target-service.com
AUTH_SECRET=your_secret_here
```

## 使用方法

**一句话启动命令**:

> **"请帮我准备生产环境部署包，使用 .env.production 的配置。"**

或者在终端运行脚本:

```bash
node .agent/skills/production-deploy-prep/scripts/package_dist.cjs
```

## 工作流详情

1.  **环境检查**: 验证 `.env.production` 是否存在并包含 `VITE_API_BASE_URL`。
2.  **构建前端**: 运行 `npm run build`。构建过程将使用环境变量中定义的 `VITE_API_BASE_URL`。
3.  **打包中间件**:
    *   清理/创建 `middleware_deploy` 目录。
    *   将 `middleware.cjs` 复制为 `index.js`。
    *   生成专用的 `package.json` (自动提取或使用标准依赖)。
    *   生成 `middleware_deploy/.env`，并使用本地 `.env.production` 中的值（如果缺失则使用占位符）进行填充。
    *   生成包含部署说明的 `README.md`。

## 自定义

您可以修改 `scripts/package_dist.cjs` 来调整默认的中间件文件名或依赖版本。
