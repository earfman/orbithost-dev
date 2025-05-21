"""
Secrets management utility for OrbitHost.

This module provides utilities for securely managing API keys and other sensitive information.
It supports loading secrets from environment variables, files, or secure storage services.
"""

import os
import json
import logging
import base64
from pathlib import Path
from typing import Dict, Optional, Any, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configure logging
logger = logging.getLogger(__name__)

class SecretsManager:
    """Secrets manager for securely handling API keys and other sensitive information."""
    
    def __init__(self, secrets_file: Optional[str] = None, encryption_key: Optional[str] = None):
        """
        Initialize the secrets manager.
        
        Args:
            secrets_file: Path to the secrets file
            encryption_key: Key for encrypting/decrypting secrets
        """
        self.secrets_file = secrets_file or os.getenv("SECRETS_FILE")
        self.encryption_key = encryption_key or os.getenv("ENCRYPTION_KEY")
        self.secrets: Dict[str, Any] = {}
        
        # Load secrets if file exists
        if self.secrets_file and Path(self.secrets_file).exists():
            self._load_secrets()
    
    def _get_fernet(self) -> Optional[Fernet]:
        """
        Get a Fernet instance for encryption/decryption.
        
        Returns:
            Fernet instance if encryption key is available, None otherwise
        """
        if not self.encryption_key:
            return None
        
        # Derive a key from the encryption key
        salt = b'orbithost_salt'  # In production, this should be stored securely
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key.encode()))
        return Fernet(key)
    
    def _load_secrets(self) -> None:
        """Load secrets from the secrets file."""
        try:
            with open(self.secrets_file, "r") as f:
                content = f.read()
                
                # Decrypt if encryption key is available
                fernet = self._get_fernet()
                if fernet and content.startswith("ENCRYPTED:"):
                    encrypted_data = content[10:].encode()  # Remove "ENCRYPTED:" prefix
                    decrypted_data = fernet.decrypt(encrypted_data).decode()
                    self.secrets = json.loads(decrypted_data)
                else:
                    self.secrets = json.loads(content)
                
            logger.info(f"Loaded secrets from {self.secrets_file}")
        except Exception as e:
            logger.error(f"Error loading secrets: {e}")
    
    def _save_secrets(self) -> None:
        """Save secrets to the secrets file."""
        if not self.secrets_file:
            logger.warning("No secrets file specified, cannot save secrets")
            return
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(os.path.abspath(self.secrets_file)), exist_ok=True)
            
            # Convert secrets to JSON
            json_data = json.dumps(self.secrets, indent=2)
            
            # Encrypt if encryption key is available
            fernet = self._get_fernet()
            if fernet:
                encrypted_data = fernet.encrypt(json_data.encode())
                content = f"ENCRYPTED:{encrypted_data.decode()}"
            else:
                content = json_data
            
            # Write to file
            with open(self.secrets_file, "w") as f:
                f.write(content)
                
            logger.info(f"Saved secrets to {self.secrets_file}")
        except Exception as e:
            logger.error(f"Error saving secrets: {e}")
    
    def get_secret(self, key: str, default: Any = None) -> Any:
        """
        Get a secret by key.
        
        Args:
            key: Secret key
            default: Default value if key is not found
            
        Returns:
            Secret value if found, default otherwise
        """
        # First check environment variables
        env_value = os.getenv(key)
        if env_value is not None:
            return env_value
        
        # Then check loaded secrets
        return self.secrets.get(key, default)
    
    def set_secret(self, key: str, value: Any, save: bool = True) -> None:
        """
        Set a secret.
        
        Args:
            key: Secret key
            value: Secret value
            save: Whether to save the secrets file
        """
        self.secrets[key] = value
        if save:
            self._save_secrets()
    
    def delete_secret(self, key: str, save: bool = True) -> None:
        """
        Delete a secret.
        
        Args:
            key: Secret key
            save: Whether to save the secrets file
        """
        if key in self.secrets:
            del self.secrets[key]
            if save:
                self._save_secrets()

# Singleton instance
_secrets_manager: Optional[SecretsManager] = None

def get_secrets_manager() -> SecretsManager:
    """
    Get the SecretsManager instance.
    
    Returns:
        SecretsManager instance
    """
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager

def get_secret(key: str, default: Any = None) -> Any:
    """
    Get a secret by key.
    
    Args:
        key: Secret key
        default: Default value if key is not found
        
    Returns:
        Secret value if found, default otherwise
    """
    return get_secrets_manager().get_secret(key, default)

def set_secret(key: str, value: Any, save: bool = True) -> None:
    """
    Set a secret.
    
    Args:
        key: Secret key
        value: Secret value
        save: Whether to save the secrets file
    """
    get_secrets_manager().set_secret(key, value, save)

def delete_secret(key: str, save: bool = True) -> None:
    """
    Delete a secret.
    
    Args:
        key: Secret key
        save: Whether to save the secrets file
    """
    get_secrets_manager().delete_secret(key, save)
