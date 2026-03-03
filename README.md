# SSE + WS Bridge Workspace

This repository is intentionally minimized to two parts:
- `apps/python-gateway` (FastAPI + uv)
- `plugins/ts-openclaw-channel` (OpenClaw plugin + npm)

## One-command smoke check

From repo root:

```bash
./scripts/smoke.sh
```

It will:
1. Run Python tests, including end-to-end SSE over reverse WebSocket flow.
2. Run plugin manifest/type checks.
3. Clean plugin `node_modules` after checks.

## Manual run (gateway)

```bash
cd apps/python-gateway
uv venv
source .venv/bin/activate
uv pip install -e '.[dev]'
uv run uvicorn main:app --host 127.0.0.1 --port 8010 --reload
```
