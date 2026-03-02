# internal-model-provider

OpenClaw custom provider plugin for internal OpenAI-compatible model gateways.

## What it does

- Registers provider: `internal-model`
- Direct upstream connection (no relay)
- API key authentication with `Authorization: Bearer` header
- Custom headers support
- OpenAI-compatible API format

## Install

```bash
cd ~/myagent
openclaw plugins install "$(pwd)/plugins/internal-model-provider"
openclaw plugins enable internal-model-provider
openclaw gateway restart
```

## Login

```bash
openclaw models auth login --provider internal-model --method api-key --set-default
```

Prompts:
1. Upstream base URL (e.g., `https://gateway.company.com/v1`)
2. API key
3. Custom headers JSON (optional)
4. Model IDs (comma-separated)

## Usage

After login, select the model:
```
/model internal-model/gpt-4o-mini
```

## Config shape

```json
{
  "models": {
    "providers": {
      "internal-model": {
        "baseUrl": "https://gateway.company.com/v1",
        "apiKey": "sk-xxx",
        "api": "openai-completions",
        "authHeader": true,
        "headers": {
          "x-tenant-id": "team-a"
        },
        "models": [
          { "id": "gpt-4o-mini", "name": "gpt-4o-mini", "contextWindow": 128000, "maxTokens": 8192 }
        ]
      }
    }
  }
}
```
