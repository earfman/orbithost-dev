"""
Service layer for database operations.

This module provides service classes that use repositories to implement business logic.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from app.db.models import (
    User,
    Team,
    TeamMember,
    Project,
    Deployment,
    Domain,
    DnsRecord,
    APICredential,
    Subscription,
    UsageMetric,
    AIFeedback,
    WebhookConfiguration,
    WebhookDelivery,
    Alert,
    AlertEvent,
)
from app.db.repositories import (
    UserRepository,
    TeamRepository,
    TeamMemberRepository,
    ProjectRepository,
    DeploymentRepository,
    DomainRepository,
    DnsRecordRepository,
    APICredentialRepository,
    SubscriptionRepository,
    UsageMetricRepository,
    AIFeedbackRepository,
    WebhookConfigurationRepository,
    WebhookDeliveryRepository,
    AlertRepository,
    AlertEventRepository,
)

# Configure logging
logger = logging.getLogger(__name__)


class UserService:
    """Service for user operations."""
    
    def __init__(self):
        """Initialize the service."""
        self.repository = UserRepository()
    
    async def create_user(self, email: str, name: Optional[str] = None) -> User:
        """
        Create a new user.
        
        Args:
            email: User email
            name: User name
            
        Returns:
            Created user
        """
        try:
            # Check if user already exists
            existing_user = await self.repository.get_by_email(email)
            if existing_user:
                raise ValueError(f"User with email {email} already exists")
            
            # Create user
            user_data = {
                "email": email,
                "name": name,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            return await self.repository.create(user_data)
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """
        Get a user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User if found, None otherwise
        """
        try:
            return await self.repository.get_by_id(user_id)
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {str(e)}")
            raise
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email.
        
        Args:
            email: User email
            
        Returns:
            User if found, None otherwise
        """
        try:
            return await self.repository.get_by_email(email)
        except Exception as e:
            logger.error(f"Error getting user by email {email}: {str(e)}")
            raise
    
    async def update_user(self, user_id: str, data: Dict[str, Any]) -> User:
        """
        Update a user.
        
        Args:
            user_id: User ID
            data: Updated data
            
        Returns:
            Updated user
        """
        try:
            # Check if user exists
            user = await self.repository.get_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Update user
            return await self.repository.update(user_id, data)
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {str(e)}")
            raise
    
    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if successful
        """
        try:
            # Check if user exists
            user = await self.repository.get_by_id(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Delete user
            return await self.repository.delete(user_id)
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            raise


class TeamService:
    """Service for team operations."""
    
    def __init__(self):
        """Initialize the service."""
        self.repository = TeamRepository()
        self.member_repository = TeamMemberRepository()
        self.user_service = UserService()
    
    async def create_team(self, name: str, owner_id: str) -> Team:
        """
        Create a new team.
        
        Args:
            name: Team name
            owner_id: Owner ID
            
        Returns:
            Created team
        """
        try:
            # Check if owner exists
            owner = await self.user_service.get_user(owner_id)
            if not owner:
                raise ValueError(f"User {owner_id} not found")
            
            # Create team
            team_data = {
                "name": name,
                "owner_id": owner_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            team = await self.repository.create(team_data)
            
            # Add owner as team member with owner role
            member_data = {
                "team_id": team.id,
                "user_id": owner_id,
                "role": "owner",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            await self.member_repository.create(member_data)
            
            return team
        except Exception as e:
            logger.error(f"Error creating team: {str(e)}")
            raise
    
    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get a team by ID.
        
        Args:
            team_id: Team ID
            
        Returns:
            Team if found, None otherwise
        """
        try:
            return await self.repository.get_by_id(team_id)
        except Exception as e:
            logger.error(f"Error getting team {team_id}: {str(e)}")
            raise
    
    async def get_teams_by_owner(self, owner_id: str) -> List[Team]:
        """
        Get teams by owner ID.
        
        Args:
            owner_id: Owner ID
            
        Returns:
            List of teams
        """
        try:
            return await self.repository.get_by_owner(owner_id)
        except Exception as e:
            logger.error(f"Error getting teams by owner {owner_id}: {str(e)}")
            raise
    
    async def get_teams_by_user(self, user_id: str) -> List[Team]:
        """
        Get teams that a user is a member of.
        
        Args:
            user_id: User ID
            
        Returns:
            List of teams
        """
        try:
            # Get team memberships
            memberships = await self.member_repository.get_by_user(user_id)
            
            # Get teams
            teams = []
            for membership in memberships:
                team = await self.repository.get_by_id(membership.team_id)
                if team:
                    teams.append(team)
            
            return teams
        except Exception as e:
            logger.error(f"Error getting teams by user {user_id}: {str(e)}")
            raise
    
    async def update_team(self, team_id: str, data: Dict[str, Any]) -> Team:
        """
        Update a team.
        
        Args:
            team_id: Team ID
            data: Updated data
            
        Returns:
            Updated team
        """
        try:
            # Check if team exists
            team = await self.repository.get_by_id(team_id)
            if not team:
                raise ValueError(f"Team {team_id} not found")
            
            # Update team
            return await self.repository.update(team_id, data)
        except Exception as e:
            logger.error(f"Error updating team {team_id}: {str(e)}")
            raise
    
    async def delete_team(self, team_id: str) -> bool:
        """
        Delete a team.
        
        Args:
            team_id: Team ID
            
        Returns:
            True if successful
        """
        try:
            # Check if team exists
            team = await self.repository.get_by_id(team_id)
            if not team:
                raise ValueError(f"Team {team_id} not found")
            
            # Get team members
            members = await self.member_repository.get_by_team(team_id)
            
            # Delete team members
            for member in members:
                await self.member_repository.delete(member.id)
            
            # Delete team
            return await self.repository.delete(team_id)
        except Exception as e:
            logger.error(f"Error deleting team {team_id}: {str(e)}")
            raise
    
    async def add_team_member(self, team_id: str, user_id: str, role: str = "member") -> TeamMember:
        """
        Add a member to a team.
        
        Args:
            team_id: Team ID
            user_id: User ID
            role: Member role
            
        Returns:
            Team member
        """
        try:
            # Check if team exists
            team = await self.repository.get_by_id(team_id)
            if not team:
                raise ValueError(f"Team {team_id} not found")
            
            # Check if user exists
            user = await self.user_service.get_user(user_id)
            if not user:
                raise ValueError(f"User {user_id} not found")
            
            # Check if user is already a member
            memberships = await self.member_repository.get_by_user(user_id)
            for membership in memberships:
                if membership.team_id == team_id:
                    raise ValueError(f"User {user_id} is already a member of team {team_id}")
            
            # Add member
            member_data = {
                "team_id": team_id,
                "user_id": user_id,
                "role": role,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            return await self.member_repository.create(member_data)
        except Exception as e:
            logger.error(f"Error adding member {user_id} to team {team_id}: {str(e)}")
            raise
    
    async def remove_team_member(self, team_id: str, user_id: str) -> bool:
        """
        Remove a member from a team.
        
        Args:
            team_id: Team ID
            user_id: User ID
            
        Returns:
            True if successful
        """
        try:
            # Check if team exists
            team = await self.repository.get_by_id(team_id)
            if not team:
                raise ValueError(f"Team {team_id} not found")
            
            # Check if user is a member
            memberships = await self.member_repository.get_by_user(user_id)
            membership_id = None
            for membership in memberships:
                if membership.team_id == team_id:
                    membership_id = membership.id
                    break
            
            if not membership_id:
                raise ValueError(f"User {user_id} is not a member of team {team_id}")
            
            # Check if user is the owner
            if membership.role == "owner":
                raise ValueError(f"Cannot remove owner from team {team_id}")
            
            # Remove member
            return await self.member_repository.delete(membership_id)
        except Exception as e:
            logger.error(f"Error removing member {user_id} from team {team_id}: {str(e)}")
            raise
    
    async def update_team_member_role(self, team_id: str, user_id: str, role: str) -> TeamMember:
        """
        Update a team member's role.
        
        Args:
            team_id: Team ID
            user_id: User ID
            role: New role
            
        Returns:
            Updated team member
        """
        try:
            # Check if team exists
            team = await self.repository.get_by_id(team_id)
            if not team:
                raise ValueError(f"Team {team_id} not found")
            
            # Check if user is a member
            memberships = await self.member_repository.get_by_user(user_id)
            membership_id = None
            membership = None
            for m in memberships:
                if m.team_id == team_id:
                    membership_id = m.id
                    membership = m
                    break
            
            if not membership_id:
                raise ValueError(f"User {user_id} is not a member of team {team_id}")
            
            # Check if user is the owner and trying to change role
            if membership.role == "owner" and role != "owner":
                # Check if there are other owners
                members = await self.member_repository.get_by_team(team_id)
                owners = [m for m in members if m.role == "owner" and m.user_id != user_id]
                
                if not owners:
                    raise ValueError(f"Cannot change role of the only owner of team {team_id}")
            
            # Update role
            return await self.member_repository.update(membership_id, {"role": role})
        except Exception as e:
            logger.error(f"Error updating role of member {user_id} in team {team_id}: {str(e)}")
            raise


class ProjectService:
    """Service for project operations."""
    
    def __init__(self):
        """Initialize the service."""
        self.repository = ProjectRepository()
        self.user_service = UserService()
        self.team_service = TeamService()
    
    async def create_project(
        self,
        name: str,
        owner_id: str,
        team_id: Optional[str] = None,
        repository_url: Optional[str] = None,
        framework: Optional[str] = None,
    ) -> Project:
        """
        Create a new project.
        
        Args:
            name: Project name
            owner_id: Owner ID
            team_id: Team ID
            repository_url: Repository URL
            framework: Framework
            
        Returns:
            Created project
        """
        try:
            # Check if owner exists
            owner = await self.user_service.get_user(owner_id)
            if not owner:
                raise ValueError(f"User {owner_id} not found")
            
            # Check if team exists
            if team_id:
                team = await self.team_service.get_team(team_id)
                if not team:
                    raise ValueError(f"Team {team_id} not found")
                
                # Check if user is a member of the team
                teams = await self.team_service.get_teams_by_user(owner_id)
                if not any(t.id == team_id for t in teams):
                    raise ValueError(f"User {owner_id} is not a member of team {team_id}")
            
            # Create project
            project_data = {
                "name": name,
                "owner_id": owner_id,
                "team_id": team_id,
                "repository_url": repository_url,
                "framework": framework,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            
            return await self.repository.create(project_data)
        except Exception as e:
            logger.error(f"Error creating project: {str(e)}")
            raise
    
    async def get_project(self, project_id: str) -> Optional[Project]:
        """
        Get a project by ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            Project if found, None otherwise
        """
        try:
            return await self.repository.get_by_id(project_id)
        except Exception as e:
            logger.error(f"Error getting project {project_id}: {str(e)}")
            raise
    
    async def get_projects_by_owner(self, owner_id: str) -> List[Project]:
        """
        Get projects by owner ID.
        
        Args:
            owner_id: Owner ID
            
        Returns:
            List of projects
        """
        try:
            return await self.repository.get_by_owner(owner_id)
        except Exception as e:
            logger.error(f"Error getting projects by owner {owner_id}: {str(e)}")
            raise
    
    async def get_projects_by_team(self, team_id: str) -> List[Project]:
        """
        Get projects by team ID.
        
        Args:
            team_id: Team ID
            
        Returns:
            List of projects
        """
        try:
            return await self.repository.get_by_team(team_id)
        except Exception as e:
            logger.error(f"Error getting projects by team {team_id}: {str(e)}")
            raise
    
    async def get_projects_by_user(self, user_id: str) -> List[Project]:
        """
        Get projects that a user has access to.
        
        Args:
            user_id: User ID
            
        Returns:
            List of projects
        """
        try:
            # Get projects owned by the user
            owned_projects = await self.repository.get_by_owner(user_id)
            
            # Get teams that the user is a member of
            teams = await self.team_service.get_teams_by_user(user_id)
            
            # Get projects for each team
            team_projects = []
            for team in teams:
                projects = await self.repository.get_by_team(team.id)
                team_projects.extend(projects)
            
            # Combine and deduplicate projects
            all_projects = owned_projects + team_projects
            unique_projects = {p.id: p for p in all_projects}.values()
            
            return list(unique_projects)
        except Exception as e:
            logger.error(f"Error getting projects by user {user_id}: {str(e)}")
            raise
    
    async def update_project(self, project_id: str, data: Dict[str, Any]) -> Project:
        """
        Update a project.
        
        Args:
            project_id: Project ID
            data: Updated data
            
        Returns:
            Updated project
        """
        try:
            # Check if project exists
            project = await self.repository.get_by_id(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Update project
            return await self.repository.update(project_id, data)
        except Exception as e:
            logger.error(f"Error updating project {project_id}: {str(e)}")
            raise
    
    async def delete_project(self, project_id: str) -> bool:
        """
        Delete a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            True if successful
        """
        try:
            # Check if project exists
            project = await self.repository.get_by_id(project_id)
            if not project:
                raise ValueError(f"Project {project_id} not found")
            
            # Delete project
            return await self.repository.delete(project_id)
        except Exception as e:
            logger.error(f"Error deleting project {project_id}: {str(e)}")
            raise


# Add more service classes for other models as needed
