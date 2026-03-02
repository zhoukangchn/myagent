# model-auth-proxy

用于 OpenClaw 的内部模型 Provider 插件，支持 **API Key 认证**、**自定义 Header 注入** 和 **TLS 证书忽略**。

## 功能说明

- 注册 Provider：`internal-model`
- 登录方式：`api-key-relay`
- 支持 API Key 认证（`Authorization: Bearer <token>`）
- 支持 2 个自定义上游 Header（`header1`、`header2`）
- 支持忽略 TLS 证书校验（`tlsInsecure=true`）
- 内置本地 relay 转发服务
- OpenAI 兼容风格（`/v1/chat/completions` 等）

## 安装

```bash
cd ~/myagent
openclaw plugins install "$(pwd)/plugins/model-auth-proxy"
openclaw plugins enable model-auth-proxy
```

## 插件运行参数

编辑 `~/.openclaw/openclaw.json`：

```json5
{
  plugins: {
    entries: {
      "model-auth-proxy": {
        "enabled": true,
        "config": {
          "upstreamUrl": "https://gateway.company.com/v1",
          "apiKey": "YOUR_API_KEY",
          "header1": { "name": "x-tenant-id", "value": "team-a" },
          "header2": { "name": "x-project", "value": "prod" },
          "tlsInsecure": false
        }
      }
    }
  }
}
```

### 参数说明

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `upstreamUrl` | string | 是 | - | 上游 OpenAI 兼容网关地址，如 `https://gateway.company.com/v1` |
| `apiKey` | string | 是 | - | 上游认证 Bearer Token |
| `header1` | object | 否 | `null` | 自定义上游 Header #1，需包含 `name` 和 `value` |
| `header2` | object | 否 | `null` | 自定义上游 Header #2，需包含 `name` 和 `value` |
| `tlsInsecure` | boolean | 否 | `false` | 是否关闭上游 TLS 证书校验（仅测试） |

### 完整配置示例

```json5
{
  plugins: {
    entries: {
      "model-auth-proxy": {
        "enabled": true,
        "config": {
          "upstreamUrl": "https://llm-gateway.internal.company.com/v1",
          "apiKey": "sk-xxxxxxxxxxxxxxxx",
          "header1": { "name": "x-tenant-id", "value": "dev-team" },
          "header2": { "name": "x-request-source", "value": "openclaw" },
          "tlsInsecure": false
        }
      }
    }
  }
}
```

## 登录配置

```bash
openclaw models auth login --provider internal-model --method api-key-relay --set-default
```

按提示输入模型 ID（逗号分隔），例如：`gpt-4o-mini,gpt-4.1-mini`

## 模型 ID 说明

- 登录时填写的模型 ID，会注册为 OpenClaw 可选模型
- 格式：`internal-model/<model-id>`
- 例如：`internal-model/gpt-4o-mini`

## 模型清单（示例）

以下是通用示例，请替换为你公司网关真实支持的模型 ID：

- `gpt-4o-mini`
- `gpt-4.1-mini`
- `claude-3-5-sonnet`
- `deepseek-chat`

## 验证

安装并登录后，可用以下命令检查状态：

```bash
openclaw plugins info model-auth-proxy
openclaw models status
```

## TLS 注意事项

- `tlsInsecure=true` 会禁用证书校验，**仅可用于隔离测试环境**
- 生产环境请保持 `tlsInsecure=false`，并使用可信证书链/内部 CA

## 常见问题

- **401/403**：通常是 `apiKey` 配置错误或 token 失效
- **400**：检查 `upstreamUrl` 格式，需以 `/v1` 结尾
- **TLS 报错**：检查证书链；仅测试环境可临时开启 `tlsInsecure=true`
- **连接拒绝**：确认上游网关可达；检查防火墙/网络策略
