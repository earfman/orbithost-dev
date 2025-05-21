"""
Operational dashboards for OrbitHost observability.

This module provides functionality for creating and managing operational dashboards
that visualize metrics, logs, and traces from OrbitHost services.
"""
import json
import logging
import os
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union

from app.utils.mcp.client import get_mcp_client

logger = logging.getLogger(__name__)

class MetricType(str, Enum):
    """Types of metrics for dashboards."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"

class VisualizationType(str, Enum):
    """Types of visualizations for dashboard panels."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    TABLE = "table"
    STAT = "stat"
    HEATMAP = "heatmap"
    LOGS = "logs"
    TRACES = "traces"

class TimeRange(str, Enum):
    """Time ranges for dashboard panels."""
    LAST_5M = "5m"
    LAST_15M = "15m"
    LAST_30M = "30m"
    LAST_1H = "1h"
    LAST_3H = "3h"
    LAST_6H = "6h"
    LAST_12H = "12h"
    LAST_24H = "24h"
    LAST_2D = "2d"
    LAST_7D = "7d"
    LAST_30D = "30d"
    LAST_90D = "90d"

class DashboardPanel:
    """Model for dashboard panels."""
    
    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        visualization_type: VisualizationType,
        query: str,
        time_range: TimeRange = TimeRange.LAST_1H,
        refresh_interval: int = 60,  # seconds
        width: int = 6,  # 1-12 grid system
        height: int = 8,  # in grid units
        position: Optional[Dict[str, int]] = None,
        thresholds: Optional[Dict[str, float]] = None,
    ):
        """
        Initialize a dashboard panel.
        
        Args:
            id: Panel ID
            title: Panel title
            description: Panel description
            visualization_type: Type of visualization
            query: Query for the panel (PromQL, LogQL, etc.)
            time_range: Time range for the panel
            refresh_interval: Refresh interval in seconds
            width: Panel width in grid units (1-12)
            height: Panel height in grid units
            position: Panel position (x, y coordinates)
            thresholds: Warning and critical thresholds
        """
        self.id = id
        self.title = title
        self.description = description
        self.visualization_type = visualization_type
        self.query = query
        self.time_range = time_range
        self.refresh_interval = refresh_interval
        self.width = width
        self.height = height
        self.position = position or {"x": 0, "y": 0}
        self.thresholds = thresholds or {"warning": None, "critical": None}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "visualization_type": self.visualization_type.value,
            "query": self.query,
            "time_range": self.time_range.value,
            "refresh_interval": self.refresh_interval,
            "width": self.width,
            "height": self.height,
            "position": self.position,
            "thresholds": self.thresholds,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DashboardPanel":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            visualization_type=VisualizationType(data["visualization_type"]),
            query=data["query"],
            time_range=TimeRange(data["time_range"]) if "time_range" in data else TimeRange.LAST_1H,
            refresh_interval=data.get("refresh_interval", 60),
            width=data.get("width", 6),
            height=data.get("height", 8),
            position=data.get("position"),
            thresholds=data.get("thresholds"),
        )

class Dashboard:
    """Model for operational dashboards."""
    
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        panels: List[DashboardPanel],
        tags: List[str] = None,
        created_at: datetime = None,
        updated_at: datetime = None,
    ):
        """
        Initialize a dashboard.
        
        Args:
            id: Dashboard ID
            name: Dashboard name
            description: Dashboard description
            panels: List of dashboard panels
            tags: List of tags
            created_at: Creation timestamp
            updated_at: Last update timestamp
        """
        self.id = id
        self.name = name
        self.description = description
        self.panels = panels
        self.tags = tags or []
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "panels": [panel.to_dict() for panel in self.panels],
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Dashboard":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            panels=[DashboardPanel.from_dict(panel) for panel in data["panels"]],
            tags=data.get("tags", []),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else None,
        )

