"""MCP Hub SDK for easy client service discovery."""
import asyncio
import json
from contextlib import AsyncExitStack
from typing import Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client


@dataclass
class ServiceCapability:
    """Service capability info."""
    name: str
    endpoint: str
    tools: list[str]
    resources: list[str]
    prompts: list[str]


class ServiceCache:
    """Cache for discovered services."""
    
    def __init__(self, ttl_seconds: int = 60):
        self._cache: dict[str, dict] = {}
        self._timestamp: dict[str, datetime] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
    
    def get(self, key: str) -> Optional[dict]:
        """Get cached item if not expired."""
        if key in self._cache:
            if datetime.utcnow() - self._timestamp[key] < self._ttl:
                return self._cache[key]
            else:
                del self._cache[key]
                del self._timestamp[key]
        return None
    
    def set(self, key: str, value: dict):
        """Cache an item."""
        self._cache[key] = value
        self._timestamp[key] = datetime.utcnow()
    
    def invalidate(self, key: Optional[str] = None):
        """Invalidate cache."""
        if key:
            self._cache.pop(key, None)
            self._timestamp.pop(key, None)
        else:
            self._cache.clear()
            self._timestamp.clear()


class HubClient:
    """MCP Hub client for service discovery and calling."""
    
    def __init__(
        self,
        hub_url: str = "http://localhost:8000",
        cache_ttl: int = 60,
    ):
        self.hub_url = hub_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=30.0)
        self._cache = ServiceCache(ttl_seconds=cache_ttl)
        self._connections: dict[str, ClientSession] = {}
        self._exit_stack = AsyncExitStack()
    
    async def close(self):
        """Close client and cleanup connections."""
        await self._exit_stack.aclose()
        await self._client.aclose()
    
    async def _api_get(self, path: str, use_cache: bool = True) -> dict:
        """Make GET request with caching."""
        cache_key = f"GET:{path}"
        
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached:
                return cached
        
        response = await self._client.get(f"{self.hub_url}{path}")
        response.raise_for_status()
        data = response.json()
        
        if use_cache:
            self._cache.set(cache_key, data)
        
        return data
    
    async def _api_post(self, path: str, json: dict = None) -> dict:
        """Make POST request."""
        response = await self._client.post(
            f"{self.hub_url}{path}",
            json=json,
        )
        response.raise_for_status()
        return response.json()
    
    async def list_services(
        self,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        use_cache: bool = True,
    ) -> list[dict]:
        """List all registered services."""
        params = []
        if status:
            params.append(f"status={status}")
        if tag:
            params.append(f"tag={tag}")
        
        path = "/api/v1/services"
        if params:
            path += "?" + "&".join(params)
        
        data = await self._api_get(path, use_cache=use_cache)
        return data.get("services", [])
    
    async def get_service(self, name: str, use_cache: bool = True) -> Optional[dict]:
        """Get a specific service by name."""
        try:
            return await self._api_get(f"/api/v1/services/{name}", use_cache=use_cache)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    async def discover(
        self,
        tools: Optional[list[str]] = None,
        resources: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
    ) -> list[ServiceCapability]:
        """Discover services by capability."""
        services = await self.list_services(status="online", use_cache=False)
        
        matches = []
        for svc in services:
            # Check tags
            if tags and not any(t in svc.get("tags", []) for t in tags):
                continue
            
            # Check tools
            svc_tools = {t["name"] for t in svc.get("tools", [])}
            if tools and not any(t in svc_tools for t in tools):
                continue
            
            # Check resources
            svc_resources = {r["uri"] for r in svc.get("resources", [])}
            if resources and not any(r in svc_resources for r in resources):
                continue
            
            matches.append(ServiceCapability(
                name=svc["name"],
                endpoint=svc["endpoint"],
                tools=list(svc_tools),
                resources=list(svc_resources),
                prompts=[p["name"] for p in svc.get("prompts", [])],
            ))
        
        return matches
    
    async def _get_connection(self, service_name: str) -> ClientSession:
        """Get or create connection to a service."""
        if service_name not in self._connections:
            # Get service info
            service = await self.get_service(service_name, use_cache=False)
            if not service:
                raise ValueError(f"Service not found: {service_name}")
            
            if service["transport"] != "sse":
                raise ValueError(f"Unsupported transport: {service['transport']}")
            
            # Connect via SSE
            sse_transport = await self._exit_stack.enter_async_context(
                sse_client(service["endpoint"])
            )
            read_stream, write_stream = sse_transport
            
            session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()
            
            self._connections[service_name] = session
        
        return self._connections[service_name]
    
    async def call_tool(
        self,
        service: str,
        tool: str,
        arguments: Optional[dict] = None,
    ) -> Any:
        """Call a tool on a specific service."""
        session = await self._get_connection(service)
        result = await session.call_tool(tool, arguments or {})
        return [json.loads(r.json()) for r in result.content]
    
    async def call_tool_proxy(
        self,
        service: str,
        tool: str,
        arguments: Optional[dict] = None,
    ) -> Any:
        """Call a tool through Hub proxy (no direct connection)."""
        result = await self._api_post(
            f"/api/v1/call/{service}/tool",
            {"tool": tool, "arguments": arguments or {}},
        )
        return result
    
    async def read_resource(self, service: str, uri: str) -> Any:
        """Read a resource from a specific service."""
        session = await self._get_connection(service)
        result = await session.read_resource(uri)
        return result.contents
    
    async def get_prompt(
        self,
        service: str,
        prompt: str,
        arguments: Optional[dict] = None,
    ) -> Any:
        """Get a prompt from a specific service."""
        session = await self._get_connection(service)
        result = await session.get_prompt(prompt, arguments)
        return result.messages
    
    async def call(
        self,
        tool: str,
        arguments: Optional[dict] = None,
        preferred_service: Optional[str] = None,
    ) -> Any:
        """Auto-discover service and call tool."""
        if preferred_service:
            return await self.call_tool(preferred_service, tool, arguments)
        
        # Discover services with this tool
        services = await self.discover(tools=[tool])
        
        if not services:
            raise ValueError(f"No service found with tool: {tool}")
        
        # Use first available service
        service = services[0]
        return await self.call_tool(service.name, tool, arguments)
