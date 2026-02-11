from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from app.core.models import McpServerConfigItem, McpServersConfigResponse, ServerCreateRequest, ServerRecord


def build_servers_router(app_state) -> APIRouter:
    router = APIRouter(prefix="/api/servers", tags=["servers"])

    def _build_mcp_config(server_id: str, request: Request) -> McpServersConfigResponse:
        rec = app_state.registry.get(server_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="server not found")

        hub_mcp_url = f"{str(request.base_url).rstrip('/')}/mcp/"
        return McpServersConfigResponse(
            mcpServers={
                rec.name: McpServerConfigItem(
                    url=hub_mcp_url,
                    headers={"x-mcp-server-id": rec.id},
                )
            }
        )

    @router.post("", response_model=ServerRecord, status_code=201)
    async def create_server(payload: ServerCreateRequest) -> ServerRecord:
        try:
            rec = app_state.registry.create(
                name=payload.name,
                base_url=payload.base_url,
                mcp_endpoint=payload.mcp_endpoint,
                description=payload.description,
                tags=payload.tags,
                headers=payload.headers,
            )
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

        return rec

    @router.get("", response_model=list[ServerRecord])
    def list_servers() -> list[ServerRecord]:
        return app_state.registry.list()

    @router.get("/{server_id}", response_model=ServerRecord)
    def get_server(server_id: str) -> ServerRecord:
        rec = app_state.registry.get(server_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="server not found")
        return rec

    @router.get("/{server_id}/mcp-config", response_model=McpServersConfigResponse)
    def get_mcp_config(server_id: str, request: Request) -> McpServersConfigResponse:
        return _build_mcp_config(server_id, request)

    @router.delete("/{server_id}", status_code=204)
    async def delete_server(server_id: str) -> Response:
        if app_state.registry.get(server_id) is None:
            raise HTTPException(status_code=404, detail="server not found")
        app_state.registry.delete(server_id)
        await app_state.fastmcp_hub.refresh_server(server_id)
        return Response(status_code=204)

    return router
