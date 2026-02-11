# MCP Hub Project

## Overview
Build a lightweight MCP (Model Context Protocol) service registry with in-memory storage.

## Architecture
- **Hub**: FastAPI-based registry center (in-memory, no database)
- **Server**: Example MCP server that auto-registers to Hub
- **Client**: Example MCP client that discovers services from Hub

## Directory Structure
```
mcp-hub/
├── hub/          # Registry center
├── server/       # Example MCP server
└── client/       # Example MCP client
```

## Requirements

### Hub Requirements:
1. FastAPI app with endpoints:
   - POST /register - Register a service (name, version, endpoint, tools, resources)
   - GET /services - List all registered services
   - GET /services/{name} - Get specific service
   - POST /services/{name}/heartbeat - Service heartbeat
   - DELETE /services/{name} - Unregister service
2. In-memory storage (dict), no database
3. Health check: mark service offline if no heartbeat for 60s
4. Background task to clean up offline services

### Server Requirements:
1. MCP server with SSE transport
2. At least 2 tools (e.g., calculate, get_time)
3. Auto-register to Hub on startup
4. Send heartbeat every 30s
5. Graceful shutdown to unregister

### Client Requirements:
1. Discover services from Hub
2. Connect to a service via SSE
3. Call tools on the discovered service
4. Simple CLI to list services and call tools

## Tech Stack
- Python 3.10+
- FastAPI + uvicorn
- mcp (official SDK)
- httpx (for HTTP calls)
- rich (for CLI output)

## Usage Flow
1. Start Hub: python hub/main.py
2. Start Server: python server/main.py (auto-registers)
3. Run Client: python client/main.py (discovers and calls)

Generate all three components with proper error handling and logging.
