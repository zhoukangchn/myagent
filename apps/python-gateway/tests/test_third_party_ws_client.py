from __future__ import annotations

import asyncio
import json

import pytest
from websockets.asyncio.server import serve

from app.core.config import Settings
from app.models.schemas import ChatStreamRequest
from app.services.third_party_protocol import ThirdPartyInboundRequest, ThirdPartyProtocolAdapter
from app.services.third_party_ws_client import ThirdPartyWsClient


@pytest.mark.asyncio
async def test_third_party_ws_client_roundtrip() -> None:
    received_messages: list[dict] = []
    response_done = asyncio.Event()

    async def event_source(inbound: ThirdPartyInboundRequest):
        assert inbound.request_id == "req-1"
        assert inbound.session_key == "chat-1:thread-1"
        assert isinstance(inbound.payload, ChatStreamRequest)
        yield {
            "type": "gateway.ack",
            "request_id": inbound.request_id,
            "session_key": inbound.session_key,
            "payload": {"request_id": inbound.request_id, "session_key": inbound.session_key},
        }
        yield {
            "type": "assistant.message_start",
            "request_id": inbound.request_id,
            "session_key": inbound.session_key,
            "payload": {"index": 1},
        }
        yield {
            "type": "assistant.delta",
            "request_id": inbound.request_id,
            "session_key": inbound.session_key,
            "payload": {"text": "hello back"},
        }
        yield {
            "type": "assistant.done",
            "request_id": inbound.request_id,
            "session_key": inbound.session_key,
            "payload": {"usage": {"input_tokens": 1}, "latency_ms": 5},
        }

    async def ws_handler(ws) -> None:
        await ws.send(
            json.dumps(
                {
                    "type": "chat.message",
                    "id": "req-1",
                    "chat_id": "chat-1",
                    "thread_id": "thread-1",
                    "sender_id": "user-1",
                    "text": "hello",
                }
            )
        )
        for _ in range(4):
            raw = await asyncio.wait_for(ws.recv(), timeout=2)
            received_messages.append(json.loads(raw))
        response_done.set()

    async with serve(ws_handler, "127.0.0.1", 0) as server:
        port = server.sockets[0].getsockname()[1]
        client = ThirdPartyWsClient(
            settings=Settings(
                THIRD_PARTY_WS_ENABLED=True,
                THIRD_PARTY_WS_URL=f"ws://127.0.0.1:{port}",
                THIRD_PARTY_WS_RECONNECT_MIN_MS=50,
                THIRD_PARTY_WS_RECONNECT_MAX_MS=100,
            ),
            adapter=ThirdPartyProtocolAdapter(),
            event_source=event_source,
        )
        await client.start()
        await asyncio.wait_for(response_done.wait(), timeout=3)
        await client.close()

    assert [msg["type"] for msg in received_messages] == [
        "chat.ack",
        "chat.reply.start",
        "chat.reply.delta",
        "chat.reply.done",
    ]
    assert received_messages[2]["payload"]["text"] == "hello back"
