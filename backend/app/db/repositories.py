"""
Repository layer for database operations.

This module provides repository classes for each model to handle database operations.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic

from pydantic import BaseModel

from app.db.supabase_client import (
    insert_data,
    update_data,
    delete_data,
    select_data,
    select_by_id,
)

# Configure logging
logger = logging.getLogger(__name__)

# Generic type for models
T = TypeVar('T', bound=BaseModel)


class BaseRepository(Generic[T]):
    """Base repository for database operations."""
    
    def __init__(self, model_class: Type[T], table_name: str):
        """
        Initialize the repository.
        
        Args:
            model_class: Pydantic model class
            table_name: Supabase table name
        """
        self.model_class = model_class
        self.table_name = table_name
    
    async def create(self, data: Dict[str, Any]) -> T:
        """
        Create a new record.
        
        Args:
            data: Record data
            
        Returns:
            Created record
        """
        try:
            result = await insert_data(self.table_name, data)
            return self.model_class(**result)
        except Exception as e:
            logger.error(f"Error creating {self.table_name} record: {str(e)}")
            raise
    
    async def update(self, id: str, data: Dict[str, Any]) -> T:
        """
        Update a record.
        
        Args:
            id: Record ID
            data: Updated data
            
        Returns:
            Updated record
        """
        try:
            # Add updated_at timestamp
            if "updated_at" not in data:
                data["updated_at"] = datetime.utcnow().isoformat()
                
            result = await update_data(self.table_name, "id", id, data)
            return self.model_class(**result)
        except Exception as e:
            logger.error(f"Error updating {self.table_name} record {id}: {str(e)}")
            raise
    
    async def delete(self, id: str) -> bool:
        """
        Delete a record.
        
        Args:
            id: Record ID
            
        Returns:
            True if successful
        """
        try:
            await delete_data(self.table_name, "id", id)
            return True
        except Exception as e:
            logger.error(f"Error deleting {self.table_name} record {id}: {str(e)}")
            raise
    
    async def get_by_id(self, id: str) -> Optional[T]:
        """
        Get a record by ID.
        
        Args:
            id: Record ID
            
        Returns:
            Record if found, None otherwise
        """
        try:
            result = await select_by_id(self.table_name, "id", id)
            return self.model_class(**result) if result else None
        except Exception as e:
            logger.error(f"Error getting {self.table_name} record {id}: {str(e)}")
            raise
    
    async def get_all(self, **filters) -> List[T]:
        """
        Get all records with optional filters.
        
        Args:
            **filters: Filters to apply
            
        Returns:
            List of records
        """
        try:
            results = await select_data(self.table_name, **filters)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting all {self.table_name} records: {str(e)}")
            raise


# Repository classes for each model
class UserRepository(BaseRepository['User']):
    """Repository for User model."""
    
    def __init__(self):
        """Initialize the repository."""
        from app.db.models import User
        super().__init__(User, "users")
    
    async def get_by_email(self, email: str) -> Optional['User']:
        """
        Get a user by email.
        
        Args:
            email: User email
            
        Returns:
            User if found, None otherwise
        """
        try:
            results = await select_data(self.table_name, email=email)
            return self.model_class(**results[0]) if results else None
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {str(e)}")
            raise


class TeamRepository(BaseRepository['Team']):
    """Repository for Team model."""
    
    def __init__(self):
        """Initialize the repository."""
        from app.db.models import Team
        super().__init__(Team, "teams")
    
    async def get_by_owner(self, owner_id: str) -> List['Team']:
        """
        Get teams by owner ID.
        
        Args:
            owner_id: Owner ID
            
        Returns:
            List of teams
        """
        try:
            results = await select_data(self.table_name, owner_id=owner_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting teams by owner {owner_id}: {str(e)}")
            raise


class TeamMemberRepository(BaseRepository['TeamMember']):
    """Repository for TeamMember model."""
    
    def __init__(self):
        """Initialize the repository."""
        from app.db.models import TeamMember
        super().__init__(TeamMember, "team_members")
    
    async def get_by_team(self, team_id: str) -> List['TeamMember']:
        """
        Get team members by team ID.
        
        Args:
            team_id: Team ID
            
        Returns:
            List of team members
        """
        try:
            results = await select_data(self.table_name, team_id=team_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting team members by team {team_id}: {str(e)}")
            raise
    
    async def get_by_user(self, user_id: str) -> List['TeamMember']:
        """
        Get team memberships by user ID.
        
        Args:
            user_id: User ID
            
        Returns:
            List of team memberships
        """
        try:
            results = await select_data(self.table_name, user_id=user_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting team memberships by user {user_id}: {str(e)}")
            raise


class ProjectRepository(BaseRepository['Project']):
    """Repository for Project model."""
    
    def __init__(self):
        """Initialize the repository."""
        from app.db.models import Project
        super().__init__(Project, "projects")
    
    async def get_by_owner(self, owner_id: str) -> List['Project']:
        """
        Get projects by owner ID.
        
        Args:
            owner_id: Owner ID
            
        Returns:
            List of projects
        """
        try:
            results = await select_data(self.table_name, owner_id=owner_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting projects by owner {owner_id}: {str(e)}")
            raise
    
    async def get_by_team(self, team_id: str) -> List['Project']:
        """
        Get projects by team ID.
        
        Args:
            team_id: Team ID
            
        Returns:
            List of projects
        """
        try:
            results = await select_data(self.table_name, team_id=team_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting projects by team {team_id}: {str(e)}")
            raise


class DeploymentRepository(BaseRepository['Deployment']):
    """Repository for Deployment model."""
    
    def __init__(self):
        """Initialize the repository."""
        from app.db.models import Deployment
        super().__init__(Deployment, "deployments")
    
    async def get_by_project(self, project_id: str) -> List['Deployment']:
        """
        Get deployments by project ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of deployments
        """
        try:
            results = await select_data(self.table_name, project_id=project_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting deployments by project {project_id}: {str(e)}")
            raise
    
    async def get_latest_by_project(self, project_id: str) -> Optional['Deployment']:
        """
        Get the latest deployment for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            Latest deployment if found, None otherwise
        """
        try:
            # This is a simplified implementation - in a real application,
            # you would use a more efficient query with ordering and limit
            deployments = await self.get_by_project(project_id)
            if not deployments:
                return None
            
            # Sort by created_at in descending order
            sorted_deployments = sorted(
                deployments,
                key=lambda d: d.created_at,
                reverse=True
            )
            
            return sorted_deployments[0] if sorted_deployments else None
        except Exception as e:
            logger.error(f"Error getting latest deployment for project {project_id}: {str(e)}")
            raise


class DomainRepository(BaseRepository['Domain']):
    """Repository for Domain model."""
    
    def __init__(self):
        """Initialize the repository."""
        from app.db.models import Domain
        super().__init__(Domain, "domains")
    
    async def get_by_user(self, user_id: str) -> List['Domain']:
        """
        Get domains by user ID.
        
        Args:
            user_id: User ID
            
        Returns:
            List of domains
        """
        try:
            results = await select_data(self.table_name, user_id=user_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting domains by user {user_id}: {str(e)}")
            raise
    
    async def get_by_project(self, project_id: str) -> List['Domain']:
        """
        Get domains by project ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of domains
        """
        try:
            results = await select_data(self.table_name, project_id=project_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting domains by project {project_id}: {str(e)}")
            raise
    
    async def get_by_name(self, name: str) -> Optional['Domain']:
        """
        Get a domain by name.
        
        Args:
            name: Domain name
            
        Returns:
            Domain if found, None otherwise
        """
        try:
            results = await select_data(self.table_name, name=name)
            return self.model_class(**results[0]) if results else None
        except Exception as e:
            logger.error(f"Error getting domain by name {name}: {str(e)}")
            raise


class DnsRecordRepository(BaseRepository['DnsRecord']):
    """Repository for DnsRecord model."""
    
    def __init__(self):
        """Initialize the repository."""
        from app.db.models import DnsRecord
        super().__init__(DnsRecord, "dns_records")
    
    async def get_by_domain(self, domain_id: str) -> List['DnsRecord']:
        """
        Get DNS records by domain ID.
        
        Args:
            domain_id: Domain ID
            
        Returns:
            List of DNS records
        """
        try:
            results = await select_data(self.table_name, domain_id=domain_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting DNS records by domain {domain_id}: {str(e)}")
            raise


class APICredentialRepository(BaseRepository['APICredential']):
    """Repository for APICredential model."""
    
    def __init__(self):
        """Initialize the repository."""
        from app.db.models import APICredential
        super().__init__(APICredential, "api_credentials")
    
    async def get_by_user(self, user_id: str) -> List['APICredential']:
        """
        Get API credentials by user ID.
        
        Args:
            user_id: User ID
            
        Returns:
            List of API credentials
        """
        try:
            results = await select_data(self.table_name, user_id=user_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting API credentials by user {user_id}: {str(e)}")
            raise
    
    async def get_by_provider(self, user_id: str, provider: str) -> List['APICredential']:
        """
        Get API credentials by user ID and provider.
        
        Args:
            user_id: User ID
            provider: Provider name
            
        Returns:
            List of API credentials
        """
        try:
            results = await select_data(self.table_name, user_id=user_id, provider=provider)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting API credentials by user {user_id} and provider {provider}: {str(e)}")
            raise


class SubscriptionRepository(BaseRepository['Subscription']):
    """Repository for Subscription model."""
    
    def __init__(self):
        """Initialize the repository."""
        from app.db.models import Subscription
        super().__init__(Subscription, "subscriptions")
    
    async def get_by_user(self, user_id: str) -> List['Subscription']:
        """
        Get subscriptions by user ID.
        
        Args:
            user_id: User ID
            
        Returns:
            List of subscriptions
        """
        try:
            results = await select_data(self.table_name, user_id=user_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting subscriptions by user {user_id}: {str(e)}")
            raise
    
    async def get_active_by_user(self, user_id: str) -> Optional['Subscription']:
        """
        Get the active subscription for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            Active subscription if found, None otherwise
        """
        try:
            results = await select_data(self.table_name, user_id=user_id, status="active")
            return self.model_class(**results[0]) if results else None
        except Exception as e:
            logger.error(f"Error getting active subscription for user {user_id}: {str(e)}")
            raise


class UsageMetricRepository(BaseRepository['UsageMetric']):
    """Repository for UsageMetric model."""
    
    def __init__(self):
        """Initialize the repository."""
        from app.db.models import UsageMetric
        super().__init__(UsageMetric, "usage_metrics")
    
    async def get_by_user(self, user_id: str) -> List['UsageMetric']:
        """
        Get usage metrics by user ID.
        
        Args:
            user_id: User ID
            
        Returns:
            List of usage metrics
        """
        try:
            results = await select_data(self.table_name, user_id=user_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting usage metrics by user {user_id}: {str(e)}")
            raise
    
    async def get_by_project(self, project_id: str) -> List['UsageMetric']:
        """
        Get usage metrics by project ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of usage metrics
        """
        try:
            results = await select_data(self.table_name, project_id=project_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting usage metrics by project {project_id}: {str(e)}")
            raise


class AIFeedbackRepository(BaseRepository['AIFeedback']):
    """Repository for AIFeedback model."""
    
    def __init__(self):
        """Initialize the repository."""
        from app.db.models import AIFeedback
        super().__init__(AIFeedback, "ai_feedback")
    
    async def get_by_deployment(self, deployment_id: str) -> List['AIFeedback']:
        """
        Get AI feedback by deployment ID.
        
        Args:
            deployment_id: Deployment ID
            
        Returns:
            List of AI feedback
        """
        try:
            results = await select_data(self.table_name, deployment_id=deployment_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting AI feedback by deployment {deployment_id}: {str(e)}")
            raise


class WebhookConfigurationRepository(BaseRepository['WebhookConfiguration']):
    """Repository for WebhookConfiguration model."""
    
    def __init__(self):
        """Initialize the repository."""
        from app.db.models import WebhookConfiguration
        super().__init__(WebhookConfiguration, "webhook_configurations")
    
    async def get_by_user(self, user_id: str) -> List['WebhookConfiguration']:
        """
        Get webhook configurations by user ID.
        
        Args:
            user_id: User ID
            
        Returns:
            List of webhook configurations
        """
        try:
            results = await select_data(self.table_name, user_id=user_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting webhook configurations by user {user_id}: {str(e)}")
            raise
    
    async def get_by_project(self, project_id: str) -> List['WebhookConfiguration']:
        """
        Get webhook configurations by project ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of webhook configurations
        """
        try:
            results = await select_data(self.table_name, project_id=project_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting webhook configurations by project {project_id}: {str(e)}")
            raise
    
    async def get_by_event(self, event: str) -> List['WebhookConfiguration']:
        """
        Get webhook configurations by event.
        
        Args:
            event: Event name
            
        Returns:
            List of webhook configurations
        """
        try:
            # This is a simplified implementation - in a real application,
            # you would use a more efficient query with array contains
            all_configs = await self.get_all()
            return [config for config in all_configs if event in config.events]
        except Exception as e:
            logger.error(f"Error getting webhook configurations by event {event}: {str(e)}")
            raise


class WebhookDeliveryRepository(BaseRepository['WebhookDelivery']):
    """Repository for WebhookDelivery model."""
    
    def __init__(self):
        """Initialize the repository."""
        from app.db.models import WebhookDelivery
        super().__init__(WebhookDelivery, "webhook_deliveries")
    
    async def get_by_webhook(self, webhook_id: str) -> List['WebhookDelivery']:
        """
        Get webhook deliveries by webhook ID.
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            List of webhook deliveries
        """
        try:
            results = await select_data(self.table_name, webhook_id=webhook_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting webhook deliveries by webhook {webhook_id}: {str(e)}")
            raise


class AlertRepository(BaseRepository['Alert']):
    """Repository for Alert model."""
    
    def __init__(self):
        """Initialize the repository."""
        from app.db.models import Alert
        super().__init__(Alert, "alerts")
    
    async def get_by_user(self, user_id: str) -> List['Alert']:
        """
        Get alerts by user ID.
        
        Args:
            user_id: User ID
            
        Returns:
            List of alerts
        """
        try:
            results = await select_data(self.table_name, user_id=user_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting alerts by user {user_id}: {str(e)}")
            raise
    
    async def get_by_project(self, project_id: str) -> List['Alert']:
        """
        Get alerts by project ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            List of alerts
        """
        try:
            results = await select_data(self.table_name, project_id=project_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting alerts by project {project_id}: {str(e)}")
            raise


class AlertEventRepository(BaseRepository['AlertEvent']):
    """Repository for AlertEvent model."""
    
    def __init__(self):
        """Initialize the repository."""
        from app.db.models import AlertEvent
        super().__init__(AlertEvent, "alert_events")
    
    async def get_by_alert(self, alert_id: str) -> List['AlertEvent']:
        """
        Get alert events by alert ID.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            List of alert events
        """
        try:
            results = await select_data(self.table_name, alert_id=alert_id)
            return [self.model_class(**result) for result in results]
        except Exception as e:
            logger.error(f"Error getting alert events by alert {alert_id}: {str(e)}")
            raise
    
    async def get_active_by_alert(self, alert_id: str) -> List['AlertEvent']:
        """
        Get active alert events by alert ID.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            List of active alert events
        """
        try:
            results = await select_data(self.table_name, alert_id=alert_id)
            return [
                self.model_class(**result)
                for result in results
                if not result.get("resolved_at")
            ]
        except Exception as e:
            logger.error(f"Error getting active alert events by alert {alert_id}: {str(e)}")
            raise
