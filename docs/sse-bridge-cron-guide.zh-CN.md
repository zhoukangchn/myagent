# SSE Bridge + OpenClaw Cron 推送完整说明

本文档说明如何把你的聊天软件对接到 OpenClaw，并验证“定时任务消息推送”链路可用。

## 1. 目标架构

链路分两段：

1. 入站（聊天软件 -> OpenClaw）  
   聊天软件调用 Python Gateway 的 `POST /v1/chat/stream`（SSE）  
   Python Gateway 通过反向 WS 转发给 OpenClaw 插件  
   插件调用 `openclaw agent` 产出回复，再经 SSE 流返回给聊天软件

2. 出站（OpenClaw -> 聊天软件）  
   OpenClaw 的 cron/subagent announce 走官方 channel delivery  
   `channel = sse_bridge`  
   插件 `outbound.sendText/sendMedia` 把消息 POST 到你提供的接口

## 2. 目录结构

- Python 服务：`apps/python-gateway`
- TypeScript 插件：`plugins/ts-openclaw-channel`
- 文档入口：`README.md`

## 3. Python Gateway 配置与启动

进入目录：

```bash
cd apps/python-gateway
```

初始化：

```bash
uv venv
source .venv/bin/activate
uv sync --extra dev --no-install-project
cp .env.example .env
```

`.env` 关键项：

```dotenv
BRIDGE_BIND_HOST=0.0.0.0
BRIDGE_BIND_PORT=8000

CHAT_SHARED_SECRET=dev-chat-secret
OPENCLAW_SHARED_SECRET=dev-openclaw-secret
```

启动：

```bash
PYTHONPATH=src uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

说明：
- `OPENCLAW_SHARED_SECRET` 必须与 OpenClaw 侧一致。
- 这里不安装本地项目包，避免生成 `.egg-info`；因此启动时显式加上 `PYTHONPATH=src`。

## 4. OpenClaw 插件安装与环境变量

插件路径：

```text
plugins/ts-openclaw-channel
```

### 4.1 开发检查（可选）

下面这一步只用于本地开发检查，不等于“安装到 OpenClaw”：

```bash
cd plugins/ts-openclaw-channel
npm install
npm run check
```

### 4.2 官方安装（必做）

回到仓库根目录后，执行 OpenClaw 插件安装：

```bash
./scripts/install-openclaw-plugin.sh
```

等价手动命令：

```bash
openclaw plugins install --link /home/zk/myagent/plugins/ts-openclaw-channel
openclaw plugins enable ts-openclaw-channel
```

验证安装状态：

```bash
openclaw plugins list --enabled --verbose
openclaw plugins info ts-openclaw-channel
```

预期：
- 能看到 `id = ts-openclaw-channel`
- `channelIds` 包含 `sse_bridge`

如需移除插件：

```bash
openclaw plugins uninstall ts-openclaw-channel
```

启动 OpenClaw 网关前设置环境变量（示例）：

```bash
export BRIDGE_WS_URL='ws://127.0.0.1:8000/v1/ws/openclaw'
export OPENCLAW_SHARED_SECRET='dev-openclaw-secret'
export OPENCLAW_ID='openclaw-local'

export SSE_CHANNEL_POST_URL='http://127.0.0.1:8000/v1/channel/post'
export SSE_CHANNEL_DEFAULT_TO='cron-demo:thread-1'
```

启动 OpenClaw：

```bash
openclaw gateway run
```

提示：
- 执行 `plugins install/enable` 后，如果网关已在运行，需要重启网关才能生效。

## 5. 插件与 channel 的关系

- 插件 id：`ts-openclaw-channel`
- 官方注册 channel id：`sse_bridge`
- cron 推送时必须使用：
  - `delivery.channel = "sse_bridge"`

你可以在 cron 命令中显式指定目标：

- `--to chat_id:thread_id`

或者依赖默认目标：

- `SSE_CHANNEL_DEFAULT_TO`

## 6. Cron 推送实测步骤

### 6.1 确认 Python Gateway 已启动

`SSE_CHANNEL_POST_URL` 默认指向 `POST /v1/channel/post`，因此无需额外 mock 服务。

### 6.2 新增并执行 cron

```bash
openclaw cron add \
  --name demo-sse-cron \
  --every 1h \
  --message "cron push test" \
  --announce \
  --channel sse_bridge \
  --to cron-demo:thread-1 \
  --json
```

得到 `job_id` 后执行：

```bash
openclaw cron run <job_id> --timeout 90000
```

预期：
- 命令返回 `{"ok": true, "ran": true}`
- Python Gateway 日志中出现：
  - `channel_post received source=openclaw-cron-delivery ...`
- `POST /v1/channel/post` 接口返回：
  - `{"ok": true, "accepted": true, "forwarded": false}`
- 回调 payload 包含：
  - `chat_id`
  - `thread_id`
  - `content`

## 7. 出站 payload 结构

插件发送到 `SSE_CHANNEL_POST_URL` 的 body：

```json
{
  "chat_id": "cron-demo",
  "thread_id": "thread-1",
  "message_id": "oc-1772551015823",
  "role": "assistant",
  "content": "Cron test received ...",
  "metadata": {
    "source": "openclaw-cron-delivery",
    "account_id": "default"
  }
}
```

## 8. 常见问题与处理

### 问题 1：`Outbound not configured for channel: sse_bridge`

原因：
- 插件 outbound 未完整注册，或插件未加载。

当前修复点：
- `sse_bridge` 同时实现了 `sendText` 和 `sendMedia`，否则 OpenClaw 不会注册该 outbound handler。

### 问题 2：`SSE_CHANNEL_POST_URL is empty`

处理：
- 设置 `SSE_CHANNEL_POST_URL` 后重启 `openclaw gateway run`。

### 问题 3：`missing target to for sse_bridge`

处理：
- cron 增加 `--to chat_id:thread_id`，或设置 `SSE_CHANNEL_DEFAULT_TO`。

### 问题 4：Gateway 已启动但插件持续 `bridge status=error/closed`

排查：
- 检查 `BRIDGE_WS_URL` 是否可访问。
- 检查 `OPENCLAW_SHARED_SECRET` 双端是否一致。
- 检查 Python Gateway 的 `/v1/ws/openclaw` 签名头验证是否通过。

## 9. 生产建议

- `SSE_CHANNEL_POST_URL` 指向你实际聊天系统的“主动出站 POST”接口。
- `chat_id/thread_id` 建议与你业务侧会话主键严格对齐。
- 为 POST 增加鉴权（例如 HMAC header），避免被伪造请求调用。
- 保留请求日志（request_id、chat_id、thread_id）用于追踪。

## 10. 快速回归命令

仓库根目录：

```bash
./scripts/smoke.sh
```

包含：
- Python 测试（含 SSE/WS E2E）
- 插件 manifest/type 检查
