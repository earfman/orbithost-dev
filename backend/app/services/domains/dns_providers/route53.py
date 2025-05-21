"""
AWS Route 53 DNS provider implementation.

This module implements the AWS Route 53 DNS provider interface for managing DNS records.
"""
import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Union

import boto3
import botocore.exceptions

from app.services.domains.credential_storage import APICredential
from app.services.domains.dns_providers.base import DNSProvider, DNSRecord, RecordType
from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

class Route53DNSProvider(DNSProvider):
    """AWS Route 53 DNS provider implementation."""
    
    def __init__(self):
        """Initialize the AWS Route 53 DNS provider."""
        logger.info("Initialized AWS Route 53 DNS provider")
    
    def _get_client(self, credential: APICredential):
        """
        Get AWS Route 53 client.
        
        Args:
            credential: API credential
            
        Returns:
            AWS Route 53 client
        """
        # Decrypt credentials if encrypted
        if credential.encrypted:
            # In a real implementation, this would decrypt the credentials
            # For now, we'll assume they're not encrypted in this method
            pass
        
        # Check credential type
        if "access_key_id" in credential.credentials and "secret_access_key" in credential.credentials:
            # Create Route 53 client
            return boto3.client(
                "route53",
                aws_access_key_id=credential.credentials["access_key_id"],
                aws_secret_access_key=credential.credentials["secret_access_key"],
                region_name=credential.credentials.get("region", "us-east-1"),
            )
        else:
            raise ValueError("Invalid AWS Route 53 credentials")
    
    async def get_zones(self, credential: APICredential) -> List[Dict[str, Any]]:
        """
        Get all hosted zones (domains) for the account.
        
        Args:
            credential: API credential
            
        Returns:
            List of zones
        """
        try:
            # Get Route 53 client
            client = self._get_client(credential)
            
            # Get hosted zones
            response = client.list_hosted_zones()
            
            # Process zones
            zones = []
            for zone in response["HostedZones"]:
                # Remove trailing dot from domain name
                domain = zone["Name"]
                if domain.endswith("."):
                    domain = domain[:-1]
                
                zones.append({
                    "id": zone["Id"].replace("/hostedzone/", ""),
                    "name": domain,
                    "status": "active",
                    "name_servers": self._get_name_servers(client, zone["Id"]),
                })
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
                "operation": "get_zones",
                "status": "success",
                "zone_count": len(zones),
            })
            
            return zones
        except botocore.exceptions.ClientError as e:
            logger.error(f"AWS Route 53 API error: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
                "operation": "get_zones",
                "status": "error",
                "error": str(e),
            })
            
            raise ValueError(f"AWS Route 53 API error: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting AWS Route 53 zones: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
                "operation": "get_zones",
                "status": "error",
                "error": str(e),
            })
            
            raise
    
    def _get_name_servers(self, client, zone_id: str) -> List[str]:
        """
        Get name servers for a hosted zone.
        
        Args:
            client: Route 53 client
            zone_id: Zone ID
            
        Returns:
            List of name servers
        """
        try:
            response = client.get_hosted_zone(Id=zone_id)
            return response["DelegationSet"]["NameServers"]
        except Exception as e:
            logger.error(f"Error getting name servers for zone {zone_id}: {str(e)}")
            return []
    
    async def get_zone(self, credential: APICredential, zone_id: str) -> Dict[str, Any]:
        """
        Get a specific zone.
        
        Args:
            credential: API credential
            zone_id: Zone ID
            
        Returns:
            Zone details
        """
        try:
            # Get Route 53 client
            client = self._get_client(credential)
            
            # Get hosted zone
            response = client.get_hosted_zone(Id=zone_id)
            
            # Process zone
            zone = response["HostedZone"]
            
            # Remove trailing dot from domain name
            domain = zone["Name"]
            if domain.endswith("."):
                domain = domain[:-1]
            
            result = {
                "id": zone["Id"].replace("/hostedzone/", ""),
                "name": domain,
                "status": "active",
                "name_servers": response["DelegationSet"]["NameServers"] if "DelegationSet" in response else [],
            }
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
                "operation": "get_zone",
                "status": "success",
                "zone_id": zone_id,
            })
            
            return result
        except botocore.exceptions.ClientError as e:
            logger.error(f"AWS Route 53 API error: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
                "operation": "get_zone",
                "status": "error",
                "zone_id": zone_id,
                "error": str(e),
            })
            
            raise ValueError(f"AWS Route 53 API error: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting AWS Route 53 zone {zone_id}: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
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
        try:
            # Get Route 53 client
            client = self._get_client(credential)
            
            # Get zone details to get the domain name
            zone = await self.get_zone(credential, zone_id)
            domain = zone["name"]
            
            # Get DNS records
            response = client.list_resource_record_sets(HostedZoneId=zone_id)
            
            # Process records
            records = []
            for record_data in response["ResourceRecordSets"]:
                # Skip records that don't match the requested type
                if record_type and record_data["Type"] != record_type.value:
                    continue
                
                # Skip SOA and NS records
                if record_data["Type"] in ["SOA", "NS"]:
                    continue
                
                # Process record content
                content = ""
                if "ResourceRecords" in record_data:
                    if len(record_data["ResourceRecords"]) > 0:
                        content = record_data["ResourceRecords"][0]["Value"]
                elif "AliasTarget" in record_data:
                    content = record_data["AliasTarget"]["DNSName"]
                
                # Remove domain suffix from name
                name = record_data["Name"]
                if name.endswith("."):
                    name = name[:-1]
                
                # Remove domain from name
                if name.endswith(domain):
                    name = name[:-len(domain)-1]  # -1 for the dot
                
                # Use @ for root domain
                if not name:
                    name = "@"
                
                # Create DNSRecord object
                record = DNSRecord(
                    id=str(uuid.uuid4()),  # Route 53 doesn't have record IDs, so we generate one
                    domain=domain,
                    name=name,
                    type=RecordType(record_data["Type"]),
                    content=content,
                    ttl=record_data.get("TTL", 3600),
                    priority=None,  # Route 53 doesn't have priority
                    proxied=False,  # Route 53 doesn't have proxying
                )
                records.append(record)
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
                "operation": "get_records",
                "status": "success",
                "zone_id": zone_id,
                "record_count": len(records),
                "record_type": record_type.value if record_type else None,
            })
            
            return records
        except botocore.exceptions.ClientError as e:
            logger.error(f"AWS Route 53 API error: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
                "operation": "get_records",
                "status": "error",
                "zone_id": zone_id,
                "record_type": record_type.value if record_type else None,
                "error": str(e),
            })
            
            raise ValueError(f"AWS Route 53 API error: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting AWS Route 53 records for zone {zone_id}: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
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
        # Route 53 doesn't have record IDs, so we need to get all records and filter
        try:
            # Get all records
            records = await self.get_records(credential, zone_id)
            
            # Find the record with the matching ID
            for record in records:
                if record.id == record_id:
                    # Log to MCP
                    await get_mcp_client().send({
                        "type": "dns_provider",
                        "provider": "route53",
                        "operation": "get_record",
                        "status": "success",
                        "zone_id": zone_id,
                        "record_id": record_id,
                    })
                    
                    return record
            
            # Record not found
            raise ValueError(f"Record {record_id} not found in zone {zone_id}")
        except ValueError:
            # Re-raise ValueError
            raise
        except Exception as e:
            logger.error(f"Error getting AWS Route 53 record {record_id} for zone {zone_id}: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
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
        try:
            # Get Route 53 client
            client = self._get_client(credential)
            
            # Get zone details to get the domain name
            zone = await self.get_zone(credential, zone_id)
            domain = zone["name"]
            
            # Prepare record name
            record_name = record.name
            if record_name == "@":
                record_name = ""
            
            # Append domain to record name
            if record_name:
                record_name = f"{record_name}.{domain}"
            else:
                record_name = domain
            
            # Append trailing dot
            if not record_name.endswith("."):
                record_name = f"{record_name}."
            
            # Prepare change batch
            change_batch = {
                "Changes": [
                    {
                        "Action": "CREATE",
                        "ResourceRecordSet": {
                            "Name": record_name,
                            "Type": record.type.value,
                            "TTL": record.ttl,
                            "ResourceRecords": [
                                {
                                    "Value": record.content
                                }
                            ]
                        }
                    }
                ]
            }
            
            # Create record
            response = client.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch=change_batch
            )
            
            # Generate record ID
            record_id = str(uuid.uuid4())
            
            # Create DNSRecord object
            created_record = DNSRecord(
                id=record_id,
                domain=domain,
                name=record.name,
                type=record.type,
                content=record.content,
                ttl=record.ttl,
                priority=record.priority,
                proxied=False,  # Route 53 doesn't have proxying
            )
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
                "operation": "create_record",
                "status": "success",
                "zone_id": zone_id,
                "record_type": record.type.value,
                "record_name": record.name,
            })
            
            return created_record
        except botocore.exceptions.ClientError as e:
            logger.error(f"AWS Route 53 API error: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
                "operation": "create_record",
                "status": "error",
                "zone_id": zone_id,
                "record_type": record.type.value,
                "record_name": record.name,
                "error": str(e),
            })
            
            raise ValueError(f"AWS Route 53 API error: {str(e)}")
        except Exception as e:
            logger.error(f"Error creating AWS Route 53 record for zone {zone_id}: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
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
        try:
            # Get Route 53 client
            client = self._get_client(credential)
            
            # Get existing record
            existing_record = await self.get_record(credential, zone_id, record_id)
            
            # Get zone details to get the domain name
            zone = await self.get_zone(credential, zone_id)
            domain = zone["name"]
            
            # Prepare old record name
            old_record_name = existing_record.name
            if old_record_name == "@":
                old_record_name = ""
            
            # Append domain to old record name
            if old_record_name:
                old_record_name = f"{old_record_name}.{domain}"
            else:
                old_record_name = domain
            
            # Append trailing dot to old record name
            if not old_record_name.endswith("."):
                old_record_name = f"{old_record_name}."
            
            # Prepare new record name
            new_record_name = record.name
            if new_record_name == "@":
                new_record_name = ""
            
            # Append domain to new record name
            if new_record_name:
                new_record_name = f"{new_record_name}.{domain}"
            else:
                new_record_name = domain
            
            # Append trailing dot to new record name
            if not new_record_name.endswith("."):
                new_record_name = f"{new_record_name}."
            
            # Prepare change batch
            change_batch = {
                "Changes": [
                    {
                        "Action": "DELETE",
                        "ResourceRecordSet": {
                            "Name": old_record_name,
                            "Type": existing_record.type.value,
                            "TTL": existing_record.ttl,
                            "ResourceRecords": [
                                {
                                    "Value": existing_record.content
                                }
                            ]
                        }
                    },
                    {
                        "Action": "CREATE",
                        "ResourceRecordSet": {
                            "Name": new_record_name,
                            "Type": record.type.value,
                            "TTL": record.ttl,
                            "ResourceRecords": [
                                {
                                    "Value": record.content
                                }
                            ]
                        }
                    }
                ]
            }
            
            # Update record
            response = client.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch=change_batch
            )
            
            # Create DNSRecord object
            updated_record = DNSRecord(
                id=record_id,
                domain=domain,
                name=record.name,
                type=record.type,
                content=record.content,
                ttl=record.ttl,
                priority=record.priority,
                proxied=False,  # Route 53 doesn't have proxying
            )
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
                "operation": "update_record",
                "status": "success",
                "zone_id": zone_id,
                "record_id": record_id,
                "record_type": record.type.value,
                "record_name": record.name,
            })
            
            return updated_record
        except botocore.exceptions.ClientError as e:
            logger.error(f"AWS Route 53 API error: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
                "operation": "update_record",
                "status": "error",
                "zone_id": zone_id,
                "record_id": record_id,
                "record_type": record.type.value,
                "record_name": record.name,
                "error": str(e),
            })
            
            raise ValueError(f"AWS Route 53 API error: {str(e)}")
        except Exception as e:
            logger.error(f"Error updating AWS Route 53 record {record_id} for zone {zone_id}: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
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
        try:
            # Get Route 53 client
            client = self._get_client(credential)
            
            # Get existing record
            existing_record = await self.get_record(credential, zone_id, record_id)
            
            # Get zone details to get the domain name
            zone = await self.get_zone(credential, zone_id)
            domain = zone["name"]
            
            # Prepare record name
            record_name = existing_record.name
            if record_name == "@":
                record_name = ""
            
            # Append domain to record name
            if record_name:
                record_name = f"{record_name}.{domain}"
            else:
                record_name = domain
            
            # Append trailing dot
            if not record_name.endswith("."):
                record_name = f"{record_name}."
            
            # Prepare change batch
            change_batch = {
                "Changes": [
                    {
                        "Action": "DELETE",
                        "ResourceRecordSet": {
                            "Name": record_name,
                            "Type": existing_record.type.value,
                            "TTL": existing_record.ttl,
                            "ResourceRecords": [
                                {
                                    "Value": existing_record.content
                                }
                            ]
                        }
                    }
                ]
            }
            
            # Delete record
            response = client.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch=change_batch
            )
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
                "operation": "delete_record",
                "status": "success",
                "zone_id": zone_id,
                "record_id": record_id,
            })
            
            return True
        except botocore.exceptions.ClientError as e:
            logger.error(f"AWS Route 53 API error: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
                "operation": "delete_record",
                "status": "error",
                "zone_id": zone_id,
                "record_id": record_id,
                "error": str(e),
            })
            
            raise ValueError(f"AWS Route 53 API error: {str(e)}")
        except Exception as e:
            logger.error(f"Error deleting AWS Route 53 record {record_id} for zone {zone_id}: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
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
                "provider": "route53",
                "operation": "verify_credential",
                "status": "success",
                "credential_id": credential.id,
                "user_id": credential.user_id,
            })
            
            return True
        except Exception as e:
            logger.error(f"Error verifying AWS Route 53 credential: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_provider",
                "provider": "route53",
                "operation": "verify_credential",
                "status": "error",
                "credential_id": credential.id,
                "user_id": credential.user_id,
                "error": str(e),
            })
            
            return False
