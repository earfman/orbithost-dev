"""
API endpoints for user management with Supabase database integration.

This module provides API endpoints for creating, retrieving, updating, and deleting users.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field, EmailStr

from app.db.dependencies import get_user_service
from app.db.models import User
from app.db.services import UserService
from app.utils.mcp.client import get_mcp_client

# Configure logging
logger = logging.getLogger(__name__)

# Create API router for users
router = APIRouter(prefix="/api/users", tags=["users"])


# Pydantic models for API
class UserCreate(BaseModel):
    """Model for creating a user."""
    email: EmailStr = Field(..., description="User email")
    name: Optional[str] = Field(None, description="User name")


class UserUpdate(BaseModel):
    """Model for updating a user."""
    name: Optional[str] = Field(None, description="User name")
    subscription_tier: Optional[str] = Field(None, description="Subscription tier")
    subscription_status: Optional[str] = Field(None, description="Subscription status")
    stripe_customer_id: Optional[str] = Field(None, description="Stripe customer ID")


class UserResponse(BaseModel):
    """Model for user response."""
    id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    name: Optional[str] = Field(None, description="User name")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    last_login: Optional[str] = Field(None, description="Last login timestamp")
    subscription_tier: str = Field(..., description="Subscription tier")
    subscription_status: str = Field(..., description="Subscription status")


@router.post("", response_model=UserResponse)
async def create_user(
    user: UserCreate = Body(...),
    user_service: UserService = Depends(get_user_service),
):
    """
    Create a new user.
    
    Args:
        user: User to create
        user_service: User service
        
    Returns:
        Created user
    """
    try:
        # Create user
        created_user = await user_service.create_user(
            email=user.email,
            name=user.name,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "user_api",
            "operation": "create",
            "user_id": created_user.id,
            "email": created_user.email,
        })
        
        return created_user
    except ValueError as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str = Path(..., description="ID of the user to get"),
    user_service: UserService = Depends(get_user_service),
):
    """
    Get a user by ID.
    
    Args:
        user_id: ID of the user to get
        user_service: User service
        
    Returns:
        User
    """
    try:
        # Get user
        user = await user_service.get_user(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail=f"User {user_id} not found")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "user_api",
            "operation": "get",
            "user_id": user_id,
        })
        
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[UserResponse])
async def list_users(
    email: Optional[str] = Query(None, description="Filter by email"),
    user_service: UserService = Depends(get_user_service),
):
    """
    List users with optional filtering.
    
    Args:
        email: Filter by email
        user_service: User service
        
    Returns:
        List of users
    """
    try:
        # Get users
        if email:
            user = await user_service.get_user_by_email(email)
            users = [user] if user else []
        else:
            users = await user_service.repository.get_all()
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "user_api",
            "operation": "list",
            "filter_email": email,
        })
        
        return users
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str = Path(..., description="ID of the user to update"),
    user_update: UserUpdate = Body(...),
    user_service: UserService = Depends(get_user_service),
):
    """
    Update a user.
    
    Args:
        user_id: ID of the user to update
        user_update: User update
        user_service: User service
        
    Returns:
        Updated user
    """
    try:
        # Update user
        updated_user = await user_service.update_user(
            user_id=user_id,
            data=user_update.dict(exclude_unset=True),
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "user_api",
            "operation": "update",
            "user_id": user_id,
        })
        
        return updated_user
    except ValueError as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{user_id}")
async def delete_user(
    user_id: str = Path(..., description="ID of the user to delete"),
    user_service: UserService = Depends(get_user_service),
):
    """
    Delete a user.
    
    Args:
        user_id: ID of the user to delete
        user_service: User service
        
    Returns:
        Success message
    """
    try:
        # Delete user
        await user_service.delete_user(user_id)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "user_api",
            "operation": "delete",
            "user_id": user_id,
        })
        
        return {"message": f"User {user_id} deleted successfully"}
    except ValueError as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
