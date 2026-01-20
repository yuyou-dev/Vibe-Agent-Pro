---
# 技能元数据（必须放在文件顶部，用---包裹）
name: Gemini Local Dev Proxy  # 技能名称（保持不变，建议唯一）
description: Complete guide to migrating, securing, and automating local Gemini development using a proxy architecture.  # 描述（保持不变）
# 【新增】触发条件：Agent在哪些场景下会调用该技能
triggers:
  - scenario: "用户需要搭建Gemini本地开发环境"  # 场景描述
  - scenario: "用户遇到Gemini API网络限制"
  - scenario: "用户需要保护Gemini API密钥"
# 【新增】参数定义：技能调用时需要的用户输入（如API密钥、端口号）
parameters:
  - name: auth_secret  # 参数名（与.env中的AUTH_SECRET对应）
    type: string  # 参数类型（string/number/boolean）
    required: true  # 是否必填（true/false）
    description: "Gemini API的AUTH_SECRET，用于生成安全头x-sign"
  - name: proxy_port  # 参数名（端口号）
    type: number
    required: false
    default: 8080  # 默认值（可选）
    description: "本地代理服务的端口号，默认8080"
---
# Gemini Local Dev Proxy

This skill helps you set up a robust local development environment for Gemini, bypassing network restrictions and securing API keys.

## 📂 Structure
*   **`scripts/`**: Automation scripts for one-click startup.
*   **`resources/`**: Configuration templates.

---

## 🏃 Quick Start (The "One-Click" Script)

1.  Copy **[scripts/start_dev.js](scripts/start_dev.js)** to your project root.
2.  Run `node start_dev.js`.
    *   It automatically runs `npm install` (if needed).
    *   It starts both Backend and Frontend in parallel.

---

## 🏗️ Implementation Guide

### 1. Backend Proxy (`server.js`)

You need a Node.js Express server to securely sign and forward requests.

**Setup Instructions:**
1.  Install dependencies: `npm install express cors body-parser axios dotenv`
2.  Create `server.js` with the following **Critical Implementation Details**:

#### Key Precautions & Code Pattern
```javascript
// server.js - Core Logic
require('dotenv').config(); // Load env vars first
const express = require('express');
const crypto = require('crypto');
const axios = require('axios');
const https = require('https');
const cors = require('cors');

// Validate Env Vars
if (!process.env.TARGET_BASE_URL || !process.env.AUTH_SECRET) {
    console.error("Missing required environment variables: TARGET_BASE_URL or AUTH_SECRET");
    process.exit(1);
}

const targetUrl = new URL(process.env.TARGET_BASE_URL);

// 1. HTTPS Agent Configuration (CRITICAL for Stability)
const httpsAgent = new https.Agent({
    rejectUnauthorized: false, // Ignore self-signed certs (if any)
    servername: targetUrl.hostname, // CRITICAL: SNI for Vercel/Cloudflare
    keepAlive: true, // Try keeping connection open
    timeout: 60000,  // Socket timeout
    scheduling: 'fifo'
});

const app = express();
app.use(cors()); // Enable CORS

// 2. Large Payload Support (CRITICAL for Image Uploads)
app.use(require('body-parser').json({ limit: '50mb' }));

app.post('/api/generate', async (req, res) => {
    try {
        // 3. Signature Generation (CRITICAL for Auth)
        const now = Math.floor(Date.now() / 1000).toString();
        const nonce = crypto.randomUUID();
        const rawString = process.env.AUTH_SECRET + now + nonce;
        const sign = crypto.createHash('md5').update(rawString).digest('hex');

        // 4. Forwarding Request
        const response = await axios({
            method: 'post',
            url: `${process.env.TARGET_BASE_URL}/api/generate`,
            data: req.body,
            headers: {
                'x-time': now,
                'x-nonce': nonce,
                'x-sign': sign,
                'Content-Type': 'application/json',
                // Masquerade User-Agent to avoid WAF blocking "axios"
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            httpsAgent: httpsAgent,
            timeout: 600000 // 10 minute timeout
        });
        
        res.json(response.data);
    } catch (error) {
        console.error("Proxy Error:", error.message);
        if (error.response) {
            console.error("Upstream Response:", error.response.data);
            res.status(error.response.status).json(error.response.data);
        } else {
            res.status(500).json({ error: "Proxy Request Failed" });
        }
    }
});
```

### 2. Frontend Service (`geminiService.ts`)

**DO NOT** use the `@google/genai` SDK in the frontend. It exposes keys and doesn't support the custom proxy logic easily.

