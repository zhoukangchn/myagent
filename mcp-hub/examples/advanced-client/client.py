#!/usr/bin/env python3
"""高级 MCP Client 示例 - 展示服务缓存、负载均衡、并行调用."""
import asyncio
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from mcp_hub.sdk import HubClient

console = Console()


class AdvancedClient:
    """高级 MCP Client."""
    
    def __init__(self, hub_url: str = "http://localhost:8000"):
        self.client = HubClient(hub_url, cache_ttl=60)
    
    async def close(self):
        await self.client.close()
    
    async def demo_service_discovery(self):
        """演示服务发现."""
        console.print(Panel.fit("🔍 服务发现演示", style="bold blue"))
        
        # 按标签发现
        console.print("\n[bold]按标签 'math' 发现服务:[/bold]")
        math_services = await self.client.discover(tags=["math"])
        for svc in math_services:
            console.print(f"  ✅ {svc.name}: {', '.join(svc.tools)}")
        
        # 按工具发现
        console.print("\n[bold]按工具 'get_weather' 发现服务:[/bold]")
        weather_services = await self.client.discover(tools=["get_weather"])
        for svc in weather_services:
            console.print(f"  ✅ {svc.name}: {svc.endpoint}")
        
        # 列出所有在线服务
        console.print("\n[bold]所有在线服务:[/bold]")
        services = await self.client.list_services(status="online")
        table = Table()
        table.add_column("服务名", style="cyan")
        table.add_column("版本", style="magenta")
        table.add_column("工具数", style="green")
        table.add_column("标签", style="blue")
        
        for svc in services:
            table.add_row(
                svc["name"],
                svc["version"],
                str(len(svc.get("tools", []))),
                ", ".join(svc.get("tags", []))
            )
        console.print(table)
    
    async def demo_auto_routing(self):
        """演示自动路由调用."""
        console.print(Panel.fit("🎯 自动路由调用演示", style="bold green"))
        
        # 调用 calculate 工具 (Hub 自动找到 calc-server)
        try:
            console.print("\n[bold]调用 calculate 工具 (自动路由到 calc-server):[/bold]")
            result = await self.client.call(
                tool="calculate",
                arguments={"operation": "multiply", "a": 42, "b": 100},
            )
            console.print(f"  ✅ 结果: {result[0]['text']}")
        except Exception as e:
            console.print(f"  ❌ 错误: {e}")
        
        # 调用 get_weather 工具
        try:
            console.print("\n[bold]调用 get_weather 工具 (自动路由到 weather-server):[/bold]")
            result = await self.client.call(
                tool="get_weather",
                arguments={"city": "北京", "days": 3},
            )
            console.print(f"  ✅ 结果: {result[0]['text']}")
        except Exception as e:
            console.print(f"  ❌ 错误: {e}")
    
    async def demo_parallel_calls(self):
        """演示并行调用多个服务."""
        console.print(Panel.fit("⚡ 并行调用演示", style="bold yellow"))
        
        async def call_weather(city: str) -> str:
            try:
                result = await self.client.call(
                    tool="get_weather",
                    arguments={"city": city, "days": 1},
                )
                return result[0]['text']
            except Exception as e:
                return f"错误: {e}"
        
        async def call_time(tz: str) -> str:
            try:
                # 直接调用 time-server
                result = await self.client.call_tool(
                    service="time-server",
                    tool="get_time",
                    arguments={"timezone": tz},
                )
                return result[0]['text']
            except Exception as e:
                return f"错误: {e}"
        
        async def call_calc() -> str:
            try:
                result = await self.client.call(
                    tool="advanced_math",
                    arguments={"function": "sqrt", "value": 144},
                )
                return result[0]['text']
            except Exception as e:
                return f"错误: {e}"
        
        # 并行执行所有调用
        console.print("\n[bold]并行调用 weather + time + calc:[/bold]")
        results = await asyncio.gather(
            call_weather("上海"),
            call_weather("东京"),
            call_time("Asia/Shanghai"),
            call_calc(),
        )
        
        for i, result in enumerate(results, 1):
            console.print(f"  {i}. {result}")
    
    async def demo_proxy_vs_direct(self):
        """演示代理调用 vs 直接连接."""
        console.print(Panel.fit("🔗 代理 vs 直接连接演示", style="bold magenta"))
        
        # 通过 Hub 代理调用
        console.print("\n[bold]通过 Hub 代理调用:[/bold]")
        try:
            import time
            start = time.time()
            result = await self.client.call_tool_proxy(
                service="calc-server",
                tool="calculate",
                arguments={"operation": "add", "a": 10, "b": 20},
            )
            elapsed = time.time() - start
            console.print(f"  ✅ 结果: {result}")
            console.print(f"  ⏱️  耗时: {elapsed:.3f}s")
        except Exception as e:
            console.print(f"  ❌ 错误: {e}")
        
        # 直接连接调用
        console.print("\n[bold]直接连接调用 (首次建立连接):[/bold]")
        try:
            import time
            start = time.time()
            result = await self.client.call_tool(
                service="calc-server",
                tool="calculate",
                arguments={"operation": "add", "a": 10, "b": 20},
            )
            elapsed = time.time() - start
            console.print(f"  ✅ 结果: {result[0]['text']}")
            console.print(f"  ⏱️  耗时: {elapsed:.3f}s (包含连接建立)")
        except Exception as e:
            console.print(f"  ❌ 错误: {e}")
        
        # 直接连接调用 (复用连接)
        console.print("\n[bold]直接连接调用 (复用连接):[/bold]")
        try:
            import time
            start = time.time()
            result = await self.client.call_tool(
                service="calc-server",
                tool="calculate",
                arguments={"operation": "multiply", "a": 5, "b": 6},
            )
            elapsed = time.time() - start
            console.print(f"  ✅ 结果: {result[0]['text']}")
            console.print(f"  ⏱️  耗时: {elapsed:.3f}s (连接已建立)")
        except Exception as e:
            console.print(f"  ❌ 错误: {e}")


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--hub", default="http://localhost:8000")
    args = parser.parse_args()
    
    client = AdvancedClient(args.hub)
    
    try:
        console.print(f"[bold]🔌 连接到 MCP Hub:[/bold] {args.hub}\n")
        
        await client.demo_service_discovery()
        console.print()
        
        await client.demo_auto_routing()
        console.print()
        
        await client.demo_parallel_calls()
        console.print()
        
        await client.demo_proxy_vs_direct()
        
    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
