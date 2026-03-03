from __future__ import annotations

from fastapi import HTTPException, Request, WebSocket

from gateway.core.security import NonceStore, build_signature_payload, timestamp_is_fresh, verify_signature
from gateway.deps.settings import Settings


class AuthService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._chat_nonce_store = NonceStore(ttl_sec=settings.nonce_ttl_sec)
        self._openclaw_nonce_store = NonceStore(ttl_sec=settings.nonce_ttl_sec)

    def verify_http_signature(self, request: Request, body: bytes) -> None:
        timestamp = request.headers.get("x-timestamp", "")
        nonce = request.headers.get("x-nonce", "")
        signature = request.headers.get("x-signature", "")
        client_id = request.headers.get("x-client-id", "")

        if not all([timestamp, nonce, signature, client_id]):
            raise HTTPException(status_code=401, detail="missing signature headers")
        if not timestamp_is_fresh(timestamp, self._settings.signature_ttl_sec):
            raise HTTPException(status_code=401, detail="expired timestamp")

        nonce_key = f"chat:{client_id}:{nonce}"
        if not self._chat_nonce_store.check_and_store(nonce_key):
            raise HTTPException(status_code=409, detail="replayed nonce")

        payload = build_signature_payload(request.method, request.url.path, timestamp, nonce, body)
        if not verify_signature(self._settings.chat_shared_secret, payload, signature):
            raise HTTPException(status_code=403, detail="invalid signature")

    def verify_ws_signature(self, ws: WebSocket) -> bool:
        timestamp = ws.headers.get("x-timestamp", "")
        nonce = ws.headers.get("x-nonce", "")
        signature = ws.headers.get("x-signature", "")
        openclaw_id = ws.headers.get("x-openclaw-id", "")

        if not all([timestamp, nonce, signature, openclaw_id]):
            return False
        if not timestamp_is_fresh(timestamp, self._settings.signature_ttl_sec):
            return False

        nonce_key = f"openclaw:{openclaw_id}:{nonce}"
        if not self._openclaw_nonce_store.check_and_store(nonce_key):
            return False

        payload = build_signature_payload("GET", ws.url.path, timestamp, nonce, b"")
        return verify_signature(self._settings.openclaw_shared_secret, payload, signature)
