"""
API endpoints for observability features.

This module provides API endpoints for managing dashboards and alerts.
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from app.services.observability.dashboards import (
    get_dashboard_service,
    Dashboard,
    DashboardPanel,
    VisualizationType,
    TimeRange,
)
from app.services.observability.alerts import (
    get_alert_service,
    AlertThreshold,
    NotificationConfig,
    Alert,
    AlertSeverity,
    AlertStatus,
    NotificationChannel,
)
from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

# Create API router for observability
router = APIRouter(prefix="/api/observability", tags=["observability"])

# Pydantic models for dashboards
class DashboardPanelCreate(BaseModel):
    """Model for creating a dashboard panel."""
    title: str = Field(..., description="Panel title")
    description: str = Field(..., description="Panel description")
    visualization_type: str = Field(..., description="Type of visualization")
    query: str = Field(..., description="Query for the panel (PromQL, LogQL, etc.)")
    time_range: str = Field("1h", description="Time range for the panel")
    refresh_interval: int = Field(60, description="Refresh interval in seconds")
    width: int = Field(6, description="Panel width in grid units (1-12)")
    height: int = Field(8, description="Panel height in grid units")
    position: Dict[str, int] = Field(None, description="Panel position (x, y coordinates)")
    thresholds: Dict[str, float] = Field(None, description="Warning and critical thresholds")

class DashboardPanelResponse(BaseModel):
    """Model for dashboard panel response."""
    id: str = Field(..., description="Panel ID")
    title: str = Field(..., description="Panel title")
    description: str = Field(..., description="Panel description")
    visualization_type: str = Field(..., description="Type of visualization")
    query: str = Field(..., description="Query for the panel (PromQL, LogQL, etc.)")
    time_range: str = Field(..., description="Time range for the panel")
    refresh_interval: int = Field(..., description="Refresh interval in seconds")
    width: int = Field(..., description="Panel width in grid units (1-12)")
    height: int = Field(..., description="Panel height in grid units")
    position: Dict[str, int] = Field(..., description="Panel position (x, y coordinates)")
    thresholds: Dict[str, float] = Field(..., description="Warning and critical thresholds")

class DashboardCreate(BaseModel):
    """Model for creating a dashboard."""
    name: str = Field(..., description="Dashboard name")
    description: str = Field(..., description="Dashboard description")
    panels: List[DashboardPanelCreate] = Field(..., description="List of dashboard panels")
    tags: List[str] = Field(None, description="List of tags")

class DashboardResponse(BaseModel):
    """Model for dashboard response."""
    id: str = Field(..., description="Dashboard ID")
    name: str = Field(..., description="Dashboard name")
    description: str = Field(..., description="Dashboard description")
    panels: List[DashboardPanelResponse] = Field(..., description="List of dashboard panels")
    tags: List[str] = Field(..., description="List of tags")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")

# Pydantic models for alerts
class AlertThresholdCreate(BaseModel):
    """Model for creating an alert threshold."""
    name: str = Field(..., description="Threshold name")
    description: str = Field(..., description="Threshold description")
    metric_name: str = Field(..., description="Name of the metric to monitor")
    query: str = Field(..., description="Query for the metric (PromQL, LogQL, etc.)")
    warning_threshold: Optional[float] = Field(None, description="Warning threshold value")
    critical_threshold: Optional[float] = Field(None, description="Critical threshold value")
    comparison: str = Field("greater", description="Comparison operator ('greater' or 'less')")
    duration: str = Field("5m", description="Duration the threshold must be exceeded")
    enabled: bool = Field(True, description="Whether the threshold is enabled")

class AlertThresholdResponse(BaseModel):
    """Model for alert threshold response."""
    id: str = Field(..., description="Threshold ID")
    name: str = Field(..., description="Threshold name")
    description: str = Field(..., description="Threshold description")
    metric_name: str = Field(..., description="Name of the metric to monitor")
    query: str = Field(..., description="Query for the metric (PromQL, LogQL, etc.)")
    warning_threshold: Optional[float] = Field(None, description="Warning threshold value")
    critical_threshold: Optional[float] = Field(None, description="Critical threshold value")
    comparison: str = Field(..., description="Comparison operator ('greater' or 'less')")
    duration: str = Field(..., description="Duration the threshold must be exceeded")
    enabled: bool = Field(..., description="Whether the threshold is enabled")

class NotificationConfigCreate(BaseModel):
    """Model for creating a notification configuration."""
    name: str = Field(..., description="Configuration name")
    channel: str = Field(..., description="Notification channel")
    config: Dict[str, Any] = Field(..., description="Channel-specific configuration")
    enabled: bool = Field(True, description="Whether the configuration is enabled")

class NotificationConfigResponse(BaseModel):
    """Model for notification configuration response."""
    id: str = Field(..., description="Configuration ID")
    name: str = Field(..., description="Configuration name")
    channel: str = Field(..., description="Notification channel")
    config: Dict[str, Any] = Field(..., description="Channel-specific configuration")
    enabled: bool = Field(..., description="Whether the configuration is enabled")

class AlertResponse(BaseModel):
    """Model for alert response."""
    id: str = Field(..., description="Alert ID")
    threshold_id: str = Field(..., description="ID of the threshold that triggered the alert")
    severity: str = Field(..., description="Alert severity")
    status: str = Field(..., description="Alert status")
    value: float = Field(..., description="Value that triggered the alert")
    message: str = Field(..., description="Alert message")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    acknowledged_by: Optional[str] = Field(None, description="User who acknowledged the alert")
    resolved_by: Optional[str] = Field(None, description="User who resolved the alert")
    notification_sent: bool = Field(..., description="Whether a notification was sent")

# Dashboard endpoints
@router.post("/dashboards", response_model=DashboardResponse)
async def create_dashboard(
    dashboard: DashboardCreate = Body(...),
):
    """
    Create a new dashboard.
    
    Args:
        dashboard: Dashboard to create
        
    Returns:
        Created dashboard
    """
    try:
        # Get dashboard service
        dashboard_service = await get_dashboard_service()
        
        # Generate dashboard ID
        dashboard_id = str(uuid.uuid4())
        
        # Create panels
        panels = []
        for panel in dashboard.panels:
            panel_id = str(uuid.uuid4())
            panels.append(
                DashboardPanel(
                    id=panel_id,
                    title=panel.title,
                    description=panel.description,
                    visualization_type=VisualizationType(panel.visualization_type),
                    query=panel.query,
                    time_range=TimeRange(panel.time_range),
                    refresh_interval=panel.refresh_interval,
                    width=panel.width,
                    height=panel.height,
                    position=panel.position or {"x": 0, "y": 0},
                    thresholds=panel.thresholds or {"warning": None, "critical": None},
                )
            )
        
        # Create dashboard
        created_dashboard = await dashboard_service.create_dashboard(
            Dashboard(
                id=dashboard_id,
                name=dashboard.name,
                description=dashboard.description,
                panels=panels,
                tags=dashboard.tags or [],
            )
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dashboard_api",
            "operation": "create",
            "dashboard_id": dashboard_id,
            "name": dashboard.name,
            "panel_count": len(panels),
        })
        
        return DashboardResponse(**created_dashboard.to_dict())
    except Exception as e:
        logger.error(f"Error creating dashboard: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: str = Path(..., description="ID of the dashboard to get"),
):
    """
    Get a dashboard by ID.
    
    Args:
        dashboard_id: ID of the dashboard to get
        
    Returns:
        Dashboard
    """
    try:
        # Get dashboard service
        dashboard_service = await get_dashboard_service()
        
        # Get dashboard
        dashboard = await dashboard_service.get_dashboard(dashboard_id)
        
        if not dashboard:
            raise HTTPException(status_code=404, detail=f"Dashboard {dashboard_id} not found")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dashboard_api",
            "operation": "get",
            "dashboard_id": dashboard_id,
            "name": dashboard.name,
        })
        
        return DashboardResponse(**dashboard.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dashboard {dashboard_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboards", response_model=List[DashboardResponse])
async def list_dashboards(
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
):
    """
    List dashboards.
    
    Args:
        tags: Filter by tags
        
    Returns:
        List of dashboards
    """
    try:
        # Get dashboard service
        dashboard_service = await get_dashboard_service()
        
        # List dashboards
        dashboards = await dashboard_service.list_dashboards(tags=tags)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dashboard_api",
            "operation": "list",
            "tag_filters": tags,
            "count": len(dashboards),
        })
        
        return [DashboardResponse(**dashboard.to_dict()) for dashboard in dashboards]
    except Exception as e:
        logger.error(f"Error listing dashboards: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Alert threshold endpoints
@router.post("/thresholds", response_model=AlertThresholdResponse)
async def create_threshold(
    threshold: AlertThresholdCreate = Body(...),
):
    """
    Create a new alert threshold.
    
    Args:
        threshold: Alert threshold to create
        
    Returns:
        Created alert threshold
    """
    try:
        # Get alert service
        alert_service = await get_alert_service()
        
        # Generate threshold ID
        threshold_id = str(uuid.uuid4())
        
        # Create threshold
        created_threshold = await alert_service.create_threshold(
            AlertThreshold(
                id=threshold_id,
                name=threshold.name,
                description=threshold.description,
                metric_name=threshold.metric_name,
                query=threshold.query,
                warning_threshold=threshold.warning_threshold,
                critical_threshold=threshold.critical_threshold,
                comparison=threshold.comparison,
                duration=threshold.duration,
                enabled=threshold.enabled,
            )
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "alert_threshold_api",
            "operation": "create",
            "threshold_id": threshold_id,
            "name": threshold.name,
            "metric_name": threshold.metric_name,
        })
        
        return AlertThresholdResponse(**created_threshold.to_dict())
    except Exception as e:
        logger.error(f"Error creating alert threshold: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/thresholds/{threshold_id}", response_model=AlertThresholdResponse)
async def get_threshold(
    threshold_id: str = Path(..., description="ID of the threshold to get"),
):
    """
    Get an alert threshold by ID.
    
    Args:
        threshold_id: ID of the threshold to get
        
    Returns:
        Alert threshold
    """
    try:
        # Get alert service
        alert_service = await get_alert_service()
        
        # Get threshold
        threshold = await alert_service.get_threshold(threshold_id)
        
        if not threshold:
            raise HTTPException(status_code=404, detail=f"Threshold {threshold_id} not found")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "alert_threshold_api",
            "operation": "get",
            "threshold_id": threshold_id,
            "name": threshold.name,
            "metric_name": threshold.metric_name,
        })
        
        return AlertThresholdResponse(**threshold.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert threshold {threshold_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/thresholds", response_model=List[AlertThresholdResponse])
async def list_thresholds():
    """
    List alert thresholds.
    
    Returns:
        List of alert thresholds
    """
    try:
        # Get alert service
        alert_service = await get_alert_service()
        
        # List thresholds
        thresholds = await alert_service.list_thresholds()
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "alert_threshold_api",
            "operation": "list",
            "count": len(thresholds),
        })
        
        return [AlertThresholdResponse(**threshold.to_dict()) for threshold in thresholds]
    except Exception as e:
        logger.error(f"Error listing alert thresholds: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Notification configuration endpoints
@router.post("/notifications", response_model=NotificationConfigResponse)
async def create_notification(
    notification: NotificationConfigCreate = Body(...),
):
    """
    Create a new notification configuration.
    
    Args:
        notification: Notification configuration to create
        
    Returns:
        Created notification configuration
    """
    try:
        # Get alert service
        alert_service = await get_alert_service()
        
        # Generate notification ID
        notification_id = str(uuid.uuid4())
        
        # Create notification config
        created_notification = await alert_service.create_notification(
            NotificationConfig(
                id=notification_id,
                name=notification.name,
                channel=NotificationChannel(notification.channel),
                config=notification.config,
                enabled=notification.enabled,
            )
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "notification_config_api",
            "operation": "create",
            "config_id": notification_id,
            "name": notification.name,
            "channel": notification.channel,
        })
        
        return NotificationConfigResponse(**created_notification.to_dict())
    except Exception as e:
        logger.error(f"Error creating notification configuration: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/notifications", response_model=List[NotificationConfigResponse])
async def list_notifications():
    """
    List notification configurations.
    
    Returns:
        List of notification configurations
    """
    try:
        # Get alert service
        alert_service = await get_alert_service()
        
        # List notification configs
        notifications = await alert_service.list_notifications()
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "notification_config_api",
            "operation": "list",
            "count": len(notifications),
        })
        
        return [NotificationConfigResponse(**notification.to_dict()) for notification in notifications]
    except Exception as e:
        logger.error(f"Error listing notification configurations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Alert endpoints
@router.get("/alerts", response_model=List[AlertResponse])
async def list_alerts(
    status: Optional[str] = Query(None, description="Filter by status"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
):
    """
    List alerts.
    
    Args:
        status: Filter by status
        severity: Filter by severity
        
    Returns:
        List of alerts
    """
    try:
        # Get alert service
        alert_service = await get_alert_service()
        
        # Convert status and severity to enums if provided
        status_enum = AlertStatus(status) if status else None
        severity_enum = AlertSeverity(severity) if severity else None
        
        # List alerts
        alerts = await alert_service.list_alerts(
            status=status_enum,
            severity=severity_enum,
        )
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "alert_api",
            "operation": "list",
            "status_filter": status,
            "severity_filter": severity,
            "count": len(alerts),
        })
        
        return [AlertResponse(**alert.to_dict()) for alert in alerts]
    except Exception as e:
        logger.error(f"Error listing alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str = Path(..., description="ID of the alert to acknowledge"),
    user_id: str = Query(..., description="ID of the user acknowledging the alert"),
):
    """
    Acknowledge an alert.
    
    Args:
        alert_id: ID of the alert to acknowledge
        user_id: ID of the user acknowledging the alert
        
    Returns:
        Success message
    """
    try:
        # Get alert service
        alert_service = await get_alert_service()
        
        # Acknowledge alert
        await alert_service.acknowledge_alert(alert_id, user_id)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "alert_api",
            "operation": "acknowledge",
            "alert_id": alert_id,
            "user_id": user_id,
        })
        
        return {"message": f"Alert {alert_id} acknowledged successfully"}
    except ValueError as e:
        logger.error(f"Error acknowledging alert {alert_id}: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error acknowledging alert {alert_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str = Path(..., description="ID of the alert to resolve"),
    user_id: str = Query(..., description="ID of the user resolving the alert"),
):
    """
    Resolve an alert.
    
    Args:
        alert_id: ID of the alert to resolve
        user_id: ID of the user resolving the alert
        
    Returns:
        Success message
    """
    try:
        # Get alert service
        alert_service = await get_alert_service()
        
        # Resolve alert
        await alert_service.resolve_alert(alert_id, user_id)
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "alert_api",
            "operation": "resolve",
            "alert_id": alert_id,
            "user_id": user_id,
        })
        
        return {"message": f"Alert {alert_id} resolved successfully"}
    except ValueError as e:
        logger.error(f"Error resolving alert {alert_id}: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error resolving alert {alert_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/{notification_id}/test")
async def test_notification(
    notification_id: str = Path(..., description="ID of the notification configuration to test"),
    message: str = Query("This is a test notification", description="Test message"),
):
    """
    Test a notification configuration.
    
    Args:
        notification_id: ID of the notification configuration to test
        message: Test message
        
    Returns:
        Success message
    """
    try:
        # Get alert service
        alert_service = await get_alert_service()
        
        # Test notification
        success = await alert_service.test_notification(notification_id, message)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to test notification {notification_id}")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "notification_config_api",
            "operation": "test",
            "config_id": notification_id,
            "message": message,
        })
        
        return {"message": f"Notification {notification_id} tested successfully"}
    except Exception as e:
        logger.error(f"Error testing notification {notification_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
