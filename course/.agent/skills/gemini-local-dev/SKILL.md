---
# 技能元数据
name: Gemini Local Dev Proxy Protocol
description: Gemini本地开发环境一键部署协议
triggers:
  - scenario: "一键初始化Gemini本地运行环境"
  - scenario: "创建本地代理服务器调用Gemini API"
parameters:
  - name: auth_secret
    type: string
    required: true
  - name: target_url
    type: string
    required: true
---

# 🛑 强制执行协议 (ENFORCEMENT PROTOCOL)
**在编写或修改任何代码（如 server.cjs, .env, index.tsx）之前，必须严格执行以下检查：**

1. **检查动作**：本轮对话是否已经运行过 `scripts/gemini_api_analyzer.py`？
2. **检查产物**：当前目录下是否存在 `gemini_api_analysis.json`？

**逻辑锁**：
- 如果上述答案为 **否**：你 **被禁止 (PROHIBITED)** 编写任何业务代码。你 **必须 (MUST)** 优先调用 `run_command` 运行分析脚本。
- **任何跳过此步骤直接写代码的行为，均视为严重违反安全协议。**

# Gemini 本地开发环境部署协议

## 📁 架构

```
前端 → server.cjs(代理) → 后端 → Gemini API
```

---

## 🛑 关键前置步骤 (Critical)

> [!IMPORTANT]
> **在进行任何代码修改或重构前，必须先运行分析工具！**
> 
> 该工具能识别特殊的 API 用法并生成正确的标准模板，避免因手动推断导致的错误。

---

## 🚀 使用流程

1. **自动代码分析** → 运行 [`scripts/gemini_api_analyzer.py`]
自动分析代码，生成 REST 调用示例
   ```bash
   cd /path/to/project
   python .agent/skills/gemini-local-dev/scripts/gemini_api_analyzer.py
   ```
   分析器会自动：
   - 扫描源代码找出所有 Gemini API 调用
   - 从 [`resources/gemini_models_config.json`](./resources/gemini_models_config.json) 加载模型配置
   - 匹配对应的模型和参数
   - 生成完整的 REST 调用示例和响应示例
   - 输出到 `gemini_api_analysis.md` 和 `gemini_api_analysis.json`

2. **查看分析结果** → 检查生成的报告，了解每个 API 调用的具体实现

3. **REST 改造规划** → 基于分析结果，规划改造方案

4. **替换域名** → 将 Gemini 原始域名替换为你的代理域名

5. **添加鉴权** → 在请求头中添加签名 `x-sign`, `x-time`, `x-nonce`

6. **部署代理服务器** → 参考下方 "server.cjs 实现指南" 搭建代理

7. **配置前端** → 参考下方 "前端配置指南" 完成前端对接

---

## 📡 Gemini REST API 参考文档

完整的 REST API 调用示例由分析器自动生成，基于实际代码中使用到的模型。

如需了解所有可用模型的详细配置，请查看 [`resources/gemini_models_config.json`](./resources/gemini_models_config.json)

---

## 🔄 域名替换与鉴权配置

### 步骤 1: 替换域名

将 Gemini 官方 API 的域名替换为你的代理域名：

```bash
# 原始 Gemini API 域名
https://generativelanguage.googleapis.com/v1beta/models/...
# ↓
# 替换为你的代理域名
http://localhost:your_port/v1beta/models/...
# 或
https://your-proxy-domain.com/v1beta/models/...
```

### 步骤 2: 添加鉴权签名

在请求头中添加鉴权信息（替代官方的 `x-goog-api-key`）：

```javascript
// 生成签名
const crypto = require('crypto');
const timestamp = Math.floor(Date.now() / 1000).toString(); // 秒级时间戳
const nonce = Math.random().toString(36).substring(2, 15);
const sign = crypto.createHash('md5')
  .update(AUTH_SECRET + timestamp + nonce)
  .digest('hex');

// 请求头
headers: {
  'x-sign': sign,
  'x-time': timestamp,
  'x-nonce': nonce
}
```

### 完整示例（前端 fetch 调用）

```typescript
const crypto = require('crypto');

function generateAuthHeaders(authSecret: string) {
  const timestamp = Math.floor(Date.now() / 1000).toString();
  const nonce = Math.random().toString(36).substring(2, 15);
  const sign = crypto.createHash('md5')
    .update(authSecret + timestamp + nonce)
    .digest('hex');

  return {
    'x-sign': sign,
    'x-time': timestamp,
    'x-nonce': nonce
  };
}

// 使用示例
const response = await fetch('http://localhost:3000/v1beta/models/gemini-2.0-flash-exp:generateContent', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    ...generateAuthHeaders('your_auth_secret')
  },
  body: JSON.stringify({
    contents: [{ parts: [{ text: "Hello" }] }]
  })
});
```

---

## 🔧 代理服务器实现指南 (Node.js 示例)

### 1. 必须使用原生 `https.request`
**不要**使用 `http-proxy-middleware`（有 body 处理 bug）

