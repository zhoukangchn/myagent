import httpx
from typing import Any, Dict, Optional, Union
from src.app.core.logging import logger

class HTTPClient:
    """
    A reusable asynchronous HTTP client utility using httpx.
    This implementation uses a persistent AsyncClient to benefit from connection pooling.
    """
    def __init__(
        self, 
        base_url: str = "", 
        timeout: float = 30.0,
        headers: Optional[Dict[str, str]] = None
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.headers = headers or {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        self._client: Optional[httpx.AsyncClient] = None

    def get_client(self) -> httpx.AsyncClient:
        """
        Get or create the internal httpx.AsyncClient.
        """
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers=self.headers
            )
        return self._client

    async def close(self):
        """
        Close the internal client.
        """
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Any:
        client = self.get_client()
        url = endpoint # base_url is handled by the client
        
        try:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=headers, # Additional headers for this specific request
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during HTTP request: {str(e)}")
            raise

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        return await self.request("GET", endpoint, params=params, **kwargs)

    async def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, **kwargs) -> Any:
        return await self.request("POST", endpoint, data=data, **kwargs)

# Global shared instance for simple use cases
http_client = HTTPClient()
