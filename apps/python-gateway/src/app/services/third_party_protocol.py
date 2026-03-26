from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.models.schemas import ChatStreamRequest


class ProtocolError(ValueError):
    def __init__(self, code: str, message: str, request_id: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.request_id = request_id


@dataclass(slots=True)
class ThirdPartyInboundRequest:
    request_id: str
    session_key: str
    payload: ChatStreamRequest


def _as_dict(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProtocolError("invalid_message", "message must be a JSON object")
    return value


def _as_non_empty_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProtocolError("invalid_message", f"missing {field}")
    return value


class ThirdPartyProtocolAdapter:
    def parse_inbound(self, raw: Any) -> ThirdPartyInboundRequest:
        data = _as_dict(raw)
        msg_type = data.get("type")
        if msg_type not in {"chat.message", "user.message"}:
            raise ProtocolError("unsupported_type", f"unsupported type: {msg_type}")

        request_id = str(data.get("request_id") or data.get("id") or uuid4())

        payload_data = data.get("payload")
        if payload_data is None:
            payload_data = data
        payload_map = _as_dict(payload_data)

        chat_id = _as_non_empty_str(payload_map.get("chat_id"), "chat_id")
        thread_id = str(payload_map.get("thread_id") or "root")
        if not thread_id.strip():
            thread_id = "root"
        sender_id = _as_non_empty_str(payload_map.get("sender_id"), "sender_id")
        text = _as_non_empty_str(payload_map.get("text"), "text")
        message_id = str(payload_map.get("message_id") or request_id)
        metadata = payload_map.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise ProtocolError("invalid_message", "metadata must be an object", request_id=request_id)

        session_key = str(data.get("session_key") or f"{chat_id}:{thread_id}")
        if not session_key.strip():
            session_key = f"{chat_id}:{thread_id}"

        payload = ChatStreamRequest(
            chat_id=chat_id,
            thread_id=thread_id,
            sender_id=sender_id,
            message_id=message_id,
            text=text,
            metadata=metadata,
        )
        return ThirdPartyInboundRequest(request_id=request_id, session_key=session_key, payload=payload)

    def build_protocol_error(
        self,
        *,
        code: str,
        message: str,
        request_id: str | None = None,
        session_key: str | None = None,
    ) -> dict[str, Any]:
        event: dict[str, Any] = {
            "type": "chat.reply.error",
            "payload": {"code": code, "message": message},
        }
        if request_id:
            event["request_id"] = request_id
        if session_key:
            event["session_key"] = session_key
        return event

    def from_gateway_event(self, event: dict[str, Any]) -> dict[str, Any]:
        request_id = str(event["request_id"])
        session_key = str(event.get("session_key") or "")
        payload = event.get("payload") or {}

        mapped: dict[str, Any]
        msg_type = event["type"]
        if msg_type == "gateway.ack":
            mapped = {"type": "chat.ack", "payload": payload}
        elif msg_type == "assistant.message_start":
            mapped = {"type": "chat.reply.start", "payload": {"index": payload.get("index")}}
        elif msg_type == "assistant.delta":
            mapped = {"type": "chat.reply.delta", "payload": {"text": payload.get("text", "")}}
        elif msg_type == "assistant.done":
            mapped = {
                "type": "chat.reply.done",
                "payload": {
                    "usage": payload.get("usage", {}),
                    "latency_ms": payload.get("latency_ms"),
                },
            }
        elif msg_type == "assistant.error":
            mapped = {
                "type": "chat.reply.error",
                "payload": {
                    "code": payload.get("code", "upstream_error"),
                    "message": payload.get("message", "unknown upstream error"),
                },
            }
        elif msg_type == "tool.event":
            mapped = {
                "type": "chat.tool",
                "payload": {
                    "tool": payload.get("tool"),
                    "data": payload,
                },
            }
        else:
            mapped = {"type": msg_type, "payload": payload}

        mapped["request_id"] = request_id
        if session_key:
            mapped["session_key"] = session_key
        return mapped
