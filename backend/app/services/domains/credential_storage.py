"""
Secure API credential storage for domain registrars and DNS providers.

This module provides functionality for securely storing, retrieving,
and managing API credentials for domain registrars and DNS providers.
"""
import base64
import json
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

class CredentialType(str, Enum):
    """Types of API credentials."""
    API_KEY = "api_key"
    API_SECRET = "api_secret"
    OAUTH_TOKEN = "oauth_token"
    USERNAME_PASSWORD = "username_password"
    OTHER = "other"

class ProviderType(str, Enum):
    """Types of service providers."""
    DOMAIN_REGISTRAR = "domain_registrar"
    DNS_PROVIDER = "dns_provider"

class Provider(str, Enum):
    """Supported service providers."""
    # Domain Registrars
    GODADDY = "godaddy"
    NAMECHEAP = "namecheap"
    GOOGLE_DOMAINS = "google_domains"
    
    # DNS Providers
    CLOUDFLARE = "cloudflare"
    AWS_ROUTE53 = "aws_route53"
    CLOUDNS = "cloudns"

class APICredential:
    """Model for API credentials."""
    
    def __init__(
        self,
        id: str,
        user_id: str,
        provider: Provider,
        provider_type: ProviderType,
        credential_type: CredentialType,
        name: str,
        credentials: Dict[str, str],
        encrypted: bool = False,
        created_at: datetime = None,
        updated_at: datetime = None,
        last_used_at: Optional[datetime] = None,
        verified: bool = False,
    ):
        """
        Initialize an API credential.
        
        Args:
            id: Credential ID
            user_id: ID of the user who owns the credential
            provider: Service provider
            provider_type: Type of service provider
            credential_type: Type of credential
            name: Credential name
            credentials: Dictionary of credential key-value pairs
            encrypted: Whether the credentials are encrypted
            created_at: Creation timestamp
            updated_at: Last update timestamp
            last_used_at: Last used timestamp
            verified: Whether the credential has been verified
        """
        self.id = id
        self.user_id = user_id
        self.provider = provider
        self.provider_type = provider_type
        self.credential_type = credential_type
        self.name = name
        self.credentials = credentials
        self.encrypted = encrypted
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.last_used_at = last_used_at
        self.verified = verified
    
    def to_dict(self, include_credentials: bool = False) -> Dict[str, Any]:
        """
        Convert to dictionary.
        
        Args:
            include_credentials: Whether to include the credentials
            
        Returns:
            Dictionary representation
        """
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "provider": self.provider.value,
            "provider_type": self.provider_type.value,
            "credential_type": self.credential_type.value,
            "name": self.name,
            "encrypted": self.encrypted,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "verified": self.verified,
        }
        
        if include_credentials:
            result["credentials"] = self.credentials
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "APICredential":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            user_id=data["user_id"],
            provider=Provider(data["provider"]),
            provider_type=ProviderType(data["provider_type"]),
            credential_type=CredentialType(data["credential_type"]),
            name=data["name"],
            credentials=data.get("credentials", {}),
            encrypted=data.get("encrypted", False),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else None,
            last_used_at=datetime.fromisoformat(data["last_used_at"]) if "last_used_at" in data else None,
            verified=data.get("verified", False),
        )

