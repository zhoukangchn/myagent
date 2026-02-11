from __future__ import annotations

from threading import RLock
from uuid import uuid4

from app.core.models import ServerRecord, utc_now_iso


class InMemoryRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._servers: dict[str, ServerRecord] = {}
        self._name_to_id: dict[str, str] = {}

    def create(
        self,
        name: str,
        base_url: str,
        mcp_endpoint: str,
        description: str,
        tags: list[str],
        headers: dict[str, str],
    ) -> ServerRecord:
        with self._lock:
            if name in self._name_to_id:
                raise ValueError(f"server name '{name}' already exists")

            now = utc_now_iso()
            server_id = str(uuid4())
            rec = ServerRecord(
                id=server_id,
                name=name,
                base_url=base_url.rstrip("/"),
                mcp_endpoint=mcp_endpoint,
                description=description,
                tags=tags,
                headers=headers,
                status="active",
                created_at=now,
                updated_at=now,
            )
            self._servers[server_id] = rec
            self._name_to_id[name] = server_id
            return rec

    def get(self, server_id: str) -> ServerRecord | None:
        with self._lock:
            return self._servers.get(server_id)

    def list(self) -> list[ServerRecord]:
        with self._lock:
            return list(self._servers.values())

    def delete(self, server_id: str) -> None:
        with self._lock:
            rec = self._servers.pop(server_id, None)
            if rec is None:
                return
            self._name_to_id.pop(rec.name, None)
