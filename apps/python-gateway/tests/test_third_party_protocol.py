from __future__ import annotations

from app.services.third_party_protocol import ProtocolError, ThirdPartyProtocolAdapter


def test_parse_inbound_chat_message() -> None:
    adapter = ThirdPartyProtocolAdapter()
    inbound = adapter.parse_inbound(
        {
            "type": "chat.message",
            "id": "req-1",
            "chat_id": "chat-1",
            "thread_id": "thread-1",
            "sender_id": "user-1",
            "text": "hello",
            "metadata": {"lang": "zh"},
        }
    )

    assert inbound.request_id == "req-1"
    assert inbound.session_key == "chat-1:thread-1"
    assert inbound.payload.chat_id == "chat-1"
    assert inbound.payload.thread_id == "thread-1"
    assert inbound.payload.sender_id == "user-1"
    assert inbound.payload.text == "hello"
    assert inbound.payload.metadata == {"lang": "zh"}


def test_parse_inbound_rejects_unknown_type() -> None:
    adapter = ThirdPartyProtocolAdapter()

    try:
        adapter.parse_inbound({"type": "noop"})
    except ProtocolError as exc:
        assert exc.code == "unsupported_type"
    else:
        raise AssertionError("expected ProtocolError")


def test_from_gateway_event_maps_delta() -> None:
    adapter = ThirdPartyProtocolAdapter()
    event = adapter.from_gateway_event(
        {
            "type": "assistant.delta",
            "request_id": "req-1",
            "session_key": "chat-1:thread-1",
            "payload": {"text": "Hello"},
        }
    )

    assert event == {
        "type": "chat.reply.delta",
        "request_id": "req-1",
        "session_key": "chat-1:thread-1",
        "payload": {"text": "Hello"},
    }
