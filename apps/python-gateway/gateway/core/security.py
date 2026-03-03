from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass


@dataclass
class NonceStore:
    ttl_sec: int

    def __post_init__(self) -> None:
        self._seen: dict[str, int] = {}

    def check_and_store(self, key: str) -> bool:
        now = int(time.time())
        expired = [nonce for nonce, seen_ts in self._seen.items() if now - seen_ts > self.ttl_sec]
        for nonce in expired:
            self._seen.pop(nonce, None)
        if key in self._seen:
            return False
        self._seen[key] = now
        return True


def build_signature_payload(method: str, path: str, timestamp: str, nonce: str, body: bytes) -> bytes:
    body_hash = hashlib.sha256(body).hexdigest()
    raw = "\n".join([method.upper(), path, timestamp, nonce, body_hash])
    return raw.encode("utf-8")


def verify_signature(secret: str, payload: bytes, signature: str) -> bool:
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def timestamp_is_fresh(timestamp: str, ttl_sec: int) -> bool:
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    now = int(time.time())
    return abs(now - ts) <= ttl_sec
