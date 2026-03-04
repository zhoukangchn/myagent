from __future__ import annotations

import logging

from app.models.schemas import ChannelPostRequest

logger = logging.getLogger(__name__)


async def relay_channel_post(message: ChannelPostRequest) -> dict[str, bool]:
    source = str(message.metadata.get("source", "")).strip() or "unknown"
    logger.info(
        "channel_post received source=%s chat_id=%s thread_id=%s message_id=%s content_len=%d",
        source,
        message.chat_id,
        message.thread_id,
        message.message_id,
        len(message.content),
    )
    logger.info("channel_post relay todo: outbound delivery is not implemented yet")
    return {"ok": True, "accepted": True, "forwarded": False}
