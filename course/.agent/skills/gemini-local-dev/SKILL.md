---
# 技能元数据
name: Gemini Local Dev Proxy Protocol
description: Gemini本地开发环境构建协议。定义了架构标准、安全规范及自动化初始化流程，指导Agent智能实现环境搭建。
triggers:
  - scenario: "一键初始化Gemini本地运行环境"
  - scenario: "修复本地开发中的跨域(CORS)或网络连接问题"
  - scenario: "需要实现前后端分离的 Gemini API 调用架构"
parameters:
  - name: auth_secret
    type: string
    required: true
    description: "鉴权密钥 (AUTH_SECRET)"
---

# Gemini Local Dev Proxy Protocol

本协议指导 Agent **主动构建**安全、稳健的 Gemini 本地开发环境。Agent 应根据项目当前状态，智能补全缺失组件，而非机械复制固定代码。

## 🎯 核心目标 (Objectives)
1.  **一键就绪**: 用户发出指令后，Agent 需全自动完成环境检查、文件创建、依赖安装及服务启动。
2.  **架构分离**: 严禁在前端直接调用 API。必须构建 `Frontend <-> Local Proxy <-> Remote API` 的三层架构。
3.  **零知识前端**: 前端代码中**绝不允许**出现 `AUTH_SECRET` 或敏感配置，所有鉴权逻辑必须封装在后端代理中。

---

## 🛠️ 执行工作流 (Execution Workflow)

Agent 收到触发指令后，**必须**按以下逻辑顺序执行操作：

### 1. 环境扫描 (Scan & Analysis)
*   **动作**: 检查项目根目录是否存在 `.env`, `server.js` (或 `server.cjs`), 以及前端 API 调用服务文件。
*   **判断**: 识别当前的前端框架 (React/Vue/Vite) 以决定启动命令。

### 2. 补全缺失组件 (Component Generation)
根据扫描结果，动态创建或修复以下组件。**请遵循下方的[实现约束]**。

*   **配置层**: 创建 `.env`，写入 `AUTH_SECRET` 和 `TARGET_BASE_URL`。
*   **接入层 (Backend)**: 创建轻量级 Node.js 代理服务器（推荐使用 Express）。
*   **调用层 (Frontend)**: 修改前端 API 服务，使其指向 `http://localhost:PORT`，而非直接调用远程接口。
*   **自动化层**: 创建 `start_dev.js` 脚本，用于**并行启动**前后端服务。

### 3. 先决条件检查 (Prerequisite Check)
*   **端口冲突检测**: 默认使用 **3005** 端口作为代理端口，避开 8080/3000。
*   **依赖检查**: 检查 `package.json`，若缺失 `express`, `cors`, `axios`, `dotenv`，则自动执行安装。

### 4. 启动与验证 (Launch & Verify)
*   **动作**: 运行 `node start_dev.js`。
*   **验证**: 启动后，Agent 必须通过 `curl -v http://localhost:PROXY_PORT` 验证代理服务是否存活。

---

## 🔒 实现约束 (Implementation Constraints)

Agent 生成代码时，必须严格遵守以下技术规范：

### A. 后端代理规范 (Backend Proxy)
1.  **CORS 健壮性**:
    *   必须显式配置 `cors` 中间件。
    *   **强制约束**: 对于 `OPTIONS` 预检请求，必须使用**正则匹配** (如 `/.*/`) 而非字符串通配符 (`'*'`)，以兼容新版 Express 生态。
    *   必须设置 `credentials: true` 并正确反射 `origin`。
2.  **连接稳定性**:
    *   使用 `https.Agent` 并开启 `keepAlive: true`。
    *   必须配置 `servername` (SNI) 以支持 Vercel/Cloudflare 等 CDN 托管的上游服务。
3.  **鉴权注入**:
    *   前端请求**不携带** Auth Secret。
    *   代理服务器接收请求后，在后端自动计算 `x-sign`, `x-time`, `x-nonce` 并注入 Headers。

### B. 前端调用规范 (Frontend Service)
1.  **原生调用**: 推荐使用原生 `fetch` API，而非特定 SDK（除非该 SDK 支持自定义 Base URL 且不校验 Key）。
2.  **动态代理**: API Base URL 应从配置或常量读取，便于开发/生产环境切换。
3.  **错误处理**: 必须检查响应 `Content-Type` 及 HTTP 状态码，优先处理 JSON 解析错误。

### C. 自动化脚本 (Automation Script)
1.  **依赖自检**: 脚本启动前应检查 `node_modules`，若缺失核心依赖则自动触发 `npm install`。
2.  **并行执行**: 使用 `child_process` 的 `spawn` 同时启动 Backend 和 Frontend，并接管 SIGINT 信号实现优雅退出。

---

## 🚨 故障自愈 (Troubleshooting Logic)

当遇到报错时，Agent 应尝试以下修复策略：

*   **端口被占用 (EADDRINUSE)**: 自动尝试 `PORT + 1`，并同步更新 `.env` 和前端配置。
*   **跨域被拦 (CORS Error)**: 检查后端 `OPTIONS` 路由定义，确认是否使用了正则匹配。
*   **连接重置 (Socket Hang Up)**: 检查 `AUTH_SECRET` 是否正确，或上游是否开启了 WAF（尝试伪造 User-Agent）。

