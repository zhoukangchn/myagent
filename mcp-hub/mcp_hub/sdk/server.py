"""MCP Hub SDK for easy server registration."""
import asyncio
import atexit
from contextlib import AsyncExitStack
from typing import Any, Callable, Optional

import httpx
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent
from starlette.applications import Starlette
from starlette.routing import Route
import uvicorn


class HubServer:
    """MCP Server with automatic Hub registration."""
    
    def __init__(
        self,
        name: str,
        hub_url: str = "http://localhost:8000",
        version: str = "1.0.0",
        description: str = "",
        tags: Optional[list[str]] = None,
    ):
        self.name = name
        self.hub_url = hub_url.rstrip("/")
        self.version = version
        self.description = description
        self.tags = tags or []
        
        self._app = Server(name)
        self._tools: list[dict] = []
        self._resources: list[dict] = []
        self._resource_templates: list[dict] = []
        self._prompts: list[dict] = []
        
        # Register handlers
        self._app.list_tools()(self._handle_list_tools)
        self._app.call_tool()(self._handle_call_tool)
        self._app.list_resources()(self._handle_list_resources)
        self._app.read_resource()(self._handle_read_resource)
        self._app.list_resource_templates()(self._handle_list_resource_templates)
        self._app.list_prompts()(self._handle_list_prompts)
        self._app.get_prompt()(self._handle_get_prompt)
        
        self._tool_handlers: dict[str, Callable] = {}
        self._resource_handlers: dict[str, Callable] = {}
        self._prompt_handlers: dict[str, Callable] = {}
    
    def register_tool(
        self,
        name: str,
        handler: Callable[[dict], Any],
        description: str,
        input_schema: Optional[dict] = None,
    ) -> "HubServer":
        """Register a tool."""
        self._tool_handlers[name] = handler
        self._tools.append({
            "name": name,
            "description": description,
            "input_schema": input_schema or {"type": "object"},
        })
        return self
    
    def register_resource(
        self,
        uri: str,
        handler: Callable[[], str],
        name: str = "",
        mime_type: Optional[str] = None,
        description: str = "",
    ) -> "HubServer":
        """Register a static resource."""
        self._resource_handlers[uri] = handler
        self._resources.append({
            "uri": uri,
            "name": name or uri,
            "mime_type": mime_type,
            "description": description,
        })
        return self
    
    def register_resource_template(
        self,
        uri_template: str,
        handler: Callable[[str, dict], str],
        name: str = "",
        mime_type: Optional[str] = None,
        description: str = "",
    ) -> "HubServer":
        """Register a resource template."""
        import re
        # Convert template to regex for matching
        pattern = re.sub(r'\{(\w+)\}', r'(?P<\1>[^/]+)', uri_template)
        self._resource_handlers[f"__template_{uri_template}"] = (handler, pattern)
        self._resource_templates.append({
            "uri_template": uri_template,
            "name": name or uri_template,
            "mime_type": mime_type,
            "description": description,
        })
        return self
    
    def register_prompt(
        self,
        name: str,
        handler: Callable[[Optional[dict]], str],
        description: str,
        arguments: Optional[list[dict]] = None,
    ) -> "HubServer":
        """Register a prompt template."""
        self._prompt_handlers[name] = handler
        self._prompts.append({
            "name": name,
            "description": description,
            "arguments": arguments or [],
        })
        return self
    
    async def _handle_list_tools(self):
        return {"tools": self._tools}
    
    async def _handle_call_tool(self, name: str, arguments: dict):
        if name not in self._tool_handlers:
            raise ValueError(f"Unknown tool: {name}")
        
        result = self._tool_handlers[name](arguments)
        
        if asyncio.iscoroutine(result):
            result = await result
        
        if isinstance(result, str):
            return [TextContent(type="text", text=result)]
        elif isinstance(result, list):
            return [TextContent(type="text", text=str(r)) for r in result]
        else:
            return [TextContent(type="text", text=str(result))]
    
    async def _handle_list_resources(self):
        return {"resources": self._resources}
    
    async def _handle_read_resource(self, uri: str):
        # Check static resources
        if uri in self._resource_handlers:
            handler = self._resource_handlers[uri]
            content = handler()
            if asyncio.iscoroutine(content):
                content = await content
            return {"contents": [{"uri": uri, "text": content}]}
        
        # Check templates
        for key, value in self._resource_handlers.items():
            if key.startswith("__template_"):
                handler, pattern = value
                import re
                match = re.match(pattern, uri)
                if match:
                    content = handler(uri, match.groupdict())
                    if asyncio.iscoroutine(content):
                        content = await content
                    return {"contents": [{"uri": uri, "text": content}]}
        
        raise ValueError(f"Unknown resource: {uri}")
    
    async def _handle_list_resource_templates(self):
        return {"resourceTemplates": self._resource_templates}
    
    async def _handle_list_prompts(self):
        return {"prompts": self._prompts}
    
    async def _handle_get_prompt(self, name: str, arguments: Optional[dict] = None):
        if name not in self._prompt_handlers:
            raise ValueError(f"Unknown prompt: {name}")
        
        content = self._prompt_handlers[name](arguments or {})
        if asyncio.iscoroutine(content):
            content = await content
        
        return {
            "description": f"Prompt: {name}",
            "messages": [{"role": "user", "content": {"type": "text", "text": content}}],
        }
    
    async def _register_with_hub(self, endpoint: str):
        """Register with MCP Hub."""
        async with httpx.AsyncClient() as client:
            registration = {
                "name": self.name,
                "version": self.version,
                "description": self.description,
                "transport": "sse",
                "endpoint": endpoint,
                "tools": self._tools,
                "resources": self._resources,
                "resource_templates": self._resource_templates,
                "prompts": self._prompts,
                "tags": self.tags,
            }
            
            try:
                response = await client.post(
                    f"{self.hub_url}/api/v1/register",
                    json=registration,
                    timeout=10.0,
                )
                response.raise_for_status()
                print(f"✅ Registered with Hub: {self.hub_url}")
                return True
            except Exception as e:
                print(f"⚠️ Failed to register with Hub: {e}")
                return False
    
    async def _send_heartbeat(self):
        """Send periodic heartbeat to Hub."""
        while True:
            await asyncio.sleep(30)
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{self.hub_url}/api/v1/services/{self.name}/heartbeat",
                        timeout=5.0,
                    )
            except Exception:
                pass
    
    async def run(self, port: int = 0, host: str = "0.0.0.0"):
        """Run the server with SSE transport and register with Hub."""
        sse = SseServerTransport("/message")
        
        async def handle_sse(request):
            async with sse.connect_session(
                request.scope, request.receive, request.send
            ) as (read_stream, write_stream):
                await self._app.run(
                    read_stream,
                    write_stream,
                    self._app.create_initialization_options(),
                )
        
        async def handle_message(request):
            await sse.handle_post_message(request.scope, request.receive, request.send)
        
        # Use port 0 to let OS assign available port
        config = uvicorn.Config(
            Starlette(routes=[
                Route("/sse", endpoint=handle_sse),
                Route("/message", endpoint=handle_message, methods=["POST"]),
            ]),
            host=host,
            port=port,
            log_level="info",
        )
        server = uvicorn.Server(config)
        
        # Get actual port if 0 was used
        await server.startup()
        actual_port = server.config.port
        endpoint = f"http://localhost:{actual_port}/sse"
        
        print(f"🚀 {self.name} running on {endpoint}")
        
        # Register with Hub
        await self._register_with_hub(endpoint)
        
        # Start heartbeat
        heartbeat_task = asyncio.create_task(self._send_heartbeat())
        
        try:
            await server.serve()
        finally:
            heartbeat_task.cancel()
    
    def run_sync(self, port: int = 0, host: str = "0.0.0.0"):
        """Synchronous entry point."""
        asyncio.run(self.run(port, host))
