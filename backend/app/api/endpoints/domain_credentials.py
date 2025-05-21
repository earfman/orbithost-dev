"""
API endpoints for managing domain registrar and DNS provider credentials.

This module provides API endpoints for securely storing, retrieving,
updating, and deleting API credentials for domain registrars and DNS providers.
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from app.services.domains.credential_storage import (
    get_credential_storage,
    APICredential,
    CredentialType,
    ProviderType,
    Provider,
)
from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

# Create API router for domain credentials
router = APIRouter(prefix="/api/domain-credentials", tags=["domain-credentials"])

# Pydantic models for API
class CredentialCreate(BaseModel):
    """Model for creating an API credential."""
    user_id: str = Field(..., description="ID of the user who owns the credential")
    provider: str = Field(..., description="Service provider")
    provider_type: str = Field(..., description="Type of service provider")
    credential_type: str = Field(..., description="Type of credential")
    name: str = Field(..., description="Credential name")
    credentials: Dict[str, str] = Field(..., description="Dictionary of credential key-value pairs")

class CredentialUpdate(BaseModel):
    """Model for updating an API credential."""
    name: Optional[str] = Field(None, description="Credential name")
    credentials: Optional[Dict[str, str]] = Field(None, description="Dictionary of credential key-value pairs")

class CredentialResponse(BaseModel):
    """Model for API credential response."""
    id: str = Field(..., description="Credential ID")
    user_id: str = Field(..., description="ID of the user who owns the credential")
    provider: str = Field(..., description="Service provider")
    provider_type: str = Field(..., description="Type of service provider")
    credential_type: str = Field(..., description="Type of credential")
    name: str = Field(..., description="Credential name")
    encrypted: bool = Field(..., description="Whether the credentials are encrypted")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    last_used_at: Optional[str] = Field(None, description="Last used timestamp")
    verified: bool = Field(..., description="Whether the credential has been verified")

class CredentialDetailResponse(CredentialResponse):
    """Model for API credential detail response with credentials."""
    credentials: Dict[str, str] = Field(..., description="Dictionary of credential key-value pairs")

@router.post("", response_model=CredentialResponse)
async def create_credential(
    credential: CredentialCreate = Body(...),
):
    """
    Create a new API credential.
    
    Args:
        credential: API credential to create
        
    Returns:
        Created API credential
    """
    try:
        # Get credential storage
        storage = await get_credential_storage()
        
        # Generate credential ID
        credential_id = str(uuid.uuid4())
        
        # Create credential
        created_credential = await storage.store_credential(
            APICredential(
                id=credential_id,
                user_id=credential.user_id,
                provider=Provider(credential.provider),
                provider_type=ProviderType(credential.provider_type),
                credential_type=CredentialType(credential.credential_type),
                name=credential.name,
                credentials=credential.credentials,
            )
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "domain_credential_api",
            "operation": "create",
            "credential_id": credential_id,
            "user_id": credential.user_id,
            "provider": credential.provider,
            "provider_type": credential.provider_type,
        })
        
        return CredentialResponse(**created_credential.to_dict())
    except ValueError as e:
        logger.error(f"Error creating credential: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating credential: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{credential_id}", response_model=CredentialResponse)
async def get_credential(
    credential_id: str = Path(..., description="ID of the credential to get"),
    include_credentials: bool = Query(False, description="Whether to include the credentials"),
):
    """
    Get an API credential by ID.
    
    Args:
        credential_id: ID of the credential to get
        include_credentials: Whether to include the credentials
        
    Returns:
        API credential
    """
    try:
        # Get credential storage
        storage = await get_credential_storage()
        
        # Get credential
        credential = await storage.get_credential(
            credential_id=credential_id,
            decrypt=include_credentials,
        )
        
        if not credential:
            raise HTTPException(status_code=404, detail=f"Credential {credential_id} not found")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "domain_credential_api",
            "operation": "get",
            "credential_id": credential_id,
            "user_id": credential.user_id,
            "provider": credential.provider.value,
            "provider_type": credential.provider_type.value,
            "include_credentials": include_credentials,
        })
        
        # Update last used timestamp
        await storage.update_last_used(credential_id)
        
        if include_credentials:
            return CredentialDetailResponse(**credential.to_dict(include_credentials=True))
        else:
            return CredentialResponse(**credential.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting credential {credential_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=List[CredentialResponse])
async def list_credentials(
    user_id: str = Query(..., description="ID of the user"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    provider_type: Optional[str] = Query(None, description="Filter by provider type"),
):
    """
    List API credentials for a user.
    
    Args:
        user_id: ID of the user
        provider: Filter by provider
        provider_type: Filter by provider type
        
    Returns:
        List of API credentials
    """
    try:
        # Get credential storage
        storage = await get_credential_storage()
        
        # Convert provider and provider_type to enums if provided
        provider_enum = Provider(provider) if provider else None
        provider_type_enum = ProviderType(provider_type) if provider_type else None
        
        # Get credentials
        credentials = await storage.get_credentials_for_user(
            user_id=user_id,
            provider=provider_enum,
            provider_type=provider_type_enum,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "domain_credential_api",
            "operation": "list",
            "user_id": user_id,
            "provider": provider,
            "provider_type": provider_type,
            "count": len(credentials),
        })
        
        return [CredentialResponse(**credential.to_dict()) for credential in credentials]
    except ValueError as e:
        logger.error(f"Error listing credentials: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing credentials: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{credential_id}", response_model=CredentialResponse)
async def update_credential(
    credential_id: str = Path(..., description="ID of the credential to update"),
    credential_update: CredentialUpdate = Body(...),
):
    """
    Update an API credential.
    
    Args:
        credential_id: ID of the credential to update
        credential_update: API credential update
        
    Returns:
        Updated API credential
    """
    try:
        # Get credential storage
        storage = await get_credential_storage()
        
        # Get existing credential
        existing_credential = await storage.get_credential(credential_id)
        
        if not existing_credential:
            raise HTTPException(status_code=404, detail=f"Credential {credential_id} not found")
        
        # Prepare updates
        updates = {}
        
        if credential_update.name is not None:
            updates["name"] = credential_update.name
        
        if credential_update.credentials is not None:
            updates["credentials"] = credential_update.credentials
        
        # Update credential
        updated_credential = await storage.update_credential(
            credential_id=credential_id,
            updates=updates,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "domain_credential_api",
            "operation": "update",
            "credential_id": credential_id,
            "user_id": updated_credential.user_id,
            "provider": updated_credential.provider.value,
            "provider_type": updated_credential.provider_type.value,
        })
        
        return CredentialResponse(**updated_credential.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating credential {credential_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{credential_id}")
async def delete_credential(
    credential_id: str = Path(..., description="ID of the credential to delete"),
):
    """
    Delete an API credential.
    
    Args:
        credential_id: ID of the credential to delete
        
    Returns:
        Success message
    """
    try:
        # Get credential storage
        storage = await get_credential_storage()
        
        # Get existing credential for logging
        existing_credential = await storage.get_credential(credential_id)
        
        if not existing_credential:
            raise HTTPException(status_code=404, detail=f"Credential {credential_id} not found")
        
        # Delete credential
        success = await storage.delete_credential(credential_id)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to delete credential {credential_id}")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "domain_credential_api",
            "operation": "delete",
            "credential_id": credential_id,
            "user_id": existing_credential.user_id,
            "provider": existing_credential.provider.value,
            "provider_type": existing_credential.provider_type.value,
        })
        
        return {"message": f"Credential {credential_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting credential {credential_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{credential_id}/verify")
async def verify_credential(
    credential_id: str = Path(..., description="ID of the credential to verify"),
    verified: bool = Query(True, description="Whether the credential is verified"),
):
    """
    Mark an API credential as verified.
    
    Args:
        credential_id: ID of the credential to verify
        verified: Whether the credential is verified
        
    Returns:
        Updated API credential
    """
    try:
        # Get credential storage
        storage = await get_credential_storage()
        
        # Verify credential
        updated_credential = await storage.verify_credential(
            credential_id=credential_id,
            verified=verified,
        )
        
        if not updated_credential:
            raise HTTPException(status_code=404, detail=f"Credential {credential_id} not found")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "domain_credential_api",
            "operation": "verify",
            "credential_id": credential_id,
            "user_id": updated_credential.user_id,
            "provider": updated_credential.provider.value,
            "provider_type": updated_credential.provider_type.value,
            "verified": verified,
        })
        
        return CredentialResponse(**updated_credential.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying credential {credential_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
