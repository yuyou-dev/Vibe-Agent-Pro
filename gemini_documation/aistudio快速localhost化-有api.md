# 🚀 AI 全栈开发指令文档

**文档目标**：基于内部接口文档，从零构建 aistudio 移植后的代码前后端开发，并实现一键自动化运行。

## 1. 上下文与核心资源 (Context)

* **业务背景**：`@gemini_documation` (了解 Gemini 功能，仅作背景参考)
* **技术标准 (Source of Truth)**：`@GeminiAPI_转发文档-内部.md` (一切接口地址、参数、鉴权方式以此为准)
* **当前项目环境**：(AI 会自动读取当前工作区文件)

## 2. 角色设定 (Role)

你是一名**高级全栈工程师**。你的任务不仅仅是写一个后端脚本，而是要**打通整个链路**。你需要交付一个**“下载即用”**的工程，这意味着你需要负责编写脚本来处理依赖安装和启动流程。

## 3. 🛡️ 核心防御性约束 (Critical Constraints - MUST FOLLOW)

**以下 6 条规则如果违反，视为任务失败：**

1.  **【最高优先级】严禁连接 Google 官方地址**：
    * **禁止**在代码中出现 `generativelanguage.googleapis.com`。
    * **强制**使用 `@GeminiAPI_转发文档-内部.md` 中定义的 **Base URL**：`你的域名`。
    * **实现策略**：为了防止 SDK 默认锁定官方地址，**强烈建议放弃 `@google/generative-ai` SDK，直接使用 `axios` 或 `node-fetch` 编写原生 HTTP 请求**。

2.  **全栈闭环 (Full-Stack Scope)**：
    * 不要只写后端！写完后端后，必须**修改前端代码**。
    * 找到前端调用 API 的地方，将请求地址改为你的本地后端地址（如 `http://localhost:3000/...`），**严禁**改变任何前端发送的 JSON 样式（包括模型参数和 Prompt 内容）。

3.  **鉴权与安全 (Auth & Security)**：
    * **严禁编造 Token**。必须从 `.env` 读取或按照文档逻辑获取。
    * **增加传输大小**：在后端转发前，增加逻辑检查上传body的大小（limit: 50mb 配置）。

4.  **稳定性优化 (Stability)**：
    * Gemini 生成耗时较长，请将 HTTP 请求的 **Timeout 设置为 180秒以上**。
    * 添加错误捕获（Try-Catch），如果转发失败，向前端返回清晰的 JSON 错误信息。

5.  **不做无效测试**：
    * **不要**编写单元测试（Unit Test）。
    * **只做**集成验证（Integration Check）。

6.  **【新增】自动化交付 (Automated Delivery)**：
    * **假设环境为空**：你必须假设用户的 `node_modules` 是空的。
    * **禁止口头指挥**：不要在聊天里告诉我“请运行 npm install”。**必须**编写一个脚本文件（如 `setup_and_run.js` 或 shell 脚本），该脚本运行后能自动完成：**安装后端依赖** -> **安装前端依赖** -> **启动服务**。

---

## 4. 执行步骤 (Step-by-Step Plan)

请严格按照以下顺序执行，每一步完成后进行检查：

### 第一步：编写本地后端转发服务 (Transparent Proxy)

* **技术栈**：Node.js (Express) + `axios` 或 `http-proxy-middleware`。
* **模式**：**透明代理**。不要解析 Body，直接透传。
* **功能**：接收前端请求 -> 转发到 `你的域名` -> 流式返回结果。

### 第二步：修改前端集成 (Frontend Integration)

* 搜索前端代码中的 API Base URL 配置。
* 将其指向本地后端（例如 `http://localhost:3000`） 并且查看改端口有没有被占用，如果被占用把之前的kill掉。
* **注意**：不要修改前端的请求构造逻辑，只改 URL。

### 第三步：编写一键启动脚本 (Build & Run Script) —— 关键步骤！

* 在项目根目录创建一个 **自动化脚本**（推荐命名为 `start_dev.js` 或 `setup.sh`）。
* **脚本逻辑必须包含**：
    1.  检查并安装后端依赖（`npm install`）。
    2.  **进入前端目录**（`cd frontend` 或类似路径），**执行 `npm install`**。
    3.  并行启动前端和后端服务（可以使用 `concurrently` 库或 `&` 操作符）。
* *提示：如果使用 Node.js 写脚本，可以使用 `child_process.execSync` 来执行 shell 命令。*

### 第四步：启动与验证 (Verification)

* **运行脚本**：在终端执行你刚才写的 `start_dev.js`。
* 验证前端是否成功启动并弹窗/打开浏览器。
* 验证后端是否打印了“Proxying request...”日志,确保当前开启的接口没有被占用。

---

## 5. 最终交付物 (Deliverables)

1.  后端服务源代码 (`server.js` 等)。
2.  修改后的前端配置文件。
3.  **一键启动脚本** (`start_dev.js`，包含 `npm install` 逻辑)。
4.  `.env` 配置示例。