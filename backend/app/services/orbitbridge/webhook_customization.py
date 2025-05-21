"""
AI-powered webhook customization for OrbitBridge.

This module enhances the existing webhook system with AI-driven customization
capabilities, allowing users to define custom webhook behaviors, transformations,
and integrations using natural language instructions.
"""
import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

from app.models.deployment import Deployment
from app.services.ai.claude_service import ClaudeService
from app.services.orbitbridge.context import OrbitContext, ContextType
from app.services.webhook_service import WebhookService
from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

class WebhookTemplate:
    """Model for webhook templates with AI-driven customization."""
    
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        user_id: str,
        project_id: str,
        destination_url: str,
        event_types: List[str],
        include_screenshot: bool = True,
        include_dom: bool = False,
        custom_headers: Optional[Dict[str, str]] = None,
        transformation_instructions: Optional[str] = None,
        ai_enhanced: bool = False,
    ):
        """
        Initialize a webhook template.
        
        Args:
            id: Template ID
            name: Template name
            description: Template description
            user_id: ID of the user who owns the template
            project_id: ID of the project the template is for
            destination_url: URL to send the webhook to
            event_types: Types of events to trigger the webhook
            include_screenshot: Whether to include screenshot data
            include_dom: Whether to include DOM content
            custom_headers: Custom HTTP headers to include
            transformation_instructions: Natural language instructions for AI transformation
            ai_enhanced: Whether to use AI to enhance the webhook payload
        """
        self.id = id
        self.name = name
        self.description = description
        self.user_id = user_id
        self.project_id = project_id
        self.destination_url = destination_url
        self.event_types = event_types
        self.include_screenshot = include_screenshot
        self.include_dom = include_dom
        self.custom_headers = custom_headers or {}
        self.transformation_instructions = transformation_instructions
        self.ai_enhanced = ai_enhanced
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "destination_url": self.destination_url,
            "event_types": self.event_types,
            "include_screenshot": self.include_screenshot,
            "include_dom": self.include_dom,
            "custom_headers": self.custom_headers,
            "transformation_instructions": self.transformation_instructions,
            "ai_enhanced": self.ai_enhanced,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WebhookTemplate":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            user_id=data["user_id"],
            project_id=data["project_id"],
            destination_url=data["destination_url"],
            event_types=data["event_types"],
            include_screenshot=data.get("include_screenshot", True),
            include_dom=data.get("include_dom", False),
            custom_headers=data.get("custom_headers"),
            transformation_instructions=data.get("transformation_instructions"),
            ai_enhanced=data.get("ai_enhanced", False),
        )

