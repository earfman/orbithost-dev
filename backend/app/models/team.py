"""
Team models for OrbitHost.
This is part of the private components that implement team collaboration features.
"""

from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class TeamRole(str, Enum):
    """Roles for team members"""
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class TeamMember(BaseModel):
    """Team member model"""
    user_id: str = Field(..., description="User ID of the team member")
    email: EmailStr = Field(..., description="Email of the team member")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: TeamRole = Field(default=TeamRole.MEMBER)
    added_at: datetime = Field(default_factory=datetime.now)
    invited_by: Optional[str] = None


class Team(BaseModel):
    """Team model"""
    id: str = Field(..., description="Team ID")
    name: str = Field(..., description="Team name")
    owner_id: str = Field(..., description="User ID of the team owner")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    members: List[TeamMember] = Field(default_factory=list)
    

class TeamCreate(BaseModel):
    """Schema for creating a new team"""
    name: str = Field(..., description="Team name")


class TeamUpdate(BaseModel):
    """Schema for updating a team"""
    name: Optional[str] = None


class TeamInvite(BaseModel):
    """Schema for inviting a user to a team"""
    email: EmailStr = Field(..., description="Email of the user to invite")
    role: TeamRole = Field(default=TeamRole.MEMBER)


class TeamInviteResponse(BaseModel):
    """Schema for team invitation response"""
    id: str = Field(..., description="Invitation ID")
    team_id: str = Field(..., description="Team ID")
    email: EmailStr = Field(..., description="Email of the invited user")
    role: TeamRole = Field(..., description="Role of the invited user")
    invited_by: str = Field(..., description="User ID of the inviter")
    created_at: datetime = Field(..., description="Invitation creation time")
    expires_at: datetime = Field(..., description="Invitation expiration time")
