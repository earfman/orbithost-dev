#!/usr/bin/env python
"""Simple test script for Supabase connection."""
import os
import sys
from pathlib import Path

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from supabase import create_client, Client

def test_supabase_connection():
    """Test Supabase connection."""
    print("Testing Supabase connection...")
    
    # Load environment variables from the root directory
    env_path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) / '.env'
    load_dotenv(dotenv_path=env_path)
    print(f"Loading environment variables from: {env_path}")
    
    # Get Supabase URL and key from environment variables
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    print(f"Supabase URL: {supabase_url}")
    
    if supabase_key:
        print(f"Supabase Key: {supabase_key[:10]}...{supabase_key[-10:]}")
    else:
        print("Supabase Key: Not found in environment variables")
        
    # Try alternative environment variable names if the first ones aren't found
    if not supabase_url:
        supabase_url = os.getenv("SUPABASE_URL")
        print(f"Trying alternative env var SUPABASE_URL: {supabase_url}")
    
    if not supabase_key:
        # Try SUPABASE_KEY
        supabase_key = os.getenv("SUPABASE_KEY")
        if supabase_key:
            print(f"Found key in SUPABASE_KEY")
        else:
            # Try SUPABASE_ANON_KEY
            supabase_key = os.getenv("SUPABASE_ANON_KEY")
            if supabase_key:
                print(f"Found key in SUPABASE_ANON_KEY")
    
    # Hardcode the values if they're still not found
    if not supabase_url or not supabase_key:
        print("Using hardcoded values for testing...")
        supabase_url = "https://vyrlsfrohzaopgqndxgv.supabase.co"
        # Fallback key should be loaded from environment variable
        supabase_key = os.getenv("SUPABASE_KEY_FALLBACK")
        if not supabase_key:
            raise ValueError("SUPABASE_KEY_FALLBACK environment variable is required for testing")
    
    # Get Supabase client
    try:
        client = create_client(supabase_url, supabase_key)
        print("Supabase client initialized successfully!")
        
        # Try a simple query
        result = client.table("orbit_context_entries").select("*").limit(1).execute()
        print(f"Query executed successfully!")
        print(f"Result: {result}")
        
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_supabase_connection()
    if success:
        print("Supabase connection test passed!")
    else:
        print("Supabase connection test failed!")
