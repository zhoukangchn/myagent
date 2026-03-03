from __future__ import annotations

from gateway.deps.settings import get_settings
from gateway.services.auth_service import AuthService
from gateway.services.bridge_service import BridgeService

settings = get_settings()
auth_service = AuthService(settings)
bridge_service = BridgeService()
