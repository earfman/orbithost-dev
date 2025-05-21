"""
Base AI service interface for all AI integrations.
"""
import abc
import logging
from typing import Any, Dict, List, Optional, Union

from app.utils.mcp.client import get_mcp_client, MCPConfig

logger = logging.getLogger(__name__)

class BaseAIService(abc.ABC):
    """
    Base class for all AI service integrations.
    
    This abstract class defines the interface that all AI service
    integrations must implement. It also provides common functionality
    for logging and monitoring through Windsurf MCP.
    """
    
    def __init__(
        self,
        service_name: str,
        api_key: Optional[str] = None,
        mcp_config: Optional[MCPConfig] = None,
    ):
        """
        Initialize the AI service.
        
        Args:
            service_name: Name of the AI service
            api_key: API key for the AI service
            mcp_config: Configuration for Windsurf MCP
        """
        self.service_name = service_name
        self.api_key = api_key
        
        # Initialize MCP client for logging and monitoring
        self.mcp_client = get_mcp_client(mcp_config)
        
        logger.info(f"Initialized {service_name} AI service")
    
    async def log_request(self, request_data: Dict[str, Any]):
        """
        Log an AI service request to Windsurf MCP.
        
        Args:
            request_data: Request data to log
        """
        log_data = {
            "type": "ai_request",
            "ai_service": self.service_name,
            "request": request_data,
        }
        
        await self.mcp_client.send(log_data)
    
    async def log_response(self, response_data: Dict[str, Any], request_id: Optional[str] = None):
        """
        Log an AI service response to Windsurf MCP.
        
        Args:
            response_data: Response data to log
            request_id: ID of the corresponding request
        """
        log_data = {
            "type": "ai_response",
            "ai_service": self.service_name,
            "response": response_data,
        }
        
        if request_id:
            log_data["request_id"] = request_id
        
        await self.mcp_client.send(log_data)
    
    async def log_error(self, error: Exception, context: Dict[str, Any] = None):
        """
        Log an AI service error to Windsurf MCP.
        
        Args:
            error: Error to log
            context: Additional context for the error
        """
        log_data = {
            "type": "ai_error",
            "ai_service": self.service_name,
            "error": {
                "type": type(error).__name__,
                "message": str(error),
            },
        }
        
        if context:
            log_data["context"] = context
        
        await self.mcp_client.send(log_data)
    
    @abc.abstractmethod
    async def initialize(self):
        """
        Initialize the AI service.
        
        This method should be implemented by subclasses to perform
        any necessary initialization for the AI service.
        """
        pass
    
    @abc.abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the AI service is healthy.
        
        Returns:
            True if the service is healthy, False otherwise
        """
        pass
    
    @abc.abstractmethod
    async def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for the AI service.
        
        Returns:
            Dictionary of usage statistics
        """
        pass
