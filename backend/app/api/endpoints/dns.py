"""
API endpoints for DNS management.

This module provides API endpoints for managing DNS records through various DNS providers.
"""
import logging
import uuid
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from app.services.domains.credential_storage import (
    get_credential_storage,
    APICredential,
    ProviderType,
)
from app.services.domains.dns_providers import get_dns_provider
from app.services.domains.dns_providers.base import DNSRecord, RecordType
from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

# Create API router for DNS management
router = APIRouter(prefix="/api/dns", tags=["dns"])

# Pydantic models for API
class ZoneResponse(BaseModel):
    """Model for DNS zone response."""
    id: str = Field(..., description="Zone ID")
    name: str = Field(..., description="Zone name (domain)")
    status: str = Field(..., description="Zone status")
    name_servers: List[str] = Field(default_factory=list, description="Name servers")

class DNSRecordCreate(BaseModel):
    """Model for creating a DNS record."""
    name: str = Field(..., description="Record name (e.g., www)")
    type: str = Field(..., description="Record type")
    content: str = Field(..., description="Record content (e.g., IP address)")
    ttl: int = Field(3600, description="Time to live in seconds")
    priority: Optional[int] = Field(None, description="Priority (for MX and SRV records)")
    proxied: bool = Field(False, description="Whether the record is proxied (Cloudflare-specific)")

class DNSRecordUpdate(BaseModel):
    """Model for updating a DNS record."""
    name: Optional[str] = Field(None, description="Record name (e.g., www)")
    type: Optional[str] = Field(None, description="Record type")
    content: Optional[str] = Field(None, description="Record content (e.g., IP address)")
    ttl: Optional[int] = Field(None, description="Time to live in seconds")
    priority: Optional[int] = Field(None, description="Priority (for MX and SRV records)")
    proxied: Optional[bool] = Field(None, description="Whether the record is proxied (Cloudflare-specific)")

class DNSRecordResponse(BaseModel):
    """Model for DNS record response."""
    id: str = Field(..., description="Record ID")
    domain: str = Field(..., description="Domain name")
    name: str = Field(..., description="Record name (e.g., www)")
    type: str = Field(..., description="Record type")
    content: str = Field(..., description="Record content (e.g., IP address)")
    ttl: int = Field(..., description="Time to live in seconds")
    priority: Optional[int] = Field(None, description="Priority (for MX and SRV records)")
    proxied: bool = Field(..., description="Whether the record is proxied (Cloudflare-specific)")

