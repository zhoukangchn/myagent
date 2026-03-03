from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatStreamRequest(BaseModel):
    chat_id: str = Field(min_length=1)
    thread_id: str = Field(default="root", min_length=1)
    sender_id: str = Field(min_length=1)
    message_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
