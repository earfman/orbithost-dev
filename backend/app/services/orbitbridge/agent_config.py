"""
AI agent configuration service for OrbitBridge.

This module provides functionality for managing AI agent configurations,
including which services are enabled, context sharing preferences,
prompt templates, and integration settings.
"""
import json
import logging
import os
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

class AIServiceType(str, Enum):
    """Types of AI services supported by OrbitBridge."""
    CLAUDE = "claude"
    REPLIT = "replit"
    CURSOR = "cursor"
    WINDSURF = "windsurf"

class ContextSharingLevel(str, Enum):
    """Levels of context sharing with AI services."""
    NONE = "none"  # No context sharing
    MINIMAL = "minimal"  # Only basic metadata
    STANDARD = "standard"  # Logs and errors without sensitive data
    FULL = "full"  # All available context including screenshots and DOM

class PromptTemplate:
    """Model for AI prompt templates."""
    
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        service_type: AIServiceType,
        template_text: str,
        variables: List[str],
        created_at: datetime = None,
        updated_at: datetime = None,
    ):
        """
        Initialize a prompt template.
        
        Args:
            id: Template ID
            name: Template name
            description: Template description
            service_type: Type of AI service this template is for
            template_text: The prompt template text with variables
            variables: List of variable names used in the template
            created_at: Creation timestamp
            updated_at: Last update timestamp
        """
        self.id = id
        self.name = name
        self.description = description
        self.service_type = service_type
        self.template_text = template_text
        self.variables = variables
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "service_type": self.service_type.value,
            "template_text": self.template_text,
            "variables": self.variables,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptTemplate":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            service_type=AIServiceType(data["service_type"]),
            template_text=data["template_text"],
            variables=data["variables"],
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else None,
        )

class AIAgentConfig:
    """Model for AI agent configuration."""
    
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        user_id: str,
        project_id: str,
        enabled_services: Set[AIServiceType],
        context_sharing: Dict[AIServiceType, ContextSharingLevel],
        rate_limits: Dict[AIServiceType, int],
        custom_instructions: Optional[str] = None,
        prompt_templates: Optional[Dict[str, str]] = None,
        auto_analyze_deployments: bool = True,
        auto_analyze_errors: bool = True,
        created_at: datetime = None,
        updated_at: datetime = None,
    ):
        """
        Initialize an AI agent configuration.
        
        Args:
            id: Configuration ID
            name: Configuration name
            description: Configuration description
            user_id: ID of the user who owns the configuration
            project_id: ID of the project the configuration is for
            enabled_services: Set of enabled AI services
            context_sharing: Dictionary mapping AI services to context sharing levels
            rate_limits: Dictionary mapping AI services to rate limits (calls per hour)
            custom_instructions: Custom instructions for AI agents
            prompt_templates: Dictionary mapping template IDs to prompt template IDs
            auto_analyze_deployments: Whether to automatically analyze deployments
            auto_analyze_errors: Whether to automatically analyze errors
            created_at: Creation timestamp
            updated_at: Last update timestamp
        """
        self.id = id
        self.name = name
        self.description = description
        self.user_id = user_id
        self.project_id = project_id
        self.enabled_services = enabled_services
        self.context_sharing = context_sharing
        self.rate_limits = rate_limits
        self.custom_instructions = custom_instructions
        self.prompt_templates = prompt_templates or {}
        self.auto_analyze_deployments = auto_analyze_deployments
        self.auto_analyze_errors = auto_analyze_errors
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "enabled_services": [s.value for s in self.enabled_services],
            "context_sharing": {k.value: v.value for k, v in self.context_sharing.items()},
            "rate_limits": {k.value: v for k, v in self.rate_limits.items()},
            "custom_instructions": self.custom_instructions,
            "prompt_templates": self.prompt_templates,
            "auto_analyze_deployments": self.auto_analyze_deployments,
            "auto_analyze_errors": self.auto_analyze_errors,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIAgentConfig":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            user_id=data["user_id"],
            project_id=data["project_id"],
            enabled_services={AIServiceType(s) for s in data["enabled_services"]},
            context_sharing={AIServiceType(k): ContextSharingLevel(v) for k, v in data["context_sharing"].items()},
            rate_limits={AIServiceType(k): v for k, v in data["rate_limits"].items()},
            custom_instructions=data.get("custom_instructions"),
            prompt_templates=data.get("prompt_templates", {}),
            auto_analyze_deployments=data.get("auto_analyze_deployments", True),
            auto_analyze_errors=data.get("auto_analyze_errors", True),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else None,
        )
    
    @classmethod
    def create_default(cls, user_id: str, project_id: str, name: str = "Default Configuration") -> "AIAgentConfig":
        """
        Create a default AI agent configuration.
        
        Args:
            user_id: ID of the user who owns the configuration
            project_id: ID of the project the configuration is for
            name: Configuration name
            
        Returns:
            Default AI agent configuration
        """
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            description="Default AI agent configuration",
            user_id=user_id,
            project_id=project_id,
            enabled_services={
                AIServiceType.CLAUDE,
                AIServiceType.WINDSURF,
            },
            context_sharing={
                AIServiceType.CLAUDE: ContextSharingLevel.STANDARD,
                AIServiceType.REPLIT: ContextSharingLevel.MINIMAL,
                AIServiceType.CURSOR: ContextSharingLevel.STANDARD,
                AIServiceType.WINDSURF: ContextSharingLevel.FULL,
            },
            rate_limits={
                AIServiceType.CLAUDE: 100,
                AIServiceType.REPLIT: 50,
                AIServiceType.CURSOR: 50,
                AIServiceType.WINDSURF: 200,
            },
            custom_instructions=None,
            prompt_templates={},
            auto_analyze_deployments=True,
            auto_analyze_errors=True,
        )

