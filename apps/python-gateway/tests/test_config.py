from __future__ import annotations

from gateway.config import get_settings


def test_settings_defaults():
    get_settings.cache_clear()
    cfg = get_settings()
    assert cfg.bind_host == "0.0.0.0"
    assert cfg.bind_port == 8010


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("BRIDGE_BIND_HOST", "127.0.0.1")
    monkeypatch.setenv("BRIDGE_BIND_PORT", "9000")
    get_settings.cache_clear()
    cfg = get_settings()
    assert cfg.bind_host == "127.0.0.1"
    assert cfg.bind_port == 9000
