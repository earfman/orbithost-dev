"""
API endpoints for AI-powered webhook customization.

This module provides API endpoints for managing webhook templates with
AI-driven customization capabilities.
"""
import logging
import uuid
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from app.services.orbitbridge.webhook_customization import (
    get_ai_webhook_service,
    AIWebhookService,
    WebhookTemplate,
)
from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

# Create API router for webhook customization
router = APIRouter(prefix="/api/webhooks/templates", tags=["webhooks", "templates"])

# Pydantic models for API
class WebhookTemplateCreate(BaseModel):
    """Model for creating a webhook template."""
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    user_id: str = Field(..., description="ID of the user who owns the template")
    project_id: str = Field(..., description="ID of the project the template is for")
    destination_url: str = Field(..., description="URL to send the webhook to")
    event_types: List[str] = Field(..., description="Types of events to trigger the webhook")
    include_screenshot: bool = Field(True, description="Whether to include screenshot data")
    include_dom: bool = Field(False, description="Whether to include DOM content")
    custom_headers: Optional[Dict[str, str]] = Field(None, description="Custom HTTP headers to include")
    transformation_instructions: Optional[str] = Field(None, description="Natural language instructions for AI transformation")
    ai_enhanced: bool = Field(False, description="Whether to use AI to enhance the webhook payload")

class WebhookTemplateUpdate(BaseModel):
    """Model for updating a webhook template."""
    name: Optional[str] = Field(None, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    destination_url: Optional[str] = Field(None, description="URL to send the webhook to")
    event_types: Optional[List[str]] = Field(None, description="Types of events to trigger the webhook")
    include_screenshot: Optional[bool] = Field(None, description="Whether to include screenshot data")
    include_dom: Optional[bool] = Field(None, description="Whether to include DOM content")
    custom_headers: Optional[Dict[str, str]] = Field(None, description="Custom HTTP headers to include")
    transformation_instructions: Optional[str] = Field(None, description="Natural language instructions for AI transformation")
    ai_enhanced: Optional[bool] = Field(None, description="Whether to use AI to enhance the webhook payload")

class WebhookTemplateResponse(BaseModel):
    """Model for webhook template response."""
    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    user_id: str = Field(..., description="ID of the user who owns the template")
    project_id: str = Field(..., description="ID of the project the template is for")
    destination_url: str = Field(..., description="URL to send the webhook to")
    event_types: List[str] = Field(..., description="Types of events to trigger the webhook")
    include_screenshot: bool = Field(..., description="Whether to include screenshot data")
    include_dom: bool = Field(..., description="Whether to include DOM content")
    custom_headers: Dict[str, str] = Field(..., description="Custom HTTP headers to include")
    transformation_instructions: Optional[str] = Field(None, description="Natural language instructions for AI transformation")
    ai_enhanced: bool = Field(..., description="Whether to use AI to enhance the webhook payload")

@router.post("", response_model=WebhookTemplateResponse)
async def create_template(
    template: WebhookTemplateCreate = Body(...),
):
    """
    Create a new webhook template.
    
    Args:
        template: Webhook template to create
        
    Returns:
        Created webhook template
    """
    try:
        # Get AI webhook service
        webhook_service = await get_ai_webhook_service()
        
        # Generate template ID
        template_id = str(uuid.uuid4())
        
        # Create template
        created_template = await webhook_service.create_template(
            WebhookTemplate(
                id=template_id,
                name=template.name,
                description=template.description,
                user_id=template.user_id,
                project_id=template.project_id,
                destination_url=template.destination_url,
                event_types=template.event_types,
                include_screenshot=template.include_screenshot,
                include_dom=template.include_dom,
                custom_headers=template.custom_headers or {},
                transformation_instructions=template.transformation_instructions,
                ai_enhanced=template.ai_enhanced,
            )
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "webhook_template_api",
            "operation": "create",
            "template_id": template_id,
            "user_id": template.user_id,
            "project_id": template.project_id,
        })
        
        return WebhookTemplateResponse(**created_template.to_dict())
    except Exception as e:
        logger.error(f"Error creating webhook template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{template_id}", response_model=WebhookTemplateResponse)
