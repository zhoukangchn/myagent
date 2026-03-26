from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.core.config import get_settings
from app.services.bridge import BridgeService
from app.services.chat_flow import stream_chat_request
from app.services.third_party_protocol import ThirdPartyProtocolAdapter
from app.services.third_party_ws_client import ThirdPartyWsClient

settings = get_settings()
bridge_service = BridgeService()
third_party_ws_client = ThirdPartyWsClient(
    settings=settings,
    adapter=ThirdPartyProtocolAdapter(),
    event_source=lambda inbound: stream_chat_request(
        bridge_service,
        payload=inbound.payload,
        stream_timeout_sec=settings.stream_timeout_sec,
        request_id=inbound.request_id,
        session_key=inbound.session_key,
    ),
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await third_party_ws_client.start()
    try:
        yield
    finally:
        await third_party_ws_client.close()


def create_app() -> FastAPI:
    from app.api.routes.channel import router as channel_router
    from app.api.routes.chat import router as chat_router
    from app.api.routes.health import router as health_router
    from app.api.routes.ws import router as ws_router

    app = FastAPI(title="Python Chat SSE Gateway", version="0.1.0", lifespan=lifespan)
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(channel_router)
    app.include_router(ws_router)
    return app


app = create_app()
