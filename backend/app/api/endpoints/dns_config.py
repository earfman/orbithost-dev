"""
API endpoints for automatic DNS configuration.

This module provides API endpoints for automatically configuring DNS records
for applications deployed on OrbitHost.
"""
import logging
import uuid
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from app.services.domains.dns_configurator import (
    get_dns_configurator,
    DNSConfigurationError,
)
from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

# Create API router for DNS configuration
router = APIRouter(prefix="/api/dns-config", tags=["dns-config"])

# Pydantic models for API
class AppDomainConfig(BaseModel):
    """Model for configuring an application domain."""
    user_id: str = Field(..., description="ID of the user")
    app_id: str = Field(..., description="ID of the application")
    domain: str = Field(..., description="Domain name")
    subdomain: str = Field("", description="Subdomain name")
    target_ip: str = Field(..., description="Target IP address")
    credential_id: Optional[str] = Field(None, description="ID of the credential to use")

class DomainVerification(BaseModel):
    """Model for domain verification."""
    user_id: str = Field(..., description="ID of the user")
    domain: str = Field(..., description="Domain name")
    credential_id: Optional[str] = Field(None, description="ID of the credential to use")

class DomainVerificationResponse(BaseModel):
    """Model for domain verification response."""
    status: str = Field(..., description="Verification status")
    operation: str = Field(..., description="Operation performed")
    domain: str = Field(..., description="Domain name")
    verification_token: str = Field(..., description="Verification token")
    verification_record: str = Field(..., description="Verification record name")

class DNSConfigResponse(BaseModel):
    """Model for DNS configuration response."""
    status: str = Field(..., description="Configuration status")
    operation: str = Field(..., description="Operation performed")
    domain: str = Field(..., description="Domain name")
    subdomain: str = Field(..., description="Subdomain name")
    fqdn: str = Field(..., description="Fully qualified domain name")

@router.post("/configure", response_model=DNSConfigResponse)
async def configure_app_domain(
    config: AppDomainConfig = Body(...),
):
    """
    Configure DNS records for an application domain.
    
    Args:
        config: Application domain configuration
        
    Returns:
        Configuration result
    """
    try:
        # Get DNS configurator
        configurator = await get_dns_configurator()
        
        # Configure domain
        result = await configurator.configure_app_domain(
            user_id=config.user_id,
            app_id=config.app_id,
            domain=config.domain,
            subdomain=config.subdomain,
            target_ip=config.target_ip,
            credential_id=config.credential_id,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_config_api",
            "operation": "configure",
            "status": "success",
            "user_id": config.user_id,
            "app_id": config.app_id,
            "domain": config.domain,
            "subdomain": config.subdomain,
        })
        
        return DNSConfigResponse(
            status=result["status"],
            operation=result["operation"],
            domain=result["domain"],
            subdomain=result["subdomain"],
            fqdn=result["fqdn"],
        )
    except DNSConfigurationError as e:
        logger.error(f"DNS configuration error: {str(e)}")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_config_api",
            "operation": "configure",
            "status": "error",
            "user_id": config.user_id,
            "app_id": config.app_id,
            "domain": config.domain,
            "subdomain": config.subdomain,
            "error": str(e),
        })
        
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error configuring DNS: {str(e)}")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_config_api",
            "operation": "configure",
            "status": "error",
            "user_id": config.user_id,
            "app_id": config.app_id,
            "domain": config.domain,
            "subdomain": config.subdomain,
            "error": str(e),
        })
        
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/remove", response_model=DNSConfigResponse)
async def remove_app_domain(
    config: AppDomainConfig = Body(...),
):
    """
    Remove DNS records for an application domain.
    
    Args:
        config: Application domain configuration
        
    Returns:
        Removal result
    """
    try:
        # Get DNS configurator
        configurator = await get_dns_configurator()
        
        # Remove domain
        result = await configurator.remove_app_domain(
            user_id=config.user_id,
            app_id=config.app_id,
            domain=config.domain,
            subdomain=config.subdomain,
            credential_id=config.credential_id,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_config_api",
            "operation": "remove",
            "status": "success",
            "user_id": config.user_id,
            "app_id": config.app_id,
            "domain": config.domain,
            "subdomain": config.subdomain,
        })
        
        return DNSConfigResponse(
            status=result["status"],
            operation=result["operation"],
            domain=result["domain"],
            subdomain=result["subdomain"],
            fqdn=result["fqdn"],
        )
    except DNSConfigurationError as e:
        logger.error(f"DNS configuration error: {str(e)}")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_config_api",
            "operation": "remove",
            "status": "error",
            "user_id": config.user_id,
            "app_id": config.app_id,
            "domain": config.domain,
            "subdomain": config.subdomain,
            "error": str(e),
        })
        
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error removing DNS: {str(e)}")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_config_api",
            "operation": "remove",
            "status": "error",
            "user_id": config.user_id,
            "app_id": config.app_id,
            "domain": config.domain,
            "subdomain": config.subdomain,
            "error": str(e),
        })
        
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/verify", response_model=DomainVerificationResponse)
async def verify_domain_ownership(
    verification: DomainVerification = Body(...),
):
    """
    Verify domain ownership by adding a TXT record.
    
    Args:
        verification: Domain verification configuration
        
    Returns:
        Verification result
    """
    try:
        # Generate verification token
        verification_token = str(uuid.uuid4())
        
        # Get DNS configurator
        configurator = await get_dns_configurator()
        
        # Verify domain
        result = await configurator.verify_domain_ownership(
            user_id=verification.user_id,
            domain=verification.domain,
            verification_token=verification_token,
            credential_id=verification.credential_id,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_config_api",
            "operation": "verify",
            "status": "success",
            "user_id": verification.user_id,
            "domain": verification.domain,
        })
        
        return DomainVerificationResponse(
            status=result["status"],
            operation=result["operation"],
            domain=result["domain"],
            verification_token=result["verification_token"],
            verification_record=result["verification_record"],
        )
    except DNSConfigurationError as e:
        logger.error(f"DNS configuration error: {str(e)}")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_config_api",
            "operation": "verify",
            "status": "error",
            "user_id": verification.user_id,
            "domain": verification.domain,
            "error": str(e),
        })
        
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error verifying domain: {str(e)}")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dns_config_api",
            "operation": "verify",
            "status": "error",
            "user_id": verification.user_id,
            "domain": verification.domain,
            "error": str(e),
        })
        
        raise HTTPException(status_code=500, detail=str(e))
