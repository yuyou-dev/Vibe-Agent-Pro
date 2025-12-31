/**
 * server.js
 */
import express from 'express';
import cors from 'cors';
import bodyParser from 'body-parser';
import { GoogleGenAI } from '@google/genai';
import dotenv from 'dotenv';
import crypto from 'crypto';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 8080;

// ==========================================
// 0. 配置与密钥管理
// ==========================================

const rawKeys = process.env.GEMINI_API_KEYS || "";
const API_KEYS = rawKeys.split(',').map(k => k.trim()).filter(k => k);
let currentKeyIndex = 0;

// 🔐 签名验证密钥
const AUTH_SECRET = process.env.AUTH_SECRET || "ilovegemini123"; 

// 🔑 管理员密码 (用于切换 Key 或 开关开发者模式)
// 务必修改 .env: ADMIN_PASSWORD=my_super_admin_pwd
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || "admin666";

// 🆕 全局变量：控制开发者模式状态 (默认关闭，即默认需要鉴权)
let isGlobalDevMode = false;

if (API_KEYS.length === 0) {
    console.error("❌ 未找到 API Key");
} else {
    console.log(`✅ 已加载 ${API_KEYS.length} 个 Key`);
    console.log(`🛡️  初始状态：安全模式 (需要签名)`);
}

app.use(cors());
app.use(bodyParser.json({ limit: '50mb' }));

// 工具函数
const sendResult = (res, code, msg, data) => res.json({ code: code || 10010, message: msg || "error", data: data || "" });
const success = (res, data, msg) => sendResult(res, 10000, msg || "success", data);
const error = (res, msg, code) => sendResult(res, code || 10010, msg || "error", "");

// ==========================================
// 🛡 中间件：动态鉴权
// ==========================================

const authMiddleware = (req, res, next) => {
    // 1. 如果全局开发者模式已开启，直接放行！
    if (isGlobalDevMode) {
        return next();
    }

    // 2. 如果前端传了 Header 超级密码，也放行 (备用通道)
    if (req.headers['x-admin-pass'] === ADMIN_PASSWORD) {
        return next();
    }

    // --- 以下为正常签名验证 ---
    const sign = req.headers['x-sign'];
    const timestamp = req.headers['x-time'];
    const nonce = req.headers['x-nonce'];

    if (!sign || !timestamp || !nonce) return error(res, "请提供鉴权参数");

    const now = Math.floor(Date.now() / 1000);
    if (Math.abs(now - parseInt(timestamp)) > 300) return error(res, "请求已过期");

    const rawString = AUTH_SECRET + timestamp + nonce;
    const serverSign = crypto.createHash('md5').update(rawString).digest('hex');

    if (sign !== serverSign) return error(res, "签名验证失败");

    next();
};

// ==========================================
// 🎮 管理员接口 (需要密码)
// ==========================================

// 🆕 1. 远程开关开发者模式
app.post('/api/admin/toggle-dev', (req, res) => {
    const { password, enable } = req.body;

    // 必须要验证密码，否则任何人都能关闭你的服务器防火墙
    if (password !== ADMIN_PASSWORD) {
        return error(res, "管理员密码错误", 403);
    }

    if (typeof enable !== 'boolean') {
        return error(res, "参数 enable 必须是 true 或 false");
    }

    isGlobalDevMode = enable;

    const statusMsg = isGlobalDevMode ? "⚠️ 已开启开发者模式 (无需鉴权)" : "🛡️ 已恢复安全模式 (开启鉴权)";
    console.log(`[Admin Op] ${statusMsg}`);

    return success(res, { isDevMode: isGlobalDevMode }, statusMsg);
});

// 2. 切换 Key
app.post('/api/admin/switch', (req, res) => {
    // 这里也可以加个密码校验，防止路人乱切 Key
    const { index, password } = req.body;
    
    if (password !== ADMIN_PASSWORD) return error(res, "密码错误", 403);

    if (index < 0 || index >= API_KEYS.length) return error(res, "索引无效");

    currentKeyIndex = index;
    console.log(`[Admin Op] 切换至 Key #${currentKeyIndex + 1}`);

    return success(res, { currentIndex: currentKeyIndex }, "切换成功");
});

// ==========================================
// 🤖 业务接口
// ==========================================

app.post('/api/generate', authMiddleware, async (req, res) => {
    try {
        const { model, contents, config } = req.body;
        const activeKey = API_KEYS[currentKeyIndex];
        
        // 打印一下当前模式，方便调试
        const modeLog = isGlobalDevMode ? "[Dev Mode]" : "[Secure Mode]";
        console.log(`${modeLog} Request Model: ${model}`);

        const ai = new GoogleGenAI({ apiKey: activeKey });
        const response = await ai.models.generateContent({
            model: model,
            contents: contents,
            config: config
        });

        return success(res, response, "生成成功");
    } catch (err) {
        return error(res, err.message);
    }
});

app.listen(PORT, () => {
    console.log(`🚀 Server running on port ${PORT}`);
});