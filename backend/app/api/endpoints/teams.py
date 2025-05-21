"""
Team API endpoints for OrbitHost.
This is part of the private components that implement team collaboration features.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Path, Body

from app.core.auth import get_current_user
from app.models.user import User
from app.models.team import Team, TeamCreate, TeamUpdate, TeamInvite, TeamRole
from app.services.team_service import TeamService

router = APIRouter()
team_service = TeamService()


@router.get("/", response_model=List[Team])
async def list_teams(current_user: User = Depends(get_current_user)):
    """
    List teams that the current user is a member of.
    """
    try:
        teams = await team_service.get_user_teams(current_user.id)
        return teams
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Team listing error: {str(e)}")


@router.post("/", response_model=Team)
async def create_team(
    team_create: TeamCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new team.
    """
    try:
        team = await team_service.create_team(current_user, team_create)
        return team
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Team creation error: {str(e)}")


@router.get("/{team_id}", response_model=Team)
async def get_team(
    team_id: str = Path(...),
    current_user: User = Depends(get_current_user)
):
    """
    Get a team by ID.
    """
    try:
        team = await team_service.get_team(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        # Check if user is a member of the team
        if not any(member.user_id == current_user.id for member in team.members):
            raise HTTPException(status_code=403, detail="You are not a member of this team")
        
        return team
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Team retrieval error: {str(e)}")


@router.put("/{team_id}", response_model=Team)
async def update_team(
    team_update: TeamUpdate,
    team_id: str = Path(...),
    current_user: User = Depends(get_current_user)
):
    """
    Update a team.
    """
    try:
        team = await team_service.update_team(team_id, current_user.id, team_update)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        return team
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Team update error: {str(e)}")


@router.delete("/{team_id}", response_model=Dict[str, Any])
async def delete_team(
    team_id: str = Path(...),
    current_user: User = Depends(get_current_user)
):
    """
    Delete a team.
    """
    try:
        success = await team_service.delete_team(team_id, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Team not found")
        
        return {"status": "success", "message": "Team deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Team deletion error: {str(e)}")


@router.post("/{team_id}/invite", response_model=Dict[str, Any])
async def invite_user(
    invite: TeamInvite,
    team_id: str = Path(...),
    current_user: User = Depends(get_current_user)
):
    """
    Invite a user to a team.
    """
    try:
        invitation = await team_service.invite_user(team_id, current_user.id, invite)
        return invitation
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invitation error: {str(e)}")


@router.post("/invitations/{invitation_id}/accept", response_model=Team)
async def accept_invitation(
    invitation_id: str = Path(...),
    current_user: User = Depends(get_current_user)
):
    """
    Accept a team invitation.
    """
    try:
        team = await team_service.accept_invitation(invitation_id, current_user)
        return team
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Invitation acceptance error: {str(e)}")


@router.delete("/{team_id}/members/{member_id}", response_model=Team)
async def remove_member(
    team_id: str = Path(...),
    member_id: str = Path(...),
    current_user: User = Depends(get_current_user)
):
    """
    Remove a member from a team.
    """
    try:
        team = await team_service.remove_member(team_id, current_user.id, member_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        return team
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Member removal error: {str(e)}")


@router.put("/{team_id}/members/{member_id}/role", response_model=Team)
async def update_member_role(
    role: TeamRole,
    team_id: str = Path(...),
    member_id: str = Path(...),
    current_user: User = Depends(get_current_user)
):
    """
    Update a team member's role.
    """
    try:
        team = await team_service.update_member_role(team_id, current_user.id, member_id, role)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        return team
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Role update error: {str(e)}")


@router.post("/{team_id}/transfer-ownership/{new_owner_id}", response_model=Team)
async def transfer_ownership(
    team_id: str = Path(...),
    new_owner_id: str = Path(...),
    current_user: User = Depends(get_current_user)
):
    """
    Transfer team ownership to another member.
    """
    try:
        team = await team_service.transfer_ownership(team_id, current_user.id, new_owner_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        
        return team
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ownership transfer error: {str(e)}")
