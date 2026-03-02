# model-auth-proxy

OpenClaw provider plugin for internal model gateways requiring API key and custom headers.

## What it does

- Registers provider: `internal-model`
- Uses direct upstream connection (no local relay)
- Stores API key directly as provider `apiKey`
- Sends API key in Authorization header (`authHeader: true`)
- Writes optional custom headers to `provider.headers`

## Install

```bash
openclaw plugins install "$(pwd)/plugins/model-auth-proxy"
openclaw plugins enable model-auth-proxy
```

## Optional plugin config

Edit `~/.openclaw/openclaw.json`:

```json5
{
  plugins: {
    entries: {
      "model-auth-proxy": {
        enabled: true,
        config: {
          tlsInsecure: false
        }
      }
    }
  }
}
```

`tlsInsecure: true` sets `NODE_TLS_REJECT_UNAUTHORIZED=0` for the running OpenClaw process. Use only for testing.

## Login flow

```bash
openclaw models auth login --provider internal-model --method api-key-headers --set-default
```

Prompts:

1. Upstream base URL (required)
2. API key (required)
3. Custom headers JSON (optional)
4. Model IDs (comma-separated)

## Generated provider config shape

```json
{
  "models": {
    "providers": {
      "internal-model": {
        "baseUrl": "https://gateway.company.com/v1",
        "apiKey": "YOUR_API_KEY",
        "api": "openai-completions",
        "authHeader": true,
        "headers": {
          "x-tenant-id": "team-a",
          "x-project": "prod"
        },
        "models": [
          {
            "id": "gpt-4o-mini",
            "name": "gpt-4o-mini",
            "contextWindow": 128000,
            "maxTokens": 8192
          }
        ]
      }
    }
  }
}
```
