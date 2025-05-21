"""
Base interface for DNS providers.

This module defines the base interface that all DNS provider implementations must follow.
"""
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from app.services.domains.credential_storage import APICredential
from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

class RecordType(str, Enum):
    """DNS record types."""
    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    MX = "MX"
    TXT = "TXT"
    NS = "NS"
    SRV = "SRV"
    CAA = "CAA"

class DNSRecord:
    """Model for DNS records."""
    
    def __init__(
        self,
        id: str,
        domain: str,
        name: str,
        type: RecordType,
        content: str,
        ttl: int = 3600,
        priority: Optional[int] = None,
        proxied: bool = False,
    ):
        """
        Initialize a DNS record.
        
        Args:
            id: Record ID
            domain: Domain name
            name: Record name (e.g., www)
            type: Record type
            content: Record content (e.g., IP address)
            ttl: Time to live in seconds
            priority: Priority (for MX and SRV records)
            proxied: Whether the record is proxied (Cloudflare-specific)
        """
        self.id = id
        self.domain = domain
        self.name = name
        self.type = type
        self.content = content
        self.ttl = ttl
        self.priority = priority
        self.proxied = proxied
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "domain": self.domain,
            "name": self.name,
            "type": self.type.value,
            "content": self.content,
            "ttl": self.ttl,
            "priority": self.priority,
            "proxied": self.proxied,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DNSRecord":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            domain=data["domain"],
            name=data["name"],
            type=RecordType(data["type"]),
            content=data["content"],
            ttl=data.get("ttl", 3600),
            priority=data.get("priority"),
            proxied=data.get("proxied", False),
        )

class DNSProvider(ABC):
    """Base interface for DNS providers."""
    
    @abstractmethod
    async def get_zones(self, credential: APICredential) -> List[Dict[str, Any]]:
        """
        Get all zones (domains) for the account.
        
        Args:
            credential: API credential
            
        Returns:
            List of zones
        """
        pass
    
    @abstractmethod
    async def get_zone(self, credential: APICredential, zone_id: str) -> Dict[str, Any]:
        """
        Get a specific zone.
        
        Args:
            credential: API credential
            zone_id: Zone ID
            
        Returns:
            Zone details
        """
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def verify_credential(self, credential: APICredential) -> bool:
        """
        Verify an API credential.
        
        Args:
            credential: API credential to verify
            
        Returns:
            Boolean indicating whether the credential is valid
        """
        pass
