from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BridgeMessage(BaseModel):
    type: str
    request_id: str
    session_key: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    seq: int | None = None
