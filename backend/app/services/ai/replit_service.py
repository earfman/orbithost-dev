"""
Replit AI service integration with Windsurf MCP.
"""
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Union

from app.utils.http.client import HttpClientConfig, post, get
from app.utils.mcp.client import MCPConfig
from app.services.ai.base_ai_service import BaseAIService

logger = logging.getLogger(__name__)

class ReplitService(BaseAIService):
    """
    Replit AI service integration with Windsurf MCP.
    
    This service integrates Replit's code execution and AI capabilities
    with the Windsurf MCP for centralized logging, monitoring, and management.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        mcp_config: Optional[MCPConfig] = None,
    ):
        """
        Initialize the Replit AI service.
        
        Args:
            api_key: Replit API key
            base_url: Replit API base URL
            mcp_config: Configuration for Windsurf MCP
        """
        super().__init__(
            service_name="replit",
            api_key=api_key or os.getenv("REPLIT_API_KEY"),
            mcp_config=mcp_config,
        )
        
        self.base_url = base_url or os.getenv("REPLIT_API_URL", "https://api.replit.com/v1")
        self.http_config = HttpClientConfig(
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            timeout=60.0,
        )
    
    async def initialize(self):
        """Initialize the Replit AI service."""
        # Log initialization to MCP
        await self.mcp_client.send({
            "type": "ai_initialization",
            "ai_service": self.service_name,
            "status": "initialized",
        })
        
        logger.info("Initialized Replit AI service")
    
    async def health_check(self) -> bool:
        """
        Check if the Replit AI service is healthy.
        
        Returns:
            True if the service is healthy, False otherwise
        """
        try:
            # Make a simple request to check if the API is responsive
            response = await get(
                f"{self.base_url}/health",
                config=self.http_config,
            )
            
            is_healthy = response.is_success
            
            # Log health check to MCP
            await self.mcp_client.send({
                "type": "ai_health_check",
                "ai_service": self.service_name,
                "status": "healthy" if is_healthy else "unhealthy",
                "response_code": response.status_code,
            })
            
            return is_healthy
        except Exception as e:
            logger.error(f"Replit health check failed: {str(e)}")
            
            # Log error to MCP
            await self.log_error(e, {"context": "health_check"})
            
            return False
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for the Replit AI service.
        
        Returns:
            Dictionary of usage statistics
        """
        # In a real implementation, you would call the Replit API to get usage stats
        # For now, we'll return placeholder data
        stats = {
            "repls_created_today": 0,
            "compute_hours_used": 0,
            "storage_used_mb": 0,
        }
        
        # Log usage stats to MCP
        await self.mcp_client.send({
            "type": "ai_usage_stats",
            "ai_service": self.service_name,
            "stats": stats,
        })
        
        return stats
    
    async def create_repl(
        self,
        name: str,
        language: str,
        code: Optional[str] = None,
        is_private: bool = True,
    ) -> Dict[str, Any]:
        """
        Create a new Repl.
        
        Args:
            name: Name of the Repl
            language: Programming language
            code: Initial code
            is_private: Whether the Repl should be private
            
        Returns:
            Created Repl details
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Prepare request data
        request_data = {
            "name": name,
            "language": language,
            "isPrivate": is_private,
        }
        
        if code:
            request_data["files"] = [
                {
                    "name": f"main.{self._get_file_extension(language)}",
                    "content": code,
                }
            ]
        
        # Log request to MCP
        await self.log_request({
            "request_id": request_id,
            "name": name,
            "language": language,
            "has_code": code is not None,
            "is_private": is_private,
        })
        
        try:
            # Make request to Replit API
            response = await post(
                f"{self.base_url}/repls",
                json_data=request_data,
                config=self.http_config,
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if response.is_error:
                error_msg = f"Replit API error: {response.status_code} - {response.content}"
                logger.error(error_msg)
                
                # Log error to MCP
                await self.log_error(
                    Exception(error_msg),
                    {
                        "request_id": request_id,
                        "status_code": response.status_code,
                        "response": response.content,
                    }
                )
                
                return {
                    "error": error_msg,
                    "request_id": request_id,
                    "duration": duration,
                }
            
            # Process successful response
            result = {
                "id": response.content.get("id"),
                "url": response.content.get("url"),
                "name": response.content.get("name"),
                "language": response.content.get("language"),
                "request_id": request_id,
                "duration": duration,
            }
            
            # Log response to MCP
            await self.log_response(
                {
                    "repl_id": result["id"],
                    "repl_url": result["url"],
                    "duration": duration,
                },
                request_id
            )
            
            return result
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            logger.error(f"Replit API request failed: {str(e)}")
            
            # Log error to MCP
            await self.log_error(
                e,
                {
                    "request_id": request_id,
                    "duration": duration,
                }
            )
            
            return {
                "error": str(e),
                "request_id": request_id,
                "duration": duration,
            }
    
    async def execute_code(
        self,
        code: str,
        language: str,
        input_data: Optional[str] = None,
        timeout: int = 10,
    ) -> Dict[str, Any]:
        """
        Execute code using Replit.
        
        Args:
            code: Code to execute
            language: Programming language
            input_data: Input data for the code
            timeout: Execution timeout in seconds
            
        Returns:
            Execution results
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Prepare request data
        request_data = {
            "language": language,
            "code": code,
            "timeout": timeout,
        }
        
        if input_data:
            request_data["input"] = input_data
        
        # Log request to MCP
        await self.log_request({
            "request_id": request_id,
            "language": language,
            "code_length": len(code),
            "has_input": input_data is not None,
            "timeout": timeout,
        })
        
        try:
            # Make request to Replit API
            response = await post(
                f"{self.base_url}/execute",
                json_data=request_data,
                config=self.http_config,
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if response.is_error:
                error_msg = f"Replit API error: {response.status_code} - {response.content}"
                logger.error(error_msg)
                
                # Log error to MCP
                await self.log_error(
                    Exception(error_msg),
                    {
                        "request_id": request_id,
                        "status_code": response.status_code,
                        "response": response.content,
                    }
                )
                
                return {
                    "error": error_msg,
                    "request_id": request_id,
                    "duration": duration,
                }
            
            # Process successful response
            result = {
                "output": response.content.get("output", ""),
                "error": response.content.get("error", ""),
                "exit_code": response.content.get("exitCode", 0),
                "execution_time": response.content.get("executionTime", 0),
                "request_id": request_id,
                "duration": duration,
            }
            
            # Log response to MCP
            await self.log_response(
                {
                    "output_length": len(result["output"]),
                    "has_error": bool(result["error"]),
                    "exit_code": result["exit_code"],
                    "execution_time": result["execution_time"],
                    "duration": duration,
                },
                request_id
            )
            
            return result
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            logger.error(f"Replit API request failed: {str(e)}")
            
            # Log error to MCP
            await self.log_error(
                e,
                {
                    "request_id": request_id,
                    "duration": duration,
                }
            )
            
            return {
                "error": str(e),
                "request_id": request_id,
                "duration": duration,
            }
    
    async def generate_code(
        self,
        prompt: str,
        language: str,
        max_tokens: int = 1000,
        temperature: float = 0.5,
    ) -> Dict[str, Any]:
        """
        Generate code using Replit AI.
        
        Args:
            prompt: Description of the code to generate
            language: Programming language
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            
        Returns:
            Generated code
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Prepare request data
        request_data = {
            "prompt": prompt,
            "language": language,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        # Log request to MCP
        await self.log_request({
            "request_id": request_id,
            "prompt": prompt,
            "language": language,
            "max_tokens": max_tokens,
            "temperature": temperature,
        })
        
        try:
            # Make request to Replit AI API
            response = await post(
                f"{self.base_url}/ai/generate",
                json_data=request_data,
                config=self.http_config,
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if response.is_error:
                error_msg = f"Replit AI API error: {response.status_code} - {response.content}"
                logger.error(error_msg)
                
                # Log error to MCP
                await self.log_error(
                    Exception(error_msg),
                    {
                        "request_id": request_id,
                        "status_code": response.status_code,
                        "response": response.content,
                    }
                )
                
                return {
                    "error": error_msg,
                    "request_id": request_id,
                    "duration": duration,
                }
            
            # Process successful response
            result = {
                "code": response.content.get("code", ""),
                "language": language,
                "request_id": request_id,
                "duration": duration,
            }
            
            # Log response to MCP
            await self.log_response(
                {
                    "code_length": len(result["code"]),
                    "language": language,
                    "duration": duration,
                },
                request_id
            )
            
            return result
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            logger.error(f"Replit AI API request failed: {str(e)}")
            
            # Log error to MCP
            await self.log_error(
                e,
                {
                    "request_id": request_id,
                    "duration": duration,
                }
            )
            
            return {
                "error": str(e),
                "request_id": request_id,
                "duration": duration,
            }
    
    def _get_file_extension(self, language: str) -> str:
        """
        Get the file extension for a programming language.
        
        Args:
            language: Programming language
            
        Returns:
            File extension
        """
        language_extensions = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "html": "html",
            "css": "css",
            "java": "java",
            "c": "c",
            "cpp": "cpp",
            "go": "go",
            "ruby": "rb",
            "rust": "rs",
            "php": "php",
            "swift": "swift",
            "kotlin": "kt",
            "csharp": "cs",
        }
        
        return language_extensions.get(language.lower(), "txt")
