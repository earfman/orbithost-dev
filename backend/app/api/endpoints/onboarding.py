"""
User onboarding API endpoints for OrbitHost.
This is part of the private components that implement user management.
"""

from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Path, Query

from app.core.auth import get_current_user
from app.models.user import User
from app.services.onboarding_service import OnboardingService

router = APIRouter()
onboarding_service = OnboardingService()


@router.get("/status", response_model=Dict[str, Any])
async def get_onboarding_status(current_user: User = Depends(get_current_user)):
    """
    Get onboarding status for the current user.
    """
    try:
        status = await onboarding_service.get_onboarding_status(current_user.id)
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Onboarding status error: {str(e)}")


@router.put("/steps/{step_id}", response_model=Dict[str, Any])
async def update_step_status(
    completed: bool,
    step_id: str = Path(...),
    current_user: User = Depends(get_current_user)
):
    """
    Update the status of an onboarding step.
    """
    try:
        updated_status = await onboarding_service.update_step_status(
            user_id=current_user.id,
            step_id=step_id,
            completed=completed
        )
        return updated_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Step update error: {str(e)}")


@router.get("/recommendations", response_model=List[Dict[str, Any]])
async def get_recommendations(current_user: User = Depends(get_current_user)):
    """
    Get personalized recommendations for the current user.
    """
    try:
        recommendations = await onboarding_service.get_personalized_recommendations(current_user.id)
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendations error: {str(e)}")


@router.post("/skip", response_model=Dict[str, Any])
async def skip_onboarding(current_user: User = Depends(get_current_user)):
    """
    Skip the onboarding process for the current user.
    """
    try:
        updated_status = await onboarding_service.skip_onboarding(current_user.id)
        return updated_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Skip onboarding error: {str(e)}")


@router.post("/reset", response_model=Dict[str, Any])
async def reset_onboarding(current_user: User = Depends(get_current_user)):
    """
    Reset the onboarding process for the current user.
    """
    try:
        updated_status = await onboarding_service.reset_onboarding(current_user.id)
        return updated_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset onboarding error: {str(e)}")
