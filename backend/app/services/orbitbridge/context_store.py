"""
OrbitContext persistent store implementation.

This module provides a persistent store for OrbitContext data, implementing
the event-sourcing pattern described in the OrbitContext whitepaper. It allows
for storing, retrieving, and querying context entries across sessions and agents.
"""
import datetime
import json
import logging
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union, Tuple

import asyncpg
import json
import datetime
from pydantic import BaseModel, Field, validator
from app.db.supabase_client import get_supabase_client

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)

from app.services.orbitbridge.context import OrbitContext, ContextType, SourceType

# Configure logging
logger = logging.getLogger(__name__)


class EntryType(str, Enum):
    """Types of OrbitContext store entries."""
    EVENT = "event"  # Immutable event that happened (e.g., deployment, error)
    ARTIFACT = "artifact"  # Versioned artifact (e.g., code file, config)
    SUMMARY = "summary"  # Compressed/summarized older events


class Relationship(BaseModel):
    """Relationship between context entries."""
    source_id: str
    target_id: str
    relationship_type: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ContextEntry(BaseModel):
    """
    Entry in the OrbitContext store.
    
    This represents either an event, artifact, or summary in the context store.
    """
    id: str = Field(default_factory=lambda: f"entry-{uuid.uuid4()}")
    entry_type: EntryType
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    agent_id: Optional[str] = None  # ID of the agent that created this entry
    project_id: str
    user_id: Optional[str] = None
    content: Dict[str, Any]  # The actual context data
    vector_embedding: Optional[List[float]] = None  # For semantic search
    tags: List[str] = Field(default_factory=list)
    
    # For artifacts only
    version: Optional[int] = None
    parent_version_id: Optional[str] = None
    
    # For summaries only
    summarized_entry_ids: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.dict(exclude_none=True)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(
            self.dict(exclude_none=True),
            default=lambda o: o.isoformat() if isinstance(o, datetime.datetime) else None
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContextEntry":
        """Create from dictionary."""
        # Convert string timestamps to datetime objects
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "ContextEntry":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    @classmethod
    def from_orbit_context(cls, context: OrbitContext, agent_id: Optional[str] = None) -> "ContextEntry":
        """Create a context entry from an OrbitContext object."""
        return cls(
            entry_type=EntryType.EVENT,
            agent_id=agent_id,
            project_id=context.project_id,
            user_id=context.user_id,
            content=context.to_dict(),
            tags=context.tags,
        )


class OrbitContextStore:
    """
    Persistent store for OrbitContext data.
    
    This class provides methods for storing, retrieving, and querying
    context entries across sessions and agents. It implements the
    event-sourcing pattern described in the OrbitContext whitepaper.
    """
    
    def __init__(self):
        """
        Initialize the OrbitContext store.
        """
        self.supabase_client = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize the store."""
        if self.initialized:
            return
        
        try:
            self.supabase_client = await get_supabase_client()
            self.initialized = True
            logger.info("OrbitContextStore initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize OrbitContextStore: {str(e)}")
            raise
    
    async def store_event(self, context: OrbitContext, agent_id: Optional[str] = None) -> str:
        """
        Store an event in the context store.
        
        Args:
            context: OrbitContext object
            agent_id: ID of the agent that created this event
            
        Returns:
            ID of the stored event
        """
        await self.initialize()
        
        entry = ContextEntry.from_orbit_context(context, agent_id)
        
        try:
            # Convert context to dict and serialize with custom encoder
            context_dict = context.dict()
            context_json = json.dumps(context_dict, cls=DateTimeEncoder)
            context_data = json.loads(context_json)  # Convert back to dict with serialized datetimes
            
            result = self.supabase_client.table("orbit_context_entries").insert(
                {
                    # Let Supabase generate the UUID
                    "context_id": context.id,
                    "project_id": context.project_id,
                    "agent_id": agent_id,
                    "context_type": context.type,
                    "source_type": context.source,
                    "content": context_data,
                    "metadata": context.metadata,
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                }
            ).execute()
            
            entry_id = result.data[0]["id"]
            logger.info(f"Stored event {entry_id} in OrbitContextStore")
            
            return entry_id
        except Exception as e:
            logger.error(f"Failed to store event in OrbitContextStore: {str(e)}")
            raise
    
    async def store_artifact(
        self,
        project_id: str,
        name: str,
        content: Dict[str, Any],
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Store an artifact in the context store.
        
        Args:
            project_id: Project ID
            name: Artifact name
            content: Artifact content
            user_id: User ID
            agent_id: Agent ID
            tags: Tags
            
        Returns:
            ID of the stored artifact
        """
        await self.initialize()
        
        # Get the latest version of this artifact if it exists
        latest_version = await self._get_latest_artifact_version(project_id, name)
        
        version = 1
        parent_version_id = None
        
        if latest_version:
            version = latest_version["version"] + 1
            parent_version_id = latest_version["id"]
        
        entry = ContextEntry(
            entry_type=EntryType.ARTIFACT,
            agent_id=agent_id,
            project_id=project_id,
            user_id=user_id,
            content={
                "name": name,
                "data": content,
            },
            version=version,
            parent_version_id=parent_version_id,
            tags=tags or [],
        )
        
        try:
            result = self.supabase_client.table("orbit_context_entries").insert(
                entry.to_dict()
            ).execute()
            
            entry_id = result.data[0]["id"]
            logger.info(f"Stored artifact {name} (version {version}) as {entry_id} in OrbitContextStore")
            
            return entry_id
        except Exception as e:
            logger.error(f"Failed to store artifact in OrbitContextStore: {str(e)}")
            raise
    
    async def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a relationship between two context entries.
        
        Args:
            source_id: Source entry ID
            target_id: Target entry ID
            relationship_type: Type of relationship
            metadata: Relationship metadata
            
        Returns:
            ID of the created relationship
        """
        await self.initialize()
        
        relationship = Relationship(
            source_id=source_id,
            target_id=target_id,
            relationship_type=relationship_type,
            metadata=metadata or {},
        )
        
        try:
            result = self.supabase_client.table("orbit_context_relationships").insert(
                relationship.dict()
            ).execute()
            
            relationship_id = result.data[0]["id"]
            logger.info(f"Created relationship {relationship_type} from {source_id} to {target_id}")
            
            return relationship_id
        except Exception as e:
            logger.error(f"Failed to create relationship in OrbitContextStore: {str(e)}")
            raise
    
    async def get_entry(self, entry_id: str) -> Optional[ContextEntry]:
        """
        Get a context entry by ID.
        
        Args:
            entry_id: Entry ID
            
        Returns:
            Context entry if found, None otherwise
        """
        await self.initialize()
        
        try:
            result = self.supabase_client.table("orbit_context_entries").select("*").eq("id", entry_id).execute()
            
            if not result.data:
                return None
            
            return ContextEntry.from_dict(result.data[0])
        except Exception as e:
            logger.error(f"Failed to get entry {entry_id} from OrbitContextStore: {str(e)}")
            raise
    
    async def get_entries_by_project(
        self,
        project_id: str,
        entry_type: Optional[EntryType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[ContextEntry]:
        """
        Get context entries for a project.
        
        Args:
            project_id: Project ID
            entry_type: Filter by entry type
            limit: Maximum number of entries to return
            offset: Offset for pagination
            
        Returns:
            List of context entries
        """
        await self.initialize()
        
        try:
            query = self.supabase_client.table("orbit_context_entries").select("*").eq("project_id", project_id)
            
            if entry_type:
                query = query.eq("entry_type", entry_type)
            
            query = query.order("timestamp", desc=True).limit(limit).offset(offset)
            
            result = query.execute()
            
            return [ContextEntry.from_dict(entry) for entry in result.data]
        except Exception as e:
            logger.error(f"Failed to get entries for project {project_id} from OrbitContextStore: {str(e)}")
            raise
    
    async def get_artifact_by_name(
        self,
        project_id: str,
        name: str,
        version: Optional[int] = None,
    ) -> Optional[ContextEntry]:
        """
        Get an artifact by name.
        
        Args:
            project_id: Project ID
            name: Artifact name
            version: Artifact version (if None, get the latest version)
            
        Returns:
            Artifact entry if found, None otherwise
        """
        await self.initialize()
        
        try:
            query = self.supabase_client.table("orbit_context_entries").select("*").eq("project_id", project_id).eq("entry_type", EntryType.ARTIFACT)
            
            # Use raw SQL to query the JSONB content field
            result = query.filter("content->>'name'", "eq", name).execute()
            
            if not result.data:
                return None
            
            # Filter artifacts by name and sort by version
            artifacts = [ContextEntry.from_dict(entry) for entry in result.data]
            artifacts.sort(key=lambda a: a.version or 0, reverse=True)
            
            if version is not None:
                # Get specific version
                for artifact in artifacts:
                    if artifact.version == version:
                        return artifact
                return None
            
            # Get latest version
            return artifacts[0] if artifacts else None
        except Exception as e:
            logger.error(f"Failed to get artifact {name} for project {project_id} from OrbitContextStore: {str(e)}")
            raise
    
    async def get_related_entries(
        self,
        entry_id: str,
        relationship_type: Optional[str] = None,
        direction: str = "outgoing",
    ) -> List[Tuple[str, ContextEntry]]:
        """
        Get entries related to a given entry.
        
        Args:
            entry_id: Entry ID
            relationship_type: Filter by relationship type
            direction: "outgoing" for entries this entry points to,
                       "incoming" for entries that point to this entry,
                       "both" for both directions
            
        Returns:
            List of (relationship_type, entry) tuples
        """
        await self.initialize()
        
        try:
            relationships = []
            
            # Get outgoing relationships
            if direction in ["outgoing", "both"]:
                query = self.supabase_client.table("orbit_context_relationships").select("*").eq("source_id", entry_id)
                
                if relationship_type:
                    query = query.eq("relationship_type", relationship_type)
                
                outgoing_result = query.execute()
                
                for rel in outgoing_result.data:
                    relationships.append((rel["relationship_type"], rel["target_id"]))
            
            # Get incoming relationships
            if direction in ["incoming", "both"]:
                query = self.supabase_client.table("orbit_context_relationships").select("*").eq("target_id", entry_id)
                
                if relationship_type:
                    query = query.eq("relationship_type", relationship_type)
                
                incoming_result = query.execute()
                
                for rel in incoming_result.data:
                    relationships.append((rel["relationship_type"], rel["source_id"]))
            
            # Get the related entries
            related_entries = []
            
            for rel_type, related_id in relationships:
                entry = await self.get_entry(related_id)
                if entry:
                    related_entries.append((rel_type, entry))
            
            return related_entries
        except Exception as e:
            logger.error(f"Failed to get related entries for {entry_id} from OrbitContextStore: {str(e)}")
            raise
    
    async def search_entries(
        self,
        project_id: str,
        query: str,
        entry_types: Optional[List[EntryType]] = None,
        tags: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[ContextEntry]:
        """
        Search for context entries.
        
        Args:
            project_id: Project ID
            query: Search query
            entry_types: Filter by entry types
            tags: Filter by tags
            limit: Maximum number of entries to return
            
        Returns:
            List of matching context entries
        """
        await self.initialize()
        
        # This is a simplified implementation that doesn't use vector search
        # In a production environment, you would use a vector database or
        # Supabase's pgvector extension for semantic search
        
        try:
            db_query = self.supabase_client.table("orbit_context_entries").select("*").eq("project_id", project_id)
            
            if entry_types:
                db_query = db_query.in_("entry_type", entry_types)
            
            # Use full-text search on the content field
            # This is a simplified approach - in production, use proper vector search
            result = db_query.execute()
            
            # Filter results manually based on query and tags
            entries = []
            
            for entry_data in result.data:
                entry = ContextEntry.from_dict(entry_data)
                
                # Check if entry matches query
                entry_json = json.dumps(entry.content).lower()
                if query.lower() not in entry_json:
                    continue
                
                # Check if entry has all required tags
                if tags and not all(tag in entry.tags for tag in tags):
                    continue
                
                entries.append(entry)
                
                if len(entries) >= limit:
                    break
            
            return entries
        except Exception as e:
            logger.error(f"Failed to search entries in OrbitContextStore: {str(e)}")
            raise
    
    async def create_summary(
        self,
        project_id: str,
        summary_content: Dict[str, Any],
        entry_ids: List[str],
        agent_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> str:
        """
        Create a summary of multiple context entries.
        
        Args:
            project_id: Project ID
            summary_content: Summary content
            entry_ids: IDs of entries being summarized
            agent_id: ID of the agent creating the summary
            user_id: User ID
            tags: Tags
            
        Returns:
            ID of the created summary
        """
        await self.initialize()
        
        entry = ContextEntry(
            entry_type=EntryType.SUMMARY,
            agent_id=agent_id,
            project_id=project_id,
            user_id=user_id,
            content=summary_content,
            summarized_entry_ids=entry_ids,
            tags=tags or [],
        )
        
        try:
            result = self.supabase_client.table("orbit_context_entries").insert(
                entry.to_dict()
            ).execute()
            
            entry_id = result.data[0]["id"]
            logger.info(f"Created summary {entry_id} for {len(entry_ids)} entries in OrbitContextStore")
            
            return entry_id
        except Exception as e:
            logger.error(f"Failed to create summary in OrbitContextStore: {str(e)}")
            raise
    
    async def _get_latest_artifact_version(self, project_id: str, name: str) -> Optional[Dict[str, Any]]:
        """
        Get the latest version of an artifact.
        
        Args:
            project_id: Project ID
            name: Artifact name
            
        Returns:
            Latest artifact version if found, None otherwise
        """
        try:
            query = self.supabase_client.table("orbit_context_entries").select("*").eq("project_id", project_id).eq("entry_type", EntryType.ARTIFACT)
            
            # Use raw SQL to query the JSONB content field
            result = query.filter("content->>'name'", "eq", name).execute()
            
            if not result.data:
                return None
            
            # Find the artifact with the highest version
            latest = None
            latest_version = -1
            
            for entry in result.data:
                version = entry.get("version", 0)
                if version > latest_version:
                    latest_version = version
                    latest = entry
            
            return latest
        except Exception as e:
            logger.error(f"Failed to get latest artifact version for {name} in project {project_id}: {str(e)}")
            raise


# Singleton instance
_context_store: Optional[OrbitContextStore] = None


async def get_context_store() -> OrbitContextStore:
    """
    Get the OrbitContextStore instance.
    
    Returns:
        OrbitContextStore instance
    """
    global _context_store
    
    if _context_store is None:
        # Override the Supabase client with direct initialization
        import os
        from dotenv import load_dotenv
        from supabase import create_client
        
        # Load environment variables
        load_dotenv()
        
        # Get Supabase URL and key
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        # Use hardcoded values if environment variables are not found
        if not supabase_url or not supabase_key:
            supabase_url = "https://vyrlsfrohzaopgqndxgv.supabase.co"
            supabase_key = os.getenv("SUPABASE_KEY")
        
        _context_store = OrbitContextStore()
        _context_store.supabase_client = create_client(supabase_url, supabase_key)
        _context_store.initialized = True
        logger.info("OrbitContextStore initialized successfully with direct Supabase client")
    
    return _context_store
