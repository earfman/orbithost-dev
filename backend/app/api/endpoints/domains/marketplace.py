"""
Domain marketplace API endpoints for OrbitHost.
This is part of the private components that implement domain management features.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body

from app.core.auth import get_current_user
from app.models.user import User
from app.services.domain_service.domain_service import DomainService

router = APIRouter()
domain_service = DomainService()


@router.get("/search", response_model=List[Dict[str, Any]])
async def search_domains(
    keyword: str = Query(...),
    tlds: List[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """
    Search for available domains based on a keyword.
    """
    try:
        results = await domain_service.search_domains(keyword, tlds)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Domain search error: {str(e)}")


@router.get("/check/{domain_name}", response_model=Dict[str, Any])
async def check_domain_availability(
    domain_name: str,
    current_user: User = Depends(get_current_user)
):
    """
    Check if a domain is available for registration.
    """
    try:
        result = await domain_service.check_domain_availability(domain_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Domain availability check error: {str(e)}")


@router.post("/register", response_model=Dict[str, Any])
async def register_domain(
    domain_name: str = Body(...),
    years: int = Body(1),
    contact_info: Dict[str, Any] = Body(None),
    current_user: User = Depends(get_current_user)
):
    """
    Register a domain for the current user.
    """
    try:
        result = await domain_service.register_domain(
            user=current_user,
            domain_name=domain_name,
            years=years,
            contact_info=contact_info
        )
        
        # In a real implementation, we would save the domain to a database
        
        return {
            "id": "dom_new",
            "name": domain_name,
            "status": "registered",
            "site_id": None,
            "created_at": "2025-05-16T00:00:00Z",
            "registration_details": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Domain registration error: {str(e)}")


@router.post("/transfer", response_model=Dict[str, Any])
async def transfer_domain(
    domain_name: str = Body(...),
    auth_code: str = Body(...),
    contact_info: Dict[str, Any] = Body(None),
    current_user: User = Depends(get_current_user)
):
    """
    Transfer a domain to OrbitHost.
    """
    try:
        result = await domain_service.transfer_domain(
            domain_name=domain_name,
            auth_code=auth_code,
            contact_info=contact_info
        )
        
        # In a real implementation, we would save the domain to a database
        
        return {
            "id": "dom_new",
            "name": domain_name,
            "status": "pending_transfer",
            "site_id": None,
            "created_at": "2025-05-16T00:00:00Z",
            "transfer_details": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Domain transfer error: {str(e)}")


@router.post("/renew", response_model=Dict[str, Any])
async def renew_domain(
    domain_name: str = Body(...),
    years: int = Body(1),
    current_user: User = Depends(get_current_user)
):
    """
    Renew a domain registration.
    """
    # In a real implementation, we would check if the domain belongs to the current user
    
    try:
        result = await domain_service.renew_domain(
            domain_name=domain_name,
            years=years
        )
        
        return {
            "name": domain_name,
            "status": "renewed",
            "renewal_details": result
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Domain renewal error: {str(e)}")
