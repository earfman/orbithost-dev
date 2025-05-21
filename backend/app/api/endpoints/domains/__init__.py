"""
Domain API endpoints for OrbitHost.
This is part of the private components that implement domain management features.
"""

from fastapi import APIRouter

from app.api.endpoints.domains import domains, marketplace

router = APIRouter()
router.include_router(domains.router, tags=["domains"])
router.include_router(marketplace.router, prefix="/marketplace", tags=["domains", "marketplace"])
