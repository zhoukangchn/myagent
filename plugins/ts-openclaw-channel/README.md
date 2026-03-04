# TS OpenClaw Channel (`plugins/ts-openclaw-channel`)

OpenClaw channel plugin for bridging:
- reverse WebSocket to Python gateway,
- official outbound channel delivery for cron/subagent announce (`sse_bridge`).

## Plugin definition files

- Primary manifest: `openclaw.plugin.json`
- Package fallback metadata: `package.json -> openclaw`
- Naming source:
  - Display name: `openclaw.plugin.json.name`
  - Package name: `package.json.name`
- Consistency requirement:
  - `extensions` must match in both files.

## Runtime behavior

- Registered channel id: `sse_bridge`
- Inbound bridge message handling:
  - `user.message` -> invoke `openclaw agent ... --json` for interactive turns
  - `system.event` -> `enqueueSystemEvent + requestHeartbeatNow`
- Outbound delivery:
  - `sendText`: POST to `SSE_CHANNEL_POST_URL`
  - `sendMedia`: degrade to text + media URL and POST to `SSE_CHANNEL_POST_URL`

## Required env vars

- `OPENCLAW_SHARED_SECRET`
- `SSE_CHANNEL_POST_URL`

## Optional env vars

- `BRIDGE_WS_URL` default `ws://127.0.0.1:8010/v1/ws/openclaw`
- `OPENCLAW_ID` default `openclaw-local`
- `OPENCLAW_CMD` default `openclaw` (Windows runs via `cmd.exe /c`, defaulting to `openclaw.cmd`)
- `BRIDGE_MODE` default `legacy-cli` (only `legacy-cli` is implemented in demo)
- `BRIDGE_REQUEST_TIMEOUT_MS` default `120000`
- `OPENCLAW_AGENT_TIMEOUT_SEC` default `90`
- `BRIDGE_OPENCLAW_AGENT_ID` default `main`
- `SSE_CHANNEL_DEFAULT_TO` default empty
  - format: `chat_id:thread_id`
  - used as fallback when cron delivery target has no explicit `to`

## Outbound payload format

`sendText/sendMedia` sends JSON:

```json
{
  "chat_id": "cron-demo",
  "thread_id": "thread-1",
  "message_id": "oc-<timestamp>",
  "role": "assistant",
  "content": "message text",
  "metadata": {
    "source": "openclaw-cron-delivery",
    "account_id": "default"
  }
}
```

## Install (OpenClaw official)

Install as linked local plugin:

```bash
./scripts/install-openclaw-plugin.sh
```

If gateway is already running, restart it after install/enable.

Equivalent manual commands:

```bash
openclaw plugins install --link /home/zk/myagent/plugins/ts-openclaw-channel
openclaw plugins enable ts-openclaw-channel
openclaw plugins list --enabled --verbose
```

## Development

```bash
cd plugins/ts-openclaw-channel
npm install
npm run check
```

## Verification checklist

1. Confirm plugin loaded:
   - `openclaw plugins list` should include `ts-openclaw-channel`.
2. Confirm channel registered:
   - run a cron with `--channel sse_bridge`.
3. Confirm outbound works:
   - gateway log should contain `res ✓ send ... channel=sse_bridge`.
4. Confirm receiver got POST:
   - your channel server should receive JSON body with `chat_id/thread_id/content`.

## Common issues

- `Outbound not configured for channel: sse_bridge`
  - cause: outbound adapter is not ready or plugin not loaded.
  - fixed in current code by implementing both `sendText` and `sendMedia`.
- `SSE_CHANNEL_POST_URL is empty`
  - set `SSE_CHANNEL_POST_URL` before starting `openclaw gateway run`.
- `missing target to for sse_bridge`
  - add cron `--to chat_id:thread_id` or set `SSE_CHANNEL_DEFAULT_TO`.

## Full guide

See `docs/sse-bridge-cron-guide.zh-CN.md` for complete setup and end-to-end test steps.
