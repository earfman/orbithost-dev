"""
Model Context Protocol (MCP) Server for OrbitBridge.

This module provides a server implementation of the Model Context Protocol (MCP),
allowing OrbitHost to host its own MCP-compatible AI services. This server can be
used by any MCP client, including our universal MCP client, Windsurf, Claude Desktop,
and other tools that implement the MCP standard.
"""
import asyncio
import datetime
import json
import logging
import os
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Callable, Set

import httpx
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, validator

from app.services.orbitbridge.enhanced_context import EnhancedOrbitContext
from app.services.orbitbridge.mcp_client import MCPResourceType, MCPTool, MCPTransportType

# Configure logging
logger = logging.getLogger(__name__)


class MCPServerConfig(BaseModel):
    """Configuration for the MCP server."""
    host: str = "0.0.0.0"
    port: int = 8000
    base_path: str = "/mcp"
    enable_sse: bool = True
    enable_websocket: bool = True
    enable_stdio: bool = False
    auth_required: bool = True  # Enable authentication by default
    api_keys: Set[str] = Field(default_factory=set)
    llm_provider: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None
    max_context_size: int = 100000
    max_resources: int = 1000
    max_tools: int = 100
    max_connections: int = 100


class MCPConnection(BaseModel):
    """MCP connection information."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_id: Optional[str] = None
    transport_type: MCPTransportType
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    last_activity: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MCPResource(BaseModel):
    """MCP resource."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MCPResourceType
    content: Any
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    connection_id: Optional[str] = None


