from __future__ import annotations

from dataclasses import dataclass
from threading import RLock

from app.core.errors import McpSessionExpiredError
from app.core.registry import InMemoryRegistry
from app.core.session_store import HubSessionStore


@dataclass
class ToolCatalogEntry:
    public_name: str
    source_server_id: str
    source_server_name: str
    source_tool_name: str
    description: str
    input_schema: dict


class ToolCatalogStore:
    def __init__(self, registry: InMemoryRegistry, session_store: HubSessionStore, downstream_client) -> None:
        self._registry = registry
        self._session_store = session_store
        self._downstream_client = downstream_client
        self._lock = RLock()
        self._by_public_name: dict[str, ToolCatalogEntry] = {}
        self._by_server: dict[str, set[str]] = {}

    async def refresh_server(self, server_id: str) -> int:
        server = self._registry.get(server_id)
        if server is None:
            self.delete_server(server_id)
            return 0

        sid = self._session_store.get(server_id)
        if sid is None:
            sid = await self._downstream_client.initialize(server)
            self._session_store.set(server_id, sid)

        try:
            listed = await self._downstream_client.list_tools(server, sid)
        except McpSessionExpiredError:
            sid = await self._downstream_client.initialize(server)
            self._session_store.set(server_id, sid)
            listed = await self._downstream_client.list_tools(server, sid)
        except Exception:
            # Keep server registered even when downstream is temporarily unavailable.
            # Existing tool mappings for this server are removed to avoid stale exposure.
            self.delete_server(server_id)
            return 0

        tools = listed.get("tools", [])
        entries: list[ToolCatalogEntry] = []
        for tool in tools:
            source_name = tool.get("name", "")
            if not source_name:
                continue
            entries.append(
                ToolCatalogEntry(
                    public_name=f"{server.name}.{source_name}",
                    source_server_id=server.id,
                    source_server_name=server.name,
                    source_tool_name=source_name,
                    description=tool.get("description", ""),
                    input_schema=tool.get("inputSchema", {}),
                )
            )

        with self._lock:
            old_public = self._by_server.get(server_id, set())
            for public_name in old_public:
                self._by_public_name.pop(public_name, None)

            mapped = set()
            for entry in entries:
                self._by_public_name[entry.public_name] = entry
                mapped.add(entry.public_name)
            self._by_server[server_id] = mapped

        return len(entries)

    async def refresh_all(self) -> None:
        servers = self._registry.list()
        for srv in servers:
            await self.refresh_server(srv.id)

    def list_by_server(self, server_id: str) -> list[ToolCatalogEntry]:
        with self._lock:
            keys = sorted(self._by_server.get(server_id, set()))
            return [self._by_public_name[k] for k in keys if k in self._by_public_name]

    def list_all(self) -> list[ToolCatalogEntry]:
        with self._lock:
            return [self._by_public_name[k] for k in sorted(self._by_public_name.keys())]

    def get(self, public_name: str) -> ToolCatalogEntry | None:
        with self._lock:
            return self._by_public_name.get(public_name)

    def delete_server(self, server_id: str) -> None:
        with self._lock:
            old_public = self._by_server.pop(server_id, set())
            for public_name in old_public:
                self._by_public_name.pop(public_name, None)
