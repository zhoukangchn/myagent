from __future__ import annotations

import logging

from fastapi import FastAPI

from gateway.bridge import BridgeService
from gateway.config import get_settings

settings = get_settings()
bridge_service = BridgeService()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)


def create_app() -> FastAPI:
    from gateway.routes.chat import router as chat_router
    from gateway.routes.health import router as health_router
    from gateway.routes.ws import router as ws_router

    app = FastAPI(title="Python Chat SSE Gateway", version="0.1.0")
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(ws_router)
    return app

