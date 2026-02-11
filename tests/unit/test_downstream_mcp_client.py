import json

import httpx
import pytest

from app.core.downstream_mcp_client import DownstreamMcpClient
from app.core.models import ServerRecord


@pytest.mark.asyncio
async def test_initialize_and_tool_calls_roundtrip():
    calls = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.headers.get("mcp-session-id"), request.content.decode()))
        body = json.loads(request.content.decode())
        method = body["method"]
        if method == "initialize":
            return httpx.Response(
                200,
                json={"jsonrpc": "2.0", "id": body["id"], "result": {"ok": True}},
                headers={"mcp-session-id": "sess-1"},
            )
        if method == "tools/list":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {"tools": [{"name": "echo", "inputSchema": {"type": "object"}}]},
                },
            )
        if method == "tools/call":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {"content": [{"type": "text", "text": "ok"}], "isError": False},
                },
            )
        return httpx.Response(400, json={"error": "unknown"})

    transport = httpx.MockTransport(handler)
    client = DownstreamMcpClient(timeout_seconds=2.0, transport=transport)
    server = ServerRecord(
        id="1",
        name="s",
        base_url="http://mock",
        mcp_endpoint="/mcp",
        description="",
        tags=[],
        headers={},
        status="active",
        created_at="2026-02-11T00:00:00Z",
        updated_at="2026-02-11T00:00:00Z",
    )

    sid = await client.initialize(server)
    assert sid == "sess-1"

    tools = await client.list_tools(server, sid)
    assert tools["tools"][0]["name"] == "echo"

    result = await client.call_tool(server, sid, "echo", {"text": "hello"})
    assert result["isError"] is False
    assert calls[1][0] == "sess-1"


@pytest.mark.asyncio
async def test_raises_on_timeout():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout")

    client = DownstreamMcpClient(timeout_seconds=0.01, transport=httpx.MockTransport(handler))
    server = ServerRecord(
        id="1",
        name="s",
        base_url="http://mock",
        mcp_endpoint="/mcp",
        description="",
        tags=[],
        headers={},
        status="active",
        created_at="2026-02-11T00:00:00Z",
        updated_at="2026-02-11T00:00:00Z",
    )

    with pytest.raises(Exception):
        await client.initialize(server)
