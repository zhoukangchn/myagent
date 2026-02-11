from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from hub.main import app, services, SERVICE_TIMEOUT_SECONDS


def setup_function() -> None:
    services.clear()


def test_register_list_get_heartbeat_unregister_flow() -> None:
    client = TestClient(app)

    response = client.post(
        "/register",
        json={"name": "calc-server", "url": "http://localhost:9000/sse", "description": "demo"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "calc-server"
    assert payload["status"] == "online"

    response = client.get("/services")
    assert response.status_code == 200
    services_payload = response.json()
    assert len(services_payload) == 1
    assert services_payload[0]["name"] == "calc-server"

    response = client.get("/services/calc-server")
    assert response.status_code == 200
    assert response.json()["url"] == "http://localhost:9000/sse"

    response = client.post("/services/calc-server/heartbeat")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

    response = client.delete("/services/calc-server")
    assert response.status_code == 200

    response = client.get("/services/calc-server")
    assert response.status_code == 404


def test_offline_marking_when_heartbeat_is_stale() -> None:
    client = TestClient(app)

    client.post(
        "/register",
        json={"name": "stale", "url": "http://localhost:9001/sse"},
    )
    services["stale"].last_heartbeat -= timedelta(seconds=SERVICE_TIMEOUT_SECONDS + 10)

    response = client.get("/services/stale")
    assert response.status_code == 200
    assert response.json()["status"] == "offline"
