require('dotenv').config();
const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const app = express();
const TARGET_URL = 'https://generativelanguage.googleapis.com';

// ==========================================
// 🔑 核心机密配置 (都在这里)
// ==========================================

// 1. 你的 Google Gemini API Key (从 .env 读取)
const GOOGLE_API_KEY = process.env.GOOGLE_API_KEY;

// 2. 鉴权签名密码 (从 .env 读取)
const AUTH_SECRET = process.env.AUTH_SECRET;

// 3. 超时时间 (10分钟)
const TIMEOUT = 600000;

// ==========================================
// 📜 证书加载
// ==========================================
const CERT_DIR = path.join(__dirname, 'certs');
console.log(path.join(CERT_DIR, 'server.key'))
let sslOptions = {};
try {
    sslOptions = {
        key: fs.readFileSync(path.join(CERT_DIR, 'server.key')),
        cert: fs.readFileSync(path.join(CERT_DIR, 'server.crt'))
    };
} catch (e) {
    console.error('❌ 启动失败: certs 目录下找不到 server.key 或 server.crt');
    process.exit(1);
}

// ==========================================
// 🛡️ 中间件 1: 跨域 (CORS)
// ==========================================
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    // 注意：这里不再需要 x-goog-api-key，因为前端不用传了
    res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization, x-sign, x-time, x-nonce');

    if (req.method === 'OPTIONS') return res.sendStatus(200);
    req.headers['x-goog-api-key'] = GOOGLE_API_KEY;
    next();
});

// ==========================================
// 🔐 中间件 2: 安全鉴权 (MD5)
// ==========================================
const authMiddleware = (req, res, next) => {
    const sign = req.headers['x-sign'];
    const timestamp = req.headers['x-time'];
    const nonce = req.headers['x-nonce'];

    // 1. 参数完整性检查
    if (!sign || !timestamp || !nonce) {
        return res.status(401).json({ error: 'Unauthorized', message: 'Missing auth headers' });
    }

    // 2. 时间戳检查 (5分钟有效期)
    const now = Math.floor(Date.now() / 1000);
    if (Math.abs(now - parseInt(timestamp)) > 300) {
        return res.status(401).json({ error: 'Unauthorized', message: 'Request expired' });
    }

    // 3. 签名比对
    const rawString = AUTH_SECRET + timestamp + nonce;
    const serverSign = crypto.createHash('md5').update(rawString).digest('hex');

    if (sign !== serverSign) {
        return res.status(401).json({ error: 'Unauthorized', message: 'Invalid signature' });
    }

    next();
};

app.use(authMiddleware);

// ==========================================
// 🚀 中间件 3: 代理转发 (自动注入 Key)
// ==========================================
const apiProxy = createProxyMiddleware({
    target: TARGET_URL,
    changeOrigin: true,
    secure: true,
    proxyTimeout: TIMEOUT,
    timeout: TIMEOUT,
    onProxyReq: (proxyReq, req, res) => {
        // 🔥 关键设置 ：告诉 Google 保持连接，不要挂断
        proxyReq.setHeader('Connection', 'keep-alive');
        proxyReq.setHeader('Keep-Alive', 'timeout=600');
    },

    onProxyRes: (proxyRes) => {
        proxyRes.headers['Access-Control-Allow-Origin'] = '*';
    },
    onError: (err, req, res) => {
        console.error('Proxy Error:', err.message);
        if (!res.headersSent) res.status(500).json({ error: 'Proxy Error' });
    }
});

app.use('/', apiProxy);

// ==========================================
// 🏁 启动服务
// ==========================================
const httpsServer = https.createServer(sslOptions, app);
httpsServer.listen(443, () => {
    console.log('✅ [HTTPS] Running on port 443 (Key Hidden & Auth Enabled)');
});
httpsServer.setTimeout(TIMEOUT);
httpsServer.keepAliveTimeout = TIMEOUT;

http.createServer((req, res) => {
    res.writeHead(301, { "Location": "https://" + req.headers['host'] + req.url });
    res.end();
}).listen(80, () => {
    console.log('✅ [HTTP]  Running on port 80 -> HTTPS');
});