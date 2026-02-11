from fastapi.testclient import TestClient

from demo.weather_server import app


client = TestClient(app)


def test_weather_server_mcp_flow():
    init_resp = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"clientInfo": {"name": "test"}, "capabilities": {}},
        },
    )
    assert init_resp.status_code == 200
    assert init_resp.headers.get("mcp-session-id") == "weather-demo-session"

    list_resp = client.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        headers={"mcp-session-id": "weather-demo-session"},
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["result"]["tools"][0]["name"] == "get_weather"

    call_resp = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "get_weather", "arguments": {"city": "Beijing"}},
        },
        headers={"mcp-session-id": "weather-demo-session"},
    )
    assert call_resp.status_code == 200
    text = call_resp.json()["result"]["content"][0]["text"]
    assert "Beijing" in text
    assert call_resp.json()["result"]["isError"] is False
