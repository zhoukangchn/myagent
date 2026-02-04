import asyncio
import httpx
from typing import Any, Dict, Optional, Union
from src.app.core.logging import logger
from src.app.core.config import settings


class HTTPClient:
    """
    A dual-mode (Async/Sync) HTTP client utility using httpx.
    Provides persistent connection pooling with configurable SSL verification and timeout.
    
    Note: httpx does not support per-request `verify` overrides. SSL verification is set
    at the client level. If you need different verify settings, create separate HTTPClient instances.
    """
    def __init__(
        self, 
        base_url: str = "", 
        timeout: Optional[float] = None,
        headers: Optional[Dict[str, str]] = None,
        verify: Optional[bool] = None
    ):
        self.base_url = base_url
        # Use provided timeout, or config, or default 30.0
        self._default_timeout = timeout if timeout is not None else getattr(settings, "http_timeout", 30.0)
        # Store the connect timeout separately for per-request overrides
        self._connect_timeout = 5.0
        self.timeout = httpx.Timeout(self._default_timeout, connect=self._connect_timeout)
        self.headers = headers or {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        # SSL verification setting (only configurable at client level in httpx)
        self.verify = verify if verify is not None else getattr(settings, "http_verify_ssl", True)
        
        # Async members
        self._async_client: Optional[httpx.AsyncClient] = None
        self._async_lock = asyncio.Lock()
        
        # Sync members
        self._sync_client: Optional[httpx.Client] = None

    # --- Timeout Helper ---

    def _get_timeout(self, timeout: Optional[float]) -> httpx.Timeout:
        """Build httpx.Timeout object, preserving connect timeout for per-request overrides."""
        if timeout is not None:
            return httpx.Timeout(timeout, connect=self._connect_timeout)
        return self.timeout

    # --- Asynchronous Implementation ---

    async def get_async_client(self) -> httpx.AsyncClient:
        async with self._async_lock:
            if self._async_client is None or self._async_client.is_closed:
                self._async_client = httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=self.timeout,
                    headers=self.headers,
                    verify=self.verify,
                    limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
                )
            return self._async_client

    async def close_async(self):
        async with self._async_lock:
            if self._async_client and not self._async_client.is_closed:
                await self._async_client.aclose()
                self._async_client = None

    async def request_async(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """
        Make an async HTTP request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: URL endpoint
            params: Query parameters
            json_data: JSON body data
            headers: Additional headers
            timeout: Per-request timeout override (seconds)
            **kwargs: Additional arguments passed to httpx.request()
        """
        client = await self.get_async_client()
        request_timeout = self._get_timeout(timeout)
        try:
            response = await client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json_data,
                headers=headers,
                timeout=request_timeout,
                **kwargs
            )
            return self._handle_response(response, method, endpoint)
        except Exception as e:
            self._handle_error(e, method, endpoint)

    async def get(self, endpoint: str, timeout: Optional[float] = None, **kwargs) -> Any:
        """GET request (async)."""
        return await self.request_async("GET", endpoint, timeout=timeout, **kwargs)

    async def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None, **kwargs) -> Any:
        """POST request (async)."""
        return await self.request_async("POST", endpoint, json_data=json_data, timeout=timeout, **kwargs)

    async def put(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None, **kwargs) -> Any:
        """PUT request (async)."""
        return await self.request_async("PUT", endpoint, json_data=json_data, timeout=timeout, **kwargs)

    async def delete(self, endpoint: str, timeout: Optional[float] = None, **kwargs) -> Any:
        """DELETE request (async)."""
        return await self.request_async("DELETE", endpoint, timeout=timeout, **kwargs)

    # --- Synchronous Implementation ---

    def get_sync_client(self) -> httpx.Client:
        if self._sync_client is None or self._sync_client.is_closed:
            self._sync_client = httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self.headers,
                verify=self.verify,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=50)
            )
        return self._sync_client

    def close_sync(self):
        if self._sync_client and not self._sync_client.is_closed:
            self._sync_client.close()
            self._sync_client = None

    def request_sync(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> Any:
        """
        Make a sync HTTP request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: URL endpoint
            params: Query parameters
            json_data: JSON body data
            headers: Additional headers
            timeout: Per-request timeout override (seconds)
            **kwargs: Additional arguments passed to httpx.request()
        """
        client = self.get_sync_client()
        request_timeout = self._get_timeout(timeout)
        try:
            response = client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json_data,
                headers=headers,
                timeout=request_timeout,
                **kwargs
            )
            return self._handle_response(response, method, endpoint)
        except Exception as e:
            self._handle_error(e, method, endpoint)

    def get_sync(self, endpoint: str, timeout: Optional[float] = None, **kwargs) -> Any:
        """GET request (sync)."""
        return self.request_sync("GET", endpoint, timeout=timeout, **kwargs)

    def post_sync(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None, **kwargs) -> Any:
        """POST request (sync)."""
        return self.request_sync("POST", endpoint, json_data=json_data, timeout=timeout, **kwargs)

    def put_sync(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, timeout: Optional[float] = None, **kwargs) -> Any:
        """PUT request (sync)."""
        return self.request_sync("PUT", endpoint, json_data=json_data, timeout=timeout, **kwargs)

    def delete_sync(self, endpoint: str, timeout: Optional[float] = None, **kwargs) -> Any:
        """DELETE request (sync)."""
        return self.request_sync("DELETE", endpoint, timeout=timeout, **kwargs)

    # --- Common Helpers ---

    def _handle_response(self, response: httpx.Response, method: str, endpoint: str) -> Any:
        response.raise_for_status()
        if response.status_code == 204:
            return None
        
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.text

    def _handle_error(self, e: Exception, method: str, endpoint: str):
        if isinstance(e, httpx.HTTPStatusError):
            logger.error(f"HTTP {e.response.status_code} for {method} {endpoint}: {e.response.text[:200]}")
        else:
            logger.error(f"Request failed for {method} {endpoint}: {str(e)}")
        raise e


# Global shared instance (uses settings.http_verify_ssl for SSL verification)
http_client = HTTPClient()

# Convenience: Pre-configured insecure client for internal APIs
# Usage: from src.app.core.http_client import insecure_client
insecure_client = HTTPClient(verify=False)
