from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class ChatStreamRequest(BaseModel):
    chat_id: str = Field(min_length=1)
    thread_id: str = Field(default="root", min_length=1)
    sender_id: str = Field(min_length=1)
    message_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    text: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BridgeMessage(BaseModel):
    type: str
    request_id: str
    session_key: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    seq: int | None = None


class ChannelPostRequest(BaseModel):
    chat_id: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)
    message_id: str = Field(min_length=1)
    role: str = Field(default="assistant", min_length=1)
    content: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)
