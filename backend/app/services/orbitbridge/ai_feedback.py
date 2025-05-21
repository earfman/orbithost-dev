"""
AI feedback services for deployments and error analysis.

This module provides AI-powered feedback on deployments and error analysis,
leveraging the OrbitContext data and AI tools integrated through OrbitBridge.
"""
import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Set, Union

from app.services.ai.claude_service import ClaudeService
from app.services.ai.cursor_service import CursorService
from app.services.ai.replit_service import ReplitService
from app.services.orbitbridge.context import OrbitContext, ContextType
from app.services.orbitbridge.bridge import get_orbit_bridge
from app.services.orbitbridge.mcp_client import MCPClient, MCPResourceType, MCPTool
from app.services.orbitbridge.enhanced_context import EnhancedOrbitContext
from app.services.orbitbridge.windsurf_discovery import get_windsurf_mcp_url

logger = logging.getLogger(__name__)

class AIFeedbackService:
    """
    AI feedback service for deployments and error analysis.
    
    This service provides AI-powered feedback on deployments and error analysis,
    leveraging the OrbitContext data and AI tools integrated through OrbitBridge.
    It uses the universal MCP client to interact with any MCP-compatible AI tool.
    """
    
    def __init__(
        self,
        claude_service: Optional[ClaudeService] = None,
        cursor_service: Optional[CursorService] = None,
        replit_service: Optional[ReplitService] = None,
        mcp_client: Optional[MCPClient] = None,
    ):
        """
        Initialize the AI feedback service.
        
        Args:
            claude_service: Claude AI service
            cursor_service: Cursor AI service
            replit_service: Replit AI service
            mcp_client: MCP client for universal AI tool integration
        """
        self.claude_service = claude_service
        self.cursor_service = cursor_service
        self.replit_service = replit_service
        self._mcp_client = mcp_client
        
        logger.info("Initialized AI feedback service")
        
    async def get_mcp_client(self) -> MCPClient:
        """
        Get or create an MCP client.
        
        Returns:
            MCP client instance
        """
        if not self._mcp_client:
            # Try to auto-discover MCP endpoint
            mcp_url = os.environ.get("MCP_URL") or await get_windsurf_mcp_url()
            if not mcp_url:
                mcp_url = "http://localhost:8000/mcp"
                logger.warning(f"No MCP URL found, using default: {mcp_url}")
            
            api_key = os.environ.get("MCP_API_KEY")
            self._mcp_client = MCPClient(mcp_url=mcp_url, api_key=api_key)
            logger.info(f"Created MCP client with URL: {mcp_url}")
            
        return self._mcp_client
    
    async def analyze_deployment(
        self,
        deployment_context: OrbitContext,
        related_contexts: Optional[List[OrbitContext]] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a deployment and provide AI-powered feedback.
        
        Args:
            deployment_context: Deployment context to analyze
            related_contexts: Related contexts (errors, logs, etc.)
            
        Returns:
            AI-powered feedback on the deployment
        """
        if not deployment_context.deployment:
            raise ValueError("Invalid deployment context")
        
        # Convert OrbitContext to EnhancedOrbitContext
        enhanced_context = EnhancedOrbitContext.from_orbit_context(deployment_context)
        if related_contexts:
            for context in related_contexts:
                enhanced_context.add_related_context(EnhancedOrbitContext.from_orbit_context(context))
        
        # Try using MCP client first
        try:
            mcp_client = await self.get_mcp_client()
            
            # Discover available tools
            tools = await mcp_client.discover_tools()
            deployment_analysis_tools = [tool for tool in tools if "deployment" in tool.name.lower() and "analyze" in tool.name.lower()]
            
            if deployment_analysis_tools:
                # Use the first available deployment analysis tool
                tool = deployment_analysis_tools[0]
                logger.info(f"Using MCP tool for deployment analysis: {tool.name}")
                
                # Send context to MCP
                context_response = await mcp_client.send_context(enhanced_context)
                context_id = context_response.get("id")
                
                # Invoke the tool
                result = await mcp_client.invoke_tool(
                    tool.name,
                    {
                        "context_id": context_id,
                        "deployment_id": deployment_context.deployment.id,
                    }
                )
                
                # Extract feedback
                feedback = result.get("feedback") or result.get("analysis") or result.get("text", "")
                
                # Store feedback in deployment context metadata
                deployment_context.metadata["ai_feedback"] = feedback
                
                # Update context in OrbitBridge
                bridge = await get_orbit_bridge()
                await bridge.store_context(deployment_context)
                
                return {
                    "feedback": feedback,
                    "deployment_id": deployment_context.deployment.id,
                    "status": "success",
                    "tool": tool.name,
                }
            else:
                logger.info("No deployment analysis tools found in MCP, falling back to direct service calls")
        except Exception as e:
            logger.warning(f"Error using MCP for deployment analysis: {str(e)}. Falling back to direct service calls.")
        
        # Fall back to Claude if MCP fails or no suitable tools are found
        if self.claude_service:
            try:
                # Get deployment data
                deployment = deployment_context.deployment
                
                # Prepare related data
                related_errors = []
                related_logs = []
                related_metrics = []
                
                if related_contexts:
                    for context in related_contexts:
                        if context.type == ContextType.ERROR:
                            related_errors.append(context)
                        elif context.type == ContextType.LOG:
                            related_logs.append(context)
                        elif context.type == ContextType.METRIC:
                            related_metrics.append(context)
                
                # Create prompt
                prompt = f"""
                Analyze the following deployment and provide detailed feedback:
                
                Project: {deployment_context.metadata.get("project_name", "Unknown Project")}
                Environment: {deployment_context.environment}
                Branch: {deployment.branch}
                Commit: {deployment.commit_hash}
                Commit Message: {deployment.commit_message or "N/A"}
                Status: {deployment.status}
                Duration: {deployment.duration_seconds} seconds
                
                """
                
                if related_errors:
                    prompt += "## Related Errors:\n"
                    for i, error in enumerate(related_errors, 1):
                        error_message = error.error.get("message", "Unknown error")
                        error_location = error.error_location
                        file_path = error_location.file if error_location else "Unknown file"
                        line = error_location.line if error_location else "Unknown line"
                        
                        prompt += f"{i}. {error_message} in {file_path}:{line}\n"
                
                if related_logs:
                    prompt += "\n## Significant Logs:\n"
                    for i, log in enumerate(related_logs[:10], 1):  # Limit to 10 logs
                        prompt += f"{i}. [{log.log_severity}] {log.log_message}\n"
                
                if related_metrics:
                    prompt += "\n## Performance Metrics:\n"
                    for i, metric in enumerate(related_metrics, 1):
                        if metric.metric:
                            prompt += f"{i}. {metric.metric.name}: {metric.metric.value} {metric.metric.unit or ''}\n"
                
                prompt += """
                Please provide comprehensive feedback on this deployment, including:
                
                1. Overall assessment of the deployment
                2. Analysis of any errors or issues
                3. Performance evaluation based on metrics
                4. Recommendations for improvement
                5. Best practices that should be followed
                """
                
                system_prompt = """
                You are an expert deployment analyst. Your job is to analyze deployments and provide actionable feedback to help improve the deployment process and application quality.
                
                Focus on:
                - Identifying patterns in errors and logs
                - Highlighting performance issues
                - Suggesting specific improvements
                - Recommending best practices
                
                Be specific, actionable, and concise in your feedback.
                """
                
                result = await self.claude_service.generate_text(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=2000,
                    temperature=0.3,
                )
                
                # Extract feedback
                feedback = result.get("text", "")
                
                # Store feedback in deployment context metadata
                deployment_context.metadata["ai_feedback"] = feedback
                
                # Update context in OrbitBridge
                bridge = await get_orbit_bridge()
                await bridge.store_context(deployment_context)
                
                return {
                    "feedback": feedback,
                    "deployment_id": deployment_context.deployment.id,
                    "status": "success",
                    "tool": "claude",
                }
            except Exception as e:
                logger.error(f"Error analyzing deployment with Claude: {str(e)}")
                return {
                    "error": str(e),
                    "status": "error",
                    "tool": "claude",
                }
        
        return {
            "error": "No AI service available for deployment analysis",
            "status": "error",
            "tool": "none",
        }
    
    async def analyze_error(
        self,
        error_context: OrbitContext,
        code: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze an error and provide AI-powered feedback.
        
        Args:
            error_context: Error context to analyze
            code: Code associated with the error
            language: Programming language of the code
            
        Returns:
            AI-powered analysis of the error
        """
        if not error_context.error:
            raise ValueError("Invalid error context")
        
        # Convert OrbitContext to EnhancedOrbitContext
        enhanced_context = EnhancedOrbitContext.from_orbit_context(error_context)
        
        # Add code as a related resource if provided
        if code and language:
            enhanced_context.add_resource({
                "type": "code",
                "content": code,
                "metadata": {
                    "language": language,
                    "file": error_context.error_location.file if error_context.error_location else "unknown",
                    "line": error_context.error_location.line if error_context.error_location else 0,
                }
            })
        
        # Try using MCP client first
        try:
            mcp_client = await self.get_mcp_client()
            
            # Discover available tools
            tools = await mcp_client.discover_tools()
            error_analysis_tools = [tool for tool in tools if "error" in tool.name.lower() and "analyze" in tool.name.lower()]
            
            if error_analysis_tools:
                # Use the first available error analysis tool
                tool = error_analysis_tools[0]
                logger.info(f"Using MCP tool for error analysis: {tool.name}")
                
                # Send context to MCP
                context_response = await mcp_client.send_context(enhanced_context)
                context_id = context_response.get("id")
                
                # Invoke the tool
                result = await mcp_client.invoke_tool(
                    tool.name,
                    {
                        "context_id": context_id,
                        "error_id": error_context.id,
                        "code": code,
                        "language": language,
                    }
                )
                
                # Extract analysis
                analysis = result.get("analysis") or result.get("explanation") or result.get("text", "")
                
                # Store analysis in error context metadata
                error_context.metadata["ai_analysis"] = analysis
                
                # Update context in OrbitBridge
                bridge = await get_orbit_bridge()
                await bridge.store_context(error_context)
                
                return {
                    "analysis": analysis,
                    "error_id": error_context.id,
                    "status": "success",
                    "tool": tool.name,
                }
            else:
                logger.info("No error analysis tools found in MCP, falling back to direct service calls")
        except Exception as e:
            logger.warning(f"Error using MCP for error analysis: {str(e)}. Falling back to direct service calls.")
        
        # Use Cursor for error analysis if available and code is provided
        if self.cursor_service and code and language:
            try:
                error_message = error_context.error.get("message", "")
                error_type = error_context.error.get("type", "")
                error_location = error_context.error_location
                
                # Create context for Cursor
                context = f"""
                Error Type: {error_type}
                Error Message: {error_message}
                """
                
                if error_location:
                    context += f"""
                    File: {error_location.file}
                    Line: {error_location.line}
                    Column: {error_location.column}
                    Function: {error_location.function}
                    """
                
                # Get explanation from Cursor
                explanation = await self.cursor_service.explain_code(
                    code=code,
                    language=language,
                    detail_level="high",
                )
                
                # Store analysis in error context metadata
                error_context.metadata["ai_analysis"] = explanation.get("explanation", "")
                
                # Update context in OrbitBridge
                bridge = await get_orbit_bridge()
                await bridge.store_context(error_context)
                
                return {
                    "explanation": explanation.get("explanation", ""),
                    "summary": explanation.get("summary", ""),
                    "complexity_score": explanation.get("complexity_score", 0),
                    "error_id": error_context.id,
                    "status": "success",
                    "tool": "cursor",
                }
            except Exception as e:
                logger.error(f"Error analyzing code with Cursor: {str(e)}")
        
        # Fall back to Claude if Cursor is not available or failed
        if self.claude_service:
            try:
                error_message = error_context.error.get("message", "")
                error_type = error_context.error.get("type", "")
                error_location = error_context.error_location
                
                # Create prompt for Claude
                prompt = f"""
                Analyze the following error:
                
                Error Type: {error_type}
                Error Message: {error_message}
                """
                
                if error_location:
                    prompt += f"""
                    File: {error_location.file}
                    Line: {error_location.line}
                    Column: {error_location.column}
                    Function: {error_location.function}
                    """
                
                if code:
                    prompt += f"""
                    Code:
                    ```{language or ''}
                    {code}
                    ```
                    """
                
                prompt += """
                Please provide a detailed analysis of this error, including:
                
                1. What caused the error
                2. How to fix it
                3. Best practices to prevent similar errors
                """
                
                system_prompt = """
                You are an expert code debugger. Your job is to analyze errors and provide actionable feedback to help developers fix issues and improve their code quality.
                
                Focus on:
                - Identifying the root cause of errors
                - Suggesting specific fixes
                - Explaining best practices
                - Providing educational context
                
                Be specific, actionable, and concise in your feedback.
                """
                
                result = await self.claude_service.generate_text(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=1500,
                    temperature=0.3,
                )
                
                # Extract analysis
                analysis = result.get("text", "")
                
                # Store analysis in error context metadata
                error_context.metadata["ai_analysis"] = analysis
                
                # Update context in OrbitBridge
                bridge = await get_orbit_bridge()
                await bridge.store_context(error_context)
                
                return {
                    "analysis": analysis,
                    "error_id": error_context.id,
                    "status": "success",
                    "tool": "claude",
                }
            except Exception as e:
                logger.error(f"Error analyzing error with Claude: {str(e)}")
                return {
                    "error": str(e),
                    "status": "error",
                    "tool": "claude",
                }
        
        return {
            "error": "No AI service available for error analysis",
            "status": "error",
            "tool": "none",
        }
    
    async def generate_performance_recommendations(
        self,
        project_id: str,
        environment: str,
        metric_contexts: List[OrbitContext],
    ) -> Dict[str, Any]:
        """
        Generate performance recommendations based on metrics.
        
        Args:
            project_id: ID of the project
            environment: Environment (development, staging, production)
            metric_contexts: Metric contexts to analyze
            
        Returns:
            AI-powered performance recommendations
        """
        # Log to MCP
        await get_mcp_client().send({
            "type": "ai_feedback",
            "operation": "generate_performance_recommendations",
            "project_id": project_id,
            "environment": environment,
            "metrics_count": len(metric_contexts),
        })
        
        # Use Claude for performance recommendations if available
        if self.claude_service:
            try:
                # Extract metrics
                metrics = []
                for context in metric_contexts:
                    if context.metric:
                        metrics.append({
                            "name": context.metric.name,
                            "value": context.metric.value,
                            "unit": context.metric.unit,
                            "timestamp": context.timestamp.isoformat(),
                            "tags": context.metric.tags,
                        })
                
                # Create prompt for Claude
                prompt = f"""
                Generate performance recommendations based on the following metrics:
                
                Project: {project_id}
                Environment: {environment}
                
                ## Metrics:
                """
                
                for i, metric in enumerate(metrics, 1):
                    prompt += f"{i}. {metric['name']}: {metric['value']} {metric['unit'] or ''}\n"
                    if metric['tags']:
                        prompt += f"   Tags: {', '.join([f'{k}={v}' for k, v in metric['tags'].items()])}\n"
                
                prompt += """
                Please provide detailed performance recommendations, including:
                
                1. Identification of performance bottlenecks
                2. Specific recommendations for improvement
                3. Best practices for performance optimization
                4. Prioritization of recommendations
                """
                
                system_prompt = """
                You are an expert performance engineer. Your job is to analyze performance metrics and provide actionable recommendations to help improve application performance.
                
                Focus on:
                - Identifying performance bottlenecks
                - Suggesting specific optimizations
                - Explaining performance best practices
                - Prioritizing recommendations by impact
                
                Be specific, actionable, and concise in your recommendations.
                """
                
                result = await self.claude_service.generate_text(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=1500,
                    temperature=0.3,
                )
                
                # Extract recommendations
                recommendations = result.get("text", "")
                
                return {
                    "recommendations": recommendations,
                    "project_id": project_id,
                    "environment": environment,
                    "metrics_count": len(metrics),
                    "status": "success",
                    "tool": "claude",
                }
            except Exception as e:
                logger.error(f"Error generating performance recommendations: {str(e)}")
                return {
                    "error": str(e),
                    "status": "error",
                    "tool": "claude",
                }
        
        return {
            "error": "No AI service available for performance recommendations",
            "status": "error",
            "tool": "none",
        }
    
    async def generate_deployment_summary(
        self,
        deployment_context: OrbitContext,
        related_contexts: Optional[List[OrbitContext]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a summary of a deployment.
        
        Args:
            deployment_context: Deployment context to summarize
            related_contexts: Related contexts (errors, logs, etc.)
            
        Returns:
            AI-generated deployment summary
        """
        if not deployment_context.deployment:
            raise ValueError("Invalid deployment context")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "ai_feedback",
            "operation": "generate_deployment_summary",
            "deployment_id": deployment_context.deployment.id,
            "related_contexts_count": len(related_contexts) if related_contexts else 0,
        })
        
        # Use Claude for deployment summary if available
        if self.claude_service:
            try:
                # Get deployment data
                deployment = deployment_context.deployment
                
                # Prepare related data
                related_errors = []
                related_logs = []
                related_metrics = []
                related_screenshots = []
                
                if related_contexts:
                    for context in related_contexts:
                        if context.type == ContextType.ERROR:
                            related_errors.append(context)
                        elif context.type == ContextType.LOG:
                            related_logs.append(context)
                        elif context.type == ContextType.METRIC:
                            related_metrics.append(context)
                        elif context.type == ContextType.SCREENSHOT:
                            related_screenshots.append(context)
                
                # Create prompt for Claude
                prompt = f"""
                Generate a concise summary of the following deployment:
                
                Project: {deployment_context.metadata.get("project_name", "Unknown Project")}
                Environment: {deployment_context.environment}
                Branch: {deployment.branch}
                Commit: {deployment.commit_hash}
                Commit Message: {deployment.commit_message or "N/A"}
                Status: {deployment.status}
                Duration: {deployment.duration_seconds} seconds
                
                """
                
                if related_errors:
                    prompt += "## Errors:\n"
                    for i, error in enumerate(related_errors[:5], 1):  # Limit to 5 errors
                        error_message = error.error.get("message", "Unknown error")
                        error_location = error.error_location
                        file_path = error_location.file if error_location else "Unknown file"
                        line = error_location.line if error_location else "Unknown line"
                        
                        prompt += f"{i}. {error_message} in {file_path}:{line}\n"
                
                if related_logs:
                    prompt += "\n## Significant Logs:\n"
                    for i, log in enumerate(related_logs[:5], 1):  # Limit to 5 logs
                        prompt += f"{i}. [{log.log_severity}] {log.log_message}\n"
                
                if related_metrics:
                    prompt += "\n## Performance Metrics:\n"
                    for i, metric in enumerate(related_metrics[:5], 1):  # Limit to 5 metrics
                        if metric.metric:
                            prompt += f"{i}. {metric.metric.name}: {metric.metric.value} {metric.metric.unit or ''}\n"
                
                prompt += """
                Please generate a concise summary of this deployment, including:
                
                1. Overall status and key information
                2. Notable changes or features
                3. Any issues or errors
                4. Performance impact
                
                Keep the summary brief and focused on the most important information.
                """
                
                system_prompt = """
                You are a deployment summary assistant. Your job is to create concise, informative summaries of code deployments highlighting key changes, potential issues, and performance impacts.
                
                Focus on:
                - Summarizing the most important information
                - Highlighting key changes and features
                - Noting any issues or errors
                - Mentioning performance impacts
                
                Be concise and focus on what's most important for developers to know.
                """
                
                result = await self.claude_service.generate_text(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    max_tokens=800,
                    temperature=0.3,
                )
                
                # Extract summary
                summary = result.get("text", "")
                
                # Store summary in deployment context metadata
                deployment_context.metadata["ai_summary"] = summary
                
                # Update context in OrbitBridge
                bridge = await get_orbit_bridge()
                await bridge.store_context(deployment_context)
                
                return {
                    "summary": summary,
                    "deployment_id": deployment.id,
                    "status": "success",
                    "tool": "claude",
                }
            except Exception as e:
                logger.error(f"Error generating deployment summary: {str(e)}")
                return {
                    "error": str(e),
                    "status": "error",
                    "tool": "claude",
                }
        
        return {
            "error": "No AI service available for deployment summary",
            "status": "error",
            "tool": "none",
        }


# Global AI feedback service instance
_ai_feedback_service = None

async def get_ai_feedback_service() -> AIFeedbackService:
    """
    Get the AI feedback service instance.
    
    Returns:
        AI feedback service instance
    """
    global _ai_feedback_service
    
    if _ai_feedback_service is None:
        from app.services.ai.claude_service import get_claude_service
        from app.services.ai.cursor_service import get_cursor_service
        from app.services.ai.replit_service import get_replit_service
        
        claude_service = await get_claude_service()
        cursor_service = await get_cursor_service()
        replit_service = await get_replit_service()
        
        # Create MCP client
        mcp_url = os.environ.get("MCP_URL") or await get_windsurf_mcp_url()
        if mcp_url:
            mcp_client = MCPClient(mcp_url=mcp_url, api_key=os.environ.get("MCP_API_KEY"))
            logger.info(f"Created MCP client with URL: {mcp_url}")
        else:
            mcp_client = None
            logger.warning("No MCP URL found, AI feedback service will use direct service calls only")
        
        _ai_feedback_service = AIFeedbackService(
            claude_service=claude_service,
            cursor_service=cursor_service,
            replit_service=replit_service,
            mcp_client=mcp_client,
        )
    
    return _ai_feedback_service
