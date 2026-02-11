from fastapi.testclient import TestClient

from app.main import app, app_state


client = TestClient(app)


def _rpc(method: str, params: dict, req_id: int = 1):
    return {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}


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
        return {"tools": [{"name": "sum", "description": "sum", "inputSchema": {"type": "object"}}]}

    async def fake_call_tool(server, downstream_session_id, tool_name, arguments):
        return {
            "content": [{"type": "text", "text": str(arguments.get("a", 0) + arguments.get("b", 0))}],
            "isError": False,
        }

    monkeypatch.setattr(app_state.downstream_client, "initialize", fake_init)
    monkeypatch.setattr(app_state.downstream_client, "list_tools", fake_list_tools)
    monkeypatch.setattr(app_state.downstream_client, "call_tool", fake_call_tool)

    app_state.fastmcp_hub.refresh_server_sync(sid)

    init_resp = client.post(
        "/mcp",
        headers={"x-mcp-server-id": sid},
        json=_rpc("initialize", {"clientInfo": {"name": "e2e"}, "capabilities": {}}),
    )
    assert init_resp.status_code == 200

    list_resp = client.post(
        "/mcp",
        headers={"x-mcp-server-id": sid},
        json=_rpc("tools/list", {}, 2),
    )
    assert list_resp.status_code == 200
    assert any(t["name"] == "e2e.sum" for t in list_resp.json()["result"]["tools"])

    call_resp = client.post(
        "/mcp",
        headers={"x-mcp-server-id": sid},
        json=_rpc("tools/call", {"name": "e2e.sum", "arguments": {"a": 1, "b": 2}}, 3),
    )
    assert call_resp.status_code == 200
