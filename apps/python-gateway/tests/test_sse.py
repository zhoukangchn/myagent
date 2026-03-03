from __future__ import annotations

from gateway.core.sse import encode_sse


def test_encode_sse_uses_real_newlines() -> None:
    out = encode_sse("ack", {"ok": True})
    assert out == b'event: ack\ndata: {"ok": true}\n\n'
    assert b"\\n" not in out


def test_encode_sse_preserves_utf8_json() -> None:
    out = encode_sse("delta", {"text": "你好"})
    assert out == 'event: delta\ndata: {"text": "你好"}\n\n'.encode("utf-8")
