/**
 * scripts/start_dev.js
 * One-click startup script for Backend (Proxy) and Frontend (Vite).
 * Usage: node scripts/start_dev.js
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// Colors for console output
const colors = {
    reset: "\x1b[0m",
    cyan: "\x1b[36m",
    green: "\x1b[32m",
    yellow: "\x1b[33m",
    red: "\x1b[31m"
};

function log(color, msg) {
    console.log(`${color}[DevScript] ${msg}${colors.reset}`);
}

// 1. Install Dependencies Check
const rootNodeModules = path.join(__dirname, '../node_modules');
const frontendNodeModules = path.join(__dirname, '../frontend/node_modules');

function installDeps(cwd, name) {
    if (!fs.existsSync(path.join(cwd, 'node_modules'))) {
        log(colors.yellow, `Installing ${name} dependencies...`);
        return new Promise((resolve, reject) => {
            const npm = spawn('npm', ['install'], { cwd, stdio: 'inherit', shell: true });
            npm.on('close', (code) => {
                if (code === 0) resolve();
                else reject(new Error(`npm install failed in ${name}`));
            });
        });
    }
    return Promise.resolve();
}

async function start() {
    try {
        // Install Root (Backend) Deps
        await installDeps(path.join(__dirname, '..'), 'Root');

        // Install Frontend Deps (Assumes 'frontend' folder exists, adjust if needed)
        if (fs.existsSync(path.join(__dirname, '../frontend'))) {
            await installDeps(path.join(__dirname, '../frontend'), 'Frontend');
        }

        log(colors.green, "🚀 Starting Services...");

        // Start Backend
        const backend = spawn('node', ['server.js'], {
            cwd: path.join(__dirname, '..'),
            stdio: 'inherit', // Pipe logs to main console
            shell: true
        });

        // Start Frontend
        const frontend = spawn('npm', ['run', 'dev'], {
            cwd: path.join(__dirname, '../frontend'),
            stdio: 'inherit',
            shell: true
        });

        // Handle Exit
        process.on('SIGINT', () => {
            log(colors.red, "Stopping services...");
            backend.kill();
            frontend.kill();
            process.exit();
        });

    } catch (err) {
        log(colors.red, err.message);
    }
}

start();
