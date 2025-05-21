"""
API endpoints for manual DNS configuration.

This module provides API endpoints for generating and managing manual DNS configuration
instructions for registrars that don't have API access or aren't directly supported by OrbitHost.
"""
import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from app.services.domains.manual_dns import (
    get_manual_dns_service,
    ManualDNSRecord,
    ManualDNSConfiguration,
    RegistrarTemplate,
    RecordType,
)
from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

# Create API router for manual DNS
router = APIRouter(prefix="/api/manual-dns", tags=["manual-dns"])

# Pydantic models for API
class DNSRecordCreate(BaseModel):
    """Model for creating a DNS record."""
    name: str = Field(..., description="Record name (e.g., www)")
    type: str = Field(..., description="Record type")
    content: str = Field(..., description="Record content (e.g., IP address)")
    ttl: int = Field(3600, description="Time to live in seconds")
    priority: Optional[int] = Field(None, description="Priority (for MX and SRV records)")

class DNSRecordResponse(BaseModel):
    """Model for DNS record response."""
    id: str = Field(..., description="Record ID")
    domain: str = Field(..., description="Domain name")
    name: str = Field(..., description="Record name (e.g., www)")
    type: str = Field(..., description="Record type")
    content: str = Field(..., description="Record content (e.g., IP address)")
    ttl: int = Field(..., description="Time to live in seconds")
    priority: Optional[int] = Field(None, description="Priority (for MX and SRV records)")

class ConfigurationCreate(BaseModel):
    """Model for creating a manual DNS configuration."""
    user_id: str = Field(..., description="ID of the user")
    domain: str = Field(..., description="Domain name")
    app_id: str = Field(..., description="ID of the application")
    target_ip: str = Field(..., description="Target IP address")
    registrar: Optional[str] = Field(None, description="Domain registrar")
    notes: Optional[str] = Field(None, description="Additional notes")

class ConfigurationUpdate(BaseModel):
    """Model for updating a manual DNS configuration."""
    registrar: Optional[str] = Field(None, description="Domain registrar")
    notes: Optional[str] = Field(None, description="Additional notes")
    nameservers: Optional[List[str]] = Field(None, description="Nameservers")
    records: Optional[List[DNSRecordCreate]] = Field(None, description="DNS records")

class ConfigurationResponse(BaseModel):
    """Model for manual DNS configuration response."""
    id: str = Field(..., description="Configuration ID")
    user_id: str = Field(..., description="ID of the user")
    domain: str = Field(..., description="Domain name")
    app_id: str = Field(..., description="ID of the application")
    records: List[DNSRecordResponse] = Field(..., description="DNS records")
    nameservers: List[str] = Field(..., description="Nameservers")
    registrar: Optional[str] = Field(None, description="Domain registrar")
    notes: Optional[str] = Field(None, description="Additional notes")

class TemplateResponse(BaseModel):
    """Model for registrar template response."""
    registrar: str = Field(..., description="Registrar name")
    instructions: str = Field(..., description="Step-by-step instructions")
    screenshots: List[str] = Field(..., description="URLs to screenshots")
    url: Optional[str] = Field(None, description="URL to registrar's DNS management page")

class InstructionsResponse(BaseModel):
    """Model for manual DNS configuration instructions response."""
    config_id: str = Field(..., description="Configuration ID")
    domain: str = Field(..., description="Domain name")
    registrar: Optional[str] = Field(None, description="Domain registrar")
    template: TemplateResponse = Field(..., description="Registrar template")
    records: List[Dict[str, Any]] = Field(..., description="DNS records")
    nameservers: List[str] = Field(..., description="Nameservers")
    notes: Optional[str] = Field(None, description="Additional notes")

@router.post("", response_model=ConfigurationResponse)
async def create_configuration(
    configuration: ConfigurationCreate = Body(...),
):
    """
    Create a new manual DNS configuration.
    
    Args:
        configuration: Manual DNS configuration to create
        
    Returns:
        Created manual DNS configuration
    """
    try:
        # Get manual DNS service
        service = await get_manual_dns_service()
        
        # Create configuration
        created_configuration = await service.create_configuration(
            user_id=configuration.user_id,
            domain=configuration.domain,
            app_id=configuration.app_id,
            target_ip=configuration.target_ip,
            registrar=configuration.registrar,
            notes=configuration.notes,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "manual_dns_api",
            "operation": "create",
            "config_id": created_configuration.id,
            "user_id": configuration.user_id,
            "domain": configuration.domain,
            "app_id": configuration.app_id,
        })
        
        # Convert to response model
        records_response = [
            DNSRecordResponse(
                id=record.id,
                domain=record.domain,
                name=record.name,
                type=record.type.value,
                content=record.content,
                ttl=record.ttl,
                priority=record.priority,
            )
            for record in created_configuration.records
        ]
        
        return ConfigurationResponse(
            id=created_configuration.id,
            user_id=created_configuration.user_id,
            domain=created_configuration.domain,
            app_id=created_configuration.app_id,
            records=records_response,
            nameservers=created_configuration.nameservers,
            registrar=created_configuration.registrar,
            notes=created_configuration.notes,
        )
    except ValueError as e:
        logger.error(f"Error creating configuration: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{config_id}", response_model=ConfigurationResponse)
