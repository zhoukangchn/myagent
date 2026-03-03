from __future__ import annotations

from fastapi import FastAPI

from gateway.api.routes.chat import router as chat_router
from gateway.api.routes.health import router as health_router
from gateway.api.routes.ws import router as ws_router


def create_app() -> FastAPI:
    app = FastAPI(title="Python Chat SSE Gateway", version="0.1.0")
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(ws_router)
    return app
