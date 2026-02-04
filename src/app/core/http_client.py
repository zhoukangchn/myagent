import asyncio
import httpx
from typing import Any, Dict, Optional
from src.app.core.logging import logger

class HTTPClient:
    """
    A dual-mode (Async/Sync) HTTP client utility using httpx.
    Provides persistent connection pooling for both asynchronous and synchronous requests.
    """
    def __init__(
        self, 
        base_url: str = "", 
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None,
        verify: bool = True
    ):
        self.base_url = base_url
        self.timeout = httpx.Timeout(timeout, connect=5.0)
        self.headers = headers or {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self.verify = verify
        
        # Async members
        self._async_client: Optional[httpx.AsyncClient] = None
        self._async_lock = asyncio.Lock()
        
        # Sync members
        self._sync_client: Optional[httpx.Client] = None

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
        **kwargs
    ) -> Any:
        client = await self.get_async_client()
        try:
            response = await client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json_data,
                headers=headers,
                **kwargs
            )
            return self._handle_response(response, method, endpoint)
        except Exception as e:
            self._handle_error(e, method, endpoint)

    async def get(self, endpoint: str, **kwargs) -> Any:
        return await self.request_async("GET", endpoint, **kwargs)

    async def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        return await self.request_async("POST", endpoint, json_data=json_data, **kwargs)

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
        **kwargs
    ) -> Any:
        client = self.get_sync_client()
        try:
            response = client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json_data,
                headers=headers,
                **kwargs
            )
            return self._handle_response(response, method, endpoint)
        except Exception as e:
            self._handle_error(e, method, endpoint)

    def get_sync(self, endpoint: str, **kwargs) -> Any:
        return self.request_sync("GET", endpoint, **kwargs)

    def post_sync(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        return self.request_sync("POST", endpoint, json_data=json_data, **kwargs)

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

# Global shared instance
http_client = HTTPClient()
