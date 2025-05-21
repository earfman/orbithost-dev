"""
Main API router for the OrbitHost backend.

This module sets up the main API router and includes all endpoint routers.
"""
import logging
from fastapi import APIRouter

# Import all endpoint modules - wrapped in try/except to handle potential import errors
try:
    from app.api.endpoints import (
        observability, domain_credentials, dns, dns_config, domain_transfer, 
        dns_verification, manual_dns, users_db, context_api
    )
    logger = logging.getLogger(__name__)
    logger.info("Successfully imported all API endpoint modules")
    
    # Flag for modules that were successfully imported
    has_users_db = True
    has_context_api = True
except ImportError as e:
    from app.api.endpoints import observability, domain_credentials, dns, dns_config, domain_transfer, dns_verification, manual_dns
    logger = logging.getLogger(__name__)
    logger.warning(f"Could not import all API endpoint modules: {e}")
    
    # Check which modules were imported successfully
    try:
        from app.api.endpoints import users_db
        has_users_db = True
    except ImportError:
        has_users_db = False
        logger.warning("Could not import users_db module")
    
    try:
        from app.api.endpoints import context_api
        has_context_api = True
    except ImportError:
        has_context_api = False
        logger.warning("Could not import context_api module")

# Create main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(observability.router)
api_router.include_router(domain_credentials.router)
api_router.include_router(dns.router)
api_router.include_router(dns_config.router)
api_router.include_router(domain_transfer.router)
api_router.include_router(dns_verification.router)
api_router.include_router(manual_dns.router)

# Include users_db and context_api routers if available
if 'has_users_db' in locals() and has_users_db:
    api_router.include_router(users_db.router)
    logger.info("Included users_db router")

if 'has_context_api' in locals() and has_context_api:
    api_router.include_router(context_api.router)
    logger.info("Included context_api router")

logger.info("API router initialized with all endpoints")
