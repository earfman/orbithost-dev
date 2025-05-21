"""
Enhanced OrbitContext implementation with persistent storage and multi-agent support.

This module extends the base OrbitContext format with:
1. Persistent storage across sessions
2. Relationships between context entries
3. Multi-agent collaboration support
4. MCP compatibility layer
5. Event-sourcing pattern implementation

It maintains backward compatibility with the original OrbitContext format
while adding new capabilities described in the OrbitContext whitepaper.
"""
import datetime
import json
import logging
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union, Tuple

from pydantic import BaseModel, Field, validator

from app.services.orbitbridge.context import (
    OrbitContext, ContextType, SourceType, Severity,
    Screenshot, ErrorLocation, DeploymentInfo, MetricValue, TraceSpan
)
from app.services.orbitbridge.context_store import (
    OrbitContextStore, ContextEntry, EntryType, Relationship,
    get_context_store
)

# Configure logging
logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    """Types of AI agents that can interact with OrbitContext."""
    WINDSURF = "windsurf"
    CLAUDE = "claude"
    CURSOR = "cursor"
    REPLIT = "replit"
    CHATGPT = "chatgpt"
    CUSTOM = "custom"


class RelationshipType(str, Enum):
    """Types of relationships between context entries."""
    CAUSED_BY = "caused_by"
    PART_OF = "part_of"
    RELATED_TO = "related_to"
    DEPENDS_ON = "depends_on"
    REFERENCES = "references"
    FIXED_BY = "fixed_by"
    TRIGGERED_BY = "triggered_by"
    SUMMARIZES = "summarizes"


