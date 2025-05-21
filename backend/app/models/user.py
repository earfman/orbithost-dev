"""
User model for OrbitHost.
This is part of the private components that implement user management and monetization features.
"""

from enum import Enum
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class SubscriptionTier(str, Enum):
    """Subscription tiers for OrbitHost users"""
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"


class SubscriptionStatus(str, Enum):
    """Status of a user's subscription"""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    TRIALING = "trialing"


class Subscription(BaseModel):
    """User subscription information"""
    tier: SubscriptionTier = Field(default=SubscriptionTier.FREE)
    status: SubscriptionStatus = Field(default=SubscriptionStatus.ACTIVE)
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False
    custom_domains_allowed: int = Field(default=0)
    team_members_allowed: int = Field(default=1)


class User(BaseModel):
    """
    User model for OrbitHost.
    This stores user information and is linked to Clerk.dev for authentication.
    """
    id: str = Field(..., description="Clerk.dev user ID")
    email: EmailStr = Field(..., description="User's email address")
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_login_at: Optional[datetime] = None
    subscription: Subscription = Field(default_factory=Subscription)
    
    class Config:
        schema_extra = {
            "example": {
                "id": "user_2NxAyQHTXn6Lx5TCGiRip6Bj7Ul",
                "email": "user@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "image_url": "https://img.clerk.com/user.jpg",
                "created_at": "2025-05-15T12:00:00",
                "updated_at": "2025-05-15T12:00:00",
                "last_login_at": "2025-05-15T12:00:00",
                "subscription": {
                    "tier": "free",
                    "status": "active",
                    "stripe_customer_id": None,
                    "stripe_subscription_id": None,
                    "current_period_start": None,
                    "current_period_end": None,
                    "cancel_at_period_end": False,
                    "custom_domains_allowed": 0,
                    "team_members_allowed": 1
                }
            }
        }


class UserCreate(BaseModel):
    """Schema for creating a new user"""
    id: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    image_url: Optional[str] = None


class UserUpdate(BaseModel):
    """Schema for updating a user"""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    image_url: Optional[str] = None


class UserResponse(BaseModel):
    """Schema for user response"""
    id: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    image_url: Optional[str] = None
    subscription_tier: SubscriptionTier
    custom_domains_allowed: int
    team_members_allowed: int
