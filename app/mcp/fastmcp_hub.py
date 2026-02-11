from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable

from starlette.responses import JSONResponse

from app.core.errors import HubError, McpSessionExpiredError


class FastMcpHubGateway:
    """ASGI gateway that dispatches MCP requests to per-server FastMCP apps.

    Notes:
    - The mounted route is `/mcp`.
    - Client must provide `x-mcp-server-id` header.
    """

    def __init__(self, app_state) -> None:
        self._app_state = app_state
        self._apps_by_server: dict[str, Callable[[dict, Callable, Callable], Awaitable[None]]] = {}
        self._lock = asyncio.Lock()

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await JSONResponse({"detail": "unsupported scope"}, status_code=500)(scope, receive, send)
            return

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        server_id = headers.get("x-mcp-server-id", "").strip()
        if not server_id:
            await JSONResponse(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32602, "message": "x-mcp-server-id required"}},
                status_code=400,
            )(scope, receive, send)
            return

        app = await self._ensure_server_app(server_id)
        if app is None:
            await JSONResponse(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32004, "message": "target server not found"}},
                status_code=404,
            )(scope, receive, send)
            return

        await app(scope, receive, send)

    async def _ensure_server_app(self, server_id: str):
        existing = self._apps_by_server.get(server_id)
        if existing is not None:
            return existing

        async with self._lock:
            existing = self._apps_by_server.get(server_id)
            if existing is not None:
                return existing

            server = self._app_state.registry.get(server_id)
            if server is None:
                return None

            await self._app_state.tool_catalog.refresh_server(server_id)
            app = self._build_fastmcp_server_app(server_id)
            self._apps_by_server[server_id] = app
            return app

    def refresh_server_sync(self, server_id: str) -> None:
        """Utility for sync test code paths.

        Uses a dedicated loop when no running loop is available.
        """
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.refresh_server(server_id))
        except RuntimeError:
            asyncio.run(self.refresh_server(server_id))

    async def refresh_server(self, server_id: str) -> None:
        server = self._app_state.registry.get(server_id)
        if server is None:
            self._apps_by_server.pop(server_id, None)
            self._app_state.tool_catalog.delete_server(server_id)
            self._app_state.session_store.delete(server_id)
            return

        await self._app_state.tool_catalog.refresh_server(server_id)
        self._apps_by_server[server_id] = self._build_fastmcp_server_app(server_id)

    async def refresh_all(self) -> None:
        for server in self._app_state.registry.list():
            await self.refresh_server(server.id)

    def _build_fastmcp_server_app(self, server_id: str):
        # Local import so the module can still be imported in environments
        # where `mcp` is not installed yet.
        from mcp.server.fastmcp import FastMCP

        server = self._app_state.registry.get(server_id)
        mcp = FastMCP(name=f"hub-{server.name if server else server_id}")
        entries = self._app_state.tool_catalog.list_by_server(server_id)

        for entry in entries:
            mcp.tool(name=entry.public_name, description=entry.description)(self._tool_factory(entry.public_name))

        return mcp.streamable_http_app()

    def _tool_factory(self, public_tool_name: str):
        async def _tool_proxy(**kwargs):
            return await self._call_public_tool(public_tool_name, kwargs)

        _tool_proxy.__name__ = f"tool_{public_tool_name.replace('.', '_')}"
        return _tool_proxy

    async def _call_public_tool(self, public_tool_name: str, arguments: dict):
        entry = self._app_state.tool_catalog.get(public_tool_name)
        if entry is None:
            raise HubError(f"tool not found: {public_tool_name}", code=-32601)

        server = self._app_state.registry.get(entry.source_server_id)
        if server is None:
            raise HubError("target server not found", code=-32004)

        downstream_sid = self._app_state.session_store.get(entry.source_server_id)
        if downstream_sid is None:
            downstream_sid = await self._app_state.downstream_client.initialize(server)
            self._app_state.session_store.set(entry.source_server_id, downstream_sid)

        try:
            result = await self._app_state.downstream_client.call_tool(
                server,
                downstream_sid,
                entry.source_tool_name,
                arguments,
            )
        except McpSessionExpiredError:
            downstream_sid = await self._app_state.downstream_client.initialize(server)
            self._app_state.session_store.set(entry.source_server_id, downstream_sid)
            result = await self._app_state.downstream_client.call_tool(
                server,
                downstream_sid,
                entry.source_tool_name,
                arguments,
            )

        # Return plain dict payload; FastMCP will serialize tool result.
        return json.loads(json.dumps(result))
