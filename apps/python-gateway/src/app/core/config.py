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
    third_party_ws_enabled: bool = Field(default=False, validation_alias=AliasChoices("THIRD_PARTY_WS_ENABLED"))
    third_party_ws_url: str = Field(default="", validation_alias=AliasChoices("THIRD_PARTY_WS_URL"))
    third_party_ws_connect_timeout_sec: int = Field(
        default=10,
        validation_alias=AliasChoices("THIRD_PARTY_WS_CONNECT_TIMEOUT_SEC"),
    )
    third_party_ws_reconnect_min_ms: int = Field(
        default=1000,
        validation_alias=AliasChoices("THIRD_PARTY_WS_RECONNECT_MIN_MS"),
    )
    third_party_ws_reconnect_max_ms: int = Field(
        default=30000,
        validation_alias=AliasChoices("THIRD_PARTY_WS_RECONNECT_MAX_MS"),
    )
    third_party_ws_ping_interval_sec: int = Field(
        default=20,
        validation_alias=AliasChoices("THIRD_PARTY_WS_PING_INTERVAL_SEC"),
    )
    third_party_ws_ping_timeout_sec: int = Field(
        default=20,
        validation_alias=AliasChoices("THIRD_PARTY_WS_PING_TIMEOUT_SEC"),
    )
    third_party_ws_headers_json: str = Field(
        default="",
        validation_alias=AliasChoices("THIRD_PARTY_WS_HEADERS_JSON"),
    )
    third_party_ws_bearer_token: str = Field(
        default="",
        validation_alias=AliasChoices("THIRD_PARTY_WS_BEARER_TOKEN"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
