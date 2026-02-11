# Architecture

## Components

- `InMemoryRegistry`: Stores downstream MCP server definitions.
- `HubSessionStore`: Caches downstream session by `server_id`.
- `DownstreamMcpClient`: Performs JSON-RPC calls to downstream MCP servers.
- `ToolCatalogStore`: Caches aggregated tool metadata as `server.tool` names.
- `FastMcpHubGateway`: ASGI gateway that dispatches to per-server FastMCP apps using `x-mcp-server-id`.
- Control plane REST (`/api/servers`): Manages server registrations.

## Data Flow

1. Admin registers downstream server via REST.
2. Hub initializes downstream session and refreshes tool catalog for that server.
3. MCP client connects to `POST /mcp` with header `x-mcp-server-id`.
4. FastMCP app for that server handles `initialize/list_tools/call_tool`.
5. Tool calls are proxied to downstream MCP server.

## Error Handling

- Missing `x-mcp-server-id` -> HTTP 400 with MCP-style error payload.
- Unknown server id -> HTTP 404 with MCP-style error payload.
- Downstream session expiration (HTTP 404) -> one-time reinitialize + retry.
