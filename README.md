# SSE + WS Bridge Workspace

- `apps/python-gateway` — FastAPI SSE gateway (Python + uv)
- `plugins/ts-openclaw-channel` — OpenClaw channel plugin (TypeScript + npm)

## Quick start

```bash
cd apps/python-gateway
uv venv && source .venv/bin/activate
uv pip install -e '.[dev]'
cp .env.example .env
uv run uvicorn main:app --host 0.0.0.0 --port 8010 --reload
```

## Plugin install

```bash
./scripts/install-openclaw-plugin.sh
```

## Smoke test

```bash
./scripts/smoke.sh
```

## Docs

- 完整说明: `docs/sse-bridge-cron-guide.zh-CN.md`
