import hmac
import hashlib
import json
from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.services.deployment_service import DeploymentService
from app.models.github import GitHubPushEvent

router = APIRouter()

async def verify_github_signature(request: Request):
    """Verify that the webhook is from GitHub using the secret token"""
    if not settings.GITHUB_WEBHOOK_SECRET:
        return True  # Skip verification if no secret is set (dev mode)
    
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        raise HTTPException(status_code=401, detail="Missing signature header")
    
    body = await request.body()
    
    # Create expected signature
    digest = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    expected_signature = f"sha256={digest}"
    
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    return True

@router.post("/", status_code=202)
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    _: bool = Depends(verify_github_signature)
):
    """
    Handle GitHub webhook events.
    Currently only supports push events.
    """
    event_type = request.headers.get("X-GitHub-Event")
    
    if event_type != "push":
        return JSONResponse(
            status_code=202,
            content={"message": f"Event type {event_type} not supported"}
        )
    
    payload = await request.json()
    push_event = GitHubPushEvent(**payload)
    
    # Process the deployment in the background
    deployment_service = DeploymentService()
    background_tasks.add_task(
        deployment_service.process_github_push,
        push_event
    )
    
    return {
        "message": "Deployment initiated",
        "repository": push_event.repository.full_name,
        "commit": push_event.after
    }
