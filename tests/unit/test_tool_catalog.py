import pytest

from app.core.registry import InMemoryRegistry
from app.core.session_store import HubSessionStore
from app.core.tool_catalog import ToolCatalogStore


@pytest.mark.asyncio
async def test_refresh_server_builds_prefixed_tools():
    reg = InMemoryRegistry()
    store = HubSessionStore()

    class FakeClient:
        async def initialize(self, server):
            return "ds-1"

        async def list_tools(self, server, sid):
            return {"tools": [{"name": "echo", "description": "Echo", "inputSchema": {"type": "object"}}]}

    rec = reg.create("demo", "http://localhost:1", "/mcp", "", [], {})

    catalog = ToolCatalogStore(reg, store, FakeClient())
    count = await catalog.refresh_server(rec.id)

    assert count == 1
    entries = catalog.list_by_server(rec.id)
    assert entries[0].public_name == "demo.echo"
    assert entries[0].source_tool_name == "echo"
