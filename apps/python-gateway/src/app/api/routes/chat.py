from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.main import bridge_service, settings
from app.models.schemas import ChatStreamRequest
from app.services.chat_flow import stream_chat_request
from app.utils.sse import encode_sse

router = APIRouter()


@router.post("/v1/chat/stream")
async def chat_stream(request: Request) -> StreamingResponse:
    body = await request.body()
    payload = ChatStreamRequest.model_validate_json(body)

    async def event_iter():
        async for event in stream_chat_request(
            bridge_service,
            payload=payload,
            stream_timeout_sec=settings.stream_timeout_sec,
        ):
            msg_type = event["type"]
            request_id = str(event["request_id"])
            payload_data = event.get("payload") or {}
            if msg_type == "gateway.ack":
                yield encode_sse("ack", {"request_id": request_id, "session_key": event.get("session_key")})
                continue
            if msg_type == "assistant.delta":
                yield encode_sse("delta", {"request_id": request_id, "text": payload_data.get("text", "")})
                continue
            if msg_type == "assistant.message_start":
                yield encode_sse("message_start", {"request_id": request_id, "index": payload_data.get("index")})
                continue
            if msg_type == "assistant.done":
                yield encode_sse(
                    "done",
                    {
                        "request_id": request_id,
                        "usage": payload_data.get("usage", {}),
                        "latency_ms": payload_data.get("latency_ms"),
                    },
                )
                return
            if msg_type == "tool.event":
                yield encode_sse(
                    "tool_event",
                    {
                        "request_id": request_id,
                        "tool": payload_data.get("tool"),
                        "data": payload_data,
                    },
                )
                continue
            if msg_type == "assistant.error":
                yield encode_sse(
                    "error",
                    {
                        "request_id": request_id,
                        "code": payload_data.get("code", "upstream_error"),
                        "message": payload_data.get("message", "unknown upstream error"),
                    },
                )
                return

    return StreamingResponse(event_iter(), media_type="text/event-stream")
