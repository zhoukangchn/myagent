#!/usr/bin/env python3
"""MCP Client 示例 - 从 Hub 发现服务并调用"""
import argparse
import asyncio
from contextlib import AsyncExitStack

import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client
from rich.console import Console
from rich.table import Table

console = Console()

class MCPHubClient:
    """MCP Hub Client"""
    
    def __init__(self, hub_url: str):
        self.hub_url = hub_url.rstrip("/")
        self._client = httpx.AsyncClient()
    
    async def close(self):
        await self._client.aclose()
    
    async def list_services(self):
        """列出所有服务"""
        response = await self._client.get(f"{self.hub_url}/services")
        response.raise_for_status()
        return response.json()
    
    async def get_service(self, name: str):
        """获取服务详情"""
        response = await self._client.get(f"{self.hub_url}/services/{name}")
        response.raise_for_status()
        return response.json()
    
    async def call_tool(self, service_name: str, tool: str, arguments: dict):
        """调用服务工具"""
        # 获取服务 endpoint
        service = await self.get_service(service_name)
        endpoint = service["endpoint"]
        
        console.print(f"\n[bold cyan]Connecting to {service_name} at {endpoint}...[/bold cyan]")
        
        # 连接到服务
        async with AsyncExitStack() as stack:
            sse = await stack.enter_async_context(sse_client(endpoint))
            read_stream, write_stream = sse
            
            session = await stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()
            
            # 调用工具
            result = await session.call_tool(tool, arguments)
            return result

async def demo_list_services(client: MCPHubClient):
    """演示：列出服务"""
    console.print("\n[bold blue]📋 Registered Services[/bold blue]\n")
    
    services = await client.list_services()
    
    if not services:
        console.print("[yellow]No services registered[/yellow]")
        return
    
    table = Table()
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Endpoint")
    table.add_column("Tools")
    
    for svc in services:
        tools = ", ".join([t["name"] for t in svc.get("tools", [])])
        table.add_row(
            svc["name"],
            svc["version"],
            svc["status"],
            svc["endpoint"],
            tools or "-"
        )
    
    console.print(table)

async def demo_call_calculate(client: MCPHubClient):
    """演示：调用 calculate 工具"""
    console.print("\n[bold green]🔧 Calling calculate tool[/bold green]\n")
    
    try:
        result = await client.call_tool(
            "demo-server",
            "calculate",
            {"operation": "multiply", "a": 42, "b": 100}
        )
        console.print(f"[green]✅ Result:[/green] {result.content[0].text}")
    except Exception as e:
        console.print(f"[red]❌ Error:[/red] {e}")

async def demo_call_get_time(client: MCPHubClient):
    """演示：调用 get_time 工具"""
    console.print("\n[bold yellow]⏰ Calling get_time tool[/bold yellow]\n")
    
    try:
        result = await client.call_tool(
            "demo-server",
            "get_time",
            {"timezone": "UTC"}
        )
        console.print(f"[green]✅ Result:[/green] {result.content[0].text}")
    except Exception as e:
        console.print(f"[red]❌ Error:[/red] {e}")

async def main():
    parser = argparse.ArgumentParser(description="MCP Hub Client Demo")
    parser.add_argument("--hub", default="http://localhost:8000", help="Hub URL")
    parser.add_argument("--action", choices=["list", "calculate", "time", "all"], 
                       default="all", help="Action to perform")
    args = parser.parse_args()
    
    client = MCPHubClient(args.hub)
    
    try:
        console.print(f"[bold]🔌 Connected to Hub:[/bold] {args.hub}\n")
        
        if args.action in ["list", "all"]:
            await demo_list_services(client)
        
        if args.action in ["calculate", "all"]:
            await demo_call_calculate(client)
        
        if args.action in ["time", "all"]:
            await demo_call_get_time(client)
            
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
