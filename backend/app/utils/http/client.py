"""
HTTP client utilities for making HTTP requests.
"""
import logging
from typing import Any, Dict, List, Optional, Union
from contextlib import asynccontextmanager

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class HttpResponse(BaseModel):
    """Model for HTTP response data."""
    status_code: int
    content: Any
    headers: Dict[str, str] = {}
    
    @property
    def is_success(self) -> bool:
        """Check if the response status code indicates success."""
        return 200 <= self.status_code < 300
    
    @property
    def is_error(self) -> bool:
        """Check if the response status code indicates an error."""
        return not self.is_success

class HttpClientConfig(BaseModel):
    """Configuration for HTTP client."""
    base_url: Optional[str] = None
    headers: Dict[str, str] = {}
    timeout: float = 30.0
    verify: bool = True
    follow_redirects: bool = True

@asynccontextmanager
async def get_http_client(config: Optional[HttpClientConfig] = None):
    """
    Get an HTTP client with the specified configuration.
    
    Args:
        config: Configuration for the HTTP client
        
    Yields:
        An HTTP client instance
    """
    client_config = config or HttpClientConfig()
    
    async with httpx.AsyncClient(
        base_url=client_config.base_url,
        headers=client_config.headers,
        timeout=client_config.timeout,
        verify=client_config.verify,
        follow_redirects=client_config.follow_redirects
    ) as client:
        yield client

async def make_request(
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    config: Optional[HttpClientConfig] = None,
) -> HttpResponse:
    """
    Make an HTTP request.
    
    Args:
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        url: URL to make the request to
        params: Query parameters
        headers: HTTP headers
        json_data: JSON data to send in the request body
        data: Form data to send in the request body
        config: HTTP client configuration
        
    Returns:
        HTTP response
    """
    method = method.upper()
    client_config = config or HttpClientConfig()
    
    if headers:
        merged_headers = {**client_config.headers, **headers}
        client_config.headers = merged_headers
    
    try:
        async with get_http_client(client_config) as client:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                headers=client_config.headers,
                json=json_data,
                data=data,
            )
            
            try:
                content = response.json()
            except Exception:
                content = response.text
            
            return HttpResponse(
                status_code=response.status_code,
                content=content,
                headers=dict(response.headers),
            )
    except httpx.RequestError as e:
        logger.error(f"HTTP request error: {str(e)}")
        return HttpResponse(
            status_code=0,
            content={"error": str(e)},
        )

async def get(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    config: Optional[HttpClientConfig] = None,
) -> HttpResponse:
    """
    Make a GET request.
    
    Args:
        url: URL to make the request to
        params: Query parameters
        headers: HTTP headers
        config: HTTP client configuration
        
    Returns:
        HTTP response
    """
    return await make_request("GET", url, params=params, headers=headers, config=config)

async def post(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    config: Optional[HttpClientConfig] = None,
) -> HttpResponse:
    """
    Make a POST request.
    
    Args:
        url: URL to make the request to
        params: Query parameters
        headers: HTTP headers
        json_data: JSON data to send in the request body
        data: Form data to send in the request body
        config: HTTP client configuration
        
    Returns:
        HTTP response
    """
    return await make_request(
        "POST", url, params=params, headers=headers, json_data=json_data, data=data, config=config
    )

async def put(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    config: Optional[HttpClientConfig] = None,
) -> HttpResponse:
    """
    Make a PUT request.
    
    Args:
        url: URL to make the request to
        params: Query parameters
        headers: HTTP headers
        json_data: JSON data to send in the request body
        data: Form data to send in the request body
        config: HTTP client configuration
        
    Returns:
        HTTP response
    """
    return await make_request(
        "PUT", url, params=params, headers=headers, json_data=json_data, data=data, config=config
    )

async def delete(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    config: Optional[HttpClientConfig] = None,
) -> HttpResponse:
    """
    Make a DELETE request.
    
    Args:
        url: URL to make the request to
        params: Query parameters
        headers: HTTP headers
        json_data: JSON data to send in the request body
        config: HTTP client configuration
        
    Returns:
        HTTP response
    """
    return await make_request(
        "DELETE", url, params=params, headers=headers, json_data=json_data, config=config
    )
