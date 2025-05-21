"""
API endpoints for AI feedback on deployments and errors.

This module provides API endpoints for accessing AI-powered feedback on deployments,
error analysis, performance recommendations, and deployment summaries.
"""
import logging
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body

from app.services.orbitbridge.ai_feedback import get_ai_feedback_service, AIFeedbackService
from app.services.orbitbridge.bridge import get_orbit_bridge, OrbitBridge
from app.services.orbitbridge.context import OrbitContext, ContextType
from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

# Create API router for AI feedback
router = APIRouter(prefix="/api/ai-feedback", tags=["ai-feedback"])

@router.post("/deployments/{deployment_id}/analyze")
async def analyze_deployment(
    deployment_id: str = Path(..., description="ID of the deployment to analyze"),
    include_related: bool = Query(True, description="Whether to include related contexts in the analysis"),
):
    """
    Analyze a deployment and provide AI-powered feedback.
    
    Args:
        deployment_id: ID of the deployment to analyze
        include_related: Whether to include related contexts in the analysis
        
    Returns:
        AI-powered feedback on the deployment
    """
    try:
        # Get OrbitBridge instance
        bridge = await get_orbit_bridge()
        
        # Get deployment context
        deployment_context = await bridge.get_context(deployment_id)
        
        if not deployment_context or deployment_context.type != ContextType.DEPLOYMENT:
            raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")
        
        # Get related contexts if requested
        related_contexts = []
        if include_related:
            # In a real implementation, this would get related contexts from the database
            # For now, we'll just use the related_contexts field in the deployment context
            for context_id in deployment_context.related_contexts:
                context = await bridge.get_context(context_id)
                if context:
                    related_contexts.append(context)
        
        # Get AI feedback service
        ai_feedback_service = await get_ai_feedback_service()
        
        # Analyze deployment
        feedback = await ai_feedback_service.analyze_deployment(
            deployment_context=deployment_context,
            related_contexts=related_contexts,
        )
        
        return feedback
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing deployment {deployment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/errors/{error_id}/analyze")
async def analyze_error(
    error_id: str = Path(..., description="ID of the error to analyze"),
    code: Optional[str] = Body(None, description="Code associated with the error"),
    language: Optional[str] = Body(None, description="Programming language of the code"),
):
    """
    Analyze an error and provide AI-powered feedback.
    
    Args:
        error_id: ID of the error to analyze
        code: Code associated with the error
        language: Programming language of the code
        
    Returns:
        AI-powered analysis of the error
    """
    try:
        # Get OrbitBridge instance
        bridge = await get_orbit_bridge()
        
        # Get error context
        error_context = await bridge.get_context(error_id)
        
        if not error_context or error_context.type != ContextType.ERROR:
            raise HTTPException(status_code=404, detail=f"Error {error_id} not found")
        
        # Get AI feedback service
        ai_feedback_service = await get_ai_feedback_service()
        
        # Analyze error
        analysis = await ai_feedback_service.analyze_error(
            error_context=error_context,
            code=code,
            language=language,
        )
        
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing error {error_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/projects/{project_id}/performance")
async def generate_performance_recommendations(
    project_id: str = Path(..., description="ID of the project"),
    environment: str = Query("production", description="Environment (development, staging, production)"),
    metric_limit: int = Query(20, description="Maximum number of metrics to include in the analysis"),
):
    """
    Generate performance recommendations based on metrics.
    
    Args:
        project_id: ID of the project
        environment: Environment (development, staging, production)
        metric_limit: Maximum number of metrics to include in the analysis
        
    Returns:
        AI-powered performance recommendations
    """
    try:
        # Get OrbitBridge instance
        bridge = await get_orbit_bridge()
        
        # Get metric contexts
        metric_contexts = await bridge.get_contexts_by_type(
            context_type=ContextType.METRIC,
            limit=metric_limit,
        )
        
        # Filter by project and environment
        filtered_contexts = [
            context for context in metric_contexts
            if context.project_id == project_id and context.environment == environment
        ]
        
        if not filtered_contexts:
            raise HTTPException(status_code=404, detail=f"No metrics found for project {project_id} in {environment}")
        
        # Get AI feedback service
        ai_feedback_service = await get_ai_feedback_service()
        
        # Generate performance recommendations
        recommendations = await ai_feedback_service.generate_performance_recommendations(
            project_id=project_id,
            environment=environment,
            metric_contexts=filtered_contexts,
        )
        
        return recommendations
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating performance recommendations for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/deployments/{deployment_id}/summary")
async def generate_deployment_summary(
    deployment_id: str = Path(..., description="ID of the deployment to summarize"),
    include_related: bool = Query(True, description="Whether to include related contexts in the summary"),
):
    """
    Generate a summary of a deployment.
    
    Args:
        deployment_id: ID of the deployment to summarize
        include_related: Whether to include related contexts in the summary
        
    Returns:
        AI-generated deployment summary
    """
    try:
        # Get OrbitBridge instance
        bridge = await get_orbit_bridge()
        
        # Get deployment context
        deployment_context = await bridge.get_context(deployment_id)
        
        if not deployment_context or deployment_context.type != ContextType.DEPLOYMENT:
            raise HTTPException(status_code=404, detail=f"Deployment {deployment_id} not found")
        
        # Get related contexts if requested
        related_contexts = []
        if include_related:
            # In a real implementation, this would get related contexts from the database
            # For now, we'll just use the related_contexts field in the deployment context
            for context_id in deployment_context.related_contexts:
                context = await bridge.get_context(context_id)
                if context:
                    related_contexts.append(context)
        
        # Get AI feedback service
        ai_feedback_service = await get_ai_feedback_service()
        
        # Generate deployment summary
        summary = await ai_feedback_service.generate_deployment_summary(
            deployment_context=deployment_context,
            related_contexts=related_contexts,
        )
        
        return summary
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating summary for deployment {deployment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
