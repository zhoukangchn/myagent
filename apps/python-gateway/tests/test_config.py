from __future__ import annotations

from app.core.config import get_settings


def test_settings_defaults():
    get_settings.cache_clear()
    cfg = get_settings()
    assert cfg.bind_host == "0.0.0.0"
    assert cfg.bind_port == 8000
    assert cfg.outbound_push_url == ""
    assert cfg.outbound_push_timeout_sec == 5
    assert cfg.outbound_push_retry == 0
    assert cfg.third_party_ws_enabled is False
    assert cfg.third_party_ws_url == ""
    assert cfg.third_party_ws_connect_timeout_sec == 10


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("BRIDGE_BIND_HOST", "127.0.0.1")
    monkeypatch.setenv("BRIDGE_BIND_PORT", "9000")
    monkeypatch.setenv("OUTBOUND_PUSH_URL", "https://example.test/push")
    monkeypatch.setenv("OUTBOUND_PUSH_TIMEOUT_SEC", "9")
    monkeypatch.setenv("OUTBOUND_PUSH_RETRY", "2")
    monkeypatch.setenv("THIRD_PARTY_WS_ENABLED", "true")
    monkeypatch.setenv("THIRD_PARTY_WS_URL", "ws://127.0.0.1:8765/ws")
    monkeypatch.setenv("THIRD_PARTY_WS_HEADERS_JSON", '{"x-test":"1"}')
    monkeypatch.setenv("THIRD_PARTY_WS_BEARER_TOKEN", "token-1")
    get_settings.cache_clear()
    cfg = get_settings()
    assert cfg.bind_host == "127.0.0.1"
    assert cfg.bind_port == 9000
    assert cfg.outbound_push_url == "https://example.test/push"
    assert cfg.outbound_push_timeout_sec == 9
    assert cfg.outbound_push_retry == 2
    assert cfg.third_party_ws_enabled is True
    assert cfg.third_party_ws_url == "ws://127.0.0.1:8765/ws"
    assert cfg.third_party_ws_headers_json == '{"x-test":"1"}'
    assert cfg.third_party_ws_bearer_token == "token-1"
