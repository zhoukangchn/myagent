"""Database models and storage."""
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, String, DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session


class Base(DeclarativeBase):
    pass


class ServiceRecord(Base):
    """Database record for registered services."""
    __tablename__ = "services"
    
    name: Mapped[str] = mapped_column(String, primary_key=True)
    version: Mapped[str] = mapped_column(String, default="1.0.0")
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    transport: Mapped[str] = mapped_column(String)
    endpoint: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="offline")
    
    # Capabilities stored as JSON
    tools: Mapped[dict] = mapped_column(JSON, default=list)
    resources: Mapped[dict] = mapped_column(JSON, default=list)
    resource_templates: Mapped[dict] = mapped_column(JSON, default=list)
    prompts: Mapped[dict] = mapped_column(JSON, default=list)
    
    tags: Mapped[dict] = mapped_column(JSON, default=list)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    
    registered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_heartbeat: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class Database:
    def __init__(self, db_url: str = "sqlite:///./mcp_hub.db"):
        self.engine = create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        return Session(self.engine)
