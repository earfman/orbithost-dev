from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.core.auth import get_current_user, get_optional_user
from app.models.user import User
from app.models.deployment import Deployment, DeploymentStatus
from app.services.deployment_service_public import DeploymentService
from app.models.github import GitHubPushEvent, GitHubRepository, GitHubCommit, GitHubPusher
from app.api.endpoints.sse import broadcast_deployment_update

router = APIRouter()

class WindsurfDeployRequest(BaseModel):
    repository_url: str
    branch: str = "main"
    commit_sha: Optional[str] = None
    deploy_message: Optional[str] = "Deployed via Windsurf"

@router.post("/deploy")
async def windsurf_deploy(
    request: WindsurfDeployRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Endpoint for Windsurf to trigger deployments directly.
    This allows for a simple "deploy on OrbitHost" command to work.
    """
    # Extract repository name from URL
    # Example: https://github.com/username/repo-name -> username/repo-name
    repo_parts = request.repository_url.split('github.com/')
    if len(repo_parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")
    
    repository_name = repo_parts[1].rstrip('/')
    if repository_name.endswith('.git'):
        repository_name = repository_name[:-4]
    
    # Create a simulated GitHub push event to use the existing deployment flow
    push_event = GitHubPushEvent(
        ref=f"refs/heads/{request.branch}",
        after=request.commit_sha or "HEAD",
        repository=GitHubRepository(
            full_name=repository_name,
            default_branch=request.branch
        ),
        pusher=GitHubPusher(
            name=current_user.email if current_user else "windsurf"
        ),
        head_commit=GitHubCommit(
            message=request.deploy_message
        ),
        deleted=False
    )
    
    # Process the GitHub push event in the background
    deployment_service = DeploymentService()
    background_tasks.add_task(
        deployment_service.process_github_push,
        push_event
    )
    
    return {
        "status": "success",
        "message": f"Deployment of {repository_name} initiated",
        "deployment_id": str(deployment.id),
        "repository": repository_name,
        "branch": request.branch
    }

@router.get("/status/{repository_name}")
async def get_deployment_status(
    repository_name: str,
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Get the status of the latest deployment for a repository
    """
    # In a real implementation, this would query the database for the latest deployment
    # For now, we'll return a simple response
    return {
        "status": "success",
        "message": f"Use the SSE endpoint to get real-time deployment updates for {repository_name}",
        "repository": repository_name,
        "sse_endpoint": "/sse/deployments"
    }
