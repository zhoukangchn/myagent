#!/usr/bin/env python3
"""
示例 MCP Weather Server
展示如何注册到 MCP Hub
"""
import argparse
import asyncio
import json
import random
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent

app = Server("weather-server")


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "get_weather":
        city = arguments.get("city", "Unknown")
        days = arguments.get("days", 1)
        
        weathers = ["晴朗", "多云", "小雨", "大雨", "雪"]
        weather = random.choice(weathers)
        temp = random.randint(5, 35)
        
        return [TextContent(
            type="text",
            text=f"{city}未来{days}天天气: {weather}, 温度 {temp}°C"
        )]
    
    elif name == "forecast":
        city = arguments.get("city", "Unknown")
        return [TextContent(
            type="text",
            text=f"{city}一周天气预报: 总体良好，偶有降雨"
        )]
    
    raise ValueError(f"Unknown tool: {name}")


@app.list_tools()
async def list_tools():
    return [
        {
            "name": "get_weather",
            "description": "获取指定城市的天气信息",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"},
                    "days": {"type": "integer", "minimum": 1, "maximum": 7},
                },
                "required": ["city"],
            },
        },
        {
            "name": "forecast",
            "description": "获取一周天气预报",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"},
                },
                "required": ["city"],
            },
        },
    ]


async def register_with_hub(hub_url: str, service_endpoint: str):
    """Register this server with MCP Hub."""
    async with httpx.AsyncClient() as client:
        registration = {
            "name": "weather-server",
            "version": "1.0.0",
            "description": "天气查询服务",
            "transport": "sse",
            "endpoint": service_endpoint,
            "tools": [
                {
                    "name": "get_weather",
                    "description": "获取指定城市的天气信息",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string"},
                            "days": {"type": "integer"},
                        },
                    },
                },
                {
                    "name": "forecast",
                    "description": "获取一周天气预报",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string"},
                        },
                    },
                },
            ],
            "tags": ["weather", "utility"],
        }
        
        try:
            response = await client.post(
                f"{hub_url}/api/v1/register",
                json=registration,
            )
            response.raise_for_status()
            print(f"✅ Registered with Hub: {hub_url}")
            return True
        except Exception as e:
            print(f"❌ Failed to register with Hub: {e}")
            return False


async def run_server(port: int, hub_url: str = None):
    """Run SSE server."""
    from starlette.applications import Starlette
    from starlette.routing import Route
    import uvicorn
    
    sse = SseServerTransport("/message")
    
    async def handle_sse(request):
        async with sse.connect_session(
            request.scope, request.receive, request.send
        ) as (read_stream, write_stream):
            await app.run(
                read_stream,
                write_stream,
                app.create_initialization_options(),
            )
    
    async def handle_message(request):
        await sse.handle_post_message(request.scope, request.receive, request.send)
    
    starlette_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/message", endpoint=handle_message, methods=["POST"]),
        ],
    )
    
    endpoint = f"http://localhost:{port}/sse"
    print(f"🌤️  Weather Server running on {endpoint}")
    
    # Register with Hub before starting
    if hub_url:
        await register_with_hub(hub_url, endpoint)
    
    uvicorn.run(starlette_app, host="0.0.0.0", port=port)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=3001)
    parser.add_argument("--hub", default="http://localhost:8000", help="MCP Hub URL")
    args = parser.parse_args()
    
    asyncio.run(run_server(args.port, args.hub))


if __name__ == "__main__":
    main()
