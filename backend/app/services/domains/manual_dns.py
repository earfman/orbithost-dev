"""
Manual DNS configuration service.

This module provides functionality for generating manual DNS configuration instructions
for registrars that don't have API access or aren't directly supported by OrbitHost.
"""
import logging
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union

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

class ManualDNSRecord:
    """Model for manual DNS record configuration."""
    
    def __init__(
        self,
        id: str,
        domain: str,
        name: str,
        type: RecordType,
        content: str,
        ttl: int = 3600,
        priority: Optional[int] = None,
    ):
        """
        Initialize a manual DNS record.
        
        Args:
            id: Record ID
            domain: Domain name
            name: Record name (e.g., www)
            type: Record type
            content: Record content (e.g., IP address)
            ttl: Time to live in seconds
            priority: Priority (for MX and SRV records)
        """
        self.id = id
        self.domain = domain
        self.name = name
        self.type = type
        self.content = content
        self.ttl = ttl
        self.priority = priority
    
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
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ManualDNSRecord":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            domain=data["domain"],
            name=data["name"],
            type=RecordType(data["type"]),
            content=data["content"],
            ttl=data.get("ttl", 3600),
            priority=data.get("priority"),
        )

class ManualDNSConfiguration:
    """Model for manual DNS configuration."""
    
    def __init__(
        self,
        id: str,
        user_id: str,
        domain: str,
        app_id: str,
        records: List[ManualDNSRecord],
        nameservers: Optional[List[str]] = None,
        registrar: Optional[str] = None,
        notes: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ):
        """
        Initialize a manual DNS configuration.
        
        Args:
            id: Configuration ID
            user_id: ID of the user
            domain: Domain name
            app_id: ID of the application
            records: DNS records
            nameservers: Nameservers
            registrar: Domain registrar
            notes: Additional notes
            created_at: Creation timestamp
            updated_at: Last update timestamp
        """
        self.id = id
        self.user_id = user_id
        self.domain = domain
        self.app_id = app_id
        self.records = records
        self.nameservers = nameservers or []
        self.registrar = registrar
        self.notes = notes
        self.created_at = created_at
        self.updated_at = updated_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "domain": self.domain,
            "app_id": self.app_id,
            "records": [record.to_dict() for record in self.records],
            "nameservers": self.nameservers,
            "registrar": self.registrar,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ManualDNSConfiguration":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            domain=data["domain"],
            app_id=data["app_id"],
            records=[ManualDNSRecord.from_dict(record) for record in data["records"]],
            nameservers=data.get("nameservers", []),
            registrar=data.get("registrar"),
            notes=data.get("notes"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

class RegistrarTemplate:
    """Model for registrar-specific templates."""
    
    def __init__(
        self,
        registrar: str,
        instructions: str,
        screenshots: List[str],
        url: Optional[str] = None,
    ):
        """
        Initialize a registrar template.
        
        Args:
            registrar: Registrar name
            instructions: Step-by-step instructions
            screenshots: URLs to screenshots
            url: URL to registrar's DNS management page
        """
        self.registrar = registrar
        self.instructions = instructions
        self.screenshots = screenshots
        self.url = url
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "registrar": self.registrar,
            "instructions": self.instructions,
            "screenshots": self.screenshots,
            "url": self.url,
        }

