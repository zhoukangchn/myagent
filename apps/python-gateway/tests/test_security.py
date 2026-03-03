from gateway.core.security import build_signature_payload, verify_signature


def test_signature_roundtrip():
    secret = "abc123"
    payload = build_signature_payload("POST", "/v1/chat/stream", "1700000000", "nonce-1", b'{"x":1}')
    import hmac
    import hashlib

    signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    assert verify_signature(secret, payload, signature)
