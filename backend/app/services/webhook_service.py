import logging
import json
from typing import Dict, Any, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.models.deployment import Deployment
from app.utils.metrics import webhook_duration, webhook_failures

logger = logging.getLogger(__name__)

class WebhookService:
    """Service for sending webhooks to AI agents"""
    
    async def send_deployment_webhook(self, deployment: Deployment) -> bool:
        """
        Send deployment data to the user's AI agent
        
        Args:
            deployment: Deployment object with all data
            
        Returns:
            Boolean indicating success or failure
        """
        logger.info(f"Sending webhook for deployment {deployment.id}")
        
        # In a real implementation, you would get the webhook URL from the user's settings
        # For now, we'll use a placeholder
        
        # Prepare the payload
        payload = {
            "event_type": "deployment",
            "deployment": {
                "id": deployment.id,
                "repository": deployment.repository_name,
                "commit_sha": deployment.commit_sha,
                "branch": deployment.branch,
                "status": deployment.status,
                "url": str(deployment.url) if deployment.url else None,
                "author": deployment.author,
                "commit_message": deployment.commit_message,
                "created_at": deployment.created_at.isoformat(),
                "updated_at": deployment.updated_at.isoformat(),
            },
            "screenshot": {
                "url": str(deployment.screenshot_url) if deployment.screenshot_url else None,
                "captured_at": deployment.updated_at.isoformat()
            },
            "dom_content": deployment.dom_content
        }
        
        # Get the webhook URL (in production, this would come from the user's settings)
        webhook_url = self._get_webhook_url_for_repository(deployment.repository_name)
        
        if not webhook_url:
            logger.warning(f"No webhook URL found for repository {deployment.repository_name}")
            return False
        
        # Send the webhook with retry logic
        try:
            success = await self._send_webhook_with_retry(webhook_url, payload)
            return success
        except Exception as e:
            logger.error(f"Failed to send webhook: {str(e)}")
            webhook_failures.inc({"repository": deployment.repository_name})
            return False
    
    def _get_webhook_url_for_repository(self, repository_name: str) -> Optional[str]:
        """
        Get the webhook URL for a repository
        
        Args:
            repository_name: GitHub repository name
            
        Returns:
            Webhook URL or None if not found
        """
        # In a real implementation, you would look up the webhook URL in your database
        # For now, we'll return a placeholder URL
        return f"https://api.ai-agent-example.com/webhooks/deployment/{repository_name}"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def _send_webhook_with_retry(self, url: str, payload: Dict[str, Any]) -> bool:
        """
        Send a webhook with retry logic
        
        Args:
            url: Webhook URL
            payload: Webhook payload
            
        Returns:
            Boolean indicating success or failure
        """
        import time
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=30.0
                )
                
                duration = time.time() - start_time
                webhook_duration.observe(duration)
                
                if response.status_code >= 200 and response.status_code < 300:
                    logger.info(f"Webhook sent successfully to {url}")
                    return True
                else:
                    logger.warning(f"Webhook failed with status {response.status_code}: {response.text}")
                    raise Exception(f"Webhook failed with status {response.status_code}")
        except httpx.RequestError as e:
            logger.warning(f"Webhook request failed: {str(e)}")
            raise
