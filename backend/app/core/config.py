import os
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from pydantic import AnyHttpUrl, validator, Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file if it exists
load_dotenv()

# Check for secrets file
SECRETS_FILE = os.getenv("SECRETS_FILE", "")
if SECRETS_FILE and Path(SECRETS_FILE).exists():
    try:
        with open(SECRETS_FILE, "r") as f:
            secrets_data = json.load(f)
            for key, value in secrets_data.items():
                if key not in os.environ:
                    os.environ[key] = value
        logger.info(f"Loaded secrets from {SECRETS_FILE}")
    except Exception as e:
        logger.error(f"Error loading secrets file: {e}")

class Settings(BaseSettings):
    """Application settings.
    
    This class uses Pydantic's BaseSettings which loads variables from environment
    variables or .env files. It provides validation and type conversion.
    """
    # API Configuration
    API_V1_STR: str = "/v1"
    PROJECT_NAME: str = "OrbitHost"
    DEBUG: bool = False
    
    # CORS
    CORS_ORIGINS: List[str] = ["*"]
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)
    
    # Supabase Configuration
    SUPABASE_URL: Optional[str] = None
    SUPABASE_KEY: Optional[str] = None
    
    # Clerk Authentication
    CLERK_API_KEY: Optional[str] = None
    CLERK_JWT_PUBLIC_KEY: Optional[str] = None
    
    # GitHub Webhook Secret
    GITHUB_WEBHOOK_SECRET: Optional[str] = None
    
    # Fly.io API
    FLY_API_TOKEN: Optional[str] = None
    
    # Stripe Configuration
    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # Validate required settings based on environment
    @validator("SUPABASE_URL", "SUPABASE_KEY", pre=True)
    def validate_supabase_settings(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        # In production, these settings are required
        if os.getenv("ENVIRONMENT", "").lower() == "production" and not v:
            logger.warning("Missing required Supabase configuration in production environment")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    # Deployment Configuration
    DEPLOYMENT_TIMEOUT: int = 600  # seconds
    
    # Monitoring Configuration
    ENABLE_METRICS: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