class AIAgentConfigService:
    """
    Service for managing AI agent configurations.
    
    This service provides functionality for creating, retrieving, updating,
    and deleting AI agent configurations, as well as managing prompt templates.
    """
    
    def __init__(self):
        """Initialize the AI agent configuration service."""
        # In a real implementation, configurations would be stored in a database
        # For now, we'll use in-memory dictionaries
        self.configs: Dict[str, AIAgentConfig] = {}
        self.templates: Dict[str, PromptTemplate] = {}
        
        # Add some default templates
        self._add_default_templates()
        
        logger.info("Initialized AI agent configuration service")
    
    def _add_default_templates(self):
        """Add default prompt templates."""
        # Deployment analysis template for Claude
        deployment_analysis_template = PromptTemplate(
            id=str(uuid.uuid4()),
            name="Deployment Analysis",
            description="Template for analyzing deployments",
            service_type=AIServiceType.CLAUDE,
            template_text="""
            Analyze the following deployment:
            
            Repository: {{repository}}
            Branch: {{branch}}
            Commit: {{commit_sha}}
            Author: {{author}}
            Commit Message: {{commit_message}}
            
            Deployment Status: {{status}}
            Deployment URL: {{url}}
            
            Please provide:
            1. A summary of the changes in this deployment
            2. Potential issues or concerns
            3. Recommendations for improvement
            
            {{custom_instructions}}
            """,
            variables=["repository", "branch", "commit_sha", "author", "commit_message", "status", "url", "custom_instructions"],
        )
        
        # Error analysis template for Claude
        error_analysis_template = PromptTemplate(
            id=str(uuid.uuid4()),
            name="Error Analysis",
            description="Template for analyzing errors",
            service_type=AIServiceType.CLAUDE,
            template_text="""
            Analyze the following error:
            
            Error Type: {{error_type}}
            Error Message: {{error_message}}
            Stack Trace:
            {{stack_trace}}
            
            Code Context:
            ```{{language}}
            {{code}}
            ```
            
            Please provide:
            1. A clear explanation of the error
            2. Potential causes
            3. Suggested fixes
            
            {{custom_instructions}}
            """,
            variables=["error_type", "error_message", "stack_trace", "language", "code", "custom_instructions"],
        )
        
        # Performance recommendations template for Claude
        performance_template = PromptTemplate(
            id=str(uuid.uuid4()),
            name="Performance Recommendations",
            description="Template for generating performance recommendations",
            service_type=AIServiceType.CLAUDE,
            template_text="""
            Analyze the following performance metrics:
            
            {{metrics}}
            
            Please provide:
            1. Key performance insights
            2. Bottlenecks and areas for improvement
            3. Specific recommendations to enhance performance
            
            {{custom_instructions}}
            """,
            variables=["metrics", "custom_instructions"],
        )
        
        # Add templates to dictionary
        self.templates[deployment_analysis_template.id] = deployment_analysis_template
        self.templates[error_analysis_template.id] = error_analysis_template
        self.templates[performance_template.id] = performance_template
    
    async def create_config(self, config: AIAgentConfig) -> AIAgentConfig:
        """
        Create a new AI agent configuration.
        
        Args:
            config: AI agent configuration to create
            
        Returns:
            Created AI agent configuration
        """
        # Store configuration
        self.configs[config.id] = config
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "ai_agent_config",
            "operation": "create",
            "config_id": config.id,
            "user_id": config.user_id,
            "project_id": config.project_id,
            "enabled_services": [s.value for s in config.enabled_services],
        })
        
        logger.info(f"Created AI agent configuration {config.id}")
        
        return config
    
    async def get_config(self, config_id: str) -> Optional[AIAgentConfig]:
        """
        Get an AI agent configuration by ID.
        
        Args:
            config_id: ID of the configuration to get
            
        Returns:
            AI agent configuration or None if not found
        """
        return self.configs.get(config_id)
    
    async def get_config_for_project(self, project_id: str) -> Optional[AIAgentConfig]:
        """
        Get an AI agent configuration for a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            AI agent configuration or None if not found
        """
        for config in self.configs.values():
            if config.project_id == project_id:
                return config
        
        return None
    
    async def update_config(self, config: AIAgentConfig) -> AIAgentConfig:
        """
        Update an AI agent configuration.
        
        Args:
            config: AI agent configuration to update
            
        Returns:
            Updated AI agent configuration
        """
        # Check if configuration exists
        if config.id not in self.configs:
            raise ValueError(f"Configuration {config.id} not found")
        
        # Update configuration
        config.updated_at = datetime.utcnow()
        self.configs[config.id] = config
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "ai_agent_config",
            "operation": "update",
            "config_id": config.id,
            "user_id": config.user_id,
            "project_id": config.project_id,
            "enabled_services": [s.value for s in config.enabled_services],
        })
        
        logger.info(f"Updated AI agent configuration {config.id}")
        
        return config
    
    async def delete_config(self, config_id: str) -> bool:
        """
        Delete an AI agent configuration.
        
        Args:
            config_id: ID of the configuration to delete
            
        Returns:
            Boolean indicating success or failure
        """
        # Check if configuration exists
        if config_id not in self.configs:
            return False
        
        # Get configuration for logging
        config = self.configs[config_id]
        
        # Delete configuration
        del self.configs[config_id]
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "ai_agent_config",
            "operation": "delete",
            "config_id": config_id,
            "user_id": config.user_id,
            "project_id": config.project_id,
        })
        
        logger.info(f"Deleted AI agent configuration {config_id}")
        
        return True
    
    async def list_configs(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> List[AIAgentConfig]:
        """
        List AI agent configurations.
        
        Args:
            user_id: Filter by user ID
            project_id: Filter by project ID
            
        Returns:
            List of AI agent configurations
        """
        configs = list(self.configs.values())
        
        # Apply filters
        if user_id:
            configs = [c for c in configs if c.user_id == user_id]
        
        if project_id:
            configs = [c for c in configs if c.project_id == project_id]
        
        return configs
    
    async def create_template(self, template: PromptTemplate) -> PromptTemplate:
        """
        Create a new prompt template.
        
        Args:
            template: Prompt template to create
            
        Returns:
            Created prompt template
        """
        # Store template
        self.templates[template.id] = template
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "prompt_template",
            "operation": "create",
            "template_id": template.id,
            "service_type": template.service_type.value,
        })
        
        logger.info(f"Created prompt template {template.id}")
        
        return template
    
    async def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """
        Get a prompt template by ID.
        
        Args:
            template_id: ID of the template to get
            
        Returns:
            Prompt template or None if not found
        """
        return self.templates.get(template_id)
    
    async def update_template(self, template: PromptTemplate) -> PromptTemplate:
        """
        Update a prompt template.
        
        Args:
            template: Prompt template to update
            
        Returns:
            Updated prompt template
        """
        # Check if template exists
        if template.id not in self.templates:
            raise ValueError(f"Template {template.id} not found")
        
        # Update template
        template.updated_at = datetime.utcnow()
        self.templates[template.id] = template
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "prompt_template",
            "operation": "update",
            "template_id": template.id,
            "service_type": template.service_type.value,
        })
        
        logger.info(f"Updated prompt template {template.id}")
        
        return template
    
    async def delete_template(self, template_id: str) -> bool:
        """
        Delete a prompt template.
        
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
            "type": "prompt_template",
            "operation": "delete",
            "template_id": template_id,
            "service_type": template.service_type.value,
        })
        
        logger.info(f"Deleted prompt template {template_id}")
        
        return True
    
    async def list_templates(
        self,
        service_type: Optional[AIServiceType] = None,
    ) -> List[PromptTemplate]:
        """
        List prompt templates.
        
        Args:
            service_type: Filter by service type
            
        Returns:
            List of prompt templates
        """
        templates = list(self.templates.values())
        
        # Apply filters
        if service_type:
            templates = [t for t in templates if t.service_type == service_type]
        
        return templates
    
    async def render_prompt(
        self,
        template_id: str,
        variables: Dict[str, Any],
    ) -> str:
        """
        Render a prompt template with variables.
        
        Args:
            template_id: ID of the template to render
            variables: Dictionary of variables to substitute
            
        Returns:
            Rendered prompt
        """
        # Get template
        template = await self.get_template(template_id)
        
        if not template:
            raise ValueError(f"Template {template_id} not found")
        
        # Render template
        rendered = template.template_text
        
        for var_name, var_value in variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            rendered = rendered.replace(placeholder, str(var_value))
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "prompt_render",
            "template_id": template_id,
            "service_type": template.service_type.value,
        })
        
        return rendered
    
    async def should_analyze_deployment(self, project_id: str) -> bool:
        """
        Check if deployments should be automatically analyzed for a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Boolean indicating whether deployments should be automatically analyzed
        """
        config = await self.get_config_for_project(project_id)
        
        if not config:
            # Default to True if no configuration exists
            return True
        
        return config.auto_analyze_deployments
    
    async def should_analyze_error(self, project_id: str) -> bool:
        """
        Check if errors should be automatically analyzed for a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Boolean indicating whether errors should be automatically analyzed
        """
        config = await self.get_config_for_project(project_id)
        
        if not config:
            # Default to True if no configuration exists
            return True
        
        return config.auto_analyze_errors
    
    async def get_context_sharing_level(
        self,
        project_id: str,
        service_type: AIServiceType,
    ) -> ContextSharingLevel:
        """
        Get the context sharing level for a service and project.
        
        Args:
            project_id: ID of the project
            service_type: Type of AI service
            
        Returns:
            Context sharing level
        """
        config = await self.get_config_for_project(project_id)
        
        if not config:
            # Default to standard if no configuration exists
            return ContextSharingLevel.STANDARD
        
        return config.context_sharing.get(service_type, ContextSharingLevel.STANDARD)
    
    async def is_service_enabled(
        self,
        project_id: str,
        service_type: AIServiceType,
    ) -> bool:
        """
        Check if a service is enabled for a project.
        
        Args:
            project_id: ID of the project
            service_type: Type of AI service
            
        Returns:
            Boolean indicating whether the service is enabled
        """
        config = await self.get_config_for_project(project_id)
        
        if not config:
            # Default to True for Claude and Windsurf, False for others
            return service_type in {AIServiceType.CLAUDE, AIServiceType.WINDSURF}
        
        return service_type in config.enabled_services
    
    async def get_custom_instructions(self, project_id: str) -> Optional[str]:
        """
        Get custom instructions for a project.
        
        Args:
            project_id: ID of the project
            
        Returns:
            Custom instructions or None if not set
        """
        config = await self.get_config_for_project(project_id)
        
        if not config:
            return None
        
        return config.custom_instructions
    
    async def get_prompt_template_id(
        self,
        project_id: str,
        template_name: str,
    ) -> Optional[str]:
        """
        Get the prompt template ID for a template name and project.
        
        Args:
            project_id: ID of the project
            template_name: Name of the template
            
        Returns:
            Prompt template ID or None if not set
        """
        config = await self.get_config_for_project(project_id)
        
        if not config:
            return None
        
        return config.prompt_templates.get(template_name)


# Global AI agent configuration service instance
_ai_agent_config_service = None

async def get_ai_agent_config_service() -> AIAgentConfigService:
    """
    Get the AI agent configuration service instance.
    
    Returns:
        AI agent configuration service instance
    """
    global _ai_agent_config_service
    
    if _ai_agent_config_service is None:
        _ai_agent_config_service = AIAgentConfigService()
    
    return _ai_agent_config_service
