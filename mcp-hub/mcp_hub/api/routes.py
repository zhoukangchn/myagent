"""FastAPI routes for MCP Hub."""
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks

from mcp_hub.models import (
    ServiceRegistration,
    ServiceInfo,
    ServiceList,
    CallToolRequest,
    CallToolResponse,
    ServiceStatus,
)
from mcp_hub.services.registry import ServiceRegistry
from mcp_hub.services.proxy import ServiceProxy


router = APIRouter(prefix="/api/v1")

# Global registry instance (set in main.py)
registry: Optional[ServiceRegistry] = None


def get_registry() -> ServiceRegistry:
    if registry is None:
        raise HTTPException(status_code=500, detail="Registry not initialized")
    return registry


@router.post("/register", response_model=ServiceInfo)
async def register_service(registration: ServiceRegistration):
    """Register a new MCP service."""
    return get_registry().register(registration)


@router.delete("/services/{name}")
async def unregister_service(name: str):
    """Unregister an MCP service."""
    success = get_registry().unregister(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    return {"message": f"Service '{name}' unregistered"}


@router.get("/services", response_model=ServiceList)
async def list_services(
    status: Optional[ServiceStatus] = None,
    tag: Optional[str] = None,
):
    """List all registered services."""
    return get_registry().list_services(status=status, tag=tag)


@router.get("/services/{name}", response_model=ServiceInfo)
async def get_service(name: str):
    """Get a specific service by name."""
    service = get_registry().get_service(name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    return service


@router.post("/services/{name}/heartbeat")
async def heartbeat(name: str):
    """Send a heartbeat for a service."""
    success = get_registry().update_heartbeat(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    return {"message": "Heartbeat received"}


@router.post("/call/{name}/tool", response_model=CallToolResponse)
async def call_tool(name: str, request: CallToolRequest):
    """Call a tool on a registered service (proxy)."""
    service = get_registry().get_service(name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    
    if service.status != ServiceStatus.ONLINE:
        raise HTTPException(
            status_code=503,
            detail=f"Service '{name}' is not online (status: {service.status})"
        )
    
    async with ServiceProxy(service) as proxy:
        return await proxy.call_tool(request.tool, request.arguments)


@router.post("/call/{name}/resource")
async def read_resource(name: str, uri: str):
    """Read a resource from a registered service (proxy)."""
    service = get_registry().get_service(name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    
    async with ServiceProxy(service) as proxy:
        return await proxy.read_resource(uri)


@router.post("/call/{name}/prompt")
async def get_prompt(name: str, prompt_name: str, arguments: Optional[dict] = None):
    """Get a prompt from a registered service (proxy)."""
    service = get_registry().get_service(name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    
    async with ServiceProxy(service) as proxy:
        return await proxy.get_prompt(prompt_name, arguments)
