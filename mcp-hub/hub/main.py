#!/usr/bin/env python3
"""MCP Hub - 服务注册中心 (内存存储版)"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
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
    endpoint: str  # SSE endpoint URL
    tools: List[ToolInfo] = Field(default_factory=list)
    
class ServiceInfo(BaseModel):
    name: str
    version: str
    description: Optional[str] = None
    endpoint: str
    tools: List[ToolInfo]
    status: str = "online"  # online/offline
    registered_at: datetime
    last_heartbeat: datetime

# ==================== 内存存储 ====================

class ServiceRegistry:
    def __init__(self, heartbeat_timeout: int = 60):
        self._services: Dict[str, ServiceInfo] = {}
        self._heartbeat_timeout = heartbeat_timeout
        
    def register(self, registration: ServiceRegistration) -> ServiceInfo:
        """注册服务"""
        now = datetime.utcnow()
        service = ServiceInfo(
            name=registration.name,
            version=registration.version,
            description=registration.description,
            endpoint=registration.endpoint,
            tools=registration.tools,
            status="online",
            registered_at=now,
            last_heartbeat=now
        )
        self._services[registration.name] = service
        logger.info(f"✅ Service registered: {registration.name}")
        return service
    
    def unregister(self, name: str) -> bool:
        """注销服务"""
        if name in self._services:
            del self._services[name]
            logger.info(f"❌ Service unregistered: {name}")
            return True
        return False
    
    def get_service(self, name: str) -> Optional[ServiceInfo]:
        """获取服务"""
        return self._services.get(name)
    
    def list_services(self) -> List[ServiceInfo]:
        """列出所有在线服务"""
        now = datetime.utcnow()
        online_services = []
        for service in self._services.values():
            # 检查心跳超时
            if (now - service.last_heartbeat).seconds < self._heartbeat_timeout:
                service.status = "online"
                online_services.append(service)
            else:
                service.status = "offline"
        return online_services
    
    def update_heartbeat(self, name: str) -> bool:
        """更新心跳"""
        if name in self._services:
            self._services[name].last_heartbeat = datetime.utcnow()
            self._services[name].status = "online"
            return True
        return False
    
    def cleanup_offline(self):
        """清理离线服务"""
        now = datetime.utcnow()
        offline = [
            name for name, svc in self._services.items()
            if (now - svc.last_heartbeat).seconds >= self._heartbeat_timeout
        ]
        for name in offline:
            self._services[name].status = "offline"
            logger.info(f"💤 Service marked offline: {name}")

# ==================== FastAPI 应用 ====================

# 全局注册表
registry = ServiceRegistry()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """生命周期管理"""
    # 启动时
    logger.info("🚀 MCP Hub starting...")
    
    # 启动清理任务
    async def cleanup_task():
        while True:
            await asyncio.sleep(30)
            registry.cleanup_offline()
    
    task = asyncio.create_task(cleanup_task())
    yield
    # 关闭时
    task.cancel()
    logger.info("🛑 MCP Hub stopped")

app = FastAPI(
    title="MCP Hub",
    description="MCP Service Registry with in-memory storage",
    version="0.1.0",
    lifespan=lifespan
)

@app.post("/register", response_model=ServiceInfo)
async def register_service(registration: ServiceRegistration):
    """注册服务"""
    return registry.register(registration)

@app.delete("/services/{name}")
async def unregister_service(name: str):
    """注销服务"""
    success = registry.unregister(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    return {"message": f"Service '{name}' unregistered"}

@app.get("/services", response_model=List[ServiceInfo])
async def list_services():
    """列出所有在线服务"""
    return registry.list_services()

@app.get("/services/{name}", response_model=ServiceInfo)
async def get_service(name: str):
    """获取服务详情"""
    service = registry.get_service(name)
    if not service:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    return service

@app.post("/services/{name}/heartbeat")
async def heartbeat(name: str):
    """服务心跳"""
    success = registry.update_heartbeat(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Service '{name}' not found")
    return {"message": "Heartbeat received"}

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "services": len(registry._services)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
