"""
Windsurf IDE integration for OrbitBridge.

This module provides the integration between OrbitBridge and Windsurf IDE,
allowing Windsurf to access OrbitContext data directly from the IDE.
"""
import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body, WebSocket, WebSocketDisconnect

from app.services.orbitbridge.bridge import get_orbit_bridge, OrbitBridge
from app.services.orbitbridge.context import OrbitContext, ContextType
from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

# Create API router for Windsurf integration
router = APIRouter(prefix="/api/orbitbridge/windsurf", tags=["orbitbridge", "windsurf"])

@router.get("/contexts/{context_id}")
async def get_context(
    context_id: str = Path(..., description="ID of the context to get"),
):
    """
    Get an OrbitContext by ID.
    
    Args:
        context_id: ID of the context to get
        
    Returns:
        OrbitContext data
    """
    try:
        # Get OrbitBridge instance
        bridge = await get_orbit_bridge()
        
        # Get context
        context = await bridge.get_context(context_id)
        
        if not context:
            raise HTTPException(status_code=404, detail=f"Context {context_id} not found")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "windsurf_integration",
            "operation": "get_context",
            "context_id": context_id,
            "context_type": context.type,
        })
        
        return context.to_dict()
    except Exception as e:
        logger.error(f"Error getting context {context_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/contexts/type/{context_type}")
async def get_contexts_by_type(
    context_type: str = Path(..., description="Type of contexts to get"),
    limit: int = Query(10, description="Maximum number of contexts to return"),
    offset: int = Query(0, description="Offset for pagination"),
):
    """
    Get OrbitContexts by type.
    
    Args:
        context_type: Type of contexts to get
        limit: Maximum number of contexts to return
        offset: Offset for pagination
        
    Returns:
        List of OrbitContext data
    """
    try:
        # Validate context type
        try:
            context_type_enum = ContextType(context_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid context type: {context_type}")
        
        # Get OrbitBridge instance
        bridge = await get_orbit_bridge()
        
        # Get contexts
        contexts = await bridge.get_contexts_by_type(
            context_type=context_type_enum,
            limit=limit,
            offset=offset,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "windsurf_integration",
            "operation": "get_contexts_by_type",
            "context_type": context_type,
            "count": len(contexts),
        })
        
        return [context.to_dict() for context in contexts]
    except Exception as e:
        logger.error(f"Error getting contexts of type {context_type}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/deployments/latest")
async def get_latest_deployment():
    """
    Get the latest deployment context.
    
    Returns:
        Latest deployment context data
    """
    try:
        # Get OrbitBridge instance
        bridge = await get_orbit_bridge()
        
        # Get latest deployment
        deployment = await bridge.get_latest_deployment()
        
        if not deployment:
            raise HTTPException(status_code=404, detail="No deployment found")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "windsurf_integration",
            "operation": "get_latest_deployment",
            "deployment_id": deployment.deployment.id if deployment.deployment else "unknown",
        })
        
        return deployment.to_dict()
    except Exception as e:
        logger.error(f"Error getting latest deployment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/errors/latest")
async def get_latest_error():
    """
    Get the latest error context.
    
    Returns:
        Latest error context data
    """
    try:
        # Get OrbitBridge instance
        bridge = await get_orbit_bridge()
        
        # Get latest error
        error = await bridge.get_latest_error()
        
        if not error:
            raise HTTPException(status_code=404, detail="No error found")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "windsurf_integration",
            "operation": "get_latest_error",
            "error_id": error.id,
        })
        
        return error.to_dict()
    except Exception as e:
        logger.error(f"Error getting latest error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/code/fix")
async def generate_code_fix(
    request: Dict[str, Any] = Body(...),
):
    """
    Generate a code fix for an error using AI tools.
    
    Args:
        request: Request data containing error context ID, file path, code, and language
        
    Returns:
        Generated code fix
    """
    try:
        # Validate request
        error_context_id = request.get("error_context_id")
        file_path = request.get("file_path")
        code = request.get("code")
        language = request.get("language")
        
        if not error_context_id:
            raise HTTPException(status_code=400, detail="error_context_id is required")
        if not file_path:
            raise HTTPException(status_code=400, detail="file_path is required")
        if not code:
            raise HTTPException(status_code=400, detail="code is required")
        if not language:
            raise HTTPException(status_code=400, detail="language is required")
        
        # Get OrbitBridge instance
        bridge = await get_orbit_bridge()
        
        # Generate code fix
        fix = await bridge.generate_code_fix(
            error_context_id=error_context_id,
            file_path=file_path,
            code=code,
            language=language,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "windsurf_integration",
            "operation": "generate_code_fix",
            "error_context_id": error_context_id,
            "file_path": file_path,
            "language": language,
            "tool": fix.get("tool", "unknown"),
        })
        
        return fix
    except Exception as e:
        logger.error(f"Error generating code fix: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/deployments/feedback")
