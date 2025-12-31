这是一份为您准备的**课程专用 `README.md` 文档**。

这份文档假设学员使用的是**腾讯云轻量服务器 (OpenCloudOS/CentOS)**，并且服务器是全新的（没有 Git，没有 Node.js）。

你可以直接将以下内容保存为 `README.md` 并推送到你的 GitHub 仓库根目录。

---

# 🚀 Gemini API 代理服务部署实战教程

欢迎来到本课程！本项目是一个基于 Node.js 的 Gemini API 中转服务，支持**多 Key 自动切换**、**负载均衡**以及**高并发处理**。

本教程将手把手教你如何在**腾讯云轻量应用服务器**上，从零开始部署这套服务，并配置 HTTPS 域名访问。

## 📋 准备工作

在开始之前，请确保你已经准备好：

1. 一台腾讯云轻量应用服务器（推荐系统：**OpenCloudOS** 或 **CentOS Stream**）。
2. 一个已经解析到服务器 IP 的域名（例如：`api.yourdomain.com`）。
3. 至少一个 Google Gemini API Key。
4. 终端连接工具（如 CMD, PowerShell,或是 Termius）。

---

## 🛠️ 第一步：安装基础工具 (Git & Node.js)

全新的服务器默认没有安装 Git，我们需要先安装它，才能拉取代码。

登录你的服务器终端，依次执行以下命令：

### 1.1 安装 Git 和基础库

```bash

# 安装 Git (这是克隆代码必须的)
sudo dnf install git -y

```

### 1.2 安装 Node.js 环境

本项目依赖 Node.js 运行。我们安装 v18 或更高版本。

```bash
# 验证安装是否成功 (如果显示版本号则成功)
node -v
npm -v

```

### 1.3 安装 PM2 进程管理器

PM2 用于在后台持久运行我们的服务，即使关闭终端服务也不会断。

```bash
# 全局安装 PM2
sudo npm install pm2 -g

```

---

## 📥 第二步：拉取项目代码

现在工具都装好了，我们把代码从 GitHub 拉取到服务器上。

```bash
# 1. 进入home文件夹
cd /home/
# 2. 克隆仓库 
git clone https://github.com/Teresa1228/gemini-proxy-tecent.git

# 3. 进入项目目录cd 你的项目名
cd gemini-proxy-tecent/

# 4. 安装项目依赖
npm install

```

---

## ⚙️ 第三步：配置 API Key

我们需要配置 API Key 才能让服务跑起来。这里我们使用 PM2 的配置文件来管理环境变量。

### 3.1 创建配置文件

项目中应该有一个 `ecosystem.config.cjs` 文件（如果没有，请手动创建）：

```bash
# 使用 nano 编辑器创建/修改配置文件
nano ecosystem.config.cjs

```

### 3.2 填入你的 Key

将以下内容复制进去。**注意：请务必替换 `GEMINI_API_KEYS` 里的内容为你真实的 Key。**

```javascript
module.exports = {
  apps : [{
    name   : "gemini-api",
    script : "./server.js",
    env: {
      // 服务运行在 8080 端口 (不要改，80 留给 Nginx)
      PORT: 8080,
      
      // 👇 在这里填入你的 Key，如果有多个，用英文逗号分隔
      GEMINI_API_KEYS: "你的Key_1,你的Key_2,你的Key_3"
    }
  }]
}

```

*操作提示：按 `Ctrl + X`，然后按 `Y`，最后按 `Enter` 保存并退出。*

---

## ▶️ 第四步：启动后端服务

配置完成后，我们启动 Node.js 服务。

```bash
# 使用 PM2 启动服务
pm2 start ecosystem.config.cjs

# 保存当前状态 (确保重启服务器后自动运行)
pm2 save

```

**检查状态：**
运行 `pm2 list`，如果看到 status 为 `online`，说明后端服务已经启动成功！

---

## 🌐 第五步：配置 Nginx 反向代理与 HTTPS (重难点)