@router.get("/zones", response_model=List[ZoneResponse])
async def list_zones(
    credential_id: str = Query(..., description="ID of the credential to use"),
):
    """
    List all DNS zones (domains) for the account.
    
    Args:
        credential_id: ID of the credential to use
        
    Returns:
        List of DNS zones
    """
    try:
        # Get credential
        storage = await get_credential_storage()
        credential = await storage.get_credential(credential_id, decrypt=True)
        
        if not credential:
            raise HTTPException(status_code=404, detail=f"Credential {credential_id} not found")
        
        # Get DNS provider
        provider = get_dns_provider(credential.provider_type)
        
        # Get zones
        zones = await provider.get_zones(credential)
        
        # Update last used timestamp
        await storage.update_last_used(credential_id)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_api",
            "operation": "list_zones",
            "credential_id": credential_id,
            "user_id": credential.user_id,
            "provider": credential.provider.value,
            "provider_type": credential.provider_type.value,
            "zone_count": len(zones),
        })
        
        return zones
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Error listing zones: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing zones: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/zones/{zone_id}", response_model=ZoneResponse)
async def get_zone(
    zone_id: str = Path(..., description="ID of the zone to get"),
    credential_id: str = Query(..., description="ID of the credential to use"),
):
    """
    Get a specific DNS zone (domain).
    
    Args:
        zone_id: ID of the zone to get
        credential_id: ID of the credential to use
        
    Returns:
        DNS zone
    """
    try:
        # Get credential
        storage = await get_credential_storage()
        credential = await storage.get_credential(credential_id, decrypt=True)
        
        if not credential:
            raise HTTPException(status_code=404, detail=f"Credential {credential_id} not found")
        
        # Get DNS provider
        provider = get_dns_provider(credential.provider_type)
        
        # Get zone
        zone = await provider.get_zone(credential, zone_id)
        
        # Update last used timestamp
        await storage.update_last_used(credential_id)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_api",
            "operation": "get_zone",
            "credential_id": credential_id,
            "user_id": credential.user_id,
            "provider": credential.provider.value,
            "provider_type": credential.provider_type.value,
            "zone_id": zone_id,
        })
        
        return zone
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Error getting zone {zone_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting zone {zone_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/zones/{zone_id}/records", response_model=List[DNSRecordResponse])
async def list_records(
    zone_id: str = Path(..., description="ID of the zone to get records for"),
    credential_id: str = Query(..., description="ID of the credential to use"),
    record_type: Optional[str] = Query(None, description="Filter by record type"),
):
    """
    List all DNS records for a zone.
    
    Args:
        zone_id: ID of the zone to get records for
        credential_id: ID of the credential to use
        record_type: Filter by record type
        
    Returns:
        List of DNS records
    """
    try:
        # Get credential
        storage = await get_credential_storage()
        credential = await storage.get_credential(credential_id, decrypt=True)
        
        if not credential:
            raise HTTPException(status_code=404, detail=f"Credential {credential_id} not found")
        
        # Get DNS provider
        provider = get_dns_provider(credential.provider_type)
        
        # Convert record_type to enum if provided
        record_type_enum = RecordType(record_type) if record_type else None
        
        # Get records
        records = await provider.get_records(credential, zone_id, record_type_enum)
        
        # Update last used timestamp
        await storage.update_last_used(credential_id)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_api",
            "operation": "list_records",
            "credential_id": credential_id,
            "user_id": credential.user_id,
            "provider": credential.provider.value,
            "provider_type": credential.provider_type.value,
            "zone_id": zone_id,
            "record_type": record_type,
            "record_count": len(records),
        })
        
        return [DNSRecordResponse(**record.to_dict()) for record in records]
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Error listing records for zone {zone_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing records for zone {zone_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/zones/{zone_id}/records/{record_id}", response_model=DNSRecordResponse)
async def get_record(
    zone_id: str = Path(..., description="ID of the zone to get record from"),
    record_id: str = Path(..., description="ID of the record to get"),
    credential_id: str = Query(..., description="ID of the credential to use"),
):
    """
    Get a specific DNS record.
    
    Args:
        zone_id: ID of the zone to get record from
        record_id: ID of the record to get
        credential_id: ID of the credential to use
        
    Returns:
        DNS record
    """
    try:
        # Get credential
        storage = await get_credential_storage()
        credential = await storage.get_credential(credential_id, decrypt=True)
        
        if not credential:
            raise HTTPException(status_code=404, detail=f"Credential {credential_id} not found")
        
        # Get DNS provider
        provider = get_dns_provider(credential.provider_type)
        
        # Get record
        record = await provider.get_record(credential, zone_id, record_id)
        
        # Update last used timestamp
        await storage.update_last_used(credential_id)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_api",
            "operation": "get_record",
            "credential_id": credential_id,
            "user_id": credential.user_id,
            "provider": credential.provider.value,
            "provider_type": credential.provider_type.value,
            "zone_id": zone_id,
            "record_id": record_id,
        })
        
        return DNSRecordResponse(**record.to_dict())
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Error getting record {record_id} for zone {zone_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting record {record_id} for zone {zone_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/zones/{zone_id}/records", response_model=DNSRecordResponse)
async def create_record(
    zone_id: str = Path(..., description="ID of the zone to create record in"),
    credential_id: str = Query(..., description="ID of the credential to use"),
    record: DNSRecordCreate = Body(...),
):
    """
    Create a DNS record.
    
    Args:
        zone_id: ID of the zone to create record in
        credential_id: ID of the credential to use
        record: DNS record to create
        
    Returns:
        Created DNS record
    """
    try:
        # Get credential
        storage = await get_credential_storage()
        credential = await storage.get_credential(credential_id, decrypt=True)
        
        if not credential:
            raise HTTPException(status_code=404, detail=f"Credential {credential_id} not found")
        
        # Get DNS provider
        provider = get_dns_provider(credential.provider_type)
        
        # Get zone details to get the domain name
        zone = await provider.get_zone(credential, zone_id)
        domain = zone["name"]
        
        # Create record
        record_id = str(uuid.uuid4())
        dns_record = DNSRecord(
            id=record_id,
            domain=domain,
            name=record.name,
            type=RecordType(record.type),
            content=record.content,
            ttl=record.ttl,
            priority=record.priority,
            proxied=record.proxied,
        )
        
        created_record = await provider.create_record(credential, zone_id, dns_record)
        
        # Update last used timestamp
        await storage.update_last_used(credential_id)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_api",
            "operation": "create_record",
            "credential_id": credential_id,
            "user_id": credential.user_id,
            "provider": credential.provider.value,
            "provider_type": credential.provider_type.value,
            "zone_id": zone_id,
            "record_type": record.type,
            "record_name": record.name,
        })
        
        return DNSRecordResponse(**created_record.to_dict())
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Error creating record for zone {zone_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating record for zone {zone_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/zones/{zone_id}/records/{record_id}", response_model=DNSRecordResponse)
async def update_record(
    zone_id: str = Path(..., description="ID of the zone to update record in"),
    record_id: str = Path(..., description="ID of the record to update"),
    credential_id: str = Query(..., description="ID of the credential to use"),
    record_update: DNSRecordUpdate = Body(...),
):
    """
    Update a DNS record.
    
    Args:
        zone_id: ID of the zone to update record in
        record_id: ID of the record to update
        credential_id: ID of the credential to use
        record_update: DNS record update
        
    Returns:
        Updated DNS record
    """
    try:
        # Get credential
        storage = await get_credential_storage()
        credential = await storage.get_credential(credential_id, decrypt=True)
        
        if not credential:
            raise HTTPException(status_code=404, detail=f"Credential {credential_id} not found")
        
        # Get DNS provider
        provider = get_dns_provider(credential.provider_type)
        
        # Get existing record
        existing_record = await provider.get_record(credential, zone_id, record_id)
        
        # Apply updates
        updated_record = DNSRecord(
            id=record_id,
            domain=existing_record.domain,
            name=record_update.name if record_update.name is not None else existing_record.name,
            type=RecordType(record_update.type) if record_update.type is not None else existing_record.type,
            content=record_update.content if record_update.content is not None else existing_record.content,
            ttl=record_update.ttl if record_update.ttl is not None else existing_record.ttl,
            priority=record_update.priority if record_update.priority is not None else existing_record.priority,
            proxied=record_update.proxied if record_update.proxied is not None else existing_record.proxied,
        )
        
        # Update record
        updated_record = await provider.update_record(credential, zone_id, record_id, updated_record)
        
        # Update last used timestamp
        await storage.update_last_used(credential_id)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_api",
            "operation": "update_record",
            "credential_id": credential_id,
            "user_id": credential.user_id,
            "provider": credential.provider.value,
            "provider_type": credential.provider_type.value,
            "zone_id": zone_id,
            "record_id": record_id,
            "record_type": updated_record.type.value,
            "record_name": updated_record.name,
        })
        
        return DNSRecordResponse(**updated_record.to_dict())
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Error updating record {record_id} for zone {zone_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating record {record_id} for zone {zone_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/zones/{zone_id}/records/{record_id}")
async def delete_record(
    zone_id: str = Path(..., description="ID of the zone to delete record from"),
    record_id: str = Path(..., description="ID of the record to delete"),
    credential_id: str = Query(..., description="ID of the credential to use"),
):
    """
    Delete a DNS record.
    
    Args:
        zone_id: ID of the zone to delete record from
        record_id: ID of the record to delete
        credential_id: ID of the credential to use
        
    Returns:
        Success message
    """
    try:
        # Get credential
        storage = await get_credential_storage()
        credential = await storage.get_credential(credential_id, decrypt=True)
        
        if not credential:
            raise HTTPException(status_code=404, detail=f"Credential {credential_id} not found")
        
        # Get DNS provider
        provider = get_dns_provider(credential.provider_type)
        
        # Delete record
        success = await provider.delete_record(credential, zone_id, record_id)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to delete record {record_id}")
        
        # Update last used timestamp
        await storage.update_last_used(credential_id)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_api",
            "operation": "delete_record",
            "credential_id": credential_id,
            "user_id": credential.user_id,
            "provider": credential.provider.value,
            "provider_type": credential.provider_type.value,
            "zone_id": zone_id,
            "record_id": record_id,
        })
        
        return {"message": f"Record {record_id} deleted successfully"}
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Error deleting record {record_id} for zone {zone_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error deleting record {record_id} for zone {zone_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