class DashboardService:
    """
    Service for managing operational dashboards.
    
    This service provides functionality for creating, retrieving, updating,
    and deleting operational dashboards, as well as managing dashboard panels.
    """
    
    def __init__(self):
        """Initialize the dashboard service."""
        # In a real implementation, dashboards would be stored in a database
        # For now, we'll use an in-memory dictionary
        self.dashboards: Dict[str, Dashboard] = {}
        
        # Add default dashboards
        self._add_default_dashboards()
        
        logger.info("Initialized dashboard service")
    
    def _add_default_dashboards(self):
        """Add default dashboards."""
        # System Overview Dashboard
        system_panels = [
            DashboardPanel(
                id="system-cpu",
                title="CPU Usage",
                description="CPU usage across all services",
                visualization_type=VisualizationType.LINE,
                query='rate(process_cpu_seconds_total{job="orbithost"}[5m])',
                position={"x": 0, "y": 0},
                thresholds={"warning": 0.7, "critical": 0.9},
            ),
            DashboardPanel(
                id="system-memory",
                title="Memory Usage",
                description="Memory usage across all services",
                visualization_type=VisualizationType.LINE,
                query='process_resident_memory_bytes{job="orbithost"}',
                position={"x": 6, "y": 0},
                thresholds={"warning": 1073741824, "critical": 2147483648},  # 1GB, 2GB
            ),
            DashboardPanel(
                id="system-http-requests",
                title="HTTP Request Rate",
                description="HTTP request rate across all services",
                visualization_type=VisualizationType.LINE,
                query='sum(rate(http_requests_total{job="orbithost"}[5m])) by (service)',
                position={"x": 0, "y": 8},
            ),
            DashboardPanel(
                id="system-http-errors",
                title="HTTP Error Rate",
                description="HTTP error rate across all services",
                visualization_type=VisualizationType.LINE,
                query='sum(rate(http_requests_total{job="orbithost", status_code=~"5.."}[5m])) by (service)',
                position={"x": 6, "y": 8},
                thresholds={"warning": 0.01, "critical": 0.05},  # 1%, 5%
            ),
        ]
        
        system_dashboard = Dashboard(
            id="system-overview",
            name="System Overview",
            description="Overview of system metrics",
            panels=system_panels,
            tags=["system", "overview"],
        )
        
        # Deployment Dashboard
        deployment_panels = [
            DashboardPanel(
                id="deployment-rate",
                title="Deployment Rate",
                description="Deployments per hour",
                visualization_type=VisualizationType.BAR,
                query='sum(increase(deployments_total[1h])) by (status)',
                position={"x": 0, "y": 0},
            ),
            DashboardPanel(
                id="deployment-duration",
                title="Deployment Duration",
                description="Time taken for deployments",
                visualization_type=VisualizationType.HISTOGRAM,
                query='deployment_duration_seconds_bucket{job="orbithost"}',
                position={"x": 6, "y": 0},
            ),
            DashboardPanel(
                id="deployment-success-rate",
                title="Deployment Success Rate",
                description="Percentage of successful deployments",
                visualization_type=VisualizationType.STAT,
                query='sum(deployments_total{status="success"}) / sum(deployments_total) * 100',
                position={"x": 0, "y": 8},
                thresholds={"warning": 90, "critical": 80},  # 90%, 80%
            ),
            DashboardPanel(
                id="deployment-errors",
                title="Deployment Errors",
                description="Recent deployment errors",
                visualization_type=VisualizationType.TABLE,
                query='deployments_total{status="error"}',
                position={"x": 6, "y": 8},
            ),
        ]
        
        deployment_dashboard = Dashboard(
            id="deployment-metrics",
            name="Deployment Metrics",
            description="Metrics for deployments",
            panels=deployment_panels,
            tags=["deployment", "metrics"],
        )
        
        # AI Integration Dashboard
        ai_panels = [
            DashboardPanel(
                id="ai-requests",
                title="AI Requests",
                description="Requests to AI services",
                visualization_type=VisualizationType.LINE,
                query='sum(rate(ai_requests_total[5m])) by (service)',
                position={"x": 0, "y": 0},
            ),
            DashboardPanel(
                id="ai-latency",
                title="AI Response Time",
                description="Response time for AI services",
                visualization_type=VisualizationType.HEATMAP,
                query='ai_response_time_seconds_bucket{job="orbithost"}',
                position={"x": 6, "y": 0},
                thresholds={"warning": 2, "critical": 5},  # 2s, 5s
            ),
            DashboardPanel(
                id="ai-errors",
                title="AI Error Rate",
                description="Error rate for AI services",
                visualization_type=VisualizationType.LINE,
                query='sum(rate(ai_requests_total{status="error"}[5m])) by (service) / sum(rate(ai_requests_total[5m])) by (service) * 100',
                position={"x": 0, "y": 8},
                thresholds={"warning": 5, "critical": 10},  # 5%, 10%
            ),
            DashboardPanel(
                id="ai-tokens",
                title="AI Token Usage",
                description="Token usage for AI services",
                visualization_type=VisualizationType.BAR,
                query='sum(increase(ai_tokens_total[1d])) by (service)',
                position={"x": 6, "y": 8},
            ),
        ]
        
        ai_dashboard = Dashboard(
            id="ai-integration",
            name="AI Integration",
            description="Metrics for AI integration",
            panels=ai_panels,
            tags=["ai", "integration"],
        )
        
        # Add dashboards to dictionary
        self.dashboards[system_dashboard.id] = system_dashboard
        self.dashboards[deployment_dashboard.id] = deployment_dashboard
        self.dashboards[ai_dashboard.id] = ai_dashboard
    
    async def create_dashboard(self, dashboard: Dashboard) -> Dashboard:
        """
        Create a new dashboard.
        
        Args:
            dashboard: Dashboard to create
            
        Returns:
            Created dashboard
        """
        # Store dashboard
        self.dashboards[dashboard.id] = dashboard
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dashboard",
            "operation": "create",
            "dashboard_id": dashboard.id,
            "name": dashboard.name,
            "panel_count": len(dashboard.panels),
        })
        
        logger.info(f"Created dashboard {dashboard.id}")
        
        return dashboard
    
    async def get_dashboard(self, dashboard_id: str) -> Optional[Dashboard]:
        """
        Get a dashboard by ID.
        
        Args:
            dashboard_id: ID of the dashboard to get
            
        Returns:
            Dashboard or None if not found
        """
        return self.dashboards.get(dashboard_id)
    
    async def update_dashboard(self, dashboard: Dashboard) -> Dashboard:
        """
        Update a dashboard.
        
        Args:
            dashboard: Dashboard to update
            
        Returns:
            Updated dashboard
        """
        # Check if dashboard exists
        if dashboard.id not in self.dashboards:
            raise ValueError(f"Dashboard {dashboard.id} not found")
        
        # Update dashboard
        dashboard.updated_at = datetime.utcnow()
        self.dashboards[dashboard.id] = dashboard
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dashboard",
            "operation": "update",
            "dashboard_id": dashboard.id,
            "name": dashboard.name,
            "panel_count": len(dashboard.panels),
        })
        
        logger.info(f"Updated dashboard {dashboard.id}")
        
        return dashboard
    
    async def delete_dashboard(self, dashboard_id: str) -> bool:
        """
        Delete a dashboard.
        
        Args:
            dashboard_id: ID of the dashboard to delete
            
        Returns:
            Boolean indicating success or failure
        """
        # Check if dashboard exists
        if dashboard_id not in self.dashboards:
            return False
        
        # Get dashboard for logging
        dashboard = self.dashboards[dashboard_id]
        
        # Delete dashboard
        del self.dashboards[dashboard_id]
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dashboard",
            "operation": "delete",
            "dashboard_id": dashboard_id,
            "name": dashboard.name,
        })
        
        logger.info(f"Deleted dashboard {dashboard_id}")
        
        return True
    
    async def list_dashboards(
        self,
        tags: Optional[List[str]] = None,
    ) -> List[Dashboard]:
        """
        List dashboards.
        
        Args:
            tags: Filter by tags
            
        Returns:
            List of dashboards
        """
        dashboards = list(self.dashboards.values())
        
        # Apply filters
        if tags:
            dashboards = [d for d in dashboards if any(tag in d.tags for tag in tags)]
        
        return dashboards
    
    async def add_panel(
        self,
        dashboard_id: str,
        panel: DashboardPanel,
    ) -> Dashboard:
        """
        Add a panel to a dashboard.
        
        Args:
            dashboard_id: ID of the dashboard to add the panel to
            panel: Panel to add
            
        Returns:
            Updated dashboard
        """
        # Get dashboard
        dashboard = await self.get_dashboard(dashboard_id)
        
        if not dashboard:
            raise ValueError(f"Dashboard {dashboard_id} not found")
        
        # Add panel
        dashboard.panels.append(panel)
        dashboard.updated_at = datetime.utcnow()
        
        # Update dashboard
        self.dashboards[dashboard_id] = dashboard
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dashboard_panel",
            "operation": "add",
            "dashboard_id": dashboard_id,
            "panel_id": panel.id,
            "panel_title": panel.title,
        })
        
        logger.info(f"Added panel {panel.id} to dashboard {dashboard_id}")
        
        return dashboard
    
    async def update_panel(
        self,
        dashboard_id: str,
        panel: DashboardPanel,
    ) -> Dashboard:
        """
        Update a panel in a dashboard.
        
        Args:
            dashboard_id: ID of the dashboard to update the panel in
            panel: Panel to update
            
        Returns:
            Updated dashboard
        """
        # Get dashboard
        dashboard = await self.get_dashboard(dashboard_id)
        
        if not dashboard:
            raise ValueError(f"Dashboard {dashboard_id} not found")
        
        # Find panel
        panel_index = None
        for i, p in enumerate(dashboard.panels):
            if p.id == panel.id:
                panel_index = i
                break
        
        if panel_index is None:
            raise ValueError(f"Panel {panel.id} not found in dashboard {dashboard_id}")
        
        # Update panel
        dashboard.panels[panel_index] = panel
        dashboard.updated_at = datetime.utcnow()
        
        # Update dashboard
        self.dashboards[dashboard_id] = dashboard
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dashboard_panel",
            "operation": "update",
            "dashboard_id": dashboard_id,
            "panel_id": panel.id,
            "panel_title": panel.title,
        })
        
        logger.info(f"Updated panel {panel.id} in dashboard {dashboard_id}")
        
        return dashboard
    
    async def delete_panel(
        self,
        dashboard_id: str,
        panel_id: str,
    ) -> Dashboard:
        """
        Delete a panel from a dashboard.
        
        Args:
            dashboard_id: ID of the dashboard to delete the panel from
            panel_id: ID of the panel to delete
            
        Returns:
            Updated dashboard
        """
        # Get dashboard
        dashboard = await self.get_dashboard(dashboard_id)
        
        if not dashboard:
            raise ValueError(f"Dashboard {dashboard_id} not found")
        
        # Find panel
        panel_index = None
        panel_title = None
        for i, p in enumerate(dashboard.panels):
            if p.id == panel_id:
                panel_index = i
                panel_title = p.title
                break
        
        if panel_index is None:
            raise ValueError(f"Panel {panel_id} not found in dashboard {dashboard_id}")
        
        # Delete panel
        dashboard.panels.pop(panel_index)
        dashboard.updated_at = datetime.utcnow()
        
        # Update dashboard
        self.dashboards[dashboard_id] = dashboard
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dashboard_panel",
            "operation": "delete",
            "dashboard_id": dashboard_id,
            "panel_id": panel_id,
            "panel_title": panel_title,
        })
        
        logger.info(f"Deleted panel {panel_id} from dashboard {dashboard_id}")
        
        return dashboard
    
    async def export_dashboard(self, dashboard_id: str) -> Dict[str, Any]:
        """
        Export a dashboard to JSON.
        
        Args:
            dashboard_id: ID of the dashboard to export
            
        Returns:
            Dashboard as JSON
        """
        # Get dashboard
        dashboard = await self.get_dashboard(dashboard_id)
        
        if not dashboard:
            raise ValueError(f"Dashboard {dashboard_id} not found")
        
        # Export dashboard
        return dashboard.to_dict()
    
    async def import_dashboard(self, dashboard_json: Dict[str, Any]) -> Dashboard:
        """
        Import a dashboard from JSON.
        
        Args:
            dashboard_json: Dashboard as JSON
            
        Returns:
            Imported dashboard
        """
        # Create dashboard
        dashboard = Dashboard.from_dict(dashboard_json)
        
        # Store dashboard
        self.dashboards[dashboard.id] = dashboard
        
        # Log to MCP
        await get_mcp_client().send({
            "type": "dashboard",
            "operation": "import",
            "dashboard_id": dashboard.id,
            "name": dashboard.name,
            "panel_count": len(dashboard.panels),
        })
        
        logger.info(f"Imported dashboard {dashboard.id}")
        
        return dashboard


# Global dashboard service instance
_dashboard_service = None

async def get_dashboard_service() -> DashboardService:
    """
    Get the dashboard service instance.
    
    Returns:
        Dashboard service instance
    """
    global _dashboard_service
    
    if _dashboard_service is None:
        _dashboard_service = DashboardService()
    
    return _dashboard_service
