"""
Registrar factory for OrbitHost.
Creates registrar instances based on configuration.
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum

from app.core.config import settings
from app.services.domain_service.registrars.base_registrar import BaseRegistrar
from app.services.domain_service.registrars.godaddy import GoDaddyRegistrar
from app.services.domain_service.registrars.namecheap import NamecheapRegistrar

logger = logging.getLogger(__name__)

class RegistrarType(str, Enum):
    """Supported domain registrars"""
    GODADDY = "godaddy"
    NAMECHEAP = "namecheap"
    GOOGLEDOMAINS = "googledomains"
    CLOUDFLARE = "cloudflare"
    ROUTE53 = "route53"

class RegistrarFactory:
    """
    Factory for creating registrar instances.
    """
    
    @staticmethod
    def create_registrar(registrar_type: str, config: Optional[Dict[str, Any]] = None) -> BaseRegistrar:
        """
        Create a registrar instance based on the specified type.
        
        Args:
            registrar_type: The type of registrar to create
            config: Optional configuration overrides
            
        Returns:
            A registrar instance
        
        Raises:
            ValueError: If the registrar type is not supported
        """
        registrar_type = registrar_type.lower()
        
        # Use provided config or fall back to settings
        if config is None:
            config = {}
            
        # Get API credentials from config or settings
        api_key = config.get("api_key", settings.DOMAIN_REGISTRAR_API_KEY)
        api_secret = config.get("api_secret", settings.DOMAIN_REGISTRAR_API_SECRET)
        
        # Create the appropriate registrar instance
        if registrar_type == RegistrarType.GODADDY:
            is_production = config.get("is_production", not settings.DOMAIN_REGISTRAR_SANDBOX_MODE)
            return GoDaddyRegistrar(
                api_key=api_key,
                api_secret=api_secret,
                is_production=is_production
            )
        elif registrar_type == RegistrarType.NAMECHEAP:
            api_user = config.get("api_user", settings.DOMAIN_REGISTRAR_API_USER)
            username = config.get("username", settings.DOMAIN_REGISTRAR_USERNAME)
            client_ip = config.get("client_ip", settings.DOMAIN_REGISTRAR_CLIENT_IP)
            is_sandbox = config.get("is_sandbox", settings.DOMAIN_REGISTRAR_SANDBOX_MODE)
            return NamecheapRegistrar(
                api_key=api_key,
                api_user=api_user,
                username=username,
                client_ip=client_ip,
                is_sandbox=is_sandbox
            )
        else:
            raise ValueError(f"Unsupported registrar type: {registrar_type}")
    
    @staticmethod
    def get_supported_registrars() -> Dict[str, str]:
        """
        Get a dictionary of supported registrars.
        
        Returns:
            A dictionary mapping registrar types to display names
        """
        return {
            RegistrarType.GODADDY: "GoDaddy",
            RegistrarType.NAMECHEAP: "Namecheap",
            RegistrarType.GOOGLEDOMAINS: "Google Domains (Coming Soon)",
            RegistrarType.CLOUDFLARE: "Cloudflare (Coming Soon)",
            RegistrarType.ROUTE53: "AWS Route 53 (Coming Soon)"
        }
