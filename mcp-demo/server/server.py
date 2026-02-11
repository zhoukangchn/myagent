#!/usr/bin/env python3
"""
MCP Demo Server - Python Implementation
Supports stdio and SSE transports
"""

import argparse
import json
import os
import platform
import random
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
    Resource,
    ResourceTemplate,
    Prompt,
    PromptArgument,
    GetPromptResult,
    PromptMessage,
)

# Initialize server
app = Server("mcp-demo-server")


# ==================== Tools Implementation ====================

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    if name == "calculate":
        return await calculate_tool(arguments)
    elif name == "get_weather":
        return await get_weather_tool(arguments)
    elif name == "list_files":
        return await list_files_tool(arguments)
    elif name == "read_file":
        return await read_file_tool(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def calculate_tool(args: dict) -> list[TextContent]:
    """Perform basic math operations."""
    operation = args.get("operation")
    a = args.get("a", 0)
    b = args.get("b", 0)
    
    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        if b == 0:
            return [TextContent(type="text", text="Error: Cannot divide by zero")]
        result = a / b
    else:
        return [TextContent(type="text", text=f"Error: Unknown operation '{operation}'")]
    
    return [TextContent(type="text", text=f"Result: {result}")]


async def get_weather_tool(args: dict) -> list[TextContent]:
    """Get weather for a city (simulated)."""
    city = args.get("city", "Unknown")
    days = args.get("days", 1)
    
    weathers = ["晴朗", "多云", "小雨", "大雨", "雪", "雾霾"]
    random_weather = random.choice(weathers)
    temp = random.randint(5, 35)
    
    return [TextContent(
        type="text",
        text=f"{city}未来{days}天天气: {random_weather}, 温度 {temp}°C"
    )]


async def list_files_tool(args: dict) -> list[TextContent]:
    """List files in a directory."""
    path = args.get("path", ".")
    
    try:
        entries = []
        for entry in Path(path).iterdir():
            stat = entry.stat()
            entries.append({
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "size": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
        
        return [TextContent(type="text", text=json.dumps(entries, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def read_file_tool(args: dict) -> list[TextContent]:
    """Read a file's content."""
    file_path = args.get("path", "")
    
    try:
        content = Path(file_path).read_text(encoding="utf-8")
        return [TextContent(type="text", text=content)]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="calculate",
            description="执行基础数学运算 (add, subtract, multiply, divide)",
            inputSchema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["add", "subtract", "multiply", "divide"],
                        "description": "要执行的数学运算",
                    },
                    "a": {"type": "number", "description": "第一个操作数"},
                    "b": {"type": "number", "description": "第二个操作数"},
                },
                "required": ["operation", "a", "b"],
            },
        ),
        Tool(
            name="get_weather",
            description="获取指定城市的天气信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名称"},
                    "days": {
                        "type": "integer",
                        "description": "预报天数 (1-7)",
                        "minimum": 1,
                        "maximum": 7,
                    },
                },
                "required": ["city"],
            },
        ),
        Tool(
            name="list_files",
            description="列出指定路径的文件和目录",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "要列出的目录路径 (默认当前目录)",
                    },
                },
            },
        ),
        Tool(
            name="read_file",
            description="读取指定文件的内容",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"},
                },
                "required": ["path"],
            },
        ),
    ]


# ==================== Resources Implementation ====================

