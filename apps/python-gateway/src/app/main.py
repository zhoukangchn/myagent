from __future__ import annotations

import logging

from fastapi import FastAPI

from app.core.config import get_settings
from app.services.bridge import BridgeService

settings = get_settings()
bridge_service = BridgeService()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)


def create_app() -> FastAPI:
    from app.api.routes.channel import router as channel_router
    from app.api.routes.chat import router as chat_router
    from app.api.routes.health import router as health_router
    from app.api.routes.ws import router as ws_router

    app = FastAPI(title="Python Chat SSE Gateway", version="0.1.0")
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(channel_router)
    app.include_router(ws_router)
    return app


app = create_app()