async def get_configuration(
    config_id: str = Path(..., description="ID of the configuration to get"),
):
    """
    Get a manual DNS configuration by ID.
    
    Args:
        config_id: ID of the configuration to get
        
    Returns:
        Manual DNS configuration
    """
    try:
        # Get manual DNS service
        service = await get_manual_dns_service()
        
        # Get configuration
        configuration = await service.get_configuration(config_id)
        
        if not configuration:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "manual_dns_api",
            "operation": "get",
            "config_id": config_id,
            "user_id": configuration.user_id,
            "domain": configuration.domain,
            "app_id": configuration.app_id,
        })
        
        # Convert to response model
        records_response = [
            DNSRecordResponse(
                id=record.id,
                domain=record.domain,
                name=record.name,
                type=record.type.value,
                content=record.content,
                ttl=record.ttl,
                priority=record.priority,
            )
            for record in configuration.records
        ]
        
        return ConfigurationResponse(
            id=configuration.id,
            user_id=configuration.user_id,
            domain=configuration.domain,
            app_id=configuration.app_id,
            records=records_response,
            nameservers=configuration.nameservers,
            registrar=configuration.registrar,
            notes=configuration.notes,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting configuration {config_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=List[ConfigurationResponse])
async def list_configurations(
    user_id: str = Query(..., description="ID of the user"),
    domain: Optional[str] = Query(None, description="Filter by domain"),
    app_id: Optional[str] = Query(None, description="Filter by application ID"),
):
    """
    List manual DNS configurations.
    
    Args:
        user_id: ID of the user
        domain: Filter by domain
        app_id: Filter by application ID
        
    Returns:
        List of manual DNS configurations
    """
    try:
        # Get manual DNS service
        service = await get_manual_dns_service()
        
        # Get configurations
        if domain:
            # Get configurations for domain
            domain_configurations = await service.get_configurations_for_domain(domain)
            
            # Filter by user
            configurations = [
                config for config in domain_configurations
                if config.user_id == user_id
            ]
        elif app_id:
            # Get configurations for application
            app_configurations = await service.get_configurations_for_app(app_id)
            
            # Filter by user
            configurations = [
                config for config in app_configurations
                if config.user_id == user_id
            ]
        else:
            # Get configurations for user
            configurations = await service.get_configurations_for_user(user_id)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "manual_dns_api",
            "operation": "list",
            "user_id": user_id,
            "domain": domain,
            "app_id": app_id,
            "count": len(configurations),
        })
        
        # Convert to response models
        response = []
        
        for configuration in configurations:
            records_response = [
                DNSRecordResponse(
                    id=record.id,
                    domain=record.domain,
                    name=record.name,
                    type=record.type.value,
                    content=record.content,
                    ttl=record.ttl,
                    priority=record.priority,
                )
                for record in configuration.records
            ]
            
            response.append(
                ConfigurationResponse(
                    id=configuration.id,
                    user_id=configuration.user_id,
                    domain=configuration.domain,
                    app_id=configuration.app_id,
                    records=records_response,
                    nameservers=configuration.nameservers,
                    registrar=configuration.registrar,
                    notes=configuration.notes,
                )
            )
        
        return response
    except Exception as e:
        logger.error(f"Error listing configurations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{config_id}", response_model=ConfigurationResponse)
