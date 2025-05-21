"""
DNS verification service.

This module provides functionality for verifying domain ownership and DNS configuration
through various verification methods like DNS TXT records, HTTP verification, and email verification.
"""
import logging
import uuid
import time
import random
import string
import dns.resolver
from enum import Enum
from typing import Any, Dict, List, Optional, Union, Tuple

from app.services.domains.credential_storage import (
    get_credential_storage,
    APICredential,
    ProviderType,
)
from app.services.domains.dns_configurator import (
    get_dns_configurator,
    DNSConfigurationError,
)
from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

class VerificationMethod(str, Enum):
    """Verification methods for domain ownership."""
    DNS_TXT = "dns_txt"
    HTTP = "http"
    EMAIL = "email"

class VerificationStatus(str, Enum):
    """Status of verification."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"

class VerificationError(Exception):
    """Exception raised for verification errors."""
    pass

class DomainVerification:
    """Model for domain verification."""
    
    def __init__(
        self,
        id: str,
        user_id: str,
        domain: str,
        method: VerificationMethod,
        token: str,
        status: VerificationStatus = VerificationStatus.PENDING,
        record_name: Optional[str] = None,
        record_value: Optional[str] = None,
        http_path: Optional[str] = None,
        email: Optional[str] = None,
        error: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        expires_at: Optional[str] = None,
    ):
        """
        Initialize a domain verification.
        
        Args:
            id: Verification ID
            user_id: ID of the user
            domain: Domain name
            method: Verification method
            token: Verification token
            status: Verification status
            record_name: DNS record name for DNS verification
            record_value: DNS record value for DNS verification
            http_path: HTTP path for HTTP verification
            email: Email address for email verification
            error: Error message if verification failed
            created_at: Creation timestamp
            updated_at: Last update timestamp
            expires_at: Expiration timestamp
        """
        self.id = id
        self.user_id = user_id
        self.domain = domain
        self.method = method
        self.token = token
        self.status = status
        self.record_name = record_name
        self.record_value = record_value
        self.http_path = http_path
        self.email = email
        self.error = error
        self.created_at = created_at
        self.updated_at = updated_at
        self.expires_at = expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "domain": self.domain,
            "method": self.method.value,
            "token": self.token,
            "status": self.status.value,
            "record_name": self.record_name,
            "record_value": self.record_value,
            "http_path": self.http_path,
            "email": self.email,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "expires_at": self.expires_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DomainVerification":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            domain=data["domain"],
            method=VerificationMethod(data["method"]),
            token=data["token"],
            status=VerificationStatus(data["status"]),
            record_name=data.get("record_name"),
            record_value=data.get("record_value"),
            http_path=data.get("http_path"),
            email=data.get("email"),
            error=data.get("error"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            expires_at=data.get("expires_at"),
        )

class DNSVerificationService:
    """Service for verifying domain ownership and DNS configuration."""
    
    def __init__(self):
        """Initialize the DNS verification service."""
        self.verifications = {}
        logger.info("Initialized DNS verification service")
    
    def _generate_token(self, length: int = 32) -> str:
        """
        Generate a random verification token.
        
        Args:
            length: Length of the token
            
        Returns:
            Random verification token
        """
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(length))
    
    async def create_verification(
        self,
        user_id: str,
        domain: str,
        method: VerificationMethod = VerificationMethod.DNS_TXT,
        email: Optional[str] = None,
    ) -> DomainVerification:
        """
        Create a domain verification.
        
        Args:
            user_id: ID of the user
            domain: Domain name
            method: Verification method
            email: Email address for email verification
            
        Returns:
            Domain verification
        """
        try:
            # Generate verification ID
            verification_id = str(uuid.uuid4())
            
            # Generate verification token
            token = self._generate_token()
            
            # Prepare verification data based on method
            record_name = None
            record_value = None
            http_path = None
            
            if method == VerificationMethod.DNS_TXT:
                record_name = f"_orbithost-verification.{domain}"
                record_value = f"orbithost-verification={token}"
            elif method == VerificationMethod.HTTP:
                http_path = f"/.well-known/orbithost-verification/{token}"
            elif method == VerificationMethod.EMAIL and not email:
                # Email verification requires an email address
                raise VerificationError("Email address is required for email verification")
            
            # Create verification
            verification = DomainVerification(
                id=verification_id,
                user_id=user_id,
                domain=domain,
                method=method,
                token=token,
                status=VerificationStatus.PENDING,
                record_name=record_name,
                record_value=record_value,
                http_path=http_path,
                email=email,
            )
            
            # Store verification
            self.verifications[verification_id] = verification
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_verification",
                "operation": "create",
                "verification_id": verification_id,
                "user_id": user_id,
                "domain": domain,
                "method": method.value,
            })
            
            return verification
        except Exception as e:
            logger.error(f"Error creating verification: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_verification",
                "operation": "create",
                "status": "error",
                "user_id": user_id,
                "domain": domain,
                "method": method.value if isinstance(method, VerificationMethod) else method,
                "error": str(e),
            })
            
            raise VerificationError(f"Failed to create verification: {str(e)}")
    
    async def verify_dns_txt(
        self,
        verification_id: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify domain ownership using DNS TXT record.
        
        Args:
            verification_id: Verification ID
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get verification
            verification = self.verifications.get(verification_id)
            
            if not verification:
                return False, f"Verification {verification_id} not found"
            
            if verification.method != VerificationMethod.DNS_TXT:
                return False, f"Verification {verification_id} is not a DNS TXT verification"
            
            # Update status
            verification.status = VerificationStatus.IN_PROGRESS
            
            # Extract domain from record name
            record_domain = verification.domain
            record_name = "_orbithost-verification"
            
            # Query DNS TXT record
            try:
                answers = dns.resolver.resolve(f"{record_name}.{record_domain}", "TXT")
                
                # Check if any of the TXT records match the expected value
                expected_value = f"orbithost-verification={verification.token}"
                
                for rdata in answers:
                    for txt_string in rdata.strings:
                        txt_value = txt_string.decode("utf-8")
                        
                        if txt_value == expected_value:
                            # Verification successful
                            verification.status = VerificationStatus.VERIFIED
                            
                            # Log to MCP
                            await get_mcp_client().send({
                                "type": "dns_verification",
                                "operation": "verify_dns_txt",
                                "status": "success",
                                "verification_id": verification_id,
                                "user_id": verification.user_id,
                                "domain": verification.domain,
                            })
                            
                            return True, None
                
                # No matching TXT record found
                return False, f"TXT record with value '{expected_value}' not found"
            except dns.resolver.NXDOMAIN:
                return False, f"TXT record '{record_name}.{record_domain}' not found"
            except dns.resolver.NoAnswer:
                return False, f"No TXT records found for '{record_name}.{record_domain}'"
            except dns.exception.DNSException as e:
                return False, f"DNS error: {str(e)}"
        except Exception as e:
            logger.error(f"Error verifying DNS TXT record: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_verification",
                "operation": "verify_dns_txt",
                "status": "error",
                "verification_id": verification_id,
                "error": str(e),
            })
            
            return False, f"Failed to verify DNS TXT record: {str(e)}"
    
    async def verify_http(
        self,
        verification_id: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify domain ownership using HTTP verification.
        
        Args:
            verification_id: Verification ID
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get verification
            verification = self.verifications.get(verification_id)
            
            if not verification:
                return False, f"Verification {verification_id} not found"
            
            if verification.method != VerificationMethod.HTTP:
                return False, f"Verification {verification_id} is not an HTTP verification"
            
            # Update status
            verification.status = VerificationStatus.IN_PROGRESS
            
            # HTTP verification would typically involve making an HTTP request
            # to the specified path and checking if the content matches the token
            # For now, we'll just return a placeholder implementation
            
            # Placeholder implementation
            success = False
            error = "HTTP verification not implemented yet"
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_verification",
                "operation": "verify_http",
                "status": "error",
                "verification_id": verification_id,
                "user_id": verification.user_id,
                "domain": verification.domain,
                "error": error,
            })
            
            return success, error
        except Exception as e:
            logger.error(f"Error verifying HTTP: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_verification",
                "operation": "verify_http",
                "status": "error",
                "verification_id": verification_id,
                "error": str(e),
            })
            
            return False, f"Failed to verify HTTP: {str(e)}"
    
    async def verify_email(
        self,
        verification_id: str,
        confirmation_code: str,
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify domain ownership using email verification.
        
        Args:
            verification_id: Verification ID
            confirmation_code: Confirmation code from email
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get verification
            verification = self.verifications.get(verification_id)
            
            if not verification:
                return False, f"Verification {verification_id} not found"
            
            if verification.method != VerificationMethod.EMAIL:
                return False, f"Verification {verification_id} is not an email verification"
            
            # Update status
            verification.status = VerificationStatus.IN_PROGRESS
            
            # Check if confirmation code matches token
            if confirmation_code == verification.token:
                # Verification successful
                verification.status = VerificationStatus.VERIFIED
                
                # Log to MCP
                await get_mcp_client().send({
                    "type": "dns_verification",
                    "operation": "verify_email",
                    "status": "success",
                    "verification_id": verification_id,
                    "user_id": verification.user_id,
                    "domain": verification.domain,
                })
                
                return True, None
            else:
                return False, "Invalid confirmation code"
        except Exception as e:
            logger.error(f"Error verifying email: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_verification",
                "operation": "verify_email",
                "status": "error",
                "verification_id": verification_id,
                "error": str(e),
            })
            
            return False, f"Failed to verify email: {str(e)}"
    
    async def verify(
        self,
        verification_id: str,
        confirmation_code: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Verify domain ownership using the appropriate method.
        
        Args:
            verification_id: Verification ID
            confirmation_code: Confirmation code for email verification
            
        Returns:
            Tuple of (success, error_message)
        """
        try:
            # Get verification
            verification = self.verifications.get(verification_id)
            
            if not verification:
                return False, f"Verification {verification_id} not found"
            
            # Verify based on method
            if verification.method == VerificationMethod.DNS_TXT:
                return await self.verify_dns_txt(verification_id)
            elif verification.method == VerificationMethod.HTTP:
                return await self.verify_http(verification_id)
            elif verification.method == VerificationMethod.EMAIL:
                if not confirmation_code:
                    return False, "Confirmation code is required for email verification"
                
                return await self.verify_email(verification_id, confirmation_code)
            else:
                return False, f"Unsupported verification method: {verification.method}"
        except Exception as e:
            logger.error(f"Error verifying domain: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_verification",
                "operation": "verify",
                "status": "error",
                "verification_id": verification_id,
                "error": str(e),
            })
            
            return False, f"Failed to verify domain: {str(e)}"
    
    async def get_verification(
        self,
        verification_id: str,
    ) -> Optional[DomainVerification]:
        """
        Get a domain verification by ID.
        
        Args:
            verification_id: Verification ID
            
        Returns:
            Domain verification or None if not found
        """
        return self.verifications.get(verification_id)
    
    async def get_verifications_for_user(
        self,
        user_id: str,
    ) -> List[DomainVerification]:
        """
        Get all domain verifications for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of domain verifications
        """
        return [
            verification for verification in self.verifications.values()
            if verification.user_id == user_id
        ]
    
    async def get_verifications_for_domain(
        self,
        domain: str,
    ) -> List[DomainVerification]:
        """
        Get all domain verifications for a domain.
        
        Args:
            domain: Domain name
            
        Returns:
            List of domain verifications
        """
        return [
            verification for verification in self.verifications.values()
            if verification.domain == domain
        ]
    
    async def delete_verification(
        self,
        verification_id: str,
    ) -> bool:
        """
        Delete a domain verification.
        
        Args:
            verification_id: Verification ID
            
        Returns:
            Boolean indicating success or failure
        """
        if verification_id in self.verifications:
            del self.verifications[verification_id]
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "dns_verification",
                "operation": "delete",
                "verification_id": verification_id,
            })
            
            return True
        
        return False

# Singleton instance
_dns_verification_service = None

async def get_dns_verification_service() -> DNSVerificationService:
    """
    Get the DNS verification service instance.
    
    Returns:
        DNS verification service instance
    """
    global _dns_verification_service
    
    if _dns_verification_service is None:
        _dns_verification_service = DNSVerificationService()
    
    return _dns_verification_service
