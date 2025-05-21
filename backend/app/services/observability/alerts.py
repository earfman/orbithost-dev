"""
Alert configuration and notification service for OrbitHost observability.

This module provides functionality for defining alert thresholds,
configuring notification channels, and sending alert notifications.
"""
import json
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class AlertStatus(str, Enum):
    """Alert status."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"

class NotificationChannel(str, Enum):
    """Notification channels for alerts."""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    SMS = "sms"

class AlertThreshold:
    """Model for alert thresholds."""
    
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        metric_name: str,
        query: str,
        warning_threshold: Optional[float] = None,
        critical_threshold: Optional[float] = None,
        comparison: str = "greater",  # "greater" or "less"
        duration: str = "5m",  # Duration the threshold must be exceeded
        enabled: bool = True,
    ):
        """
        Initialize an alert threshold.
        
        Args:
            id: Threshold ID
            name: Threshold name
            description: Threshold description
            metric_name: Name of the metric to monitor
            query: Query for the metric (PromQL, LogQL, etc.)
            warning_threshold: Warning threshold value
            critical_threshold: Critical threshold value
            comparison: Comparison operator ("greater" or "less")
            duration: Duration the threshold must be exceeded
            enabled: Whether the threshold is enabled
        """
        self.id = id
        self.name = name
        self.description = description
        self.metric_name = metric_name
        self.query = query
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.comparison = comparison
        self.duration = duration
        self.enabled = enabled
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "metric_name": self.metric_name,
            "query": self.query,
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "comparison": self.comparison,
            "duration": self.duration,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AlertThreshold":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            metric_name=data["metric_name"],
            query=data["query"],
            warning_threshold=data.get("warning_threshold"),
            critical_threshold=data.get("critical_threshold"),
            comparison=data.get("comparison", "greater"),
            duration=data.get("duration", "5m"),
            enabled=data.get("enabled", True),
        )

class NotificationConfig:
    """Model for notification configuration."""
    
    def __init__(
        self,
        id: str,
        name: str,
        channel: NotificationChannel,
        config: Dict[str, Any],
        enabled: bool = True,
    ):
        """
        Initialize a notification configuration.
        
        Args:
            id: Configuration ID
            name: Configuration name
            channel: Notification channel
            config: Channel-specific configuration
            enabled: Whether the configuration is enabled
        """
        self.id = id
        self.name = name
        self.channel = channel
        self.config = config
        self.enabled = enabled
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "channel": self.channel.value,
            "config": self.config,
            "enabled": self.enabled,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotificationConfig":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            channel=NotificationChannel(data["channel"]),
            config=data["config"],
            enabled=data.get("enabled", True),
        )

class Alert:
    """Model for alerts."""
    
    def __init__(
        self,
        id: str,
        threshold_id: str,
        severity: AlertSeverity,
        status: AlertStatus,
        value: float,
        message: str,
        created_at: datetime = None,
        updated_at: datetime = None,
        acknowledged_by: Optional[str] = None,
        resolved_by: Optional[str] = None,
        notification_sent: bool = False,
    ):
        """
        Initialize an alert.
        
        Args:
            id: Alert ID
            threshold_id: ID of the threshold that triggered the alert
            severity: Alert severity
            status: Alert status
            value: Value that triggered the alert
            message: Alert message
            created_at: Creation timestamp
            updated_at: Last update timestamp
            acknowledged_by: User who acknowledged the alert
            resolved_by: User who resolved the alert
            notification_sent: Whether a notification was sent
        """
        self.id = id
        self.threshold_id = threshold_id
        self.severity = severity
        self.status = status
        self.value = value
        self.message = message
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
        self.acknowledged_by = acknowledged_by
        self.resolved_by = resolved_by
        self.notification_sent = notification_sent
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "threshold_id": self.threshold_id,
            "severity": self.severity.value,
            "status": self.status.value,
            "value": self.value,
            "message": self.message,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "acknowledged_by": self.acknowledged_by,
            "resolved_by": self.resolved_by,
            "notification_sent": self.notification_sent,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Alert":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            threshold_id=data["threshold_id"],
            severity=AlertSeverity(data["severity"]),
            status=AlertStatus(data["status"]),
            value=data["value"],
            message=data["message"],
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else None,
            acknowledged_by=data.get("acknowledged_by"),
            resolved_by=data.get("resolved_by"),
            notification_sent=data.get("notification_sent", False),
        )

class AlertService:
    """
    Service for managing alert thresholds and notifications.
    
    This service provides functionality for creating, retrieving, updating,
    and deleting alert thresholds, as well as sending notifications.
    """
    
    def __init__(self):
        """Initialize the alert service."""
        # In a real implementation, these would be stored in a database
        # For now, we'll use in-memory dictionaries
        self.thresholds: Dict[str, AlertThreshold] = {}
        self.notifications: Dict[str, NotificationConfig] = {}
        self.alerts: Dict[str, Alert] = {}
        
        # Add default thresholds and notification configs
        self._add_default_thresholds()
        self._add_default_notifications()
        
        logger.info("Initialized alert service")
    
    def _add_default_thresholds(self):
        """Add default alert thresholds."""
        # System thresholds
        cpu_threshold = AlertThreshold(
            id="system-cpu",
            name="CPU Usage",
            description="Alert when CPU usage exceeds threshold",
            metric_name="cpu_usage",
            query='rate(process_cpu_seconds_total{job="orbithost"}[5m])',
            warning_threshold=0.7,
            critical_threshold=0.9,
        )
        
        memory_threshold = AlertThreshold(
            id="system-memory",
            name="Memory Usage",
            description="Alert when memory usage exceeds threshold",
            metric_name="memory_usage",
            query='process_resident_memory_bytes{job="orbithost"}',
            warning_threshold=1073741824,  # 1GB
            critical_threshold=2147483648,  # 2GB
        )
        
        # Application thresholds
        error_rate_threshold = AlertThreshold(
            id="app-error-rate",
            name="HTTP Error Rate",
            description="Alert when HTTP error rate exceeds threshold",
            metric_name="http_error_rate",
            query='sum(rate(http_requests_total{job="orbithost", status_code=~"5.."}[5m])) / sum(rate(http_requests_total{job="orbithost"}[5m])) * 100',
            warning_threshold=1.0,  # 1%
            critical_threshold=5.0,  # 5%
        )
        
        latency_threshold = AlertThreshold(
            id="app-latency",
            name="HTTP Latency",
            description="Alert when HTTP latency exceeds threshold",
            metric_name="http_latency",
            query='histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="orbithost"}[5m])) by (le))',
            warning_threshold=0.5,  # 500ms
            critical_threshold=1.0,  # 1s
        )
        
        # Deployment thresholds
        deployment_success_threshold = AlertThreshold(
            id="deployment-success-rate",
            name="Deployment Success Rate",
            description="Alert when deployment success rate falls below threshold",
            metric_name="deployment_success_rate",
            query='sum(deployments_total{status="success"}) / sum(deployments_total) * 100',
            warning_threshold=90.0,  # 90%
            critical_threshold=80.0,  # 80%
            comparison="less",
        )
        
        # AI service thresholds
        ai_error_threshold = AlertThreshold(
            id="ai-error-rate",
            name="AI Error Rate",
            description="Alert when AI error rate exceeds threshold",
            metric_name="ai_error_rate",
            query='sum(rate(ai_requests_total{status="error"}[5m])) / sum(rate(ai_requests_total[5m])) * 100',
            warning_threshold=5.0,  # 5%
            critical_threshold=10.0,  # 10%
        )
        
        ai_latency_threshold = AlertThreshold(
            id="ai-latency",
            name="AI Response Time",
            description="Alert when AI response time exceeds threshold",
            metric_name="ai_latency",
            query='histogram_quantile(0.95, sum(rate(ai_response_time_seconds_bucket{job="orbithost"}[5m])) by (le))',
            warning_threshold=2.0,  # 2s
            critical_threshold=5.0,  # 5s
        )
        
        # Add thresholds to dictionary
        self.thresholds[cpu_threshold.id] = cpu_threshold
        self.thresholds[memory_threshold.id] = memory_threshold
        self.thresholds[error_rate_threshold.id] = error_rate_threshold
        self.thresholds[latency_threshold.id] = latency_threshold
        self.thresholds[deployment_success_threshold.id] = deployment_success_threshold
        self.thresholds[ai_error_threshold.id] = ai_error_threshold
        self.thresholds[ai_latency_threshold.id] = ai_latency_threshold
    
    def _add_default_notifications(self):
        """Add default notification configurations."""
        # Email notification
        email_config = NotificationConfig(
            id="email-notification",
            name="Email Notification",
            channel=NotificationChannel.EMAIL,
            config={
                "recipients": ["admin@orbithost.example.com"],
                "subject_template": "[{severity}] OrbitHost Alert: {name}",
                "body_template": "Alert: {name}\nSeverity: {severity}\nValue: {value}\nMessage: {message}\nTime: {time}",
            },
        )
        
        # Slack notification
        slack_config = NotificationConfig(
            id="slack-notification",
            name="Slack Notification",
            channel=NotificationChannel.SLACK,
            config={
                "webhook_url": "https://hooks.slack.com/services/EXAMPLE/WEBHOOK/URL",
                "channel": "#alerts",
                "username": "OrbitHost Alerts",
                "icon_emoji": ":warning:",
                "message_template": "*[{severity}] {name}*\nValue: {value}\nMessage: {message}\nTime: {time}",
            },
        )
        
        # Webhook notification
        webhook_config = NotificationConfig(
            id="webhook-notification",
            name="Webhook Notification",
            channel=NotificationChannel.WEBHOOK,
            config={
                "url": "https://example.com/webhook",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body_template": {
                    "alert_id": "{id}",
                    "name": "{name}",
                    "severity": "{severity}",
                    "value": "{value}",
                    "message": "{message}",
                    "time": "{time}",
                },
            },
        )
        
        # Add notification configs to dictionary
        self.notifications[email_config.id] = email_config
        self.notifications[slack_config.id] = slack_config
        self.notifications[webhook_config.id] = webhook_config
    
    async def create_threshold(self, threshold: AlertThreshold) -> AlertThreshold:
        """
        Create a new alert threshold.
        
        Args:
            threshold: Alert threshold to create
            
        Returns:
            Created alert threshold
        """
        # Store threshold
        self.thresholds[threshold.id] = threshold
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "alert_threshold",
            "operation": "create",
            "threshold_id": threshold.id,
            "name": threshold.name,
            "metric_name": threshold.metric_name,
        })
        
        logger.info(f"Created alert threshold {threshold.id}")
        
        return threshold
    
    async def get_threshold(self, threshold_id: str) -> Optional[AlertThreshold]:
        """
        Get an alert threshold by ID.
        
        Args:
            threshold_id: ID of the threshold to get
            
        Returns:
            Alert threshold or None if not found
        """
        return self.thresholds.get(threshold_id)
    
    async def update_threshold(self, threshold: AlertThreshold) -> AlertThreshold:
        """
        Update an alert threshold.
        
        Args:
            threshold: Alert threshold to update
            
        Returns:
            Updated alert threshold
        """
        # Check if threshold exists
        if threshold.id not in self.thresholds:
            raise ValueError(f"Threshold {threshold.id} not found")
        
        # Update threshold
        self.thresholds[threshold.id] = threshold
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "alert_threshold",
            "operation": "update",
            "threshold_id": threshold.id,
            "name": threshold.name,
            "metric_name": threshold.metric_name,
        })
        
        logger.info(f"Updated alert threshold {threshold.id}")
        
        return threshold
    
    async def delete_threshold(self, threshold_id: str) -> bool:
        """
        Delete an alert threshold.
        
        Args:
            threshold_id: ID of the threshold to delete
            
        Returns:
            Boolean indicating success or failure
        """
        # Check if threshold exists
        if threshold_id not in self.thresholds:
            return False
        
        # Get threshold for logging
        threshold = self.thresholds[threshold_id]
        
        # Delete threshold
        del self.thresholds[threshold_id]
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "alert_threshold",
            "operation": "delete",
            "threshold_id": threshold_id,
            "name": threshold.name,
            "metric_name": threshold.metric_name,
        })
        
        logger.info(f"Deleted alert threshold {threshold_id}")
        
        return True
    
    async def list_thresholds(self) -> List[AlertThreshold]:
        """
        List alert thresholds.
        
        Returns:
            List of alert thresholds
        """
        return list(self.thresholds.values())
    
    async def create_notification(self, notification: NotificationConfig) -> NotificationConfig:
        """
        Create a new notification configuration.
        
        Args:
            notification: Notification configuration to create
            
        Returns:
            Created notification configuration
        """
        # Store notification config
        self.notifications[notification.id] = notification
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "notification_config",
            "operation": "create",
            "config_id": notification.id,
            "name": notification.name,
            "channel": notification.channel.value,
        })
        
        logger.info(f"Created notification configuration {notification.id}")
        
        return notification
    
    async def get_notification(self, notification_id: str) -> Optional[NotificationConfig]:
        """
        Get a notification configuration by ID.
        
        Args:
            notification_id: ID of the notification configuration to get
            
        Returns:
            Notification configuration or None if not found
        """
        return self.notifications.get(notification_id)
    
    async def update_notification(self, notification: NotificationConfig) -> NotificationConfig:
        """
        Update a notification configuration.
        
        Args:
            notification: Notification configuration to update
            
        Returns:
            Updated notification configuration
        """
        # Check if notification config exists
        if notification.id not in self.notifications:
            raise ValueError(f"Notification configuration {notification.id} not found")
        
        # Update notification config
        self.notifications[notification.id] = notification
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "notification_config",
            "operation": "update",
            "config_id": notification.id,
            "name": notification.name,
            "channel": notification.channel.value,
        })
        
        logger.info(f"Updated notification configuration {notification.id}")
        
        return notification
    
    async def delete_notification(self, notification_id: str) -> bool:
        """
        Delete a notification configuration.
        
        Args:
            notification_id: ID of the notification configuration to delete
            
        Returns:
            Boolean indicating success or failure
        """
        # Check if notification config exists
        if notification_id not in self.notifications:
            return False
        
        # Get notification config for logging
        notification = self.notifications[notification_id]
        
        # Delete notification config
        del self.notifications[notification_id]
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "notification_config",
            "operation": "delete",
            "config_id": notification_id,
            "name": notification.name,
            "channel": notification.channel.value,
        })
        
        logger.info(f"Deleted notification configuration {notification_id}")
        
        return True
    
    async def list_notifications(self) -> List[NotificationConfig]:
        """
        List notification configurations.
        
        Returns:
            List of notification configurations
        """
        return list(self.notifications.values())
    
    async def create_alert(self, alert: Alert) -> Alert:
        """
        Create a new alert.
        
        Args:
            alert: Alert to create
            
        Returns:
            Created alert
        """
        # Store alert
        self.alerts[alert.id] = alert
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "alert",
            "operation": "create",
            "alert_id": alert.id,
            "threshold_id": alert.threshold_id,
            "severity": alert.severity.value,
            "status": alert.status.value,
        })
        
        logger.info(f"Created alert {alert.id}")
        
        # Send notification if not already sent
        if not alert.notification_sent:
            await self.send_notification(alert)
        
        return alert
    
    async def get_alert(self, alert_id: str) -> Optional[Alert]:
        """
        Get an alert by ID.
        
        Args:
            alert_id: ID of the alert to get
            
        Returns:
            Alert or None if not found
        """
        return self.alerts.get(alert_id)
    
    async def update_alert(self, alert: Alert) -> Alert:
        """
        Update an alert.
        
        Args:
            alert: Alert to update
            
        Returns:
            Updated alert
        """
        # Check if alert exists
        if alert.id not in self.alerts:
            raise ValueError(f"Alert {alert.id} not found")
        
        # Get existing alert
        existing_alert = self.alerts[alert.id]
        
        # Update alert
        alert.updated_at = datetime.utcnow()
        self.alerts[alert.id] = alert
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "alert",
            "operation": "update",
            "alert_id": alert.id,
            "threshold_id": alert.threshold_id,
            "severity": alert.severity.value,
            "status": alert.status.value,
        })
        
        logger.info(f"Updated alert {alert.id}")
        
        # Send notification if status changed
        if existing_alert.status != alert.status and not alert.notification_sent:
            await self.send_notification(alert)
        
        return alert
    
    async def acknowledge_alert(self, alert_id: str, user_id: str) -> Alert:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: ID of the alert to acknowledge
            user_id: ID of the user acknowledging the alert
            
        Returns:
            Updated alert
        """
        # Get alert
        alert = await self.get_alert(alert_id)
        
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")
        
        # Update alert
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = user_id
        alert.updated_at = datetime.utcnow()
        
        # Store updated alert
        self.alerts[alert_id] = alert
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "alert",
            "operation": "acknowledge",
            "alert_id": alert_id,
            "user_id": user_id,
        })
        
        logger.info(f"Acknowledged alert {alert_id}")
        
        return alert
    
    async def resolve_alert(self, alert_id: str, user_id: str) -> Alert:
        """
        Resolve an alert.
        
        Args:
            alert_id: ID of the alert to resolve
            user_id: ID of the user resolving the alert
            
        Returns:
            Updated alert
        """
        # Get alert
        alert = await self.get_alert(alert_id)
        
        if not alert:
            raise ValueError(f"Alert {alert_id} not found")
        
        # Update alert
        alert.status = AlertStatus.RESOLVED
        alert.resolved_by = user_id
        alert.updated_at = datetime.utcnow()
        
        # Store updated alert
        self.alerts[alert_id] = alert
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "alert",
            "operation": "resolve",
            "alert_id": alert_id,
            "user_id": user_id,
        })
        
        logger.info(f"Resolved alert {alert_id}")
        
        return alert
    
    async def list_alerts(
        self,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
    ) -> List[Alert]:
        """
        List alerts.
        
        Args:
            status: Filter by status
            severity: Filter by severity
            
        Returns:
            List of alerts
        """
        alerts = list(self.alerts.values())
        
        # Apply filters
        if status:
            alerts = [a for a in alerts if a.status == status]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        return alerts
    
    async def send_notification(self, alert: Alert) -> bool:
        """
        Send a notification for an alert.
        
        Args:
            alert: Alert to send notification for
            
        Returns:
            Boolean indicating success or failure
        """
        # In a real implementation, this would send notifications to configured channels
        # For now, we'll just log the notification
        
        # Get threshold
        threshold = await self.get_threshold(alert.threshold_id)
        
        if not threshold:
            logger.error(f"Threshold {alert.threshold_id} not found")
            return False
        
        # Log notification
        logger.info(f"Sending notification for alert {alert.id} ({threshold.name})")
        
        # Mark alert as notified
        alert.notification_sent = True
        self.alerts[alert.id] = alert
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "alert_notification",
            "alert_id": alert.id,
            "threshold_id": alert.threshold_id,
            "severity": alert.severity.value,
            "status": alert.status.value,
        })
        
        return True
    
    async def test_notification(
        self,
        notification_id: str,
        message: str = "This is a test notification",
    ) -> bool:
        """
        Test a notification configuration.
        
        Args:
            notification_id: ID of the notification configuration to test
            message: Test message
            
        Returns:
            Boolean indicating success or failure
        """
        # Get notification config
        notification = await self.get_notification(notification_id)
        
        if not notification:
            logger.error(f"Notification configuration {notification_id} not found")
            return False
        
        # In a real implementation, this would send a test notification
        # For now, we'll just log the test
        
        # Log test
        logger.info(f"Testing notification {notification_id} ({notification.name}): {message}")
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "notification_test",
            "config_id": notification_id,
            "channel": notification.channel.value,
            "message": message,
        })
        
        return True


# Global alert service instance
_alert_service = None

async def get_alert_service() -> AlertService:
    """
    Get the alert service instance.
    
    Returns:
        Alert service instance
    """
    global _alert_service
    
    if _alert_service is None:
        _alert_service = AlertService()
    
    return _alert_service
