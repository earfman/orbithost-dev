"""
API endpoints for AI agent configuration.

This module provides API endpoints for managing AI agent configurations,
including service enablement, context sharing preferences, prompt templates,
and integration settings.
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from app.services.orbitbridge.agent_config import (
    get_ai_agent_config_service,
    AIAgentConfigService,
    AIAgentConfig,
    PromptTemplate,
    AIServiceType,
    ContextSharingLevel,
)
from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

# Create API router for AI agent configuration
router = APIRouter(prefix="/api/ai-config", tags=["ai-config"])

# Pydantic models for API
class PromptTemplateCreate(BaseModel):
    """Model for creating a prompt template."""
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    service_type: str = Field(..., description="Type of AI service this template is for")
    template_text: str = Field(..., description="The prompt template text with variables")
    variables: List[str] = Field(..., description="List of variable names used in the template")

class PromptTemplateUpdate(BaseModel):
    """Model for updating a prompt template."""
    name: Optional[str] = Field(None, description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    template_text: Optional[str] = Field(None, description="The prompt template text with variables")
    variables: Optional[List[str]] = Field(None, description="List of variable names used in the template")

class PromptTemplateResponse(BaseModel):
    """Model for prompt template response."""
    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    service_type: str = Field(..., description="Type of AI service this template is for")
    template_text: str = Field(..., description="The prompt template text with variables")
    variables: List[str] = Field(..., description="List of variable names used in the template")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

class AIAgentConfigCreate(BaseModel):
    """Model for creating an AI agent configuration."""
    name: str = Field(..., description="Configuration name")
    description: str = Field(..., description="Configuration description")
    user_id: str = Field(..., description="ID of the user who owns the configuration")
    project_id: str = Field(..., description="ID of the project the configuration is for")
    enabled_services: List[str] = Field(..., description="List of enabled AI services")
    context_sharing: Dict[str, str] = Field(..., description="Dictionary mapping AI services to context sharing levels")
    rate_limits: Dict[str, int] = Field(..., description="Dictionary mapping AI services to rate limits (calls per hour)")
    custom_instructions: Optional[str] = Field(None, description="Custom instructions for AI agents")
    prompt_templates: Optional[Dict[str, str]] = Field(None, description="Dictionary mapping template names to prompt template IDs")
    auto_analyze_deployments: bool = Field(True, description="Whether to automatically analyze deployments")
    auto_analyze_errors: bool = Field(True, description="Whether to automatically analyze errors")

class AIAgentConfigUpdate(BaseModel):
    """Model for updating an AI agent configuration."""
    name: Optional[str] = Field(None, description="Configuration name")
    description: Optional[str] = Field(None, description="Configuration description")
    enabled_services: Optional[List[str]] = Field(None, description="List of enabled AI services")
    context_sharing: Optional[Dict[str, str]] = Field(None, description="Dictionary mapping AI services to context sharing levels")
    rate_limits: Optional[Dict[str, int]] = Field(None, description="Dictionary mapping AI services to rate limits (calls per hour)")
    custom_instructions: Optional[str] = Field(None, description="Custom instructions for AI agents")
    prompt_templates: Optional[Dict[str, str]] = Field(None, description="Dictionary mapping template names to prompt template IDs")
    auto_analyze_deployments: Optional[bool] = Field(None, description="Whether to automatically analyze deployments")
    auto_analyze_errors: Optional[bool] = Field(None, description="Whether to automatically analyze errors")

class AIAgentConfigResponse(BaseModel):
    """Model for AI agent configuration response."""
    id: str = Field(..., description="Configuration ID")
    name: str = Field(..., description="Configuration name")
    description: str = Field(..., description="Configuration description")
    user_id: str = Field(..., description="ID of the user who owns the configuration")
    project_id: str = Field(..., description="ID of the project the configuration is for")
    enabled_services: List[str] = Field(..., description="List of enabled AI services")
    context_sharing: Dict[str, str] = Field(..., description="Dictionary mapping AI services to context sharing levels")
    rate_limits: Dict[str, int] = Field(..., description="Dictionary mapping AI services to rate limits (calls per hour)")
    custom_instructions: Optional[str] = Field(None, description="Custom instructions for AI agents")
    prompt_templates: Dict[str, str] = Field(..., description="Dictionary mapping template names to prompt template IDs")
    auto_analyze_deployments: bool = Field(..., description="Whether to automatically analyze deployments")
    auto_analyze_errors: bool = Field(..., description="Whether to automatically analyze errors")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

class RenderPromptRequest(BaseModel):
    """Model for rendering a prompt template."""
    template_id: str = Field(..., description="ID of the template to render")
    variables: Dict[str, Any] = Field(..., description="Dictionary of variables to substitute")

@router.post("/templates", response_model=PromptTemplateResponse)
async def create_template(
    template: PromptTemplateCreate = Body(...),
):
    """
    Create a new prompt template.
    
    Args:
        template: Prompt template to create
        
    Returns:
        Created prompt template
    """
    try:
        # Get AI agent configuration service
        config_service = await get_ai_agent_config_service()
        
        # Generate template ID
        template_id = str(uuid.uuid4())
        
        # Create template
        created_template = await config_service.create_template(
            PromptTemplate(
                id=template_id,
                name=template.name,
                description=template.description,
                service_type=AIServiceType(template.service_type),
                template_text=template.template_text,
                variables=template.variables,
            )
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "prompt_template_api",
            "operation": "create",
            "template_id": template_id,
            "service_type": template.service_type,
        })
        
        return PromptTemplateResponse(**created_template.to_dict())
    except ValueError as e:
        logger.error(f"Error creating prompt template: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating prompt template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/{template_id}", response_model=PromptTemplateResponse)
async def get_template(
    template_id: str = Path(..., description="ID of the template to get"),
):
    """
    Get a prompt template by ID.
    
    Args:
        template_id: ID of the template to get
        
    Returns:
        Prompt template
    """
    try:
        # Get AI agent configuration service
        config_service = await get_ai_agent_config_service()
        
        # Get template
        template = await config_service.get_template(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "prompt_template_api",
            "operation": "get",
            "template_id": template_id,
            "service_type": template.service_type.value,
        })
        
        return PromptTemplateResponse(**template.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt template {template_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/templates/{template_id}", response_model=PromptTemplateResponse)
async def update_template(
    template_id: str = Path(..., description="ID of the template to update"),
    template_update: PromptTemplateUpdate = Body(...),
):
    """
    Update a prompt template.
    
    Args:
        template_id: ID of the template to update
        template_update: Prompt template update
        
    Returns:
        Updated prompt template
    """
    try:
        # Get AI agent configuration service
        config_service = await get_ai_agent_config_service()
        
        # Get existing template
        existing_template = await config_service.get_template(template_id)
        
        if not existing_template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        # Update template fields
        updated_template = PromptTemplate(
            id=template_id,
            name=template_update.name or existing_template.name,
            description=template_update.description or existing_template.description,
            service_type=existing_template.service_type,
            template_text=template_update.template_text or existing_template.template_text,
            variables=template_update.variables or existing_template.variables,
            created_at=existing_template.created_at,
        )
        
        # Update template
        updated_template = await config_service.update_template(updated_template)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "prompt_template_api",
            "operation": "update",
            "template_id": template_id,
            "service_type": updated_template.service_type.value,
        })
        
        return PromptTemplateResponse(**updated_template.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt template {template_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str = Path(..., description="ID of the template to delete"),
):
    """
    Delete a prompt template.
    
    Args:
        template_id: ID of the template to delete
        
    Returns:
        Success message
    """
    try:
        # Get AI agent configuration service
        config_service = await get_ai_agent_config_service()
        
        # Get existing template for logging
        existing_template = await config_service.get_template(template_id)
        
        if not existing_template:
            raise HTTPException(status_code=404, detail=f"Template {template_id} not found")
        
        # Delete template
        success = await config_service.delete_template(template_id)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to delete template {template_id}")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "prompt_template_api",
            "operation": "delete",
            "template_id": template_id,
            "service_type": existing_template.service_type.value,
        })
        
        return {"message": f"Template {template_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting prompt template {template_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates", response_model=List[PromptTemplateResponse])
async def list_templates(
    service_type: Optional[str] = Query(None, description="Filter by service type"),
):
    """
    List prompt templates.
    
    Args:
        service_type: Filter by service type
        
    Returns:
        List of prompt templates
    """
    try:
        # Get AI agent configuration service
        config_service = await get_ai_agent_config_service()
        
        # List templates
        templates = await config_service.list_templates(
            service_type=AIServiceType(service_type) if service_type else None,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "prompt_template_api",
            "operation": "list",
            "service_type": service_type,
            "count": len(templates),
        })
        
        return [PromptTemplateResponse(**template.to_dict()) for template in templates]
    except ValueError as e:
        logger.error(f"Error listing prompt templates: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing prompt templates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/templates/render", response_model=Dict[str, Any])
async def render_prompt(
    request: RenderPromptRequest = Body(...),
):
    """
    Render a prompt template with variables.
    
    Args:
        request: Render prompt request
        
    Returns:
        Rendered prompt
    """
    try:
        # Get AI agent configuration service
        config_service = await get_ai_agent_config_service()
        
        # Get template for validation
        template = await config_service.get_template(request.template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail=f"Template {request.template_id} not found")
        
        # Check if all required variables are provided
        missing_vars = [var for var in template.variables if var not in request.variables]
        
        if missing_vars:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required variables: {', '.join(missing_vars)}",
            )
        
        # Render prompt
        rendered = await config_service.render_prompt(
            template_id=request.template_id,
            variables=request.variables,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "prompt_template_api",
            "operation": "render",
            "template_id": request.template_id,
            "service_type": template.service_type.value,
        })
        
        return {
            "template_id": request.template_id,
            "rendered_prompt": rendered,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering prompt template: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs", response_model=AIAgentConfigResponse)
async def create_config(
    config: AIAgentConfigCreate = Body(...),
):
    """
    Create a new AI agent configuration.
    
    Args:
        config: AI agent configuration to create
        
    Returns:
        Created AI agent configuration
    """
    try:
        # Get AI agent configuration service
        config_service = await get_ai_agent_config_service()
        
        # Generate configuration ID
        config_id = str(uuid.uuid4())
        
        # Validate service types
        enabled_services = {AIServiceType(s) for s in config.enabled_services}
        
        # Validate context sharing levels
        context_sharing = {
            AIServiceType(k): ContextSharingLevel(v)
            for k, v in config.context_sharing.items()
        }
        
        # Validate rate limits
        rate_limits = {
            AIServiceType(k): v
            for k, v in config.rate_limits.items()
        }
        
        # Create configuration
        created_config = await config_service.create_config(
            AIAgentConfig(
                id=config_id,
                name=config.name,
                description=config.description,
                user_id=config.user_id,
                project_id=config.project_id,
                enabled_services=enabled_services,
                context_sharing=context_sharing,
                rate_limits=rate_limits,
                custom_instructions=config.custom_instructions,
                prompt_templates=config.prompt_templates or {},
                auto_analyze_deployments=config.auto_analyze_deployments,
                auto_analyze_errors=config.auto_analyze_errors,
            )
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "ai_agent_config_api",
            "operation": "create",
            "config_id": config_id,
            "user_id": config.user_id,
            "project_id": config.project_id,
        })
        
        return AIAgentConfigResponse(**created_config.to_dict())
    except ValueError as e:
        logger.error(f"Error creating AI agent configuration: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating AI agent configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/configs/{config_id}", response_model=AIAgentConfigResponse)
async def get_config(
    config_id: str = Path(..., description="ID of the configuration to get"),
):
    """
    Get an AI agent configuration by ID.
    
    Args:
        config_id: ID of the configuration to get
        
    Returns:
        AI agent configuration
    """
    try:
        # Get AI agent configuration service
        config_service = await get_ai_agent_config_service()
        
        # Get configuration
        config = await config_service.get_config(config_id)
        
        if not config:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "ai_agent_config_api",
            "operation": "get",
            "config_id": config_id,
            "user_id": config.user_id,
            "project_id": config.project_id,
        })
        
        return AIAgentConfigResponse(**config.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting AI agent configuration {config_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/configs/project/{project_id}", response_model=AIAgentConfigResponse)
async def get_config_for_project(
    project_id: str = Path(..., description="ID of the project"),
):
    """
    Get an AI agent configuration for a project.
    
    Args:
        project_id: ID of the project
        
    Returns:
        AI agent configuration
    """
    try:
        # Get AI agent configuration service
        config_service = await get_ai_agent_config_service()
        
        # Get configuration
        config = await config_service.get_config_for_project(project_id)
        
        if not config:
            # Create a default configuration
            # First, we need a user ID - in a real implementation, this would come from the auth context
            # For now, we'll use a placeholder
            user_id = "default_user"
            
            config = AIAgentConfig.create_default(
                user_id=user_id,
                project_id=project_id,
            )
            
            # Store the default configuration
            config = await config_service.create_config(config)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "ai_agent_config_api",
            "operation": "get_for_project",
            "project_id": project_id,
            "user_id": config.user_id,
        })
        
        return AIAgentConfigResponse(**config.to_dict())
    except Exception as e:
        logger.error(f"Error getting AI agent configuration for project {project_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/configs/{config_id}", response_model=AIAgentConfigResponse)
async def update_config(
    config_id: str = Path(..., description="ID of the configuration to update"),
    config_update: AIAgentConfigUpdate = Body(...),
):
    """
    Update an AI agent configuration.
    
    Args:
        config_id: ID of the configuration to update
        config_update: AI agent configuration update
        
    Returns:
        Updated AI agent configuration
    """
    try:
        # Get AI agent configuration service
        config_service = await get_ai_agent_config_service()
        
        # Get existing configuration
        existing_config = await config_service.get_config(config_id)
        
        if not existing_config:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")
        
        # Process updates
        enabled_services = existing_config.enabled_services
        if config_update.enabled_services is not None:
            enabled_services = {AIServiceType(s) for s in config_update.enabled_services}
        
        context_sharing = existing_config.context_sharing
        if config_update.context_sharing is not None:
            context_sharing = {
                AIServiceType(k): ContextSharingLevel(v)
                for k, v in config_update.context_sharing.items()
            }
        
        rate_limits = existing_config.rate_limits
        if config_update.rate_limits is not None:
            rate_limits = {
                AIServiceType(k): v
                for k, v in config_update.rate_limits.items()
            }
        
        # Update configuration
        updated_config = AIAgentConfig(
            id=config_id,
            name=config_update.name or existing_config.name,
            description=config_update.description or existing_config.description,
            user_id=existing_config.user_id,
            project_id=existing_config.project_id,
            enabled_services=enabled_services,
            context_sharing=context_sharing,
            rate_limits=rate_limits,
            custom_instructions=config_update.custom_instructions if config_update.custom_instructions is not None else existing_config.custom_instructions,
            prompt_templates=config_update.prompt_templates or existing_config.prompt_templates,
            auto_analyze_deployments=config_update.auto_analyze_deployments if config_update.auto_analyze_deployments is not None else existing_config.auto_analyze_deployments,
            auto_analyze_errors=config_update.auto_analyze_errors if config_update.auto_analyze_errors is not None else existing_config.auto_analyze_errors,
            created_at=existing_config.created_at,
        )
        
        # Update configuration
        updated_config = await config_service.update_config(updated_config)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "ai_agent_config_api",
            "operation": "update",
            "config_id": config_id,
            "user_id": updated_config.user_id,
            "project_id": updated_config.project_id,
        })
        
        return AIAgentConfigResponse(**updated_config.to_dict())
    except ValueError as e:
        logger.error(f"Error updating AI agent configuration {config_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating AI agent configuration {config_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/configs/{config_id}")
async def delete_config(
    config_id: str = Path(..., description="ID of the configuration to delete"),
):
    """
    Delete an AI agent configuration.
    
    Args:
        config_id: ID of the configuration to delete
        
    Returns:
        Success message
    """
    try:
        # Get AI agent configuration service
        config_service = await get_ai_agent_config_service()
        
        # Get existing configuration for logging
        existing_config = await config_service.get_config(config_id)
        
        if not existing_config:
            raise HTTPException(status_code=404, detail=f"Configuration {config_id} not found")
        
        # Delete configuration
        success = await config_service.delete_config(config_id)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to delete configuration {config_id}")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "ai_agent_config_api",
            "operation": "delete",
            "config_id": config_id,
            "user_id": existing_config.user_id,
            "project_id": existing_config.project_id,
        })
        
        return {"message": f"Configuration {config_id} deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting AI agent configuration {config_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/configs", response_model=List[AIAgentConfigResponse])
async def list_configs(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
):
    """
    List AI agent configurations.
    
    Args:
        user_id: Filter by user ID
        project_id: Filter by project ID
        
    Returns:
        List of AI agent configurations
    """
    try:
        # Get AI agent configuration service
        config_service = await get_ai_agent_config_service()
        
        # List configurations
        configs = await config_service.list_configs(
            user_id=user_id,
            project_id=project_id,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "ai_agent_config_api",
            "operation": "list",
            "user_id": user_id,
            "project_id": project_id,
            "count": len(configs),
        })
        
        return [AIAgentConfigResponse(**config.to_dict()) for config in configs]
    except Exception as e:
        logger.error(f"Error listing AI agent configurations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/configs/default")
async def create_default_config(
    user_id: str = Query(..., description="ID of the user who owns the configuration"),
    project_id: str = Query(..., description="ID of the project the configuration is for"),
    name: str = Query("Default Configuration", description="Configuration name"),
):
    """
    Create a default AI agent configuration.
    
    Args:
        user_id: ID of the user who owns the configuration
        project_id: ID of the project the configuration is for
        name: Configuration name
        
    Returns:
        Created AI agent configuration
    """
    try:
        # Get AI agent configuration service
        config_service = await get_ai_agent_config_service()
        
        # Check if configuration already exists
        existing_config = await config_service.get_config_for_project(project_id)
        
        if existing_config:
            return AIAgentConfigResponse(**existing_config.to_dict())
        
        # Create default configuration
        config = AIAgentConfig.create_default(
            user_id=user_id,
            project_id=project_id,
            name=name,
        )
        
        # Store configuration
        created_config = await config_service.create_config(config)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "ai_agent_config_api",
            "operation": "create_default",
            "config_id": created_config.id,
            "user_id": user_id,
            "project_id": project_id,
        })
        
        return AIAgentConfigResponse(**created_config.to_dict())
    except Exception as e:
        logger.error(f"Error creating default AI agent configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
