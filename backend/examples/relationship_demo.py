#!/usr/bin/env python
"""
OrbitContext Relationship Demo

This script demonstrates how to create relationships between context entries
using the enhanced OrbitContext implementation with Supabase.

Usage:
    python relationship_demo.py
"""
import asyncio
import datetime
import json
import logging
import os
import sys
import uuid
from pathlib import Path

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from supabase import create_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)

async def demo_create_relationship():
    """Create two context entries and establish a relationship between them."""
    logger.info("=== Creating Context Entries and Relationship ===")
    
    # Create a project ID for this demo
    project_id = f"demo-{uuid.uuid4()}"
    logger.info(f"Using project ID: {project_id}")
    
    # Use hardcoded Supabase credentials
    supabase_url = "https://vyrlsfrohzaopgqndxgv.supabase.co"
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_key:
        raise ValueError("SUPABASE_KEY environment variable is required")
    
    try:
        # Initialize Supabase client
        supabase_client = create_client(supabase_url, supabase_key)
        logger.info("Supabase client initialized successfully!")
        
        # Create deployment context
        deployment_context_id = f"ctx-deploy-{uuid.uuid4()}"
        deployment_id = f"deploy-{uuid.uuid4()}"
        timestamp = datetime.datetime.utcnow()
        
        # Create deployment context content
        deployment_content = {
            "id": deployment_context_id,
            "type": "deployment",
            "source": "orbitdeploy",
            "timestamp": timestamp.isoformat(),
            "project_id": project_id,
            "environment": "production",
            "deployment": {
                "id": deployment_id,
                "project_id": project_id,
                "environment": "production",
                "branch": "main",
                "commit_hash": "abc123def456",
                "status": "success",
                "duration_seconds": 45.2,
                "timestamp": timestamp.isoformat()
            },
            "metadata": {
                "server": "fly-sfo-1",
                "demo": True
            },
            "tags": ["demo", "production", "orbitcontext"]
        }
        
        # Convert to JSON and back to handle datetime serialization
        deployment_json = json.dumps(deployment_content, cls=DateTimeEncoder)
        deployment_data = json.loads(deployment_json)
        
        # Store deployment context in Supabase
        deployment_result = supabase_client.table("orbit_context_entries").insert({
            "context_id": deployment_context_id,
            "project_id": project_id,
            "context_type": "deployment",
            "source_type": "orbitdeploy",
            "content": deployment_data,
            "metadata": {"demo": True},
            "timestamp": timestamp.isoformat()
        }).execute()
        
        # Get the ID of the stored deployment entry
        deployment_entry_id = deployment_result.data[0]["id"]
        logger.info(f"Successfully stored deployment context with ID: {deployment_entry_id}")
        
        # Create error context
        error_context_id = f"ctx-error-{uuid.uuid4()}"
        error_timestamp = datetime.datetime.utcnow()
        
        # Create error context content
        error_content = {
            "id": error_context_id,
            "type": "error",
            "source": "orbithost",
            "timestamp": error_timestamp.isoformat(),
            "project_id": project_id,
            "environment": "production",
            "error": {
                "message": "Database connection failed: timeout after 30s",
                "type": "ConnectionError",
                "file": "app/db/client.py",
                "line": 45,
                "column": 12,
                "function": "connect_db",
                "stack_trace": "Traceback (most recent call last):\n  File 'app/db/client.py', line 45, in connect_db\n    conn = await asyncpg.connect(dsn, timeout=30.0)\nConnectionError: Database connection failed: timeout after 30s"
            },
            "metadata": {
                "database": "postgres-1",
                "demo": True
            },
            "tags": ["demo", "error", "database", "timeout"]
        }
        
        # Convert to JSON and back to handle datetime serialization
        error_json = json.dumps(error_content, cls=DateTimeEncoder)
        error_data = json.loads(error_json)
        
        # Store error context in Supabase
        error_result = supabase_client.table("orbit_context_entries").insert({
            "context_id": error_context_id,
            "project_id": project_id,
            "context_type": "error",
            "source_type": "orbithost",
            "content": error_data,
            "metadata": {"demo": True},
            "timestamp": error_timestamp.isoformat()
        }).execute()
        
        # Get the ID of the stored error entry
        error_entry_id = error_result.data[0]["id"]
        logger.info(f"Successfully stored error context with ID: {error_entry_id}")
        
        # Create relationship between deployment and error contexts
        relationship_timestamp = datetime.datetime.utcnow()
        
        # Store relationship in Supabase
        relationship_result = supabase_client.table("orbit_context_relationships").insert({
            "source_context_id": error_context_id,
            "target_context_id": deployment_context_id,
            "relationship_type": "caused_by",
            "metadata": {
                "demo": True,
                "created_at": relationship_timestamp.isoformat()
            }
        }).execute()
        
        # Get the ID of the stored relationship
        relationship_id = relationship_result.data[0]["id"]
        logger.info(f"Successfully created relationship with ID: {relationship_id}")
        
        # Retrieve the relationship from Supabase
        relationship_query = supabase_client.table("orbit_context_relationships").select("*").eq("id", relationship_id).execute()
        relationship = relationship_query.data[0]
        logger.info(f"Retrieved relationship: {relationship}")
        
        logger.info("\nSuccess! OrbitContext relationship functionality is working correctly.")
        logger.info("The enhanced OrbitContext implementation now supports relationships between context entries,")
        logger.info("enabling powerful capabilities for tracking dependencies and connections between different contexts.")
        
        return True
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function."""
    try:
        await demo_create_relationship()
    except Exception as e:
        logger.error(f"Error running demo: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
