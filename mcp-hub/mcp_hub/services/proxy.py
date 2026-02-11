"""Service proxy for calling remote MCP services."""
import asyncio
from typing import Any, Optional

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client

from mcp_hub.models import ServiceInfo, TransportType, CallToolResponse


class ServiceProxy:
    """Proxy for calling registered MCP services."""
    
    def __init__(self, service: ServiceInfo):
        self.service = service
        self._client: Optional[ClientSession] = None
        self._exit_stack = None
    
    async def __aenter__(self):
        """Connect to the service."""
        from contextlib import AsyncExitStack
        
        self._exit_stack = AsyncExitStack()
        
        if self.service.transport == TransportType.STDIO:
            # For stdio, we need command info from metadata
            command = self.service.metadata.get("command", "python")
            args = self.service.metadata.get("args", [])
            
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=None,
            )
            
            stdio_transport = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read_stream, write_stream = stdio_transport
            
        elif self.service.transport == TransportType.SSE:
            sse_transport = await self._exit_stack.enter_async_context(
                sse_client(self.service.endpoint)
            )
            read_stream, write_stream = sse_transport
        else:
            raise ValueError(f"Unknown transport: {self.service.transport}")
        
        self._client = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        
        await self._client.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Disconnect from the service."""
        if self._exit_stack:
            await self._exit_stack.aclose()
    
    async def call_tool(self, tool: str, arguments: dict[str, Any]) -> CallToolResponse:
        """Call a tool on the remote service."""
        try:
            result = await self._client.call_tool(tool, arguments)
            return CallToolResponse(
                success=True,
                result=[{"type": c.type, "text": c.text} for c in result.content],
            )
        except Exception as e:
            return CallToolResponse(success=False, error=str(e))
    
    async def read_resource(self, uri: str) -> CallToolResponse:
        """Read a resource from the remote service."""
        try:
            result = await self._client.read_resource(uri)
            return CallToolResponse(
                success=True,
                result=[{"uri": c.uri, "text": c.text} for c in result.contents],
            )
        except Exception as e:
            return CallToolResponse(success=False, error=str(e))
    
    async def get_prompt(self, name: str, arguments: Optional[dict] = None) -> CallToolResponse:
        """Get a prompt from the remote service."""
        try:
            result = await self._client.get_prompt(name, arguments)
            return CallToolResponse(
                success=True,
                result=[
                    {"role": m.role, "text": m.content.text}
                    for m in result.messages
                ],
            )
        except Exception as e:
            return CallToolResponse(success=False, error=str(e))


class HealthChecker:
    """Health checker for services."""
    
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
    
    async def check(self, service: ServiceInfo) -> bool:
        """Check if service is healthy."""
        if service.transport == TransportType.SSE:
            return await self._check_sse(service.endpoint)
        elif service.transport == TransportType.STDIO:
            # For stdio, we can't easily check health without starting the process
            # Assume healthy if it was registered recently
            return True
        return False
    
    async def _check_sse(self, endpoint: str) -> bool:
        """Check SSE endpoint health."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    endpoint,
                    timeout=self.timeout,
                    headers={"Accept": "text/event-stream"},
                )
                return response.status_code == 200
        except Exception:
            return False
