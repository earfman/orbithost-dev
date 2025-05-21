"""
API endpoints for OrbitContext management and AI tool integration.

These endpoints provide a RESTful API for creating, retrieving, and searching
OrbitContext entries, as well as integrating with AI tools like Windsurf,
Claude, Replit, and Cursor.
"""
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field

from app.services.orbitbridge.enhanced_context import (
    EnhancedOrbitContext, ContextType, SourceType, AgentType, RelationshipType,
    get_context_by_id, get_project_contexts, search_contexts, create_artifact, get_artifact
)
from app.services.orbitbridge.context_store import get_context_store
from app.db.dependencies import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/context",
    tags=["context"],
    responses={404: {"description": "Not found"}},
)


# Request and response models
class ContextResponse(BaseModel):
    """Response model for context entries."""
    id: str
    type: str
    source: str
    timestamp: str
    project_id: str
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    environment: str
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    tags: List[str]


class CreateRelationshipRequest(BaseModel):
    """Request model for creating relationships."""
    source_id: str
    target_id: str
    relationship_type: str
    metadata: Optional[Dict[str, Any]] = None


class CreateDeploymentContextRequest(BaseModel):
    """Request model for creating deployment contexts."""
    project_id: str
    deployment_id: str
    environment: str
    branch: str
    commit_hash: str
    status: str
    duration_seconds: float
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    commit_message: Optional[str] = None
    author: Optional[str] = None
    url: Optional[str] = None
    logs_url: Optional[str] = None
    build_command: Optional[str] = None
    deploy_command: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class CreateErrorContextRequest(BaseModel):
    """Request model for creating error contexts."""
    project_id: str
    environment: str
    error_message: str
    error_type: str
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    deployment_id: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    function: Optional[str] = None
    stack_trace: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class CreateArtifactRequest(BaseModel):
    """Request model for creating artifacts."""
    project_id: str
    name: str
    content: Dict[str, Any]
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    tags: Optional[List[str]] = None


class CreateConversationContextRequest(BaseModel):
    """Request model for creating conversation contexts."""
    project_id: str
    environment: str
    agent_id: str
    agent_type: str
    agent_name: str
    conversation: List[Dict[str, Any]]
    user_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class MCPContextRequest(BaseModel):
    """Request model for MCP-compatible context."""
    id: Optional[str] = None
    timestamp: Optional[str] = None
    type: str
    source: str
    project: Dict[str, Any]
    user: Optional[Dict[str, Any]] = None
    agent: Optional[Dict[str, Any]] = None
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class SearchRequest(BaseModel):
    """Request model for searching contexts."""
    project_id: str
    query: str
    tags: Optional[List[str]] = None
    limit: Optional[int] = 10


# Helper functions
def _context_to_response(context: EnhancedOrbitContext) -> ContextResponse:
    """Convert a context to a response model."""
    content = {}
    
    if context.type == ContextType.DEPLOYMENT and context.deployment:
        content["deployment"] = context.deployment.dict()
    elif context.type == ContextType.ERROR and context.error:
        content["error"] = context.error
        if context.error_location:
            content["error_location"] = context.error_location.dict()
    elif context.type == ContextType.SCREENSHOT and context.screenshot:
        content["screenshot"] = context.screenshot.dict()
    elif context.type == ContextType.LOG and context.log_message:
        content["log"] = {
            "message": context.log_message,
            "severity": context.log_severity.value if context.log_severity else None,
        }
    elif context.type == ContextType.METRIC and context.metric:
        content["metric"] = context.metric.dict()
    elif context.type == ContextType.TRACE and context.trace:
        content["trace"] = context.trace.dict()
    
    return ContextResponse(
        id=context.id,
        type=context.type.value,
        source=context.source.value,
        timestamp=context.timestamp.isoformat(),
        project_id=context.project_id,
        user_id=context.user_id,
        agent_id=context.agent_id,
        environment=context.environment,
        content=content,
        metadata=context.metadata,
        tags=context.tags,
    )


