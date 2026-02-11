#!/usr/bin/env python3
"""
示例 MCP Hub Client
展示如何从 Hub 发现服务并调用
"""
import argparse
import asyncio
from typing import Any

import httpx
from rich.console import Console
from rich.table import Table

console = Console()


class HubClient:
    """Client for MCP Hub."""
    
    def __init__(self, hub_url: str):
        self.hub_url = hub_url.rstrip("/")
        self.client = httpx.AsyncClient()
    
    async def close(self):
        await self.client.aclose()
    
    async def list_services(self) -> list[dict]:
        """List all registered services."""
        response = await self.client.get(f"{self.hub_url}/api/v1/services")
        response.raise_for_status()
        data = response.json()
        return data.get("services", [])
    
    async def get_service(self, name: str) -> dict:
        """Get a specific service."""
        response = await self.client.get(f"{self.hub_url}/api/v1/services/{name}")
        response.raise_for_status()
        return response.json()
    
    async def call_tool(self, service: str, tool: str, arguments: dict) -> dict:
        """Call a tool through Hub proxy."""
        response = await self.client.post(
            f"{self.hub_url}/api/v1/call/{service}/tool",
            json={"tool": tool, "arguments": arguments},
        )
        response.raise_for_status()
        return response.json()


async def show_services(client: HubClient):
    """Display all services in a table."""
    services = await client.list_services()
    
    if not services:
        console.print("[yellow]No services registered[/yellow]")
        return
    
    table = Table(title="Registered MCP Services")
    table.add_column("Name", style="cyan")
    table.add_column("Version", style="magenta")
    table.add_column("Status", style="green")
    table.add_column("Transport", style="blue")
    table.add_column("Endpoint")
    table.add_column("Tools")
    
    for svc in services:
        tools = ", ".join([t["name"] for t in svc.get("tools", [])])
        status_color = {
            "online": "green",
            "offline": "red",
            "unhealthy": "yellow",
        }.get(svc.get("status"), "white")
        
        table.add_row(
            svc["name"],
            svc["version"],
            f"[{status_color}]{svc['status']}[/{status_color}]",
            svc["transport"],
            svc["endpoint"],
            tools or "-",
        )
    
    console.print(table)


async def demo_weather_service(client: HubClient):
    """Demo: Call weather service through Hub."""
    console.print("\n[bold blue]🌤️  Demo: Weather Service[/bold blue]\n")
    
    # Check if weather-server is registered
    try:
        service = await client.get_service("weather-server")
        console.print(f"✅ Found service: {service['name']} ({service['version']})")
        console.print(f"   Endpoint: {service['endpoint']}")
        console.print(f"   Status: {service['status']}")
        console.print()
    except Exception:
        console.print("[red]❌ weather-server not found in Hub[/red]")
        console.print("   Please start the weather-server example first")
        return
    
    # Call get_weather tool
    console.print("[bold]Calling get_weather tool...[/bold]")
    try:
        result = await client.call_tool(
            service="weather-server",
            tool="get_weather",
            arguments={"city": "上海", "days": 3},
        )
        
        if result.get("success"):
            console.print(f"[green]✅ Result:[/green] {result['result'][0]['text']}")
        else:
            console.print(f"[red]❌ Error:[/red] {result.get('error')}")
    except Exception as e:
        console.print(f"[red]❌ Failed to call tool:[/red] {e}")


async def main():
    parser = argparse.ArgumentParser(description="MCP Hub Client Demo")
    parser.add_argument(
        "--hub",
        default="http://localhost:8000",
        help="MCP Hub URL",
    )
    args = parser.parse_args()
    
    client = HubClient(args.hub)
    
    try:
        console.print(f"[bold]🔌 Connected to MCP Hub:[/bold] {args.hub}\n")
        
        # Show all services
        await show_services(client)
        
        # Demo calling weather service
        await demo_weather_service(client)
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
