"""
Domain transfer service.

This module provides functionality for transferring domains from other platforms
to OrbitHost, including verification, DNS record transfer, and application settings migration.
"""
import logging
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from app.services.domains.credential_storage import (
    get_credential_storage,
    APICredential,
    ProviderType,
)
from app.services.domains.dns_configurator import (
    get_dns_configurator,
    DNSConfigurationError,
)
from app.services.domains.dns_providers import get_dns_provider
from app.services.domains.dns_providers.base import DNSRecord, RecordType
from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

class TransferSource(str, Enum):
    """Source platforms for domain transfers."""
    LOVABLE = "lovable"
    REPLIT = "replit"
    CURSOR = "cursor"
    OTHER = "other"

class TransferStatus(str, Enum):
    """Status of domain transfer."""
    PENDING = "pending"
    VERIFYING = "verifying"
    TRANSFERRING_DNS = "transferring_dns"
    UPDATING_NAMESERVERS = "updating_nameservers"
    MIGRATING_SETTINGS = "migrating_settings"
    COMPLETED = "completed"
    FAILED = "failed"

class TransferError(Exception):
    """Exception raised for domain transfer errors."""
    pass

class DomainTransfer:
    """Model for domain transfer."""
    
    def __init__(
        self,
        id: str,
        user_id: str,
        domain: str,
        source: TransferSource,
        status: TransferStatus = TransferStatus.PENDING,
        verification_token: Optional[str] = None,
        verification_method: Optional[str] = None,
        source_credential_id: Optional[str] = None,
        target_credential_id: Optional[str] = None,
        dns_records: Optional[List[Dict[str, Any]]] = None,
        app_settings: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ):
        """
        Initialize a domain transfer.
        
        Args:
            id: Transfer ID
            user_id: ID of the user
            domain: Domain name
            source: Source platform
            status: Transfer status
            verification_token: Verification token
            verification_method: Verification method
            source_credential_id: ID of the source credential
            target_credential_id: ID of the target credential
            dns_records: DNS records to transfer
            app_settings: Application settings to migrate
            error: Error message if transfer failed
            created_at: Creation timestamp
            updated_at: Last update timestamp
        """
        self.id = id
        self.user_id = user_id
        self.domain = domain
        self.source = source
        self.status = status
        self.verification_token = verification_token
        self.verification_method = verification_method
        self.source_credential_id = source_credential_id
        self.target_credential_id = target_credential_id
        self.dns_records = dns_records or []
        self.app_settings = app_settings or {}
        self.error = error
        self.created_at = created_at
        self.updated_at = updated_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "domain": self.domain,
            "source": self.source.value,
            "status": self.status.value,
            "verification_token": self.verification_token,
            "verification_method": self.verification_method,
            "source_credential_id": self.source_credential_id,
            "target_credential_id": self.target_credential_id,
            "dns_records": self.dns_records,
            "app_settings": self.app_settings,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DomainTransfer":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            domain=data["domain"],
            source=TransferSource(data["source"]),
            status=TransferStatus(data["status"]),
            verification_token=data.get("verification_token"),
            verification_method=data.get("verification_method"),
            source_credential_id=data.get("source_credential_id"),
            target_credential_id=data.get("target_credential_id"),
            dns_records=data.get("dns_records", []),
            app_settings=data.get("app_settings", {}),
            error=data.get("error"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

class DomainTransferService:
    """Service for transferring domains from other platforms."""
    
    def __init__(self):
        """Initialize the domain transfer service."""
        self.transfers = {}
        logger.info("Initialized domain transfer service")
    
    async def initiate_transfer(
        self,
        user_id: str,
        domain: str,
        source: TransferSource,
        source_credential_id: Optional[str] = None,
        target_credential_id: Optional[str] = None,
    ) -> DomainTransfer:
        """
        Initiate a domain transfer.
        
        Args:
            user_id: ID of the user
            domain: Domain name
            source: Source platform
            source_credential_id: ID of the source credential
            target_credential_id: ID of the target credential
            
        Returns:
            Domain transfer
        """
        try:
            # Generate transfer ID
            transfer_id = str(uuid.uuid4())
            
            # Generate verification token
            verification_token = str(uuid.uuid4())
            
            # Create transfer
            transfer = DomainTransfer(
                id=transfer_id,
                user_id=user_id,
                domain=domain,
                source=source,
                status=TransferStatus.PENDING,
                verification_token=verification_token,
                verification_method="dns",
                source_credential_id=source_credential_id,
                target_credential_id=target_credential_id,
            )
            
            # Store transfer
            self.transfers[transfer_id] = transfer
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "domain_transfer",
                "operation": "initiate",
                "transfer_id": transfer_id,
                "user_id": user_id,
                "domain": domain,
                "source": source.value,
            })
            
            return transfer
        except Exception as e:
            logger.error(f"Error initiating domain transfer: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "domain_transfer",
                "operation": "initiate",
                "status": "error",
                "user_id": user_id,
                "domain": domain,
                "source": source.value if isinstance(source, TransferSource) else source,
                "error": str(e),
            })
            
            raise TransferError(f"Failed to initiate domain transfer: {str(e)}")
    
    async def verify_ownership(
        self,
        transfer_id: str,
    ) -> DomainTransfer:
        """
        Verify domain ownership.
        
        Args:
            transfer_id: Transfer ID
            
        Returns:
            Updated domain transfer
        """
        try:
            # Get transfer
            transfer = self.transfers.get(transfer_id)
            
            if not transfer:
                raise TransferError(f"Transfer {transfer_id} not found")
            
            # Update status
            transfer.status = TransferStatus.VERIFYING
            
            # Get DNS configurator
            dns_configurator = await get_dns_configurator()
            
            # Verify domain ownership
            verification_result = await dns_configurator.verify_domain_ownership(
                user_id=transfer.user_id,
                domain=transfer.domain,
                verification_token=transfer.verification_token,
                credential_id=transfer.target_credential_id,
            )
            
            # Update transfer
            transfer.verification_method = "dns"
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "domain_transfer",
                "operation": "verify_ownership",
                "transfer_id": transfer_id,
                "user_id": transfer.user_id,
                "domain": transfer.domain,
                "source": transfer.source.value,
                "verification_method": transfer.verification_method,
            })
            
            return transfer
        except Exception as e:
            logger.error(f"Error verifying domain ownership: {str(e)}")
            
            # Update transfer status
            if transfer_id in self.transfers:
                self.transfers[transfer_id].status = TransferStatus.FAILED
                self.transfers[transfer_id].error = str(e)
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "domain_transfer",
                "operation": "verify_ownership",
                "status": "error",
                "transfer_id": transfer_id,
                "error": str(e),
            })
            
            raise TransferError(f"Failed to verify domain ownership: {str(e)}")
    
    async def transfer_dns_records(
        self,
        transfer_id: str,
    ) -> DomainTransfer:
        """
        Transfer DNS records from source to target.
        
        Args:
            transfer_id: Transfer ID
            
        Returns:
            Updated domain transfer
        """
        try:
            # Get transfer
            transfer = self.transfers.get(transfer_id)
            
            if not transfer:
                raise TransferError(f"Transfer {transfer_id} not found")
            
            # Update status
            transfer.status = TransferStatus.TRANSFERRING_DNS
            
            # Get credential storage
            storage = await get_credential_storage()
            
            # Get source credential
            source_credential = None
            if transfer.source_credential_id:
                source_credential = await storage.get_credential(
                    credential_id=transfer.source_credential_id,
                    decrypt=True,
                )
            
            # Get target credential
            target_credential = None
            if transfer.target_credential_id:
                target_credential = await storage.get_credential(
                    credential_id=transfer.target_credential_id,
                    decrypt=True,
                )
                
                if not target_credential:
                    raise TransferError(f"Target credential {transfer.target_credential_id} not found")
            else:
                # Find a suitable target credential
                credentials = await storage.get_credentials_for_user(
                    user_id=transfer.user_id,
                    provider_type=ProviderType.DNS_PROVIDER,
                )
                
                if not credentials:
                    raise TransferError("No DNS provider credentials found for user")
                
                # Use the first credential
                target_credential = credentials[0]
                transfer.target_credential_id = target_credential.id
            
            # Get DNS records from source
            dns_records = []
            
            if source_credential:
                # Get DNS provider
                source_provider = get_dns_provider(source_credential.provider_type)
                
                # Find the zone for the domain
                zones = await source_provider.get_zones(source_credential)
                zone_id = None
                
                for zone in zones:
                    if zone["name"] == transfer.domain:
                        zone_id = zone["id"]
                        break
                
                if zone_id:
                    # Get DNS records
                    records = await source_provider.get_records(source_credential, zone_id)
                    
                    # Store DNS records
                    dns_records = [record.to_dict() for record in records]
            else:
                # For platforms without API access, we'll need to implement
                # platform-specific logic to get DNS records
                if transfer.source == TransferSource.LOVABLE:
                    # Implement Lovable-specific logic
                    pass
                elif transfer.source == TransferSource.REPLIT:
                    # Implement Replit-specific logic
                    pass
                elif transfer.source == TransferSource.CURSOR:
                    # Implement Cursor-specific logic
                    pass
            
            # Store DNS records
            transfer.dns_records = dns_records
            
            # Get target DNS provider
            target_provider = get_dns_provider(target_credential.provider_type)
            
            # Find the zone for the domain
            zones = await target_provider.get_zones(target_credential)
            zone_id = None
            
            for zone in zones:
                if zone["name"] == transfer.domain:
                    zone_id = zone["id"]
                    break
            
            if not zone_id:
                raise TransferError(f"Zone for domain {transfer.domain} not found")
            
            # Transfer DNS records
            for record_data in dns_records:
                # Skip SOA and NS records
                if record_data["type"] in ["SOA", "NS"]:
                    continue
                
                # Create record
                record = DNSRecord.from_dict(record_data)
                
                # Create record in target
                await target_provider.create_record(target_credential, zone_id, record)
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "domain_transfer",
                "operation": "transfer_dns_records",
                "transfer_id": transfer_id,
                "user_id": transfer.user_id,
                "domain": transfer.domain,
                "source": transfer.source.value,
                "record_count": len(dns_records),
            })
            
            return transfer
        except Exception as e:
            logger.error(f"Error transferring DNS records: {str(e)}")
            
            # Update transfer status
            if transfer_id in self.transfers:
                self.transfers[transfer_id].status = TransferStatus.FAILED
                self.transfers[transfer_id].error = str(e)
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "domain_transfer",
                "operation": "transfer_dns_records",
                "status": "error",
                "transfer_id": transfer_id,
                "error": str(e),
            })
            
            raise TransferError(f"Failed to transfer DNS records: {str(e)}")
    
    async def update_nameservers(
        self,
        transfer_id: str,
        nameservers: List[str],
    ) -> DomainTransfer:
        """
        Update nameservers for the domain.
        
        Args:
            transfer_id: Transfer ID
            nameservers: Nameservers to set
            
        Returns:
            Updated domain transfer
        """
        try:
            # Get transfer
            transfer = self.transfers.get(transfer_id)
            
            if not transfer:
                raise TransferError(f"Transfer {transfer_id} not found")
            
            # Update status
            transfer.status = TransferStatus.UPDATING_NAMESERVERS
            
            # Get credential storage
            storage = await get_credential_storage()
            
            # Get target credential
            target_credential = None
            if transfer.target_credential_id:
                target_credential = await storage.get_credential(
                    credential_id=transfer.target_credential_id,
                    decrypt=True,
                )
                
                if not target_credential:
                    raise TransferError(f"Target credential {transfer.target_credential_id} not found")
            else:
                # Find a suitable target credential
                credentials = await storage.get_credentials_for_user(
                    user_id=transfer.user_id,
                    provider_type=ProviderType.DNS_PROVIDER,
                )
                
                if not credentials:
                    raise TransferError("No DNS provider credentials found for user")
                
                # Use the first credential
                target_credential = credentials[0]
                transfer.target_credential_id = target_credential.id
            
            # Get DNS provider
            target_provider = get_dns_provider(target_credential.provider_type)
            
            # Find the zone for the domain
            zones = await target_provider.get_zones(target_credential)
            zone_id = None
            
            for zone in zones:
                if zone["name"] == transfer.domain:
                    zone_id = zone["id"]
                    break
            
            if not zone_id:
                raise TransferError(f"Zone for domain {transfer.domain} not found")
            
            # Update nameservers
            # Note: This is a placeholder as the actual implementation would depend
            # on the DNS provider's API for updating nameservers
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "domain_transfer",
                "operation": "update_nameservers",
                "transfer_id": transfer_id,
                "user_id": transfer.user_id,
                "domain": transfer.domain,
                "source": transfer.source.value,
                "nameservers": nameservers,
            })
            
            return transfer
        except Exception as e:
            logger.error(f"Error updating nameservers: {str(e)}")
            
            # Update transfer status
            if transfer_id in self.transfers:
                self.transfers[transfer_id].status = TransferStatus.FAILED
                self.transfers[transfer_id].error = str(e)
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "domain_transfer",
                "operation": "update_nameservers",
                "status": "error",
                "transfer_id": transfer_id,
                "error": str(e),
            })
            
            raise TransferError(f"Failed to update nameservers: {str(e)}")
    
    async def migrate_app_settings(
        self,
        transfer_id: str,
        app_id: str,
    ) -> DomainTransfer:
        """
        Migrate application settings from source to target.
        
        Args:
            transfer_id: Transfer ID
            app_id: ID of the target application
            
        Returns:
            Updated domain transfer
        """
        try:
            # Get transfer
            transfer = self.transfers.get(transfer_id)
            
            if not transfer:
                raise TransferError(f"Transfer {transfer_id} not found")
            
            # Update status
            transfer.status = TransferStatus.MIGRATING_SETTINGS
            
            # For platforms without API access, we'll need to implement
            # platform-specific logic to get application settings
            app_settings = {}
            
            if transfer.source == TransferSource.LOVABLE:
                # Implement Lovable-specific logic
                pass
            elif transfer.source == TransferSource.REPLIT:
                # Implement Replit-specific logic
                pass
            elif transfer.source == TransferSource.CURSOR:
                # Implement Cursor-specific logic
                pass
            
            # Store application settings
            transfer.app_settings = app_settings
            
            # Apply application settings to target application
            # Note: This is a placeholder as the actual implementation would depend
            # on the application settings format and how they are applied
            
            # Update status
            transfer.status = TransferStatus.COMPLETED
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "domain_transfer",
                "operation": "migrate_app_settings",
                "transfer_id": transfer_id,
                "user_id": transfer.user_id,
                "domain": transfer.domain,
                "source": transfer.source.value,
                "app_id": app_id,
            })
            
            return transfer
        except Exception as e:
            logger.error(f"Error migrating application settings: {str(e)}")
            
            # Update transfer status
            if transfer_id in self.transfers:
                self.transfers[transfer_id].status = TransferStatus.FAILED
                self.transfers[transfer_id].error = str(e)
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "domain_transfer",
                "operation": "migrate_app_settings",
                "status": "error",
                "transfer_id": transfer_id,
                "error": str(e),
            })
            
            raise TransferError(f"Failed to migrate application settings: {str(e)}")
    
    async def get_transfer(
        self,
        transfer_id: str,
    ) -> Optional[DomainTransfer]:
        """
        Get a domain transfer by ID.
        
        Args:
            transfer_id: Transfer ID
            
        Returns:
            Domain transfer or None if not found
        """
        return self.transfers.get(transfer_id)
    
    async def get_transfers_for_user(
        self,
        user_id: str,
    ) -> List[DomainTransfer]:
        """
        Get all domain transfers for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of domain transfers
        """
        return [
            transfer for transfer in self.transfers.values()
            if transfer.user_id == user_id
        ]
    
    async def get_transfers_for_domain(
        self,
        domain: str,
    ) -> List[DomainTransfer]:
        """
        Get all domain transfers for a domain.
        
        Args:
            domain: Domain name
            
        Returns:
            List of domain transfers
        """
        return [
            transfer for transfer in self.transfers.values()
            if transfer.domain == domain
        ]
    
    async def delete_transfer(
        self,
        transfer_id: str,
    ) -> bool:
        """
        Delete a domain transfer.
        
        Args:
            transfer_id: Transfer ID
            
        Returns:
            Boolean indicating success or failure
        """
        if transfer_id in self.transfers:
            del self.transfers[transfer_id]
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "domain_transfer",
                "operation": "delete",
                "transfer_id": transfer_id,
            })
            
            return True
        
        return False

# Singleton instance
_domain_transfer_service = None

async def get_domain_transfer_service() -> DomainTransferService:
    """
    Get the domain transfer service instance.
    
    Returns:
        Domain transfer service instance
    """
    global _domain_transfer_service
    
    if _domain_transfer_service is None:
        _domain_transfer_service = DomainTransferService()
    
    return _domain_transfer_service
