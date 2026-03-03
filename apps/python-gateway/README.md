# Python Gateway (`apps/python-gateway`)

FastAPI service that:
- exposes `POST /v1/chat/stream` as SSE output for chat software,
- accepts reverse WebSocket from OpenClaw on `GET /v1/ws/openclaw`.

## Run

```bash
cd apps/python-gateway
uv venv
source .venv/bin/activate
uv pip install -e '.[dev]'
cp .env.example .env
uv run uvicorn main:app --reload
```

Default bind is `0.0.0.0:8010` (configured via `.env` / env vars).
To apply bind config from settings directly:

```bash
uv run python -m gateway
```

You can still override at runtime, for example:

```bash
BRIDGE_BIND_HOST=127.0.0.1 BRIDGE_BIND_PORT=8010 uv run uvicorn main:app --host "$BRIDGE_BIND_HOST" --port "$BRIDGE_BIND_PORT" --reload
```

## Required headers

### Chat -> Gateway (`POST /v1/chat/stream`)
- `x-client-id`
- `x-timestamp`
- `x-nonce`
- `x-signature`

### OpenClaw -> Gateway (`GET /v1/ws/openclaw`)
- `x-openclaw-id`
- `x-timestamp`
- `x-nonce`
- `x-signature`

## Signature rule

`hex(hmac_sha256(secret, METHOD + "\\n" + PATH + "\\n" + TIMESTAMP + "\\n" + NONCE + "\\n" + SHA256(body)))`

For WebSocket handshake body is empty bytes.
