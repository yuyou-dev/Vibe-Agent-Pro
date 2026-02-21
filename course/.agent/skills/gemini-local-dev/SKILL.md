---
name: Gemini Local Dev Proxy Protocol (Universal Edition)
description: 阶段 1：本地开发环境初始化。强制运行 API 分析脚本，根据检测到的具体模型，将前端 SDK 动态替换为原生的 fetch 请求，并启动包含安全签名的本地透明代理。
---

# 🚀 阶段 1：多模型网络打通与鉴权代理

当前项目使用了 `@google/genai` 原生 SDK。本阶段目标是将网络请求切换为本地透明代理，注入自定义鉴权签名，同时**完美动态适配项目中使用的任何 Gemini 模型**（视觉、文本、语音等）。

## 🛑 绝对安全红线 (Security Rules)
1. **强制前置分析**：严禁凭空猜测 API 结构。不同的模型 REST 参数完全不同，必须依赖分析脚本的产出。
2. **禁止在前端写签名**：严禁在前端代码（如 `src/`）中引入 Node.js 的 `crypto` 模块或计算 `x-sign`。前端 Vite 环境会因此彻底崩溃。鉴权只能在 Node.js 代理中完成。
3. **Node 版本要求**：由于代理依赖了原生的 `fetch` API，执行代理的 Node.js 环境必须 **>= 18.0.0**。

## 📋 执行清单 (SOP) - 必须严格按顺序执行

### [ ] 1. 运行 API 动态分析脚本 (Critical)
- 必须在终端运行：`python agent/skills/gemini-local-dev/scripts/gemini_api_analyzer.py`
- 仔细阅读生成的 `gemini_api_analysis.md` 和 `gemini_api_analysis.json`。
- 提取关键信息：
  1. 当前项目使用的模型名称 (如 `gemini-3-pro-image-preview` 或 `gemini-2.5-flash-preview-tts` 等)。
  2. 对应的 Endpoint (如 `generateContent`)。
  3. **推荐的 REST Payload 结构**（⚠️ 极度重要：你组装 fetch 时必须严格照抄报告中的 `request_template` 或 `REST 调用示例`）。

### [ ] 2. 创建通用透明签名代理 (`server.cjs`)
- 在项目根目录创建 `server.cjs`。
- **必须完整复制以下代码（它是模型无关的透明代理，严禁修改内部的签名逻辑）：**

\`\`\`javascript
const express = require('express');
const cors = require('cors');
const crypto = require('crypto');
const path = require('path');
require('dotenv').config({ path: path.resolve(__dirname, '.env.local') });

const app = express();
app.use(cors());
app.use(express.json({ limit: '50mb' }));

// ⚠️ 修复 Express 5 PathError：使用 app.use 挂载前缀，绝对禁止使用 app.post('/*')
app.use('/proxy/gemini', async (req, res) => {
    // 仅拦截 POST 业务请求 (前端发出的 OPTIONS 跨域预检请求已被上方的 cors() 中间件处理)
    if (req.method !== 'POST') return res.status(405).json({ error: 'Method Not Allowed' });

    try {
        const secret = process.env.AUTH_SECRET;
        const targetBaseUrl = process.env.TARGET_BASE_URL;
        if (!secret || !targetBaseUrl) throw new Error("Missing AUTH_SECRET or TARGET_BASE_URL in .env.local");

        const timestamp = Math.floor(Date.now() / 1000).toString(); // 必须秒级
        const nonce = Math.random().toString(36).substring(2, 15);
        const sign = crypto.createHash('md5').update(secret + timestamp + nonce).digest('hex');

        // 💡 核心魔法：req.url 在 app.use 中会自动剥离 '/proxy/gemini' 前缀
        // 例如 req.url 将直接是: '/v1beta/models/gemini-xxx:generateContent'
        const baseUrl = targetBaseUrl.replace(/\\/$/, ''); // 确保末尾没有斜杠
        const targetUrl = \`\${baseUrl}\${req.url}\`;

        const response = await fetch(targetUrl, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json', 
                'x-sign': sign, 
                'x-time': timestamp, 
                'x-nonce': nonce 
            },
            body: JSON.stringify(req.body) // 原样透传前端发来的 Payload
        });
        
        // 容错处理：防止上游网关出错返回 HTML 导致 JSON 解析异常
        let data;
        const contentType = response.headers.get("content-type") || "";
        if (contentType.includes("application/json")) {
            data = await response.json();
        } else {
            data = await response.text();
            console.error("[Proxy Raw Response]:", data);
        }

        if (!response.ok) {
            console.error(`[Proxy Target Error] Status: ${response.status}`, data);
        }

        res.status(response.status).json(data);
    } catch (e) { 
        console.error("Proxy Exception:", e);
        res.status(500).json({ error: e.message }); 
    }
});

const PORT = process.env.PORT || 3005;
app.listen(PORT, () => console.log(\`Universal Proxy running on port \${PORT}\`));
\`\`\`

### [ ] 3. 动态改造前端 SDK 调用 (`src/` 目录)
- 移除 `@google/genai` 的导入和实例化。
- **基于步骤 1 的分析报告**，将原 SDK 调用转换为原生的 `fetch`。
- **目标 URL 格式**：`http://localhost:3005/proxy/gemini/v1beta/models/【检测到的模型名称】:【对应的Endpoint】`
- **请求体 (Body)**：必须按照报告中的 `REST 调用示例` 来组装。不要照抄原 SDK 的 config 嵌套层级，一切以分析报告的 JSON 结构为准！

### [ ] 4. 清理环境与补全依赖 (Stability Fix)
- 去除 `vite.config.ts` 中的 `define: { 'process.env.API_KEY': ... }` 危险硬编码。
- 在根目录 `.env.local` 添加 `AUTH_SECRET` 和 `TARGET_BASE_URL`。
- **强制安装 Node.js 代理运行及进程管理依赖**：使用包管理器（如 `npm install express cors dotenv concurrently`）安装这四个包。
  *(原因：AiStudio 项目通常只包含 Vite 纯前端依赖。缺失 express 会导致 server.cjs 崩溃；而引入 concurrently 可以有效解决 Vite 开发服务器（特别是 V6+）在后台静默运行时丢失 TTY 焦点导致进程自动退出 (Exit Code 130) 的核心痛点。)*

### [ ] 5. 注入一键启动脚本 (Universal Start)
- 自动修改项目的 `package.json`，在 `scripts` 字段中新增一条聚合启动命令（请勿覆盖原有 `dev`）：
  `"dev:all": "concurrently \"node server.cjs\" \"npm run dev\""`
- 启动并测试：指导在此后的工作流中，**统一通过运行 `npm run dev:all` 来启动项目**。
- 这项机制只需占用一个终端会话，就能同时且稳健地守护 Vite 前端与 Node.js 代理服务，合并输出日志流，彻底消除在跨终端或后台单独启动时引发的前端运行停止或顺序混乱问题。