async def get_template(
    template_id: str = Path(..., description="ID of the template to get"),
):
    """
    Get a webhook template by ID.
    
    Args:
        template_id: ID of the template to get
        
    Returns:
        Webhook template
    """
    try:
        # Get AI webhook service
        webhook_service = await get_ai_webhook_service()
        
        # Get template
        template = await webhook_service.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "webhook_template_api",
            "operation": "get",
            "template_id": template_id,
            "user_id": template.user_id,
            "project_id": template.project_id,
        })
        
        return WebhookTemplateResponse(**template.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting webhook template {template_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{template_id}", response_model=WebhookTemplateResponse)
async def update_template(
    template_id: str = Path(..., description="ID of the template to update"),
    template_update: WebhookTemplateUpdate = Body(...),
):
    """
    Update a webhook template.
    
    Args:
        template_id: ID of the template to update
        template_update: Webhook template update
        
    Returns:
        Updated webhook template
    """
    try:
        # Get AI webhook service
        webhook_service = await get_ai_webhook_service()
        
        # Get existing template
        existing_template = await webhook_service.get_template(template_id)
        
        if not existing_template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        # Update template fields
        updated_template = WebhookTemplate(
            id=template_id,
            name=template_update.name or existing_template.name,
            description=template_update.description or existing_template.description,
            user_id=existing_template.user_id,
            project_id=existing_template.project_id,
            destination_url=template_update.destination_url or existing_template.destination_url,
            event_types=template_update.event_types or existing_template.event_types,
            include_screenshot=template_update.include_screenshot if template_update.include_screenshot is not None else existing_template.include_screenshot,
            include_dom=template_update.include_dom if template_update.include_dom is not None else existing_template.include_dom,
            custom_headers=template_update.custom_headers or existing_template.custom_headers,
            transformation_instructions=template_update.transformation_instructions if template_update.transformation_instructions is not None else existing_template.transformation_instructions,
            ai_enhanced=template_update.ai_enhanced if template_update.ai_enhanced is not None else existing_template.ai_enhanced,
        )
        
        # Update template
        updated_template = await webhook_service.update_template(updated_template)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "webhook_template_api",
            "operation": "update",
            "template_id": template_id,
            "user_id": updated_template.user_id,
            "project_id": updated_template.project_id,
        })
        
        return WebhookTemplateResponse(**updated_template.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating webhook template {template_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{template_id}")
async def delete_template(
    template_id: str = Path(..., description="ID of the template to delete"),
):
    """
    Delete a webhook template.
    
    Args:
        template_id: ID of the template to delete
        
    Returns:
        Success message
    """
    try:
        # Get AI webhook service
        webhook_service = await get_ai_webhook_service()
        
        # Get existing template for logging
        existing_template = await webhook_service.get_template(template_id)
        
        if not existing_template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        # Delete template
        success = await webhook_service.delete_template(template_id)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to delete template {template_id}")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "webhook_template_api",
            "operation": "delete",
            "template_id": template_id,
            "user_id": existing_template.user_id,
            "project_id": existing_template.project_id,
        })
        
        return {"message": f"Template {template_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting webhook template {template_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("", response_model=List[WebhookTemplateResponse])
async def list_templates(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
):
    """
    List webhook templates.
    
    Args:
        user_id: Filter by user ID
        project_id: Filter by project ID
        
    Returns:
        List of webhook templates
    """
    try:
        # Get AI webhook service
        webhook_service = await get_ai_webhook_service()
        
        # List templates
        templates = await webhook_service.list_templates(
            user_id=user_id,
            project_id=project_id,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "webhook_template_api",
            "operation": "list",
            "user_id": user_id,
            "project_id": project_id,
            "count": len(templates),
        })
        
        return [WebhookTemplateResponse(**template.to_dict()) for template in templates]
    except Exception as e:
        logger.error(f"Error listing webhook templates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{template_id}/test")
async def test_template(
    template_id: str = Path(..., description="ID of the template to test"),
    payload: Dict[str, Any] = Body(..., description="Test payload"),
):
    """
    Test a webhook template with a sample payload.
    
    Args:
        template_id: ID of the template to test
        payload: Test payload
        
    Returns:
        Transformed payload
    """
    try:
        # Get AI webhook service
        webhook_service = await get_ai_webhook_service()
        
        # Get template
        template = await webhook_service.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        # Transform payload
        transformed_payload = await webhook_service.transform_payload(template, payload)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "webhook_template_api",
            "operation": "test",
            "template_id": template_id,
            "user_id": template.user_id,
            "project_id": template.project_id,
        })
        
        return {
            "original_payload": payload,
            "transformed_payload": transformed_payload,
            "ai_enhanced": template.ai_enhanced,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing webhook template {template_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
