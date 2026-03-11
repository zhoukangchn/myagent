# TS OpenClaw Channel (`plugins/ts-openclaw-channel`)

OpenClaw channel plugin:
- Reverse WebSocket bridge to Python gateway
- Official outbound channel delivery for cron/subagent (`sse_bridge`)
- Inbound: `user.message` → channel-inbound dispatch → streaming delta response

## Required env vars

- `OPENCLAW_SHARED_SECRET`
- `SSE_CHANNEL_POST_URL` — outbound POST target (default: `http://127.0.0.1:8000/v1/channel/post`)

## Optional env vars

| Variable | Default | Description |
|---|---|---|
| `BRIDGE_WS_URL` | `ws://127.0.0.1:8000/v1/ws/openclaw` | Gateway WS URL |
| `OPENCLAW_ID` | `openclaw-local` | OpenClaw instance ID |
| `BRIDGE_OPENCLAW_AGENT_ID` | `main` | Agent ID for routing |
| `BRIDGE_REQUEST_TIMEOUT_MS` | `120000` | Request timeout |
| `SSE_CHANNEL_DEFAULT_TO` | (empty) | Fallback `chat_id:thread_id` |
| `SSE_BRIDGE_HUMAN_DELAY_MODE` | `off` | Buffered reply human delay: `off`, `natural`, `custom` |
| `SSE_BRIDGE_HUMAN_DELAY_MIN_MS` | `800` | Min delay when `SSE_BRIDGE_HUMAN_DELAY_MODE=custom` |
| `SSE_BRIDGE_HUMAN_DELAY_MAX_MS` | `2500` | Max delay when `SSE_BRIDGE_HUMAN_DELAY_MODE=custom` |

## Install

```bash
./scripts/install-openclaw-plugin.sh
```

## Development

```bash
npm install && npm run check
```

## TODO

- Add a per-session outbound send queue for live `sendText`/`sendMedia` so multi-message replies can be intentionally spaced.
- Current `humanDelay` only affects OpenClaw buffered reply blocks; it does not slow down agent-driven consecutive outbound sends.

## Full guide

See `docs/sse-bridge-cron-guide.zh-CN.md`.
