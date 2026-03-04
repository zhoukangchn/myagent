from __future__ import annotations

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bind_host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("BRIDGE_BIND_HOST", "BIND_HOST"))
    bind_port: int = Field(default=8010, validation_alias=AliasChoices("BRIDGE_BIND_PORT", "BIND_PORT"))
    stream_timeout_sec: int = Field(default=120, validation_alias=AliasChoices("STREAM_TIMEOUT_SEC"))

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
