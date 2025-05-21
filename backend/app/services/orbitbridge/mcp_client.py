"""
Model Context Protocol (MCP) client for OrbitBridge.

This module provides a client for interacting with any MCP-compatible server,
including Windsurf, Claude Desktop, and other tools that implement the
Model Context Protocol standard.
"""
import asyncio
import datetime
import json
import logging
import os
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable

import httpx
from pydantic import BaseModel, Field, validator

from app.services.orbitbridge.enhanced_context import EnhancedOrbitContext

# Configure logging
logger = logging.getLogger(__name__)


class MCPTransportType(str, Enum):
    """Types of MCP transport protocols."""
    SSE = "sse"
    STDIO = "stdio"
    WEBSOCKET = "websocket"


class MCPResourceType(str, Enum):
    """Types of MCP resources."""
    ORBIT_CONTEXT = "orbitcontext"
    DOCUMENT = "document"
    CODE = "code"
    IMAGE = "image"
    CUSTOM = "custom"


class MCPTool(BaseModel):
    """MCP tool definition."""
    name: str
    description: str
    parameters: Dict[str, Any]
    required_parameters: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPClient:
    """Client for interacting with any MCP-compatible server."""
    
    def __init__(
        self, 
        mcp_url: str, 
        api_key: Optional[str] = None,
        transport_type: MCPTransportType = MCPTransportType.SSE,
        client_id: Optional[str] = None
    ):
        """
        Initialize the MCP client.
        
        Args:
            mcp_url: MCP endpoint URL (typically ends with /sse for SSE transport)
            api_key: Optional API key for authentication
            transport_type: MCP transport type (SSE, STDIO, or WEBSOCKET)
            client_id: Optional client identifier
        """
        self.mcp_url = mcp_url
        self.api_key = api_key
        self.transport_type = transport_type
        self.client_id = client_id or f"orbitbridge-{uuid.uuid4()}"
        
        # Headers for MCP protocol
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if transport_type == MCPTransportType.SSE else "application/json",
            "X-MCP-Client-ID": self.client_id
        }
        
        # Add authorization if API key is provided
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        self.client = httpx.AsyncClient(
            base_url=mcp_url,
            headers=headers,
            timeout=60.0,  # Longer timeout for SSE connections
        )
        
        # Track active SSE connections
        self.active_connections = set()
        self.connection_id = 0
        
        # Cache for discovered tools
        self.available_tools: List[MCPTool] = []
        self.tools_discovered = False
    
    async def send_context(self, context: EnhancedOrbitContext) -> Dict[str, Any]:
        """
        Send a context to an MCP server as a resource.
        
        Args:
            context: OrbitContext to send
            
        Returns:
            Response from the MCP server
        """
        try:
            # Convert to MCP resource format
            mcp_data = {
                "type": "resource",
                "resource": {
                    "type": MCPResourceType.ORBIT_CONTEXT.value,
                    "content": context.to_mcp_format()
                }
            }
            
            # Send to MCP endpoint
            response = await self.client.post("/resources", json=mcp_data)
            response.raise_for_status()
            
            # Parse the resource URI from the response
            result = response.json()
            resource_uri = result.get("uri")
            
            if not resource_uri:
                raise ValueError("No resource URI returned from MCP server")
                
            logger.info(f"Successfully sent context to MCP server with URI: {resource_uri}")
            return {"resource_uri": resource_uri, "response": result}
        except Exception as e:
            logger.error(f"Error sending context to MCP server: {str(e)}")
            raise
    
    async def send_contexts(self, contexts: List[EnhancedOrbitContext]) -> Dict[str, Any]:
        """
        Send multiple contexts to an MCP server as resources.
        
        Args:
            contexts: OrbitContexts to send
            
        Returns:
            Response from the MCP server with resource URIs
        """
        try:
            results = []
            resource_uris = []
            
            # Send each context as a separate resource
            for context in contexts:
                result = await self.send_context(context)
                results.append(result)
                resource_uris.append(result.get("resource_uri"))
            
            return {"resource_uris": resource_uris, "results": results}
        except Exception as e:
            logger.error(f"Error sending contexts to MCP server: {str(e)}")
            raise
    
    async def start_sse_connection(self, callback: Callable) -> str:
        """
        Start a Server-Sent Events (SSE) connection to receive updates from the MCP server.
        
        Args:
            callback: Async function to call when events are received
            
        Returns:
            Connection ID string
        """
        if self.transport_type != MCPTransportType.SSE:
            raise ValueError(f"Cannot start SSE connection with transport type {self.transport_type}")
            
        self.connection_id += 1
        connection_id = f"conn-{self.connection_id}"
        
        # Store connection for later cleanup
        self.active_connections.add(connection_id)
        
        # Start SSE connection in background task
        asyncio.create_task(self._listen_for_events(connection_id, callback))
        
        return connection_id
    
    async def _listen_for_events(self, connection_id: str, callback: Callable):
        """
        Listen for SSE events from the MCP server.
        
        Args:
            connection_id: Connection identifier
            callback: Function to call with received events
        """
        try:
            async with self.client.stream("GET", "") as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        try:
                            event = json.loads(data)
                            await callback(event)
                        except json.JSONDecodeError:
                            logger.error(f"Invalid JSON in SSE event: {data}")
        except Exception as e:
            logger.error(f"Error in SSE connection {connection_id}: {str(e)}")
        finally:
            # Remove connection from active set when done
            if connection_id in self.active_connections:
                self.active_connections.remove(connection_id)
    
    async def stop_sse_connection(self, connection_id: str):
        """
        Stop an active SSE connection.
        
        Args:
            connection_id: Connection ID to stop
        """
        if connection_id in self.active_connections:
            self.active_connections.remove(connection_id)
    
    async def discover_tools(self) -> List[MCPTool]:
        """
        Discover available tools from the MCP server.
        
        Returns:
            List of available tools
        """
        try:
            response = await self.client.get("/tools")
            response.raise_for_status()
            
            tools_data = response.json()
            tools = []
            
            for tool_data in tools_data.get("tools", []):
                tool = MCPTool(
                    name=tool_data.get("name"),
                    description=tool_data.get("description", ""),
                    parameters=tool_data.get("parameters", {}),
                    required_parameters=tool_data.get("required", []),
                    metadata=tool_data.get("metadata", {})
                )
                tools.append(tool)
            
            self.available_tools = tools
            self.tools_discovered = True
            
            logger.info(f"Discovered {len(tools)} tools from MCP server")
            return tools
        except Exception as e:
            logger.error(f"Error discovering tools from MCP server: {str(e)}")
            return []
    
    async def invoke_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke a tool in the MCP server.
        
        Args:
            tool_name: Name of the tool to invoke
            parameters: Tool parameters
            
        Returns:
            Tool response
        """
        try:
            # If tools haven't been discovered yet, try to discover them
            if not self.tools_discovered:
                await self.discover_tools()
            
            # Format the tool call according to MCP
            tool_call = {
                "type": "tool_call",
                "tool": tool_name,
                "parameters": parameters
            }
            
            # Send the tool call
            response = await self.client.post("/tools", json=tool_call)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logger.error(f"Error invoking tool {tool_name} via MCP: {str(e)}")
            raise
    
    async def send_prompt(self, prompt: str, resources: List[str] = None) -> Dict[str, Any]:
        """
        Send a prompt to the MCP server.
        
        Args:
            prompt: Prompt text
            resources: Optional list of resource URIs to include
            
        Returns:
            Response from the MCP server
        """
        try:
            # Format the prompt according to MCP
            prompt_data = {
                "type": "prompt",
                "prompt": prompt
            }
            
            # Add resources if provided
            if resources:
                prompt_data["resources"] = resources
            
            # Send the prompt
            response = await self.client.post("/prompts", json=prompt_data)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            logger.error(f"Error sending prompt to MCP server: {str(e)}")
            raise
    
    async def close(self):
        """Close the client and all active connections."""
        # Clear all active connections
        self.active_connections.clear()
        
        # Close the HTTP client
        await self.client.aclose()


# Convenience functions

async def send_context_to_mcp(
    context: EnhancedOrbitContext,
    mcp_url: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send a context to an MCP server.
    
    Args:
        context: OrbitContext to send
        mcp_url: MCP endpoint URL
        api_key: Optional API key
        
    Returns:
        Response from the MCP server
    """
    client = MCPClient(mcp_url=mcp_url, api_key=api_key)
    try:
        return await client.send_context(context)
    finally:
        await client.close()


async def invoke_mcp_tool(
    tool_name: str,
    parameters: Dict[str, Any],
    mcp_url: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Invoke a tool in an MCP server.
    
    Args:
        tool_name: Name of the tool to invoke
        parameters: Tool parameters
        mcp_url: MCP endpoint URL
        api_key: Optional API key
        
    Returns:
        Tool response
    """
    client = MCPClient(mcp_url=mcp_url, api_key=api_key)
    try:
        return await client.invoke_tool(tool_name, parameters)
    finally:
        await client.close()