class MCPEvent(BaseModel):
    """MCP event."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    connection_id: Optional[str] = None


class MCPToolRequest(BaseModel):
    """MCP tool request."""
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    context_id: Optional[str] = None


class MCPToolResponse(BaseModel):
    """MCP tool response."""
    tool_name: str
    result: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    status: str = "success"


class MCPServer:
    """
    MCP server implementation.
    
    This class provides a server implementation of the Model Context Protocol (MCP),
    allowing OrbitHost to host its own MCP-compatible AI services.
    """
    
    def __init__(self, config: Optional[MCPServerConfig] = None):
        """
        Initialize the MCP server.
        
        Args:
            config: Server configuration
        """
        self.config = config or MCPServerConfig()
        self.router = APIRouter(prefix=self.config.base_path)
        self.connections: Dict[str, MCPConnection] = {}
        self.resources: Dict[str, MCPResource] = {}
        self.tools: Dict[str, MCPTool] = {}
        self.event_handlers: Dict[str, List[Callable]] = {}
        
        # Initialize tools
        self._init_tools()
        
        # Initialize routes
        self._init_routes()
        
        logger.info(f"Initialized MCP server with config: {self.config}")
    
    def _init_tools(self):
        """Initialize the default tools."""
        # Add deployment analysis tool
        self.tools["analyze_deployment"] = MCPTool(
            name="analyze_deployment",
            description="Analyze a deployment and provide feedback",
            parameters={
                "context_id": {
                    "type": "string",
                    "description": "ID of the context containing deployment information"
                },
                "deployment_id": {
                    "type": "string",
                    "description": "ID of the deployment to analyze"
                }
            },
            required_parameters=["context_id"],
            metadata={
                "category": "deployment",
                "provider": "orbithost"
            }
        )
        
        # Add error analysis tool
        self.tools["analyze_error"] = MCPTool(
            name="analyze_error",
            description="Analyze an error and provide feedback",
            parameters={
                "context_id": {
                    "type": "string",
                    "description": "ID of the context containing error information"
                },
                "error_id": {
                    "type": "string",
                    "description": "ID of the error to analyze"
                },
                "code": {
                    "type": "string",
                    "description": "Code associated with the error"
                },
                "language": {
                    "type": "string",
                    "description": "Programming language of the code"
                }
            },
            required_parameters=["context_id"],
            metadata={
                "category": "error",
                "provider": "orbithost"
            }
        )
        
        # Add performance recommendation tool
        self.tools["recommend_performance"] = MCPTool(
            name="recommend_performance",
            description="Generate performance recommendations",
            parameters={
                "context_id": {
                    "type": "string",
                    "description": "ID of the context containing performance metrics"
                },
                "project_id": {
                    "type": "string",
                    "description": "ID of the project to analyze"
                }
            },
            required_parameters=["context_id"],
            metadata={
                "category": "performance",
                "provider": "orbithost"
            }
        )
        
        logger.info(f"Initialized {len(self.tools)} default tools")
    
    def _init_routes(self):
        """Initialize the API routes."""
        # Health check endpoint
        @self.router.get("/health")
        async def health_check():
            return {"status": "ok", "timestamp": datetime.datetime.utcnow().isoformat()}
        
        # Tool discovery endpoint
        @self.router.get("/tools")
        async def get_tools():
            return {"tools": list(self.tools.values())}
        
        # Tool invocation endpoint
        @self.router.post("/tools/{tool_name}")
        async def invoke_tool(tool_name: str, request: MCPToolRequest):
            if tool_name not in self.tools:
                raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
            
            tool = self.tools[tool_name]
            
            # Validate required parameters
            for param in tool.required_parameters:
                if param not in request.parameters:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Missing required parameter: {param}"
                    )
            
            # Get context if provided
            context = None
            if request.context_id:
                resource = self.resources.get(request.context_id)
                if not resource:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Context with ID '{request.context_id}' not found"
                    )
                
                if resource.type != MCPResourceType.ORBIT_CONTEXT:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Resource with ID '{request.context_id}' is not an OrbitContext"
                    )
                
                context = resource.content
            
            # Execute the tool
            try:
                result = await self._execute_tool(
                    tool_name=tool_name,
                    parameters=request.parameters,
                    context=context
                )
                
                return MCPToolResponse(
                    tool_name=tool_name,
                    result=result,
                    status="success"
                )
            except Exception as e:
                logger.error(f"Error executing tool '{tool_name}': {str(e)}")
                return MCPToolResponse(
                    tool_name=tool_name,
                    result={},
                    error=str(e),
                    status="error"
                )
        
        # Resource management endpoints
        @self.router.post("/resources")
        async def create_resource(resource_type: MCPResourceType, content: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None):
            resource_id = str(uuid.uuid4())
            
            resource = MCPResource(
                id=resource_id,
                type=resource_type,
                content=content,
                metadata=metadata or {},
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow()
            )
            
            self.resources[resource_id] = resource
            
            return {"id": resource_id, "type": resource_type}
        
        @self.router.get("/resources/{resource_id}")
        async def get_resource(resource_id: str):
            resource = self.resources.get(resource_id)
            if not resource:
                raise HTTPException(status_code=404, detail=f"Resource '{resource_id}' not found")
            
            return resource
        
        # SSE endpoint for event streaming
        if self.config.enable_sse:
            @self.router.get("/sse")
            async def sse_endpoint(request: Request):
                connection_id = str(uuid.uuid4())
                
                connection = MCPConnection(
                    id=connection_id,
                    transport_type=MCPTransportType.SSE,
                    client_id=request.headers.get("X-Client-ID")
                )
                
                self.connections[connection_id] = connection
                logger.info(f"New SSE connection: {connection_id}")
                
                async def event_generator():
                    try:
                        # Send initial connection event
                        yield f"data: {json.dumps({'type': 'connection', 'id': connection_id})}\n\n"
                        
                        # Create event queue
                        queue = asyncio.Queue()
                        
                        # Register event handler
                        async def handle_event(event: MCPEvent):
                            if event.connection_id is None or event.connection_id == connection_id:
                                await queue.put(event)
                        
                        # Add handler to all event types
                        for event_type in ["tool_result", "resource_update", "system"]:
                            self._add_event_handler(event_type, handle_event)
                        
                        # Keep connection alive and process events
                        while True:
                            try:
                                # Send heartbeat every 30 seconds
                                heartbeat_task = asyncio.create_task(asyncio.sleep(30))
                                event_task = asyncio.create_task(queue.get())
                                
                                done, pending = await asyncio.wait(
                                    [heartbeat_task, event_task],
                                    return_when=asyncio.FIRST_COMPLETED
                                )
                                
                                for task in pending:
                                    task.cancel()
                                
                                if event_task in done:
                                    event = event_task.result()
                                    yield f"data: {json.dumps(event.dict())}\n\n"
                                else:
                                    # Heartbeat
                                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                                    
                                # Update last activity
                                connection.last_activity = datetime.datetime.utcnow()
                                
                            except asyncio.CancelledError:
                                break
                    
                    finally:
                        # Clean up connection
                        if connection_id in self.connections:
                            del self.connections[connection_id]
                        logger.info(f"SSE connection closed: {connection_id}")
                
                return StreamingResponse(
                    event_generator(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no"
                    }
                )
        
        # WebSocket endpoint for bidirectional communication
        if self.config.enable_websocket:
            @self.router.websocket("/ws")
            async def websocket_endpoint(websocket: WebSocket):
                await websocket.accept()
                
                connection_id = str(uuid.uuid4())
                client_id = None
                
                try:
                    # Get client ID from initial message
                    initial_message = await websocket.receive_json()
                    client_id = initial_message.get("client_id")
                    
                    connection = MCPConnection(
                        id=connection_id,
                        transport_type=MCPTransportType.WEBSOCKET,
                        client_id=client_id
                    )
                    
                    self.connections[connection_id] = connection
                    logger.info(f"New WebSocket connection: {connection_id}")
                    
                    # Send connection confirmation
                    await websocket.send_json({
                        "type": "connection",
                        "id": connection_id
                    })
                    
                    # Create event queue
                    queue = asyncio.Queue()
                    
                    # Register event handler
                    async def handle_event(event: MCPEvent):
                        if event.connection_id is None or event.connection_id == connection_id:
                            await queue.put(event)
                    
                    # Add handler to all event types
                    for event_type in ["tool_result", "resource_update", "system"]:
                        self._add_event_handler(event_type, handle_event)
                    
                    # Process incoming messages and outgoing events
                    while True:
                        # Wait for either a message from the client or an event to send
                        receive_task = asyncio.create_task(websocket.receive_json())
                        event_task = asyncio.create_task(queue.get())
                        heartbeat_task = asyncio.create_task(asyncio.sleep(30))
                        
                        done, pending = await asyncio.wait(
                            [receive_task, event_task, heartbeat_task],
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        
                        for task in pending:
                            task.cancel()
                        
                        if receive_task in done:
                            # Process message from client
                            message = receive_task.result()
                            await self._handle_websocket_message(connection_id, message, websocket)
                        
                        if event_task in done:
                            # Send event to client
                            event = event_task.result()
                            await websocket.send_json(event.dict())
                        
                        if heartbeat_task in done:
                            # Send heartbeat
                            await websocket.send_json({"type": "heartbeat"})
                        
                        # Update last activity
                        connection.last_activity = datetime.datetime.utcnow()
                
                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected: {connection_id}")
                
                except Exception as e:
                    logger.error(f"WebSocket error: {str(e)}")
                
                finally:
                    # Clean up connection
                    if connection_id in self.connections:
                        del self.connections[connection_id]
                    logger.info(f"WebSocket connection closed: {connection_id}")
    
    async def _handle_websocket_message(self, connection_id: str, message: Dict[str, Any], websocket: WebSocket):
        """
        Handle a message from a WebSocket client.
        
        Args:
            connection_id: Connection ID
            message: Message from the client
            websocket: WebSocket connection
        """
        message_type = message.get("type")
        
        if message_type == "invoke_tool":
            # Invoke a tool
            tool_name = message.get("tool_name")
            parameters = message.get("parameters", {})
            context_id = message.get("context_id")
            
            if not tool_name:
                await websocket.send_json({
                    "type": "error",
                    "error": "Missing tool_name in invoke_tool message"
                })
                return
            
            if tool_name not in self.tools:
                await websocket.send_json({
                    "type": "error",
                    "error": f"Tool '{tool_name}' not found"
                })
                return
            
            # Get context if provided
            context = None
            if context_id:
                resource = self.resources.get(context_id)
                if not resource:
                    await websocket.send_json({
                        "type": "error",
                        "error": f"Context with ID '{context_id}' not found"
                    })
                    return
                
                if resource.type != MCPResourceType.ORBIT_CONTEXT:
                    await websocket.send_json({
                        "type": "error",
                        "error": f"Resource with ID '{context_id}' is not an OrbitContext"
                    })
                    return
                
                context = resource.content
            
            # Execute the tool
            try:
                result = await self._execute_tool(
                    tool_name=tool_name,
                    parameters=parameters,
                    context=context
                )
                
                # Send result
                await websocket.send_json({
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "result": result,
                    "status": "success"
                })
            
            except Exception as e:
                logger.error(f"Error executing tool '{tool_name}': {str(e)}")
                await websocket.send_json({
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "error": str(e),
                    "status": "error"
                })
        
        elif message_type == "create_resource":
            # Create a resource
            resource_type_str = message.get("resource_type")
            content = message.get("content")
            metadata = message.get("metadata", {})
            
            if not resource_type_str:
                await websocket.send_json({
                    "type": "error",
                    "error": "Missing resource_type in create_resource message"
                })
                return
            
            if not content:
                await websocket.send_json({
                    "type": "error",
                    "error": "Missing content in create_resource message"
                })
                return
            
            try:
                resource_type = MCPResourceType(resource_type_str)
            except ValueError:
                await websocket.send_json({
                    "type": "error",
                    "error": f"Invalid resource_type: {resource_type_str}"
                })
                return
            
            resource_id = str(uuid.uuid4())
            
            resource = MCPResource(
                id=resource_id,
                type=resource_type,
                content=content,
                metadata=metadata,
                created_at=datetime.datetime.utcnow(),
                updated_at=datetime.datetime.utcnow(),
                connection_id=connection_id
            )
            
            self.resources[resource_id] = resource
            
            # Send result
            await websocket.send_json({
                "type": "resource_created",
                "id": resource_id,
                "resource_type": resource_type
            })
        
        elif message_type == "get_resource":
            # Get a resource
            resource_id = message.get("id")
            
            if not resource_id:
                await websocket.send_json({
                    "type": "error",
                    "error": "Missing id in get_resource message"
                })
                return
            
            resource = self.resources.get(resource_id)
            if not resource:
                await websocket.send_json({
                    "type": "error",
                    "error": f"Resource '{resource_id}' not found"
                })
                return
            
            # Send result
            await websocket.send_json({
                "type": "resource",
                "resource": resource.dict()
            })
        
        elif message_type == "heartbeat":
            # Heartbeat, just update last activity
            pass
        
        else:
            # Unknown message type
            await websocket.send_json({
                "type": "error",
                "error": f"Unknown message type: {message_type}"
            })
    
    async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any], context: Optional[Any] = None) -> Dict[str, Any]:
        """
        Execute a tool.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            context: Optional context for the tool
            
        Returns:
            Tool result
        """
        # This is a placeholder for the actual tool execution
        # In a real implementation, we would dispatch to the appropriate tool handler
        
        if tool_name == "analyze_deployment":
            # Placeholder for deployment analysis
            return {
                "feedback": "This is a placeholder for deployment analysis feedback.",
                "deployment_id": parameters.get("deployment_id", "unknown"),
                "status": "success",
                "tool": "mcp_server"
            }
        
        elif tool_name == "analyze_error":
            # Placeholder for error analysis
            return {
                "analysis": "This is a placeholder for error analysis.",
                "error_id": parameters.get("error_id", "unknown"),
                "status": "success",
                "tool": "mcp_server"
            }
        
        elif tool_name == "recommend_performance":
            # Placeholder for performance recommendations
            return {
                "recommendations": [
                    "This is a placeholder for performance recommendations."
                ],
                "project_id": parameters.get("project_id", "unknown"),
                "status": "success",
                "tool": "mcp_server"
            }
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    def _add_event_handler(self, event_type: str, handler: Callable):
        """
        Add an event handler.
        
        Args:
            event_type: Type of event to handle
            handler: Event handler function
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
        
        self.event_handlers[event_type].append(handler)
    
    async def _emit_event(self, event: MCPEvent):
        """
        Emit an event to all registered handlers.
        
        Args:
            event: Event to emit
        """
        handlers = self.event_handlers.get(event.type, [])
        
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {str(e)}")
    
    def get_router(self) -> APIRouter:
        """
        Get the FastAPI router for the MCP server.
        
        Returns:
            FastAPI router
        """
        return self.router


