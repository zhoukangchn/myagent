# Python Gateway (`apps/python-gateway`)

FastAPI service:
- `POST /v1/chat/stream` — SSE streaming for chat clients
- `GET /v1/ws/openclaw` — reverse WebSocket from OpenClaw plugin
- outbound third-party WebSocket client — gateway actively connects to external WS and replies on the same socket
- `POST /v1/channel/post` — OpenClaw channel outbound callback (cron/subagent announce)

## Run

```bash
uv venv && source .venv/bin/activate
uv sync --extra dev --no-install-project
cp .env.example .env
PYTHONPATH=src uvicorn main:app --reload
```

Default bind: `0.0.0.0:8000` (via `.env`). `PYTHONPATH=src` keeps local imports working without installing the project package.

## Required headers

### Chat → Gateway (`POST /v1/chat/stream`)
`x-client-id`, `x-timestamp`, `x-nonce`, `x-signature`

### OpenClaw → Gateway (`GET /v1/ws/openclaw`)
`x-openclaw-id`, `x-timestamp`, `x-nonce`, `x-signature`

### OpenClaw Channel Outbound → Gateway (`POST /v1/channel/post`)
No signature check in current implementation (local relay stub).

## Signature

`hex(hmac_sha256(secret, METHOD + "\n" + PATH + "\n" + TIMESTAMP + "\n" + NONCE + "\n" + SHA256(body)))`

WebSocket handshake uses empty body.

## Third-Party WS Mode

Set these env vars to let the gateway actively connect to an external WebSocket server:

```dotenv
THIRD_PARTY_WS_ENABLED=true
THIRD_PARTY_WS_URL=ws://127.0.0.1:8765/ws
THIRD_PARTY_WS_HEADERS_JSON={"x-api-key":"demo"}
THIRD_PARTY_WS_BEARER_TOKEN=
```

Default protocol shape:

- inbound request:
  - `{"type":"chat.message","id":"req-1","chat_id":"chat-1","thread_id":"root","sender_id":"u-1","text":"hello","metadata":{}}`
- outbound events:
  - `chat.ack`
  - `chat.reply.start`
  - `chat.reply.delta`
  - `chat.reply.done`
  - `chat.reply.error`
  - `chat.tool`
