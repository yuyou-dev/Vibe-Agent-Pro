---
name: Middleware Logic Isolation (BFF Pattern)
description: 阶段 2：中间层隔离。依据 API 分析报告，将前端暴露的 AI 提示词（Prompt）和特定模型的 Payload 动态组装逻辑完整剥离，移入 Node.js 后端。
---

# 🛡️ 阶段 2：中间层逻辑隔离 (BFF)

目标：保护 AI 商业机密。前端将不再包含任何 Prompt 模板、系统指令或特定模型的参数配置，彻底降级为纯业务传参层。

## 📋 执行清单 (SOP)

### [ ] 1. 回顾 API 分析报告
- 再次查看根目录的 `gemini_api_analysis.json`。确认该项目使用的模型及其特定的数据结构要求（例如是否需要处理特定的 `generationConfig` 或 `speechConfig`）。

### [ ] 2. 升级并重构后端 (`middleware.cjs`)
- 将阶段 1 的 `server.cjs` 重命名为 `middleware.cjs`。**保留顶部的 MD5 签名生成代码**。
- 删除通用的 `/proxy/gemini/*` 透明转发路由。
- 新建基于业务意图的 API 路由（例如：`app.post('/api/action/generate', ...)`）。
- ⚠️ **逻辑大转移**：扫描前端负责 AI 调用的文件，将所有的提示词拼接逻辑（Prompt Engineering）、映射字典（如 `getStylePrompt` 等）、以及根据 JSON 报告动态组装 REST Payload 的逻辑，**完整物理剪切**到 `middleware.cjs` 的新路由中。
- 在后端调用原生 `fetch` 向中转 API 发送带有签名的请求，并根据报告的 `extract_path` 解析响应，将纯净的业务数据返回给前端。

### [ ] 3. 极简前端重构
- 前端的 API 调用不再包含任何 Prompt 或复杂的生成配置，仅发送用户输入的纯粹业务数据。
  示例：`await fetch('/api/action/generate', { method: 'POST', body: JSON.stringify({ 纯业务参数 }) })`。

### [ ] 4. 更新 Vite 本地代理 (Critical: Prevent 404 Errors)
- 修改 `vite.config.ts`，配置 Server Proxy，将前端的 `/api` 请求无缝转发到后端。
- ⚠️ **核心防御指引**：修改时必须**基于现有的 `server` 配置进行深度合并**（保留原本的 `host`, `port` 等参数），仅在内部追加 `proxy` 对象。严禁粗暴替换或重写整个 `server` 块，这极易导致配置丢失或代理未生效从而引发前端 404。
- **端口对齐核对**：必须确保 `proxy` 指向的端口（默认 `3005`）与你在 `middleware.cjs` 底部实际启动的端口精确吻合。

\`\`\`typescript
  // Vite 代理合并修改示例
  server: {
    port: 3000,         // <-- 必须保留原有项目可能存在的配置
    host: '0.0.0.0',    // <-- 必须保留原有项目可能存在的配置
    proxy: {
      '/api': 'http://localhost:3005' // <-- 安全地追加这部分
    }
  },
\`\`\`