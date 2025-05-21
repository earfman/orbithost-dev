"""
API endpoints for DNS verification.

This module provides API endpoints for verifying domain ownership and DNS configuration
through various verification methods like DNS TXT records, HTTP verification, and email verification.
"""
import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from app.services.domains.dns_verification import (
    get_dns_verification_service,
    DomainVerification,
    VerificationMethod,
    VerificationStatus,
    VerificationError,
)
from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

# Create API router for DNS verification
router = APIRouter(prefix="/api/dns-verification", tags=["dns-verification"])

# Pydantic models for API
class VerificationCreate(BaseModel):
    """Model for creating a domain verification."""
    user_id: str = Field(..., description="ID of the user")
    domain: str = Field(..., description="Domain name")
    method: str = Field("dns_txt", description="Verification method")
    email: Optional[str] = Field(None, description="Email address for email verification")

class VerificationResponse(BaseModel):
    """Model for domain verification response."""
    id: str = Field(..., description="Verification ID")
    user_id: str = Field(..., description="ID of the user")
    domain: str = Field(..., description="Domain name")
    method: str = Field(..., description="Verification method")
    status: str = Field(..., description="Verification status")
    record_name: Optional[str] = Field(None, description="DNS record name for DNS verification")
    record_value: Optional[str] = Field(None, description="DNS record value for DNS verification")
    http_path: Optional[str] = Field(None, description="HTTP path for HTTP verification")
    email: Optional[str] = Field(None, description="Email address for email verification")
    error: Optional[str] = Field(None, description="Error message if verification failed")

class VerificationCheck(BaseModel):
    """Model for checking a domain verification."""
    confirmation_code: Optional[str] = Field(None, description="Confirmation code for email verification")

class VerificationResult(BaseModel):
    """Model for domain verification result."""
    success: bool = Field(..., description="Whether the verification was successful")
    error: Optional[str] = Field(None, description="Error message if verification failed")
    verification: VerificationResponse = Field(..., description="Domain verification")

@router.post("", response_model=VerificationResponse)
async def create_verification(
    verification: VerificationCreate = Body(...),
):
    """
    Create a new domain verification.
    
    Args:
        verification: Domain verification to create
        
    Returns:
        Created domain verification
    """
    try:
        # Get DNS verification service
        service = await get_dns_verification_service()
        
        # Create verification
        created_verification = await service.create_verification(
            user_id=verification.user_id,
            domain=verification.domain,
            method=VerificationMethod(verification.method),
            email=verification.email,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_verification_api",
            "operation": "create",
            "verification_id": created_verification.id,
            "user_id": verification.user_id,
            "domain": verification.domain,
            "method": verification.method,
        })
        
        return VerificationResponse(**created_verification.to_dict())
    except ValueError as e:
        logger.error(f"Error creating verification: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating verification: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{verification_id}", response_model=VerificationResponse)
async def get_verification(
    verification_id: str = Path(..., description="ID of the verification to get"),
):
    """
    Get a domain verification by ID.
    
    Args:
        verification_id: ID of the verification to get
        
    Returns:
        Domain verification
    """
    try:
        # Get DNS verification service
        service = await get_dns_verification_service()
        
        # Get verification
        verification = await service.get_verification(verification_id)
        
        if not verification:
            raise HTTPException(status_code=404, detail=f"Verification {verification_id} not found")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_verification_api",
            "operation": "get",
            "verification_id": verification_id,
            "user_id": verification.user_id,
            "domain": verification.domain,
        })
        
        return VerificationResponse(**verification.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting verification {verification_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=List[VerificationResponse])
async def list_verifications(
    user_id: str = Query(..., description="ID of the user"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
):
    """
    List domain verifications for a user.
    
    Args:
        user_id: ID of the user
        domain: Filter by domain
        
    Returns:
        List of domain verifications
    """
    try:
        # Get DNS verification service
        service = await get_dns_verification_service()
        
        # Get verifications
        if domain:
            # Get verifications for domain
            domain_verifications = await service.get_verifications_for_domain(domain)
            
            # Filter by user
            verifications = [
                verification for verification in domain_verifications
                if verification.user_id == user_id
            ]
        else:
            # Get verifications for user
            verifications = await service.get_verifications_for_user(user_id)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_verification_api",
            "operation": "list",
            "user_id": user_id,
            "domain": domain,
            "count": len(verifications),
        })
        
        return [VerificationResponse(**verification.to_dict()) for verification in verifications]
    except Exception as e:
        logger.error(f"Error listing verifications: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{verification_id}/verify", response_model=VerificationResult)
async def verify_domain(
    verification_id: str = Path(..., description="ID of the verification to check"),
    verification_check: VerificationCheck = Body(...),
):
    """
    Verify domain ownership and DNS configuration.
    
    Args:
        verification_id: ID of the verification to check
        verification_check: Verification check parameters
        
    Returns:
        Verification result
    """
    try:
        # Get DNS verification service
        service = await get_dns_verification_service()
        
        # Get verification
        verification = await service.get_verification(verification_id)
        
        if not verification:
            raise HTTPException(status_code=404, detail=f"Verification {verification_id} not found")
        
        # Verify domain
        success, error = await service.verify(
            verification_id=verification_id,
            confirmation_code=verification_check.confirmation_code,
        )
        
        # Get updated verification
        updated_verification = await service.get_verification(verification_id)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_verification_api",
            "operation": "verify",
            "verification_id": verification_id,
            "user_id": verification.user_id,
            "domain": verification.domain,
            "method": verification.method.value,
            "success": success,
            "error": error,
        })
        
        return VerificationResult(
            success=success,
            error=error,
            verification=VerificationResponse(**updated_verification.to_dict()),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying domain: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{verification_id}")
async def delete_verification(
    verification_id: str = Path(..., description="ID of the verification to delete"),
):
    """
    Delete a domain verification.
    
    Args:
        verification_id: ID of the verification to delete
        
    Returns:
        Success message
    """
    try:
        # Get DNS verification service
        service = await get_dns_verification_service()
        
        # Get verification for logging
        verification = await service.get_verification(verification_id)
        
        if not verification:
            raise HTTPException(status_code=404, detail=f"Verification {verification_id} not found")
        
        # Delete verification
        success = await service.delete_verification(verification_id)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to delete verification {verification_id}")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_verification_api",
            "operation": "delete",
            "verification_id": verification_id,
            "user_id": verification.user_id,
            "domain": verification.domain,
        })
        
        return {"message": f"Verification {verification_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting verification {verification_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
