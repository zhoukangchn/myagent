from __future__ import annotations

from fastapi import APIRouter

from app.models.schemas import ChannelPostRequest
from app.services.channel_relay import relay_channel_post

router = APIRouter()


@router.post("/v1/channel/post")
async def channel_post(payload: ChannelPostRequest) -> dict[str, bool]:
    return await relay_channel_post(payload)