class AIWebhookService:
    """
    AI-powered webhook customization service.
    
    This service enhances the existing webhook system with AI-driven customization
    capabilities, allowing users to define custom webhook behaviors, transformations,
    and integrations using natural language instructions.
    """
    
    def __init__(
        self,
        webhook_service: WebhookService,
        claude_service: Optional[ClaudeService] = None,
    ):
        """
        Initialize the AI webhook service.
        
        Args:
            webhook_service: Base webhook service
            claude_service: Claude AI service
        """
        self.webhook_service = webhook_service
        self.claude_service = claude_service
        
        # In a real implementation, templates would be stored in a database
        # For now, we'll use an in-memory dictionary
        self.templates: Dict[str, WebhookTemplate] = {}
        
        logger.info("Initialized AI webhook service")
    
    async def create_template(self, template: WebhookTemplate) -> WebhookTemplate:
        """
        Create a new webhook template.
        
        Args:
            template: Webhook template to create
            
        Returns:
            Created webhook template
        """
        # Store template
        self.templates[template.id] = template
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "webhook_template",
            "operation": "create",
            "template_id": template.id,
            "user_id": template.user_id,
            "project_id": template.project_id,
            "ai_enhanced": template.ai_enhanced,
        })
        
        logger.info(f"Created webhook template {template.id}")
        
        return template
    
    async def get_template(self, template_id: str) -> Optional[WebhookTemplate]:
        """
        Get a webhook template by ID.
        
        Args:
            template_id: ID of the template to get
            
        Returns:
            Webhook template or None if not found
        """
        return self.templates.get(template_id)
    
    async def update_template(self, template: WebhookTemplate) -> WebhookTemplate:
        """
        Update a webhook template.
        
        Args:
            template: Webhook template to update
            
        Returns:
            Updated webhook template
        """
        # Check if template exists
        if template.id not in self.templates:
            raise ValueError(f"Template {template.id} not found")
        
        # Update template
        self.templates[template.id] = template
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "webhook_template",
            "operation": "update",
            "template_id": template.id,
            "user_id": template.user_id,
            "project_id": template.project_id,
            "ai_enhanced": template.ai_enhanced,
        })
        
        logger.info(f"Updated webhook template {template.id}")
        
        return template
    
    async def delete_template(self, template_id: str) -> bool:
        """
        Delete a webhook template.
        
        Args:
            template_id: ID of the template to delete
            
        Returns:
            Boolean indicating success or failure
        """
        # Check if template exists
        if template_id not in self.templates:
            return False
        
        # Get template for logging
        template = self.templates[template_id]
        
        # Delete template
        del self.templates[template_id]
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "webhook_template",
            "operation": "delete",
            "template_id": template_id,
            "user_id": template.user_id,
            "project_id": template.project_id,
        })
        
        logger.info(f"Deleted webhook template {template_id}")
        
        return True
    
    async def list_templates(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[WebhookTemplate]:
        """
        List webhook templates.
        
        Args:
            user_id: Filter by user ID
            project_id: Filter by project ID
            
        Returns:
            List of webhook templates
        """
        templates = list(self.templates.values())
        
        # Apply filters
        if user_id:
            templates = [t for t in templates if t.user_id == user_id]
        
        if project_id:
            templates = [t for t in templates if t.project_id == project_id]
        
        return templates
    
    async def transform_payload(
        self,
        template: WebhookTemplate,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Transform a webhook payload using AI.
        
        Args:
            template: Webhook template
            payload: Original webhook payload
            
        Returns:
            Transformed webhook payload
        """
        # If not AI-enhanced or no transformation instructions, return original payload
        if not template.ai_enhanced or not template.transformation_instructions:
            return payload
        
        # If no Claude service, return original payload
        if not self.claude_service:
            logger.warning("Claude service not available for webhook transformation")
            return payload
        
        try:
            # Create prompt for Claude
            prompt = f"""
            Transform the following webhook payload according to these instructions:
            
            INSTRUCTIONS:
            {template.transformation_instructions}
            
            ORIGINAL PAYLOAD:
            ```json
            {json.dumps(payload, indent=2)}
            ```
            
            Please provide only the transformed JSON payload as your response, with no additional text.
            """
            
            system_prompt = """
            You are a webhook transformation assistant. Your job is to transform webhook payloads according to user instructions.
            
            Follow these rules:
            1. Only output valid JSON
            2. Do not include any explanatory text, only the transformed JSON
            3. Ensure all required fields from the instructions are included
            4. Format the JSON neatly with proper indentation
            """
            
            # Generate transformed payload
            result = await self.claude_service.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=2000,
                temperature=0.1,  # Low temperature for more deterministic output
            )
            
            # Extract JSON from response
            response_text = result.get("text", "")
            
            # Try to parse as JSON
            try:
                # Remove any markdown code block syntax
                if "```json" in response_text:
                    json_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    json_text = response_text.split("```")[1].strip()
                else:
                    json_text = response_text.strip()
                
                transformed_payload = json.loads(json_text)
                
                # Log to MCP
                await get_mcp_client().send({
                    "type": "webhook_transformation",
                    "template_id": template.id,
                    "user_id": template.user_id,
                    "project_id": template.project_id,
                    "status": "success",
                })
                
                logger.info(f"Successfully transformed webhook payload for template {template.id}")
                
                return transformed_payload
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing transformed payload: {str(e)}")
                
                # Log to MCP
                await get_mcp_client().send({
                    "type": "webhook_transformation",
                    "template_id": template.id,
                    "user_id": template.user_id,
                    "project_id": template.project_id,
                    "status": "error",
                    "error": f"JSON parse error: {str(e)}",
                })
                
                # Fall back to original payload
                return payload
        except Exception as e:
            logger.error(f"Error transforming webhook payload: {str(e)}")
            
            # Log to MCP
            await get_mcp_client().send({
                "type": "webhook_transformation",
                "template_id": template.id,
                "user_id": template.user_id,
                "project_id": template.project_id,
                "status": "error",
                "error": str(e),
            })
            
            # Fall back to original payload
            return payload
    
    async def send_webhook(
        self,
        template_id: str,
        context: OrbitContext,
    ) -> bool:
        """
        Send a webhook using a template.
        
        Args:
            template_id: ID of the template to use
            context: OrbitContext to send
            
        Returns:
            Boolean indicating success or failure
        """
        # Get template
        template = await self.get_template(template_id)
        
        if not template:
            logger.error(f"Template {template_id} not found")
            return False
        
        # Check if this context type should trigger the webhook
        if context.type.value not in template.event_types:
            logger.info(f"Context type {context.type} not in template event types {template.event_types}")
            return False
        
        # Convert context to payload
        payload = context.to_dict()
        
        # Apply template filters
        if not template.include_screenshot and "screenshot" in payload:
            del payload["screenshot"]
        
        if not template.include_dom and "metadata" in payload and "dom_content" in payload["metadata"]:
            del payload["metadata"]["dom_content"]
        
        # Transform payload if AI-enhanced
        if template.ai_enhanced:
            payload = await self.transform_payload(template, payload)
        
        # Send webhook
        success = await self.webhook_service.send_webhook(
            url=template.destination_url,
            payload=payload,
            headers=template.custom_headers,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "webhook_delivery",
            "template_id": template_id,
            "context_id": context.id,
            "context_type": context.type.value,
            "user_id": template.user_id,
            "project_id": template.project_id,
            "status": "success" if success else "error",
        })
        
        return success
    
    async def send_deployment_webhook(
        self,
        template_id: str,
        deployment: Deployment,
    ) -> bool:
        """
        Send a deployment webhook using a template.
        
        Args:
            template_id: ID of the template to use
            deployment: Deployment to send
            
        Returns:
            Boolean indicating success or failure
        """
        # Get template
        template = await self.get_template(template_id)
        
        if not template:
            logger.error(f"Template {template_id} not found")
            return False
        
        # Check if deployment events should trigger the webhook
        if "deployment" not in template.event_types:
            logger.info(f"Deployment events not in template event types {template.event_types}")
            return False
        
        # Convert deployment to payload
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
            }
        }
        
        # Add screenshot if included
        if template.include_screenshot and deployment.screenshot_url:
            payload["screenshot"] = {
                "url": str(deployment.screenshot_url),
                "captured_at": deployment.updated_at.isoformat()
            }
        
        # Add DOM content if included
        if template.include_dom and deployment.dom_content:
            payload["dom_content"] = deployment.dom_content
        
        # Transform payload if AI-enhanced
        if template.ai_enhanced:
            payload = await self.transform_payload(template, payload)
        
        # Send webhook
        success = await self.webhook_service.send_webhook(
            url=template.destination_url,
            payload=payload,
            headers=template.custom_headers,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "webhook_delivery",
            "template_id": template_id,
            "deployment_id": deployment.id,
            "user_id": template.user_id,
            "project_id": template.project_id,
            "status": "success" if success else "error",
        })
        
        return success


# Global AI webhook service instance
_ai_webhook_service = None

async def get_ai_webhook_service() -> AIWebhookService:
    """
    Get the AI webhook service instance.
    
    Returns:
        AI webhook service instance
    """
    global _ai_webhook_service
    
    if _ai_webhook_service is None:
        # Get base webhook service
        from app.services.webhook_service import WebhookService
        webhook_service = WebhookService()
        
        # Get Claude service if available
        claude_service = None
        try:
            from app.services.orbitbridge.bridge import get_orbit_bridge
            bridge = await get_orbit_bridge()
            claude_service = bridge.claude_service
        except Exception as e:
            logger.warning(f"Error getting Claude service: {str(e)}")
        
        # Create AI webhook service
        _ai_webhook_service = AIWebhookService(
            webhook_service=webhook_service,
            claude_service=claude_service,
        )
    
    return _ai_webhook_service
