"""
Automatic DNS configuration service.

This module provides functionality for automatically configuring DNS records
for applications deployed on OrbitHost.
"""
import logging
import uuid
from typing import Any, Dict, List, Optional, Union

from app.services.domains.credential_storage import (
    get_credential_storage,
    APICredential,
    ProviderType,
)
from app.services.domains.dns_providers import get_dns_provider
from app.services.domains.dns_providers.base import DNSRecord, RecordType
from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

class DNSConfigurationError(Exception):
    """Exception raised for DNS configuration errors."""
    pass

class DNSConfigurator:
    """Service for automatically configuring DNS records."""
    
    def __init__(self):
        """Initialize the DNS configurator."""
        logger.info("Initialized DNS configurator")
    
    async def configure_app_domain(
        self,
        user_id: str,
        app_id: str,
        domain: str,
        subdomain: str,
        target_ip: str,
        credential_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Configure DNS records for an application domain.
        
        Args:
            user_id: ID of the user
            app_id: ID of the application
            domain: Domain name
            subdomain: Subdomain name
            target_ip: Target IP address
            credential_id: ID of the credential to use (optional)
            
        Returns:
            Configuration result
        """
        try:
            # Get credential storage
            storage = await get_credential_storage()
            
            # If credential_id is not provided, find a suitable credential
            if not credential_id:
                credentials = await storage.get_credentials_for_user(
                    user_id=user_id,
                    provider_type=ProviderType.DNS_PROVIDER,
                )
                
                if not credentials:
                    raise DNSConfigurationError("No DNS provider credentials found for user")
                
                # Use the first credential
                credential = credentials[0]
                credential_id = credential.id
            else:
                # Get the specified credential
                credential = await storage.get_credential(credential_id, decrypt=True)
                
                if not credential:
                    raise DNSConfigurationError(f"Credential {credential_id} not found")
            
            # Get DNS provider
            provider = get_dns_provider(credential.provider_type)
            
            # Find the zone for the domain
            zones = await provider.get_zones(credential)
            zone_id = None
            
            for zone in zones:
                if zone["name"] == domain:
                    zone_id = zone["id"]
                    break
            
            if not zone_id:
                raise DNSConfigurationError(f"Zone for domain {domain} not found")
            
            # Prepare record name
            record_name = subdomain if subdomain else "@"
            
            # Check if record already exists
            existing_records = await provider.get_records(
                credential,
                zone_id,
                RecordType.A,
            )
            
            existing_record = None
            for record in existing_records:
                if record.name == record_name:
                    existing_record = record
                    break
            
            # Create or update record
            if existing_record:
                # Update existing record
                updated_record = DNSRecord(
                    id=existing_record.id,
                    domain=domain,
                    name=record_name,
                    type=RecordType.A,
                    content=target_ip,
                    ttl=3600,
                    proxied=False,
                )
                
                result_record = await provider.update_record(
                    credential,
                    zone_id,
                    existing_record.id,
                    updated_record,
                )
                
                operation = "update"
            else:
                # Create new record
                new_record = DNSRecord(
                    id=str(uuid.uuid4()),
                    domain=domain,
                    name=record_name,
                    type=RecordType.A,
                    content=target_ip,
                    ttl=3600,
                    proxied=False,
                )
                
                result_record = await provider.create_record(
                    credential,
                    zone_id,
                    new_record,
                )
                
                operation = "create"
            
            # Update last used timestamp
            await storage.update_last_used(credential_id)
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_configurator",
                "operation": operation,
                "status": "success",
                "credential_id": credential_id,
                "user_id": user_id,
                "app_id": app_id,
                "domain": domain,
                "subdomain": subdomain,
                "record_type": "A",
                "target_ip": target_ip,
            })
            
            # Prepare result
            result = {
                "status": "success",
                "operation": operation,
                "domain": domain,
                "subdomain": subdomain,
                "record": result_record.to_dict(),
                "fqdn": f"{subdomain}.{domain}" if subdomain else domain,
            }
            
            return result
        except DNSConfigurationError as e:
            logger.error(f"DNS configuration error: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_configurator",
                "operation": "configure",
                "status": "error",
                "user_id": user_id,
                "app_id": app_id,
                "domain": domain,
                "subdomain": subdomain,
                "error": str(e),
            })
            
            raise
        except Exception as e:
            logger.error(f"Error configuring DNS for app {app_id}: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_configurator",
                "operation": "configure",
                "status": "error",
                "user_id": user_id,
                "app_id": app_id,
                "domain": domain,
                "subdomain": subdomain,
                "error": str(e),
            })
            
            raise DNSConfigurationError(f"Failed to configure DNS: {str(e)}")
    
    async def remove_app_domain(
        self,
        user_id: str,
        app_id: str,
        domain: str,
        subdomain: str,
        credential_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Remove DNS records for an application domain.
        
        Args:
            user_id: ID of the user
            app_id: ID of the application
            domain: Domain name
            subdomain: Subdomain name
            credential_id: ID of the credential to use (optional)
            
        Returns:
            Removal result
        """
        try:
            # Get credential storage
            storage = await get_credential_storage()
            
            # If credential_id is not provided, find a suitable credential
            if not credential_id:
                credentials = await storage.get_credentials_for_user(
                    user_id=user_id,
                    provider_type=ProviderType.DNS_PROVIDER,
                )
                
                if not credentials:
                    raise DNSConfigurationError("No DNS provider credentials found for user")
                
                # Use the first credential
                credential = credentials[0]
                credential_id = credential.id
            else:
                # Get the specified credential
                credential = await storage.get_credential(credential_id, decrypt=True)
                
                if not credential:
                    raise DNSConfigurationError(f"Credential {credential_id} not found")
            
            # Get DNS provider
            provider = get_dns_provider(credential.provider_type)
            
            # Find the zone for the domain
            zones = await provider.get_zones(credential)
            zone_id = None
            
            for zone in zones:
                if zone["name"] == domain:
                    zone_id = zone["id"]
                    break
            
            if not zone_id:
                raise DNSConfigurationError(f"Zone for domain {domain} not found")
            
            # Prepare record name
            record_name = subdomain if subdomain else "@"
            
            # Check if record exists
            existing_records = await provider.get_records(
                credential,
                zone_id,
                RecordType.A,
            )
            
            existing_record = None
            for record in existing_records:
                if record.name == record_name:
                    existing_record = record
                    break
            
            if not existing_record:
                # Record not found, nothing to do
                return {
                    "status": "success",
                    "operation": "none",
                    "domain": domain,
                    "subdomain": subdomain,
                    "message": "Record not found, nothing to remove",
                }
            
            # Delete record
            success = await provider.delete_record(
                credential,
                zone_id,
                existing_record.id,
            )
            
            if not success:
                raise DNSConfigurationError(f"Failed to delete record for {record_name}.{domain}")
            
            # Update last used timestamp
            await storage.update_last_used(credential_id)
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_configurator",
                "operation": "remove",
                "status": "success",
                "credential_id": credential_id,
                "user_id": user_id,
                "app_id": app_id,
                "domain": domain,
                "subdomain": subdomain,
            })
            
            # Prepare result
            result = {
                "status": "success",
                "operation": "delete",
                "domain": domain,
                "subdomain": subdomain,
                "fqdn": f"{subdomain}.{domain}" if subdomain else domain,
            }
            
            return result
        except DNSConfigurationError as e:
            logger.error(f"DNS configuration error: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_configurator",
                "operation": "remove",
                "status": "error",
                "user_id": user_id,
                "app_id": app_id,
                "domain": domain,
                "subdomain": subdomain,
                "error": str(e),
            })
            
            raise
        except Exception as e:
            logger.error(f"Error removing DNS for app {app_id}: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_configurator",
                "operation": "remove",
                "status": "error",
                "user_id": user_id,
                "app_id": app_id,
                "domain": domain,
                "subdomain": subdomain,
                "error": str(e),
            })
            
            raise DNSConfigurationError(f"Failed to remove DNS configuration: {str(e)}")
    
    async def verify_domain_ownership(
        self,
        user_id: str,
        domain: str,
        verification_token: str,
        credential_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Verify domain ownership by adding a TXT record.
        
        Args:
            user_id: ID of the user
            domain: Domain name
            verification_token: Verification token
            credential_id: ID of the credential to use (optional)
            
        Returns:
            Verification result
        """
        try:
            # Get credential storage
            storage = await get_credential_storage()
            
            # If credential_id is not provided, find a suitable credential
            if not credential_id:
                credentials = await storage.get_credentials_for_user(
                    user_id=user_id,
                    provider_type=ProviderType.DNS_PROVIDER,
                )
                
                if not credentials:
                    raise DNSConfigurationError("No DNS provider credentials found for user")
                
                # Use the first credential
                credential = credentials[0]
                credential_id = credential.id
            else:
                # Get the specified credential
                credential = await storage.get_credential(credential_id, decrypt=True)
                
                if not credential:
                    raise DNSConfigurationError(f"Credential {credential_id} not found")
            
            # Get DNS provider
            provider = get_dns_provider(credential.provider_type)
            
            # Find the zone for the domain
            zones = await provider.get_zones(credential)
            zone_id = None
            
            for zone in zones:
                if zone["name"] == domain:
                    zone_id = zone["id"]
                    break
            
            if not zone_id:
                raise DNSConfigurationError(f"Zone for domain {domain} not found")
            
            # Prepare record name for verification
            record_name = "_orbithost-verification"
            
            # Check if verification record already exists
            existing_records = await provider.get_records(
                credential,
                zone_id,
                RecordType.TXT,
            )
            
            existing_record = None
            for record in existing_records:
                if record.name == record_name:
                    existing_record = record
                    break
            
            # Create or update verification record
            if existing_record:
                # Update existing record
                updated_record = DNSRecord(
                    id=existing_record.id,
                    domain=domain,
                    name=record_name,
                    type=RecordType.TXT,
                    content=f"orbithost-verification={verification_token}",
                    ttl=3600,
                    proxied=False,
                )
                
                result_record = await provider.update_record(
                    credential,
                    zone_id,
                    existing_record.id,
                    updated_record,
                )
                
                operation = "update"
            else:
                # Create new record
                new_record = DNSRecord(
                    id=str(uuid.uuid4()),
                    domain=domain,
                    name=record_name,
                    type=RecordType.TXT,
                    content=f"orbithost-verification={verification_token}",
                    ttl=3600,
                    proxied=False,
                )
                
                result_record = await provider.create_record(
                    credential,
                    zone_id,
                    new_record,
                )
                
                operation = "create"
            
            # Update last used timestamp
            await storage.update_last_used(credential_id)
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_configurator",
                "operation": "verify",
                "status": "success",
                "credential_id": credential_id,
                "user_id": user_id,
                "domain": domain,
                "record_type": "TXT",
            })
            
            # Prepare result
            result = {
                "status": "success",
                "operation": operation,
                "domain": domain,
                "record": result_record.to_dict(),
                "verification_token": verification_token,
                "verification_record": f"{record_name}.{domain}",
            }
            
            return result
        except DNSConfigurationError as e:
            logger.error(f"DNS configuration error: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_configurator",
                "operation": "verify",
                "status": "error",
                "user_id": user_id,
                "domain": domain,
                "error": str(e),
            })
            
            raise
        except Exception as e:
            logger.error(f"Error verifying domain ownership for {domain}: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_configurator",
                "operation": "verify",
                "status": "error",
                "user_id": user_id,
                "domain": domain,
                "error": str(e),
            })
            
            raise DNSConfigurationError(f"Failed to verify domain ownership: {str(e)}")

# Singleton instance
_dns_configurator = None

async def get_dns_configurator() -> DNSConfigurator:
    """
    Get the DNS configurator instance.
    
    Returns:
        DNS configurator instance
    """
    global _dns_configurator
    
    if _dns_configurator is None:
        _dns_configurator = DNSConfigurator()
    
    return _dns_configurator
