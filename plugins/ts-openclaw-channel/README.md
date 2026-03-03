# TS OpenClaw Channel (`plugins/ts-openclaw-channel`)

Thin OpenClaw plugin that opens reverse WebSocket to Python gateway.

## Plugin definition
- Primary plugin manifest: `openclaw.plugin.json`
- Package metadata fallback: `package.json -> openclaw`
- Naming source:
  - Display name: `openclaw.plugin.json.name`
  - Package name: `package.json.name`
- Consistency rule: `extensions` must match in both files.

## Env
- `BRIDGE_WS_URL` default: `ws://127.0.0.1:8010/v1/ws/openclaw`
- `OPENCLAW_SHARED_SECRET`
- `OPENCLAW_ID`

## Dev

```bash
cd plugins/ts-openclaw-channel
npm install
npm run check
```

This plugin currently provides connection/auth skeleton and message envelope types.
