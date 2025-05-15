import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from app.models.github import GitHubPushEvent
from app.models.deployment import Deployment, DeploymentStatus
from app.services.hosting_service import HostingService
from app.services.screenshot_service import ScreenshotService
from app.services.webhook_service import WebhookService
from app.utils.metrics import track_deployment_time, track_deployment_status
from app.api.endpoints.sse import broadcast_deployment_update

logger = logging.getLogger(__name__)

class DeploymentService:
    """
    Public version of the deployment service that handles the core deployment functionality.
    This version excludes proprietary features like branding injection and custom domains.
    """
    
    def __init__(self):
        self.hosting_service = HostingService()
        self.screenshot_service = ScreenshotService()
        self.webhook_service = WebhookService()
        
    async def process_github_push(self, push_event: GitHubPushEvent) -> None:
        """
        Process a GitHub push event and trigger a deployment if necessary.
        
        Args:
            push_event: The GitHub push event to process
        """
        # Only deploy on pushes to the default branch
        if not push_event.ref.endswith(push_event.repository.default_branch):
            logger.info(f"Ignoring push to non-default branch: {push_event.ref}")
            return
            
        # Don't deploy on deletion events
        if push_event.deleted:
            logger.info(f"Ignoring deletion event for {push_event.repository.full_name}")
            return
            
        # Start tracking deployment time
        start_time = datetime.now()
        
        # Create a deployment record
        deployment = Deployment(
            repository_name=push_event.repository.full_name,
            commit_sha=push_event.after,
            branch=push_event.repository.default_branch,
            status=DeploymentStatus.PENDING,
            author=push_event.pusher.name,
            commit_message=push_event.head_commit.message if push_event.head_commit else "",
            created_at=datetime.now()
        )
        
        # Broadcast initial deployment status
        await broadcast_deployment_update(deployment)
        
        try:
            # Deploy to OrbitHost's own infrastructure
            logger.info(f"Deploying {deployment.repository_name} @ {deployment.commit_sha} to OrbitHost")
            hosting_response = await self.hosting_service.deploy_site(deployment)
            
            # Update deployment with hosting response
            deployment.url = hosting_response.get("url")
            deployment.site_id = hosting_response.get("site_id")
            
            # Check if the deployment was successful
            if hosting_response.get("status") == "deployed":
                deployment.status = DeploymentStatus.DEPLOYED
                # Broadcast deployment success
                await broadcast_deployment_update(deployment)
                
                # Capture screenshot and DOM content
                if deployment.url:
                    logger.info(f"Capturing screenshot for {deployment.url}")
                    screenshot_data = await self.screenshot_service.capture(deployment.url)
                    deployment.screenshot_url = screenshot_data.get("screenshot_url")
                    deployment.dom_content = screenshot_data.get("dom_content")
                    deployment.screenshot_captured_at = screenshot_data.get("captured_at")
                    
                    # Broadcast updated deployment with screenshot
                    await broadcast_deployment_update(deployment)
            else:
                deployment.status = DeploymentStatus.FAILED
                logger.error(f"Deployment failed for {deployment.repository_name}")
                # Broadcast deployment failure
                await broadcast_deployment_update(deployment)
                
        except Exception as e:
            deployment.status = DeploymentStatus.FAILED
            deployment.error_message = str(e)
            logger.exception(f"Error deploying {deployment.repository_name}: {e}")
            # Broadcast deployment error
            await broadcast_deployment_update(deployment)
            
        finally:
            # Update deployment record with completion time
            deployment.completed_at = datetime.now()
            
            # Track metrics
            track_deployment_time(
                repository=deployment.repository_name,
                duration=(deployment.completed_at - start_time).total_seconds()
            )
            track_deployment_status(
                repository=deployment.repository_name,
                status=deployment.status.value
            )
            
            # Send webhook notifications
            await self.webhook_service.send_deployment_webhook(deployment)
            
    # The _wait_for_deployment method is no longer needed since we're using our own hosting service
    # which provides immediate status in the deploy_site response