class Agent(BaseModel):
    """AI agent information."""
    id: str = Field(default_factory=lambda: f"agent-{uuid.uuid4()}")
    type: AgentType
    name: str
    version: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ConversationMessage(BaseModel):
    """Message in a conversation with an AI agent."""
    id: str = Field(default_factory=lambda: f"msg-{uuid.uuid4()}")
    agent_id: Optional[str] = None
    user_id: Optional[str] = None
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    content: str
    role: str  # "user", "assistant", "system", etc.
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Conversation(BaseModel):
    """Conversation with an AI agent."""
    id: str = Field(default_factory=lambda: f"conv-{uuid.uuid4()}")
    agent_id: str
    user_id: Optional[str] = None
    project_id: str
    start_time: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    end_time: Optional[datetime.datetime] = None
    messages: List[ConversationMessage] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class EnhancedOrbitContext(OrbitContext):
    """
    Enhanced OrbitContext with persistent storage and multi-agent support.
    
    This class extends the base OrbitContext with additional capabilities:
    1. Persistent storage across sessions
    2. Relationships between context entries
    3. Multi-agent collaboration support
    4. MCP compatibility layer
    5. Event-sourcing pattern implementation
    
    It maintains backward compatibility with the original OrbitContext format.
    """
    
    # Additional fields for enhanced capabilities
    agent_id: Optional[str] = None
    conversation_id: Optional[str] = None
    parent_context_id: Optional[str] = None
    
    async def store(self) -> str:
        """
        Store this context in the persistent store.
        
        Returns:
            ID of the stored context entry
        """
        store = await get_context_store()
        return await store.store_event(self, self.agent_id)
    
    async def add_relationship(
        self,
        target_context_id: str,
        relationship_type: Union[RelationshipType, str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a relationship from this context to another context.
        
        Args:
            target_context_id: ID of the target context
            relationship_type: Type of relationship
            metadata: Additional metadata for the relationship
            
        Returns:
            ID of the created relationship
        """
        if isinstance(relationship_type, RelationshipType):
            relationship_type = relationship_type.value
            
        store = await get_context_store()
        return await store.create_relationship(
            self.id,
            target_context_id,
            relationship_type,
            metadata,
        )
    
    async def get_related_contexts(
        self,
        relationship_type: Optional[Union[RelationshipType, str]] = None,
        direction: str = "outgoing",
    ) -> List[Tuple[str, "EnhancedOrbitContext"]]:
        """
        Get contexts related to this context.
        
        Args:
            relationship_type: Filter by relationship type
            direction: "outgoing", "incoming", or "both"
            
        Returns:
            List of (relationship_type, context) tuples
        """
        if isinstance(relationship_type, RelationshipType):
            relationship_type = relationship_type.value
            
        store = await get_context_store()
        related_entries = await store.get_related_entries(
            self.id,
            relationship_type,
            direction,
        )
        
        result = []
        for rel_type, entry in related_entries:
            if entry.entry_type == EntryType.EVENT:
                context_dict = entry.content
                context = EnhancedOrbitContext.from_dict(context_dict)
                result.append((rel_type, context))
        
        return result
    
    @classmethod
    async def get_by_id(cls, context_id: str) -> Optional["EnhancedOrbitContext"]:
        """
        Get a context by ID from the persistent store.
        
        Args:
            context_id: Context ID
            
        Returns:
            EnhancedOrbitContext if found, None otherwise
        """
        store = await get_context_store()
        entry = await store.get_entry(context_id)
        
        if not entry or entry.entry_type != EntryType.EVENT:
            return None
        
        return cls.from_dict(entry.content)
    
    @classmethod
    async def search(
        cls,
        project_id: str,
        query: str,
        tags: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List["EnhancedOrbitContext"]:
        """
        Search for contexts.
        
        Args:
            project_id: Project ID
            query: Search query
            tags: Filter by tags
            limit: Maximum number of results
            
        Returns:
            List of matching contexts
        """
        store = await get_context_store()
        entries = await store.search_entries(
            project_id,
            query,
            [EntryType.EVENT],
            tags,
            limit,
        )
        
        return [cls.from_dict(entry.content) for entry in entries]
    
    @classmethod
    async def get_project_contexts(
        cls,
        project_id: str,
        context_type: Optional[ContextType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List["EnhancedOrbitContext"]:
        """
        Get contexts for a project.
        
        Args:
            project_id: Project ID
            context_type: Filter by context type
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of contexts
        """
        store = await get_context_store()
        entries = await store.get_entries_by_project(
            project_id,
            EntryType.EVENT,
            limit,
            offset,
        )
        
        contexts = [cls.from_dict(entry.content) for entry in entries]
        
        if context_type:
            contexts = [ctx for ctx in contexts if ctx.type == context_type]
        
        return contexts
    
    def to_mcp_format(self) -> Dict[str, Any]:
        """
        Convert to MCP-compatible format.
        
        Returns:
            MCP-compatible dictionary
        """
        # Basic MCP structure
        mcp_data = {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.type.value,
            "source": self.source.value,
            "project": {
                "id": self.project_id,
                "environment": self.environment,
            },
            "metadata": self.metadata.copy(),
            "tags": self.tags.copy(),
        }
        
        # Add user if present
        if self.user_id:
            mcp_data["user"] = {"id": self.user_id}
        
        # Add agent if present
        if self.agent_id:
            mcp_data["agent"] = {"id": self.agent_id}
        
        # Add conversation if present
        if self.conversation_id:
            mcp_data["conversation"] = {"id": self.conversation_id}
        
        # Add content based on context type
        if self.type == ContextType.DEPLOYMENT and self.deployment:
            mcp_data["content"] = {
                "deployment": {
                    "id": self.deployment.id,
                    "branch": self.deployment.branch,
                    "commit": {
                        "hash": self.deployment.commit_hash,
                        "message": self.deployment.commit_message,
                        "author": self.deployment.author,
                    },
                    "status": self.deployment.status,
                    "duration": self.deployment.duration_seconds,
                    "url": self.deployment.url,
                    "logs_url": self.deployment.logs_url,
                }
            }
        elif self.type == ContextType.ERROR and self.error:
            mcp_data["content"] = {
                "error": self.error.copy(),
                "location": self.error_location.dict(exclude_none=True) if self.error_location else None,
            }
        elif self.type == ContextType.SCREENSHOT and self.screenshot:
            mcp_data["content"] = {
                "screenshot": self.screenshot.dict(),
            }
        elif self.type == ContextType.LOG and self.log_message:
            mcp_data["content"] = {
                "log": {
                    "message": self.log_message,
                    "severity": self.log_severity.value if self.log_severity else None,
                }
            }
        elif self.type == ContextType.METRIC and self.metric:
            mcp_data["content"] = {
                "metric": self.metric.dict(),
            }
        elif self.type == ContextType.TRACE and self.trace:
            mcp_data["content"] = {
                "trace": self.trace.dict(),
            }
        
        return mcp_data
    
    @classmethod
    async def create_deployment_context(
        cls,
        project_id: str,
        deployment_id: str,
        environment: str,
        branch: str,
        commit_hash: str,
        status: str,
        duration_seconds: float,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        commit_message: Optional[str] = None,
        author: Optional[str] = None,
        url: Optional[str] = None,
        logs_url: Optional[str] = None,
        build_command: Optional[str] = None,
        deploy_command: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        store: bool = True,
    ) -> "EnhancedOrbitContext":
        """
        Create and optionally store a deployment context.
        
        Args:
            project_id: Project ID
            deployment_id: Deployment ID
            environment: Environment (e.g., "production", "staging")
            branch: Git branch
            commit_hash: Git commit hash
            status: Deployment status
            duration_seconds: Deployment duration in seconds
            user_id: User ID
            agent_id: Agent ID
            commit_message: Git commit message
            author: Git commit author
            url: Deployment URL
            logs_url: Deployment logs URL
            build_command: Build command
            deploy_command: Deploy command
            metadata: Additional metadata
            tags: Tags
            store: Whether to store the context
            
        Returns:
            Created context
        """
        # Create base context
        context = await super().create_deployment_context(
            project_id=project_id,
            deployment_id=deployment_id,
            environment=environment,
            branch=branch,
            commit_hash=commit_hash,
            status=status,
            duration_seconds=duration_seconds,
            user_id=user_id,
            commit_message=commit_message,
            author=author,
            url=url,
            logs_url=logs_url,
            build_command=build_command,
            deploy_command=deploy_command,
            metadata=metadata or {},
            tags=tags or [],
        )
        
        # Convert to enhanced context
        enhanced_context = cls(**context.dict())
        enhanced_context.agent_id = agent_id
        
        # Store if requested
        if store:
            await enhanced_context.store()
        
        return enhanced_context
    
    @classmethod
    async def create_error_context(
        cls,
        project_id: str,
        environment: str,
        error_message: str,
        error_type: str,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        deployment_id: Optional[str] = None,
        file: Optional[str] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
        function: Optional[str] = None,
        stack_trace: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        store: bool = True,
    ) -> "EnhancedOrbitContext":
        """
        Create and optionally store an error context.
        
        Args:
            project_id: Project ID
            environment: Environment (e.g., "production", "staging")
            error_message: Error message
            error_type: Error type
            user_id: User ID
            agent_id: Agent ID
            deployment_id: Related deployment ID
            file: File where the error occurred
            line: Line number
            column: Column number
            function: Function name
            stack_trace: Stack trace
            metadata: Additional metadata
            tags: Tags
            store: Whether to store the context
            
        Returns:
            Created context
        """
        # Create base context
        context = await super().create_error_context(
            project_id=project_id,
            environment=environment,
            error_message=error_message,
            error_type=error_type,
            user_id=user_id,
            file=file,
            line=line,
            column=column,
            function=function,
            stack_trace=stack_trace,
            metadata=metadata or {},
            tags=tags or [],
        )
        
        # Convert to enhanced context
        enhanced_context = cls(**context.dict())
        enhanced_context.agent_id = agent_id
        
        # Store if requested
        if store:
            context_id = await enhanced_context.store()
            
            # Create relationship to deployment if provided
            if deployment_id:
                await enhanced_context.add_relationship(
                    deployment_id,
                    RelationshipType.CAUSED_BY,
                    {"automatic": True},
                )
        
        return enhanced_context
    
    # Similar enhanced methods for other context types...
    # Implementation would follow the same pattern as above
    
    @classmethod
    async def create_conversation_context(
        cls,
        project_id: str,
        environment: str,
        agent_id: str,
        agent_type: AgentType,
        agent_name: str,
        conversation: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        store: bool = True,
    ) -> "EnhancedOrbitContext":
        """
        Create and optionally store a conversation context.
        
        Args:
            project_id: Project ID
            environment: Environment (e.g., "production", "staging")
            agent_id: Agent ID
            agent_type: Agent type
            agent_name: Agent name
            conversation: List of conversation messages
            user_id: User ID
            metadata: Additional metadata
            tags: Tags
            store: Whether to store the context
            
        Returns:
            Created context
        """
        # Create conversation object
        conv = Conversation(
            id=f"conv-{uuid.uuid4()}",
            agent_id=agent_id,
            user_id=user_id,
            project_id=project_id,
            start_time=datetime.datetime.utcnow(),
            messages=[ConversationMessage(**msg) for msg in conversation],
            metadata=metadata or {},
            tags=tags or [],
        )
        
        # Create context
        context = cls(
            type=ContextType.FEEDBACK,  # Using FEEDBACK for conversations
            source=SourceType.EXTERNAL,
            project_id=project_id,
            user_id=user_id,
            environment=environment,
            agent_id=agent_id,
            conversation_id=conv.id,
            metadata={
                "conversation": conv.dict(exclude={"messages"}),
                "agent": {
                    "id": agent_id,
                    "type": agent_type.value,
                    "name": agent_name,
                },
                "messages": [msg.dict() for msg in conv.messages],
            },
            tags=tags or [],
        )
        
        # Store if requested
        if store:
            await context.store()
        
        return context


# Convenience functions for working with enhanced context

async def get_project_contexts(
    project_id: str,
    context_type: Optional[ContextType] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[EnhancedOrbitContext]:
    """
    Get contexts for a project.
    
    Args:
        project_id: Project ID
        context_type: Filter by context type
        limit: Maximum number of results
        offset: Offset for pagination
        
    Returns:
        List of contexts
    """
    return await EnhancedOrbitContext.get_project_contexts(
        project_id,
        context_type,
        limit,
        offset,
    )


async def search_contexts(
    project_id: str,
    query: str,
    tags: Optional[List[str]] = None,
    limit: int = 10,
) -> List[EnhancedOrbitContext]:
    """
    Search for contexts.
    
    Args:
        project_id: Project ID
        query: Search query
        tags: Filter by tags
        limit: Maximum number of results
        
    Returns:
        List of matching contexts
    """
    return await EnhancedOrbitContext.search(
        project_id,
        query,
        tags,
        limit,
    )


async def get_context_by_id(context_id: str) -> Optional[EnhancedOrbitContext]:
    """
    Get a context by ID.
    
    Args:
        context_id: Context ID
        
    Returns:
        Context if found, None otherwise
    """
    return await EnhancedOrbitContext.get_by_id(context_id)


async def create_artifact(
    project_id: str,
    name: str,
    content: Dict[str, Any],
    user_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> str:
    """
    Create an artifact.
    
    Args:
        project_id: Project ID
        name: Artifact name
        content: Artifact content
        user_id: User ID
        agent_id: Agent ID
        tags: Tags
        
    Returns:
        Artifact ID
    """
    store = await get_context_store()
    return await store.store_artifact(
        project_id,
        name,
        content,
        user_id,
        agent_id,
        tags,
    )


async def get_artifact(
    project_id: str,
    name: str,
    version: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    """
    Get an artifact.
    
    Args:
        project_id: Project ID
        name: Artifact name
        version: Artifact version (if None, get the latest version)
        
    Returns:
        Artifact content if found, None otherwise
    """
    store = await get_context_store()
    artifact = await store.get_artifact_by_name(
        project_id,
        name,
        version,
    )
    
    if not artifact:
        return None
    
    return artifact.content.get("data", {})
