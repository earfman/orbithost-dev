"""
User service for OrbitHost.
This is part of the private components that implement user management and monetization features.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

import httpx
from supabase import create_client, Client

from app.core.config import settings
from app.models.user import User, UserCreate, UserUpdate, SubscriptionTier, SubscriptionStatus, Subscription

logger = logging.getLogger(__name__)

class UserService:
    """
    Service for managing users in OrbitHost.
    Uses Supabase as the database backend.
    """
    
    def __init__(self):
        self.supabase: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
        self.table = "users"
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """
        Get a user by ID.
        
        Args:
            user_id: The Clerk.dev user ID
            
        Returns:
            User object if found, None otherwise
        """
        try:
            response = self.supabase.table(self.table).select("*").eq("id", user_id).execute()
            
            if response.data and len(response.data) > 0:
                user_data = response.data[0]
                
                # Convert subscription data from JSON to Subscription object
                subscription_data = user_data.get("subscription", {})
                if not subscription_data:
                    subscription_data = {}
                
                subscription = Subscription(
                    tier=subscription_data.get("tier", SubscriptionTier.FREE),
                    status=subscription_data.get("status", SubscriptionStatus.ACTIVE),
                    stripe_customer_id=subscription_data.get("stripe_customer_id"),
                    stripe_subscription_id=subscription_data.get("stripe_subscription_id"),
                    current_period_start=subscription_data.get("current_period_start"),
                    current_period_end=subscription_data.get("current_period_end"),
                    cancel_at_period_end=subscription_data.get("cancel_at_period_end", False),
                    custom_domains_allowed=subscription_data.get("custom_domains_allowed", 0),
                    team_members_allowed=subscription_data.get("team_members_allowed", 1)
                )
                
                # Create User object
                return User(
                    id=user_data["id"],
                    email=user_data["email"],
                    first_name=user_data.get("first_name"),
                    last_name=user_data.get("last_name"),
                    image_url=user_data.get("image_url"),
                    created_at=user_data.get("created_at"),
                    updated_at=user_data.get("updated_at"),
                    last_login_at=user_data.get("last_login_at"),
                    subscription=subscription
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {str(e)}")
            return None
    
    async def create_user(
        self, 
        id: str, 
        email: str, 
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        image_url: Optional[str] = None
    ) -> User:
        """
        Create a new user.
        
        Args:
            id: Clerk.dev user ID
            email: User's email address
            first_name: User's first name
            last_name: User's last name
            image_url: URL to user's profile image
            
        Returns:
            Created User object
        """
        now = datetime.now()
        
        # Default subscription for free tier
        subscription = Subscription(
            tier=SubscriptionTier.FREE,
            status=SubscriptionStatus.ACTIVE,
            custom_domains_allowed=0,
            team_members_allowed=1
        )
        
        user_data = {
            "id": id,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "image_url": image_url,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "last_login_at": now.isoformat(),
            "subscription": subscription.dict()
        }
        
        try:
            response = self.supabase.table(self.table).insert(user_data).execute()
            
            if response.data and len(response.data) > 0:
                return User(
                    id=id,
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    image_url=image_url,
                    created_at=now,
                    updated_at=now,
                    last_login_at=now,
                    subscription=subscription
                )
            
            raise Exception("Failed to create user")
            
        except Exception as e:
            logger.error(f"Error creating user {id}: {str(e)}")
            raise
    
    async def update_user(self, user_id: str, user_update: UserUpdate) -> Optional[User]:
        """
        Update a user's information.
        
        Args:
            user_id: The Clerk.dev user ID
            user_update: User update data
            
        Returns:
            Updated User object if successful, None otherwise
        """
        try:
            update_data = user_update.dict(exclude_unset=True)
            update_data["updated_at"] = datetime.now().isoformat()
            
            response = self.supabase.table(self.table).update(update_data).eq("id", user_id).execute()
            
            if response.data and len(response.data) > 0:
                return await self.get_user(user_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating user {user_id}: {str(e)}")
            return None
    
    async def update_last_login(self, user_id: str) -> bool:
        """
        Update a user's last login time.
        
        Args:
            user_id: The Clerk.dev user ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            update_data = {
                "last_login_at": datetime.now().isoformat()
            }
            
            response = self.supabase.table(self.table).update(update_data).eq("id", user_id).execute()
            
            return response.data is not None and len(response.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating last login for user {user_id}: {str(e)}")
            return False
    
    async def update_subscription(
        self, 
        user_id: str, 
        subscription_data: Dict[str, Any]
    ) -> Optional[User]:
        """
        Update a user's subscription information.
        
        Args:
            user_id: The Clerk.dev user ID
            subscription_data: Subscription data to update
            
        Returns:
            Updated User object if successful, None otherwise
        """
        try:
            # Get current user to merge subscription data
            user = await self.get_user(user_id)
            if not user:
                return None
            
            # Merge subscription data
            current_subscription = user.subscription.dict()
            current_subscription.update(subscription_data)
            
            # Update user in database
            update_data = {
                "subscription": current_subscription,
                "updated_at": datetime.now().isoformat()
            }
            
            response = self.supabase.table(self.table).update(update_data).eq("id", user_id).execute()
            
            if response.data and len(response.data) > 0:
                return await self.get_user(user_id)
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating subscription for user {user_id}: {str(e)}")
            return None
    
    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a user.
        
        Args:
            user_id: The Clerk.dev user ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = self.supabase.table(self.table).delete().eq("id", user_id).execute()
            
            return response.data is not None
            
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {str(e)}")
            return False
    
    async def list_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        """
        List users with pagination.
        
        Args:
            limit: Maximum number of users to return
            offset: Offset for pagination
            
        Returns:
            List of User objects
        """
        try:
            response = self.supabase.table(self.table).select("*").range(offset, offset + limit - 1).execute()
            
            users = []
            for user_data in response.data:
                # Convert subscription data from JSON to Subscription object
                subscription_data = user_data.get("subscription", {})
                if not subscription_data:
                    subscription_data = {}
                
                subscription = Subscription(
                    tier=subscription_data.get("tier", SubscriptionTier.FREE),
                    status=subscription_data.get("status", SubscriptionStatus.ACTIVE),
                    stripe_customer_id=subscription_data.get("stripe_customer_id"),
                    stripe_subscription_id=subscription_data.get("stripe_subscription_id"),
                    current_period_start=subscription_data.get("current_period_start"),
                    current_period_end=subscription_data.get("current_period_end"),
                    cancel_at_period_end=subscription_data.get("cancel_at_period_end", False),
                    custom_domains_allowed=subscription_data.get("custom_domains_allowed", 0),
                    team_members_allowed=subscription_data.get("team_members_allowed", 1)
                )
                
                # Create User object
                user = User(
                    id=user_data["id"],
                    email=user_data["email"],
                    first_name=user_data.get("first_name"),
                    last_name=user_data.get("last_name"),
                    image_url=user_data.get("image_url"),
                    created_at=user_data.get("created_at"),
                    updated_at=user_data.get("updated_at"),
                    last_login_at=user_data.get("last_login_at"),
                    subscription=subscription
                )
                
                users.append(user)
            
            return users
            
        except Exception as e:
            logger.error(f"Error listing users: {str(e)}")
            return []
