"""
API endpoints for domain transfer.

This module provides API endpoints for transferring domains from other platforms
to OrbitHost, including verification, DNS record transfer, and application settings migration.
"""
import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from app.services.domains.domain_transfer import (
    get_domain_transfer_service,
    DomainTransfer,
    TransferSource,
    TransferStatus,
    TransferError,
)
from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

# Create API router for domain transfer
router = APIRouter(prefix="/api/domain-transfer", tags=["domain-transfer"])

# Pydantic models for API
class TransferCreate(BaseModel):
    """Model for creating a domain transfer."""
    user_id: str = Field(..., description="ID of the user")
    domain: str = Field(..., description="Domain name")
    source: str = Field(..., description="Source platform")
    source_credential_id: Optional[str] = Field(None, description="ID of the source credential")
    target_credential_id: Optional[str] = Field(None, description="ID of the target credential")

class TransferResponse(BaseModel):
    """Model for domain transfer response."""
    id: str = Field(..., description="Transfer ID")
    user_id: str = Field(..., description="ID of the user")
    domain: str = Field(..., description="Domain name")
    source: str = Field(..., description="Source platform")
    status: str = Field(..., description="Transfer status")
    verification_token: Optional[str] = Field(None, description="Verification token")
    verification_method: Optional[str] = Field(None, description="Verification method")
    error: Optional[str] = Field(None, description="Error message if transfer failed")

class NameserversUpdate(BaseModel):
    """Model for updating nameservers."""
    nameservers: List[str] = Field(..., description="Nameservers to set")

class AppSettingsMigration(BaseModel):
    """Model for migrating application settings."""
    app_id: str = Field(..., description="ID of the target application")

@router.post("", response_model=TransferResponse)
async def create_transfer(
    transfer: TransferCreate = Body(...),
):
    """
    Create a new domain transfer.
    
    Args:
        transfer: Domain transfer to create
        
    Returns:
        Created domain transfer
    """
    try:
        # Get domain transfer service
        service = await get_domain_transfer_service()
        
        # Create transfer
        created_transfer = await service.initiate_transfer(
            user_id=transfer.user_id,
            domain=transfer.domain,
            source=TransferSource(transfer.source),
            source_credential_id=transfer.source_credential_id,
            target_credential_id=transfer.target_credential_id,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "domain_transfer_api",
            "operation": "create",
            "transfer_id": created_transfer.id,
            "user_id": transfer.user_id,
            "domain": transfer.domain,
            "source": transfer.source,
        })
        
        return TransferResponse(**created_transfer.to_dict())
    except ValueError as e:
        logger.error(f"Error creating transfer: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating transfer: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{transfer_id}", response_model=TransferResponse)
async def get_transfer(
    transfer_id: str = Path(..., description="ID of the transfer to get"),
):
    """
    Get a domain transfer by ID.
    
    Args:
        transfer_id: ID of the transfer to get
        
    Returns:
        Domain transfer
    """
    try:
        # Get domain transfer service
        service = await get_domain_transfer_service()
        
        # Get transfer
        transfer = await service.get_transfer(transfer_id)
        
        if not transfer:
            raise HTTPException(status_code=404, detail=f"Transfer {transfer_id} not found")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "domain_transfer_api",
            "operation": "get",
            "transfer_id": transfer_id,
            "user_id": transfer.user_id,
            "domain": transfer.domain,
        })
        
        return TransferResponse(**transfer.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting transfer {transfer_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=List[TransferResponse])
async def list_transfers(
    user_id: str = Query(..., description="ID of the user"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
):
    """
    List domain transfers for a user.
    
    Args:
        user_id: ID of the user
        domain: Filter by domain
        
    Returns:
        List of domain transfers
    """
    try:
        # Get domain transfer service
        service = await get_domain_transfer_service()
        
        # Get transfers
        if domain:
            # Get transfers for domain
            domain_transfers = await service.get_transfers_for_domain(domain)
            
            # Filter by user
            transfers = [
                transfer for transfer in domain_transfers
                if transfer.user_id == user_id
            ]
        else:
            # Get transfers for user
            transfers = await service.get_transfers_for_user(user_id)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "domain_transfer_api",
            "operation": "list",
            "user_id": user_id,
            "domain": domain,
            "count": len(transfers),
        })
        
        return [TransferResponse(**transfer.to_dict()) for transfer in transfers]
    except Exception as e:
        logger.error(f"Error listing transfers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{transfer_id}/verify", response_model=TransferResponse)
