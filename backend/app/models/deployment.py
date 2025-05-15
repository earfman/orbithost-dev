from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl

class DeploymentStatus(str, Enum):
    PENDING = "pending"
    BUILDING = "building"
    DEPLOYED = "deployed"
    FAILED = "failed"

class Deployment(BaseModel):
    """Model representing a deployment"""
    id: Optional[str] = None
    repository_name: str
    commit_sha: str
    branch: str
    status: DeploymentStatus
    url: Optional[HttpUrl] = None
    site_id: Optional[str] = None  # OrbitHost site identifier
    author: str
    commit_message: str
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    completed_at: Optional[datetime] = None
    screenshot_url: Optional[HttpUrl] = None
    screenshot_captured_at: Optional[datetime] = None
    dom_content: Optional[str] = None
    error_message: Optional[str] = None
    
    class Config:
        orm_mode = True
