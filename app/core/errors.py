class HubError(Exception):
    def __init__(self, message: str, code: int = -32000, data: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.data = data or {}


class RegistryError(HubError):
    pass


class McpTransportError(HubError):
    pass


class McpProtocolError(HubError):
    pass


class McpSessionExpiredError(HubError):
    pass
