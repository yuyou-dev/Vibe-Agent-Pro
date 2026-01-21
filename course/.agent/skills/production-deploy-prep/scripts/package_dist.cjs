const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Configuration
const PROJECT_ROOT = path.resolve(__dirname, '../../../../');
const DIST_DIR = path.join(PROJECT_ROOT, 'dist');
const DEPLOY_DIR = path.join(PROJECT_ROOT, 'middleware_deploy');
const MIDDLEWARE_SOURCE = path.join(PROJECT_ROOT, 'middleware.cjs');
const ENV_PROD_FILE = path.join(PROJECT_ROOT, '.env.production');

// ANSI Colors
const colors = {
    reset: "\x1b[0m",
    bright: "\x1b[1m",
    green: "\x1b[32m",
    yellow: "\x1b[33m",
    red: "\x1b[31m",
    cyan: "\x1b[36m"
};

function log(message, type = 'info') {
    const prefix = type === 'error' ? `${colors.red}[ERROR]${colors.reset}` :
        type === 'success' ? `${colors.green}[SUCCESS]${colors.reset}` :
            type === 'warn' ? `${colors.yellow}[WARN]${colors.reset}` :
                `${colors.cyan}[INFO]${colors.reset}`;
    console.log(`${prefix} ${message}`);
}

async function run() {
    console.log(`${colors.bright}🚀 生产环境部署准备 (Production Deployment Prep)${colors.reset}\n`);

    // 1. Validation & Env Loading
    if (!fs.existsSync(MIDDLEWARE_SOURCE)) {
        log(`未找到中间件源文件: ${MIDDLEWARE_SOURCE}`, 'error');
        process.exit(1);
    }

    let envConfig = {};
    if (fs.existsSync(ENV_PROD_FILE)) {
        log(`正在加载 .env.production 配置...`);
        const envContent = fs.readFileSync(ENV_PROD_FILE, 'utf-8');
        envContent.split('\n').forEach(line => {
            const match = line.match(/^([^=]+)=(.*)$/);
            if (match) {
                const key = match[1].trim();
                const value = match[2].trim().replace(/^["']|["']$/g, ''); // Remove quotes
                envConfig[key] = value;
            }
        });
    } else {
        log(`未找到 .env.production。构建过程将依赖于现有的环境变量。`, 'warn');
    }

    // Check VITE_API_BASE_URL for Frontend
    if (!envConfig.VITE_API_BASE_URL && !process.env.VITE_API_BASE_URL) {
        log(`未在 .env.production 中设置 VITE_API_BASE_URL。前端将默认为硬编码值（如果有）。`, 'warn');
        // We don't exit, just warn.
    } else {
        log(`前端配置的 API URL: ${envConfig.VITE_API_BASE_URL || process.env.VITE_API_BASE_URL}`, 'success');
    }

    // 2. Build Frontend
    log(`正在构建前端 (Vite)...`);
    try {
        // We strictly use .env.production by ensuring it exists, Vite picks it up automatically. 
        // If we parsed it manually, we can also pass it to env.
        execSync('npm run build', {
            cwd: PROJECT_ROOT,
            stdio: 'inherit',
            env: { ...process.env, ...envConfig } // Ensure our parsed envs are visible
        });
        log(`前端构建完成。产物位于 'dist/'`, 'success');
    } catch (error) {
        log(`前端构建失败。`, 'error');
        process.exit(1);
    }

    // 3. Package Middleware
    log(`正在打包中间件...`);

    // Clean/Create Dir
    if (fs.existsSync(DEPLOY_DIR)) {
        fs.rmSync(DEPLOY_DIR, { recursive: true, force: true });
    }
    fs.mkdirSync(DEPLOY_DIR);

    // Copy Source
    fs.copyFileSync(MIDDLEWARE_SOURCE, path.join(DEPLOY_DIR, 'index.js'));
    log(`已复制中间件源码到 middleware_deploy/index.js`);

    // Create package.json
    const packageJson = {
        name: "gemini-middleware-deployment",
        version: "1.0.0",
        description: "Production build of Gemini Middleware",
        main: "index.js",
        scripts: {
            "start": "node index.js"
        },
        dependencies: {
            "axios": "^1.7.9",
            "body-parser": "^1.20.3",
            "cors": "^2.8.5",
            "dotenv": "^16.4.7",
            "express": "^4.21.2"
        },
        engines: {
            "node": ">=18.0.0"
        }
    };
    fs.writeFileSync(path.join(DEPLOY_DIR, 'package.json'), JSON.stringify(packageJson, null, 2));
    log(`已生成 package.json`);

    // Create .env for Middleware
    // We look for specific keys that the middleware needs
    const middlewareKeys = ['PORT', 'TARGET_BASE_URL', 'AUTH_SECRET'];
    let middlewareEnvContent = `# Production Configuration\n`;

    middlewareKeys.forEach(key => {
        const val = envConfig[key] || process.env[key];
        if (val) {
            middlewareEnvContent += `${key}=${val}\n`;
            log(`- 配置 ${key} 来自 environment/config`);
        } else {
            middlewareEnvContent += `${key}=PLACEHOLDER_PLEASE_CHANGE\n`;
            log(`- ${key} 未找到。设置为占位符。`, 'warn');
        }
    });

    fs.writeFileSync(path.join(DEPLOY_DIR, '.env'), middlewareEnvContent);
    log(`已为中间件生成 .env`);

    // Create README
    const readmeContent = `# 部署说明 (Deployment Instructions)

1. **前端 (Frontend)**: 将 \`dist\` 文件夹中的所有内容上传到您的 Web 服务器（如 Nginx 或 Apache 的根目录）。
2. **中间件 (Middleware)**: 
   - 将此 \`middleware_deploy\` 文件夹上传到您的后端服务器。
   - 运行 \`npm install --production\` 安装依赖。
   - 如果尚未配置，请更新 \`.env\` 文件中的真实密钥。
   - 运行 \`npm start\` 启动服务。
`;
    fs.writeFileSync(path.join(DEPLOY_DIR, 'README.md'), readmeContent);

    log(`\n${colors.green}构建与打包完成！ (Build & Package Complete!)${colors.reset}`);
    console.log(`- 前端产物: ${DIST_DIR}`);
    console.log(`- 中间件包: ${DEPLOY_DIR}`);
}

run().catch(err => {
    console.error(err);
    process.exit(1);
});
