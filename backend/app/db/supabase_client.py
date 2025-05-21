"""
Supabase client module for OrbitHost.

This module provides a client for interacting with Supabase.
"""

import logging
import os
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from supabase import create_client, Client
from tenacity import retry, stop_after_attempt, wait_exponential

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Global client instance
_supabase_client: Optional[Client] = None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def get_supabase_client() -> Client:
    """
    Get a Supabase client instance.

    Returns:
        Client: Supabase client instance
    
    Raises:
        ValueError: If Supabase URL or key is not configured
        Exception: If client initialization fails
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase URL and key must be configured in environment variables")

    try:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized successfully")
        return _supabase_client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {str(e)}")
        raise


async def execute_query(table: str, query_func: callable, **kwargs) -> Any:
    """
    Execute a query against Supabase.

    Args:
        table: Table name to query
        query_func: Function to apply to the query builder
        **kwargs: Additional arguments to pass to the query function

    Returns:
        Query result

    Raises:
        Exception: If query execution fails
    """
    try:
        client = await get_supabase_client()
        query = client.table(table)
        result = query_func(query, **kwargs)
        return result
    except Exception as e:
        logger.error(f"Error executing query on table {table}: {str(e)}")
        raise


async def insert_data(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert data into a Supabase table.

    Args:
        table: Table name to insert into
        data: Data to insert

    Returns:
        Inserted data with generated IDs

    Raises:
        Exception: If insertion fails
    """
    def query_builder(query, **kwargs):
        return query.insert(kwargs.get("data")).execute()

    result = await execute_query(table, query_builder, data=data)
    return result.data[0] if result.data else {}


async def update_data(table: str, id_column: str, id_value: Any, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update data in a Supabase table.

    Args:
        table: Table name to update
        id_column: Column name for the ID
        id_value: ID value to match
        data: Data to update

    Returns:
        Updated data

    Raises:
        Exception: If update fails
    """
    def query_builder(query, **kwargs):
        return query.update(kwargs.get("data")).eq(kwargs.get("id_column"), kwargs.get("id_value")).execute()

    result = await execute_query(table, query_builder, data=data, id_column=id_column, id_value=id_value)
    return result.data[0] if result.data else {}


async def delete_data(table: str, id_column: str, id_value: Any) -> Dict[str, Any]:
    """
    Delete data from a Supabase table.

    Args:
        table: Table name to delete from
        id_column: Column name for the ID
        id_value: ID value to match

    Returns:
        Deleted data

    Raises:
        Exception: If deletion fails
    """
    def query_builder(query, **kwargs):
        return query.delete().eq(kwargs.get("id_column"), kwargs.get("id_value")).execute()

    result = await execute_query(table, query_builder, id_column=id_column, id_value=id_value)
    return result.data[0] if result.data else {}


async def select_data(table: str, columns: str = "*", **filters) -> list:
    """
    Select data from a Supabase table.

    Args:
        table: Table name to select from
        columns: Columns to select
        **filters: Filters to apply (column=value)

    Returns:
        Selected data

    Raises:
        Exception: If selection fails
    """
    def query_builder(query, **kwargs):
        query = query.select(kwargs.get("columns"))
        
        # Apply filters
        for column, value in kwargs.get("filters", {}).items():
            query = query.eq(column, value)
        
        return query.execute()

    result = await execute_query(table, query_builder, columns=columns, filters=filters)
    return result.data if result.data else []


async def select_by_id(table: str, id_column: str, id_value: Any, columns: str = "*") -> Dict[str, Any]:
    """
    Select a single record by ID from a Supabase table.

    Args:
        table: Table name to select from
        id_column: Column name for the ID
        id_value: ID value to match
        columns: Columns to select

    Returns:
        Selected record

    Raises:
        Exception: If selection fails
    """
    def query_builder(query, **kwargs):
        return query.select(kwargs.get("columns")).eq(kwargs.get("id_column"), kwargs.get("id_value")).execute()

    result = await execute_query(table, query_builder, columns=columns, id_column=id_column, id_value=id_value)
    return result.data[0] if result.data and result.data[0] else {}
