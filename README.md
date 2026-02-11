# Python MCP Hub Demo

A demo MCP hub with:
- Control plane REST APIs for downstream server registration
- Data plane MCP powered by official FastMCP server implementation
- In-memory storage and session mapping (demo only)

## Run (uv)

```bash
uv venv
source .venv/bin/activate
uv pip install -e '.[dev]'
uv run uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## Run Demo Weather MCP Server

In another terminal:

```bash
cd /home/zk/myagent
source .venv/bin/activate
uv run uvicorn demo.weather_server:app --host 127.0.0.1 --port 9001 --reload
```

## Control Plane API

- `POST /api/servers`
- `GET /api/servers`
- `GET /api/servers/{server_id}`
- `DELETE /api/servers/{server_id}`
- `GET /api/health`

## Data Plane MCP

`POST /mcp/`

Required header:
- `x-mcp-server-id: <server_id>`

Supported methods:
- `initialize`
- `tools/list`
- `tools/call`

Tool naming:
- Hub exposes aggregated tools as `server_name.tool_name`.
- Example: `weather-downstream.get_weather`.

## Demo Flow (curl)

1. Register downstream server:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/servers \
  -H 'content-type: application/json' \
  -d '{
    "name": "weather-downstream",
    "base_url": "http://127.0.0.1:9001",
    "mcp_endpoint": "/mcp",
    "description": "demo",
    "tags": ["demo"],
    "headers": {}
  }'
```

2. Initialize MCP on Hub (replace `<server_id>`):

```bash
curl -sS -X POST http://127.0.0.1:8000/mcp/ \
  -H 'content-type: application/json' \
  -H 'x-mcp-server-id: <server_id>' \
  -d '{
    "jsonrpc":"2.0",
    "id":1,
    "method":"initialize",
    "params":{
      "clientInfo":{"name":"demo-client"},
      "capabilities":{}
    }
  }'
```

3. List tools:

```bash
curl -sS -X POST http://127.0.0.1:8000/mcp/ \
  -H 'content-type: application/json' \
  -H 'x-mcp-server-id: <server_id>' \
  -d '{
    "jsonrpc":"2.0",
    "id":2,
    "method":"tools/list",
    "params":{}
  }'
```

4. Call weather tool:

```bash
curl -sS -X POST http://127.0.0.1:8000/mcp/ \
  -H 'content-type: application/json' \
  -H 'x-mcp-server-id: <server_id>' \
  -d '{
    "jsonrpc":"2.0",
    "id":3,
    "method":"tools/call",
    "params":{
      "name":"weather-downstream.get_weather",
      "arguments":{"city":"Beijing"}
    }
  }'
```

## Official Python MCP SDK Example

See `examples/sdk_client.py`:

```bash
uv run python examples/sdk_client.py --server-id <server_id> --city Beijing
```

## Notes

- Demo intentionally has no auth and no persistence.
- Downstream transport is Streamable HTTP style JSON-RPC over HTTP.
- Tool metadata cache refreshes on server registration and periodically in background.
