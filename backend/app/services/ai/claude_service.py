"""
Claude AI service integration with Windsurf MCP.
"""
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Union

import httpx

from app.utils.http.client import HttpClientConfig, post
from app.utils.mcp.client import MCPConfig
from app.services.ai.base_ai_service import BaseAIService

logger = logging.getLogger(__name__)

class ClaudeService(BaseAIService):
    """
    Claude AI service integration with Windsurf MCP.
    
    This service integrates Anthropic's Claude AI with the Windsurf MCP
    for centralized logging, monitoring, and management.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        mcp_config: Optional[MCPConfig] = None,
    ):
        """
        Initialize the Claude AI service.
        
        Args:
            api_key: Claude API key
            base_url: Claude API base URL
            model: Claude model to use
            mcp_config: Configuration for Windsurf MCP
        """
        super().__init__(
            service_name="claude",
            api_key=api_key or os.getenv("CLAUDE_API_KEY"),
            mcp_config=mcp_config,
        )
        
        self.base_url = base_url or os.getenv("CLAUDE_API_URL", "https://api.anthropic.com/v1")
        self.model = model or os.getenv("CLAUDE_MODEL", "claude-3-opus-20240229")
        self.http_config = HttpClientConfig(
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
            },
            timeout=120.0,  # Longer timeout for AI requests
        )
    
    async def initialize(self):
        """Initialize the Claude AI service."""
        # Log initialization to MCP
        await self.mcp_client.send({
            "type": "ai_initialization",
            "ai_service": self.service_name,
            "model": self.model,
            "status": "initialized",
        })
        
        logger.info(f"Initialized Claude AI service with model: {self.model}")
    
    async def health_check(self) -> bool:
        """
        Check if the Claude AI service is healthy.
        
        Returns:
            True if the service is healthy, False otherwise
        """
        try:
            # Make a simple request to check if the API is responsive
            response = await post(
                f"{self.base_url}/messages",
                json_data={
                    "model": self.model,
                    "max_tokens": 10,
                    "messages": [
                        {"role": "user", "content": "Hello, are you working?"}
                    ],
                },
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
            logger.error(f"Claude health check failed: {str(e)}")
            
            # Log error to MCP
            await self.log_error(e, {"context": "health_check"})
            
            return False
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get usage statistics for the Claude AI service.
        
        Returns:
            Dictionary of usage statistics
        """
        # In a real implementation, you would call the Claude API to get usage stats
        # For now, we'll return placeholder data
        stats = {
            "requests_today": 0,
            "tokens_used_today": 0,
            "cost_today": 0.0,
        }
        
        # Log usage stats to MCP
        await self.mcp_client.send({
            "type": "ai_usage_stats",
            "ai_service": self.service_name,
            "stats": stats,
        })
        
        return stats
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.95,
        stop_sequences: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Generate text using Claude.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            stop_sequences: Sequences that will stop generation
            
        Returns:
            Generated text and metadata
        """
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Prepare request data
        request_data = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "messages": [
                {"role": "user", "content": prompt}
            ],
        }
        
        if system_prompt:
            request_data["system"] = system_prompt
        
        if stop_sequences:
            request_data["stop_sequences"] = stop_sequences
        
        # Log request to MCP
        await self.log_request({
            "request_id": request_id,
            "prompt": prompt,
            "system_prompt": system_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "model": self.model,
        })
        
        try:
            # Make request to Claude API
            response = await post(
                f"{self.base_url}/messages",
                json_data=request_data,
                config=self.http_config,
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if response.is_error:
                error_msg = f"Claude API error: {response.status_code} - {response.content}"
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
                "text": response.content.get("content", [{"text": ""}])[0].get("text", ""),
                "request_id": request_id,
                "model": self.model,
                "usage": response.content.get("usage", {}),
                "duration": duration,
            }
            
            # Log response to MCP
            await self.log_response(
                {
                    "text_length": len(result["text"]),
                    "usage": result["usage"],
                    "duration": duration,
                },
                request_id
            )
            
            return result
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            
            logger.error(f"Claude API request failed: {str(e)}")
            
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
    
    async def analyze_code(self, code: str, language: str = None) -> Dict[str, Any]:
        """
        Analyze code using Claude.
        
        Args:
            code: Code to analyze
            language: Programming language
            
        Returns:
            Analysis results
        """
        prompt = f"Analyze the following code and provide feedback on potential issues, improvements, and best practices:\n\n```{language or ''}\n{code}\n```"
        
        system_prompt = "You are an expert code reviewer. Focus on identifying bugs, security issues, performance problems, and adherence to best practices. Be concise and specific in your feedback."
        
        return await self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=1500,
            temperature=0.2,  # Lower temperature for more deterministic responses
        )
    
    async def summarize_deployment(self, deployment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a summary of a deployment using Claude.
        
        Args:
            deployment_data: Deployment data
            
        Returns:
            Deployment summary
        """
        # Extract relevant information from deployment data
        project = deployment_data.get("project", {})
        changes = deployment_data.get("changes", [])
        status = deployment_data.get("status", {})
        
        # Create a prompt for Claude
        prompt = f"""
        Generate a concise summary of this deployment:
        
        Project: {project.get('name')}
        Environment: {deployment_data.get('environment')}
        Status: {status.get('state')}
        Duration: {status.get('duration_seconds')} seconds
        
        Changes:
        {json.dumps(changes, indent=2)}
        
        Performance metrics:
        {json.dumps(deployment_data.get('metrics', {}), indent=2)}
        """
        
        system_prompt = "You are a deployment summary assistant. Create concise, informative summaries of code deployments highlighting key changes, potential issues, and performance impacts. Focus on what's most important for developers to know."
        
        return await self.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            max_tokens=800,
            temperature=0.3,
        )
