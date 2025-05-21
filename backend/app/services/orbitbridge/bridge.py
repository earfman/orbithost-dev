"""
OrbitBridge service for connecting OrbitContext data with AI tools.

This service provides the integration layer that connects OrbitContext data
from OrbitHost, OrbitDeploy, and OrbitLogs with AI tools like Windsurf,
Claude, Replit, and Cursor.
"""
import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Set, Union

from app.services.ai.claude_service import ClaudeService
from app.services.ai.cursor_service import CursorService
from app.services.ai.replit_service import ReplitService
from app.services.orbitbridge.context import OrbitContext, ContextType
from app.utils.mcp.client import get_mcp_client, MCPConfig

logger = logging.getLogger(__name__)

class OrbitBridge:
    """
    OrbitBridge service for connecting OrbitContext data with AI tools.
    
    This service provides the integration layer that connects OrbitContext data
    from OrbitHost, OrbitDeploy, and OrbitLogs with AI tools like Windsurf,
    Claude, Replit, and Cursor.
    """
    
    def __init__(
        self,
        project_id: str,
        environment: str,
        user_id: Optional[str] = None,
        claude_api_key: Optional[str] = None,
        replit_api_key: Optional[str] = None,
        cursor_api_key: Optional[str] = None,
        mcp_config: Optional[MCPConfig] = None,
    ):
        """
        Initialize the OrbitBridge service.
        
        Args:
            project_id: ID of the project
            environment: Environment (development, staging, production)
            user_id: ID of the user
            claude_api_key: API key for Claude
            replit_api_key: API key for Replit
            cursor_api_key: API key for Cursor
            mcp_config: Configuration for Windsurf MCP
        """
        self.project_id = project_id
        self.environment = environment
        self.user_id = user_id
        
        # Initialize MCP client
        self.mcp_client = get_mcp_client(mcp_config)
        
        # Initialize AI services if API keys are provided
        self.claude_service = ClaudeService(api_key=claude_api_key) if claude_api_key else None
        self.replit_service = ReplitService(api_key=replit_api_key) if replit_api_key else None
        self.cursor_service = CursorService(api_key=cursor_api_key) if cursor_api_key else None
        
        # Context storage
        self.contexts: Dict[str, OrbitContext] = {}
        self.context_by_type: Dict[ContextType, Set[str]] = {
            context_type: set() for context_type in ContextType
        }
        
        logger.info(f"Initialized OrbitBridge for project {project_id} in {environment}")
    
    async def initialize_ai_services(self):
        """Initialize AI services."""
        initialization_tasks = []
        
        if self.claude_service:
            initialization_tasks.append(self.claude_service.initialize())
        
        if self.replit_service:
            initialization_tasks.append(self.replit_service.initialize())
        
        if self.cursor_service:
            initialization_tasks.append(self.cursor_service.initialize())
        
        if initialization_tasks:
            await asyncio.gather(*initialization_tasks)
            logger.info("AI services initialized")
    
    async def store_context(self, context: OrbitContext):
        """
        Store an OrbitContext.
        
        Args:
            context: OrbitContext to store
        """
        # Store context
        self.contexts[context.id] = context
        self.context_by_type[context.type].add(context.id)
        
        # Log to MCP
        await self.mcp_client.send({
            "type": "orbit_context",
            "context_id": context.id,
            "context_type": context.type,
            "project_id": context.project_id,
            "environment": context.environment,
        })
        
        logger.info(f"Stored {context.type} context {context.id}")
        
        # Process context based on type
        await self._process_context(context)
    
    async def _process_context(self, context: OrbitContext):
        """
        Process an OrbitContext based on its type.
        
        Args:
            context: OrbitContext to process
        """
        if context.type == ContextType.DEPLOYMENT:
            await self._process_deployment_context(context)
        elif context.type == ContextType.ERROR:
            await self._process_error_context(context)
        elif context.type == ContextType.SCREENSHOT:
            await self._process_screenshot_context(context)
        elif context.type == ContextType.LOG:
            await self._process_log_context(context)
        elif context.type == ContextType.METRIC:
            await self._process_metric_context(context)
        elif context.type == ContextType.TRACE:
            await self._process_trace_context(context)
    
    async def _process_deployment_context(self, context: OrbitContext):
        """
        Process a deployment context.
        
        Args:
            context: Deployment context to process
        """
        if not context.deployment:
            return
        
        # Generate deployment summary with Claude if available
        if self.claude_service:
            try:
                summary = await self.claude_service.summarize_deployment(
                    deployment_data={
                        "project": {
                            "id": context.project_id,
                            "name": context.metadata.get("project_name", "Unknown Project"),
                        },
                        "environment": context.environment,
                        "status": {
                            "state": context.deployment.status,
                            "duration_seconds": context.deployment.duration_seconds,
                        },
                        "changes": context.metadata.get("changes", []),
                        "metrics": context.metadata.get("metrics", {}),
                    }
                )
                
                # Store summary in context metadata
                context.metadata["ai_summary"] = summary.get("text", "")
                
                logger.info(f"Generated AI summary for deployment {context.deployment.id}")
            except Exception as e:
                logger.error(f"Error generating deployment summary: {str(e)}")
    
    async def _process_error_context(self, context: OrbitContext):
        """
        Process an error context.
        
        Args:
            context: Error context to process
        """
        if not context.error or not context.error_location:
            return
        
        # Analyze error with Claude if available
        if self.claude_service:
            try:
                # Extract code from metadata if available
                code = context.metadata.get("code", "")
                language = context.metadata.get("language", "")
                
                if code:
                    analysis = await self.claude_service.analyze_code(code, language)
                    
                    # Store analysis in context metadata
                    context.metadata["ai_analysis"] = analysis.get("text", "")
                    
                    logger.info(f"Generated AI analysis for error in {context.error_location.file}")
            except Exception as e:
                logger.error(f"Error analyzing code: {str(e)}")
    
    async def _process_screenshot_context(self, context: OrbitContext):
        """
        Process a screenshot context.
        
        Args:
            context: Screenshot context to process
        """
        # Currently no specific processing for screenshots
        pass
    
    async def _process_log_context(self, context: OrbitContext):
        """
        Process a log context.
        
        Args:
            context: Log context to process
        """
        # Currently no specific processing for logs
        pass
    
    async def _process_metric_context(self, context: OrbitContext):
        """
        Process a metric context.
        
        Args:
            context: Metric context to process
        """
        # Currently no specific processing for metrics
        pass
    
    async def _process_trace_context(self, context: OrbitContext):
        """
        Process a trace context.
        
        Args:
            context: Trace context to process
        """
        # Currently no specific processing for traces
        pass
    
    async def get_context(self, context_id: str) -> Optional[OrbitContext]:
        """
        Get an OrbitContext by ID.
        
        Args:
            context_id: ID of the context to get
            
        Returns:
            OrbitContext or None if not found
        """
        return self.contexts.get(context_id)
    
    async def get_contexts_by_type(
        self,
        context_type: ContextType,
        limit: int = 10,
        offset: int = 0,
    ) -> List[OrbitContext]:
        """
        Get OrbitContexts by type.
        
        Args:
            context_type: Type of contexts to get
            limit: Maximum number of contexts to return
            offset: Offset for pagination
            
        Returns:
            List of OrbitContexts
        """
        context_ids = list(self.context_by_type[context_type])
        context_ids.sort(reverse=True)  # Sort by ID (newest first)
        
        paginated_ids = context_ids[offset:offset + limit]
        
        return [self.contexts[context_id] for context_id in paginated_ids]
    
    async def get_latest_deployment(self) -> Optional[OrbitContext]:
        """
        Get the latest deployment context.
        
        Returns:
            Latest deployment context or None if not found
        """
        deployment_ids = list(self.context_by_type[ContextType.DEPLOYMENT])
        
        if not deployment_ids:
            return None
        
        # Sort by timestamp (newest first)
        sorted_ids = sorted(
            deployment_ids,
            key=lambda id: self.contexts[id].timestamp,
            reverse=True
        )
        
        return self.contexts[sorted_ids[0]] if sorted_ids else None
    
    async def get_latest_error(self) -> Optional[OrbitContext]:
        """
        Get the latest error context.
        
        Returns:
            Latest error context or None if not found
        """
        error_ids = list(self.context_by_type[ContextType.ERROR])
        
        if not error_ids:
            return None
        
        # Sort by timestamp (newest first)
        sorted_ids = sorted(
            error_ids,
            key=lambda id: self.contexts[id].timestamp,
            reverse=True
        )
        
        return self.contexts[sorted_ids[0]] if sorted_ids else None
    
    async def generate_code_fix(
        self,
        error_context_id: str,
        file_path: str,
        code: str,
        language: str,
    ) -> Dict[str, Any]:
        """
        Generate a code fix for an error using AI tools.
        
        Args:
            error_context_id: ID of the error context
            file_path: Path to the file with the error
            code: Code with the error
            language: Programming language
            
        Returns:
            Generated code fix
        """
        error_context = await self.get_context(error_context_id)
        
        if not error_context or error_context.type != ContextType.ERROR:
            raise ValueError(f"Invalid error context ID: {error_context_id}")
        
        # Use Cursor for code editing if available
        if self.cursor_service:
            try:
                error_message = error_context.error.get("message", "")
                error_type = error_context.error.get("type", "")
                
                instruction = f"Fix the {error_type} error: {error_message}"
                
                fix = await self.cursor_service.edit_code(
                    code=code,
                    instruction=instruction,
                    language=language,
                    context=f"File: {file_path}\nError: {error_message}"
                )
                
                return {
                    "fixed_code": fix.get("edited_code", ""),
                    "explanation": fix.get("explanation", ""),
                    "diff": fix.get("diff", ""),
                    "tool": "cursor",
                }
            except Exception as e:
                logger.error(f"Error generating code fix with Cursor: {str(e)}")
        
        # Fall back to Claude if Cursor is not available
        if self.claude_service:
            try:
                error_message = error_context.error.get("message", "")
                error_type = error_context.error.get("type", "")
                
                prompt = f"""
                Fix the following code that has a {error_type} error: {error_message}
                
                File: {file_path}
                Language: {language}
                
                ```{language}
                {code}
                ```
                
                Please provide the fixed code and explain what was wrong and how you fixed it.
                """
                
                system_prompt = "You are an expert code fixer. Focus on fixing the specific error mentioned while making minimal changes to the code. Explain your changes clearly."
                
                result = await self.claude_service.generate_text(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=2000,
                    temperature=0.2,
                )
                
                # Extract code from the response
                response_text = result.get("text", "")
                
                # Simple code block extraction
                if "```" in response_text:
                    code_blocks = response_text.split("```")
                    fixed_code = code_blocks[1].strip()
                    if language in fixed_code:
                        fixed_code = fixed_code.replace(language, "", 1).strip()
                else:
                    fixed_code = ""
                
                return {
                    "fixed_code": fixed_code,
                    "explanation": response_text,
                    "diff": "",
                    "tool": "claude",
                }
            except Exception as e:
                logger.error(f"Error generating code fix with Claude: {str(e)}")
        
        return {
            "error": "No AI service available for generating code fixes",
            "fixed_code": "",
            "explanation": "",
            "diff": "",
            "tool": "none",
        }
    
    async def generate_deployment_feedback(
        self,
        deployment_context_id: str,
    ) -> Dict[str, Any]:
        """
        Generate feedback for a deployment using AI tools.
        
        Args:
            deployment_context_id: ID of the deployment context
            
        Returns:
            Generated deployment feedback
        """
        deployment_context = await self.get_context(deployment_context_id)
        
        if not deployment_context or deployment_context.type != ContextType.DEPLOYMENT:
            raise ValueError(f"Invalid deployment context ID: {deployment_context_id}")
        
        # Use Claude for deployment feedback if available
        if self.claude_service:
            try:
                # Get deployment data
                deployment = deployment_context.deployment
                
                # Get related contexts
                related_errors = []
                for context_id in deployment_context.related_contexts:
                    context = await self.get_context(context_id)
                    if context and context.type == ContextType.ERROR:
                        related_errors.append(context)
                
                # Create prompt
                prompt = f"""
                Generate feedback for the following deployment:
                
                Project: {deployment_context.metadata.get("project_name", "Unknown Project")}
                Environment: {deployment_context.environment}
                Branch: {deployment.branch}
                Commit: {deployment.commit_hash}
                Commit Message: {deployment.commit_message or "N/A"}
                Status: {deployment.status}
                Duration: {deployment.duration_seconds} seconds
                
                """
                
                if related_errors:
                    prompt += "Related Errors:\n"
                    for i, error in enumerate(related_errors, 1):
                        error_message = error.error.get("message", "Unknown error")
                        error_location = error.error_location
                        file_path = error_location.file if error_location else "Unknown file"
                        line = error_location.line if error_location else "Unknown line"
                        
                        prompt += f"{i}. {error_message} in {file_path}:{line}\n"
                
                prompt += "\nPlease provide feedback on this deployment, including any issues, performance concerns, and recommendations for improvement."
                
                system_prompt = "You are a deployment feedback assistant. Analyze the deployment data and provide actionable feedback to help improve the deployment process and application quality."
                
                result = await self.claude_service.generate_text(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=1500,
                    temperature=0.3,
                )
                
                return {
                    "feedback": result.get("text", ""),
                    "tool": "claude",
                }
            except Exception as e:
                logger.error(f"Error generating deployment feedback: {str(e)}")
        
        return {
            "error": "No AI service available for generating deployment feedback",
            "feedback": "",
            "tool": "none",
        }
    
    async def close(self):
        """Close the OrbitBridge service."""
        # Close AI services
        close_tasks = []
        
        if self.claude_service and hasattr(self.claude_service, "close"):
            close_tasks.append(self.claude_service.close())
        
        if self.replit_service and hasattr(self.replit_service, "close"):
            close_tasks.append(self.replit_service.close())
        
        if self.cursor_service and hasattr(self.cursor_service, "close"):
            close_tasks.append(self.cursor_service.close())
        
        if close_tasks:
            await asyncio.gather(*close_tasks)
        
        # Close MCP client
        if self.mcp_client:
            await self.mcp_client.close()
        
        logger.info(f"Closed OrbitBridge for project {self.project_id}")


