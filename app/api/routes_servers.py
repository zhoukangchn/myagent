from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response

from app.core.models import ServerCreateRequest, ServerRecord


def build_servers_router(app_state) -> APIRouter:
    router = APIRouter(prefix="/api/servers", tags=["servers"])

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

        try:
            await app_state.fastmcp_hub.refresh_server(rec.id)
        except Exception:
            # Keep registration successful even if downstream is temporarily unreachable.
            pass

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

    @router.delete("/{server_id}", status_code=204)
    async def delete_server(server_id: str) -> Response:
        if app_state.registry.get(server_id) is None:
            raise HTTPException(status_code=404, detail="server not found")
        app_state.registry.delete(server_id)
        await app_state.fastmcp_hub.refresh_server(server_id)
        return Response(status_code=204)

    return router
