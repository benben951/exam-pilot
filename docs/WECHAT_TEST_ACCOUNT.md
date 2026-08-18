# 微信公众号测试号接入

## 目标

让微信测试号把用户消息转发到 ExamPilot 后端：

```text
微信测试号 -> /api/wechat/callback -> ExamPilot -> 模型 API -> 微信回复
```

## 前置条件

微信服务器必须访问到一个公网 HTTPS/HTTP 地址。本机 `127.0.0.1` 不能直接填到微信后台。

开发期可选：

- ngrok
- cloudflared tunnel
- frp
- 部署到云服务器

## 本地配置

复制 `.env.local.example` 为 `.env.local`，填写：

```text
OPENAI_API_KEY=你的模型key
OPENAI_BASE_URL=中转站或官方 base url，例如 https://api.openai.com/v1
OPENAI_MODEL=模型名
WECHAT_TOKEN=你自己设置的微信 Token
```

注意：不要把 `.env.local` 发给别人，也不要提交到 Git。

## 微信测试号配置

进入微信公众平台测试号页面后，在“接口配置信息”里填写：

```text
URL: https://你的公网域名/api/wechat/callback
Token: 必须和 .env.local 里的 WECHAT_TOKEN 一致
```

EncodingAESKey 可随机生成。消息加解密方式开发期建议先用明文模式。

微信会用 GET 请求携带 `signature`、`timestamp`、`nonce`、`echostr` 验证服务器。ExamPilot 已实现校验并原样返回 `echostr`。

## 测试消息

关注测试号后发送：

```text
高考地理 等值线 总是判断错方向，帮我分析
```

如果模型 key 可用，会返回 AI 建议；如果没有配置 key，会返回本地规则版建议。

## 当前接口

- `GET /api/wechat/callback`: 微信服务器验证。
- `POST /api/wechat/callback`: 接收微信文本消息并被动回复。
