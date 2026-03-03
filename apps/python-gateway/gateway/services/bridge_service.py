from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket


class BridgeService:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._openclaw_ws: WebSocket | None = None
        self._streams: dict[str, asyncio.Queue[dict[str, Any]]] = {}

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
        return q

    async def unregister_stream(self, request_id: str) -> None:
        async with self._lock:
            self._streams.pop(request_id, None)

    async def send_to_openclaw(self, message: dict[str, Any]) -> None:
        async with self._lock:
            ws = self._openclaw_ws
        if ws is None:
            raise RuntimeError("openclaw websocket is not connected")
        await ws.send_json(message)

    async def dispatch_from_openclaw(self, message: dict[str, Any]) -> None:
        request_id = message.get("request_id")
        if not request_id:
            return
        async with self._lock:
            q = self._streams.get(str(request_id))
        if q is not None:
            await q.put(message)