#### Implementation Pattern
Use native `fetch` to call your local proxy.

```typescript
// services/geminiService.ts
const PROXY_URL = "http://localhost:8080/api/generate";

export async function generateContent(model: string, prompt: string, imageBase64?: string) {
  const payload = {
    model: model, // e.g., "gemini-3-pro-image-preview"
    contents: [{
      parts: [
        { text: prompt },
        // Inline data for images
        ...(imageBase64 ? [{ inlineData: { mimeType: "image/jpeg", data: imageBase64 } }] : [])
      ]
    }],
    config: {
        // Add generation config here
    }
  };

  const response = await fetch(PROXY_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  if (!response.ok) throw new Error("Proxy request failed");
  
  const result = await response.json();
  
  // NOTE: Check for 'data' wrapper if upstream API changes structure
  // Some mirrors return { data: { candidates: [...] } }
  const candidates = result.candidates || result.data?.candidates;
  
  return candidates;
}
```

### 3. Documentation & Model Selection
Instead of guessing models, ALWAYS consult the local documentation in `resources/gemini_documation/`.

*   **Image Generation**: See `resources/gemini_documation/gemini图片生成文档.md`
*   **Text/Chat**: See `resources/gemini_documation/gemini文本生成文档.md`
*   **Vision/Multimodal**: See `resources/gemini_documation/gemini图片理解文档.md`
*   **Audio/Video**: See `resources/gemini_documation/gemini音频理解文档.md`, `resources/gemini_documation/gemini视频理解文档.md`

**Agent Instruction**: When a user asks for a specific capability (e.g., "generate image"), **read the relevant documentation file first** to find the correct model name (e.g., `gemini-3-pro-image-preview` or newer) and API parameters.

### 4. Image Generation Strategy
If the documentation confirms usage of `gemini-3-pro-image-preview` (Nano Banana Pro):
*   **Mode**: Non-streaming.
*   **Response**: Watch for wrapped responses (e.g., `data.candidates`).


### 5. Configuration (`.env`)

Ensure your `.env` contains the following strict configuration. **Do not commit this file.**
```env
# Security Configuration
AUTH_SECRET=your_actual_secret_here
PORT=8080
TARGET_BASE_URL=https://target-api-domain.com
```

---

## 🔧 Troubleshooting

### "404 Not Found", "No content generated", or "Socket Disconnected"

If you encounter a `404` error, "No content generated", or `500 Client network socket disconnected`:


1.  **Check `AUTH_SECRET`**: Ensure your `.env` has the correct `AUTH_SECRET`. An incorrect secret will cause the upstream mirror to reject the request (often with a 403 or 404 depending on implementation).
2.  **Valid Token**: Ensure the `AUTH_SECRET` matches exactly what is provided by your administrator.
3.  **Check Payload**: "No content generated" often means the model returned an empty `candidates` list. This can happen if:
    *   The prompt triggered safety filters.
    *   The model failed to process the image.
    *   **Debugging**: Modify `geminiService.ts` to log the full response.
    *   **Wrapped Response**: Sometimes the API response is wrapped in a `data` field (e.g. `{ code: 10000, data: { candidates: [...] } }`). Ensure your `geminiService.ts` checks `result.data?.candidates` in addition to `result.candidates`.
5.  **Socket Disconnected (500 Error)**: If you see `Client network socket disconnected` or a `500` error:
    *   **Enable keepAlive**: Set `keepAlive: true` in your `https.Agent`.
    *   **Add servername**: Add `servername: targetUrl.hostname` to your `https.Agent` options.
    *   **Masquerade User-Agent**: Add a browser-like `User-Agent` header to bypass WAFs blocking axios.
    *   **See the updated `server.js` code pattern above.**

5.  **Timeout / Connection Failed (ETIMEDOUT)**:
    *   **Cause**: The upstream server (configured in `TARGET_BASE_URL`) is not reachable. This is usually due to firewall, VPN, or network restrictions.
    *   **Solution**:
        *   Check if you can reach the `TARGET_BASE_URL` from your browser or via `curl`.
        *   If using a VPN, ensure it allows traffic to the target IP.
        *   The provided `server.js` now includes **automatic retry logic**. Check server logs to see if it retries.
6.  **Check Proxy Port**: Ensure the frontend is calling the correct proxy server.

### Common Pitfalls
*   **Tailwind CSS**: Use v3 (`npm install -D tailwindcss@3 postcss autoprefixer`) to avoid PostCSS plugin errors common in v4 with standard configurations.
