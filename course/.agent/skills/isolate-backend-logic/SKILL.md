---
name: Middleware Logic Isolation (BFF Pattern)
description: "将简单的本地代理重构为专用的 Node.js 中间层（Backend for Frontend），用于封装核心 AI 逻辑、提示词和敏感配置，使其与前端彻底隔离。"
version: 1.1.0
---

# 🛡️ 中间层逻辑隔离与核心保护 (BFF模式)

本 Skill 指导 Agent 将核心业务逻辑和敏感的 AI 提示词（Prompts）从前端客户端分离，迁移到安全的 Node.js 中间层（BFF - Backend for Frontend）。通过这种方式，确保在项目上线时，没有任何知识产权（IP）或原始提示词暴露在浏览器端。

## 🎯 触发指令 (Usage Trigger)
> "将核心 AI 逻辑重构到中间层。"
> "隔离后端逻辑。"

## 📋 标准操作流程 (SOP)

### 第一阶段：分析与设计 (Analysis & Design)
1.  **识别敏感逻辑**：扫描前端服务文件（如 `services/*.ts`），查找：
    *   硬编码的模型名称（如 `gemini-2.5-flash`）。
    *   系统指令（System Instructions）、角色设定（Personas）和复杂的提示词模板。
    *   API 密钥或敏感配置信息。
2.  **定义 API 接口**：设计基于业务意图的专用接口，而不是简单的模型透传包装。
    *   ❌ `POST /api/generate { prompt: "..." }`
    *   ✅ `POST /api/process/roast { images: [], intensity: "high" }`

### 第二阶段：中间层实现 (Middleware Implementation)
1.  **创建中间层文件**：在根目录创建 `middleware.cjs`（注意：如果项目是 `type: "module"`，务必使用 `.cjs` 后缀）。
    *   引入依赖：`express`, `cors`, `dotenv`。
2.  **实现核心逻辑**：将所有的提示词工程（Prompt Engineering）和上游 API 调用逻辑迁移至此。
3.  **本地开发配置**：
    *   确保中间层运行在专用端口（例如 `3005`）。
    *   配置 CORS 允许 `localhost:5173` (Vite 默认端口) 访问。

### 第三阶段：前端重构 (Frontend Refactoring)
1.  **配置 Vite 代理**：在 `vite.config.ts` 中添加代理配置，将 `/api` 指向中间层端口。
    ```typescript
    // vite.config.ts
    server: {
      proxy: {
        '/api': 'http://localhost:3005'
      }
    }
    ```
2.  **更新服务层**：
    *   修改 API 调用为 **相对路径**（例如 `/api/roast`）。
    *   **严禁**在 UI 代码中硬编码 `http://localhost:3005`；必须依赖代理。这能确保无缝迁移到生产环境（生产环境下前后端同源）。

### 第三阶段：验证 (Verification)
1.  **双重启动脚本**：创建/更新 `start-dev.sh` 以同时启动：
    *   中间层：`node middleware.cjs`
    *   前端：`npm run dev`
2.  **一致性检查**：验证后端使用的文本模型（如 `gemini-2.5-flash`）和图像模型（如 `gemini-3-pro`）版本是否与用户需求完全一致。

## 💡 关键检查点 (Critical Checkpoints)
*   **路由**：前端是否使用 `/api/...` 形式的请求？
*   **代理**：Vite 代理是否已正确配置？
*   **模型**：开发环境和任何生成的生产模版中，模型版本 (v1.5 vs v2.5) 是否完全一致？

