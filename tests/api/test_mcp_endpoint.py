from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _rpc(method: str, params: dict, req_id: int = 1):
    return {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}


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
        return {"tools": [{"name": "echo", "description": "Echo", "inputSchema": {"type": "object"}}]}

    async def fake_call_tool(server, downstream_session_id, tool_name, arguments):
        assert tool_name == "echo"
        assert arguments == {"text": "hello"}
        return {"content": [{"type": "text", "text": "hello"}], "isError": False}

    monkeypatch.setattr(app_state.downstream_client, "initialize", fake_init)
    monkeypatch.setattr(app_state.downstream_client, "list_tools", fake_list_tools)
    monkeypatch.setattr(app_state.downstream_client, "call_tool", fake_call_tool)

    # Warm-up catalog/app for this server.
    app_state.fastmcp_hub.refresh_server_sync(sid)

    init_resp = client.post(
        "/mcp",
        headers={"x-mcp-server-id": sid},
        json=_rpc("initialize", {"clientInfo": {"name": "demo-client"}, "capabilities": {}}),
    )
    assert init_resp.status_code == 200

    list_resp = client.post(
        "/mcp",
        headers={"x-mcp-server-id": sid},
        json=_rpc("tools/list", {}, req_id=2),
    )
    assert list_resp.status_code == 200
    tools = list_resp.json()["result"]["tools"]
    assert any(t["name"] == "remote.echo" for t in tools)

    call_resp = client.post(
        "/mcp",
        headers={"x-mcp-server-id": sid},
        json=_rpc("tools/call", {"name": "remote.echo", "arguments": {"text": "hello"}}, req_id=3),
    )
    assert call_resp.status_code == 200


def test_mcp_missing_header_returns_400():
    resp = client.post(
        "/mcp",
        json=_rpc("initialize", {"clientInfo": {"name": "x"}, "capabilities": {}}),
    )
    assert resp.status_code == 200
    assert resp.json()["error"]["code"] == -32602
