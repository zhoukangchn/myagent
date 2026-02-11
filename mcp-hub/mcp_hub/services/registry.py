"""Service registry and discovery."""
from datetime import datetime
from typing import Optional

from mcp_hub.models import (
    ServiceRegistration,
    ServiceInfo,
    ServiceList,
    ServiceStatus,
)
from mcp_hub.models.database import Database, ServiceRecord


class ServiceRegistry:
    """Manages service registration and discovery."""
    
    def __init__(self, db: Database):
        self.db = db
    
    def register(self, registration: ServiceRegistration) -> ServiceInfo:
        """Register a new service or update existing one."""
        with self.db.get_session() as session:
            # Check if service exists
            existing = session.get(ServiceRecord, registration.name)
            
            record = ServiceRecord(
                name=registration.name,
                version=registration.version,
                description=registration.description,
                transport=registration.transport.value,
                endpoint=registration.endpoint,
                status=ServiceStatus.ONLINE.value,
                tools=[t.model_dump() for t in registration.tools],
                resources=[r.model_dump() for r in registration.resources],
                resource_templates=[rt.model_dump() for rt in registration.resource_templates],
                prompts=[p.model_dump() for p in registration.prompts],
                tags=registration.tags,
                metadata=registration.metadata,
                last_heartbeat=datetime.utcnow(),
            )
            
            if existing:
                # Update existing
                session.delete(existing)
            
            session.add(record)
            session.commit()
            
            return self._to_service_info(record)
    
    def unregister(self, name: str) -> bool:
        """Unregister a service."""
        with self.db.get_session() as session:
            record = session.get(ServiceRecord, name)
            if record:
                session.delete(record)
                session.commit()
                return True
            return False
    
    def get_service(self, name: str) -> Optional[ServiceInfo]:
        """Get service by name."""
        with self.db.get_session() as session:
            record = session.get(ServiceRecord, name)
            if record:
                return self._to_service_info(record)
            return None
    
    def list_services(
        self,
        status: Optional[ServiceStatus] = None,
        tag: Optional[str] = None,
    ) -> ServiceList:
        """List all registered services."""
        with self.db.get_session() as session:
            query = session.query(ServiceRecord)
            
            if status:
                query = query.filter(ServiceRecord.status == status.value)
            
            records = query.all()
            
            # Filter by tag in Python (SQLite JSON filtering is limited)
            if tag:
                records = [r for r in records if tag in r.tags]
            
            services = [self._to_service_info(r) for r in records]
            return ServiceList(services=services, total=len(services))
    
    def update_heartbeat(self, name: str) -> bool:
        """Update service heartbeat."""
        with self.db.get_session() as session:
            record = session.get(ServiceRecord, name)
            if record:
                record.last_heartbeat = datetime.utcnow()
                record.status = ServiceStatus.ONLINE.value
                session.commit()
                return True
            return False
    
    def update_status(self, name: str, status: ServiceStatus) -> bool:
        """Update service status."""
        with self.db.get_session() as session:
            record = session.get(ServiceRecord, name)
            if record:
                record.status = status.value
                session.commit()
                return True
            return False
    
    def _to_service_info(self, record: ServiceRecord) -> ServiceInfo:
        """Convert database record to ServiceInfo."""
        from mcp_hub.models import (
            ToolInfo, ResourceInfo, ResourceTemplateInfo, PromptInfo, TransportType
        )
        
        return ServiceInfo(
            name=record.name,
            version=record.version,
            description=record.description,
            transport=TransportType(record.transport),
            endpoint=record.endpoint,
            status=ServiceStatus(record.status),
            tools=[ToolInfo(**t) for t in record.tools],
            resources=[ResourceInfo(**r) for r in record.resources],
            resource_templates=[ResourceTemplateInfo(**rt) for rt in record.resource_templates],
            prompts=[PromptInfo(**p) for p in record.prompts],
            tags=record.tags,
            metadata=record.metadata,
            registered_at=record.registered_at,
            last_heartbeat=record.last_heartbeat,
        )
