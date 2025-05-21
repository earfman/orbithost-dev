"""
AI integration service for OrbitBridge.

This module provides services for integrating with AI tools like Windsurf,
Claude, Replit, and Cursor, enabling them to access and interact with
OrbitContext data.
"""
import asyncio
import datetime
import json
import logging
import os
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import httpx
from pydantic import BaseModel, Field, validator

from app.services.orbitbridge.enhanced_context import (
    EnhancedOrbitContext, ContextType, SourceType, AgentType,
    get_context_by_id, get_project_contexts, search_contexts
)
from app.services.orbitbridge.mcp_client import MCPClient, MCPTransportType

# Configure logging
logger = logging.getLogger(__name__)


class AIToolType(str, Enum):
    """Types of AI tools that can integrate with OrbitContext."""
    WINDSURF = "windsurf"
    CLAUDE = "claude"
    REPLIT = "replit"
    CURSOR = "cursor"
    MCP = "mcp"  # Generic MCP-compatible tool


class AIToolConfig(BaseModel):
    """Configuration for an AI tool."""
    type: AIToolType
    name: str
    api_key: Optional[str] = None
    api_url: str
    webhook_url: Optional[str] = None
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Use the universal MCPClient instead of a Windsurf-specific client
# The implementation has been moved to mcp_client.py


