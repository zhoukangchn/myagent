"""集中式异常层次结构"""

from typing import Optional


class AppException(Exception):
    """应用基础异常类"""

    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class ServiceException(AppException):
    """服务层基础异常"""

    def __init__(self, service: str, message: str, details: Optional[dict] = None):
        self.service = service
        super().__init__(f"[{service}] {message}", details)


class LLMServiceException(ServiceException):
    """LLM 服务异常"""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__("LLM", message, details)


class KnowledgeServiceException(ServiceException):
    """知识检索服务异常"""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__("Knowledge", message, details)


class HTTPClientException(ServiceException):
    """HTTP 客户端异常"""

    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[dict] = None):
        self.status_code = status_code
        if status_code:
            details = details or {}
            details["status_code"] = status_code
        super().__init__("HTTPClient", message, details)


class AuthServiceException(ServiceException):
    """认证服务异常"""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__("Auth", message, details)


class ConfigurationException(AppException):
    """配置异常"""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(f"[Configuration] {message}", details)


def handle_exception(exception: Exception) -> AppException:
    """将第三方异常转换为应用异常"""
    if isinstance(exception, AppException):
        return exception

    exception_name = type(exception).__name__

    # httpx 异常映射
    if exception_name.startswith("httpx"):
        return HTTPClientException(
            message=str(exception),
            details={"original_exception": exception_name}
        )

    # langchain 异常映射
    if "LangChain" in str(type(exception).__module__) or exception_name in [
        "ValueError", "TypeError", "KeyError"
    ]:
        return LLMServiceException(
            message=str(exception),
            details={"original_exception": exception_name}
        )

    # 默认转换为服务异常
    return AppException(message=str(exception), details={"original_exception": exception_name})
