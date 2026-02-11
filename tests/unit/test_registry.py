from app.core.registry import InMemoryRegistry


def test_registry_add_get_list_delete():
    reg = InMemoryRegistry()
    created = reg.create(
        name="demo",
        base_url="http://example.com",
        mcp_endpoint="/mcp",
        description="d",
        tags=["x"],
        headers={"x-key": "1"},
    )

    fetched = reg.get(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert len(reg.list()) == 1

    reg.delete(created.id)
    assert reg.get(created.id) is None
    assert reg.list() == []


def test_registry_duplicate_name_rejected():
    reg = InMemoryRegistry()
    reg.create("demo", "http://a", "/mcp", "", [], {})

    try:
        reg.create("demo", "http://b", "/mcp", "", [], {})
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "already exists" in str(exc)
