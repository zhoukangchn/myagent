from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator
from uuid import uuid4

from app.models.schemas import BridgeMessage, ChatStreamRequest
from app.services.bridge import BridgeService

logger = logging.getLogger(__name__)

TERMINAL_TYPES = {"assistant.done", "assistant.error"}


def build_session_key(payload: ChatStreamRequest) -> str:
    return f"{payload.chat_id}:{payload.thread_id}"


def build_gateway_ack(request_id: str, session_key: str) -> dict[str, Any]:
    return {
        "type": "gateway.ack",
        "request_id": request_id,
        "session_key": session_key,
        "payload": {"request_id": request_id, "session_key": session_key},
    }


def build_assistant_error(
    request_id: str,
    session_key: str,
    code: str,
    message: str,
) -> dict[str, Any]:
    return {
        "type": "assistant.error",
        "request_id": request_id,
        "session_key": session_key,
        "payload": {"code": code, "message": message},
    }


async def stream_chat_request(
    bridge_service: BridgeService,
    *,
    payload: ChatStreamRequest,
    stream_timeout_sec: int,
    request_id: str | None = None,
    session_key: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    request_id = request_id or str(uuid4())
    session_key = session_key or build_session_key(payload)
    logger.info("stream start request_id=%s session_key=%s", request_id, session_key)

    yield build_gateway_ack(request_id, session_key)

    acquired = await bridge_service.try_acquire_session(session_key, request_id)
    if not acquired:
        yield build_assistant_error(
            request_id,
            session_key,
            "session_busy",
            "previous request is still running for this session",
        )
        return

    is_connected = await bridge_service.is_openclaw_connected()
    if not is_connected:
        yield build_assistant_error(
            request_id,
            session_key,
            "upstream_unavailable",
            "OpenClaw websocket is not connected",
        )
        await bridge_service.release_session(session_key, request_id)
        return

    q = await bridge_service.register_stream(request_id)
    emitted_output = False
    try:
        outgoing = {
            "type": "user.message",
            "request_id": request_id,
            "session_key": session_key,
            "seq": 1,
            "payload": payload.model_dump(),
        }
        logger.info("send_to_openclaw request_id=%s msg=%s", request_id, json.dumps(outgoing, ensure_ascii=False))
        try:
            await bridge_service.send_to_openclaw(outgoing)
        except RuntimeError:
            yield build_assistant_error(
                request_id,
                session_key,
                "upstream_unavailable",
                "OpenClaw websocket is not connected",
            )
            return

        while True:
            try:
                msg = await asyncio.wait_for(q.get(), timeout=stream_timeout_sec)
            except TimeoutError:
                yield build_assistant_error(
                    request_id,
                    session_key,
                    "upstream_timeout",
                    "OpenClaw did not respond in time",
                )
                return

            bridge_msg = BridgeMessage.model_validate(msg)
            msg_type = bridge_msg.type
            raw_payload = json.dumps(bridge_msg.payload, ensure_ascii=False)
            payload_preview = raw_payload if len(raw_payload) <= 300 else raw_payload[:300] + "...(truncated)"
            logger.info("stream recv request_id=%s msg_type=%s payload=%s", request_id, msg_type, payload_preview)

            if msg_type == "assistant.delta" and bridge_msg.payload.get("text"):
                emitted_output = True

            if msg_type == "assistant.error" and bridge_msg.payload.get("code") == "upstream_empty" and emitted_output:
                yield {
                    "type": "assistant.done",
                    "request_id": request_id,
                    "session_key": session_key,
                    "payload": {"usage": {}, "latency_ms": None},
                }
                return

            event = bridge_msg.model_dump()
            if not event.get("session_key"):
                event["session_key"] = session_key
            yield event

            if msg_type in TERMINAL_TYPES:
                return
    finally:
        await bridge_service.unregister_stream(request_id)
        await bridge_service.release_session(session_key, request_id)
