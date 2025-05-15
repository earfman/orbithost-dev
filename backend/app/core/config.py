import os
from typing import List
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/v1"
    PROJECT_NAME: str = "OrbitHost"
    
    # CORS
    CORS_ORIGINS: List[AnyHttpUrl] = []
    
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Clerk Authentication
    CLERK_API_KEY: str
    CLERK_JWT_PUBLIC_KEY: str
    
    # GitHub Webhook Secret
    GITHUB_WEBHOOK_SECRET: str
    
    # Fly.io API
    FLY_API_TOKEN: str
    
    # Stripe Configuration
    STRIPE_API_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    
    # Deployment Configuration
    DEPLOYMENT_TIMEOUT: int = 600  # seconds
    
    # Monitoring Configuration
    ENABLE_METRICS: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
