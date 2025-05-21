from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class DeploymentStatus(str, Enum):
    PENDING = "pending"
    BUILDING = "building"
    DEPLOYED = "deployed"
    FAILED = "failed"
    PREVIEW = "preview"

class DeploymentType(str, Enum):
    PRODUCTION = "production"
    PREVIEW = "preview"
    BRANCH = "branch"

class Deployment(BaseModel):
    """Model representing a deployment"""
    id: Optional[str] = None
    repository_name: str
    commit_sha: str
    branch: str
    status: DeploymentStatus
    deployment_type: DeploymentType = DeploymentType.PRODUCTION
    url: Optional[str] = None
    site_id: Optional[str] = None  # OrbitHost site identifier
    author: str
    commit_message: str
    error_message: Optional[str] = None
    screenshot_url: Optional[str] = None
    dom_content: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    screenshot_captured_at: Optional[datetime] = None
    parent_deployment_id: Optional[str] = None  # For rollbacks, points to the original deployment
    is_rollback: bool = False
    preview_expiry: Optional[datetime] = None  # When preview deployments expire
    build_cache_hit: bool = False  # Whether the build used cached artifacts
    
    class Config:
        orm_mode = True
