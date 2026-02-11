#!/usr/bin/env python3
"""MCP Server 示例 - 自动注册到 Hub"""
import argparse
import asyncio
import atexit
import logging
from datetime import datetime

import httpx
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent
from starlette.applications import Starlette
from starlette.routing import Route
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server")

# ==================== MCP 服务实现 ====================

app = Server("demo-server")

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """处理工具调用"""
    if name == "calculate":
        operation = arguments.get("operation", "add")
        a = arguments.get("a", 0)
        b = arguments.get("b", 0)
        
        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            result = a / b if b != 0 else float("inf")
        else:
            return [TextContent(type="text", text=f"Unknown operation: {operation}")]
        
        return [TextContent(type="text", text=f"Result: {result}")]
    
    elif name == "get_time":
        timezone = arguments.get("timezone", "UTC")
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        return [TextContent(type="text", text=f"Current time ({timezone}): {now}")]
    
    else:
        raise ValueError(f"Unknown tool: {name}")

@app.list_tools()
async def list_tools():
    """列出可用工具"""
    return [
        {
            "name": "calculate",
            "description": "基础数学计算 (add, subtract, multiply, divide)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                },
                "required": ["operation", "a", "b"]
            }
        },
        {
            "name": "get_time",
            "description": "获取当前时间",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "default": "UTC"}
                }
            }
        }
    ]

# ==================== Hub 注册 ====================

async def register_with_hub(hub_url: str, service_endpoint: str):
    """注册到 Hub"""
    async with httpx.AsyncClient() as client:
        registration = {
            "name": "demo-server",
            "version": "1.0.0",
            "description": "Demo MCP Server with calculate and get_time tools",
            "endpoint": service_endpoint,
            "tools": [
                {"name": "calculate", "description": "基础数学计算"},
                {"name": "get_time", "description": "获取当前时间"}
            ]
        }
        
        try:
            response = await client.post(f"{hub_url}/register", json=registration)
            response.raise_for_status()
            logger.info(f"✅ Registered with Hub: {hub_url}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to register: {e}")
            return False

async def send_heartbeat(hub_url: str, service_name: str):
    """发送心跳"""
    while True:
        await asyncio.sleep(30)
        try:
            async with httpx.AsyncClient() as client:
                await client.post(f"{hub_url}/services/{service_name}/heartbeat")
        except Exception as e:
            logger.warning(f"Heartbeat failed: {e}")

async def unregister_from_hub(hub_url: str, service_name: str):
    """从 Hub 注销"""
    try:
        async with httpx.AsyncClient() as client:
            await client.delete(f"{hub_url}/services/{service_name}")
            logger.info(f"✅ Unregistered from Hub")
    except Exception as e:
        logger.error(f"❌ Failed to unregister: {e}")

# ==================== 主函数 ====================

async def main(port: int, hub_url: str):
    """运行服务"""
    sse = SseServerTransport("/message")
    
    async def handle_sse(request):
        async with sse.connect_session(
            request.scope, request.receive, request.send
        ) as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())
    
    async def handle_message(request):
        await sse.handle_post_message(request.scope, request.receive, request.send)
    
    starlette_app = Starlette(routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/message", endpoint=handle_message, methods=["POST"]),
    ])
    
    # 启动服务
    server = uvicorn.Server(uvicorn.Config(starlette_app, host="0.0.0.0", port=port))
    
    # 获取实际端口
    await server.startup()
    actual_port = server.config.port
    endpoint = f"http://localhost:{actual_port}/sse"
    
    logger.info(f"🚀 Server running on {endpoint}")
    
    # 注册到 Hub
    if await register_with_hub(hub_url, endpoint):
        # 启动心跳
        heartbeat_task = asyncio.create_task(send_heartbeat(hub_url, "demo-server"))
        
        # 注册退出处理
        atexit.register(lambda: asyncio.run(unregister_from_hub(hub_url, "demo-server")))
        
        try:
            await server.serve()
        finally:
            heartbeat_task.cancel()
            await unregister_from_hub(hub_url, "demo-server")
    else:
        logger.warning("Running without Hub registration")
        await server.serve()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--hub", default="http://localhost:8000")
    args = parser.parse_args()
    
    asyncio.run(main(args.port, args.hub))
