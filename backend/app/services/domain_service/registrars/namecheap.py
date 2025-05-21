"""
Namecheap API integration for OrbitHost.
Implements the Namecheap API for domain management.
"""

import os
import logging
import httpx
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib

from app.core.config import settings
from app.services.domain_service.registrars.base_registrar import BaseRegistrar
from app.utils.metrics import track_api_call

logger = logging.getLogger(__name__)

class NamecheapRegistrar(BaseRegistrar):
    """
    Namecheap API client for domain management.
    
    Documentation: https://www.namecheap.com/support/api/intro/
    """
    
    def __init__(self, api_key: str, api_user: str, username: str, client_ip: str, is_sandbox: bool = False):
        """
        Initialize the Namecheap API client.
        
        Args:
            api_key: Namecheap API key
            api_user: Namecheap API user
            username: Namecheap username
            client_ip: Client IP address (required by Namecheap API)
            is_sandbox: Whether to use the sandbox API (True) or production API (False)
        """
        self.api_key = api_key
        self.api_user = api_user
        self.username = username
        self.client_ip = client_ip
        self.base_url = "https://api.sandbox.namecheap.com/xml.response" if is_sandbox else "https://api.namecheap.com/xml.response"
        
    async def check_availability(self, domain_name: str) -> Dict[str, Any]:
        """
        Check if a domain is available for registration.
        
        Args:
            domain_name: The domain name to check
            
        Returns:
            Dictionary with availability status and pricing
        """
        # Split domain into SLD (second-level domain) and TLD
        parts = domain_name.split(".")
        if len(parts) < 2:
            raise ValueError(f"Invalid domain name: {domain_name}")
            
        sld = parts[0]
        tld = ".".join(parts[1:])
        
        params = {
            "ApiUser": self.api_user,
            "ApiKey": self.api_key,
            "UserName": self.username,
            "ClientIp": self.client_ip,
            "Command": "namecheap.domains.check",
            "DomainList": domain_name
        }
        
        try:
            start_time = datetime.now()
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params)
                
            track_api_call(
                provider="namecheap",
                endpoint="check_availability",
                status_code=response.status_code,
                duration=(datetime.now() - start_time).total_seconds()
            )
            
            response.raise_for_status()
            xml_response = response.text
            
            # Parse XML response
            root = ET.fromstring(xml_response)
            
            # Check for errors
            error_count = int(root.find(".//Errors").get("Count", "0"))
            if error_count > 0:
                error_msg = root.find(".//Errors/Error").text
                logger.error(f"Namecheap API error: {error_msg}")
                raise Exception(f"Namecheap API error: {error_msg}")
            
            # Get domain availability
            domain_check = root.find(".//DomainCheckResult")
            if domain_check is None:
                raise Exception("No domain check result found in response")
                
            available = domain_check.get("Available", "").lower() == "true"
            
            # Format the response to match our common interface
            result = {
                "domain": domain_name,
                "available": available,
                "provider": "namecheap"
            }
            
            if available:
                # Get pricing
                pricing = await self._get_domain_pricing(sld, tld)
                if pricing:
                    result.update(pricing)
                
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Namecheap API error checking domain availability: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error checking domain availability with Namecheap: {str(e)}")
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
        # Default TLDs if none provided
        if not tlds:
            tlds = [".com", ".net", ".org", ".io", ".app"]
            
        results = []
        for tld in tlds:
            domain = f"{keyword}{tld}"
            try:
                availability = await self.check_availability(domain)
                if availability["available"]:
                    results.append(availability)
            except Exception as e:
                logger.error(f"Error checking availability for {domain}: {str(e)}")
                results.append({
                    "domain": domain,
                    "available": False,
                    "error": str(e),
                    "provider": "namecheap"
                })
        
        return results
    
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
        # Split domain into SLD (second-level domain) and TLD
        parts = domain_name.split(".")
        if len(parts) < 2:
            raise ValueError(f"Invalid domain name: {domain_name}")
            
        sld = parts[0]
        tld = ".".join(parts[1:])
        
        # Default nameservers if none provided
        if not nameservers:
            nameservers = ["ns1.orbithost.app", "ns2.orbithost.app"]
            
        # Default contact info if none provided
        if not contact_info:
            contact_info = self._get_default_contact_info()
        
        # Prepare the request parameters
        params = {
            "ApiUser": self.api_user,
            "ApiKey": self.api_key,
            "UserName": self.username,
            "ClientIp": self.client_ip,
            "Command": "namecheap.domains.create",
            "DomainName": domain_name,
            "Years": years,
            "AuxBillingFirstName": contact_info.get("first_name", ""),
            "AuxBillingLastName": contact_info.get("last_name", ""),
            "AuxBillingAddress1": contact_info.get("address1", ""),
            "AuxBillingCity": contact_info.get("city", ""),
            "AuxBillingStateProvince": contact_info.get("state", ""),
            "AuxBillingPostalCode": contact_info.get("postal_code", ""),
            "AuxBillingCountry": contact_info.get("country", "US"),
            "AuxBillingPhone": contact_info.get("phone", ""),
            "AuxBillingEmailAddress": contact_info.get("email", ""),
            "TechFirstName": contact_info.get("first_name", ""),
            "TechLastName": contact_info.get("last_name", ""),
            "TechAddress1": contact_info.get("address1", ""),
            "TechCity": contact_info.get("city", ""),
            "TechStateProvince": contact_info.get("state", ""),
            "TechPostalCode": contact_info.get("postal_code", ""),
            "TechCountry": contact_info.get("country", "US"),
            "TechPhone": contact_info.get("phone", ""),
            "TechEmailAddress": contact_info.get("email", ""),
            "AdminFirstName": contact_info.get("first_name", ""),
            "AdminLastName": contact_info.get("last_name", ""),
            "AdminAddress1": contact_info.get("address1", ""),
            "AdminCity": contact_info.get("city", ""),
            "AdminStateProvince": contact_info.get("state", ""),
            "AdminPostalCode": contact_info.get("postal_code", ""),
            "AdminCountry": contact_info.get("country", "US"),
            "AdminPhone": contact_info.get("phone", ""),
            "AdminEmailAddress": contact_info.get("email", ""),
            "RegistrantFirstName": contact_info.get("first_name", ""),
            "RegistrantLastName": contact_info.get("last_name", ""),
            "RegistrantAddress1": contact_info.get("address1", ""),
            "RegistrantCity": contact_info.get("city", ""),
            "RegistrantStateProvince": contact_info.get("state", ""),
            "RegistrantPostalCode": contact_info.get("postal_code", ""),
            "RegistrantCountry": contact_info.get("country", "US"),
            "RegistrantPhone": contact_info.get("phone", ""),
            "RegistrantEmailAddress": contact_info.get("email", ""),
            "AddFreeWhoisguard": "yes",
            "WGEnabled": "yes",
            "Nameservers": ",".join(nameservers)
        }
        
        try:
            start_time = datetime.now()
            async with httpx.AsyncClient() as client:
                response = await client.post(self.base_url, params=params)
                
            track_api_call(
                provider="namecheap",
                endpoint="register_domain",
                status_code=response.status_code,
                duration=(datetime.now() - start_time).total_seconds()
            )
            
            response.raise_for_status()
            xml_response = response.text
            
            # Parse XML response
            root = ET.fromstring(xml_response)
            
            # Check for errors
            error_count = int(root.find(".//Errors").get("Count", "0"))
            if error_count > 0:
                error_msg = root.find(".//Errors/Error").text
                logger.error(f"Namecheap API error: {error_msg}")
                raise Exception(f"Namecheap API error: {error_msg}")
            
            # Get registration result
            domain_create = root.find(".//DomainCreateResult")
            if domain_create is None:
                raise Exception("No domain create result found in response")
                
            registered = domain_create.get("Registered", "").lower() == "true"
            if not registered:
                raise Exception("Domain registration failed")
            
            # Format the response to match our common interface
            result = {
                "domain": domain_name,
                "order_id": domain_create.get("OrderID", ""),
                "transaction_id": domain_create.get("TransactionID", ""),
                "status": "registered",
                "created_date": datetime.now().isoformat(),
                "expiry_date": self._calculate_expiry_date(years).isoformat(),
                "auto_renew": auto_renew,
                "nameservers": nameservers,
                "provider": "namecheap"
            }
            
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Namecheap API error registering domain: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error registering domain with Namecheap: {str(e)}")
            raise
    
    async def get_domain_details(self, domain_name: str) -> Dict[str, Any]:
        """
        Get details for a domain.
        
        Args:
            domain_name: The domain name to get details for
            
        Returns:
            Dictionary with domain details
        """
        # Split domain into SLD (second-level domain) and TLD
        parts = domain_name.split(".")
        if len(parts) < 2:
            raise ValueError(f"Invalid domain name: {domain_name}")
            
        sld = parts[0]
        tld = ".".join(parts[1:])
        
        params = {
            "ApiUser": self.api_user,
            "ApiKey": self.api_key,
            "UserName": self.username,
            "ClientIp": self.client_ip,
            "Command": "namecheap.domains.getInfo",
            "DomainName": domain_name
        }
        
        try:
            start_time = datetime.now()
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params)
                
            track_api_call(
                provider="namecheap",
                endpoint="get_domain_details",
                status_code=response.status_code,
                duration=(datetime.now() - start_time).total_seconds()
            )
            
            response.raise_for_status()
            xml_response = response.text
            
            # Parse XML response
            root = ET.fromstring(xml_response)
            
            # Check for errors
            error_count = int(root.find(".//Errors").get("Count", "0"))
            if error_count > 0:
                error_msg = root.find(".//Errors/Error").text
                logger.error(f"Namecheap API error: {error_msg}")
                raise Exception(f"Namecheap API error: {error_msg}")
            
            # Get domain info
            domain_info = root.find(".//DomainGetInfoResult")
            if domain_info is None:
                raise Exception("No domain info found in response")
                
            # Get nameservers
            nameservers_elem = domain_info.find(".//Nameservers")
            nameservers = []
            if nameservers_elem is not None:
                for ns in nameservers_elem.findall(".//Nameserver"):
                    if ns.text:
                        nameservers.append(ns.text)
            
            # Format the response to match our common interface
            result = {
                "domain": domain_name,
                "status": domain_info.get("Status", ""),
                "created_date": domain_info.get("CreatedDate", ""),
                "expiry_date": domain_info.get("ExpiredDate", ""),
                "auto_renew": domain_info.get("AutoRenew", "").lower() == "true",
                "locked": domain_info.get("IsLocked", "").lower() == "true",
                "nameservers": nameservers,
                "privacy": domain_info.get("WhoisGuard", "").lower() == "enabled",
                "provider": "namecheap"
            }
            
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Namecheap API error getting domain details: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error getting domain details with Namecheap: {str(e)}")
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
        # Split domain into SLD (second-level domain) and TLD
        parts = domain_name.split(".")
        if len(parts) < 2:
            raise ValueError(f"Invalid domain name: {domain_name}")
            
        sld = parts[0]
        tld = ".".join(parts[1:])
        
        params = {
            "ApiUser": self.api_user,
            "ApiKey": self.api_key,
            "UserName": self.username,
            "ClientIp": self.client_ip,
            "Command": "namecheap.domains.dns.setCustom",
            "SLD": sld,
            "TLD": tld,
            "Nameservers": ",".join(nameservers)
        }
        
        try:
            start_time = datetime.now()
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params)
                
            track_api_call(
                provider="namecheap",
                endpoint="update_nameservers",
                status_code=response.status_code,
                duration=(datetime.now() - start_time).total_seconds()
            )
            
            response.raise_for_status()
            xml_response = response.text
            
            # Parse XML response
            root = ET.fromstring(xml_response)
            
            # Check for errors
            error_count = int(root.find(".//Errors").get("Count", "0"))
            if error_count > 0:
                error_msg = root.find(".//Errors/Error").text
                logger.error(f"Namecheap API error: {error_msg}")
                raise Exception(f"Namecheap API error: {error_msg}")
            
            # Get result
            result_elem = root.find(".//DomainDNSSetCustomResult")
            if result_elem is None:
                raise Exception("No result found in response")
                
            success = result_elem.get("Updated", "").lower() == "true"
            if not success:
                raise Exception("Failed to update nameservers")
            
            # Format the response to match our common interface
            result = {
                "domain": domain_name,
                "nameservers": nameservers,
                "status": "updated",
                "provider": "namecheap"
            }
            
            return result
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Namecheap API error updating nameservers: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error updating nameservers with Namecheap: {str(e)}")
            raise
    
    async def _get_domain_pricing(self, sld: str, tld: str) -> Dict[str, Any]:
        """
        Get pricing for a domain.
        
        Args:
            sld: Second-level domain
            tld: Top-level domain
            
        Returns:
            Dictionary with pricing information
        """
        params = {
            "ApiUser": self.api_user,
            "ApiKey": self.api_key,
            "UserName": self.username,
            "ClientIp": self.client_ip,
            "Command": "namecheap.users.getPricing",
            "ProductType": "DOMAIN",
            "ProductCategory": "DOMAINS",
            "ActionName": "REGISTER",
            "ProductName": tld.lstrip(".")
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, params=params)
                
            response.raise_for_status()
            xml_response = response.text
            
            # Parse XML response
            root = ET.fromstring(xml_response)
            
            # Check for errors
            error_count = int(root.find(".//Errors").get("Count", "0"))
            if error_count > 0:
                error_msg = root.find(".//Errors/Error").text
                logger.error(f"Namecheap API error: {error_msg}")
                return {}
            
            # Get pricing
            product = root.find(".//Product")
            if product is None:
                return {}
                
            price_elem = product.find(".//Price")
            if price_elem is None:
                return {}
                
            price = float(price_elem.get("Price", "0"))
            
            return {
                "price": price,
                "currency": "USD",
                "period": 1  # years
            }
            
        except Exception as e:
            logger.error(f"Error getting domain pricing: {str(e)}")
            return {}
    
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
