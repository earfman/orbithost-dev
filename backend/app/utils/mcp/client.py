"""
Windsurf MCP client for centralized log management.
"""
import asyncio
import json
import logging
import os
import socket
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from app.utils.http.client import HttpClientConfig, post
from app.utils.logging.zap_logger import get_logger

logger = get_logger(service_name="mcp_client")

class MCPConfig:
    """Configuration for Windsurf MCP client."""
    
    def __init__(
        self,
        endpoint: str = None,
        api_key: str = None,
        service_name: str = None,
        environment: str = None,
        batch_size: int = 100,
        flush_interval: float = 5.0,
        enabled: bool = True,
    ):
        """
        Initialize MCP configuration.
        
        Args:
            endpoint: MCP API endpoint
            api_key: MCP API key
            service_name: Name of the service
            environment: Environment (development, staging, production)
            batch_size: Maximum number of logs to send in a batch
            flush_interval: Interval in seconds to flush logs
            enabled: Whether to enable MCP integration
        """
        self.endpoint = endpoint or os.getenv("MCP_ENDPOINT", "https://mcp.windsurf.io/api/v1/logs")
        self.api_key = api_key or os.getenv("MCP_API_KEY")
        self.service_name = service_name or os.getenv("SERVICE_NAME", "orbithost")
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.enabled = enabled and self.api_key is not None
        
        # Get hostname
        self.hostname = socket.gethostname()

class MCPClient:
    """
    Client for sending logs to Windsurf MCP.
    """
    
    def __init__(self, config: MCPConfig = None):
        """
        Initialize MCP client.
        
        Args:
            config: MCP configuration
        """
        self.config = config or MCPConfig()
        self.logs = []
        self.lock = asyncio.Lock()
        self.task = None
        
        if self.config.enabled:
            # Start background task to flush logs periodically
            self.task = asyncio.create_task(self._flush_periodically())
            logger.info(f"MCP client initialized with endpoint: {self.config.endpoint}")
        else:
            logger.warning("MCP client is disabled, logs will not be sent to MCP")
    
    async def _flush_periodically(self):
        """Flush logs periodically."""
        while True:
            await asyncio.sleep(self.config.flush_interval)
            await self.flush()
    
    async def flush(self):
        """Flush logs to MCP."""
        if not self.config.enabled or not self.logs:
            return
        
        async with self.lock:
            logs_to_send = self.logs.copy()
            self.logs = []
        
        if not logs_to_send:
            return
        
        try:
            # Send logs to MCP
            http_config = HttpClientConfig(
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.config.api_key}",
                },
                timeout=10.0,
            )
            
            payload = {
                "service": self.config.service_name,
                "environment": self.config.environment,
                "hostname": self.config.hostname,
                "logs": logs_to_send,
            }
            
            response = await post(
                self.config.endpoint,
                json_data=payload,
                config=http_config,
            )
            
            if response.is_error:
                logger.error(f"Failed to send logs to MCP: {response.content}")
            else:
                logger.debug(f"Sent {len(logs_to_send)} logs to MCP")
        except Exception as e:
            logger.error(f"Error sending logs to MCP: {str(e)}")
            
            # Put logs back in queue
            async with self.lock:
                self.logs = logs_to_send + self.logs
                
                # Trim logs if too many
                if len(self.logs) > self.config.batch_size * 10:
                    self.logs = self.logs[-self.config.batch_size * 10:]
    
    async def send(self, log: Dict[str, Any]):
        """
        Send a log to MCP.
        
        Args:
            log: Log data
        """
        if not self.config.enabled:
            return
        
        # Add timestamp if not present
        if "timestamp" not in log:
            log["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # Add service name if not present
        if "service" not in log:
            log["service"] = self.config.service_name
        
        # Add environment if not present
        if "environment" not in log:
            log["environment"] = self.config.environment
        
        # Add hostname if not present
        if "hostname" not in log:
            log["hostname"] = self.config.hostname
        
        async with self.lock:
            self.logs.append(log)
            
            # Flush if batch size reached
            if len(self.logs) >= self.config.batch_size:
                asyncio.create_task(self.flush())
    
    async def close(self):
        """Close the MCP client."""
        if self.task:
            self.task.cancel()
            
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        await self.flush()

class MCPHandler(logging.Handler):
    """
    Logging handler for sending logs to Windsurf MCP.
    """
    
    def __init__(self, client: MCPClient = None, config: MCPConfig = None):
        """
        Initialize MCP handler.
        
        Args:
            client: MCP client
            config: MCP configuration
        """
        super().__init__()
        self.client = client or MCPClient(config)
    
    def emit(self, record: logging.LogRecord):
        """
        Emit a log record to MCP.
        
        Args:
            record: Log record to emit
        """
        try:
            # Format log record
            log = {
                "timestamp": self._format_time(record.created),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "service": self.client.config.service_name,
                "environment": self.client.config.environment,
                "hostname": self.client.config.hostname,
            }
            
            # Include exception info if available
            if record.exc_info:
                log["exception"] = self._format_exception(record.exc_info)
            
            # Include caller info
            log["caller"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }
            
            # Include extra fields
            if hasattr(record, "extra") and record.extra:
                log.update(record.extra)
            
            # Send log to MCP
            asyncio.create_task(self.client.send(log))
        except Exception as e:
            sys.stderr.write(f"Error in MCPHandler: {str(e)}\n")
    
    def _format_time(self, timestamp: float) -> str:
        """
        Format timestamp as ISO 8601.
        
        Args:
            timestamp: UNIX timestamp
            
        Returns:
            ISO 8601 formatted timestamp
        """
        return datetime.fromtimestamp(timestamp).isoformat() + "Z"
    
    def _format_exception(self, exc_info) -> Dict[str, str]:
        """
        Format exception info.
        
        Args:
            exc_info: Exception info tuple
            
        Returns:
            Formatted exception info
        """
        import traceback
        exc_type, exc_value, exc_traceback = exc_info
        return {
            "type": exc_type.__name__,
            "message": str(exc_value),
            "traceback": "".join(traceback.format_exception(*exc_info)),
        }
    
    async def close(self):
        """Close the MCP handler."""
        await self.client.close()
        super().close()

_mcp_client = None

def get_mcp_client(config: MCPConfig = None) -> MCPClient:
    """
    Get a configured MCP client instance.
    
    Args:
        config: MCP configuration
        
    Returns:
        Configured MCP client instance
    """
    global _mcp_client
    
    if _mcp_client is None:
        _mcp_client = MCPClient(config)
    
    return _mcp_client

def setup_mcp_logging(logger_name: str = None, config: MCPConfig = None):
    """
    Set up MCP logging for a logger.
    
    Args:
        logger_name: Name of the logger to set up MCP logging for
        config: MCP configuration
    """
    # Get logger
    logger_to_setup = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    
    # Create MCP handler
    handler = MCPHandler(config=config)
    
    # Add handler to logger
    logger_to_setup.addHandler(handler)
    
    return handler
