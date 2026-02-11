from __future__ import annotations

import random
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather-mcp-demo")

_CONDITIONS = ["Sunny", "Cloudy", "Rain", "Snow", "Windy", "Fog"]


@mcp.tool(name="get_weather", description="Return random weather for a city")
async def get_weather(city: str) -> str:
    condition = random.choice(_CONDITIONS)
    temperature_c = random.randint(-5, 36)
    observed_at = datetime.now(timezone.utc).isoformat()
    return f"{city}: {condition}, {temperature_c}C (observed_at={observed_at})"


app = mcp.streamable_http_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("demo.weather_server:app", host="127.0.0.1", port=9001, reload=True)