### 2. 关键中间件 (Body 解析 & CORS)

**Body 解析：**
```javascript
app.use(express.json({
  limit: '50mb',
  verify: (req, res, buf, encoding) => {
    req.rawBody = buf.toString(encoding || 'utf8'); // 保存原始 body
  }
}));
```

**CORS 配置 (⚠️ 必加，否则前端无法调用)：**
```javascript
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*'); 
  res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type, x-sign, x-time, x-nonce');
  if (req.method === 'OPTIONS') return res.status(200).end();
  next();
});
```

### 3. 鉴权签名（⚠️ 时间戳必须用秒）

```javascript
// ✅ 正确：使用秒级时间戳
const timestamp = Math.floor(Date.now() / 1000).toString();
const nonce = Math.random().toString(36).substring(2, 15);
const sign = crypto.createHash('md5')
  .update(AUTH_SECRET + timestamp + nonce)
  .digest('hex');

req.authHeaders = {
  'x-nonce': nonce,
  'x-time': timestamp,     // 秒级时间戳
  'x-sign': sign
};
```

### 4. 响应与请求头清理 (关键点)
```javascript
// ✅ 正确：清理干扰头 (关键！否则会导致 500 Socket Hangup)
delete options.headers['host'];            // ⚠️ 必须删除 host，避免与目标域名冲突
delete options.headers['content-length'];
delete options.headers['connection'];
delete options.headers['accept-encoding']; // 强制返回明文 JSON

res.status(proxyRes.statusCode);
res.set('Content-Type', proxyRes.headers['content-type'] || 'application/json');
```

### 5. 路由兼容性 (Express 5+)
```javascript
// ✅ 正确：使用 app.use 捕获所有路径，避免 Express 5 中 '*' 的 PathError
app.use((req, res) => { ... });

// ❌ 错误：app.all('*') 在新版本中可能报错
```

### 6. 超时配置
```javascript
const options = { timeout: 500000, ... };
const server = app.listen(PORT);
server.setTimeout(500000);
```

---

## 📝 前端关键注意事项


**响应（从API返回）使用驼峰命名：**
```typescript
// ✅ 正确
if (part.inlineData?.data) {
  const mimeType = part.inlineData.mimeType || 'image/png';
  image = `data:${mimeType};base64,${part.inlineData.data}`;
}
```

### 请求体配置（⚠️ 使用 generationConfig）

```typescript
const requestBody = {
  contents: [
    {
      role: "user",
      parts: [
        { text: "提示词..." },
        { inline_data: { mime_type: "image/jpeg", data: base64Data } }
      ]
    }
  ],
  // ✅ 正确：使用 generationConfig 并严格规定 JSON 结构
  generationConfig: {
    response_mime_type: "text/plain" // 或 "application/json"
  }
};
```

### 鲁棒性建议 (防止前端崩溃)

**在 Prompt 中明确定义返回结构：**
```typescript
const prompt = `... 
IMPORTANT: You must return valid JSON with this structure: 
{ "title": string, "summary": string, "points": [] } 
即使 points 为空也必须返回空数组。`;
```

### 禁止使用的字段
```typescript
// ❌ 不要使用 imageConfig（不是标准字段）
requestBody.imageConfig = { ... };
```

---

## ⚙️ 前端开发服务器配置 (Vite Config)

必须在 `vite.config.js` (或 `vite.config.ts`) 中配置 server 代理，以解决跨域和 host 限制问题：

```javascript
  allowedHosts: true,
  proxy: {
    '/v1beta': {
      target: 'http://localhost:xxxx',//开启的后端接口
      changeOrigin: true,
      secure: false,
    }
  }
```

---

## 🔧 配置文件

### `.env`
```env
AUTH_SECRET=your_secret_here
TARGET_BASE_URL=your_target_url_here
PORT=your_port_here
```

### 前端 API 地址

```typescript
// services/geminiService.ts
const API_BASE_URL = "http://localhost:your_port_here/v1beta/models/";
```

---

## 📋 签名验证规则

| 项目 | 值 |
|------|-----|
| 签名算法 | `MD5(AUTH_SECRET + timestamp + nonce)` |
| 时间戳单位 | **秒** (`Math.floor(Date.now() / 1000)`) |
| 时间窗口 | ±300 秒（5 分钟） |
| 请求头 | `x-sign`, `x-time`, `x-nonce` |

---

## 🐛 常见问题速查

| 问题 | 解决方案 |
|------|---------|
| 401 Request expired | 使用秒级时间戳 `Math.floor(Date.now() / 1000)` |
| 404 Not Found | 检查 API 路径是否为 `/v1beta/models/` |
| 请求挂起 | 用原生 `https.request` |
| 504 超时 | 设置 `timeout: 500000` |
| CORS Blocked | 在 server.cjs 添加 CORS Middleware (Access-Control-Allow-Origin: *) |
| 500 socket hang up | 请求头冲突，需在 server.cjs 中 `delete headers['host']` |

---

