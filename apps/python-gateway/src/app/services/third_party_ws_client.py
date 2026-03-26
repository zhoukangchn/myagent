from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator, Callable
from contextlib import suppress
from typing import Any

from websockets import ConnectionClosed
from websockets.asyncio.client import connect

from app.core.config import Settings
from app.services.third_party_protocol import ProtocolError, ThirdPartyProtocolAdapter, ThirdPartyInboundRequest

logger = logging.getLogger(__name__)

GatewayEventSource = Callable[[ThirdPartyInboundRequest], AsyncIterator[dict[str, Any]]]


class ThirdPartyWsClient:
    def __init__(
        self,
        *,
        settings: Settings,
        adapter: ThirdPartyProtocolAdapter,
        event_source: GatewayEventSource,
    ) -> None:
        self._settings = settings
        self._adapter = adapter
        self._event_source = event_source
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if not self._settings.third_party_ws_enabled or not self._settings.third_party_ws_url:
            logger.info("third-party ws client disabled")
            return
        if self._task and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_forever(), name="third-party-ws-client")

    async def close(self) -> None:
        self._stop_event.set()
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run_forever(self) -> None:
        delay_ms = self._settings.third_party_ws_reconnect_min_ms
        while not self._stop_event.is_set():
            try:
                await self._run_once()
                delay_ms = self._settings.third_party_ws_reconnect_min_ms
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("third-party ws loop error: %s", exc)
            if self._stop_event.is_set():
                break
            await asyncio.sleep(delay_ms / 1000)
            delay_ms = min(delay_ms * 2, self._settings.third_party_ws_reconnect_max_ms)

    async def _run_once(self) -> None:
        extra_headers = self._build_headers()
        logger.info("connecting third-party ws url=%s", self._settings.third_party_ws_url)
        async with connect(
            self._settings.third_party_ws_url,
            additional_headers=extra_headers,
            open_timeout=self._settings.third_party_ws_connect_timeout_sec,
            ping_interval=self._settings.third_party_ws_ping_interval_sec,
            ping_timeout=self._settings.third_party_ws_ping_timeout_sec,
        ) as ws:
            logger.info("third-party ws connected")
            send_lock = asyncio.Lock()
            inflight: set[asyncio.Task[None]] = set()
            try:
                async for raw in ws:
                    task = asyncio.create_task(self._handle_message(ws, raw, send_lock), name="third-party-ws-request")
                    inflight.add(task)
                    task.add_done_callback(inflight.discard)
            finally:
                for task in inflight:
                    task.cancel()
                if inflight:
                    await asyncio.gather(*inflight, return_exceptions=True)
                logger.info("third-party ws disconnected")

    async def _handle_message(self, ws: Any, raw: Any, send_lock: asyncio.Lock) -> None:
        try:
            data = self._decode_json(raw)
            inbound = self._adapter.parse_inbound(data)
        except ProtocolError as exc:
            await self._safe_send(
                ws,
                self._adapter.build_protocol_error(
                    code=exc.code,
                    message=exc.message,
                    request_id=exc.request_id,
                ),
                send_lock,
            )
            return
        except json.JSONDecodeError:
            await self._safe_send(
                ws,
                self._adapter.build_protocol_error(
                    code="invalid_json",
                    message="message must be valid JSON",
                ),
                send_lock,
            )
            return

        async for event in self._event_source(inbound):
            await self._safe_send(ws, self._adapter.from_gateway_event(event), send_lock)

    async def _safe_send(self, ws: Any, message: dict[str, Any], send_lock: asyncio.Lock) -> None:
        try:
            async with send_lock:
                await ws.send(json.dumps(message, ensure_ascii=False))
        except ConnectionClosed:
            logger.info("third-party ws closed before send request_id=%s", message.get("request_id"))

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        raw = self._settings.third_party_ws_headers_json.strip()
        if raw:
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError("THIRD_PARTY_WS_HEADERS_JSON must be a JSON object")
            headers.update({str(k): str(v) for k, v in parsed.items()})
        if self._settings.third_party_ws_bearer_token:
            headers.setdefault("authorization", f"Bearer {self._settings.third_party_ws_bearer_token}")
        return headers

    @staticmethod
    def _decode_json(raw: Any) -> Any:
        if isinstance(raw, bytes):
            return json.loads(raw.decode("utf-8"))
        return json.loads(raw)
