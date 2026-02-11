from __future__ import annotations

import hashlib
import json
import random
from datetime import date, datetime, timedelta, timezone

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather-mcp-demo")

_CONDITIONS = ["Sunny", "Cloudy", "Rain", "Snow", "Windy", "Fog"]


@mcp.tool(name="get_weather", description="Return random weather for a city")
async def get_weather(city: str) -> str:
    condition = random.choice(_CONDITIONS)
    temperature_c = random.randint(-5, 36)
    observed_at = datetime.now(timezone.utc).isoformat()
    return f"{city}: {condition}, {temperature_c}C (observed_at={observed_at})"


def _stable_seed(city: str, day: str) -> int:
    digest = hashlib.sha256(f"{city.lower()}|{day}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


@mcp.tool(name="get_weather_forecast", description="Return deterministic weather forecast for a city")
async def get_weather_forecast(city: str, days: int = 3) -> str:
    span = max(1, min(days, 7))
    today = date.today()
    items = []

    for i in range(span):
        current = today + timedelta(days=i)
        current_day = current.isoformat()
        rng = random.Random(_stable_seed(city, current_day))
        temp_low = rng.randint(-8, 28)
        temp_high = temp_low + rng.randint(3, 12)
        items.append(
            {
                "date": current_day,
                "condition": _CONDITIONS[rng.randint(0, len(_CONDITIONS) - 1)],
                "temp_high_c": temp_high,
                "temp_low_c": temp_low,
            }
        )

    payload = {
        "city": city,
        "days": span,
        "forecast": items,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    return json.dumps(payload, ensure_ascii=True)


app = mcp.streamable_http_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("demo.weather_server:app", host="127.0.0.1", port=9001, reload=True)
