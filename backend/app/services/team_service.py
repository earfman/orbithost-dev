"""
Team service for OrbitHost.
This is part of the private components that implement team collaboration features.
"""

import os
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.core.config import settings
from app.models.user import User
from app.models.team import Team, TeamMember, TeamRole, TeamCreate, TeamUpdate, TeamInvite

logger = logging.getLogger(__name__)

class TeamService:
    """
    Service for managing teams in OrbitHost.
    Handles team creation, updates, and member management.
    """
    
    def __init__(self):
        # In a real implementation, we would connect to a database
        # For now, we'll use an in-memory store
        self.teams = {}
        self.invitations = {}
    
    async def create_team(self, user: User, team_create: TeamCreate) -> Team:
        """
        Create a new team.
        
        Args:
            user: The user creating the team
            team_create: Team creation data
            
        Returns:
            Created Team object
        """
        try:
            # Check if user has reached their team limit
            if user.subscription.team_members_allowed <= 1:
                raise ValueError("Your subscription does not allow team creation")
            
            # Generate team ID
            team_id = f"team_{uuid.uuid4().hex[:8]}"
            
            # Create team owner member
            owner = TeamMember(
                user_id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=TeamRole.OWNER
            )
            
            # Create team
            team = Team(
                id=team_id,
                name=team_create.name,
                owner_id=user.id,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                members=[owner]
            )
            
            # In a real implementation, we would save to a database
            self.teams[team_id] = team
            
            return team
            
        except Exception as e:
            logger.error(f"Error creating team for user {user.id}: {str(e)}")
            raise
    
    async def get_team(self, team_id: str) -> Optional[Team]:
        """
        Get a team by ID.
        
        Args:
            team_id: The team ID
            
        Returns:
            Team object if found, None otherwise
        """
        try:
            # In a real implementation, we would fetch from a database
            return self.teams.get(team_id)
            
        except Exception as e:
            logger.error(f"Error getting team {team_id}: {str(e)}")
            raise
    
    async def update_team(self, team_id: str, user_id: str, team_update: TeamUpdate) -> Optional[Team]:
        """
        Update a team.
        
        Args:
            team_id: The team ID
            user_id: The user ID making the update
            team_update: Team update data
            
        Returns:
            Updated Team object if successful, None otherwise
        """
        try:
            # Get team
            team = await self.get_team(team_id)
            if not team:
                return None
            
            # Check if user is authorized to update the team
            member = next((m for m in team.members if m.user_id == user_id), None)
            if not member or member.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
                raise ValueError("You are not authorized to update this team")
            
            # Update team
            if team_update.name:
                team.name = team_update.name
            
            team.updated_at = datetime.now()
            
            # In a real implementation, we would save to a database
            self.teams[team_id] = team
            
            return team
            
        except Exception as e:
            logger.error(f"Error updating team {team_id}: {str(e)}")
            raise
    
    async def delete_team(self, team_id: str, user_id: str) -> bool:
        """
        Delete a team.
        
        Args:
            team_id: The team ID
            user_id: The user ID making the deletion
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get team
            team = await self.get_team(team_id)
            if not team:
                return False
            
            # Check if user is authorized to delete the team
            if team.owner_id != user_id:
                raise ValueError("Only the team owner can delete the team")
            
            # Delete team
            if team_id in self.teams:
                del self.teams[team_id]
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting team {team_id}: {str(e)}")
            raise
    
    async def get_user_teams(self, user_id: str) -> List[Team]:
        """
        Get teams that a user is a member of.
        
        Args:
            user_id: The user ID
            
        Returns:
            List of Team objects
        """
        try:
            # In a real implementation, we would fetch from a database
            return [
                team for team in self.teams.values()
                if any(member.user_id == user_id for member in team.members)
            ]
            
        except Exception as e:
            logger.error(f"Error getting teams for user {user_id}: {str(e)}")
            raise
    
    async def invite_user(
        self, 
        team_id: str, 
        inviter_id: str, 
        invite: TeamInvite
    ) -> Dict[str, Any]:
        """
        Invite a user to a team.
        
        Args:
            team_id: The team ID
            inviter_id: The user ID sending the invitation
            invite: Invitation data
            
        Returns:
            Dictionary with invitation details
        """
        try:
            # Get team
            team = await self.get_team(team_id)
            if not team:
                raise ValueError("Team not found")
            
            # Check if user is authorized to invite
            inviter = next((m for m in team.members if m.user_id == inviter_id), None)
            if not inviter or inviter.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
                raise ValueError("You are not authorized to invite users to this team")
            
            # Check if email is already a member
            if any(member.email == invite.email for member in team.members):
                raise ValueError("User is already a member of this team")
            
            # Generate invitation ID
            invitation_id = f"inv_{uuid.uuid4().hex[:8]}"
            
            # Create invitation
            invitation = {
                "id": invitation_id,
                "team_id": team_id,
                "team_name": team.name,
                "email": invite.email,
                "role": invite.role,
                "invited_by": inviter_id,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=7)).isoformat()
            }
            
            # In a real implementation, we would save to a database and send an email
            self.invitations[invitation_id] = invitation
            
            # Log the invitation (in a real implementation, we would send an email)
            logger.info(f"Invitation sent to {invite.email} for team {team.name}")
            
            return invitation
            
        except Exception as e:
            logger.error(f"Error inviting user to team {team_id}: {str(e)}")
            raise
    
    async def accept_invitation(self, invitation_id: str, user: User) -> Team:
        """
        Accept a team invitation.
        
        Args:
            invitation_id: The invitation ID
            user: The user accepting the invitation
            
        Returns:
            Team object
        """
        try:
            # Get invitation
            invitation = self.invitations.get(invitation_id)
            if not invitation:
                raise ValueError("Invitation not found")
            
            # Check if invitation has expired
            expires_at = datetime.fromisoformat(invitation["expires_at"])
            if datetime.now() > expires_at:
                raise ValueError("Invitation has expired")
            
            # Check if email matches
            if invitation["email"].lower() != user.email.lower():
                raise ValueError("This invitation is not for your email address")
            
            # Get team
            team_id = invitation["team_id"]
            team = await self.get_team(team_id)
            if not team:
                raise ValueError("Team not found")
            
            # Create team member
            member = TeamMember(
                user_id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=invitation["role"],
                added_at=datetime.now(),
                invited_by=invitation["invited_by"]
            )
            
            # Add member to team
            team.members.append(member)
            team.updated_at = datetime.now()
            
            # In a real implementation, we would save to a database
            self.teams[team_id] = team
            
            # Delete invitation
            if invitation_id in self.invitations:
                del self.invitations[invitation_id]
            
            return team
            
        except Exception as e:
            logger.error(f"Error accepting invitation {invitation_id}: {str(e)}")
            raise
    
    async def remove_member(self, team_id: str, remover_id: str, member_id: str) -> Optional[Team]:
        """
        Remove a member from a team.
        
        Args:
            team_id: The team ID
            remover_id: The user ID removing the member
            member_id: The user ID to remove
            
        Returns:
            Updated Team object if successful, None otherwise
        """
        try:
            # Get team
            team = await self.get_team(team_id)
            if not team:
                return None
            
            # Check if user is authorized to remove members
            remover = next((m for m in team.members if m.user_id == remover_id), None)
            if not remover or remover.role not in [TeamRole.OWNER, TeamRole.ADMIN]:
                raise ValueError("You are not authorized to remove members from this team")
            
            # Check if target is the owner
            if member_id == team.owner_id:
                raise ValueError("Cannot remove the team owner")
            
            # Check if remover is trying to remove an admin while not being the owner
            member = next((m for m in team.members if m.user_id == member_id), None)
            if (member and member.role == TeamRole.ADMIN and 
                remover.role != TeamRole.OWNER):
                raise ValueError("Only the team owner can remove admins")
            
            # Remove member
            team.members = [m for m in team.members if m.user_id != member_id]
            team.updated_at = datetime.now()
            
            # In a real implementation, we would save to a database
            self.teams[team_id] = team
            
            return team
            
        except Exception as e:
            logger.error(f"Error removing member {member_id} from team {team_id}: {str(e)}")
            raise
    
    async def update_member_role(
        self, 
        team_id: str, 
        updater_id: str, 
        member_id: str, 
        role: TeamRole
    ) -> Optional[Team]:
        """
        Update a team member's role.
        
        Args:
            team_id: The team ID
            updater_id: The user ID updating the role
            member_id: The user ID to update
            role: The new role
            
        Returns:
            Updated Team object if successful, None otherwise
        """
        try:
            # Get team
            team = await self.get_team(team_id)
            if not team:
                return None
            
            # Check if user is authorized to update roles
            updater = next((m for m in team.members if m.user_id == updater_id), None)
            if not updater or updater.role != TeamRole.OWNER:
                raise ValueError("Only the team owner can update member roles")
            
            # Check if target is the owner
            if member_id == team.owner_id:
                raise ValueError("Cannot change the role of the team owner")
            
            # Update member role
            for member in team.members:
                if member.user_id == member_id:
                    member.role = role
                    break
            
            team.updated_at = datetime.now()
            
            # In a real implementation, we would save to a database
            self.teams[team_id] = team
            
            return team
            
        except Exception as e:
            logger.error(f"Error updating role for member {member_id} in team {team_id}: {str(e)}")
            raise
    
    async def transfer_ownership(
        self, 
        team_id: str, 
        current_owner_id: str, 
        new_owner_id: str
    ) -> Optional[Team]:
        """
        Transfer team ownership to another member.
        
        Args:
            team_id: The team ID
            current_owner_id: The current owner's user ID
            new_owner_id: The new owner's user ID
            
        Returns:
            Updated Team object if successful, None otherwise
        """
        try:
            # Get team
            team = await self.get_team(team_id)
            if not team:
                return None
            
            # Check if user is the current owner
            if team.owner_id != current_owner_id:
                raise ValueError("Only the team owner can transfer ownership")
            
            # Check if new owner is a member
            new_owner = next((m for m in team.members if m.user_id == new_owner_id), None)
            if not new_owner:
                raise ValueError("New owner must be a team member")
            
            # Update team owner
            team.owner_id = new_owner_id
            
            # Update member roles
            for member in team.members:
                if member.user_id == current_owner_id:
                    member.role = TeamRole.ADMIN
                elif member.user_id == new_owner_id:
                    member.role = TeamRole.OWNER
            
            team.updated_at = datetime.now()
            
            # In a real implementation, we would save to a database
            self.teams[team_id] = team
            
            return team
            
        except Exception as e:
            logger.error(f"Error transferring ownership of team {team_id}: {str(e)}")
            raise
