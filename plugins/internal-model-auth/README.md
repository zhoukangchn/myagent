# internal-model-auth

用于 OpenClaw 的内部模型 Provider 插件，支持**自定义 Header 注入**和**自定义 Body Patch 注入**。

## 功能说明

- 注册 Provider：`internal-model`
- 登录方式：`header-body`
- 支持上游自定义请求头（JSON 对象）
- 支持上游请求体补丁（JSON 对象，浅合并）
- 内置本地 relay 转发服务
- 保护保留字段，防止误覆盖核心请求字段

## 公司环境安装（推荐）

```bash
git clone <你的仓库地址>
cd myagent
openclaw plugins install "$(pwd)/plugins/internal-model-auth"
openclaw plugins enable internal-model-auth
```

## 插件运行参数（可选）

编辑 `~/.openclaw/openclaw.json`：

```json5
{
  plugins: {
    entries: {
      "internal-model-auth": {
        enabled: true,
        config: {
          relayPort: 19321,
          tlsInsecure: false,
          requestTimeoutMs: 120000,
          maxBodyBytes: 4194304
        }
      }
    }
  }
}
```

参数说明：

- `relayPort`: 本地 relay 监听端口
- `tlsInsecure`: 是否关闭上游 TLS 证书校验（仅测试）
- `requestTimeoutMs`: 上游请求超时
- `maxBodyBytes`: 允许的最大请求体

## 登录配置（核心步骤）

```bash
openclaw models auth login --provider internal-model --method header-body --set-default
```

按提示输入：

1. 上游模型网关 URL（例如 `https://internal-llm.company.com/v1`）
2. 自定义 Header JSON（例如 `{"x-api-key":"xxx","x-tenant-id":"team-a"}`）
3. Body Patch JSON（例如 `{"temperature":0.2,"top_p":0.9}`）
4. 模型 ID（逗号分隔，例如 `model-a,model-b`）

## 模型 ID 是什么

- 这里填写的 `模型 ID`，就是请求体里的 `model` 字段值。
- 可以理解为和 OpenAI 接口里的 `model` 参数一致。
- 登录时填写的模型会注册为 OpenClaw 可选模型，格式通常是：`internal-model/<model-id>`。

## 模型清单（示例）

以下是通用示例，请替换为你公司网关真实支持的模型 ID：

- `chat-model`
- `chat-model-32k`
- `reasoning-model`
- `vision-model`

## 使用与验证

安装并登录后，默认模型会设置为 `internal-model/<第一个模型ID>`。

可用以下命令检查状态：

```bash
openclaw plugins info internal-model-auth
openclaw models status
```

## 快速切换模型

- 若希望切换模型，重新执行登录命令并把目标模型放在第一个：

```bash
openclaw models auth login --provider internal-model --method header-body --set-default
```

- 例如你输入 `reasoning-model,chat-model`，默认模型会变成 `internal-model/reasoning-model`。

## 合并与安全规则

Body Patch 使用浅合并：

```js
{ ...requestBody, ...bodyPatch }
```

以下字段**禁止覆盖**：

- `model`
- `messages`
- `input`
- `tools`
- `tool_choice`
- `stream`
- `max_tokens`
- `response_format`
- `parallel_tool_calls`

如果 Body Patch 包含上述字段，插件会直接拒绝请求并返回错误。

## TLS 注意事项

- `tlsInsecure=true` 会禁用证书校验，仅可用于隔离测试环境。
- 生产环境请保持 `tlsInsecure=false`，并使用可信证书链/内部 CA。

## 常见问题

- 401/403：通常是 Header 配置错误或 token 失效。
- 400：Body Patch 不是合法 JSON，或覆盖了保留字段。
- TLS 报错：检查证书链；仅测试环境可临时开启 `tlsInsecure=true`。
