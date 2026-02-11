from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_list_get_delete_server():
    payload = {
        "name": "s1",
        "base_url": "http://localhost:9999",
        "mcp_endpoint": "/mcp",
        "description": "demo",
        "tags": ["demo"],
        "headers": {"x-api-key": "k"},
    }

    created = client.post("/api/servers", json=payload)
    assert created.status_code == 201
    sid = created.json()["id"]

    listing = client.get("/api/servers")
    assert listing.status_code == 200
    assert any(it["id"] == sid for it in listing.json())

    fetched = client.get(f"/api/servers/{sid}")
    assert fetched.status_code == 200
    assert fetched.json()["name"] == "s1"

    deleted = client.delete(f"/api/servers/{sid}")
    assert deleted.status_code == 204

    missing = client.get(f"/api/servers/{sid}")
    assert missing.status_code == 404


def test_get_mcp_config_by_server_id():
    payload = {
        "name": "weather-downstream",
        "base_url": "http://localhost:9999",
        "mcp_endpoint": "/mcp",
        "description": "demo",
        "tags": ["demo"],
        "headers": {"Authorization": "secret-token"},
    }

    created = client.post("/api/servers", json=payload)
    assert created.status_code == 201
    server = created.json()

    resp = client.get(f"/api/servers/{server['id']}/mcp-config")
    assert resp.status_code == 200
    data = resp.json()

    assert "mcpServers" in data
    assert list(data["mcpServers"].keys()) == [server["name"]]
    cfg = data["mcpServers"][server["name"]]
    assert cfg["url"] == "http://testserver/mcp/"
    assert cfg["headers"] == {"x-mcp-server-id": server["id"]}
    assert "Authorization" not in cfg["headers"]


def test_get_mcp_config_404_for_unknown_server():
    resp = client.get("/api/servers/not-found/mcp-config")
    assert resp.status_code == 404


def test_mcp_config_json_download_endpoint_not_found():
    resp = client.get("/api/servers/not-found/mcp-config.json")
    assert resp.status_code == 404
