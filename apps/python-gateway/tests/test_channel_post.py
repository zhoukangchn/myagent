from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def test_channel_post_accepts_valid_payload():
    payload = {
        "chat_id": "cron-demo",
        "thread_id": "thread-1",
        "message_id": "m-1",
        "role": "assistant",
        "content": "hello from cron",
        "metadata": {"source": "openclaw-cron-delivery", "account_id": "default"},
    }
    with TestClient(app) as client:
        resp = client.post("/v1/channel/post", json=payload)

    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "accepted": True, "forwarded": False}


def test_channel_post_rejects_invalid_payload():
    payload = {
        "chat_id": "",
        "thread_id": "thread-1",
        "message_id": "m-1",
        "role": "assistant",
        "content": "",
    }
    with TestClient(app) as client:
        resp = client.post("/v1/channel/post", json=payload)

    assert resp.status_code == 422
