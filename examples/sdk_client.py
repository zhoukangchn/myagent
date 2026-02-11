from __future__ import annotations

import argparse
import asyncio

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

MCP_PROTOCOL_VERSION = "2025-06-18"


async def run(hub_base_url: str, server_id: str, city: str, timeout_seconds: float) -> None:
    endpoint = f"{hub_base_url.rstrip('/')}/mcp/"

    headers = {
        "x-mcp-server-id": server_id,
        "accept": "application/json, text/event-stream",
        "mcp-protocol-version": MCP_PROTOCOL_VERSION,
    }
    timeout = httpx.Timeout(timeout_seconds)

    async with httpx.AsyncClient(headers=headers, timeout=timeout) as client:
        async with streamable_http_client(endpoint, http_client=client) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                tools = await session.list_tools()
                print("Tools:", tools)

                tool_name = "get_weather"
                for t in getattr(tools, "tools", []):
                    if t.name.endswith(".get_weather"):
                        tool_name = t.name
                        break

                result = await session.call_tool(tool_name, {"city": city})
                print("Weather result:", result)


def main() -> None:
    parser = argparse.ArgumentParser(description="Official MCP SDK client for MCP Hub demo")
    parser.add_argument("--hub", default="http://127.0.0.1:8000", help="Hub base URL")
    parser.add_argument("--server-id", required=True, help="Registered server_id from /api/servers")
    parser.add_argument("--city", default="Beijing", help="City for get_weather tool")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds")
    args = parser.parse_args()

    asyncio.run(run(args.hub, args.server_id, args.city, args.timeout))


if __name__ == "__main__":
    main()
