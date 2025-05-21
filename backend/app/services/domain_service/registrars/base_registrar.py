"""
Base registrar interface for OrbitHost.
Defines the common interface for all domain registrar implementations.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseRegistrar(ABC):
    """
    Base class for domain registrar implementations.
    All registrar-specific implementations should inherit from this class.
    """
    
    @abstractmethod
    async def check_availability(self, domain_name: str) -> Dict[str, Any]:
        """
        Check if a domain is available for registration.
        
        Args:
            domain_name: The domain name to check
            
        Returns:
            Dictionary with availability status and pricing
        """
        pass
    
    @abstractmethod
    async def search_domains(self, keyword: str, tlds: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search for available domains based on a keyword.
        
        Args:
            keyword: The keyword to search for
            tlds: List of TLDs to check
            
        Returns:
            List of available domains with pricing
        """
        pass
    
    @abstractmethod
    async def register_domain(
        self, 
        domain_name: str, 
        years: int = 1,
        contact_info: Dict[str, Any] = None,
        nameservers: List[str] = None,
        auto_renew: bool = False
    ) -> Dict[str, Any]:
        """
        Register a domain.
        
        Args:
            domain_name: The domain name to register
            years: Number of years to register for
            contact_info: Contact information for domain registration
            nameservers: List of nameservers to use
            auto_renew: Whether to enable auto-renewal
            
        Returns:
            Dictionary with registration details
        """
        pass
    
    @abstractmethod
    async def get_domain_details(self, domain_name: str) -> Dict[str, Any]:
        """
        Get details for a domain.
        
        Args:
            domain_name: The domain name to get details for
            
        Returns:
            Dictionary with domain details
        """
        pass
    
    @abstractmethod
    async def update_nameservers(self, domain_name: str, nameservers: List[str]) -> Dict[str, Any]:
        """
        Update nameservers for a domain.
        
        Args:
            domain_name: The domain name to update nameservers for
            nameservers: List of nameservers to use
            
        Returns:
            Dictionary with update status
        """
        pass
