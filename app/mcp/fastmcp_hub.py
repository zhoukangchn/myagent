from __future__ import annotations

import asyncio
import json
from contextlib import AsyncExitStack

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
        self._lock = asyncio.Lock()

    async def __call__(self, scope, receive, send) -> None:
        if scope.get("type") != "http":
            await self._rpc_error(scope, receive, send, -32603, "unsupported scope")
            return

        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        server_id = headers.get("x-mcp-server-id", "").strip()
        if not server_id:
            await self._rpc_error(scope, receive, send, -32602, "x-mcp-server-id required")
            return

        try:
            app = await self._build_request_subapp(server_id)
        except Exception as exc:
            await self._rpc_error(scope, receive, send, -32050, f"failed to prepare target server: {exc}")
            return

        # `FastMCP.streamable_http_app()` serves its transport endpoint at `/mcp`.
        # This gateway is mounted under `/mcp`, so we normalize sub-app path here.
        forwarded_scope = dict(scope)
        forwarded_scope["path"] = "/mcp"
        forwarded_scope["raw_path"] = b"/mcp"
        forwarded_scope["root_path"] = ""
        await self._run_subapp_in_request_lifespan(app, forwarded_scope, receive, send)

    async def _build_request_subapp(self, server_id: str):
        server = self._app_state.registry.get(server_id)
        if server is None:
            raise HubError("target server not found", code=-32004)

        async with self._lock:
            await self._app_state.tool_catalog.refresh_server(server_id)
            return self._build_fastmcp_server_app(server_id)

    async def _rpc_error(self, scope, receive, send, code: int, message: str) -> None:
        await JSONResponse(
            {"jsonrpc": "2.0", "id": None, "error": {"code": code, "message": message}},
            status_code=200,
        )(scope, receive, send)

    def refresh_server_sync(self, server_id: str) -> None:
        """Utility for sync test code paths.

        Uses a dedicated loop when no running loop is available.
        """
        async def _refresh_catalog_only() -> None:
            server = self._app_state.registry.get(server_id)
            if server is None:
                self._app_state.tool_catalog.delete_server(server_id)
                self._app_state.session_store.delete(server_id)
                return
            await self._app_state.tool_catalog.refresh_server(server_id)

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_refresh_catalog_only())
        except RuntimeError:
            asyncio.run(_refresh_catalog_only())

    async def refresh_server(self, server_id: str) -> None:
        server = self._app_state.registry.get(server_id)
        if server is None:
            self._app_state.tool_catalog.delete_server(server_id)
            self._app_state.session_store.delete(server_id)
            return

        await self._app_state.tool_catalog.refresh_server(server_id)

    async def refresh_all(self) -> None:
        for server in self._app_state.registry.list():
            await self.refresh_server(server.id)

    async def _run_subapp_in_request_lifespan(self, app, scope, receive, send) -> None:
        stack = AsyncExitStack()
        router = getattr(app, "router", None)
        lifespan_context = getattr(router, "lifespan_context", None)
        if lifespan_context is not None:
            await stack.enter_async_context(lifespan_context(app))
        try:
            await app(scope, receive, send)
        finally:
            await stack.aclose()

    def _build_fastmcp_server_app(self, server_id: str):
        # Local import so the module can still be imported in environments
        # where `mcp` is not installed yet.
        from mcp.server.fastmcp import FastMCP

        server = self._app_state.registry.get(server_id)
        mcp = FastMCP(name=f"hub-{server.name if server else server_id}", stateless_http=True)
        entries = self._app_state.tool_catalog.list_by_server(server_id)

        for entry in entries:
            mcp.tool(name=entry.public_name, description=entry.description)(self._tool_factory(entry))

        return mcp.streamable_http_app()

    def _tool_factory(self, entry):
        input_schema = entry.input_schema if isinstance(entry.input_schema, dict) else {}
        properties = input_schema.get("properties", {})
        required = set(input_schema.get("required", []))
        arg_names = [name for name in properties.keys() if isinstance(name, str) and name.isidentifier()]

        # Build a concrete function signature from schema keys so FastMCP
        # exposes natural tool args (e.g. city) instead of a synthetic kwargs field.
        if arg_names:
            params = []
            for name in arg_names:
                if name in required:
                    params.append(name)
                else:
                    params.append(f"{name}=None")
            args_expr = ", ".join([f"'{name}': {name}" for name in arg_names])
            src = (
                f"async def _tool_proxy({', '.join(params)}):\n"
                f"    arguments = {{{args_expr}}}\n"
                "    arguments = {k: v for k, v in arguments.items() if v is not None}\n"
                f"    return await gateway._call_public_tool('{entry.public_name}', arguments)\n"
            )
            namespace = {"gateway": self}
            exec(src, namespace)
            func = namespace["_tool_proxy"]
        else:
            async def func(arguments: dict | None = None):
                return await self._call_public_tool(entry.public_name, arguments or {})

        func.__name__ = f"tool_{entry.public_name.replace('.', '_')}"
        return func

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
