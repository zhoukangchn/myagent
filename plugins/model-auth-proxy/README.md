# internal-model-auth-proxy

OpenClaw plugin that registers `internal-model` and relays requests to an OpenAI-compatible upstream gateway.

## Features

- Upstream auth via `Authorization: Bearer <apiKey>`
- Two optional custom headers (`header1`, `header2`)
- Optional TLS cert ignore (`tlsInsecure=true`) for testing
- OpenAI-compatible path relay (`/v1/chat/completions`, `/v1/responses`, etc.)

## Install

```bash
openclaw plugins install /home/zk/my/plugins/internal-model-auth
openclaw plugins enable internal-model-auth-proxy
```

## Plugin config

Put in `~/.openclaw/openclaw.json`:

```json5
{
  plugins: {
    entries: {
      "internal-model-auth-proxy": {
        enabled: true,
        config: {
          upstreamUrl: "https://gateway.company.com/v1",
          apiKey: "YOUR_TOKEN",
          header1: { name: "x-tenant-id", value: "team-a" },
          header2: { name: "x-project", value: "prod" },
          tlsInsecure: false
        }
      }
    }
  }
}
```

## Login

```bash
openclaw models auth login --provider internal-model --method api-key-relay --set-default
```

You will be prompted for model IDs (comma-separated), e.g. `gpt-4o-mini,gpt-4.1-mini`.

## Notes

- `tlsInsecure=true` is only for isolated test environments.
- Upstream URL is normalized to include `/v1`.
- Provider traffic is routed through a local relay on `127.0.0.1:19429`.
