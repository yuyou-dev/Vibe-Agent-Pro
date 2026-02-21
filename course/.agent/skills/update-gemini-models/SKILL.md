---
name: Gemini 模型更新器 (Gemini Models Updater)
description: 这是一个内置技能，用于通过 gemini-docs-mcp 自主获取最新的 Gemini 模型及其特性（来自 Google GenAI SDK 官方文档），并更新本地的模型配置文件。
---

# Gemini 模型更新器技能 (Gemini Models Updater Skill)

## 🎯 目的
此技能旨在自动使您的本地 Gemini 模型配置（例如 `gemini_models_config.json`）与 Google 发布的最新模型、参数和功能保持同步。它利用 `gemini-docs-mcp` 服务器来读取最新的官方文档。

## 🛠️ 前提条件
- 可以访问 `gemini-docs-mcp` MCP 服务器的以下工具：
  - `mcp_gemini-docs-mcp_get_current_model`
  - `mcp_gemini-docs-mcp_search_documentation`
  - `mcp_gemini-docs-mcp_get_capability_page`
- 包含现有模型目录的目标配置文件（例如，`resources/gemini_models_config.json`）。

## 📋 执行步骤

### 1. 检查和配置 MCP 环境 (非常重要)
- 使用 `list_resources` 或检查是否有 `mcp_gemini-docs-mcp_get_current_model` 等工具，来验证当前环境是否已经配置好 `gemini-docs-mcp` 服务器。
- **如果没有发现该 MCP 服务**，请暂停后续操作，并立刻通过 `notify_user` 通知用户：
  - 说明无法检测到 `gemini-docs-mcp` 服务。
  - 建议用户参考官方途径或相关文档来安装并配置该 MCP 服务器，例如：执行相应的 npx 命令或在本地 MCP 配置文件中添加对 `gemini-docs-mcp` 的支持。
  - 只有在确认用户已经配置好该环境后，才继续进行下一步。

### 2. 确定更新范围
- 询问用户或从提示语中判断本次更新是针对**特定某个模型**（例如 "gemini-3.1-pro"）还是针对所有新可用模型的**全局更新**。
- 定位需要更新的目标配置文件（默认是 `@[.agent/skills/gemini-local-dev/resources/gemini_models_config.json]`）。

### 3. 获取最新文档
- **针对特定模型：**
  - 使用 `mcp_gemini-docs-mcp_search_documentation` 工具，配合简短的关键词，如 `["gemini-3.1-pro", "google-genai"]` 取回资料。
- **针对全局更新：**
  - 使用 `mcp_gemini-docs-mcp_get_current_model` 工具获取所有当前可用模型的索引（包括 Stable, Preview, Experimental 等版本）。
  - 查找最新引入的模型，并在必要时进一步获取它们特定的使用文档。

### 4. 分析与提取配置数据
仔细阅读获取到的文档内容，提取以下关键信息：
- `name`（名称）和 `description`（描述）
- `category`（分类，例如 advanced_reasoning, multimodal_understanding）
- `api_version`（API 版本，例如 v1beta）
- `context_window`（上下文窗口：输入/输出 Token 限制）
- `request_template`（请求模板：特别是结构化输出的 Schema 格式，以及支持的 `tools` 如 `googleSearch` 或 `urlContext` 等）。
- 默认参数设置 (Default parameters) 和响应结束原因 (Finish reasons)。

### 5. 更新配置文件 (关键步骤)
- 使用 `view_file` 彻底读取并分析现有的目标 JSON 配置文件。
- **严禁**修改或删除任何已经存在的模型配置项（除非用户明确要求）。系统的其它部分可能强依赖它们现有的数据结构。
- 在 `"models"` 对象层级下，将新模型的配置作为全新的键值对加入进去。
- 确保新添加的配置严格遵守文件中现有的 Schema 规范和约定（例如：请求结构模板、`{{variable}}` 变量绑定等格式）。
- 使用 `replace_file_content` 或 `multi_replace_file_content` 工具安全地注入新的配置块。

### 6. 验证与总结
- 必须确保更新后的文件仍然是格式完全合法的 JSON 文件。
- 输出一份排版精美的总结报告给用户，详细说明新增或更新了哪些模型，并高亮介绍引入的重大新特性（例如：新的 Token 上限、网络搜索/Grounding 能力、原生函数/工具调用等）。
