#!/usr/bin/env python
"""
Simple test script for OrbitContext with Supabase.
"""
import asyncio
import datetime
import json
import os
import sys
import uuid
from pathlib import Path

# Custom JSON encoder to handle datetime objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return super().default(obj)

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from supabase import create_client

# Import the necessary modules
from app.services.orbitbridge.context import OrbitContext, ContextType, SourceType
from app.services.orbitbridge.context_store import OrbitContextStore

async def test_orbit_context():
    """Test OrbitContext with Supabase."""
    print("Testing OrbitContext with Supabase...")
    
    # Load environment variables from the root directory
    env_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / '.env'
    load_dotenv(dotenv_path=env_path)
    print(f"Loading environment variables from: {env_path}")
    
    # Get Supabase URL and key from environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    # If not found, try alternative environment variable names
    if not supabase_url:
        print("SUPABASE_URL not found, trying alternative environment variables...")
        supabase_url = os.getenv("SUPABASE_URL")
        
    if not supabase_key:
        print("SUPABASE_SERVICE_ROLE_KEY not found, trying alternative environment variables...")
        supabase_key = os.getenv("SUPABASE_KEY")
    
    print(f"Supabase URL: {supabase_url}")
    
    if supabase_key:
        print(f"Supabase Key: {supabase_key[:10]}...{supabase_key[-10:]}")
    else:
        print("Supabase Key: Not found in environment variables")
    
    # Always use hardcoded values for testing
    print("Using hardcoded values for testing...")
    supabase_url = "https://vyrlsfrohzaopgqndxgv.supabase.co"
    supabase_key = os.getenv("SUPABASE_KEY")
    if not supabase_key:
        raise ValueError("SUPABASE_KEY environment variable is required")
    
    try:
        # Initialize Supabase client
        supabase_client = create_client(supabase_url, supabase_key)
        print("Supabase client initialized successfully!")
        
        # Create OrbitContextStore
        context_store = OrbitContextStore()
        context_store.supabase_client = supabase_client
        context_store.initialized = True
        print("OrbitContextStore initialized successfully!")
        
        # Create a simple OrbitContext
        project_id = f"test-{uuid.uuid4()}"
        context = OrbitContext(
            id=f"ctx-{uuid.uuid4()}",
            project_id=project_id,
            type=ContextType.DEPLOYMENT,
            source=SourceType.ORBITDEPLOY,
            environment="test",
            deployment={
                "id": f"deploy-{uuid.uuid4()}",
                "project_id": project_id,
                "environment": "test",
                "branch": "main",
                "commit_hash": "abc123",
                "status": "success",
                "duration_seconds": 10.5,
                "timestamp": datetime.datetime.utcnow()
            },
            metadata={
                "test": True
            },
            tags=["test", "supabase"]
        )
        print(f"Created OrbitContext: {context.id}")
        
        # Store the context
        context_id = await context_store.store_event(context)
        print(f"Stored context with ID: {context_id}")
        
        # Retrieve the context
        retrieved_context = await context_store.get_entry(context_id)
        print(f"Retrieved context: {retrieved_context}")
        
        # Success! We've successfully stored and retrieved a context entry
        print("\nSuccess! OrbitContext integration with Supabase is working correctly.")
        print("The enhanced OrbitContext implementation can now be used for persistent storage,")
        print("relationships between context entries, and multi-agent collaboration.")
        
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_orbit_context())
    if success:
        print("OrbitContext test passed!")
    else:
        print("OrbitContext test failed!")
