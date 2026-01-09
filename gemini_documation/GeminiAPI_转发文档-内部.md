# Gemini API 中转服务接口文档

**版本**: v1.0
**服务地址 (Base URL)**: `你的域名`
**请求格式**: `Content-Type: application/json`

---

## 1. 鉴权机制 (Authentication)

业务接口（`/api/generate`）需要在 Header 中携带鉴权信息，支持以下两种方式之一。

### 方式 A：生产环境（签名验证）

适用于正式环境，防篡改与重放。

* **Header 参数**:
* `x-time`: 当前 Unix 时间戳（秒）。
* `x-nonce`: 随机字符串。
* `x-sign`: 签名字符串。


* **签名算法**: `MD5(密钥 + x-time + x-nonce)`
* 密钥 (AUTH_SECRET): ``
* 结果为 32 位小写字符串。



## 2. 核心业务接口

### 内容生成 (全能接口)

支持对话、识图、画图、联网搜索及 JSON 格式化。

* **地址**: `POST /api/generate`
* **参数说明 (Body)**:

| 参数 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `model` | String | 是 | 模型名称 (如 `gemini-2.5-flash`, `gemini-2.5-pro`) |
| `contents` | Array | 是 | 标准 Gemini 对话数组，包含 `role` 和 `parts` |
| `config` | Object | 否 | 用于控制画图、搜索或格式化输出的高级配置 |

### 功能配置速查 (Config / Input)

根据不同场景，调整 Input 结构或 Config 参数：

1. **视觉识别 (Vision)**: 在 `parts` 中增加 `inlineData` 字段（MimeType + Base64，**不带前缀**）。
2. **AI 画图**: 设置 `config` 为 `{ "responseModalities": ["IMAGE"] }`。可选参数 `imageConfig` 控制比例和数量。
3. **联网搜索**: 设置 `config` 为 `{ "tools": [{ "googleSearch": {} }] }`。
4. **JSON 输出**: 设置 `config` 为 `{ "responseMimeType": "application/json" }`。


---

## 3. 响应结构与状态码

### 统一响应结构

```json
{
  "code": 10000,          // 状态码
  "message": "success",   // 提示信息
  "data": { ... }         // 业务数据 (candidates 列表)
}

```

### 状态码说明

| Code | Message | 说明 |
| --- | --- | --- |
| **10000** | success | 请求成功 |
| **10010** | Invalid Signature / Expired | 签名错误或时间戳过期 (>5分钟) |
| **403** | Forbidden | 管理员密码错误 |
| **500** | Internal Error | 服务端异常 (如配额耗尽) |

---