为了让前端能通过域名（HTTPS）安全访问，我们需要配置 Nginx。

### 5.1 安装 Nginx 和 SSL 工具

```bash

# 安装 Nginx 和 Certbot
sudo dnf install nginx certbot python3-certbot-nginx -y

```

### 5.2 确保端口未被占用 (防坑必做)

在启动 Nginx 之前，必须确保 80 端口没有被之前的 Node 进程占用。

```bash
# 杀掉所有 Node 进程，并立即启动 Nginx (组合拳)
sudo killall -9 node && sudo systemctl start nginx

# Nginx 启动后，再把刚才的 PM2 服务拉起来
pm2 restart gemini-api

```

### 5.3 配置 Nginx 转发

我们需要告诉 Nginx：把域名的请求转给后台的 8080 端口。

1. **创建配置文件**（请将文件名换成你的域名，方便管理）：
```bash
# 例如：sudo nano /etc/nginx/conf.d/api.conf
sudo nano /etc/nginx/conf.d/gemini.conf

```


2. **粘贴以下内容**（把 `你的域名` 替换成真实域名）：
```nginx
# 1. 监听 80 端口，强制跳转到 HTTPS
server {
    listen 80;
    server_name 你的域名;
    return 301 https://$host$request_uri;
}

# 2. 监听 443 端口 (HTTPS)
server {
    listen 443 ssl;
    server_name 你的域名;

    # 🔥🔥🔥 关键：请修改下面两行为你真实的证书路径 🔥🔥🔥
    ssl_certificate     /etc/nginx/ssl/xxxx.net_bundle.crt; 
    ssl_certificate_key /etc/nginx/ssl/xxxx.key;

    # SSL 优化配置 
    ssl_session_timeout 5m;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:HIGH:!aNULL:!MD5:!RC4:!DHE;

    location / {
        # 转发给你的 Node.js (8080)
        proxy_pass http://127.0.0.1:8080;

        # 必要的转发头
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;

        # 超时设置
        proxy_read_timeout 300s;
    }
}
```


3. **验证并重载配置**：
```bash
sudo nginx -t
sudo systemctl reload nginx

```



### 5.3.2（获取证书另一种方式，如果已有可忽略）一键开启 HTTPS

使用 Certbot 自动申请免费证书并配置 HTTPS。

```bash
# 请替换为你的真实域名
sudo certbot --nginx -d 你的域名

```

**交互提示：**

1. 输入邮箱（用于接收过期提醒）。
2. 同意协议（输入 `Y`）。
3. **Redirect (重定向)**：**务必选择 `2**`。这会强制将 HTTP 转换为 HTTPS。

---

## ✅ 第六步：验证与使用

恭喜！你的服务已成功上线。

### 1. 接口地址

* **生成内容**: `https://你的域名/api/generate` (POST)
* **切换 Key**: `https://你的域名/api/admin/switch` (POST)

### 2. 测试命令 (Curl)

你可以直接在本地终端测试一下：

```bash
curl -X POST https://你的域名/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "contents": [{ "parts": [{ "text": "Hello, world!" }] }]
  }'

```

---

## ❓ 常见问题排查 (Troubleshooting)

**Q1: 访问显示 "502 Bad Gateway"**

* **原因**: 后端 Node.js 服务没跑起来。
* **解决**: 运行 `pm2 list` 检查状态。如果是 `errored`，运行 `pm2 logs` 看报错信息（通常是 Key 没配对）。

**Q2: Nginx 启动失败 "Address already in use"**

* **原因**: 80 端口被占用了。
* **解决**: 运行 `sudo killall -9 node` 杀掉进程，然后 `sudo systemctl start nginx`，最后再 `pm2 restart all`。

**Q3: 无法访问，浏览器转圈圈**

* **原因**: 腾讯云防火墙没开。
* **解决**: 去腾讯云控制台 -> 防火墙，确保 **TCP:80** 和 **TCP:443** 处于“放行”状态。