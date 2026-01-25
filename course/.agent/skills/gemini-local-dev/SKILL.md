---
# 技能元数据
name: Gemini Local Dev Proxy Protocol v2
description: Gemini本地开发环境一键部署协议（精简版）
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

# Gemini 本地开发环境部署协议

## 📁 架构

```
前端 → server.cjs(代理) → aidev后端 → Gemini API
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

## ⚠️ server.cjs 关键要点

### 1. 必须使用原生 `https.request`
**不要**使用 `http-proxy-middleware`（有 body 处理 bug）

### 2. Body 解析
```javascript
app.use(express.json({
  limit: '50mb',
  verify: (req, res, buf, encoding) => {
    req.rawBody = buf.toString(encoding || 'utf8'); // 保存原始 body
  }
}));
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
// ✅ 正确：清理干扰头，特别是 accept-encoding 以防止 Gzip 引起乱码
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

### 字段命名规则

**请求（发送到API）必须使用下划线命名：**
```typescript
// ✅ 正确
{
  inline_data: { mime_type: "image/jpeg", data: "..." }
}

// ❌ 错误
{
  inlineData: { mimeType: "image/jpeg", data: "..." }
}
```

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

## 📋 签名验证规则

| 项目 | 值 |
|------|-----|
| 签名算法 | `MD5(AUTH_SECRET + timestamp + nonce)` |
| 时间戳单位 | **秒** (`Math.floor(Date.now() / 1000)`) |
| 时间窗口 | ±300 秒（5 分钟） |
| 请求头 | `x-sign`, `x-time`, `x-nonce` |

---

## 📚 API 参考

详细的 REST API 调用方式，请参考 `resources/gemini_documation/`：

- **图片生成**: `gemini图片生成文档.md` - 查找 `### REST` 章节
- **图片理解**: `gemini图片理解文档.md`

---

## 🐛 常见问题速查

| 问题 | 解决方案 |
|------|---------|
| 401 Request expired | 使用秒级时间戳 `Math.floor(Date.now() / 1000)` |
| 404 Not Found | 检查 API 路径是否为 `/v1beta/models/` |
| 400 Unknown name "config" | 使用 `generationConfig` 而不是 `config` |
| 400 错误 | 使用 `inline_data` / `mime_type` 下划线命名 |
| 无图片数据 | 兼容两种命名方式（响应用驼峰） |
| 请求挂起 | 用原生 `https.request` |
| 504 超时 | 设置 `timeout: 500000` |

---

## ⚠️ 严格重构边界 (Strict Refactoring Boundaries)

在应用本 Skill 进行代码重构时，开发者（Agent）必须遵守：

1.  **模型名称绝对冻结**:
    *   ❌ 禁止修改：`gemini-3-pro`, `gemini-2.5-flash` → `gemini-1.5-flash`
    *   ✅ 原样保留：即便模型名称看起来像是“未来版本”或“自定义别名”，也**必须原样保留**。因为 Proxy 后端可能对这些名称做了特殊路由映射。
    *   💡 **必须查阅文档**：在判定模型是否可用前，必须先查阅 `resources/gemini_documation/` 下的最新文档。

2.  **Prompt 零修改**:
    *   移动 Prompt 到新文件时，必须字符级（Character-level）一致，禁止“优化”、“压缩”或“修正语法”。
    *   任何对 Prompt 的修改都属于业务逻辑变更，不属于环境初始化重构范围。

3.  **配置即常量 (Configuration as Constant)**:
    *   任何字符串字面量（String Literals），尤其是涉及 `model`, `endpoint`, `system_instruction` 的，除非任务明确要求"升级模型"，否则在重构任务中应视为**不可变常量**。
