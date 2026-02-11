from __future__ import annotations

import json
from typing import Any

import httpx

from app.core.errors import McpProtocolError, McpSessionExpiredError, McpTransportError
from app.core.models import ServerRecord


class DownstreamMcpClient:
    def __init__(self, timeout_seconds: float = 10.0, transport: httpx.BaseTransport | None = None) -> None:
        self._timeout = timeout_seconds
        self._transport = transport

    async def initialize(self, server: ServerRecord) -> str:
        response, headers = await self._rpc(
            server,
            "initialize",
            {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "hub", "version": "0.1.0"},
            },
        )
        session_id = headers.get("mcp-session-id") or headers.get("Mcp-Session-Id")
        if not session_id:
            raise McpProtocolError("downstream initialize did not return mcp-session-id")
        if "error" in response:
            raise McpProtocolError(response["error"].get("message", "initialize failed"))
        return session_id

    async def list_tools(self, server: ServerRecord, downstream_session_id: str) -> dict[str, Any]:
        response, _ = await self._rpc(server, "tools/list", {}, downstream_session_id)
        if "error" in response:
            raise McpProtocolError(response["error"].get("message", "tools/list failed"))
        return response.get("result", {})

    async def call_tool(
        self,
        server: ServerRecord,
        downstream_session_id: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        response, _ = await self._rpc(
            server,
            "tools/call",
            {"name": tool_name, "arguments": arguments},
            downstream_session_id,
        )
        if "error" in response:
            raise McpProtocolError(response["error"].get("message", "tools/call failed"))
        return response.get("result", {})

    async def _rpc(
        self,
        server: ServerRecord,
        method: str,
        params: dict[str, Any],
        downstream_session_id: str | None = None,
    ) -> tuple[dict[str, Any], httpx.Headers]:
        headers = {
            "content-type": "application/json",
            "accept": "application/json, text/event-stream",
            **server.headers,
        }
        if downstream_session_id:
            headers["mcp-session-id"] = downstream_session_id

        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        url = f"{server.base_url}{server.mcp_endpoint}"

        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                resp = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as exc:
            raise McpTransportError(f"downstream timeout on {method}") from exc
        except httpx.HTTPError as exc:
            raise McpTransportError(f"downstream transport error on {method}: {exc}") from exc

        if resp.status_code == 404 and downstream_session_id:
            raise McpSessionExpiredError("downstream session expired")

        if resp.status_code >= 400:
            raise McpTransportError(f"downstream returned HTTP {resp.status_code}")

        body = self._parse_response_body(resp)
        if body.get("jsonrpc") != "2.0":
            raise McpProtocolError("invalid jsonrpc response")

        return body, resp.headers

    def _parse_response_body(self, resp: httpx.Response) -> dict[str, Any]:
        content_type = (resp.headers.get("content-type") or "").lower()

        if "text/event-stream" in content_type:
            # FastMCP may return a single SSE event containing one JSON-RPC message.
            raw = resp.text
            data_lines: list[str] = []
            for line in raw.splitlines():
                if line.startswith("data:"):
                    data_lines.append(line[len("data:") :].strip())
            if not data_lines:
                raise McpProtocolError("empty SSE response from downstream")
            payload = "\n".join(data_lines)
            try:
                return json.loads(payload)
            except json.JSONDecodeError as exc:
                raise McpProtocolError(f"failed to decode downstream SSE payload: {exc}") from exc

        try:
            return resp.json()
        except json.JSONDecodeError as exc:
            raise McpProtocolError(f"failed to decode downstream JSON payload: {exc}") from exc
