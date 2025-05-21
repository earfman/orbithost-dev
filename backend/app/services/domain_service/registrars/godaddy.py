"""
GoDaddy API integration for OrbitHost.
Implements the GoDaddy Domains API for domain management.
"""

import os
import logging
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.config import settings
from app.services.domain_service.registrars.base_registrar import BaseRegistrar
from app.utils.metrics import track_api_call

logger = logging.getLogger(__name__)

class GoDaddyRegistrar(BaseRegistrar):
    """
    GoDaddy API client for domain management.
    
    Documentation: https://developer.godaddy.com/doc/endpoint/domains
    """
    
    def __init__(self, api_key: str, api_secret: str, is_production: bool = True):
        """
        Initialize the GoDaddy API client.
        
        Args:
            api_key: GoDaddy API key
            api_secret: GoDaddy API secret
            is_production: Whether to use the production API (True) or OTE/test API (False)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.godaddy.com" if is_production else "https://api.ote-godaddy.com"
        self.api_version = "v1"
        
    async def check_availability(self, domain_name: str) -> Dict[str, Any]:
        """
        Check if a domain is available for registration.
        
        Args:
            domain_name: The domain name to check
            
        Returns:
            Dictionary with availability status and pricing
        """
        url = f"{self.base_url}/{self.api_version}/domains/available"
        headers = self._get_headers()
        
        params = {
            "domain": domain_name,
            "checkType": "FULL",  # Get full availability info including price
            "forTransfer": "false"
        }
        
        try:
            start_time = datetime.now()
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params)
                
            track_api_call(
                provider="godaddy",
                endpoint="check_availability",
                status_code=response.status_code,
                duration=(datetime.now() - start_time).total_seconds()
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Format the response to match our common interface
            result = {
                "domain": domain_name,
                "available": data.get("available", False),
                "provider": "godaddy"
            }
            
            if result["available"]:
                result["price"] = data.get("price", 0) / 1000000  # GoDaddy prices are in millicents
                result["currency"] = "USD"
                result["period"] = 1  # years
                
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"GoDaddy API error checking domain availability: {str(e)}")
            if e.response.status_code == 429:
                logger.warning("GoDaddy API rate limit exceeded")
            raise
        except Exception as e:
            logger.error(f"Error checking domain availability with GoDaddy: {str(e)}")
            raise
    
    async def search_domains(self, keyword: str, tlds: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search for available domains based on a keyword.
        
        Args:
            keyword: The keyword to search for
            tlds: List of TLDs to check
            
        Returns:
            List of available domains with pricing
        """
        url = f"{self.base_url}/{self.api_version}/domains/suggest"
        headers = self._get_headers()
        
        # Default TLDs if none provided
        if not tlds:
            tlds = [".com", ".net", ".org", ".io", ".app"]
            
        params = {
            "query": keyword,
            "limit": 25,
            "waitMs": 1000
        }
        
        try:
            start_time = datetime.now()
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params)
                
            track_api_call(
                provider="godaddy",
                endpoint="search_domains",
                status_code=response.status_code,
                duration=(datetime.now() - start_time).total_seconds()
            )
            
            response.raise_for_status()
            suggestions = response.json()
            
            results = []
            for suggestion in suggestions:
                domain = suggestion.get("domain", "")
                
                # Check if domain matches any of the requested TLDs
                if not tlds or any(domain.endswith(tld) for tld in tlds):
                    results.append({
                        "domain": domain,
                        "available": True,  # GoDaddy only returns available domains
                        "price": suggestion.get("price", 0) / 1000000,  # Convert from millicents
                        "currency": "USD",
                        "period": 1,  # years
                        "provider": "godaddy"
                    })
                    
            return results
            
        except httpx.HTTPStatusError as e:
            logger.error(f"GoDaddy API error searching domains: {str(e)}")
            if e.response.status_code == 429:
                logger.warning("GoDaddy API rate limit exceeded")
            raise
        except Exception as e:
            logger.error(f"Error searching domains with GoDaddy: {str(e)}")
            raise
    
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
        url = f"{self.base_url}/{self.api_version}/domains/purchase"
        headers = self._get_headers()
        
        # Default nameservers if none provided
        if not nameservers:
            nameservers = ["ns1.orbithost.app", "ns2.orbithost.app"]
            
        # Default contact info if none provided
        if not contact_info:
            contact_info = self._get_default_contact_info()
            
        # Prepare the request payload
        payload = {
            "domain": domain_name,
            "period": years,
            "nameServers": nameservers,
            "renewAuto": auto_renew,
            "consent": {
                "agreementKeys": [
                    "DNRA"  # Domain Name Registration Agreement
                ],
                "agreedBy": contact_info.get("email", ""),
                "agreedAt": datetime.now().isoformat()
            },
            "contactAdmin": self._format_contact_for_godaddy(contact_info),
            "contactBilling": self._format_contact_for_godaddy(contact_info),
            "contactRegistrant": self._format_contact_for_godaddy(contact_info),
            "contactTech": self._format_contact_for_godaddy(contact_info)
        }
        
        try:
            start_time = datetime.now()
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                
            track_api_call(
                provider="godaddy",
                endpoint="register_domain",
                status_code=response.status_code,
                duration=(datetime.now() - start_time).total_seconds()
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Format the response to match our common interface
            result = {
                "domain": domain_name,
                "order_id": data.get("orderId", ""),
                "status": "registered",
                "created_date": datetime.now().isoformat(),
                "expiry_date": self._calculate_expiry_date(years).isoformat(),
                "auto_renew": auto_renew,
                "nameservers": nameservers,
                "provider": "godaddy"
            }
            
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"GoDaddy API error registering domain: {str(e)}")
            if e.response.status_code == 429:
                logger.warning("GoDaddy API rate limit exceeded")
            raise
        except Exception as e:
            logger.error(f"Error registering domain with GoDaddy: {str(e)}")
            raise
    
    async def get_domain_details(self, domain_name: str) -> Dict[str, Any]:
        """
        Get details for a domain.
        
        Args:
            domain_name: The domain name to get details for
            
        Returns:
            Dictionary with domain details
        """
        url = f"{self.base_url}/{self.api_version}/domains/{domain_name}"
        headers = self._get_headers()
        
        try:
            start_time = datetime.now()
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                
            track_api_call(
                provider="godaddy",
                endpoint="get_domain_details",
                status_code=response.status_code,
                duration=(datetime.now() - start_time).total_seconds()
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Format the response to match our common interface
            result = {
                "domain": domain_name,
                "status": data.get("status", ""),
                "created_date": data.get("createdAt", ""),
                "expiry_date": data.get("expires", ""),
                "auto_renew": data.get("renewAuto", False),
                "locked": data.get("locked", False),
                "nameservers": data.get("nameServers", []),
                "privacy": data.get("privacy", False),
                "provider": "godaddy"
            }
            
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"GoDaddy API error getting domain details: {str(e)}")
            if e.response.status_code == 429:
                logger.warning("GoDaddy API rate limit exceeded")
            raise
        except Exception as e:
            logger.error(f"Error getting domain details with GoDaddy: {str(e)}")
            raise
    
    async def update_nameservers(self, domain_name: str, nameservers: List[str]) -> Dict[str, Any]:
        """
        Update nameservers for a domain.
        
        Args:
            domain_name: The domain name to update nameservers for
            nameservers: List of nameservers to use
            
        Returns:
            Dictionary with update status
        """
        url = f"{self.base_url}/{self.api_version}/domains/{domain_name}"
        headers = self._get_headers()
        
        payload = {
            "nameServers": nameservers
        }
        
        try:
            start_time = datetime.now()
            async with httpx.AsyncClient() as client:
                response = await client.patch(url, headers=headers, json=payload)
                
            track_api_call(
                provider="godaddy",
                endpoint="update_nameservers",
                status_code=response.status_code,
                duration=(datetime.now() - start_time).total_seconds()
            )
            
            response.raise_for_status()
            
            # Format the response to match our common interface
            result = {
                "domain": domain_name,
                "nameservers": nameservers,
                "status": "updated",
                "provider": "godaddy"
            }
            
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"GoDaddy API error updating nameservers: {str(e)}")
            if e.response.status_code == 429:
                logger.warning("GoDaddy API rate limit exceeded")
            raise
        except Exception as e:
            logger.error(f"Error updating nameservers with GoDaddy: {str(e)}")
            raise
    
    def _get_headers(self) -> Dict[str, str]:
        """Get the headers required for GoDaddy API requests."""
        return {
            "Authorization": f"sso-key {self.api_key}:{self.api_secret}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _format_contact_for_godaddy(self, contact_info: Dict[str, Any]) -> Dict[str, Any]:
        """Format contact information for GoDaddy API."""
        return {
            "nameFirst": contact_info.get("first_name", ""),
            "nameLast": contact_info.get("last_name", ""),
            "email": contact_info.get("email", ""),
            "phone": contact_info.get("phone", ""),
            "addressMailing": {
                "address1": contact_info.get("address1", ""),
                "address2": contact_info.get("address2", ""),
                "city": contact_info.get("city", ""),
                "state": contact_info.get("state", ""),
                "postalCode": contact_info.get("postal_code", ""),
                "country": contact_info.get("country", "US")
            }
        }
    
    def _get_default_contact_info(self) -> Dict[str, Any]:
        """Get default contact information."""
        return {
            "first_name": "OrbitHost",
            "last_name": "Admin",
            "email": "domains@orbithost.app",
            "phone": "+1.5555555555",
            "address1": "123 Main St",
            "city": "San Francisco",
            "state": "CA",
            "postal_code": "94105",
            "country": "US"
        }
    
    def _calculate_expiry_date(self, years: int) -> datetime:
        """Calculate the expiry date based on the registration period."""
        return datetime.now().replace(year=datetime.now().year + years)
