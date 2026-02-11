from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Weather MCP Demo Server", version="0.1.0")

_CONDITIONS = ["Sunny", "Cloudy", "Rain", "Snow", "Windy", "Fog"]


def _rpc_ok(req_id: Any, result: dict[str, Any], headers: dict[str, str] | None = None) -> JSONResponse:
    return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": result}, headers=headers or {})


def _rpc_err(req_id: Any, code: int, message: str) -> JSONResponse:
    return JSONResponse({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}})


@app.post("/mcp")
async def mcp(request: Request) -> JSONResponse:
    payload = await request.json()
    req_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})

    if method == "initialize":
        # Demo server always assigns a fixed session id.
        return _rpc_ok(
            req_id,
            {
                "protocolVersion": "2025-06-18",
                "serverInfo": {"name": "weather-mcp-demo", "version": "0.1.0"},
                "capabilities": {"tools": {}},
            },
            headers={"mcp-session-id": "weather-demo-session"},
        )

    if method == "tools/list":
        if request.headers.get("mcp-session-id") != "weather-demo-session":
            return JSONResponse({"error": "session not found"}, status_code=404)
        return _rpc_ok(
            req_id,
            {
                "tools": [
                    {
                        "name": "get_weather",
                        "description": "Return random weather for a city",
                        "inputSchema": {
                            "type": "object",
                            "properties": {"city": {"type": "string"}},
                            "required": ["city"],
                        },
                    }
                ]
            },
        )

    if method == "tools/call":
        if request.headers.get("mcp-session-id") != "weather-demo-session":
            return JSONResponse({"error": "session not found"}, status_code=404)

        name = params.get("name")
        if name != "get_weather":
            return _rpc_err(req_id, -32602, f"unknown tool: {name}")

        arguments = params.get("arguments", {})
        city = arguments.get("city")
        if not city:
            return _rpc_err(req_id, -32602, "city is required")

        condition = random.choice(_CONDITIONS)
        temperature_c = random.randint(-5, 36)
        observed_at = datetime.now(timezone.utc).isoformat()

        return _rpc_ok(
            req_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": f"{city}: {condition}, {temperature_c}C (observed_at={observed_at})",
                    }
                ],
                "isError": False,
            },
        )

    return _rpc_err(req_id, -32601, f"method not found: {method}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("demo.weather_server:app", host="127.0.0.1", port=9001, reload=True)
