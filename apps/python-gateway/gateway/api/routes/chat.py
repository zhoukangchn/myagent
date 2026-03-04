from __future__ import annotations

import asyncio
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from gateway.core.sse import encode_sse
from gateway.core.state import auth_service, bridge_service, settings
from gateway.schemas.bridge import BridgeMessage
from gateway.schemas.chat import ChatStreamRequest

router = APIRouter()


@router.post("/v1/chat/stream")
async def chat_stream(request: Request) -> StreamingResponse:
    body = await request.body()
    auth_service.verify_http_signature(request, body)
    payload = ChatStreamRequest.model_validate_json(body)

    request_id = str(uuid4())
    session_key = f"{payload.chat_id}:{payload.thread_id}"
    print(f"[chat] stream start request_id={request_id} session_key={session_key}")

    async def event_iter():
        yield encode_sse("ack", {"request_id": request_id, "session_key": session_key})

        acquired = await bridge_service.try_acquire_session(session_key, request_id)
        if not acquired:
            yield encode_sse(
                "error",
                {
                    "request_id": request_id,
                    "code": "session_busy",
                    "message": "previous request is still running for this session",
                },
            )
            return

        is_connected = await bridge_service.is_openclaw_connected()
        if not is_connected:
            yield encode_sse("error", {"request_id": request_id, "code": "upstream_unavailable"})
            await bridge_service.release_session(session_key, request_id)
            return

        q = await bridge_service.register_stream(request_id)
        try:
            await bridge_service.send_to_openclaw(
                {
                    "type": "user.message",
                    "request_id": request_id,
                    "session_key": session_key,
                    "seq": 1,
                    "payload": payload.model_dump(),
                }
            )
            while True:
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=settings.stream_timeout_sec)
                except TimeoutError:
                    yield encode_sse(
                        "error",
                        {
                            "request_id": request_id,
                            "code": "upstream_timeout",
                            "message": "OpenClaw did not respond in time",
                        },
                    )
                    return

                bridge_msg = BridgeMessage.model_validate(msg)
                msg_type = bridge_msg.type
                print(f"[chat] stream recv request_id={request_id} msg_type={msg_type}")

                if msg_type == "assistant.delta":
                    delta = bridge_msg.payload.get("text", "")
                    yield encode_sse("delta", {"request_id": request_id, "text": delta})
                    continue

                if msg_type == "assistant.done":
                    done = {
                        "request_id": request_id,
                        "usage": bridge_msg.payload.get("usage", {}),
                        "latency_ms": bridge_msg.payload.get("latency_ms"),
                    }
                    yield encode_sse("done", done)
                    return

                if msg_type == "tool.event":
                    yield encode_sse(
                        "tool_event",
                        {
                            "request_id": request_id,
                            "tool": bridge_msg.payload.get("tool"),
                            "data": bridge_msg.payload,
                        },
                    )
                    continue

                if msg_type == "assistant.error":
                    yield encode_sse(
                        "error",
                        {
                            "request_id": request_id,
                            "code": bridge_msg.payload.get("code", "upstream_error"),
                            "message": bridge_msg.payload.get("message", "unknown upstream error"),
                        },
                    )
                    return
        finally:
            await bridge_service.unregister_stream(request_id)
            await bridge_service.release_session(session_key, request_id)

    return StreamingResponse(event_iter(), media_type="text/event-stream")
