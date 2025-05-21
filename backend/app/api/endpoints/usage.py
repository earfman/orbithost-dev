"""
Usage tracking API endpoints for OrbitHost.
This is part of the private components that implement monetization features.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import get_current_user
from app.models.user import User
from app.services.usage_service import UsageService

router = APIRouter()
usage_service = UsageService()


@router.get("/summary", response_model=Dict[str, Any])
async def get_usage_summary(
    period: str = Query("month", description="Period for summary: 'day', 'week', 'month', 'year'"),
    current_user: User = Depends(get_current_user)
):
    """
    Get usage summary for the current user.
    """
    try:
        # Calculate date range based on period
        now = datetime.now()
        
        if period == "day":
            start_date = datetime(now.year, now.month, now.day)
            end_date = now
        elif period == "week":
            # Start from the beginning of the week (Monday)
            start_date = now - timedelta(days=now.weekday())
            start_date = datetime(start_date.year, start_date.month, start_date.day)
            end_date = now
        elif period == "month":
            start_date = datetime(now.year, now.month, 1)
            end_date = now
        elif period == "year":
            start_date = datetime(now.year, 1, 1)
            end_date = now
        else:
            raise HTTPException(status_code=400, detail="Invalid period")
        
        # Get usage summary
        summary = await usage_service.get_usage_summary(
            user_id=current_user.id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Get usage limits
        limits = await usage_service.get_usage_limits(current_user)
        
        # Check if any limits are exceeded
        exceeded = await usage_service.check_usage_exceeded(current_user)
        
        # Combine results
        return {
            "summary": summary,
            "limits": limits,
            "exceeded": exceeded
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Usage summary error: {str(e)}")


@router.get("/limits", response_model=Dict[str, Any])
async def get_usage_limits(current_user: User = Depends(get_current_user)):
    """
    Get usage limits for the current user.
    """
    try:
        limits = await usage_service.get_usage_limits(current_user)
        return limits
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Usage limits error: {str(e)}")


@router.post("/track/deployment", response_model=Dict[str, Any])
async def track_deployment(
    deployment_id: str,
    build_time_seconds: int,
    artifact_size_bytes: int,
    current_user: User = Depends(get_current_user)
):
    """
    Track a deployment for usage metrics.
    """
    try:
        result = await usage_service.track_deployment(
            user_id=current_user.id,
            deployment_id=deployment_id,
            build_time_seconds=build_time_seconds,
            artifact_size_bytes=artifact_size_bytes
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deployment tracking error: {str(e)}")


@router.post("/track/request", response_model=Dict[str, Any])
async def track_request(
    site_id: str,
    bandwidth_bytes: int,
    status_code: int,
    country: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Track a request for usage metrics.
    """
    try:
        result = await usage_service.track_request(
            user_id=current_user.id,
            site_id=site_id,
            bandwidth_bytes=bandwidth_bytes,
            status_code=status_code,
            country=country
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Request tracking error: {str(e)}")
