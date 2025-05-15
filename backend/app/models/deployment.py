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
    author: str
    commit_message: str
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    screenshot_url: Optional[HttpUrl] = None
    dom_content: Optional[str] = None
    
    class Config:
        orm_mode = True
