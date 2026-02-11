import json
import socket
import threading
import time

import pytest
import uvicorn

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from demo.weather_server import app


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.mark.asyncio
async def test_weather_server_mcp_flow_via_sdk():
    port = _free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)

    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    time.sleep(0.3)

    try:
        async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                tools = await session.list_tools()
                assert any(t.name == "get_weather" for t in tools.tools)
                assert any(t.name == "get_weather_forecast" for t in tools.tools)

                result = await session.call_tool("get_weather", {"city": "Beijing"})
                assert result.isError is False
                text = result.content[0].text
                assert "Beijing" in text

                forecast1 = await session.call_tool("get_weather_forecast", {"city": "Beijing", "days": 3})
                assert forecast1.isError is False
                payload1 = json.loads(forecast1.content[0].text)
                assert payload1["city"] == "Beijing"
                assert payload1["days"] == 3
                assert len(payload1["forecast"]) == 3

                forecast2 = await session.call_tool("get_weather_forecast", {"city": "Beijing", "days": 3})
                assert forecast2.isError is False
                payload2 = json.loads(forecast2.content[0].text)
                assert payload2["forecast"] == payload1["forecast"]
    finally:
        server.should_exit = True
        thread.join(timeout=2)
