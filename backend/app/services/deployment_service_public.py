import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from app.models.github import GitHubPushEvent
from app.models.deployment import Deployment, DeploymentStatus, DeploymentType
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
        # Extract branch name from ref
        branch = push_event.ref.split('/')[-1]
        
        # Determine deployment type based on branch
        deployment_type = DeploymentType.PRODUCTION if branch == push_event.repository.default_branch else DeploymentType.BRANCH
        
        # For non-default branches, check if we should create a branch deployment
        if branch != push_event.repository.default_branch:
            logger.info(f"Processing branch deployment for: {push_event.ref}")
            # You could add logic here to only deploy certain branches
            # For now, we'll deploy all branches
            
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
            branch=branch,
            status=DeploymentStatus.PENDING,
            deployment_type=deployment_type,
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
            
    async def create_preview_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """
        Create a preview deployment from an existing deployment.
        
        Args:
            deployment_id: The ID of the deployment to create a preview from
            
        Returns:
            The preview deployment if successful, None otherwise
        """
        # In a real implementation, you would retrieve the deployment from the database
        # For now, we'll simulate it with a mock deployment
        original_deployment = self._get_deployment_by_id(deployment_id)
        
        if not original_deployment:
            logger.error(f"Deployment not found: {deployment_id}")
            return None
            
        # Create a preview deployment
        preview_deployment = Deployment(
            repository_name=original_deployment.repository_name,
            commit_sha=original_deployment.commit_sha,
            branch=original_deployment.branch,
            status=DeploymentStatus.PENDING,
            deployment_type=DeploymentType.PREVIEW,
            author=original_deployment.author,
            commit_message=f"Preview of {original_deployment.commit_message}",
            created_at=datetime.now(),
            parent_deployment_id=deployment_id
        )
        
        # Broadcast initial preview deployment status
        await broadcast_deployment_update(preview_deployment)
        
        try:
            # Deploy to a preview environment
            logger.info(f"Creating preview deployment for {preview_deployment.repository_name} @ {preview_deployment.commit_sha}")
            hosting_response = await self.hosting_service.deploy_preview(preview_deployment)
            
            # Update preview deployment with hosting response
            preview_deployment.url = hosting_response.get("url")
            preview_deployment.site_id = hosting_response.get("site_id")
            preview_deployment.preview_expiry = datetime.now() + timedelta(days=7)  # Preview lasts for 7 days
            
            # Check if the preview deployment was successful
            if hosting_response.get("status") == "deployed":
                preview_deployment.status = DeploymentStatus.PREVIEW
                # Broadcast preview deployment success
                await broadcast_deployment_update(preview_deployment)
                
                # Capture screenshot and DOM content
                if preview_deployment.url:
                    logger.info(f"Capturing screenshot for preview: {preview_deployment.url}")
                    screenshot_data = await self.screenshot_service.capture(preview_deployment.url)
                    preview_deployment.screenshot_url = screenshot_data.get("screenshot_url")
                    preview_deployment.dom_content = screenshot_data.get("dom_content")
                    preview_deployment.screenshot_captured_at = screenshot_data.get("captured_at")
                    
                    # Broadcast updated preview deployment with screenshot
                    await broadcast_deployment_update(preview_deployment)
            else:
                preview_deployment.status = DeploymentStatus.FAILED
                logger.error(f"Preview deployment failed for {preview_deployment.repository_name}")
                # Broadcast preview deployment failure
                await broadcast_deployment_update(preview_deployment)
                
        except Exception as e:
            preview_deployment.status = DeploymentStatus.FAILED
            preview_deployment.error_message = str(e)
            logger.exception(f"Error creating preview deployment for {preview_deployment.repository_name}: {e}")
            # Broadcast preview deployment error
            await broadcast_deployment_update(preview_deployment)
            
        finally:
            # Update preview deployment record with completion time
            preview_deployment.completed_at = datetime.now()
            
            # Track metrics
            track_deployment_time(
                repository=preview_deployment.repository_name,
                duration=(preview_deployment.completed_at - preview_deployment.created_at).total_seconds(),
                deployment_type="preview"
            )
            track_deployment_status(
                repository=preview_deployment.repository_name,
                status=preview_deployment.status.value,
                deployment_type="preview"
            )
            
        return preview_deployment
        
    async def rollback_deployment(self, deployment_id: str, target_deployment_id: str) -> Optional[Deployment]:
        """
        Rollback a deployment to a previous version.
        
        Args:
            deployment_id: The ID of the current deployment
            target_deployment_id: The ID of the deployment to rollback to
            
        Returns:
            The new deployment if successful, None otherwise
        """
        # In a real implementation, you would retrieve both deployments from the database
        current_deployment = self._get_deployment_by_id(deployment_id)
        target_deployment = self._get_deployment_by_id(target_deployment_id)
        
        if not current_deployment or not target_deployment:
            logger.error(f"One or both deployments not found: {deployment_id}, {target_deployment_id}")
            return None
            
        # Create a rollback deployment
        rollback_deployment = Deployment(
            repository_name=current_deployment.repository_name,
            commit_sha=target_deployment.commit_sha,  # Use the target commit SHA
            branch=current_deployment.branch,
            status=DeploymentStatus.PENDING,
            deployment_type=DeploymentType.PRODUCTION,
            author=current_deployment.author,
            commit_message=f"Rollback to {target_deployment.commit_sha[:7]}",
            created_at=datetime.now(),
            parent_deployment_id=target_deployment_id,
            is_rollback=True
        )
        
        # Broadcast initial rollback deployment status
        await broadcast_deployment_update(rollback_deployment)
        
        try:
            # Deploy the rollback
            logger.info(f"Rolling back {rollback_deployment.repository_name} to {target_deployment.commit_sha[:7]}")
            hosting_response = await self.hosting_service.deploy_rollback(rollback_deployment, target_deployment)
            
            # Update rollback deployment with hosting response
            rollback_deployment.url = hosting_response.get("url")
            rollback_deployment.site_id = hosting_response.get("site_id")
            
            # Check if the rollback was successful
            if hosting_response.get("status") == "deployed":
                rollback_deployment.status = DeploymentStatus.DEPLOYED
                # Broadcast rollback success
                await broadcast_deployment_update(rollback_deployment)
                
                # Capture screenshot and DOM content
                if rollback_deployment.url:
                    logger.info(f"Capturing screenshot for rollback: {rollback_deployment.url}")
                    screenshot_data = await self.screenshot_service.capture(rollback_deployment.url)
                    rollback_deployment.screenshot_url = screenshot_data.get("screenshot_url")
                    rollback_deployment.dom_content = screenshot_data.get("dom_content")
                    rollback_deployment.screenshot_captured_at = screenshot_data.get("captured_at")
                    
                    # Broadcast updated rollback deployment with screenshot
                    await broadcast_deployment_update(rollback_deployment)
            else:
                rollback_deployment.status = DeploymentStatus.FAILED
                logger.error(f"Rollback failed for {rollback_deployment.repository_name}")
                # Broadcast rollback failure
                await broadcast_deployment_update(rollback_deployment)
                
        except Exception as e:
            rollback_deployment.status = DeploymentStatus.FAILED
            rollback_deployment.error_message = str(e)
            logger.exception(f"Error rolling back {rollback_deployment.repository_name}: {e}")
            # Broadcast rollback error
            await broadcast_deployment_update(rollback_deployment)
            
        finally:
            # Update rollback deployment record with completion time
            rollback_deployment.completed_at = datetime.now()
            
            # Track metrics
            track_deployment_time(
                repository=rollback_deployment.repository_name,
                duration=(rollback_deployment.completed_at - rollback_deployment.created_at).total_seconds(),
                deployment_type="rollback"
            )
            track_deployment_status(
                repository=rollback_deployment.repository_name,
                status=rollback_deployment.status.value,
                deployment_type="rollback"
            )
            
        return rollback_deployment
    
    def _get_deployment_by_id(self, deployment_id: str) -> Optional[Deployment]:
        """
        Get a deployment by ID.
        
        Args:
            deployment_id: The ID of the deployment to get
            
        Returns:
            The deployment if found, None otherwise
        """
        # In a real implementation, you would retrieve the deployment from the database
        # For now, we'll return a mock deployment
        if deployment_id == "deploy1":
            return Deployment(
                id="deploy1",
                repository_name="user/repo1",
                commit_sha="abc123",
                branch="main",
                status=DeploymentStatus.DEPLOYED,
                deployment_type=DeploymentType.PRODUCTION,
                url="https://repo1.fly.dev",
                site_id="site1",
                author="Demo User",
                commit_message="Initial commit",
                created_at=datetime.now() - timedelta(days=1),
                completed_at=datetime.now() - timedelta(days=1) + timedelta(minutes=5)
            )
        
        return None
        
    # The _wait_for_deployment method is no longer needed since we're using our own hosting service
    # which provides immediate status in the deploy_site response
