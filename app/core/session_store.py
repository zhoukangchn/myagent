from __future__ import annotations

from threading import RLock


class HubSessionStore:
    """Caches downstream MCP session id per registered server."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._by_server: dict[str, str] = {}

    def get(self, server_id: str) -> str | None:
        with self._lock:
            return self._by_server.get(server_id)

    def set(self, server_id: str, downstream_session_id: str) -> None:
        with self._lock:
            self._by_server[server_id] = downstream_session_id

    def delete(self, server_id: str) -> None:
        with self._lock:
            self._by_server.pop(server_id, None)
