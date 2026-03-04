from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class BridgeService:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._openclaw_ws: WebSocket | None = None
        self._streams: dict[str, asyncio.Queue[dict[str, Any]]] = {}
        self._inflight_by_session: dict[str, str] = {}

    async def attach_openclaw(self, ws: WebSocket) -> None:
        async with self._lock:
            self._openclaw_ws = ws

    async def detach_openclaw(self, ws: WebSocket) -> None:
        async with self._lock:
            if self._openclaw_ws is ws:
                self._openclaw_ws = None

    async def is_openclaw_connected(self) -> bool:
        async with self._lock:
            return self._openclaw_ws is not None

    async def register_stream(self, request_id: str) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        async with self._lock:
            self._streams[request_id] = q
            logger.debug("register_stream request_id=%s total_streams=%d", request_id, len(self._streams))
        return q

    async def unregister_stream(self, request_id: str) -> None:
        async with self._lock:
            self._streams.pop(request_id, None)
            logger.debug("unregister_stream request_id=%s total_streams=%d", request_id, len(self._streams))

    async def try_acquire_session(self, session_key: str, request_id: str) -> bool:
        async with self._lock:
            current = self._inflight_by_session.get(session_key)
            if current and current != request_id:
                logger.warning(
                    "session busy session_key=%s active_request_id=%s incoming_request_id=%s",
                    session_key, current, request_id,
                )
                return False
            self._inflight_by_session[session_key] = request_id
            logger.debug("acquire session_key=%s request_id=%s", session_key, request_id)
            return True

    async def release_session(self, session_key: str, request_id: str) -> None:
        async with self._lock:
            current = self._inflight_by_session.get(session_key)
            if current == request_id:
                self._inflight_by_session.pop(session_key, None)
                logger.debug("release session_key=%s request_id=%s", session_key, request_id)

    async def send_to_openclaw(self, message: dict[str, Any]) -> None:
        async with self._lock:
            ws = self._openclaw_ws
        if ws is None:
            raise RuntimeError("openclaw websocket is not connected")
        await ws.send_json(message)

    async def dispatch_from_openclaw(self, message: dict[str, Any]) -> None:
        request_id = message.get("request_id")
        if not request_id:
            logger.warning("dispatch_from_openclaw missing request_id type=%s", message.get("type"))
            return
        async with self._lock:
            q = self._streams.get(str(request_id))
            has_stream = q is not None
        raw_json = json.dumps(message, ensure_ascii=False)
        raw_preview = raw_json if len(raw_json) <= 500 else raw_json[:500] + "...(truncated)"
        logger.info(
            "dispatch_from_openclaw request_id=%s type=%s matched_stream=%s raw=%s",
            request_id, message.get("type"), has_stream, raw_preview,
        )
        if q is not None:
            await q.put(message)
