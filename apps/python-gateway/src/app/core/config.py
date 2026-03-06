from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bind_host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("BRIDGE_BIND_HOST", "BIND_HOST"))
    bind_port: int = Field(default=8000, validation_alias=AliasChoices("BRIDGE_BIND_PORT", "BIND_PORT"))
    stream_timeout_sec: int = Field(default=120, validation_alias=AliasChoices("STREAM_TIMEOUT_SEC"))
    outbound_push_url: str = Field(default="", validation_alias=AliasChoices("OUTBOUND_PUSH_URL"))
    outbound_push_timeout_sec: int = Field(default=5, validation_alias=AliasChoices("OUTBOUND_PUSH_TIMEOUT_SEC"))
    outbound_push_retry: int = Field(default=0, validation_alias=AliasChoices("OUTBOUND_PUSH_RETRY"))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