class ManualDNSService:
    """Service for generating manual DNS configuration instructions."""
    
    def __init__(self):
        """Initialize the manual DNS service."""
        self.configurations = {}
        self.templates = self._initialize_templates()
        logger.info("Initialized manual DNS service")
    
    def _initialize_templates(self) -> Dict[str, RegistrarTemplate]:
        """
        Initialize registrar-specific templates.
        
        Returns:
            Dictionary of registrar templates
        """
        templates = {}
        
        # GoDaddy template
        templates["godaddy"] = RegistrarTemplate(
            registrar="GoDaddy",
            instructions="""
1. Log in to your GoDaddy account
2. Navigate to My Products > Domains
3. Click on the domain you want to configure
4. Click on DNS & Nameservers
5. Scroll down to the DNS Records section
6. Add or edit the records as needed
7. Click Save
            """,
            screenshots=[
                "https://orbithost.io/static/images/manual-dns/godaddy-1.png",
                "https://orbithost.io/static/images/manual-dns/godaddy-2.png",
            ],
            url="https://dcc.godaddy.com/manage",
        )
        
        # Namecheap template
        templates["namecheap"] = RegistrarTemplate(
            registrar="Namecheap",
            instructions="""
1. Log in to your Namecheap account
2. Navigate to Domain List
3. Click on Manage next to the domain you want to configure
4. Click on Advanced DNS
5. Add or edit the records as needed
6. Click Save All Changes
            """,
            screenshots=[
                "https://orbithost.io/static/images/manual-dns/namecheap-1.png",
                "https://orbithost.io/static/images/manual-dns/namecheap-2.png",
            ],
            url="https://ap.www.namecheap.com/domains/list",
        )
        
        # Google Domains template
        templates["google"] = RegistrarTemplate(
            registrar="Google Domains",
            instructions="""
1. Log in to your Google Domains account
2. Click on the domain you want to configure
3. Click on DNS
4. Scroll down to the Custom resource records section
5. Add or edit the records as needed
6. Click Add
            """,
            screenshots=[
                "https://orbithost.io/static/images/manual-dns/google-1.png",
                "https://orbithost.io/static/images/manual-dns/google-2.png",
            ],
            url="https://domains.google.com/registrar",
        )
        
        # Cloudflare template
        templates["cloudflare"] = RegistrarTemplate(
            registrar="Cloudflare",
            instructions="""
1. Log in to your Cloudflare account
2. Click on the domain you want to configure
3. Click on DNS
4. Click on Add Record
5. Enter the record details
6. Click Save
            """,
            screenshots=[
                "https://orbithost.io/static/images/manual-dns/cloudflare-1.png",
                "https://orbithost.io/static/images/manual-dns/cloudflare-2.png",
            ],
            url="https://dash.cloudflare.com",
        )
        
        # AWS Route 53 template
        templates["route53"] = RegistrarTemplate(
            registrar="AWS Route 53",
            instructions="""
1. Log in to your AWS Management Console
2. Navigate to Route 53
3. Click on Hosted Zones
4. Click on the domain you want to configure
5. Click on Create Record
6. Enter the record details
7. Click Create Records
            """,
            screenshots=[
                "https://orbithost.io/static/images/manual-dns/route53-1.png",
                "https://orbithost.io/static/images/manual-dns/route53-2.png",
            ],
            url="https://console.aws.amazon.com/route53",
        )
        
        # Generic template
        templates["generic"] = RegistrarTemplate(
            registrar="Generic",
            instructions="""
1. Log in to your domain registrar account
2. Navigate to the DNS management section
3. Add or edit the records as needed
4. Save your changes
            """,
            screenshots=[],
            url=None,
        )
        
        return templates
    
    async def create_configuration(
        self,
        user_id: str,
        domain: str,
        app_id: str,
        target_ip: str,
        registrar: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> ManualDNSConfiguration:
        """
        Create a manual DNS configuration.
        
        Args:
            user_id: ID of the user
            domain: Domain name
            app_id: ID of the application
            target_ip: Target IP address
            registrar: Domain registrar
            notes: Additional notes
            
        Returns:
            Manual DNS configuration
        """
        try:
            # Generate configuration ID
            config_id = str(uuid.uuid4())
            
            # Create A record for root domain
            root_record = ManualDNSRecord(
                id=str(uuid.uuid4()),
                domain=domain,
                name="@",
                type=RecordType.A,
                content=target_ip,
                ttl=3600,
            )
            
            # Create A record for www subdomain
            www_record = ManualDNSRecord(
                id=str(uuid.uuid4()),
                domain=domain,
                name="www",
                type=RecordType.A,
                content=target_ip,
                ttl=3600,
            )
            
            # Create TXT record for verification
            verification_token = str(uuid.uuid4())
            verification_record = ManualDNSRecord(
                id=str(uuid.uuid4()),
                domain=domain,
                name="_orbithost-verification",
                type=RecordType.TXT,
                content=f"orbithost-verification={verification_token}",
                ttl=3600,
            )
            
            # Create configuration
            configuration = ManualDNSConfiguration(
                id=config_id,
                user_id=user_id,
                domain=domain,
                app_id=app_id,
                records=[root_record, www_record, verification_record],
                registrar=registrar,
                notes=notes,
            )
            
            # Store configuration
            self.configurations[config_id] = configuration
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "manual_dns",
                "operation": "create_configuration",
                "config_id": config_id,
                "user_id": user_id,
                "domain": domain,
                "app_id": app_id,
                "registrar": registrar,
            })
            
            return configuration
        except Exception as e:
            logger.error(f"Error creating manual DNS configuration: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "manual_dns",
                "operation": "create_configuration",
                "status": "error",
                "user_id": user_id,
                "domain": domain,
                "app_id": app_id,
                "error": str(e),
            })
            
            raise
    
    async def get_configuration(
        self,
        config_id: str,
    ) -> Optional[ManualDNSConfiguration]:
        """
        Get a manual DNS configuration by ID.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            Manual DNS configuration or None if not found
        """
        return self.configurations.get(config_id)
    
    async def get_configurations_for_user(
        self,
        user_id: str,
    ) -> List[ManualDNSConfiguration]:
        """
        Get all manual DNS configurations for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of manual DNS configurations
        """
        return [
            config for config in self.configurations.values()
            if config.user_id == user_id
        ]
    
    async def get_configurations_for_domain(
        self,
        domain: str,
    ) -> List[ManualDNSConfiguration]:
        """
        Get all manual DNS configurations for a domain.
        
        Args:
            domain: Domain name
            
        Returns:
            List of manual DNS configurations
        """
        return [
            config for config in self.configurations.values()
            if config.domain == domain
        ]
    
    async def get_configurations_for_app(
        self,
        app_id: str,
    ) -> List[ManualDNSConfiguration]:
        """
        Get all manual DNS configurations for an application.
        
        Args:
            app_id: ID of the application
            
        Returns:
            List of manual DNS configurations
        """
        return [
            config for config in self.configurations.values()
            if config.app_id == app_id
        ]
    
    async def update_configuration(
        self,
        config_id: str,
        updates: Dict[str, Any],
    ) -> Optional[ManualDNSConfiguration]:
        """
        Update a manual DNS configuration.
        
        Args:
            config_id: Configuration ID
            updates: Dictionary of updates
            
        Returns:
            Updated manual DNS configuration or None if not found
        """
        try:
            # Get configuration
            configuration = self.configurations.get(config_id)
            
            if not configuration:
                return None
            
            # Update configuration
            for key, value in updates.items():
                if key == "records":
                    # Update records
                    configuration.records = [
                        ManualDNSRecord.from_dict(record) if isinstance(record, dict) else record
                        for record in value
                    ]
                elif key == "nameservers":
                    # Update nameservers
                    configuration.nameservers = value
                elif key == "registrar":
                    # Update registrar
                    configuration.registrar = value
                elif key == "notes":
                    # Update notes
                    configuration.notes = value
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "manual_dns",
                "operation": "update_configuration",
                "config_id": config_id,
                "user_id": configuration.user_id,
                "domain": configuration.domain,
                "app_id": configuration.app_id,
            })
            
            return configuration
        except Exception as e:
            logger.error(f"Error updating manual DNS configuration {config_id}: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "manual_dns",
                "operation": "update_configuration",
                "status": "error",
                "config_id": config_id,
                "error": str(e),
            })
            
            raise
    
    async def delete_configuration(
        self,
        config_id: str,
    ) -> bool:
        """
        Delete a manual DNS configuration.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            Boolean indicating success or failure
        """
        if config_id in self.configurations:
            # Get configuration for logging
            configuration = self.configurations[config_id]
            
            # Delete configuration
            del self.configurations[config_id]
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "manual_dns",
                "operation": "delete_configuration",
                "config_id": config_id,
                "user_id": configuration.user_id,
                "domain": configuration.domain,
                "app_id": configuration.app_id,
            })
            
            return True
        
        return False
    
    async def get_template(
        self,
        registrar: str,
    ) -> RegistrarTemplate:
        """
        Get a registrar-specific template.
        
        Args:
            registrar: Registrar name
            
        Returns:
            Registrar template
        """
        # Normalize registrar name
        registrar_lower = registrar.lower()
        
        # Find matching template
        for key, template in self.templates.items():
            if key in registrar_lower or registrar_lower in key:
                return template
        
        # Return generic template if no match
        return self.templates["generic"]
    
    async def generate_instructions(
        self,
        config_id: str,
    ) -> Dict[str, Any]:
        """
        Generate manual DNS configuration instructions.
        
        Args:
            config_id: Configuration ID
            
        Returns:
            Dictionary with instructions and template
        """
        try:
            # Get configuration
            configuration = self.configurations.get(config_id)
            
            if not configuration:
                raise ValueError(f"Configuration {config_id} not found")
            
            # Get template
            template = await self.get_template(
                registrar=configuration.registrar or "generic"
            )
            
            # Generate record instructions
            record_instructions = []
            
            for record in configuration.records:
                instruction = {
                    "type": record.type.value,
                    "name": record.name,
                    "content": record.content,
                    "ttl": record.ttl,
                }
                
                if record.priority is not None:
                    instruction["priority"] = record.priority
                
                record_instructions.append(instruction)
            
            # Generate result
            result = {
                "config_id": config_id,
                "domain": configuration.domain,
                "registrar": configuration.registrar,
                "template": template.to_dict(),
                "records": record_instructions,
                "nameservers": configuration.nameservers,
                "notes": configuration.notes,
            }
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "manual_dns",
                "operation": "generate_instructions",
                "config_id": config_id,
                "user_id": configuration.user_id,
                "domain": configuration.domain,
                "app_id": configuration.app_id,
                "registrar": configuration.registrar,
            })
            
            return result
        except Exception as e:
            logger.error(f"Error generating instructions for configuration {config_id}: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "manual_dns",
                "operation": "generate_instructions",
                "status": "error",
                "config_id": config_id,
                "error": str(e),
            })
            
            raise

# Singleton instance
_manual_dns_service = None

async def get_manual_dns_service() -> ManualDNSService:
    """
    Get the manual DNS service instance.
    
    Returns:
        Manual DNS service instance
    """
    global _manual_dns_service
    
    if _manual_dns_service is None:
        _manual_dns_service = ManualDNSService()
    
    return _manual_dns_service
