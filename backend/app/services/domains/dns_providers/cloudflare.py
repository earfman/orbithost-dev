"""
Cloudflare DNS provider implementation.

This module implements the Cloudflare DNS provider interface for managing DNS records.
"""
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Union

import httpx

from app.services.domains.credential_storage import APICredential
from app.services.domains.dns_providers.base import DNSProvider, DNSRecord, RecordType
from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

class CloudflareDNSProvider(DNSProvider):
    """Cloudflare DNS provider implementation."""
    
    def __init__(self):
        """Initialize the Cloudflare DNS provider."""
        self.base_url = "https://api.cloudflare.com/client/v4"
        logger.info("Initialized Cloudflare DNS provider")
    
    def _get_headers(self, credential: APICredential) -> Dict[str, str]:
        """
        Get headers for Cloudflare API requests.
        
        Args:
            credential: API credential
            
        Returns:
            Headers for API requests
        """
        # Decrypt credentials if encrypted
        if credential.encrypted:
            # In a real implementation, this would decrypt the credentials
            # For now, we'll assume they're not encrypted in this method
            pass
        
        # Check credential type
        if "api_token" in credential.credentials:
            # Use API token authentication
            return {
                "Authorization": f"Bearer {credential.credentials['api_token']}",
                "Content-Type": "application/json",
            }
        elif "api_key" in credential.credentials and "email" in credential.credentials:
            # Use API key authentication
            return {
                "X-Auth-Key": credential.credentials["api_key"],
                "X-Auth-Email": credential.credentials["email"],
                "Content-Type": "application/json",
            }
        else:
            raise ValueError("Invalid Cloudflare credentials")
    
    async def get_zones(self, credential: APICredential) -> List[Dict[str, Any]]:
        """
        Get all zones (domains) for the account.
        
        Args:
            credential: API credential
            
        Returns:
            List of zones
        """
        headers = self._get_headers(credential)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/zones",
                    headers=headers,
                )
                
                response.raise_for_status()
                data = response.json()
                
                if not data["success"]:
                    raise ValueError(f"Cloudflare API error: {data['errors']}")
                
                # Log to MCP
                await get_mcp_client().send({
                    "type": "dns_provider",
                    "provider": "cloudflare",
                    "operation": "get_zones",
                    "status": "success",
                    "zone_count": len(data["result"]),
                })
                
                return data["result"]
        except httpx.HTTPStatusError as e:
            logger.error(f"Cloudflare API error: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "cloudflare",
                "operation": "get_zones",
                "status": "error",
                "error": str(e),
            })
            
            raise ValueError(f"Cloudflare API error: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting Cloudflare zones: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "cloudflare",
                "operation": "get_zones",
                "status": "error",
                "error": str(e),
            })
            
            raise
    
    async def get_zone(self, credential: APICredential, zone_id: str) -> Dict[str, Any]:
        """
        Get a specific zone.
        
        Args:
            credential: API credential
            zone_id: Zone ID
            
        Returns:
            Zone details
        """
        headers = self._get_headers(credential)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/zones/{zone_id}",
                    headers=headers,
                )
                
                response.raise_for_status()
                data = response.json()
                
                if not data["success"]:
                    raise ValueError(f"Cloudflare API error: {data['errors']}")
                
                # Log to MCP
                await get_mcp_client().send({
                    "type": "dns_provider",
                    "provider": "cloudflare",
                    "operation": "get_zone",
                    "status": "success",
                    "zone_id": zone_id,
                })
                
                return data["result"]
        except httpx.HTTPStatusError as e:
            logger.error(f"Cloudflare API error: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "cloudflare",
                "operation": "get_zone",
                "status": "error",
                "zone_id": zone_id,
                "error": str(e),
            })
            
            raise ValueError(f"Cloudflare API error: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting Cloudflare zone {zone_id}: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "cloudflare",
                "operation": "get_zone",
                "status": "error",
                "zone_id": zone_id,
                "error": str(e),
            })
            
            raise
    
    async def get_records(
        self,
        credential: APICredential,
        zone_id: str,
        record_type: Optional[RecordType] = None,
    ) -> List[DNSRecord]:
        """
        Get all DNS records for a zone.
        
        Args:
            credential: API credential
            zone_id: Zone ID
            record_type: Filter by record type
            
        Returns:
            List of DNS records
        """
        headers = self._get_headers(credential)
        params = {}
        
        if record_type:
            params["type"] = record_type.value
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/zones/{zone_id}/dns_records",
                    headers=headers,
                    params=params,
                )
                
                response.raise_for_status()
                data = response.json()
                
                if not data["success"]:
                    raise ValueError(f"Cloudflare API error: {data['errors']}")
                
                # Get zone details to get the domain name
                zone = await self.get_zone(credential, zone_id)
                domain = zone["name"]
                
                # Convert to DNSRecord objects
                records = []
                for record_data in data["result"]:
                    record = DNSRecord(
                        id=record_data["id"],
                        domain=domain,
                        name=record_data["name"],
                        type=RecordType(record_data["type"]),
                        content=record_data["content"],
                        ttl=record_data["ttl"],
                        priority=record_data.get("priority"),
                        proxied=record_data.get("proxied", False),
                    )
                    records.append(record)
                
                # Log to MCP
                await get_mcp_client().send({
                    "type": "dns_provider",
                    "provider": "cloudflare",
                    "operation": "get_records",
                    "status": "success",
                    "zone_id": zone_id,
                    "record_count": len(records),
                    "record_type": record_type.value if record_type else None,
                })
                
                return records
        except httpx.HTTPStatusError as e:
            logger.error(f"Cloudflare API error: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "cloudflare",
                "operation": "get_records",
                "status": "error",
                "zone_id": zone_id,
                "record_type": record_type.value if record_type else None,
                "error": str(e),
            })
            
            raise ValueError(f"Cloudflare API error: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting Cloudflare records for zone {zone_id}: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "cloudflare",
                "operation": "get_records",
                "status": "error",
                "zone_id": zone_id,
                "record_type": record_type.value if record_type else None,
                "error": str(e),
            })
            
            raise
    
    async def get_record(
        self,
        credential: APICredential,
        zone_id: str,
        record_id: str,
    ) -> DNSRecord:
        """
        Get a specific DNS record.
        
        Args:
            credential: API credential
            zone_id: Zone ID
            record_id: Record ID
            
        Returns:
            DNS record
        """
        headers = self._get_headers(credential)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/zones/{zone_id}/dns_records/{record_id}",
                    headers=headers,
                )
                
                response.raise_for_status()
                data = response.json()
                
                if not data["success"]:
                    raise ValueError(f"Cloudflare API error: {data['errors']}")
                
                # Get zone details to get the domain name
                zone = await self.get_zone(credential, zone_id)
                domain = zone["name"]
                
                # Convert to DNSRecord object
                record_data = data["result"]
                record = DNSRecord(
                    id=record_data["id"],
                    domain=domain,
                    name=record_data["name"],
                    type=RecordType(record_data["type"]),
                    content=record_data["content"],
                    ttl=record_data["ttl"],
                    priority=record_data.get("priority"),
                    proxied=record_data.get("proxied", False),
                )
                
                # Log to MCP
                await get_mcp_client().send({
                    "type": "dns_provider",
                    "provider": "cloudflare",
                    "operation": "get_record",
                    "status": "success",
                    "zone_id": zone_id,
                    "record_id": record_id,
                })
                
                return record
        except httpx.HTTPStatusError as e:
            logger.error(f"Cloudflare API error: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "cloudflare",
                "operation": "get_record",
                "status": "error",
                "zone_id": zone_id,
                "record_id": record_id,
                "error": str(e),
            })
            
            raise ValueError(f"Cloudflare API error: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting Cloudflare record {record_id} for zone {zone_id}: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "cloudflare",
                "operation": "get_record",
                "status": "error",
                "zone_id": zone_id,
                "record_id": record_id,
                "error": str(e),
            })
            
            raise
    
    async def create_record(
        self,
        credential: APICredential,
        zone_id: str,
        record: DNSRecord,
    ) -> DNSRecord:
        """
        Create a DNS record.
        
        Args:
            credential: API credential
            zone_id: Zone ID
            record: DNS record to create
            
        Returns:
            Created DNS record
        """
        headers = self._get_headers(credential)
        
        # Prepare request data
        data = {
            "type": record.type.value,
            "name": record.name,
            "content": record.content,
            "ttl": record.ttl,
            "proxied": record.proxied,
        }
        
        if record.priority is not None and record.type in [RecordType.MX, RecordType.SRV]:
            data["priority"] = record.priority
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/zones/{zone_id}/dns_records",
                    headers=headers,
                    json=data,
                )
                
                response.raise_for_status()
                response_data = response.json()
                
                if not response_data["success"]:
                    raise ValueError(f"Cloudflare API error: {response_data['errors']}")
                
                # Get zone details to get the domain name
                zone = await self.get_zone(credential, zone_id)
                domain = zone["name"]
                
                # Convert to DNSRecord object
                record_data = response_data["result"]
                created_record = DNSRecord(
                    id=record_data["id"],
                    domain=domain,
                    name=record_data["name"],
                    type=RecordType(record_data["type"]),
                    content=record_data["content"],
                    ttl=record_data["ttl"],
                    priority=record_data.get("priority"),
                    proxied=record_data.get("proxied", False),
                )
                
                # Log to MCP
                await get_mcp_client().send({
                    "type": "dns_provider",
                    "provider": "cloudflare",
                    "operation": "create_record",
                    "status": "success",
                    "zone_id": zone_id,
                    "record_type": record.type.value,
                    "record_name": record.name,
                })
                
                return created_record
        except httpx.HTTPStatusError as e:
            logger.error(f"Cloudflare API error: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "cloudflare",
                "operation": "create_record",
                "status": "error",
                "zone_id": zone_id,
                "record_type": record.type.value,
                "record_name": record.name,
                "error": str(e),
            })
            
            raise ValueError(f"Cloudflare API error: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating Cloudflare record for zone {zone_id}: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "cloudflare",
                "operation": "create_record",
                "status": "error",
                "zone_id": zone_id,
                "record_type": record.type.value,
                "record_name": record.name,
                "error": str(e),
            })
            
            raise
    
    async def update_record(
        self,
        credential: APICredential,
        zone_id: str,
        record_id: str,
        record: DNSRecord,
    ) -> DNSRecord:
        """
        Update a DNS record.
        
        Args:
            credential: API credential
            zone_id: Zone ID
            record_id: Record ID
            record: DNS record with updates
            
        Returns:
            Updated DNS record
        """
        headers = self._get_headers(credential)
        
        # Prepare request data
        data = {
            "type": record.type.value,
            "name": record.name,
            "content": record.content,
            "ttl": record.ttl,
            "proxied": record.proxied,
        }
        
        if record.priority is not None and record.type in [RecordType.MX, RecordType.SRV]:
            data["priority"] = record.priority
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/zones/{zone_id}/dns_records/{record_id}",
                    headers=headers,
                    json=data,
                )
                
                response.raise_for_status()
                response_data = response.json()
                
                if not response_data["success"]:
                    raise ValueError(f"Cloudflare API error: {response_data['errors']}")
                
                # Get zone details to get the domain name
                zone = await self.get_zone(credential, zone_id)
                domain = zone["name"]
                
                # Convert to DNSRecord object
                record_data = response_data["result"]
                updated_record = DNSRecord(
                    id=record_data["id"],
                    domain=domain,
                    name=record_data["name"],
                    type=RecordType(record_data["type"]),
                    content=record_data["content"],
                    ttl=record_data["ttl"],
                    priority=record_data.get("priority"),
                    proxied=record_data.get("proxied", False),
                )
                
                # Log to MCP
                await get_mcp_client().send({
                    "type": "dns_provider",
                    "provider": "cloudflare",
                    "operation": "update_record",
                    "status": "success",
                    "zone_id": zone_id,
                    "record_id": record_id,
                    "record_type": record.type.value,
                    "record_name": record.name,
                })
                
                return updated_record
        except httpx.HTTPStatusError as e:
            logger.error(f"Cloudflare API error: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "cloudflare",
                "operation": "update_record",
                "status": "error",
                "zone_id": zone_id,
                "record_id": record_id,
                "record_type": record.type.value,
                "record_name": record.name,
                "error": str(e),
            })
            
            raise ValueError(f"Cloudflare API error: {str(e)}")
        except Exception as e:
            logger.error(f"Error updating Cloudflare record {record_id} for zone {zone_id}: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "cloudflare",
                "operation": "update_record",
                "status": "error",
                "zone_id": zone_id,
                "record_id": record_id,
                "record_type": record.type.value,
                "record_name": record.name,
                "error": str(e),
            })
            
            raise
    
    async def delete_record(
        self,
        credential: APICredential,
        zone_id: str,
        record_id: str,
    ) -> bool:
        """
        Delete a DNS record.
        
        Args:
            credential: API credential
            zone_id: Zone ID
            record_id: Record ID
            
        Returns:
            Boolean indicating success or failure
        """
        headers = self._get_headers(credential)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/zones/{zone_id}/dns_records/{record_id}",
                    headers=headers,
                )
                
                response.raise_for_status()
                data = response.json()
                
                if not data["success"]:
                    raise ValueError(f"Cloudflare API error: {data['errors']}")
                
                # Log to MCP
                await get_mcp_client().send({
                    "type": "dns_provider",
                    "provider": "cloudflare",
                    "operation": "delete_record",
                    "status": "success",
                    "zone_id": zone_id,
                    "record_id": record_id,
                })
                
                return True
        except httpx.HTTPStatusError as e:
            logger.error(f"Cloudflare API error: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "cloudflare",
                "operation": "delete_record",
                "status": "error",
                "zone_id": zone_id,
                "record_id": record_id,
                "error": str(e),
            })
            
            raise ValueError(f"Cloudflare API error: {str(e)}")
        except Exception as e:
            logger.error(f"Error deleting Cloudflare record {record_id} for zone {zone_id}: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "cloudflare",
                "operation": "delete_record",
                "status": "error",
                "zone_id": zone_id,
                "record_id": record_id,
                "error": str(e),
            })
            
            raise
    
    async def verify_credential(self, credential: APICredential) -> bool:
        """
        Verify an API credential.
        
        Args:
            credential: API credential to verify
            
        Returns:
            Boolean indicating whether the credential is valid
        """
        try:
            # Try to get zones as a simple verification
            await self.get_zones(credential)
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "cloudflare",
                "operation": "verify_credential",
                "status": "success",
                "credential_id": credential.id,
                "user_id": credential.user_id,
            })
            
            return True
        except Exception as e:
            logger.error(f"Error verifying Cloudflare credential: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "cloudflare",
                "operation": "verify_credential",
                "status": "error",
                "credential_id": credential.id,
                "user_id": credential.user_id,
                "error": str(e),
            })
            
            return False