async def update_configuration(
    config_id: str = Path(..., description="ID of the configuration to update"),
    configuration_update: ConfigurationUpdate = Body(...),
):
    """
    Update a manual DNS configuration.
    
    Args:
        config_id: ID of the configuration to update
        configuration_update: Manual DNS configuration update
        
    Returns:
        Updated manual DNS configuration
    """
    try:
        # Get manual DNS service
        service = await get_manual_dns_service()
        
        # Get existing configuration
        existing_configuration = await service.get_configuration(config_id)
        
        if not existing_configuration:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")
        
        # Prepare updates
        updates = {}
        
        if configuration_update.registrar is not None:
            updates["registrar"] = configuration_update.registrar
        
        if configuration_update.notes is not None:
            updates["notes"] = configuration_update.notes
        
        if configuration_update.nameservers is not None:
            updates["nameservers"] = configuration_update.nameservers
        
        if configuration_update.records is not None:
            # Convert records to ManualDNSRecord objects
            records = []
            
            for record_data in configuration_update.records:
                record = ManualDNSRecord(
                    id=str(uuid.uuid4()),
                    domain=existing_configuration.domain,
                    name=record_data.name,
                    type=RecordType(record_data.type),
                    content=record_data.content,
                    ttl=record_data.ttl,
                    priority=record_data.priority,
                )
                
                records.append(record)
            
            updates["records"] = records
        
        # Update configuration
        updated_configuration = await service.update_configuration(
            config_id=config_id,
            updates=updates,
        )
        
        if not updated_configuration:
            raise HTTPException(status_code=500, detail=f"Failed to update configuration {config_id}")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "manual_dns_api",
            "operation": "update",
            "config_id": config_id,
            "user_id": updated_configuration.user_id,
            "domain": updated_configuration.domain,
            "app_id": updated_configuration.app_id,
        })
        
        # Convert to response model
        records_response = [
            DNSRecordResponse(
                id=record.id,
                domain=record.domain,
                name=record.name,
                type=record.type.value,
                content=record.content,
                ttl=record.ttl,
                priority=record.priority,
            )
            for record in updated_configuration.records
        ]
        
        return ConfigurationResponse(
            id=updated_configuration.id,
            user_id=updated_configuration.user_id,
            domain=updated_configuration.domain,
            app_id=updated_configuration.app_id,
            records=records_response,
            nameservers=updated_configuration.nameservers,
            registrar=updated_configuration.registrar,
            notes=updated_configuration.notes,
        )
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Error updating configuration {config_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating configuration {config_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{config_id}")
async def delete_configuration(
    config_id: str = Path(..., description="ID of the configuration to delete"),
):
    """
    Delete a manual DNS configuration.
    
    Args:
        config_id: ID of the configuration to delete
        
    Returns:
        Success message
    """
    try:
        # Get manual DNS service
        service = await get_manual_dns_service()
        
        # Get configuration for logging
        configuration = await service.get_configuration(config_id)
        
        if not configuration:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")
        
        # Delete configuration
        success = await service.delete_configuration(config_id)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to delete configuration {config_id}")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "manual_dns_api",
            "operation": "delete",
            "config_id": config_id,
            "user_id": configuration.user_id,
            "domain": configuration.domain,
            "app_id": configuration.app_id,
        })
        
        return {"message": f"Configuration {config_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting configuration {config_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{config_id}/instructions", response_model=InstructionsResponse)
async def get_instructions(
    config_id: str = Path(..., description="ID of the configuration to get instructions for"),
):
    """
    Get manual DNS configuration instructions.
    
    Args:
        config_id: ID of the configuration to get instructions for
        
    Returns:
        Manual DNS configuration instructions
    """
    try:
        # Get manual DNS service
        service = await get_manual_dns_service()
        
        # Get configuration
        configuration = await service.get_configuration(config_id)
        
        if not configuration:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")
        
        # Generate instructions
        instructions = await service.generate_instructions(config_id)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "manual_dns_api",
            "operation": "get_instructions",
            "config_id": config_id,
            "user_id": configuration.user_id,
            "domain": configuration.domain,
            "app_id": configuration.app_id,
        })
        
        return InstructionsResponse(**instructions)
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Error getting instructions for configuration {config_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting instructions for configuration {config_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/{registrar}", response_model=TemplateResponse)
async def get_template(
    registrar: str = Path(..., description="Registrar name"),
):
    """
    Get a registrar-specific template.
    
    Args:
        registrar: Registrar name
        
    Returns:
        Registrar template
    """
    try:
        # Get manual DNS service
        service = await get_manual_dns_service()
        
        # Get template
        template = await service.get_template(registrar)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "manual_dns_api",
            "operation": "get_template",
            "registrar": registrar,
        })
        
        return TemplateResponse(**template.to_dict())
    except Exception as e:
        logger.error(f"Error getting template for registrar {registrar}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
