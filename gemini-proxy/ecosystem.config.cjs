module.exports = {
  apps : [{
    name   : "gemini-api",
    script : "./server.js",
    env: {
      // 在这里强制指定环境变量，确保 100% 能读取到
      GEMINI_API_KEYS: "",//可以有多个key，中间用逗号分隔
      AUTH_SECRET: "",//鉴权密钥
      ADMIN_PASSWORD: "",//管理员密码
      PORT: 8080
    }
  }]
}