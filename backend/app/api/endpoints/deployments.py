from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Query

from app.models.deployment import Deployment, DeploymentStatus
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
        author="Demo User",
        commit_message="Initial commit"
    )
