from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Path

from app.models.deployment import Deployment, DeploymentStatus, DeploymentType
from app.services.deployment_service import DeploymentService

router = APIRouter()

# In a real implementation, you would have authentication middleware
# For MVP, we'll simulate authentication with a simple dependency
async def get_current_user():
    # This would normally verify a token and return the user
    return {"id": "user123", "name": "Demo User"}

@router.get("/", response_model=List[Deployment])
async def list_deployments(
    repository: Optional[str] = None,
    status: Optional[DeploymentStatus] = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user = Depends(get_current_user)
):
    """
    List deployments with optional filtering
    """
    # In a real implementation, you would query your database
    # For MVP, we'll return mock data
    
    # Mock deployments for demo purposes
    deployments = [
        Deployment(
            id="deploy1",
            repository_name="user/repo1",
            commit_sha="abc123",
            branch="main",
            status=DeploymentStatus.DEPLOYED,
            url="https://repo1.fly.dev",
            author="Demo User",
            commit_message="Initial commit"
        ),
        Deployment(
            id="deploy2",
            repository_name="user/repo2",
            commit_sha="def456",
            branch="feature/new-ui",
            status=DeploymentStatus.BUILDING,
            author="Demo User",
            commit_message="Update UI components"
        )
    ]
    
    # Apply filters
    if repository:
        deployments = [d for d in deployments if d.repository_name == repository]
    
    if status:
        deployments = [d for d in deployments if d.status == status]
    
    # Apply pagination
    deployments = deployments[offset:offset+limit]
    
    return deployments

@router.get("/{deployment_id}", response_model=Deployment)
async def get_deployment(
    deployment_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get a specific deployment by ID
    """
    # In a real implementation, you would query your database
    # For MVP, we'll return mock data
    
    # Mock deployment for demo purposes
    if deployment_id == "deploy1":
        return Deployment(
            id="deploy1",
            repository_name="user/repo1",
            commit_sha="abc123",
            branch="main",
            status=DeploymentStatus.DEPLOYED,
            url="https://repo1.fly.dev",
            author="Demo User",
            commit_message="Initial commit",
            screenshot_url="https://storage.orbithost.example/screenshots/screenshot_20250515154500.png",
            dom_content="<!DOCTYPE html><html><head><title>Demo Site</title></head><body><h1>Hello World</h1></body></html>"
        )
    
    raise HTTPException(status_code=404, detail="Deployment not found")

@router.post("/{deployment_id}/retry", response_model=Deployment)
async def retry_deployment(
    deployment_id: str,
    current_user = Depends(get_current_user)
):
    """
    Retry a failed deployment
    """
    # In a real implementation, you would check if the deployment exists and is failed
    # Then trigger a new deployment
    
    # For MVP, we'll return a mock response
    return Deployment(
        id=deployment_id,
        repository_name="user/repo1",
        commit_sha="abc123",
        branch="main",
        status=DeploymentStatus.PENDING,
        deployment_type=DeploymentType.PRODUCTION,
        author="Demo User",
        commit_message="Initial commit"
    )

@router.post("/{deployment_id}/preview", response_model=Deployment)
async def create_preview(
    deployment_id: str = Path(..., description="The ID of the deployment to create a preview from"),
    current_user = Depends(get_current_user)
):
    """
    Create a preview deployment from an existing deployment
    """
    deployment_service = DeploymentService()
    preview_deployment = await deployment_service.create_preview_deployment(deployment_id)
    
    if not preview_deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    return preview_deployment

@router.post("/{deployment_id}/rollback/{target_deployment_id}", response_model=Deployment)
async def rollback_deployment(
    deployment_id: str = Path(..., description="The ID of the current deployment"),
    target_deployment_id: str = Path(..., description="The ID of the deployment to rollback to"),
    current_user = Depends(get_current_user)
):
    """
    Rollback a deployment to a previous version
    """
    deployment_service = DeploymentService()
    rollback_deployment = await deployment_service.rollback_deployment(deployment_id, target_deployment_id)
    
    if not rollback_deployment:
        raise HTTPException(status_code=404, detail="One or both deployments not found")
    
    return rollback_deployment

@router.get("/branch/{branch}", response_model=List[Deployment])
async def list_branch_deployments(
    branch: str = Path(..., description="The branch to list deployments for"),
    repository: Optional[str] = None,
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user = Depends(get_current_user)
):
    """
    List deployments for a specific branch
    """
    # In a real implementation, you would query your database for branch deployments
    # For MVP, we'll return mock data
    
    # Mock branch deployments for demo purposes
    deployments = [
        Deployment(
            id="branch1",
            repository_name="user/repo1" if not repository else repository,
            commit_sha="def456",
            branch=branch,
            status=DeploymentStatus.DEPLOYED,
            deployment_type=DeploymentType.BRANCH,
            url=f"https://{branch}--repo1.fly.dev",
            author="Demo User",
            commit_message=f"Update on {branch} branch"
        ),
        Deployment(
            id="branch2",
            repository_name="user/repo1" if not repository else repository,
            commit_sha="ghi789",
            branch=branch,
            status=DeploymentStatus.FAILED,
            deployment_type=DeploymentType.BRANCH,
            author="Demo User",
            commit_message=f"Another update on {branch} branch"
        )
    ]
    
    # Apply repository filter if provided
    if repository:
        deployments = [d for d in deployments if d.repository_name == repository]
    
    # Apply pagination
    deployments = deployments[offset:offset+limit]
    
    return deployments
