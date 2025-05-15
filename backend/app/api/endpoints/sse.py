from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.models.deployment import Deployment, DeploymentStatus

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory store for active SSE connections
# In a production environment, this would be replaced with a Redis pub/sub system
active_connections: Dict[str, List[Response]] = {}

@router.get("/deployments/{repository}")
async def sse_deployments(repository: str, request: Request):
    """
    Server-Sent Events (SSE) endpoint for deployment updates.
    
    Args:
        repository: The repository to subscribe to (format: owner/repo)
        request: The FastAPI request object
        
    Returns:
        A streaming response with SSE events
    """
    logger.info(f"New SSE connection for repository: {repository}")
    
    async def event_generator():
        # Send initial connection established event
        yield format_sse_event(
            data={"status": "connected", "repository": repository, "timestamp": datetime.now().isoformat()},
            event="connection_established"
        )
        
        # Register this connection
        if repository not in active_connections:
            active_connections[repository] = []
        
        # Create a queue for this connection
        queue = asyncio.Queue()
        active_connections[repository].append(queue)
        
        try:
            # Keep the connection alive
            while True:
                # Send a heartbeat every 30 seconds
                heartbeat_task = asyncio.create_task(asyncio.sleep(30))
                
                # Wait for either a new event or the heartbeat
                event_task = asyncio.create_task(queue.get())
                
                done, pending = await asyncio.wait(
                    [heartbeat_task, event_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Cancel the pending task
                for task in pending:
                    task.cancel()
                
                # If we got a heartbeat, send a comment
                if heartbeat_task in done:
                    yield ": heartbeat\n\n"
                
                # If we got an event, send it
                if event_task in done:
                    event_data = event_task.result()
                    yield format_sse_event(
                        data=event_data["data"],
                        event=event_data["event"]
                    )
        except asyncio.CancelledError:
            # Connection was closed
            logger.info(f"SSE connection closed for repository: {repository}")
        finally:
            # Remove this connection
            if repository in active_connections:
                active_connections[repository].remove(queue)
                if not active_connections[repository]:
                    del active_connections[repository]
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )

def format_sse_event(data: Dict[str, Any], event: Optional[str] = None) -> str:
    """
    Format a server-sent event.
    
    Args:
        data: The data to send
        event: The event type
        
    Returns:
        A formatted SSE event string
    """
    message = f"data: {json.dumps(data)}\n"
    if event:
        message = f"event: {event}\n{message}"
    message += "\n"
    return message

async def broadcast_deployment_update(deployment: Deployment):
    """
    Broadcast a deployment update to all connected clients.
    
    Args:
        deployment: The deployment to broadcast
    """
    repository = deployment.repository_name
    
    if repository not in active_connections:
        return
    
    # Prepare the event data
    event_data = {
        "data": {
            "repository": repository,
            "status": deployment.status.value,
            "url": deployment.url,
            "commit_sha": deployment.commit_sha,
            "author": deployment.author,
            "commit_message": deployment.commit_message,
            "timestamp": datetime.now().isoformat()
        },
        "event": "deployment_update"
    }
    
    # Send to all connected clients for this repository
    for queue in active_connections[repository]:
        await queue.put(event_data)
    
    logger.info(f"Broadcast deployment update for {repository} to {len(active_connections[repository])} clients")