class ClaudeClient:
    """Client for interacting with Claude."""
    
    def __init__(self, api_url: str, api_key: str):
        """
        Initialize the Claude client.
        
        Args:
            api_url: Claude API URL
            api_key: Claude API key
        """
        self.api_url = api_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=api_url,
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            timeout=60.0,
        )
    
    async def analyze_context(
        self,
        context: EnhancedOrbitContext,
        prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a context with Claude.
        
        Args:
            context: OrbitContext to analyze
            prompt: Custom prompt for Claude
            
        Returns:
            Analysis from Claude
        """
        try:
            # Convert context to a format Claude can understand
            context_dict = context.to_dict()
            context_json = json.dumps(context_dict, indent=2)
            
            # Create prompt
            if not prompt:
                if context.type == ContextType.ERROR:
                    prompt = f"""
                    You are an expert software developer helping analyze an error.
                    
                    Here is the error context:
                    {context_json}
                    
                    Please analyze this error and provide:
                    1. A clear explanation of what went wrong
                    2. The likely root cause
                    3. Suggested fixes
                    4. Any preventative measures for the future
                    
                    Format your response as markdown.
                    """
                elif context.type == ContextType.DEPLOYMENT:
                    prompt = f"""
                    You are an expert DevOps engineer helping analyze a deployment.
                    
                    Here is the deployment context:
                    {context_json}
                    
                    Please analyze this deployment and provide:
                    1. A summary of what was deployed
                    2. Any potential issues or concerns
                    3. Recommendations for improving the deployment process
                    
                    Format your response as markdown.
                    """
                else:
                    prompt = f"""
                    You are an expert software developer helping analyze some context.
                    
                    Here is the context:
                    {context_json}
                    
                    Please analyze this context and provide useful insights.
                    Format your response as markdown.
                    """
            
            # Send to Claude
            response = await self.client.post(
                "/v1/messages",
                json={
                    "model": "claude-3-opus-20240229",
                    "max_tokens": 4000,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                }
            )
            response.raise_for_status()
            
            result = response.json()
            
            # Extract the response content
            if "content" in result:
                return {
                    "analysis": result["content"][0]["text"],
                    "model": result.get("model", "claude"),
                    "id": result.get("id"),
                }
            
            return result
        except Exception as e:
            logger.error(f"Error analyzing context with Claude: {str(e)}")
            raise
    
    async def close(self):
        """Close the client."""
        await self.client.aclose()


class ReplitClient:
    """Client for interacting with Replit."""
    
    def __init__(self, api_url: str, api_key: Optional[str] = None):
        """
        Initialize the Replit client.
        
        Args:
            api_url: Replit API URL
            api_key: Replit API key
        """
        self.api_url = api_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=api_url,
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=30.0,
        )
    
    async def execute_code(
        self,
        code: str,
        language: str,
        context: Optional[EnhancedOrbitContext] = None,
    ) -> Dict[str, Any]:
        """
        Execute code with Replit.
        
        Args:
            code: Code to execute
            language: Programming language
            context: Optional context
            
        Returns:
            Execution result
        """
        try:
            # Prepare request
            request_data = {
                "code": code,
                "language": language,
            }
            
            if context:
                request_data["context"] = context.to_dict()
            
            # Send to Replit
            response = await self.client.post("/api/execute", json=request_data)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logger.error(f"Error executing code with Replit: {str(e)}")
            raise
    
    async def close(self):
        """Close the client."""
        await self.client.aclose()


class CursorClient:
    """Client for interacting with Cursor."""
    
    def __init__(self, api_url: str, api_key: str):
        """
        Initialize the Cursor client.
        
        Args:
            api_url: Cursor API URL
            api_key: Cursor API key
        """
        self.api_url = api_url
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url=api_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )
    
    async def suggest_edits(
        self,
        context: EnhancedOrbitContext,
        file_path: str,
        file_content: str,
    ) -> Dict[str, Any]:
        """
        Get edit suggestions from Cursor.
        
        Args:
            context: OrbitContext
            file_path: Path to the file
            file_content: Content of the file
            
        Returns:
            Edit suggestions
        """
        try:
            # Prepare request
            request_data = {
                "context": context.to_dict(),
                "file_path": file_path,
                "file_content": file_content,
            }
            
            # Send to Cursor
            response = await self.client.post("/api/suggest-edits", json=request_data)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logger.error(f"Error getting edit suggestions from Cursor: {str(e)}")
            raise
    
    async def close(self):
        """Close the client."""
        await self.client.aclose()


class AIIntegrationService:
    """
    Service for integrating with AI tools.
    
    This service provides methods for sending context to AI tools,
    getting feedback from them, and managing AI tool configurations.
    """
    
    def __init__(self):
        """Initialize the AI integration service."""
        self.configs: Dict[str, AIToolConfig] = {}
        self.mcp_clients: Dict[str, MCPClient] = {}  # Universal MCP clients
        self.claude_clients: Dict[str, ClaudeClient] = {}
        self.replit_clients: Dict[str, ReplitClient] = {}
        self.cursor_clients: Dict[str, CursorClient] = {}
        self.initialized = False
    
    async def initialize(self):
        """Initialize the service."""
        if self.initialized:
            return
        
        try:
            # Load configurations
            self._load_configs()
            
            # Import the MCP discovery utility
            from app.services.orbitbridge.windsurf_discovery import get_windsurf_mcp_url
            
            # Initialize clients
            for config_id, config in self.configs.items():
                if not config.enabled:
                    continue
                    
                # Handle MCP-compatible tools (including Windsurf)
                if config.type in [AIToolType.WINDSURF, AIToolType.MCP]:
                    # For Windsurf or other MCP tools, try to discover endpoint if set to "auto"
                    if config.api_url == "auto" and config.type == AIToolType.WINDSURF:
                        mcp_url = await get_windsurf_mcp_url()
                        if mcp_url:
                            logger.info(f"Discovered Windsurf MCP endpoint: {mcp_url}")
                            config.api_url = mcp_url
                        else:
                            logger.warning(f"Could not discover MCP endpoint for {config_id}. Integration disabled.")
                            continue
                    
                    # Determine transport type based on URL
                    transport_type = MCPTransportType.SSE
                    if config.api_url.endswith("/websocket"):
                        transport_type = MCPTransportType.WEBSOCKET
                    
                    # Create MCP client
                    self.mcp_clients[config_id] = MCPClient(
                        mcp_url=config.api_url,
                        api_key=config.api_key,
                        transport_type=transport_type,
                        client_id=f"orbitbridge-{config_id}"
                    )
                    logger.info(f"Initialized MCP client for {config_id} with endpoint: {config.api_url}")
                
                # Handle other AI tools
                elif config.type == AIToolType.CLAUDE:
                    self.claude_clients[config_id] = ClaudeClient(
                        api_url=config.api_url,
                        api_key=config.api_key,
                    )
                    logger.info(f"Initialized Claude client for {config_id}")
                elif config.type == AIToolType.REPLIT:
                    self.replit_clients[config_id] = ReplitClient(
                        api_url=config.api_url,
                        api_key=config.api_key,
                    )
                    logger.info(f"Initialized Replit client for {config_id}")
                elif config.type == AIToolType.CURSOR:
                    self.cursor_clients[config_id] = CursorClient(
                        api_url=config.api_url,
                        api_key=config.api_key,
                    )
                    logger.info(f"Initialized Cursor client for {config_id}")
            
            self.initialized = True
        except Exception as e:
            logger.error(f"Error initializing AI integration service: {str(e)}")
            raise
    
    async def _load_configs(self):
        """Load AI tool configurations."""
        # In a real implementation, this would load from a database
        # For now, we'll use environment variables as an example
        
        # Windsurf
        windsurf_url = os.getenv("WINDSURF_API_URL")
        windsurf_key = os.getenv("WINDSURF_API_KEY")
        
        if windsurf_url:
            self.configs["windsurf"] = AIToolConfig(
                type=AIToolType.WINDSURF,
                name="Windsurf MCP",
                api_url=windsurf_url,
                api_key=windsurf_key,
                webhook_url=os.getenv("WINDSURF_WEBHOOK_URL"),
                enabled=True,
            )
        
        # Claude
        claude_url = os.getenv("CLAUDE_API_URL", "https://api.anthropic.com")
        claude_key = os.getenv("CLAUDE_API_KEY")
        
        if claude_key:
            self.configs["claude"] = AIToolConfig(
                type=AIToolType.CLAUDE,
                name="Claude",
                api_url=claude_url,
                api_key=claude_key,
                webhook_url=os.getenv("CLAUDE_WEBHOOK_URL"),
                enabled=True,
            )
        
        # Replit
        replit_url = os.getenv("REPLIT_API_URL")
        replit_key = os.getenv("REPLIT_API_KEY")
        
        if replit_url:
            self.configs["replit"] = AIToolConfig(
                type=AIToolType.REPLIT,
                name="Replit",
                api_url=replit_url,
                api_key=replit_key,
                webhook_url=os.getenv("REPLIT_WEBHOOK_URL"),
                enabled=True,
            )
        
        # Cursor
        cursor_url = os.getenv("CURSOR_API_URL")
        cursor_key = os.getenv("CURSOR_API_KEY")
        
        if cursor_url and cursor_key:
            self.configs["cursor"] = AIToolConfig(
                type=AIToolType.CURSOR,
                name="Cursor",
                api_url=cursor_url,
                api_key=cursor_key,
                webhook_url=os.getenv("CURSOR_WEBHOOK_URL"),
                enabled=True,
            )
    
    async def send_context_to_mcp(
        self,
        context: EnhancedOrbitContext,
        config_id: str,
    ) -> Dict[str, Any]:
        """
        Send a context to an MCP-compatible server.
        
        Args:
            context: OrbitContext to send
            config_id: MCP configuration ID
            
        Returns:
            Response from the MCP server
        """
        await self.initialize()
        
        if config_id not in self.mcp_clients:
            raise ValueError(f"MCP client with ID '{config_id}' not found")
        
        return await self.mcp_clients[config_id].send_context(context)
        
    async def send_context_to_windsurf(
        self,
        context: EnhancedOrbitContext,
        config_id: str = "windsurf",
    ) -> Dict[str, Any]:
        """
        Send a context to Windsurf (legacy method, use send_context_to_mcp instead).
        
        Args:
            context: OrbitContext to send
            config_id: Windsurf configuration ID
            
        Returns:
            Response from Windsurf
        """
        logger.warning("send_context_to_windsurf is deprecated, use send_context_to_mcp instead")
        return await self.send_context_to_mcp(context, config_id)
    
    async def send_contexts_to_mcp(
        self,
        contexts: List[EnhancedOrbitContext],
        config_id: str,
    ) -> Dict[str, Any]:
        """
        Send multiple contexts to an MCP-compatible server.
        
        Args:
            contexts: OrbitContexts to send
            config_id: MCP configuration ID
            
        Returns:
            Response from the MCP server
        """
        await self.initialize()
        
        if config_id not in self.mcp_clients:
            raise ValueError(f"MCP client with ID '{config_id}' not found")
        
        return await self.mcp_clients[config_id].send_contexts(contexts)
    
    async def send_contexts_to_windsurf(
        self,
        contexts: List[EnhancedOrbitContext],
        config_id: str = "windsurf",
    ) -> Dict[str, Any]:
        """
        Send multiple contexts to Windsurf (legacy method, use send_contexts_to_mcp instead).
        
        Args:
            contexts: OrbitContexts to send
            config_id: Windsurf configuration ID
            
        Returns:
            Response from Windsurf
        """
        logger.warning("send_contexts_to_windsurf is deprecated, use send_contexts_to_mcp instead")
        return await self.send_contexts_to_mcp(contexts, config_id)
    
    async def invoke_mcp_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        config_id: str,
    ) -> Dict[str, Any]:
        """
        Invoke a tool in an MCP-compatible server.
        
        Args:
            tool_name: Name of the tool to invoke
            parameters: Tool parameters
            config_id: MCP configuration ID
            
        Returns:
            Tool response
        """
        await self.initialize()
        
        if config_id not in self.mcp_clients:
            raise ValueError(f"MCP client with ID '{config_id}' not found")
        
        return await self.mcp_clients[config_id].invoke_tool(tool_name, parameters)
    
    async def get_windsurf_feedback(
        self,
        context_id: str,
        config_id: str = "windsurf",
    ) -> Dict[str, Any]:
        """
        Get feedback from Windsurf for a context (legacy method, use invoke_mcp_tool instead).
        
        Args:
            context_id: Context ID
            config_id: Windsurf configuration ID
            
        Returns:
            Feedback from Windsurf
        """
        logger.warning("get_windsurf_feedback is deprecated, use invoke_mcp_tool instead")
        return await self.invoke_mcp_tool("get_feedback", {"context_id": context_id}, config_id)
    
    async def analyze_context_with_claude(
        self,
        context: EnhancedOrbitContext,
        prompt: Optional[str] = None,
        config_id: str = "claude",
    ) -> Dict[str, Any]:
        """
        Analyze a context with Claude.
        
        Args:
            context: OrbitContext to analyze
            prompt: Custom prompt for Claude
            config_id: Claude configuration ID
            
        Returns:
            Analysis from Claude
        """
        await self.initialize()
        
        if config_id not in self.claude_clients:
            raise ValueError(f"Claude client not found: {config_id}")
        
        client = self.claude_clients[config_id]
        return await client.analyze_context(context, prompt)
    
    async def execute_code_with_replit(
        self,
        code: str,
        language: str,
        context: Optional[EnhancedOrbitContext] = None,
        config_id: str = "replit",
    ) -> Dict[str, Any]:
        """
        Execute code with Replit.
        
        Args:
            code: Code to execute
            language: Programming language
            context: Optional context
            config_id: Replit configuration ID
            
        Returns:
            Execution result
        """
        await self.initialize()
        
        if config_id not in self.replit_clients:
            raise ValueError(f"Replit client not found: {config_id}")
        
        client = self.replit_clients[config_id]
        return await client.execute_code(code, language, context)
    
    async def get_cursor_edit_suggestions(
        self,
        context: EnhancedOrbitContext,
        file_path: str,
        file_content: str,
        config_id: str = "cursor",
    ) -> Dict[str, Any]:
        """
        Get edit suggestions from Cursor.
        
        Args:
            context: OrbitContext
            file_path: Path to the file
            file_content: Content of the file
            config_id: Cursor configuration ID
            
        Returns:
            Edit suggestions
        """
        await self.initialize()
        
        if config_id not in self.cursor_clients:
            raise ValueError(f"Cursor client not found: {config_id}")
        
        client = self.cursor_clients[config_id]
        return await client.suggest_edits(context, file_path, file_content)
    
    async def close(self):
        """Close all clients."""
        for client in self.windsurf_clients.values():
            await client.close()
        
        for client in self.claude_clients.values():
            await client.close()
        
        for client in self.replit_clients.values():
            await client.close()
        
        for client in self.cursor_clients.values():
            await client.close()


# Singleton instance
_ai_integration_service: Optional[AIIntegrationService] = None


async def get_ai_integration_service() -> AIIntegrationService:
    """
    Get the AIIntegrationService instance.
    
    Returns:
        AIIntegrationService instance
    """
    global _ai_integration_service
    
    if _ai_integration_service is None:
        _ai_integration_service = AIIntegrationService()
        await _ai_integration_service.initialize()
    
    return _ai_integration_service


# Convenience functions

async def send_context_to_windsurf(context: EnhancedOrbitContext) -> Dict[str, Any]:
    """
    Send a context to Windsurf.
    
    Args:
        context: OrbitContext to send
        
    Returns:
        Response from Windsurf
    """
    service = await get_ai_integration_service()
    return await service.send_context_to_windsurf(context)


async def analyze_context_with_claude(
    context: EnhancedOrbitContext,
    prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze a context with Claude.
    
    Args:
        context: OrbitContext to analyze
        prompt: Custom prompt for Claude
        
    Returns:
        Analysis from Claude
    """
    service = await get_ai_integration_service()
    return await service.analyze_context_with_claude(context, prompt)


async def execute_code_with_replit(
    code: str,
    language: str,
    context: Optional[EnhancedOrbitContext] = None,
) -> Dict[str, Any]:
    """
    Execute code with Replit.
    
    Args:
        code: Code to execute
        language: Programming language
        context: Optional context
        
    Returns:
        Execution result
    """
    service = await get_ai_integration_service()
    return await service.execute_code_with_replit(code, language, context)


async def get_cursor_edit_suggestions(
    context: EnhancedOrbitContext,
    file_path: str,
    file_content: str,
) -> Dict[str, Any]:
    """
    Get edit suggestions from Cursor.
    
    Args:
        context: OrbitContext
        file_path: Path to the file
        file_content: Content of the file
        
    Returns:
        Edit suggestions
    """
    service = await get_ai_integration_service()
    return await service.get_cursor_edit_suggestions(context, file_path, file_content)
