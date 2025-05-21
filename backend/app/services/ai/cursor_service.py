"""
Cursor AI service integration with Windsurf MCP.
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

class CursorService(BaseAIService):
    """
    Cursor AI service integration with Windsurf MCP.
    
    This service integrates Cursor's AI-assisted code editing capabilities
    with the Windsurf MCP for centralized logging, monitoring, and management.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        mcp_config: Optional[MCPConfig] = None,
    ):
        """
        Initialize the Cursor AI service.
        
        Args:
            api_key: Cursor API key
            base_url: Cursor API base URL
            mcp_config: Configuration for Windsurf MCP
        """
        super().__init__(
            service_name="cursor",
            api_key=api_key or os.getenv("CURSOR_API_KEY"),
            mcp_config=mcp_config,
        )
        
        self.base_url = base_url or os.getenv("CURSOR_API_URL", "https://api.cursor.sh/v1")
        self.http_config = HttpClientConfig(
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            timeout=60.0,
        )
    
    async def initialize(self):
        """Initialize the Cursor AI service."""
        # Log initialization to MCP
        await self.mcp_client.send({
            "type": "ai_initialization",
            "ai_service": self.service_name,
            "status": "initialized",
        })
        
        logger.info("Initialized Cursor AI service")
    
    async def health_check(self) -> bool:
        """
        Check if the Cursor AI service is healthy.
        
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
            logger.error(f"Cursor health check failed: {str(e)}")
            
            # Log error to MCP
            await self.log_error(e, {"context": "health_check"})
            
            return False
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for the Cursor AI service.
        
        Returns:
            Dictionary of usage statistics
        """
        # In a real implementation, you would call the Cursor API to get usage stats
        # For now, we'll return placeholder data
        stats = {
            "edits_today": 0,
            "tokens_used": 0,
            "active_sessions": 0,
        }
        
        # Log usage stats to MCP
        await self.mcp_client.send({
            "type": "ai_usage_stats",
            "ai_service": self.service_name,
            "stats": stats,
        })
        
        return stats
    
    async def edit_code(
        self,
        code: str,
        instruction: str,
        language: str = None,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Edit code using Cursor AI.
        
        Args:
            code: Original code
            instruction: Edit instruction
            language: Programming language
            context: Additional context
            
        Returns:
            Edited code
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Prepare request data
        request_data = {
            "code": code,
            "instruction": instruction,
        }
        
        if language:
            request_data["language"] = language
        
        if context:
            request_data["context"] = context
        
        # Log request to MCP
        await self.log_request({
            "request_id": request_id,
            "code_length": len(code),
            "instruction": instruction,
            "language": language,
            "has_context": context is not None,
        })
        
        try:
            # Make request to Cursor API
            response = await post(
                f"{self.base_url}/edit",
                json_data=request_data,
                config=self.http_config,
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if response.is_error:
                error_msg = f"Cursor API error: {response.status_code} - {response.content}"
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
                "edited_code": response.content.get("code", ""),
                "diff": response.content.get("diff", ""),
                "explanation": response.content.get("explanation", ""),
                "request_id": request_id,
                "duration": duration,
            }
            
            # Log response to MCP
            await self.log_response(
                {
                    "edited_code_length": len(result["edited_code"]),
                    "has_diff": bool(result["diff"]),
                    "has_explanation": bool(result["explanation"]),
                    "duration": duration,
                },
                request_id
            )
            
            return result
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            logger.error(f"Cursor API request failed: {str(e)}")
            
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
    
    async def explain_code(
        self,
        code: str,
        language: str = None,
        detail_level: str = "medium",
    ) -> Dict[str, Any]:
        """
        Explain code using Cursor AI.
        
        Args:
            code: Code to explain
            language: Programming language
            detail_level: Level of detail (low, medium, high)
            
        Returns:
            Code explanation
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Prepare request data
        request_data = {
            "code": code,
            "detail_level": detail_level,
        }
        
        if language:
            request_data["language"] = language
        
        # Log request to MCP
        await self.log_request({
            "request_id": request_id,
            "code_length": len(code),
            "language": language,
            "detail_level": detail_level,
        })
        
        try:
            # Make request to Cursor API
            response = await post(
                f"{self.base_url}/explain",
                json_data=request_data,
                config=self.http_config,
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if response.is_error:
                error_msg = f"Cursor API error: {response.status_code} - {response.content}"
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
                "explanation": response.content.get("explanation", ""),
                "summary": response.content.get("summary", ""),
                "complexity_score": response.content.get("complexity_score", 0),
                "request_id": request_id,
                "duration": duration,
            }
            
            # Log response to MCP
            await self.log_response(
                {
                    "explanation_length": len(result["explanation"]),
                    "has_summary": bool(result["summary"]),
                    "complexity_score": result["complexity_score"],
                    "duration": duration,
                },
                request_id
            )
            
            return result
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            logger.error(f"Cursor API request failed: {str(e)}")
            
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
    
    async def generate_tests(
        self,
        code: str,
        language: str,
        test_framework: Optional[str] = None,
        coverage_level: str = "medium",
    ) -> Dict[str, Any]:
        """
        Generate tests for code using Cursor AI.
        
        Args:
            code: Code to generate tests for
            language: Programming language
            test_framework: Test framework to use
            coverage_level: Level of test coverage (low, medium, high)
            
        Returns:
            Generated tests
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Prepare request data
        request_data = {
            "code": code,
            "language": language,
            "coverage_level": coverage_level,
        }
        
        if test_framework:
            request_data["test_framework"] = test_framework
        
        # Log request to MCP
        await self.log_request({
            "request_id": request_id,
            "code_length": len(code),
            "language": language,
            "test_framework": test_framework,
            "coverage_level": coverage_level,
        })
        
        try:
            # Make request to Cursor API
            response = await post(
                f"{self.base_url}/generate-tests",
                json_data=request_data,
                config=self.http_config,
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if response.is_error:
                error_msg = f"Cursor API error: {response.status_code} - {response.content}"
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
                "tests": response.content.get("tests", ""),
                "test_count": response.content.get("test_count", 0),
                "coverage_estimate": response.content.get("coverage_estimate", 0),
                "request_id": request_id,
                "duration": duration,
            }
            
            # Log response to MCP
            await self.log_response(
                {
                    "tests_length": len(result["tests"]),
                    "test_count": result["test_count"],
                    "coverage_estimate": result["coverage_estimate"],
                    "duration": duration,
                },
                request_id
            )
            
            return result
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            logger.error(f"Cursor API request failed: {str(e)}")
            
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