async def verify_ownership(
    transfer_id: str = Path(..., description="ID of the transfer to verify"),
):
    """
    Verify domain ownership.
    
    Args:
        transfer_id: ID of the transfer to verify
        
    Returns:
        Updated domain transfer
    """
    try:
        # Get domain transfer service
        service = await get_domain_transfer_service()
        
        # Verify ownership
        updated_transfer = await service.verify_ownership(transfer_id)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "domain_transfer_api",
            "operation": "verify_ownership",
            "transfer_id": transfer_id,
            "user_id": updated_transfer.user_id,
            "domain": updated_transfer.domain,
        })
        
        return TransferResponse(**updated_transfer.to_dict())
    except TransferError as e:
        logger.error(f"Error verifying ownership: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error verifying ownership: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{transfer_id}/transfer-dns", response_model=TransferResponse)
async def transfer_dns_records(
    transfer_id: str = Path(..., description="ID of the transfer to process"),
):
    """
    Transfer DNS records from source to target.
    
    Args:
        transfer_id: ID of the transfer to process
        
    Returns:
        Updated domain transfer
    """
    try:
        # Get domain transfer service
        service = await get_domain_transfer_service()
        
        # Transfer DNS records
        updated_transfer = await service.transfer_dns_records(transfer_id)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "domain_transfer_api",
            "operation": "transfer_dns_records",
            "transfer_id": transfer_id,
            "user_id": updated_transfer.user_id,
            "domain": updated_transfer.domain,
        })
        
        return TransferResponse(**updated_transfer.to_dict())
    except TransferError as e:
        logger.error(f"Error transferring DNS records: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error transferring DNS records: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{transfer_id}/update-nameservers", response_model=TransferResponse)
async def update_nameservers(
    transfer_id: str = Path(..., description="ID of the transfer to update"),
    nameservers: NameserversUpdate = Body(...),
):
    """
    Update nameservers for the domain.
    
    Args:
        transfer_id: ID of the transfer to update
        nameservers: Nameservers to set
        
    Returns:
        Updated domain transfer
    """
    try:
        # Get domain transfer service
        service = await get_domain_transfer_service()
        
        # Update nameservers
        updated_transfer = await service.update_nameservers(
            transfer_id=transfer_id,
            nameservers=nameservers.nameservers,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "domain_transfer_api",
            "operation": "update_nameservers",
            "transfer_id": transfer_id,
            "user_id": updated_transfer.user_id,
            "domain": updated_transfer.domain,
        })
        
        return TransferResponse(**updated_transfer.to_dict())
    except TransferError as e:
        logger.error(f"Error updating nameservers: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating nameservers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{transfer_id}/migrate-settings", response_model=TransferResponse)
async def migrate_app_settings(
    transfer_id: str = Path(..., description="ID of the transfer to migrate"),
    migration: AppSettingsMigration = Body(...),
):
    """
    Migrate application settings from source to target.
    
    Args:
        transfer_id: ID of the transfer to migrate
        migration: Application settings migration
        
    Returns:
        Updated domain transfer
    """
    try:
        # Get domain transfer service
        service = await get_domain_transfer_service()
        
        # Migrate application settings
        updated_transfer = await service.migrate_app_settings(
            transfer_id=transfer_id,
            app_id=migration.app_id,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "domain_transfer_api",
            "operation": "migrate_app_settings",
            "transfer_id": transfer_id,
            "user_id": updated_transfer.user_id,
            "domain": updated_transfer.domain,
            "app_id": migration.app_id,
        })
        
        return TransferResponse(**updated_transfer.to_dict())
    except TransferError as e:
        logger.error(f"Error migrating application settings: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error migrating application settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{transfer_id}")
async def delete_transfer(
    transfer_id: str = Path(..., description="ID of the transfer to delete"),
):
    """
    Delete a domain transfer.
    
    Args:
        transfer_id: ID of the transfer to delete
        
    Returns:
        Success message
    """
    try:
        # Get domain transfer service
        service = await get_domain_transfer_service()
        
        # Get transfer for logging
        transfer = await service.get_transfer(transfer_id)
        
        if not transfer:
            raise HTTPException(status_code=404, detail=f"Transfer {transfer_id} not found")
        
        # Delete transfer
        success = await service.delete_transfer(transfer_id)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to delete transfer {transfer_id}")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "domain_transfer_api",
            "operation": "delete",
            "transfer_id": transfer_id,
            "user_id": transfer.user_id,
            "domain": transfer.domain,
        })
        
        return {"message": f"Transfer {transfer_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting transfer {transfer_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
