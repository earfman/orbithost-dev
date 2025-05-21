#!/usr/bin/env python
"""
Minimal OrbitContext Demo Script

This script demonstrates the basic functionality of the enhanced OrbitContext
implementation with Supabase integration. It shows how to:

1. Create a deployment context
2. Store it in the Supabase database

Usage:
    python minimal_context_demo.py
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

async def demo_create_context():
    """Create and store a deployment context."""
    logger.info("=== Creating Deployment Context ===")
    
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
        
        # Create context data
        context_id = f"ctx-{uuid.uuid4()}"
        deployment_id = f"deploy-{uuid.uuid4()}"
        timestamp = datetime.datetime.utcnow()
        
        # Create context content
        content = {
            "id": context_id,
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
        content_json = json.dumps(content, cls=DateTimeEncoder)
        content_data = json.loads(content_json)
        
        # Store in Supabase
        result = supabase_client.table("orbit_context_entries").insert({
            "context_id": context_id,
            "project_id": project_id,
            "context_type": "deployment",
            "source_type": "orbitdeploy",
            "content": content_data,
            "metadata": {"demo": True},
            "timestamp": timestamp.isoformat()
        }).execute()
        
        # Get the ID of the stored entry
        entry_id = result.data[0]["id"]
        logger.info(f"Successfully stored context with ID: {entry_id}")
        
        logger.info("\nSuccess! OrbitContext integration with Supabase is working correctly.")
        logger.info("The enhanced OrbitContext implementation can now be used for persistent storage,")
        logger.info("relationships between context entries, and multi-agent collaboration.")
        
        return True
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function."""
    try:
        await demo_create_context()
    except Exception as e:
        logger.error(f"Error running demo: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