async def generate_deployment_feedback(
    request: Dict[str, Any] = Body(...),
):
    """
    Generate feedback for a deployment using AI tools.
    
    Args:
        request: Request data containing deployment context ID
        
    Returns:
        Generated deployment feedback
    """
    try:
        # Validate request
        deployment_context_id = request.get("deployment_context_id")
        
        if not deployment_context_id:
            raise HTTPException(status_code=400, detail="deployment_context_id is required")
        
        # Get OrbitBridge instance
        bridge = await get_orbit_bridge()
        
        # Generate deployment feedback
        feedback = await bridge.generate_deployment_feedback(
            deployment_context_id=deployment_context_id,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "windsurf_integration",
            "operation": "generate_deployment_feedback",
            "deployment_context_id": deployment_context_id,
            "tool": feedback.get("tool", "unknown"),
        })
        
        return feedback
    except Exception as e:
        logger.error(f"Error generating deployment feedback: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates from OrbitBridge.
    
    Args:
        websocket: WebSocket connection
    """
    await websocket.accept()
    
    # Log to MCP
    await get_mcp_client().send({
        "type": "windsurf_integration",
        "operation": "websocket_connect",
    })
    
    # Create a queue for messages
    queue = asyncio.Queue()
    
    # Function to handle new contexts
    async def handle_new_context(context: OrbitContext):
        await queue.put({
            "type": "new_context",
            "context": context.to_dict(),
        })
    
    # Register event handler (in a real implementation, this would be a proper event system)
    # For now, we'll just simulate periodic updates
    
    # Task to simulate periodic updates
    async def send_periodic_updates():
        try:
            while True:
                # In a real implementation, this would be triggered by actual events
                # For now, we'll just wait and not send anything
                await asyncio.sleep(60)
        except asyncio.CancelledError:
            pass
    
    # Start the periodic updates task
    periodic_task = asyncio.create_task(send_periodic_updates())
    
    try:
        # Handle incoming messages and send outgoing messages
        receive_task = asyncio.create_task(websocket.receive_text())
        send_task = asyncio.create_task(queue.get())
        
        while True:
            # Wait for either an incoming message or an outgoing message
            done, pending = await asyncio.wait(
                [receive_task, send_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            
            if receive_task in done:
                # Handle incoming message
                message = receive_task.result()
                
                try:
                    data = json.loads(message)
                    
                    # Handle different message types
                    if data.get("type") == "subscribe":
                        # Subscribe to specific context types
                        context_types = data.get("context_types", [])
                        
                        # Log to MCP
                        await get_mcp_client().send({
                            "type": "windsurf_integration",
                            "operation": "websocket_subscribe",
                            "context_types": context_types,
                        })
                        
                        # Acknowledge subscription
                        await websocket.send_json({
                            "type": "subscription_ack",
                            "context_types": context_types,
                        })
                    
                    # Reset receive task
                    receive_task = asyncio.create_task(websocket.receive_text())
                except json.JSONDecodeError:
                    # Invalid JSON
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON",
                    })
                    
                    # Reset receive task
                    receive_task = asyncio.create_task(websocket.receive_text())
            
            if send_task in done:
                # Send outgoing message
                message = send_task.result()
                await websocket.send_json(message)
                
                # Reset send task
                send_task = asyncio.create_task(queue.get())
    except WebSocketDisconnect:
        # Log to MCP
        await get_mcp_client().send({
            "type": "windsurf_integration",
            "operation": "websocket_disconnect",
        })
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        # Cancel tasks
        periodic_task.cancel()
        
        for task in [receive_task, send_task]:
            if not task.done():
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass

class WindsurfPlugin:
    """
    Windsurf IDE plugin for OrbitBridge integration.
    
    This class provides the client-side implementation for the Windsurf IDE plugin
    that integrates with OrbitBridge.
    """
    
    def __init__(
        self,
        api_url: str,
        api_key: Optional[str] = None,
    ):
        """
        Initialize the Windsurf plugin.
        
        Args:
            api_url: URL of the OrbitBridge API
            api_key: API key for authentication
        """
        self.api_url = api_url
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
        }
        
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    async def get_context(self, context_id: str) -> Dict[str, Any]:
        """
        Get an OrbitContext by ID.
        
        Args:
            context_id: ID of the context to get
            
        Returns:
            OrbitContext data
        """
        # In a real implementation, this would make an HTTP request to the API
        # For now, we'll just return a placeholder
        return {
            "id": context_id,
            "type": "deployment",
            "source": "orbitdeploy",
            "timestamp": "2025-05-20T21:00:00Z",
            "project_id": "project-123",
            "environment": "production",
        }
    
    async def get_latest_deployment(self) -> Dict[str, Any]:
        """
        Get the latest deployment context.
        
        Returns:
            Latest deployment context data
        """
        # In a real implementation, this would make an HTTP request to the API
        # For now, we'll just return a placeholder
        return {
            "id": "deployment-123",
            "type": "deployment",
            "source": "orbitdeploy",
            "timestamp": "2025-05-20T21:00:00Z",
            "project_id": "project-123",
            "environment": "production",
            "deployment": {
                "id": "deployment-123",
                "project_id": "project-123",
                "environment": "production",
                "branch": "main",
                "commit_hash": "abc123",
                "status": "success",
                "duration_seconds": 60.0,
            },
        }
    
    async def get_latest_error(self) -> Dict[str, Any]:
        """
        Get the latest error context.
        
        Returns:
            Latest error context data
        """
        # In a real implementation, this would make an HTTP request to the API
        # For now, we'll just return a placeholder
        return {
            "id": "error-123",
            "type": "error",
            "source": "orbithost",
            "timestamp": "2025-05-20T21:00:00Z",
            "project_id": "project-123",
            "environment": "production",
            "error": {
                "message": "TypeError: Cannot read property 'foo' of undefined",
                "type": "TypeError",
            },
            "error_location": {
                "file": "src/app.js",
                "line": 42,
                "column": 10,
                "function": "processData",
            },
        }
    
    async def generate_code_fix(
        self,
        error_context_id: str,
        file_path: str,
        code: str,
        language: str,
    ) -> Dict[str, Any]:
        """
        Generate a code fix for an error using AI tools.
        
        Args:
            error_context_id: ID of the error context
            file_path: Path to the file with the error
            code: Code with the error
            language: Programming language
            
        Returns:
            Generated code fix
        """
        # In a real implementation, this would make an HTTP request to the API
        # For now, we'll just return a placeholder
        return {
            "fixed_code": code.replace("undefined", "{}"),
            "explanation": "The error was caused by trying to access a property of undefined. I've replaced it with an empty object.",
            "diff": "@@ -42,7 +42,7 @@\n-foo.bar = undefined;\n+foo.bar = {};",
            "tool": "cursor",
        }
    
    async def generate_deployment_feedback(
        self,
        deployment_context_id: str,
    ) -> Dict[str, Any]:
        """
        Generate feedback for a deployment using AI tools.
        
        Args:
            deployment_context_id: ID of the deployment context
            
        Returns:
            Generated deployment feedback
        """
        # In a real implementation, this would make an HTTP request to the API
        # For now, we'll just return a placeholder
        return {
            "feedback": "The deployment was successful, but there are some performance concerns. Consider optimizing the database queries in src/db.js.",
            "tool": "claude",
        }
    
    async def subscribe_to_updates(
        self,
        callback: callable,
        context_types: Optional[List[str]] = None,
    ):
        """
        Subscribe to real-time updates from OrbitBridge.
        
        Args:
            callback: Callback function to call when updates are received
            context_types: Types of contexts to subscribe to
        """
        # In a real implementation, this would establish a WebSocket connection
        # For now, we'll just log a message
        print(f"Subscribed to updates for context types: {context_types or 'all'}")
        
        # In a real implementation, this would start a background task to listen for updates
        # For now, we'll just return immediately