@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource by URI."""
    if uri == "system://info":
        return json.dumps({
            "platform": platform.system(),
            "arch": platform.machine(),
            "python_version": platform.python_version(),
            "pid": os.getpid(),
        }, indent=2)
    
    # Handle user://{id}/profile
    if uri.startswith("user://") and uri.endswith("/profile"):
        user_id = uri[7:-8]  # Extract id from user://{id}/profile
        users = {
            "1": {"name": "Alice", "role": "admin", "email": "alice@example.com"},
            "2": {"name": "Bob", "role": "user", "email": "bob@example.com"},
        }
        user = users.get(user_id, {"name": f"User-{user_id}", "role": "guest", "email": "unknown"})
        return json.dumps(user, indent=2)
    
    # Handle docs://{topic}
    if uri.startswith("docs://"):
        topic = uri[7:]
        docs = {
            "mcp": "Model Context Protocol (MCP) 是一个开放协议...",
            "tools": "Tools 允许 LLM 执行操作，如计算、API 调用等...",
            "resources": "Resources 提供 LLM 可以读取的数据和上下文...",
            "prompts": "Prompts 是可复用的模板，用于标准化交互...",
        }
        return docs.get(topic, f"暂无关于 '{topic}' 的文档")
    
    raise ValueError(f"Unknown resource: {uri}")


@app.list_resources()
async def list_resources() -> list[Resource]:
    """List static resources."""
    return [
        Resource(
            uri="system://info",
            name="系统信息",
            mimeType="application/json",
            description="当前系统的运行信息",
        ),
    ]


@app.list_resource_templates()
async def list_resource_templates() -> list[ResourceTemplate]:
    """List resource templates."""
    return [
        ResourceTemplate(
            uriTemplate="user://{id}/profile",
            name="用户资料",
            mimeType="application/json",
            description="获取指定用户的资料信息",
        ),
        ResourceTemplate(
            uriTemplate="docs://{topic}",
            name="文档资源",
            mimeType="text/plain",
            description="获取指定主题的文档",
        ),
    ]


# ==================== Prompts Implementation ====================

@app.get_prompt()
async def get_prompt(name: str, arguments: dict | None = None) -> GetPromptResult:
    """Get a prompt by name."""
    arguments = arguments or {}
    
    if name == "code_review":
        code = arguments.get("code", "")
        language = arguments.get("language", "unknown")
        
        return GetPromptResult(
            description="代码审查模板",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f"""请审查以下 {language} 代码，提供改进建议：

```{language}
{code}
```

请从以下方面分析：
1. 代码质量和可读性
2. 潜在的错误或漏洞
3. 性能优化建议
4. 最佳实践遵循情况"""
                    ),
                ),
            ],
        )
    
    elif name == "explain_concept":
        concept = arguments.get("concept", "")
        level = arguments.get("level", "intermediate")
        
        level_descriptions = {
            "beginner": "用简单易懂的语言解释，适合初学者",
            "intermediate": "提供技术细节和实际例子",
            "advanced": "深入底层原理和实现细节",
        }
        
        return GetPromptResult(
            description="概念解释模板",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(
                        type="text",
                        text=f'请解释 "{concept}" 这个概念。\n\n目标受众：{level_descriptions.get(level, "intermediate")}'
                    ),
                ),
            ],
        )
    
    raise ValueError(f"Unknown prompt: {name}")


@app.list_prompts()
async def list_prompts() -> list[Prompt]:
    """List available prompts."""
    return [
        Prompt(
            name="code_review",
            description="代码审查模板",
            arguments=[
                PromptArgument(
                    name="code",
                    description="要审查的代码",
                    required=True,
                ),
                PromptArgument(
                    name="language",
                    description="编程语言",
                    required=False,
                ),
            ],
        ),
        Prompt(
            name="explain_concept",
            description="概念解释模板",
            arguments=[
                PromptArgument(
                    name="concept",
                    description="要解释的概念",
                    required=True,
                ),
                PromptArgument(
                    name="level",
                    description="解释深度 (beginner, intermediate, advanced)",
                    required=False,
                ),
            ],
        ),
    ]


# ==================== Server Startup ====================

async def run_stdio():
    """Run server with stdio transport."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


async def run_sse(port: int = 3001):
    """Run server with SSE transport."""
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
        debug=True,
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/message", endpoint=handle_message, methods=["POST"]),
        ],
    )
    
    print(f"MCP Server running on SSE at http://localhost:{port}/sse")
    uvicorn.run(starlette_app, host="0.0.0.0", port=port)


def main():
    parser = argparse.ArgumentParser(description="MCP Demo Server")
    parser.add_argument("--stdio", action="store_true", help="Use stdio transport")
    parser.add_argument("--sse", action="store_true", help="Use SSE transport")
    parser.add_argument("--port", type=int, default=3001, help="Port for SSE mode")
    
    args = parser.parse_args()
    
    if args.stdio:
        import asyncio
        asyncio.run(run_stdio())
    elif args.sse:
        import asyncio
        asyncio.run(run_sse(args.port))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