class CredentialStorage:
    """
    Service for securely storing and managing API credentials.
    
    This service provides functionality for storing, retrieving, updating,
    and deleting API credentials for domain registrars and DNS providers.
    """
    
    def __init__(self, encryption_key: Optional[str] = None):
        """
        Initialize the credential storage service.
        
        Args:
            encryption_key: Key for encrypting credentials
        """
        # In a real implementation, credentials would be stored in a secure database
        # For now, we'll use an in-memory dictionary
        self.credentials: Dict[str, APICredential] = {}
        
        # Set up encryption
        self.encryption_key = encryption_key or os.environ.get("CREDENTIAL_ENCRYPTION_KEY")
        self.fernet = None
        
        if self.encryption_key:
            # Derive a key from the encryption key
            salt = b"orbithost_credential_storage"  # In production, this would be a secure random value
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key.encode()))
            self.fernet = Fernet(key)
        
        logger.info("Initialized credential storage service")
    
    def _encrypt_credentials(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """
        Encrypt credentials.
        
        Args:
            credentials: Dictionary of credential key-value pairs
            
        Returns:
            Encrypted credentials
        """
        if not self.fernet:
            logger.warning("Encryption key not set, credentials will not be encrypted")
            return credentials
        
        encrypted_credentials = {}
        
        for key, value in credentials.items():
            encrypted_value = self.fernet.encrypt(value.encode()).decode()
            encrypted_credentials[key] = encrypted_value
        
        return encrypted_credentials
    
    def _decrypt_credentials(self, credentials: Dict[str, str]) -> Dict[str, str]:
        """
        Decrypt credentials.
        
        Args:
            credentials: Dictionary of encrypted credential key-value pairs
            
        Returns:
            Decrypted credentials
        """
        if not self.fernet:
            logger.warning("Encryption key not set, credentials cannot be decrypted")
            return credentials
        
        decrypted_credentials = {}
        
        for key, value in credentials.items():
            try:
                decrypted_value = self.fernet.decrypt(value.encode()).decode()
                decrypted_credentials[key] = decrypted_value
            except Exception as e:
                logger.error(f"Error decrypting credential {key}: {str(e)}")
                decrypted_credentials[key] = value  # Use encrypted value as fallback
        
        return decrypted_credentials
    
    async def store_credential(self, credential: APICredential) -> APICredential:
        """
        Store an API credential.
        
        Args:
            credential: API credential to store
            
        Returns:
            Stored API credential
        """
        # Encrypt credentials if not already encrypted
        if not credential.encrypted and self.fernet:
            credential.credentials = self._encrypt_credentials(credential.credentials)
            credential.encrypted = True
        
        # Store credential
        self.credentials[credential.id] = credential
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "credential_storage",
            "operation": "store",
            "credential_id": credential.id,
            "user_id": credential.user_id,
            "provider": credential.provider.value,
            "provider_type": credential.provider_type.value,
        })
        
        logger.info(f"Stored credential {credential.id} for {credential.provider.value}")
        
        return credential
    
    async def get_credential(
        self,
        credential_id: str,
        decrypt: bool = False,
    ) -> Optional[APICredential]:
        """
        Get an API credential by ID.
        
        Args:
            credential_id: ID of the credential to get
            decrypt: Whether to decrypt the credentials
            
        Returns:
            API credential or None if not found
        """
        credential = self.credentials.get(credential_id)
        
        if not credential:
            return None
        
        # Decrypt credentials if requested
        if decrypt and credential.encrypted and self.fernet:
            # Create a copy of the credential with decrypted credentials
            decrypted_credential = APICredential(
                id=credential.id,
                user_id=credential.user_id,
                provider=credential.provider,
                provider_type=credential.provider_type,
                credential_type=credential.credential_type,
                name=credential.name,
                credentials=self._decrypt_credentials(credential.credentials),
                encrypted=False,
                created_at=credential.created_at,
                updated_at=credential.updated_at,
                last_used_at=credential.last_used_at,
                verified=credential.verified,
            )
            
            return decrypted_credential
        
        return credential
    
    async def get_credentials_for_user(
        self,
        user_id: str,
        provider: Optional[Provider] = None,
        provider_type: Optional[ProviderType] = None,
        decrypt: bool = False,
    ) -> List[APICredential]:
        """
        Get API credentials for a user.
        
        Args:
            user_id: ID of the user
            provider: Filter by provider
            provider_type: Filter by provider type
            decrypt: Whether to decrypt the credentials
            
        Returns:
            List of API credentials
        """
        credentials = []
        
        for credential in self.credentials.values():
            if credential.user_id != user_id:
                continue
            
            if provider and credential.provider != provider:
                continue
            
            if provider_type and credential.provider_type != provider_type:
                continue
            
            if decrypt and credential.encrypted and self.fernet:
                # Create a copy of the credential with decrypted credentials
                decrypted_credential = APICredential(
                    id=credential.id,
                    user_id=credential.user_id,
                    provider=credential.provider,
                    provider_type=credential.provider_type,
                    credential_type=credential.credential_type,
                    name=credential.name,
                    credentials=self._decrypt_credentials(credential.credentials),
                    encrypted=False,
                    created_at=credential.created_at,
                    updated_at=credential.updated_at,
                    last_used_at=credential.last_used_at,
                    verified=credential.verified,
                )
                
                credentials.append(decrypted_credential)
            else:
                credentials.append(credential)
        
        return credentials
    
    async def update_credential(
        self,
        credential_id: str,
        updates: Dict[str, Any],
        encrypt_credentials: bool = True,
    ) -> Optional[APICredential]:
        """
        Update an API credential.
        
        Args:
            credential_id: ID of the credential to update
            updates: Dictionary of updates
            encrypt_credentials: Whether to encrypt the credentials
            
        Returns:
            Updated API credential or None if not found
        """
        credential = self.credentials.get(credential_id)
        
        if not credential:
            return None
        
        # Update fields
        for key, value in updates.items():
            if key == "credentials":
                if encrypt_credentials and self.fernet:
                    credential.credentials = self._encrypt_credentials(value)
                    credential.encrypted = True
                else:
                    credential.credentials = value
                    credential.encrypted = False
            elif hasattr(credential, key):
                setattr(credential, key, value)
        
        # Update timestamp
        credential.updated_at = datetime.utcnow()
        
        # Store updated credential
        self.credentials[credential_id] = credential
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "credential_storage",
            "operation": "update",
            "credential_id": credential_id,
            "user_id": credential.user_id,
            "provider": credential.provider.value,
            "provider_type": credential.provider_type.value,
        })
        
        logger.info(f"Updated credential {credential_id}")
        
        return credential
    
    async def delete_credential(self, credential_id: str) -> bool:
        """
        Delete an API credential.
        
        Args:
            credential_id: ID of the credential to delete
            
        Returns:
            Boolean indicating success or failure
        """
        if credential_id not in self.credentials:
            return False
        
        # Get credential for logging
        credential = self.credentials[credential_id]
        
        # Delete credential
        del self.credentials[credential_id]
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "credential_storage",
            "operation": "delete",
            "credential_id": credential_id,
            "user_id": credential.user_id,
            "provider": credential.provider.value,
            "provider_type": credential.provider_type.value,
        })
        
        logger.info(f"Deleted credential {credential_id}")
        
        return True
    
    async def verify_credential(
        self,
        credential_id: str,
        verified: bool = True,
    ) -> Optional[APICredential]:
        """
        Mark an API credential as verified.
        
        Args:
            credential_id: ID of the credential to verify
            verified: Whether the credential is verified
            
        Returns:
            Updated API credential or None if not found
        """
        credential = self.credentials.get(credential_id)
        
        if not credential:
            return None
        
        # Update verification status
        credential.verified = verified
        credential.updated_at = datetime.utcnow()
        
        # Store updated credential
        self.credentials[credential_id] = credential
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "credential_storage",
            "operation": "verify",
            "credential_id": credential_id,
            "user_id": credential.user_id,
            "provider": credential.provider.value,
            "provider_type": credential.provider_type.value,
            "verified": verified,
        })
        
        logger.info(f"{'Verified' if verified else 'Unverified'} credential {credential_id}")
        
        return credential
    
    async def update_last_used(self, credential_id: str) -> Optional[APICredential]:
        """
        Update the last used timestamp of an API credential.
        
        Args:
            credential_id: ID of the credential to update
            
        Returns:
            Updated API credential or None if not found
        """
        credential = self.credentials.get(credential_id)
        
        if not credential:
            return None
        
        # Update last used timestamp
        credential.last_used_at = datetime.utcnow()
        
        # Store updated credential
        self.credentials[credential_id] = credential
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "credential_storage",
            "operation": "update_last_used",
            "credential_id": credential_id,
            "user_id": credential.user_id,
            "provider": credential.provider.value,
            "provider_type": credential.provider_type.value,
        })
        
        logger.info(f"Updated last used timestamp for credential {credential_id}")
        
        return credential


# Global credential storage instance
_credential_storage = None

async def get_credential_storage() -> CredentialStorage:
    """
    Get the credential storage instance.
    
    Returns:
        Credential storage instance
    """
    global _credential_storage
    
    if _credential_storage is None:
        encryption_key = os.environ.get("CREDENTIAL_ENCRYPTION_KEY")
        _credential_storage = CredentialStorage(encryption_key=encryption_key)
    
    return _credential_storage
