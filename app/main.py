from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app.api.routes_servers import build_servers_router
from app.core.downstream_mcp_client import DownstreamMcpClient
from app.core.registry import InMemoryRegistry
from app.core.session_store import HubSessionStore
from app.core.tool_catalog import ToolCatalogStore
from app.mcp.fastmcp_hub import FastMcpHubGateway


class AppState:
    def __init__(self) -> None:
        self.registry = InMemoryRegistry()
        self.session_store = HubSessionStore()
        self.downstream_client = DownstreamMcpClient(timeout_seconds=10.0)
        self.tool_catalog = ToolCatalogStore(self.registry, self.session_store, self.downstream_client)
        self.fastmcp_hub = FastMcpHubGateway(self)


app_state = AppState()


@asynccontextmanager
async def lifespan(_: FastAPI):
    async def refresh_loop() -> None:
        while True:
            await asyncio.sleep(30)
            await app_state.fastmcp_hub.refresh_all()

    task = asyncio.create_task(refresh_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="Python MCP Hub Demo", version="0.1.0", lifespan=lifespan)

app.include_router(build_servers_router(app_state))
app.mount("/mcp", app_state.fastmcp_hub)

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "web" / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
