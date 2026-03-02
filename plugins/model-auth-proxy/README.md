# model-auth-proxy

OpenClaw plugin for provider `internal-model`, using a local relay to forward requests to an OpenAI-compatible upstream.

## What changed

This plugin now uses **provider headers only** (set during login) for:
- `upstreamUrl`
- `apiKey`
- `header1`
- `header2`

`plugin.config` is no longer used for those fields. It only keeps:
- `tlsInsecure` (optional, testing only)

## Install

```bash
cd ~/myagent
openclaw plugins install "$(pwd)/plugins/model-auth-proxy"
openclaw plugins enable model-auth-proxy
```

## Plugin config (`~/.openclaw/openclaw.json`)

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

## Login flow (required)

Run:

```bash
openclaw models auth login --provider internal-model --method api-key-relay --set-default
```

During login, you will be prompted for:
- Upstream OpenAI-compatible base URL (`upstreamUrl`)
- Upstream API key (`apiKey`)
- Optional custom header #1 (`header1`, format: `name:value`)
- Optional custom header #2 (`header2`, format: `name:value`)
- Model IDs (comma-separated)

The plugin writes these values into `models.providers.internal-model.headers` as relay control headers.

## Relay control headers (auto-generated)

After login, generated provider config looks like:

```json5
{
  models: {
    providers: {
      "internal-model": {
        "baseUrl": "http://127.0.0.1:19429/v1",
        "apiKey": "model-auth-proxy",
        "api": "openai-completions",
        "authHeader": false,
        "headers": {
          "x-openclaw-upstream-url": "https://gateway.company.com/v1",
          "x-openclaw-upstream-api-key": "YOUR_API_KEY",
          "x-openclaw-upstream-custom-headers": "{\"x-tenant-id\":\"team-a\",\"x-project\":\"prod\"}"
        }
      }
    }
  }
}
```

Do not manually move these values into `plugin.config`; they are expected in provider headers.

## TLS note

- Set `tlsInsecure=true` only for isolated test environments with self-signed certs.
- Keep `tlsInsecure=false` in production.

## Verify

```bash
openclaw plugins info model-auth-proxy
openclaw models status
```
