from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ServerCreateRequest(BaseModel):
    name: str = Field(min_length=1)
    base_url: str = Field(min_length=1)
    mcp_endpoint: str = Field(min_length=1)
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)


class ServerRecord(BaseModel):
    id: str
    name: str
    base_url: str
    mcp_endpoint: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)
    status: str = "active"
    created_at: str
    updated_at: str


class McpServerConfigItem(BaseModel):
    url: str
    headers: dict[str, str] = Field(default_factory=dict)


class McpServersConfigResponse(BaseModel):
    mcpServers: dict[str, McpServerConfigItem] = Field(default_factory=dict)


class RpcRequest(BaseModel):
    jsonrpc: str
    id: Any = None
    method: str
    params: dict[str, Any] = Field(default_factory=dict)


class RpcResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Any = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


class ToolCallRequest(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
