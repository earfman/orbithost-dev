"""
Credential service for OrbitHost.
Provides secure storage and retrieval of API credentials.
"""

import os
import logging
import json
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

class CredentialService:
    """
    Service for securely storing and retrieving API credentials.
    Uses encryption to protect sensitive information.
    """
    
    def __init__(self):
        """Initialize the credential service."""
        self.encryption_key = self._derive_key(settings.SECRET_KEY)
        self.cipher = Fernet(self.encryption_key)
        self.credentials_dir = os.path.join(settings.DATA_DIR, "credentials")
        
        # Ensure credentials directory exists
        os.makedirs(self.credentials_dir, exist_ok=True)
    
    async def store_credentials(
        self, 
        user_id: str, 
        provider: str, 
        credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store API credentials for a user and provider.
        
        Args:
            user_id: The ID of the user
            provider: The provider name (e.g., 'godaddy', 'namecheap')
            credentials: The credentials to store
            
        Returns:
            Dictionary with storage status
        """
        try:
            # Add metadata
            credentials_with_metadata = {
                "provider": provider,
                "created_at": datetime.now().isoformat(),
                "last_used": None,
                "credentials": credentials
            }
            
            # Encrypt the credentials
            encrypted_data = self._encrypt(json.dumps(credentials_with_metadata))
            
            # Save to file
            file_path = self._get_credentials_path(user_id, provider)
            with open(file_path, "wb") as f:
                f.write(encrypted_data)
                
            logger.info(f"Stored credentials for user {user_id} and provider {provider}")
            
            return {
                "status": "success",
                "provider": provider,
                "user_id": user_id,
                "created_at": credentials_with_metadata["created_at"]
            }
            
        except Exception as e:
            logger.error(f"Error storing credentials for user {user_id} and provider {provider}: {str(e)}")
            raise
    
    async def get_credentials(
        self, 
        user_id: str, 
        provider: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get API credentials for a user and provider.
        
        Args:
            user_id: The ID of the user
            provider: The provider name (e.g., 'godaddy', 'namecheap')
            
        Returns:
            Dictionary with credentials if found, None otherwise
        """
        try:
            file_path = self._get_credentials_path(user_id, provider)
            
            # Check if credentials exist
            if not os.path.exists(file_path):
                logger.warning(f"No credentials found for user {user_id} and provider {provider}")
                return None
                
            # Read and decrypt the credentials
            with open(file_path, "rb") as f:
                encrypted_data = f.read()
                
            decrypted_data = self._decrypt(encrypted_data)
            credentials_with_metadata = json.loads(decrypted_data)
            
            # Update last used timestamp
            credentials_with_metadata["last_used"] = datetime.now().isoformat()
            
            # Save updated metadata
            encrypted_data = self._encrypt(json.dumps(credentials_with_metadata))
            with open(file_path, "wb") as f:
                f.write(encrypted_data)
                
            logger.info(f"Retrieved credentials for user {user_id} and provider {provider}")
            
            return credentials_with_metadata["credentials"]
            
        except Exception as e:
            logger.error(f"Error getting credentials for user {user_id} and provider {provider}: {str(e)}")
            return None
    
    async def delete_credentials(
        self, 
        user_id: str, 
        provider: str
    ) -> Dict[str, Any]:
        """
        Delete API credentials for a user and provider.
        
        Args:
            user_id: The ID of the user
            provider: The provider name (e.g., 'godaddy', 'namecheap')
            
        Returns:
            Dictionary with deletion status
        """
        try:
            file_path = self._get_credentials_path(user_id, provider)
            
            # Check if credentials exist
            if not os.path.exists(file_path):
                logger.warning(f"No credentials found for user {user_id} and provider {provider}")
                return {
                    "status": "not_found",
                    "provider": provider,
                    "user_id": user_id
                }
                
            # Delete the credentials file
            os.remove(file_path)
            
            logger.info(f"Deleted credentials for user {user_id} and provider {provider}")
            
            return {
                "status": "success",
                "provider": provider,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Error deleting credentials for user {user_id} and provider {provider}: {str(e)}")
            raise
    
    async def list_user_credentials(
        self, 
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        List all API credentials for a user.
        
        Args:
            user_id: The ID of the user
            
        Returns:
            List of credential metadata
        """
        try:
            user_dir = os.path.join(self.credentials_dir, user_id)
            
            # Check if user directory exists
            if not os.path.exists(user_dir):
                os.makedirs(user_dir, exist_ok=True)
                return []
                
            # Get all credential files
            credential_files = [f for f in os.listdir(user_dir) if f.endswith(".cred")]
            
            results = []
            for file_name in credential_files:
                provider = file_name.replace(".cred", "")
                file_path = os.path.join(user_dir, file_name)
                
                # Read and decrypt the credentials
                with open(file_path, "rb") as f:
                    encrypted_data = f.read()
                    
                decrypted_data = self._decrypt(encrypted_data)
                credentials_with_metadata = json.loads(decrypted_data)
                
                # Add metadata to results (without the actual credentials)
                metadata = {
                    "provider": provider,
                    "created_at": credentials_with_metadata.get("created_at"),
                    "last_used": credentials_with_metadata.get("last_used")
                }
                
                results.append(metadata)
                
            logger.info(f"Listed {len(results)} credentials for user {user_id}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error listing credentials for user {user_id}: {str(e)}")
            return []
    
    async def validate_credentials(
        self, 
        user_id: str, 
        provider: str
    ) -> Dict[str, Any]:
        """
        Validate API credentials for a user and provider.
        
        Args:
            user_id: The ID of the user
            provider: The provider name (e.g., 'godaddy', 'namecheap')
            
        Returns:
            Dictionary with validation status
        """
        try:
            # Get the credentials
            credentials = await self.get_credentials(user_id, provider)
            
            if not credentials:
                return {
                    "status": "not_found",
                    "valid": False,
                    "provider": provider,
                    "user_id": user_id
                }
                
            # TODO: Implement actual validation with the provider API
            # For now, we'll just check if the required fields are present
            
            required_fields = {
                "godaddy": ["api_key", "api_secret"],
                "namecheap": ["api_key", "api_user", "username"],
                "googledomains": ["api_key", "api_secret"],
                "cloudflare": ["api_key", "email"],
                "route53": ["access_key", "secret_key"]
            }
            
            if provider not in required_fields:
                return {
                    "status": "unsupported_provider",
                    "valid": False,
                    "provider": provider,
                    "user_id": user_id
                }
                
            # Check if all required fields are present
            missing_fields = []
            for field in required_fields[provider]:
                if field not in credentials or not credentials[field]:
                    missing_fields.append(field)
                    
            if missing_fields:
                return {
                    "status": "missing_fields",
                    "valid": False,
                    "provider": provider,
                    "user_id": user_id,
                    "missing_fields": missing_fields
                }
                
            # All required fields are present
            return {
                "status": "success",
                "valid": True,
                "provider": provider,
                "user_id": user_id
            }
            
        except Exception as e:
            logger.error(f"Error validating credentials for user {user_id} and provider {provider}: {str(e)}")
            return {
                "status": "error",
                "valid": False,
                "provider": provider,
                "user_id": user_id,
                "error": str(e)
            }
    
    def _get_credentials_path(self, user_id: str, provider: str) -> str:
        """Get the file path for storing credentials."""
        user_dir = os.path.join(self.credentials_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        return os.path.join(user_dir, f"{provider}.cred")
    
    def _derive_key(self, secret_key: str) -> bytes:
        """Derive an encryption key from the secret key."""
        salt = b"orbithost_credentials"  # A fixed salt is OK since we have a strong secret key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
        return key
    
    def _encrypt(self, data: str) -> bytes:
        """Encrypt data."""
        return self.cipher.encrypt(data.encode())
    
    def _decrypt(self, encrypted_data: bytes) -> str:
        """Decrypt data."""
        return self.cipher.decrypt(encrypted_data).decode()