# API endpoints
@router.get("/{context_id}", response_model=ContextResponse)
async def get_context(context_id: str):
    """Get a context by ID."""
    context = await get_context_by_id(context_id)
    
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")
    
    return _context_to_response(context)


@router.get("/project/{project_id}", response_model=List[ContextResponse])
async def get_contexts_for_project(
    project_id: str,
    context_type: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """Get contexts for a project."""
    context_type_enum = None
    if context_type:
        try:
            context_type_enum = ContextType(context_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid context type: {context_type}")
    
    contexts = await get_project_contexts(
        project_id,
        context_type_enum,
        limit,
        offset,
    )
    
    return [_context_to_response(context) for context in contexts]


@router.post("/search", response_model=List[ContextResponse])
async def search(request: SearchRequest):
    """Search for contexts."""
    contexts = await search_contexts(
        request.project_id,
        request.query,
        request.tags,
        request.limit or 10,
    )
    
    return [_context_to_response(context) for context in contexts]


@router.post("/relationship", response_model=Dict[str, Any])
async def create_relationship(request: CreateRelationshipRequest):
    """Create a relationship between contexts."""
    try:
        # Get the source context
        source_context = await get_context_by_id(request.source_id)
        if not source_context:
            raise HTTPException(status_code=404, detail=f"Source context not found: {request.source_id}")
        
        # Get the target context
        target_context = await get_context_by_id(request.target_id)
        if not target_context:
            raise HTTPException(status_code=404, detail=f"Target context not found: {request.target_id}")
        
        # Create the relationship
        relationship_id = await source_context.add_relationship(
            request.target_id,
            request.relationship_type,
            request.metadata,
        )
        
        return {
            "id": relationship_id,
            "source_id": request.source_id,
            "target_id": request.target_id,
            "relationship_type": request.relationship_type,
        }
    except Exception as e:
        logger.error(f"Error creating relationship: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating relationship: {str(e)}")


@router.get("/{context_id}/related", response_model=List[ContextResponse])
async def get_related_contexts(
    context_id: str,
    relationship_type: Optional[str] = None,
    direction: str = Query("outgoing", regex="^(outgoing|incoming|both)$"),
):
    """Get contexts related to a context."""
    context = await get_context_by_id(context_id)
    
    if not context:
        raise HTTPException(status_code=404, detail="Context not found")
    
    related = await context.get_related_contexts(relationship_type, direction)
    
    return [_context_to_response(related_context) for _, related_context in related]


@router.post("/deployment", response_model=ContextResponse)
async def create_deployment_context(request: CreateDeploymentContextRequest):
    """Create a deployment context."""
    try:
        context = await EnhancedOrbitContext.create_deployment_context(
            project_id=request.project_id,
            deployment_id=request.deployment_id,
            environment=request.environment,
            branch=request.branch,
            commit_hash=request.commit_hash,
            status=request.status,
            duration_seconds=request.duration_seconds,
            user_id=request.user_id,
            agent_id=request.agent_id,
            commit_message=request.commit_message,
            author=request.author,
            url=request.url,
            logs_url=request.logs_url,
            build_command=request.build_command,
            deploy_command=request.deploy_command,
            metadata=request.metadata,
            tags=request.tags,
            store=True,
        )
        
        return _context_to_response(context)
    except Exception as e:
        logger.error(f"Error creating deployment context: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating deployment context: {str(e)}")


@router.post("/error", response_model=ContextResponse)
async def create_error_context(request: CreateErrorContextRequest):
    """Create an error context."""
    try:
        context = await EnhancedOrbitContext.create_error_context(
            project_id=request.project_id,
            environment=request.environment,
            error_message=request.error_message,
            error_type=request.error_type,
            user_id=request.user_id,
            agent_id=request.agent_id,
            deployment_id=request.deployment_id,
            file=request.file,
            line=request.line,
            column=request.column,
            function=request.function,
            stack_trace=request.stack_trace,
            metadata=request.metadata,
            tags=request.tags,
            store=True,
        )
        
        return _context_to_response(context)
    except Exception as e:
        logger.error(f"Error creating error context: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating error context: {str(e)}")


@router.post("/artifact", response_model=Dict[str, Any])
async def create_artifact_endpoint(request: CreateArtifactRequest):
    """Create an artifact."""
    try:
        artifact_id = await create_artifact(
            project_id=request.project_id,
            name=request.name,
            content=request.content,
            user_id=request.user_id,
            agent_id=request.agent_id,
            tags=request.tags,
        )
        
        return {
            "id": artifact_id,
            "project_id": request.project_id,
            "name": request.name,
        }
    except Exception as e:
        logger.error(f"Error creating artifact: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating artifact: {str(e)}")


@router.get("/artifact/{project_id}/{name}", response_model=Dict[str, Any])
async def get_artifact_endpoint(
    project_id: str,
    name: str,
    version: Optional[int] = None,
):
    """Get an artifact."""
    artifact = await get_artifact(project_id, name, version)
    
    if not artifact:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {name}")
    
    return artifact


@router.post("/conversation", response_model=ContextResponse)
async def create_conversation_context(request: CreateConversationContextRequest):
    """Create a conversation context."""
    try:
        # Convert string agent type to enum
        try:
            agent_type = AgentType(request.agent_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid agent type: {request.agent_type}")
        
        context = await EnhancedOrbitContext.create_conversation_context(
            project_id=request.project_id,
            environment=request.environment,
            agent_id=request.agent_id,
            agent_type=agent_type,
            agent_name=request.agent_name,
            conversation=request.conversation,
            user_id=request.user_id,
            metadata=request.metadata,
            tags=request.tags,
            store=True,
        )
        
        return _context_to_response(context)
    except Exception as e:
        logger.error(f"Error creating conversation context: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating conversation context: {str(e)}")


# AI tool integration endpoints
@router.post("/mcp", response_model=ContextResponse)
async def create_mcp_context(request: MCPContextRequest):
    """Create a context from MCP format."""
    try:
        # Extract project info
        project_id = request.project.get("id")
        if not project_id:
            raise HTTPException(status_code=400, detail="Missing project ID")
        
        environment = request.project.get("environment", "production")
        
        # Extract user info
        user_id = None
        if request.user:
            user_id = request.user.get("id")
        
        # Extract agent info
        agent_id = None
        if request.agent:
            agent_id = request.agent.get("id")
        
        # Convert MCP type to OrbitContext type
        try:
            context_type = ContextType(request.type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid context type: {request.type}")
        
        # Convert MCP source to OrbitContext source
        try:
            source_type = SourceType(request.source)
        except ValueError:
            source_type = SourceType.EXTERNAL
        
        # Create base context
        context = EnhancedOrbitContext(
            id=request.id or f"ctx-{uuid.uuid4()}",
            type=context_type,
            source=source_type,
            timestamp=datetime.datetime.fromisoformat(request.timestamp) if request.timestamp else datetime.datetime.utcnow(),
            project_id=project_id,
            user_id=user_id,
            agent_id=agent_id,
            environment=environment,
            metadata=request.metadata or {},
            tags=request.tags or [],
        )
        
        # Add content based on type
        if context_type == ContextType.DEPLOYMENT and "deployment" in request.content:
            deployment_data = request.content["deployment"]
            context.deployment = DeploymentInfo(
                id=deployment_data.get("id", f"deploy-{uuid.uuid4()}"),
                project_id=project_id,
                environment=environment,
                branch=deployment_data.get("branch", "main"),
                commit_hash=deployment_data.get("commit", {}).get("hash", ""),
                commit_message=deployment_data.get("commit", {}).get("message"),
                author=deployment_data.get("commit", {}).get("author"),
                timestamp=datetime.datetime.fromisoformat(deployment_data.get("timestamp", context.timestamp.isoformat())),
                status=deployment_data.get("status", "unknown"),
                duration_seconds=float(deployment_data.get("duration", 0)),
                url=deployment_data.get("url"),
                logs_url=deployment_data.get("logs_url"),
            )
        elif context_type == ContextType.ERROR and "error" in request.content:
            error_data = request.content["error"]
            context.error = error_data
            
            if "location" in request.content:
                location_data = request.content["location"]
                context.error_location = ErrorLocation(
                    file=location_data.get("file"),
                    line=location_data.get("line"),
                    column=location_data.get("column"),
                    function=location_data.get("function"),
                    stack_trace=location_data.get("stack_trace"),
                )
        
        # Store the context
        await context.store()
        
        return _context_to_response(context)
    except Exception as e:
        logger.error(f"Error creating MCP context: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating MCP context: {str(e)}")


@router.post("/windsurf/webhook", response_model=Dict[str, Any])
async def windsurf_webhook(data: Dict[str, Any] = Body(...)):
    """Webhook for receiving context from Windsurf."""
    try:
        # Extract context data
        context_data = data.get("context", {})
        
        # Convert to MCP format if needed
        if "mcp_version" not in context_data:
            # This is not MCP format, so convert it
            project_id = context_data.get("project_id")
            if not project_id:
                raise HTTPException(status_code=400, detail="Missing project ID")
            
            context_type = context_data.get("type")
            if not context_type:
                raise HTTPException(status_code=400, detail="Missing context type")
            
            # Create MCP-compatible format
            mcp_data = {
                "id": context_data.get("id"),
                "timestamp": context_data.get("timestamp"),
                "type": context_type,
                "source": context_data.get("source", "windsurf"),
                "project": {
                    "id": project_id,
                    "environment": context_data.get("environment", "development"),
                },
                "content": context_data.get("content", {}),
                "metadata": context_data.get("metadata", {}),
                "tags": context_data.get("tags", []),
            }
            
            # Add user if present
            if "user_id" in context_data:
                mcp_data["user"] = {"id": context_data["user_id"]}
            
            # Add agent if present
            if "agent_id" in context_data:
                mcp_data["agent"] = {"id": context_data["agent_id"]}
            
            context_data = mcp_data
        
        # Create context from MCP format
        request = MCPContextRequest(**context_data)
        context = await create_mcp_context(request)
        
        return {"status": "success", "context_id": context.id}
    except Exception as e:
        logger.error(f"Error processing Windsurf webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing Windsurf webhook: {str(e)}")


@router.post("/claude/webhook", response_model=Dict[str, Any])
async def claude_webhook(data: Dict[str, Any] = Body(...)):
    """Webhook for receiving context from Claude."""
    try:
        # Extract context data
        conversation = data.get("conversation", [])
        if not conversation:
            raise HTTPException(status_code=400, detail="Missing conversation data")
        
        project_id = data.get("project_id")
        if not project_id:
            raise HTTPException(status_code=400, detail="Missing project ID")
        
        # Create conversation context
        request = CreateConversationContextRequest(
            project_id=project_id,
            environment=data.get("environment", "development"),
            agent_id=data.get("agent_id", "claude"),
            agent_type="claude",
            agent_name=data.get("agent_name", "Claude"),
            conversation=conversation,
            user_id=data.get("user_id"),
            metadata=data.get("metadata", {}),
            tags=data.get("tags", []),
        )
        
        context = await create_conversation_context(request)
        
        return {"status": "success", "context_id": context.id}
    except Exception as e:
        logger.error(f"Error processing Claude webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing Claude webhook: {str(e)}")


@router.post("/replit/webhook", response_model=Dict[str, Any])
async def replit_webhook(data: Dict[str, Any] = Body(...)):
    """Webhook for receiving context from Replit."""
    # Similar implementation to Claude webhook
    try:
        # Extract context data
        project_id = data.get("project_id")
        if not project_id:
            raise HTTPException(status_code=400, detail="Missing project ID")
        
        # Handle different types of Replit events
        event_type = data.get("event_type")
        
        if event_type == "code_execution":
            # Handle code execution event
            execution_data = data.get("execution", {})
            
            # Create artifact for code execution
            artifact_request = CreateArtifactRequest(
                project_id=project_id,
                name=f"code_execution_{execution_data.get('id', uuid.uuid4())}",
                content={
                    "code": execution_data.get("code", ""),
                    "language": execution_data.get("language", ""),
                    "result": execution_data.get("result", ""),
                    "status": execution_data.get("status", ""),
                    "timestamp": execution_data.get("timestamp", datetime.datetime.utcnow().isoformat()),
                },
                user_id=data.get("user_id"),
                agent_id=data.get("agent_id", "replit"),
                tags=["replit", "code_execution"] + data.get("tags", []),
            )
            
            artifact_id = await create_artifact_endpoint(artifact_request)
            
            return {"status": "success", "artifact_id": artifact_id["id"]}
        elif event_type == "conversation":
            # Handle conversation event
            conversation = data.get("conversation", [])
            
            request = CreateConversationContextRequest(
                project_id=project_id,
                environment=data.get("environment", "development"),
                agent_id=data.get("agent_id", "replit"),
                agent_type="replit",
                agent_name=data.get("agent_name", "Replit"),
                conversation=conversation,
                user_id=data.get("user_id"),
                metadata=data.get("metadata", {}),
                tags=["replit", "conversation"] + data.get("tags", []),
            )
            
            context = await create_conversation_context(request)
            
            return {"status": "success", "context_id": context.id}
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported event type: {event_type}")
    except Exception as e:
        logger.error(f"Error processing Replit webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing Replit webhook: {str(e)}")


@router.post("/cursor/webhook", response_model=Dict[str, Any])
async def cursor_webhook(data: Dict[str, Any] = Body(...)):
    """Webhook for receiving context from Cursor."""
    # Similar implementation to other webhooks
    try:
        # Extract context data
        project_id = data.get("project_id")
        if not project_id:
            raise HTTPException(status_code=400, detail="Missing project ID")
        
        # Handle different types of Cursor events
        event_type = data.get("event_type")
        
        if event_type == "code_edit":
            # Handle code edit event
            edit_data = data.get("edit", {})
            
            # Create artifact for code edit
            artifact_request = CreateArtifactRequest(
                project_id=project_id,
                name=f"code_edit_{edit_data.get('file', 'unknown')}",
                content={
                    "file": edit_data.get("file", ""),
                    "changes": edit_data.get("changes", []),
                    "timestamp": edit_data.get("timestamp", datetime.datetime.utcnow().isoformat()),
                },
                user_id=data.get("user_id"),
                agent_id=data.get("agent_id", "cursor"),
                tags=["cursor", "code_edit"] + data.get("tags", []),
            )
            
            artifact_id = await create_artifact_endpoint(artifact_request)
            
            return {"status": "success", "artifact_id": artifact_id["id"]}
        elif event_type == "conversation":
            # Handle conversation event
            conversation = data.get("conversation", [])
            
            request = CreateConversationContextRequest(
                project_id=project_id,
                environment=data.get("environment", "development"),
                agent_id=data.get("agent_id", "cursor"),
                agent_type="cursor",
                agent_name=data.get("agent_name", "Cursor"),
                conversation=conversation,
                user_id=data.get("user_id"),
                metadata=data.get("metadata", {}),
                tags=["cursor", "conversation"] + data.get("tags", []),
            )
            
            context = await create_conversation_context(request)
            
            return {"status": "success", "context_id": context.id}
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported event type: {event_type}")
    except Exception as e:
        logger.error(f"Error processing Cursor webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing Cursor webhook: {str(e)}")
