"""
OrbitContext format implementation for structured runtime data.

The OrbitContext format is a standardized format for representing runtime data
from OrbitHost, including deployment logs, errors, screenshots, and metadata.
This structured format enables AI tools like Windsurf, Claude, Replit, and Cursor
to easily access and analyze runtime data for providing real-time feedback.
"""
import datetime
import json
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class ContextType(str, Enum):
    """Types of OrbitContext data."""
    DEPLOYMENT = "deployment"
    ERROR = "error"
    SCREENSHOT = "screenshot"
    LOG = "log"
    METRIC = "metric"
    TRACE = "trace"
    FEEDBACK = "feedback"


class SourceType(str, Enum):
    """Source of OrbitContext data."""
    ORBITDEPLOY = "orbitdeploy"
    ORBITHOST = "orbithost"
    ORBITLOGS = "orbitlogs"
    EXTERNAL = "external"


class Severity(str, Enum):
    """Severity levels for errors and logs."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Screenshot(BaseModel):
    """Screenshot data."""
    url: str
    timestamp: datetime.datetime
    width: int
    height: int
    format: str = "png"
    dom_snapshot_url: Optional[str] = None
    viewport: Optional[Dict[str, int]] = None
    device: Optional[str] = None


class ErrorLocation(BaseModel):
    """Location information for an error."""
    file: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    function: Optional[str] = None
    stack_trace: Optional[str] = None


class DeploymentInfo(BaseModel):
    """Deployment information."""
    id: str
    project_id: str
    environment: str
    branch: str
    commit_hash: str
    commit_message: Optional[str] = None
    author: Optional[str] = None
    timestamp: datetime.datetime
    status: str
    duration_seconds: float
    url: Optional[str] = None
    logs_url: Optional[str] = None
    build_command: Optional[str] = None
    deploy_command: Optional[str] = None


class MetricValue(BaseModel):
    """Metric value with metadata."""
    name: str
    value: float
    unit: Optional[str] = None
    timestamp: datetime.datetime
    tags: Dict[str, str] = Field(default_factory=dict)


class TraceSpan(BaseModel):
    """Trace span information."""
    id: str
    trace_id: str
    parent_id: Optional[str] = None
    name: str
    start_time: datetime.datetime
    end_time: Optional[datetime.datetime] = None
    duration_ms: Optional[float] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)

    @validator("duration_ms", always=True)
    def calculate_duration(cls, v, values):
        """Calculate duration if not provided."""
        if v is not None:
            return v
        if values.get("start_time") and values.get("end_time"):
            return (values["end_time"] - values["start_time"]).total_seconds() * 1000
        return None


class OrbitContext(BaseModel):
    """
    OrbitContext is a standardized format for representing runtime data.
    
    It provides a structured way to represent deployment logs, errors,
    screenshots, and metadata from OrbitHost, enabling AI tools to
    access and analyze this data for providing real-time feedback.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: ContextType
    source: SourceType
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    project_id: str
    user_id: Optional[str] = None
    environment: str
    version: str = "1.0.0"
    
    # Type-specific data
    deployment: Optional[DeploymentInfo] = None
    error: Optional[Dict[str, Any]] = None
    error_location: Optional[ErrorLocation] = None
    screenshot: Optional[Screenshot] = None
    log_message: Optional[str] = None
    log_severity: Optional[Severity] = None
    metric: Optional[MetricValue] = None
    trace: Optional[TraceSpan] = None
    
    # Additional data
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    related_contexts: List[str] = Field(default_factory=list)
    
    @validator("deployment", always=True)
    def validate_deployment(cls, v, values):
        """Validate that deployment data is present for deployment type."""
        if values.get("type") == ContextType.DEPLOYMENT and v is None:
            raise ValueError("Deployment data is required for deployment context type")
        return v
    
    @validator("error", "error_location", always=True)
    def validate_error(cls, v, values):
        """Validate that error data is present for error type."""
        if values.get("type") == ContextType.ERROR and v is None:
            raise ValueError("Error data is required for error context type")
        return v
    
    @validator("screenshot", always=True)
    def validate_screenshot(cls, v, values):
        """Validate that screenshot data is present for screenshot type."""
        if values.get("type") == ContextType.SCREENSHOT and v is None:
            raise ValueError("Screenshot data is required for screenshot context type")
        return v
    
    @validator("log_message", "log_severity", always=True)
    def validate_log(cls, v, values):
        """Validate that log data is present for log type."""
        if values.get("type") == ContextType.LOG and v is None:
            raise ValueError("Log data is required for log context type")
        return v
    
    @validator("metric", always=True)
    def validate_metric(cls, v, values):
        """Validate that metric data is present for metric type."""
        if values.get("type") == ContextType.METRIC and v is None:
            raise ValueError("Metric data is required for metric context type")
        return v
    
    @validator("trace", always=True)
    def validate_trace(cls, v, values):
        """Validate that trace data is present for trace type."""
        if values.get("type") == ContextType.TRACE and v is None:
            raise ValueError("Trace data is required for trace context type")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.dict(exclude_none=True)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(
            self.dict(exclude_none=True),
            default=lambda o: o.isoformat() if isinstance(o, datetime.datetime) else None
        )
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrbitContext":
        """Create from dictionary."""
        # Convert string timestamps to datetime objects
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        
        if "deployment" in data and data["deployment"] and "timestamp" in data["deployment"]:
            data["deployment"]["timestamp"] = datetime.datetime.fromisoformat(
                data["deployment"]["timestamp"].replace("Z", "+00:00")
            )
        
        if "screenshot" in data and data["screenshot"] and "timestamp" in data["screenshot"]:
            data["screenshot"]["timestamp"] = datetime.datetime.fromisoformat(
                data["screenshot"]["timestamp"].replace("Z", "+00:00")
            )
        
        if "metric" in data and data["metric"] and "timestamp" in data["metric"]:
            data["metric"]["timestamp"] = datetime.datetime.fromisoformat(
                data["metric"]["timestamp"].replace("Z", "+00:00")
            )
        
        if "trace" in data and data["trace"]:
            if "start_time" in data["trace"]:
                data["trace"]["start_time"] = datetime.datetime.fromisoformat(
                    data["trace"]["start_time"].replace("Z", "+00:00")
                )
            if "end_time" in data["trace"]:
                data["trace"]["end_time"] = datetime.datetime.fromisoformat(
                    data["trace"]["end_time"].replace("Z", "+00:00")
                )
        
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> "OrbitContext":
        """Create from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    @classmethod
    def create_deployment_context(
        cls,
        project_id: str,
        deployment_id: str,
        environment: str,
        branch: str,
        commit_hash: str,
        status: str,
        duration_seconds: float,
        user_id: Optional[str] = None,
        commit_message: Optional[str] = None,
        author: Optional[str] = None,
        url: Optional[str] = None,
        logs_url: Optional[str] = None,
        build_command: Optional[str] = None,
        deploy_command: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> "OrbitContext":
        """Create a deployment context."""
        return cls(
            type=ContextType.DEPLOYMENT,
            source=SourceType.ORBITDEPLOY,
            project_id=project_id,
            user_id=user_id,
            environment=environment,
            deployment=DeploymentInfo(
                id=deployment_id,
                project_id=project_id,
                environment=environment,
                branch=branch,
                commit_hash=commit_hash,
                commit_message=commit_message,
                author=author,
                timestamp=datetime.datetime.utcnow(),
                status=status,
                duration_seconds=duration_seconds,
                url=url,
                logs_url=logs_url,
                build_command=build_command,
                deploy_command=deploy_command,
            ),
            metadata=metadata or {},
            tags=tags or [],
        )
    
    @classmethod
    def create_error_context(
        cls,
        project_id: str,
        environment: str,
        error_message: str,
        error_type: str,
        user_id: Optional[str] = None,
        file: Optional[str] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
        function: Optional[str] = None,
        stack_trace: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> "OrbitContext":
        """Create an error context."""
        return cls(
            type=ContextType.ERROR,
            source=SourceType.ORBITHOST,
            project_id=project_id,
            user_id=user_id,
            environment=environment,
            error={
                "message": error_message,
                "type": error_type,
            },
            error_location=ErrorLocation(
                file=file,
                line=line,
                column=column,
                function=function,
                stack_trace=stack_trace,
            ),
            metadata=metadata or {},
            tags=tags or [],
        )
    
    @classmethod
    def create_screenshot_context(
        cls,
        project_id: str,
        environment: str,
        url: str,
        width: int,
        height: int,
        user_id: Optional[str] = None,
        dom_snapshot_url: Optional[str] = None,
        viewport: Optional[Dict[str, int]] = None,
        device: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> "OrbitContext":
        """Create a screenshot context."""
        return cls(
            type=ContextType.SCREENSHOT,
            source=SourceType.ORBITHOST,
            project_id=project_id,
            user_id=user_id,
            environment=environment,
            screenshot=Screenshot(
                url=url,
                timestamp=datetime.datetime.utcnow(),
                width=width,
                height=height,
                dom_snapshot_url=dom_snapshot_url,
                viewport=viewport,
                device=device,
            ),
            metadata=metadata or {},
            tags=tags or [],
        )
    
    @classmethod
    def create_log_context(
        cls,
        project_id: str,
        environment: str,
        message: str,
        severity: Severity,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> "OrbitContext":
        """Create a log context."""
        return cls(
            type=ContextType.LOG,
            source=SourceType.ORBITLOGS,
            project_id=project_id,
            user_id=user_id,
            environment=environment,
            log_message=message,
            log_severity=severity,
            metadata=metadata or {},
            tags=tags or [],
        )
    
    @classmethod
    def create_metric_context(
        cls,
        project_id: str,
        environment: str,
        metric_name: str,
        metric_value: float,
        unit: Optional[str] = None,
        user_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        context_tags: Optional[List[str]] = None,
    ) -> "OrbitContext":
        """Create a metric context."""
        return cls(
            type=ContextType.METRIC,
            source=SourceType.ORBITLOGS,
            project_id=project_id,
            user_id=user_id,
            environment=environment,
            metric=MetricValue(
                name=metric_name,
                value=metric_value,
                unit=unit,
                timestamp=datetime.datetime.utcnow(),
                tags=tags or {},
            ),
            metadata=metadata or {},
            tags=context_tags or [],
        )
    
    @classmethod
    def create_trace_context(
        cls,
        project_id: str,
        environment: str,
        span_id: str,
        trace_id: str,
        span_name: str,
        parent_id: Optional[str] = None,
        start_time: Optional[datetime.datetime] = None,
        end_time: Optional[datetime.datetime] = None,
        duration_ms: Optional[float] = None,
        attributes: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> "OrbitContext":
        """Create a trace context."""
        return cls(
            type=ContextType.TRACE,
            source=SourceType.ORBITLOGS,
            project_id=project_id,
            user_id=user_id,
            environment=environment,
            trace=TraceSpan(
                id=span_id,
                trace_id=trace_id,
                parent_id=parent_id,
                name=span_name,
                start_time=start_time or datetime.datetime.utcnow(),
                end_time=end_time,
                duration_ms=duration_ms,
                attributes=attributes or {},
            ),
            metadata=metadata or {},
            tags=tags or [],
        )
