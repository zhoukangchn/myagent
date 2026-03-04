from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from gateway.core.state import auth_service, bridge_service

router = APIRouter()


@router.websocket("/v1/ws/openclaw")
async def openclaw_ws(ws: WebSocket):
    if not auth_service.verify_ws_signature(ws):
        await ws.close(code=4401)
        return

    await ws.accept()
    await bridge_service.attach_openclaw(ws)

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            print(
                f"[ws] inbound type={data.get('type')} request_id={data.get('request_id')} session_key={data.get('session_key')}"
            )
            if data.get("type") == "ping":
                await ws.send_json({"type": "pong"})
                continue
            await bridge_service.dispatch_from_openclaw(data)
    except (WebSocketDisconnect, json.JSONDecodeError):
        pass
    finally:
        await bridge_service.detach_openclaw(ws)
