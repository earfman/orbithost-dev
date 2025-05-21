"""
Domain service for OrbitHost.
This is part of the private components that implement domain management features.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.models.user import User, SubscriptionTier
from app.services.domain_service.registrars.factory import RegistrarFactory, RegistrarType
from app.services.domain_service.dns_provider import DNSProvider
from app.services.credential_service import CredentialService

logger = logging.getLogger(__name__)

class DomainService:
    """
    Service for managing domains in OrbitHost.
    Handles domain registration, DNS configuration, and SSL provisioning.
    """
    
    def __init__(self):
        self.credential_service = CredentialService()
        self.dns_provider = DNSProvider()
        self.default_registrar_type = os.getenv("DEFAULT_DOMAIN_REGISTRAR", RegistrarType.GODADDY)
    
    async def check_domain_availability(self, domain_name: str, registrar_type: str = None, user_id: str = None) -> Dict[str, Any]:
        """
        Check if a domain is available for registration.
        
        Args:
            domain_name: The domain name to check
            registrar_type: The registrar to use (defaults to system default)
            user_id: The user ID to get credentials for (if None, uses system credentials)
            
        Returns:
            Dictionary with availability status and pricing
        """
        try:
            # Use specified registrar or default
            registrar_type = registrar_type or self.default_registrar_type
            
            # Get credentials if user_id is provided
            config = None
            if user_id:
                credentials = await self.credential_service.get_credentials(user_id, registrar_type)
                if credentials:
                    config = credentials
            
            # Create registrar instance
            registrar = RegistrarFactory.create_registrar(registrar_type, config)
            
            # Check domain availability
            return await registrar.check_availability(domain_name)
        except Exception as e:
            logger.error(f"Error checking domain availability for {domain_name}: {str(e)}")
            raise
    
    async def search_domains(self, keyword: str, tlds: List[str] = None, registrar_type: str = None, user_id: str = None) -> List[Dict[str, Any]]:
        """
        Search for available domains based on a keyword.
        
        Args:
            keyword: The keyword to search for
            tlds: List of TLDs to check (e.g., ['.com', '.org', '.io'])
            registrar_type: The registrar to use (defaults to system default)
            user_id: The user ID to get credentials for (if None, uses system credentials)
            
        Returns:
            List of available domains with pricing
        """
        try:
            # Use specified registrar or default
            registrar_type = registrar_type or self.default_registrar_type
            
            # Get credentials if user_id is provided
            config = None
            if user_id:
                credentials = await self.credential_service.get_credentials(user_id, registrar_type)
                if credentials:
                    config = credentials
            
            # Create registrar instance
            registrar = RegistrarFactory.create_registrar(registrar_type, config)
            
            # Search domains
            return await registrar.search_domains(keyword, tlds)
        except Exception as e:
            logger.error(f"Error searching domains for {keyword}: {str(e)}")
            raise
    
    async def register_domain(
        self, 
        user: User, 
        domain_name: str, 
        years: int = 1,
        contact_info: Dict[str, Any] = None,
        nameservers: List[str] = None,
        auto_renew: bool = False,
        registrar_type: str = None
    ) -> Dict[str, Any]:
        """
        Register a domain for a user.
        
        Args:
            user: The user registering the domain
            domain_name: The domain name to register
            years: Number of years to register for
            contact_info: Contact information for domain registration
            nameservers: List of nameservers to use
            auto_renew: Whether to enable auto-renewal
            registrar_type: The registrar to use (defaults to user's preferred registrar or system default)
            
        Returns:
            Dictionary with registration details
        """
        # Check user's subscription tier
        if user.subscription.tier == SubscriptionTier.FREE:
            raise ValueError("Custom domains require a Pro or Business subscription")
        
        # Check if user has reached their domain limit
        # In a real implementation, we would check how many domains the user already has
        
        try:
            # Use specified registrar or get user's preferred registrar or default
            if not registrar_type:
                # Get user's preferred registrar from their stored credentials
                user_credentials = await self.credential_service.list_user_credentials(user.id)
                if user_credentials:
                    # Use the most recently used registrar
                    registrar_type = user_credentials[0].get("provider")
                else:
                    registrar_type = self.default_registrar_type
            
            # Get user's credentials for the registrar
            config = None
            credentials = await self.credential_service.get_credentials(user.id, registrar_type)
            if credentials:
                config = credentials
            else:
                # If no user credentials, check if they want to use the system credentials
                # In a real implementation, this would be a user preference setting
                # For now, we'll just use the system credentials
                pass
            
            # Create registrar instance
            registrar = RegistrarFactory.create_registrar(registrar_type, config)
            
            # Default nameservers if none provided
            if not nameservers:
                nameservers = ["ns1.orbithost.app", "ns2.orbithost.app"]
            
            # Register domain with registrar
            registration = await registrar.register_domain(
                domain_name=domain_name,
                years=years,
                contact_info=contact_info,
                nameservers=nameservers,
                auto_renew=auto_renew
            )
            
            # Configure DNS
            dns_config = await self.dns_provider.configure_domain(
                domain_name=domain_name,
                user_id=user.id
            )
            
            # Provision SSL certificate
            ssl_config = await self.provision_ssl(domain_name)
            
            # Return combined result
            return {
                "domain": registration,
                "dns": dns_config,
                "ssl": ssl_config,
                "registrar": registrar_type
            }
        except Exception as e:
            logger.error(f"Error registering domain {domain_name} for user {user.id}: {str(e)}")
            raise
    
    async def connect_existing_domain(
        self, 
        user: User, 
        domain_name: str
    ) -> Dict[str, Any]:
        """
        Connect an existing domain to OrbitHost.
        
        Args:
            user: The user connecting the domain
            domain_name: The domain name to connect
            
        Returns:
            Dictionary with connection details
        """
        # Check user's subscription tier
        if user.subscription.tier == SubscriptionTier.FREE:
            raise ValueError("Custom domains require a Pro or Business subscription")
        
        try:
            # Configure DNS
            dns_config = await self.dns_provider.configure_domain(
                domain_name=domain_name,
                user_id=user.id
            )
            
            # Provision SSL certificate
            ssl_config = await self.provision_ssl(domain_name)
            
            # Return combined result
            return {
                "dns": dns_config,
                "ssl": ssl_config
            }
        except Exception as e:
            logger.error(f"Error connecting domain {domain_name} for user {user.id}: {str(e)}")
            raise
    
    async def verify_domain(self, domain_name: str) -> Dict[str, Any]:
        """
        Verify domain ownership by checking DNS records.
        
        Args:
            domain_name: The domain name to verify
            
        Returns:
            Dictionary with verification status
        """
        try:
            return await self.dns_provider.verify_domain(domain_name)
        except Exception as e:
            logger.error(f"Error verifying domain {domain_name}: {str(e)}")
            raise
    
    async def update_nameservers(
        self,
        user: User,
        domain_name: str,
        nameservers: List[str],
        registrar_type: str = None
    ) -> Dict[str, Any]:
        """
        Update nameservers for a domain.
        
        Args:
            user: The user who owns the domain
            domain_name: The domain name to update nameservers for
            nameservers: List of nameservers to use
            registrar_type: The registrar to use (defaults to the registrar used for the domain)
            
        Returns:
            Dictionary with update status
        """
        try:
            # Use specified registrar or get the registrar used for the domain
            if not registrar_type:
                # In a real implementation, we would look up the domain in the database
                # to determine which registrar was used for registration
                # For now, we'll get the user's preferred registrar
                user_credentials = await self.credential_service.list_user_credentials(user.id)
                if user_credentials:
                    registrar_type = user_credentials[0].get("provider")
                else:
                    registrar_type = self.default_registrar_type
            
            # Get user's credentials for the registrar
            config = None
            credentials = await self.credential_service.get_credentials(user.id, registrar_type)
            if credentials:
                config = credentials
            
            # Create registrar instance
            registrar = RegistrarFactory.create_registrar(registrar_type, config)
            
            # Update nameservers
            result = await registrar.update_nameservers(domain_name, nameservers)
            
            # Update DNS configuration
            dns_config = await self.dns_provider.configure_domain(
                domain_name=domain_name,
                user_id=user.id,
                nameservers=nameservers
            )
            
            # Return combined result
            return {
                "nameservers": result,
                "dns": dns_config,
                "registrar": registrar_type
            }
        except Exception as e:
            logger.error(f"Error updating nameservers for domain {domain_name}: {str(e)}")
            raise
    
    async def provision_ssl(self, domain_name: str) -> Dict[str, Any]:
        """
        Provision an SSL certificate for a domain.
        
        Args:
            domain_name: The domain name to provision SSL for
            
        Returns:
            Dictionary with SSL provisioning details
        """
        try:
            # In a real implementation, we would use Let's Encrypt or a similar service
            # For now, we'll simulate the SSL provisioning
            return {
                "status": "success",
                "certificate_expiry": datetime.now().replace(year=datetime.now().year + 1).isoformat(),
                "issuer": "Let's Encrypt"
            }
        except Exception as e:
            logger.error(f"Error provisioning SSL for domain {domain_name}: {str(e)}")
            raise
    
    async def get_domain_details(self, domain_name: str) -> Dict[str, Any]:
        """
        Get details for a domain.
        
        Args:
            domain_name: The domain name to get details for
            
        Returns:
            Dictionary with domain details
        """
        try:
            # Get domain details from reseller
            domain_details = await self.reseller_client.get_domain_details(domain_name)
            
            # Get DNS configuration
            dns_config = await self.dns_provider.get_dns_records(domain_name)
            
            # Return combined result
            return {
                "domain": domain_details,
                "dns": dns_config
            }
        except Exception as e:
            logger.error(f"Error getting domain details for {domain_name}: {str(e)}")
            raise
    
    async def update_dns_records(
        self, 
        domain_name: str, 
        records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update DNS records for a domain.
        
        Args:
            domain_name: The domain name to update DNS records for
            records: List of DNS records to update
            
        Returns:
            Dictionary with update status
        """
        try:
            return await self.dns_provider.update_dns_records(domain_name, records)
        except Exception as e:
            logger.error(f"Error updating DNS records for {domain_name}: {str(e)}")
            raise
    
    async def renew_domain(
        self, 
        domain_name: str, 
        years: int = 1
    ) -> Dict[str, Any]:
        """
        Renew a domain registration.
        
        Args:
            domain_name: The domain name to renew
            years: Number of years to renew for
            
        Returns:
            Dictionary with renewal details
        """
        try:
            return await self.reseller_client.renew_domain(domain_name, years)
        except Exception as e:
            logger.error(f"Error renewing domain {domain_name}: {str(e)}")
            raise
    
    async def transfer_domain(
        self, 
        domain_name: str, 
        auth_code: str,
        contact_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Transfer a domain to OrbitHost.
        
        Args:
            domain_name: The domain name to transfer
            auth_code: Authorization code for the transfer
            contact_info: Contact information for domain transfer
            
        Returns:
            Dictionary with transfer details
        """
        try:
            return await self.reseller_client.transfer_domain(
                domain_name=domain_name,
                auth_code=auth_code,
                contact_info=contact_info
            )
        except Exception as e:
            logger.error(f"Error transferring domain {domain_name}: {str(e)}")
            raise
