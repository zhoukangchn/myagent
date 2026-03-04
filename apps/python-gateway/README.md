# Python Gateway (`apps/python-gateway`)

FastAPI service:
- `POST /v1/chat/stream` — SSE streaming for chat clients
- `GET /v1/ws/openclaw` — reverse WebSocket from OpenClaw plugin
- `POST /v1/channel/post` — OpenClaw channel outbound callback (cron/subagent announce)

## Run

```bash
uv venv && source .venv/bin/activate
uv pip install -e '.[dev]'
cp .env.example .env
uv run uvicorn main:app --reload
```

Default bind: `0.0.0.0:8010` (via `.env`).

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
