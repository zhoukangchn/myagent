from __future__ import annotations

import argparse
import asyncio
import json

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


def load_config_from_file(config_file: str) -> dict:
    with open(config_file, "r", encoding="utf-8") as f:
        return json.load(f)


def select_tool_name(tool_names: list[str]) -> str:
    if not tool_names:
        raise RuntimeError("no tools available")

    for name in tool_names:
        if name == "get_weather" or name.endswith(".get_weather"):
            return name
    for name in tool_names:
        if name == "get_weather_forecast" or name.endswith(".get_weather_forecast"):
            return name
    return tool_names[0]


def build_call_arguments(tool_name: str, city: str) -> dict:
    if tool_name == "get_weather" or tool_name.endswith(".get_weather"):
        return {"city": city}
    if tool_name == "get_weather_forecast" or tool_name.endswith(".get_weather_forecast"):
        return {"city": city, "days": 3}
    return {}


async def run(config_file: str, city: str) -> None:
    cfg = load_config_from_file(config_file)

    mcp_servers = cfg.get("mcpServers", {})
    if not mcp_servers:
        raise RuntimeError("mcpServers config is empty")

    server_name, server_config = next(iter(mcp_servers.items()))
    endpoint = server_config["url"]
    headers = server_config.get("headers", {})

    async with httpx.AsyncClient(headers=headers) as client:
        async with streamable_http_client(endpoint, http_client=client) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                init_result = await session.initialize()
                print("Using config key:", server_name)
                print("Initialize result:", init_result)

                tools = await session.list_tools()
                tool_items = list(getattr(tools, "tools", []))
                names = [t.name for t in tool_items]

                print("Tools count:", len(names))
                for t in tool_items:
                    print(f"- {t.name}: {getattr(t, 'description', '') or ''}")

                selected = select_tool_name(names)
                arguments = build_call_arguments(selected, city)
                print("Selected tool:", selected)
                print("Call arguments:", arguments)

                result = await session.call_tool(selected, arguments)
                print("Tool result:", result)


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP Hub client via local mcpServers JSON")
    parser.add_argument("--config-file", required=True, help="Local mcpServers JSON file path")
    parser.add_argument("--city", default="Beijing", help="City for weather tools")
    args = parser.parse_args()

    asyncio.run(run(args.config_file, args.city))


if __name__ == "__main__":
    main()