# Global OrbitBridge instance
_orbit_bridge = None

async def get_orbit_bridge(
    project_id: str = None,
    environment: str = None,
    user_id: str = None,
) -> OrbitBridge:
    """
    Get the OrbitBridge instance.
    
    Args:
        project_id: ID of the project
        environment: Environment (development, staging, production)
        user_id: ID of the user
        
    Returns:
        OrbitBridge instance
    """
    global _orbit_bridge
    
    if _orbit_bridge is None:
        # Get configuration from environment variables if not provided
        project_id = project_id or os.getenv("ORBIT_PROJECT_ID")
        environment = environment or os.getenv("ORBIT_ENVIRONMENT", "development")
        user_id = user_id or os.getenv("ORBIT_USER_ID")
        
        # Get API keys from environment variables
        claude_api_key = os.getenv("CLAUDE_API_KEY")
        replit_api_key = os.getenv("REPLIT_API_KEY")
        cursor_api_key = os.getenv("CURSOR_API_KEY")
        
        # Create OrbitBridge instance
        _orbit_bridge = OrbitBridge(
            project_id=project_id,
            environment=environment,
            user_id=user_id,
            claude_api_key=claude_api_key,
            replit_api_key=replit_api_key,
            cursor_api_key=cursor_api_key,
        )
        
        # Initialize AI services
        await _orbit_bridge.initialize_ai_services()
    
    return _orbit_bridge
