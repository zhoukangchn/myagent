import threading
import time

import pytest
import uvicorn

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from demo.weather_server import app


@pytest.mark.asyncio
async def test_weather_server_mcp_flow_via_sdk():
    config = uvicorn.Config(app, host="127.0.0.1", port=9911, log_level="error")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(0.3)

    try:
        async with streamable_http_client("http://127.0.0.1:9911/mcp") as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                tools = await session.list_tools()
                assert any(t.name == "get_weather" for t in tools.tools)

                result = await session.call_tool("get_weather", {"city": "Beijing"})
                assert result.isError is False
                text = result.content[0].text
                assert "Beijing" in text
    finally:
        server.should_exit = True
        thread.join(timeout=2)
