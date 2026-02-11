#!/usr/bin/env python3
"""MCP Hub - 服务注册中心 (内存存储版)"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-hub")

# ==================== 数据模型 ====================

class ToolInfo(BaseModel):
    name: str
    description: str
    input_schema: dict = Field(default_factory=dict)

class ServiceRegistration(BaseModel):
    name: str
    version: str = "1.0.0"
    description: Optional[str] = None
    url: str
    tools: List[ToolInfo] = Field(default_factory=list)
    
class ServiceInfo(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    url: str
    tools: List[ToolInfo]
    status: str = "online"
    registered_at: datetime
    last_heartbeat: datetime

# ==================== 内存存储 ====================

SERVICE_TIMEOUT_SECONDS = 60

services: Dict[str, ServiceInfo] = {}

def register_service(registration: ServiceRegistration) -> ServiceInfo:
    """注册服务"""
    now = datetime.utcnow()
    service = ServiceInfo(
        name=registration.name,
        version=registration.version,
        description=registration.description,
        url=registration.url,
        tools=registration.tools,
        status="online",
        registered_at=now,
        last_heartbeat=now
    )
    services[registration.name] = service
    logger.info(f"✅ Service registered: {registration.name}")
    return service

def unregister_service(name: str) -> bool:
    """注销服务"""
    if name in services:
        del services[name]
        logger.info(f"❌ Service unregistered: {name}")
        return True
    return False

def get_service(name: str) -> Optional[ServiceInfo]:
    """获取服务"""
    return services.get(name)

def list_services() -> List[ServiceInfo]:
    """列出所有服务"""
    now = datetime.utcnow()
    online_services = []
    for service in services.values():
        elapsed = (now - service.last_heartbeat).total_seconds()
        if elapsed < SERVICE_TIMEOUT_SECONDS:
            service.status = "online"
            online_services.append(service)
        else:
            service.status = "offline"
    return online_services

def update_heartbeat(name: str) -> bool:
    """更新心跳"""
    if name in services:
        services[name].last_heartbeat = datetime.utcnow()
        services[name].status = "online"
        return True
    return False

def cleanup_offline():
    """清理离线服务"""
    now = datetime.utcnow()
    for name, svc in services.items():
        elapsed = (now - svc.last_heartbeat).total_seconds()
        if elapsed >= SERVICE_TIMEOUT_SECONDS:
            services[name].status = "offline"
            logger.info(f"💤 Service marked offline: {name}")

# ==================== FastAPI 应用 ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 MCP Hub starting...")
    async def cleanup_task():
        while True:
            await asyncio.sleep(30)
            cleanup_offline()
    task = asyncio.create_task(cleanup_task())
    yield
    task.cancel()
    logger.info("🛑 MCP Hub stopped")

app = FastAPI(
    title="MCP Hub",
    description="MCP Service Registry with in-memory storage",
    version="0.1.0",
    lifespan=lifespan
)

@app.post("/register", response_model=ServiceInfo)
async def register(registration: ServiceRegistration):
    return register_service(registration)

@app.delete("/services/{name}")
async def unregister(name: str):
    if not unregister_service(name):
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    return {"message": f"Service '{name}' unregistered"}

@app.get("/services", response_model=List[ServiceInfo])
async def list():
    return list_services()

@app.get("/services/{name}", response_model=ServiceInfo)
async def get(name: str):
    service = get_service(name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    elapsed = (datetime.utcnow() - service.last_heartbeat).total_seconds()
    if elapsed >= SERVICE_TIMEOUT_SECONDS:
        service.status = "offline"
    return service

@app.post("/services/{name}/heartbeat")
async def heartbeat(name: str):
    if not update_heartbeat(name):
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    return {"status": "online", "message": "Heartbeat received"}

@app.get("/health")
async def health():
    return {"status": "healthy", "services": len(services)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