# Global MCP server instance
_mcp_server = None


async def get_mcp_server(config: Optional[MCPServerConfig] = None) -> MCPServer:
    """
    Get the MCP server instance.
    
    Args:
        config: Optional server configuration
        
    Returns:
        MCP server instance
    """
    global _mcp_server
    
    if _mcp_server is None:
        _mcp_server = MCPServer(config)
    
    return _mcp_server


def init_mcp_server(app: FastAPI, config: Optional[MCPServerConfig] = None):
    """
    Initialize the MCP server and add its routes to a FastAPI application.
        
    Args:
        app: FastAPI application
        config: Optional server configuration
    """
    # Import authentication dependencies
    from app.core.auth import clerk_auth
    
    # Get or create MCP server instance
    server = get_mcp_server(config)
    
    # Add authentication dependency to routes that require it
    if server.config.auth_required:
        router = server.get_router()
        for route in router.routes:
            if getattr(route, "methods", None) and "GET" not in route.methods:
                # Add authentication dependency to non-GET routes
                route.dependencies.append(Depends(clerk_auth.get_current_user))
    
    # Add MCP server routes to FastAPI application
    app.include_router(server.get_router())
    
    return server

async def startup_mcp_server(app: FastAPI, config: Optional[MCPServerConfig] = None):
    """Initialize the MCP server during application startup."""
    server = await get_mcp_server(config)
    logger.info("MCP server initialized during application startup")
    app.include_router(server.get_router())
    logger.info("MCP server initialized and routes added to FastAPI application")
