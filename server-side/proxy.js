const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const https = require('https');
const http = require('http');
const fs = require('fs');
const path = require('path');

const app = express();
const TARGET_URL = 'https://generativelanguage.googleapis.com';

// ==========================================
// 核心配置：超时设置 (关键修改)
// ==========================================
// 设置为 10 分钟 (10 * 60 * 1000 毫秒)
// 足够应对 Gemini 识图和长文本生成的等待时间
const TIMEOUT = 600000;

// 1. 自动寻找证书
const CERT_DIR = path.join(__dirname, 'certs');
let sslOptions = {};
try {
    sslOptions = {
        key: fs.readFileSync(path.join(CERT_DIR, 'server.key')),
        cert: fs.readFileSync(path.join(CERT_DIR, 'server.crt'))
    };
} catch (e) {
    console.error('\n❌ 启动失败: 证书文件缺失');
    console.error(`👉 请将 server.key 和 server.crt 放入目录: ${CERT_DIR}\n`);
    process.exit(1);
}

// 2. 跨域配置
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Content-Type, x-goog-api-key, Authorization');
    if (req.method === 'OPTIONS') return res.sendStatus(200);
    next();
});

// 3. 代理配置 (增加超时参数)
const apiProxy = createProxyMiddleware({
    target: TARGET_URL,
    changeOrigin: true,
    secure: true,

    // ==========================================
    // 关键修改 1：代理层面的超时
    // ==========================================
    proxyTimeout: TIMEOUT, // 等待 Google 响应的时间
    timeout: TIMEOUT,      // 客户端连接的超时时间

    onProxyRes: (proxyRes) => {
        proxyRes.headers['Access-Control-Allow-Origin'] = '*';
    },
    onError: (err, req, res) => {
        // 只有在真的连不上时才报错，超时也会被捕获
        console.error('代理错误:', err.message);
        if (!res.headersSent) {
            res.status(500).json({ error: 'Proxy Error', message: err.message });
        }
    }
});

app.use('/', apiProxy);

// ==========================================
// 4. 启动服务 (增加服务器层面的超时)
// ==========================================

// HTTPS 服务
const httpsServer = https.createServer(sslOptions, app);
httpsServer.listen(443, () => {
    console.log('✅ [HTTPS] 服务运行中: 端口 443 (超时时间: 10分钟)');
});

// ==========================================
// 关键修改 2：Socket 层面的超时
// 防止 Node.js 默认 2 分钟后自动断开连接
// ==========================================
httpsServer.setTimeout(TIMEOUT);
httpsServer.keepAliveTimeout = TIMEOUT;
httpsServer.headersTimeout = TIMEOUT;


// HTTP 服务 (自动跳转)
const httpServer = http.createServer((req, res) => {
    const host = req.headers['host'];
    res.writeHead(301, { "Location": "https://" + host + req.url });
    res.end();
});
httpServer.listen(80, () => {
    console.log('✅ [HTTP]  服务运行中: 端口 80 -> 跳转 HTTPS');
});