from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from gateway.app import bridge_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/v1/ws/openclaw")
async def openclaw_ws(ws: WebSocket):
    await ws.accept()
    await bridge_service.attach_openclaw(ws)
    logger.info("openclaw ws connected")

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            logger.debug(
                "ws inbound type=%s request_id=%s session_key=%s",
                data.get("type"), data.get("request_id"), data.get("session_key"),
            )
            if data.get("type") == "ping":
                await ws.send_json({"type": "pong"})
                continue
            await bridge_service.dispatch_from_openclaw(data)
    except (WebSocketDisconnect, json.JSONDecodeError):
        pass
    finally:
        logger.info("openclaw ws disconnected")
        await bridge_service.detach_openclaw(ws)
