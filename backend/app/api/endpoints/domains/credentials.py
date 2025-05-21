"""
API endpoints for managing domain registrar credentials.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Body

from app.models.user import User
from app.services.credential_service import CredentialService
from app.services.domain_service.registrars.factory import RegistrarFactory
from app.api.deps import get_current_user

router = APIRouter()
credential_service = CredentialService()

@router.post("/", response_model=Dict[str, Any])
async def store_credentials(
    provider: str,
    credentials: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Store API credentials for a domain registrar.
    
    Args:
        provider: The provider name (e.g., 'godaddy', 'namecheap')
        credentials: The credentials to store
        current_user: The authenticated user
        
    Returns:
        Dictionary with storage status
    """
    try:
        # Validate the provider
        supported_registrars = RegistrarFactory.get_supported_registrars()
        if provider not in supported_registrars:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported provider: {provider}. Supported providers: {', '.join(supported_registrars.keys())}"
            )
            
        # Store the credentials
        result = await credential_service.store_credentials(
            user_id=current_user.id,
            provider=provider,
            credentials=credentials
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error storing credentials: {str(e)}"
        )

@router.get("/", response_model=List[Dict[str, Any]])
async def list_credentials(
    current_user: User = Depends(get_current_user)
):
    """
    List all API credentials for the current user.
    
    Args:
        current_user: The authenticated user
        
    Returns:
        List of credential metadata
    """
    try:
        # List the credentials
        results = await credential_service.list_user_credentials(
            user_id=current_user.id
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing credentials: {str(e)}"
        )

@router.get("/{provider}", response_model=Dict[str, Any])
async def validate_credentials(
    provider: str,
    current_user: User = Depends(get_current_user)
):
    """
    Validate API credentials for a domain registrar.
    
    Args:
        provider: The provider name (e.g., 'godaddy', 'namecheap')
        current_user: The authenticated user
        
    Returns:
        Dictionary with validation status
    """
    try:
        # Validate the credentials
        result = await credential_service.validate_credentials(
            user_id=current_user.id,
            provider=provider
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error validating credentials: {str(e)}"
        )

@router.delete("/{provider}", response_model=Dict[str, Any])
async def delete_credentials(
    provider: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete API credentials for a domain registrar.
    
    Args:
        provider: The provider name (e.g., 'godaddy', 'namecheap')
        current_user: The authenticated user
        
    Returns:
        Dictionary with deletion status
    """
    try:
        # Delete the credentials
        result = await credential_service.delete_credentials(
            user_id=current_user.id,
            provider=provider
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting credentials: {str(e)}"
        )
