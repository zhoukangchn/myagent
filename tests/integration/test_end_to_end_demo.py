import json

from fastapi.testclient import TestClient

from app.main import app, app_state


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


def test_end_to_end_with_mocked_downstream(monkeypatch):
    created = client.post(
        "/api/servers",
        json={
            "name": "e2e",
            "base_url": "http://downstream",
            "mcp_endpoint": "/mcp",
            "description": "",
            "tags": [],
            "headers": {},
        },
    )
    assert created.status_code == 201
    sid = created.json()["id"]

    async def fake_init(server):
        return "ds-1"

    async def fake_list_tools(server, downstream_session_id):
        return {
            "tools": [
                {"name": "sum", "description": "sum", "inputSchema": {"type": "object"}},
                {
                    "name": "get_weather_forecast",
                    "description": "forecast",
                    "inputSchema": {"type": "object"},
                },
            ]
        }

    async def fake_call_tool(server, downstream_session_id, tool_name, arguments):
        if tool_name == "get_weather_forecast":
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "city": arguments.get("city", ""),
                                "days": arguments.get("days", 3),
                                "forecast": [
                                    {"date": "2026-02-11", "condition": "Sunny", "temp_high_c": 20, "temp_low_c": 10}
                                ],
                            }
                        ),
                    }
                ],
                "isError": False,
            }
        return {
            "content": [{"type": "text", "text": str(arguments.get("a", 0) + arguments.get("b", 0))}],
            "isError": False,
        }

    monkeypatch.setattr(app_state.downstream_client, "initialize", fake_init)
    monkeypatch.setattr(app_state.downstream_client, "list_tools", fake_list_tools)
    monkeypatch.setattr(app_state.downstream_client, "call_tool", fake_call_tool)

    app_state.fastmcp_hub.refresh_server_sync(sid)

    init_resp = client.post(
        "/mcp/",
        headers=_mcp_headers(sid),
        json=_rpc(
            "initialize",
            {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "clientInfo": {"name": "e2e", "version": "0.1"},
                "capabilities": {},
            },
        ),
    )
    assert init_resp.status_code == 200

    list_resp = client.post(
        "/mcp/",
        headers=_mcp_headers(sid),
        json=_rpc("tools/list", {}, 2),
    )
    assert list_resp.status_code == 200
    assert any(t["name"] == "e2e.sum" for t in _response_payload(list_resp)["result"]["tools"])
    assert any(t["name"] == "e2e.get_weather_forecast" for t in _response_payload(list_resp)["result"]["tools"])

    call_resp = client.post(
        "/mcp/",
        headers=_mcp_headers(sid),
        json=_rpc("tools/call", {"name": "e2e.sum", "arguments": {"a": 1, "b": 2}}, 3),
    )
    assert call_resp.status_code == 200

    forecast_resp = client.post(
        "/mcp/",
        headers=_mcp_headers(sid),
        json=_rpc(
            "tools/call",
            {"name": "e2e.get_weather_forecast", "arguments": {"city": "Beijing", "days": 3}},
            4,
        ),
    )
    assert forecast_resp.status_code == 200
