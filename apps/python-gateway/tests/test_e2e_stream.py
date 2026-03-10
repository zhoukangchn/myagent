from __future__ import annotations

import json
import threading
import time

from fastapi.testclient import TestClient

from app.main import app


def test_e2e_sse_over_reverse_ws():
    ts = str(int(time.time()))
    ws_nonce = "ws-nonce-1"
    http_nonce = "http-nonce-1"

    chat_payload = {
        "chat_id": "chat-1",
        "thread_id": "t-1",
        "sender_id": "u-1",
        "message_id": "m-1",
        "text": "hello",
        "metadata": {},
    }
    body = json.dumps(chat_payload).encode("utf-8")
    ws_headers = {}
    http_headers = {
        "content-type": "application/json",
    }
    with TestClient(app) as client:
        # Keep a reverse ws connected, echoing a streaming response back to gateway.
        with client.websocket_connect("/v1/ws/openclaw", headers=ws_headers) as ws:
            def ws_worker():
                msg = ws.receive_json()
                assert msg["type"] == "user.message"
                req_id = msg["request_id"]
                ws.send_json(
                    {"type": "assistant.message_start", "request_id": req_id, "payload": {"index": 1}}
                )
                ws.send_json({"type": "assistant.delta", "request_id": req_id, "payload": {"text": "Hi"}})
                ws.send_json(
                    {"type": "assistant.message_start", "request_id": req_id, "payload": {"index": 2}}
                )
                ws.send_json(
                    {"type": "assistant.delta", "request_id": req_id, "payload": {"text": "Again"}}
                )
                ws.send_json(
                    {
                        "type": "tool.event",
                        "request_id": req_id,
                        "payload": {"tool": "search", "status": "running"},
                    }
                )
                ws.send_json(
                    {
                        "type": "assistant.done",
                        "request_id": req_id,
                        "payload": {"usage": {"input_tokens": 1, "output_tokens": 1}, "latency_ms": 5},
                    }
                )

            t = threading.Thread(target=ws_worker)
            t.start()

            resp = client.post("/v1/chat/stream", content=body, headers=http_headers)
            t.join(timeout=2)

            assert resp.status_code == 200
            assert "text/event-stream" in (resp.headers.get("content-type") or "")
            assert "event: ack" in resp.text
            assert resp.text.count("event: message_start") == 2
            assert resp.text.count("event: delta") == 2
            assert "event: tool_event" in resp.text
            assert "event: done" in resp.text
            assert resp.text.index('"index": 1') < resp.text.index('"text": "Hi"')
            assert resp.text.index('"index": 2') < resp.text.index('"text": "Again"')


def test_e2e_sse_three_message_response():
    chat_payload = {
        "chat_id": "chat-3",
        "thread_id": "t-3",
        "sender_id": "u-3",
        "message_id": "m-3",
        "text": "hello",
        "metadata": {},
    }
    body = json.dumps(chat_payload).encode("utf-8")
    http_headers = {
        "content-type": "application/json",
    }
    with TestClient(app) as client:
        with client.websocket_connect("/v1/ws/openclaw") as ws:
            def ws_worker():
                msg = ws.receive_json()
                assert msg["type"] == "user.message"
                req_id = msg["request_id"]
                ws.send_json(
                    {"type": "assistant.message_start", "request_id": req_id, "payload": {"index": 1}}
                )
                ws.send_json(
                    {"type": "assistant.delta", "request_id": req_id, "payload": {"text": "收到。"}}
                )
                ws.send_json(
                    {"type": "assistant.message_start", "request_id": req_id, "payload": {"index": 2}}
                )
                ws.send_json(
                    {"type": "assistant.delta", "request_id": req_id, "payload": {"text": "正在处理。"}}
                )
                ws.send_json(
                    {"type": "assistant.message_start", "request_id": req_id, "payload": {"index": 3}}
                )
                ws.send_json(
                    {"type": "assistant.delta", "request_id": req_id, "payload": {"text": "处理完成。"}}
                )
                ws.send_json(
                    {
                        "type": "assistant.done",
                        "request_id": req_id,
                        "payload": {"usage": {"input_tokens": 1, "output_tokens": 3}, "latency_ms": 8},
                    }
                )

            t = threading.Thread(target=ws_worker)
            t.start()

            resp = client.post("/v1/chat/stream", content=body, headers=http_headers)
            t.join(timeout=2)

            assert resp.status_code == 200
            assert resp.text.count("event: message_start") == 3
            assert resp.text.count("event: delta") == 3
            assert resp.text.index('"index": 1') < resp.text.index('"text": "收到。"')
            assert resp.text.index('"index": 2') < resp.text.index('"text": "正在处理。"')
            assert resp.text.index('"index": 3') < resp.text.index('"text": "处理完成。"')
            assert "event: done" in resp.text
