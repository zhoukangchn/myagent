#!/usr/bin/env python3
"""
MCP Demo Client - Python Implementation
"""

import argparse
import asyncio
import json
import sys
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client


class MCPDemoClient:
    """MCP Client wrapper."""
    
    def __init__(self):
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()
    
    async def connect_stdio(self, command: str, args: list[str] = None):
        """Connect via stdio transport."""
        server_params = StdioServerParameters(
            command=command,
            args=args or [],
            env=None,
        )
        
        stdio_transport = await self.exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read_stream, write_stream = stdio_transport
        
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        
        await self.session.initialize()
        print("✅ Connected to MCP Server (stdio)")
    
    async def connect_sse(self, url: str):
        """Connect via SSE transport."""
        sse_transport = await self.exit_stack.enter_async_context(
            sse_client(url)
        )
        read_stream, write_stream = sse_transport
        
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        
        await self.session.initialize()
        print(f"✅ Connected to MCP Server (SSE: {url})")
    
    async def disconnect(self):
        """Disconnect from server."""
        await self.exit_stack.aclose()
        print("👋 Disconnected from MCP Server")
    
    # ===== Tools =====
    
    async def list_tools(self) -> list[dict]:
        """List available tools."""
        response = await self.session.list_tools()
        return [
            {
                "name": tool.name,
                "description": tool.description,
            }
            for tool in response.tools
        ]
    
    async def call_tool(self, name: str, arguments: dict) -> list[dict]:
        """Call a tool."""
        response = await self.session.call_tool(name, arguments)
        return [
            {"type": content.type, "text": content.text}
            for content in response.content
        ]
    
    # ===== Resources =====
    
    async def list_resources(self) -> tuple[list[dict], list[dict]]:
        """List available resources and templates."""
        response = await self.session.list_resources()
        templates_response = await self.session.list_resource_templates()
        
        resources = [
            {"uri": r.uri, "description": r.description}
            for r in response.resources
        ]
        templates = [
            {"uri_template": t.uriTemplate, "description": t.description}
            for t in templates_response.resourceTemplates
        ]
        
        return resources, templates
    
    async def read_resource(self, uri: str) -> str:
        """Read a resource."""
        response = await self.session.read_resource(uri)
        return response.contents[0].text if response.contents else ""
    
    # ===== Prompts =====
    
    async def list_prompts(self) -> list[dict]:
        """List available prompts."""
        response = await self.session.list_prompts()
        return [
            {"name": p.name, "description": p.description}
            for p in response.prompts
        ]
    
    async def get_prompt(self, name: str, arguments: dict | None = None) -> list[dict]:
        """Get a prompt."""
        response = await self.session.get_prompt(name, arguments)
        return [
            {"role": msg.role, "text": msg.content.text}
            for msg in response.messages
        ]


async def run_examples(client: MCPDemoClient):
    """Run demo examples."""
    print("\n🧪 运行 MCP Client 示例\n")
    print("=" * 50)
    
    # 1. 列出工具
    print("\n📦 可用工具列表:")
    tools = await client.list_tools()
    for i, tool in enumerate(tools, 1):
        print(f"  {i}. {tool['name']}: {tool['description']}")
    
    # 2. 调用 calculate 工具
    print("\n🔧 调用 calculate 工具:")
    calc_result = await client.call_tool("calculate", {
        "operation": "multiply",
        "a": 42,
        "b": 100,
    })
    print(f"  结果: {calc_result[0]['text']}")
    
    # 3. 调用 get_weather 工具
    print("\n🌤️  调用 get_weather 工具:")
    weather_result = await client.call_tool("get_weather", {
        "city": "上海",
        "days": 3,
    })
    print(f"  结果: {weather_result[0]['text']}")
    
    # 4. 列出资源
    print("\n📚 可用资源列表:")
    resources, templates = await client.list_resources()
    for i, res in enumerate(resources, 1):
        print(f"  {i}. {res['uri']}: {res['description']}")
    print("\n  资源模板:")
    for i, tpl in enumerate(templates, 1):
        print(f"  {i}. {tpl['uri_template']}: {tpl['description']}")
    
    # 5. 读取系统资源
    print("\n📖 读取 system://info:")
    system_info = await client.read_resource("system://info")
    info = json.loads(system_info)
    print(f"  平台: {info.get('platform')}")
    print(f"  架构: {info.get('arch')}")
    print(f"  Python版本: {info.get('python_version')}")
    
    # 6. 读取用户资料
    print("\n👤 读取 user://1/profile:")
    user_profile = await client.read_resource("user://1/profile")
    print(f"  内容: {user_profile}")
    
    # 7. 列出提示模板
    print("\n📝 可用提示模板:")
    prompts = await client.list_prompts()
    for i, prompt in enumerate(prompts, 1):
        print(f"  {i}. {prompt['name']}: {prompt['description']}")
    
    # 8. 获取代码审查提示
    print("\n💻 获取 code_review 提示模板:")
    code_review_prompt = await client.get_prompt("code_review", {
        "code": "function add(a, b) { return a + b; }",
        "language": "javascript",
    })
    text = code_review_prompt[0]['text']
    print(f"  提示内容预览: {text[:100]}...")
    
    # 9. 获取概念解释提示
    print("\n🎓 获取 explain_concept 提示模板:")
    explain_prompt = await client.get_prompt("explain_concept", {
        "concept": "Model Context Protocol",
        "level": "beginner",
    })
    text = explain_prompt[0]['text']
    print(f"  提示内容预览: {text[:100]}...")
    
    print("\n" + "=" * 50)
    print("✨ 所有示例运行完成!\n")


async def main():
    parser = argparse.ArgumentParser(description="MCP Demo Client")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse"],
        default="stdio",
        help="Transport type",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:3001/sse",
        help="SSE server URL",
    )
    parser.add_argument(
        "--server-path",
        default="../server/server.py",
        help="Path to server script (stdio mode)",
    )
    
    args = parser.parse_args()
    
    client = MCPDemoClient()
    
    try:
        if args.transport == "stdio":
            print("🔗 通过 stdio 连接 MCP Server...")
            await client.connect_stdio(
                command="python",
                args=[args.server_path, "--stdio"],
            )
        else:
            print(f"🔗 通过 SSE 连接 MCP Server ({args.url})...")
            await client.connect_sse(args.url)
        
        # 运行示例
        await run_examples(client)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
