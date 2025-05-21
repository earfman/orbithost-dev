"""
DNS provider factory and initialization.

This module provides factory functions for getting DNS provider implementations.
"""
import logging
from typing import Dict, Optional, Type

from app.services.domains.credential_storage import ProviderType
from app.services.domains.dns_providers.base import DNSProvider
from app.services.domains.dns_providers.cloudflare import CloudflareDNSProvider
from app.services.domains.dns_providers.route53 import Route53DNSProvider

logger = logging.getLogger(__name__)

# Global provider instances
_providers: Dict[ProviderType, DNSProvider] = {}

def get_dns_provider(provider_type: ProviderType) -> DNSProvider:
    """
    Get a DNS provider implementation for the given provider type.
    
    Args:
        provider_type: Provider type
        
    Returns:
        DNS provider implementation
    """
    global _providers
    
    # Check if provider is already initialized
    if provider_type in _providers:
        return _providers[provider_type]
    
    # Initialize provider
    if provider_type == ProviderType.CLOUDFLARE:
        provider = CloudflareDNSProvider()
    elif provider_type == ProviderType.ROUTE53:
        provider = Route53DNSProvider()
    else:
        raise ValueError(f"Unsupported DNS provider type: {provider_type}")
    
    # Cache provider
    _providers[provider_type] = provider
    
    return provider
