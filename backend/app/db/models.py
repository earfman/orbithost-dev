"""
Database models for OrbitHost.

This module defines Pydantic models that represent the database schema.
These models are used for data validation and serialization/deserialization.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class ProviderType(str, Enum):
    """Type of service provider."""
    REGISTRAR = "registrar"
    DNS = "dns"
    HOSTING = "hosting"


class DeploymentStatus(str, Enum):
    """Status of a deployment."""
    QUEUED = "queued"
    BUILDING = "building"
    DEPLOYING = "deploying"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class User(BaseModel):
    """User model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    email: str
    name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    subscription_tier: str = "free"
    subscription_status: str = "active"
    stripe_customer_id: Optional[str] = None
    
    class Config:
        orm_mode = True


class Team(BaseModel):
    """Team model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    owner_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True


class TeamMember(BaseModel):
    """Team member model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    team_id: str
    user_id: str
    role: str = "member"  # member, admin, owner
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True


class Project(BaseModel):
    """Project model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    owner_id: str
    team_id: Optional[str] = None
    repository_url: Optional[str] = None
    framework: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True


class Deployment(BaseModel):
    """Deployment model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    status: DeploymentStatus = DeploymentStatus.QUEUED
    version: str
    commit_hash: Optional[str] = None
    branch: Optional[str] = None
    environment: str = "production"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deployed_at: Optional[datetime] = None
    deployed_by: str
    build_logs: Optional[str] = None
    deployment_logs: Optional[str] = None
    error_message: Optional[str] = None
    preview_url: Optional[str] = None
    production_url: Optional[str] = None
    
    class Config:
        orm_mode = True


class Domain(BaseModel):
    """Domain model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    project_id: Optional[str] = None
    user_id: str
    status: str = "pending"  # pending, active, error
    verification_status: str = "pending"  # pending, verified, failed
    dns_provider: Optional[str] = None
    registrar: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expiration_date: Optional[datetime] = None
    auto_renew: bool = False
    
    class Config:
        orm_mode = True


class DnsRecord(BaseModel):
    """DNS record model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    domain_id: str
    type: str  # A, CNAME, TXT, MX, etc.
    name: str
    value: str
    ttl: int = 3600
    priority: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True


class APICredential(BaseModel):
    """API credential model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    provider: str
    provider_type: ProviderType
    name: str
    encrypted: bool = True
    credentials: Dict[str, str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    verified: bool = False
    
    class Config:
        orm_mode = True


class Subscription(BaseModel):
    """Subscription model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    stripe_subscription_id: str
    plan_id: str
    status: str  # active, canceled, past_due, etc.
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True


class UsageMetric(BaseModel):
    """Usage metric model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    project_id: Optional[str] = None
    metric_type: str  # bandwidth, storage, requests, etc.
    value: float
    unit: str  # MB, GB, count, etc.
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True


class AIFeedback(BaseModel):
    """AI feedback model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    deployment_id: str
    feedback_type: str  # error_analysis, performance, security, etc.
    content: str
    severity: str = "info"  # info, warning, error, critical
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    class Config:
        orm_mode = True


class WebhookConfiguration(BaseModel):
    """Webhook configuration model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    project_id: Optional[str] = None
    name: str
    url: str
    secret: Optional[str] = None
    events: List[str]  # deployment.success, deployment.failure, etc.
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True


class WebhookDelivery(BaseModel):
    """Webhook delivery model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    webhook_id: str
    event: str
    payload: Dict[str, Any]
    response_code: Optional[int] = None
    response_body: Optional[str] = None
    success: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True


class Alert(BaseModel):
    """Alert model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    project_id: Optional[str] = None
    alert_type: str  # system, application, ai_service, etc.
    metric: str  # cpu, memory, error_rate, etc.
    threshold: float
    operator: str  # >, <, ==, etc.
    severity: str  # info, warning, error, critical
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        orm_mode = True


class AlertEvent(BaseModel):
    """Alert event model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    alert_id: str
    value: float
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    
    class Config:
        orm_mode = True
