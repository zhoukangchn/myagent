import json

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app, base_url="http://127.0.0.1:8000")
MCP_PROTOCOL_VERSION = "2025-06-18"


def _rpc(method: str, params: dict, req_id: int = 1):
    return {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}


def _mcp_headers(server_id: str) -> dict[str, str]:
    return {
        "x-mcp-server-id": server_id,
        "accept": "application/json, text/event-stream",
        "mcp-protocol-version": MCP_PROTOCOL_VERSION,
    }


def _response_payload(resp):
    text = resp.text
    if text.lstrip().startswith("{"):
        return resp.json()
    for line in text.splitlines():
        if line.startswith("data: "):
            return json.loads(line[len("data: ") :])
    raise AssertionError(f"unable to parse response body: {text}")


def test_mcp_initialize_list_and_call_flow(monkeypatch):
    created = client.post(
        "/api/servers",
        json={
            "name": "remote",
            "base_url": "http://downstream",
            "mcp_endpoint": "/mcp",
            "description": "",
            "tags": [],
            "headers": {},
        },
    )
    sid = created.json()["id"]

    from app.main import app_state

    async def fake_init(server):
        return "down-1"

    async def fake_list_tools(server, downstream_session_id):
        return {
            "tools": [
                {"name": "echo", "description": "Echo", "inputSchema": {"type": "object"}},
                {
                    "name": "get_weather_forecast",
                    "description": "Forecast",
                    "inputSchema": {"type": "object"},
                },
            ]
        }

    async def fake_call_tool(server, downstream_session_id, tool_name, arguments):
        if tool_name == "echo":
            assert arguments == {"text": "hello"}
            return {"content": [{"type": "text", "text": "hello"}], "isError": False}
        if tool_name == "get_weather_forecast":
            assert arguments == {"city": "Beijing", "days": 3}
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "city": "Beijing",
                                "days": 3,
                                "forecast": [
                                    {"date": "2026-02-11", "condition": "Sunny", "temp_high_c": 21, "temp_low_c": 11}
                                ],
                            }
                        ),
                    }
                ],
                "isError": False,
            }
        raise AssertionError(f"unexpected tool: {tool_name}")

    monkeypatch.setattr(app_state.downstream_client, "initialize", fake_init)
    monkeypatch.setattr(app_state.downstream_client, "list_tools", fake_list_tools)
    monkeypatch.setattr(app_state.downstream_client, "call_tool", fake_call_tool)

    # Warm-up catalog/app for this server.
    app_state.fastmcp_hub.refresh_server_sync(sid)

    init_resp = client.post(
        "/mcp/",
        headers=_mcp_headers(sid),
        json=_rpc(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "clientInfo": {"name": "demo-client", "version": "0.1"},
                "capabilities": {},
            },
        ),
    )
    assert init_resp.status_code == 200

    list_resp = client.post(
        "/mcp/",
        headers=_mcp_headers(sid),
        json=_rpc("tools/list", {}, req_id=2),
    )
    assert list_resp.status_code == 200
    tools = _response_payload(list_resp)["result"]["tools"]
    assert any(t["name"] == "remote.echo" for t in tools)
    assert any(t["name"] == "remote.get_weather_forecast" for t in tools)

    call_resp = client.post(
        "/mcp/",
        headers=_mcp_headers(sid),
        json=_rpc("tools/call", {"name": "remote.echo", "arguments": {"text": "hello"}}, req_id=3),
    )
    assert call_resp.status_code == 200

    forecast_resp = client.post(
        "/mcp/",
        headers=_mcp_headers(sid),
        json=_rpc(
            "tools/call",
            {"name": "remote.get_weather_forecast", "arguments": {"city": "Beijing", "days": 3}},
            req_id=4,
        ),
    )
    assert forecast_resp.status_code == 200


def test_mcp_missing_header_returns_400():
    resp = client.post(
        "/mcp/",
        headers={
            "accept": "application/json, text/event-stream",
            "mcp-protocol-version": MCP_PROTOCOL_VERSION,
        },
        json=_rpc(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "clientInfo": {"name": "x", "version": "0.1"},
                "capabilities": {},
            },
        ),
    )
    assert resp.status_code == 200
    assert _response_payload(resp)["error"]["code"] == -32602
