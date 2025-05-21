"""
Windsurf MCP discovery utility.

This module provides utilities for discovering Windsurf MCP endpoints.
"""
import asyncio
import json
import logging
import os
import platform
import socket
from typing import List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

# Common Windsurf MCP endpoint ports
DEFAULT_MCP_PORTS = [8000, 8080, 3000, 3001]

# Common Windsurf installation paths by platform
WINDSURF_PATHS = {
    "Darwin": [
        "/Applications/Windsurf.app",
        "~/Applications/Windsurf.app",
    ],
    "Windows": [
        "C:\\Program Files\\Windsurf",
        "C:\\Program Files (x86)\\Windsurf",
        "%LOCALAPPDATA%\\Windsurf",
    ],
    "Linux": [
        "/opt/windsurf",
        "/usr/local/bin/windsurf",
        "~/.local/bin/windsurf",
    ]
}


async def is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """Check if a port is open on the given host."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except (asyncio.TimeoutError, ConnectionRefusedError, socket.gaierror):
        return False


async def check_mcp_endpoint(url: str) -> bool:
    """Check if a URL is a valid MCP endpoint."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{url}/health", timeout=2.0)
            if response.status_code == 200:
                return True
            
            # Try another common MCP health endpoint
            response = await client.get(f"{url}/status", timeout=2.0)
            return response.status_code == 200
    except Exception:
        return False


async def discover_local_windsurf_mcp() -> Optional[str]:
    """
    Discover local Windsurf MCP endpoint.
    
    Returns:
        MCP endpoint URL if found, None otherwise
    """
    # First check environment variable
    mcp_url = os.getenv("WINDSURF_MCP_URL")
    if mcp_url:
        logger.info(f"Using MCP URL from environment: {mcp_url}")
        if await check_mcp_endpoint(mcp_url):
            return mcp_url
        logger.warning(f"MCP endpoint {mcp_url} is not responding")
    
    # Check common local ports
    for port in DEFAULT_MCP_PORTS:
        if await is_port_open("localhost", port):
            for protocol in ["http", "https"]:
                url = f"{protocol}://localhost:{port}/sse"
                if await check_mcp_endpoint(url.replace("/sse", "")):
                    logger.info(f"Discovered Windsurf MCP at {url}")
                    return url
    
    logger.warning("No local Windsurf MCP endpoint found")
    return None


async def check_windsurf_installed() -> bool:
    """Check if Windsurf is installed on the system."""
    system = platform.system()
    if system in WINDSURF_PATHS:
        for path in WINDSURF_PATHS[system]:
            expanded_path = os.path.expanduser(path)
            if os.path.exists(expanded_path):
                logger.info(f"Found Windsurf installation at {expanded_path}")
                return True
    
    logger.warning("No Windsurf installation found")
    return False


async def get_windsurf_mcp_url() -> Optional[str]:
    """
    Get the Windsurf MCP URL, discovering it if necessary.
    
    Returns:
        MCP endpoint URL if found, None otherwise
    """
    # Try to discover local Windsurf MCP
    mcp_url = await discover_local_windsurf_mcp()
    if mcp_url:
        return mcp_url
    
    # Check if Windsurf is installed
    if await check_windsurf_installed():
        logger.info("Windsurf is installed but not running or MCP is not accessible")
        logger.info("Please start Windsurf and try again")
    else:
        logger.info("Windsurf is not installed")
        logger.info("Please install Windsurf from https://windsurf.ai or configure a remote MCP endpoint")
    
    return None
