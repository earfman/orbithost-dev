"""
User onboarding service for OrbitHost.
This is part of the private components that implement user management.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

class OnboardingService:
    """
    Service for managing user onboarding in OrbitHost.
    Handles onboarding steps, progress tracking, and personalized recommendations.
    """
    
    def __init__(self):
        # In a real implementation, we would connect to a database
        # For now, we'll use an in-memory store
        self.onboarding_data = {}
    
    async def initialize_onboarding(self, user: User) -> Dict[str, Any]:
        """
        Initialize onboarding for a new user.
        
        Args:
            user: The user to initialize onboarding for
            
        Returns:
            Dictionary with onboarding details
        """
        try:
            # Define onboarding steps
            steps = [
                {
                    "id": "profile",
                    "title": "Complete Your Profile",
                    "description": "Add your name and profile picture to personalize your account.",
                    "completed": bool(user.first_name and user.last_name),
                    "order": 1
                },
                {
                    "id": "github",
                    "title": "Connect GitHub Repository",
                    "description": "Connect your GitHub repository to deploy your first project.",
                    "completed": False,
                    "order": 2
                },
                {
                    "id": "deploy",
                    "title": "Deploy Your First Site",
                    "description": "Deploy your first website to OrbitHost.",
                    "completed": False,
                    "order": 3
                },
                {
                    "id": "domain",
                    "title": "Set Up a Domain",
                    "description": "Configure a domain for your site.",
                    "completed": False,
                    "order": 4
                },
                {
                    "id": "invite",
                    "title": "Invite Your Team",
                    "description": "Invite team members to collaborate on your projects.",
                    "completed": False,
                    "order": 5
                }
            ]
            
            # Create onboarding data
            onboarding_data = {
                "user_id": user.id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "completed": False,
                "current_step": "profile" if not (user.first_name and user.last_name) else "github",
                "steps": steps,
                "progress_percentage": 0
            }
            
            # Calculate initial progress
            completed_steps = sum(1 for step in steps if step["completed"])
            onboarding_data["progress_percentage"] = int((completed_steps / len(steps)) * 100)
            
            # In a real implementation, we would save to a database
            self.onboarding_data[user.id] = onboarding_data
            
            return onboarding_data
            
        except Exception as e:
            logger.error(f"Error initializing onboarding for user {user.id}: {str(e)}")
            raise
    
    async def get_onboarding_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get onboarding status for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            Dictionary with onboarding status
        """
        try:
            # Check if onboarding data exists
            if user_id not in self.onboarding_data:
                # Initialize onboarding for user
                # In a real implementation, we would fetch the user from the database
                # For now, we'll create a minimal user object
                user = User(
                    id=user_id,
                    email=f"user_{user_id}@example.com",
                    first_name=None,
                    last_name=None
                )
                return await self.initialize_onboarding(user)
            
            return self.onboarding_data[user_id]
            
        except Exception as e:
            logger.error(f"Error getting onboarding status for user {user_id}: {str(e)}")
            raise
    
    async def update_step_status(
        self, 
        user_id: str, 
        step_id: str, 
        completed: bool
    ) -> Dict[str, Any]:
        """
        Update the status of an onboarding step.
        
        Args:
            user_id: The user ID
            step_id: The step ID
            completed: Whether the step is completed
            
        Returns:
            Updated onboarding data
        """
        try:
            # Get onboarding data
            onboarding_data = await self.get_onboarding_status(user_id)
            
            # Update step status
            for step in onboarding_data["steps"]:
                if step["id"] == step_id:
                    step["completed"] = completed
                    break
            
            # Calculate progress
            completed_steps = sum(1 for step in onboarding_data["steps"] if step["completed"])
            total_steps = len(onboarding_data["steps"])
            onboarding_data["progress_percentage"] = int((completed_steps / total_steps) * 100)
            
            # Check if all steps are completed
            onboarding_data["completed"] = completed_steps == total_steps
            
            # Update current step
            if completed:
                # Find the next incomplete step
                next_steps = [s for s in onboarding_data["steps"] if not s["completed"]]
                if next_steps:
                    next_steps.sort(key=lambda s: s["order"])
                    onboarding_data["current_step"] = next_steps[0]["id"]
            
            # Update timestamp
            onboarding_data["updated_at"] = datetime.now().isoformat()
            
            # In a real implementation, we would save to a database
            self.onboarding_data[user_id] = onboarding_data
            
            return onboarding_data
            
        except Exception as e:
            logger.error(f"Error updating step status for user {user_id}: {str(e)}")
            raise
    
    async def get_personalized_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get personalized recommendations for a user based on their onboarding progress.
        
        Args:
            user_id: The user ID
            
        Returns:
            List of recommendations
        """
        try:
            # Get onboarding data
            onboarding_data = await self.get_onboarding_status(user_id)
            
            # Generate recommendations based on current step
            recommendations = []
            current_step = onboarding_data["current_step"]
            
            if current_step == "profile":
                recommendations.append({
                    "id": "rec_profile",
                    "title": "Complete Your Profile",
                    "description": "Add your name and profile picture to personalize your account.",
                    "action_url": "/settings/profile",
                    "action_text": "Edit Profile"
                })
            elif current_step == "github":
                recommendations.append({
                    "id": "rec_github",
                    "title": "Connect Your GitHub Repository",
                    "description": "Link your GitHub repository to deploy your projects.",
                    "action_url": "/deployments/new",
                    "action_text": "Connect GitHub"
                })
            elif current_step == "deploy":
                recommendations.append({
                    "id": "rec_deploy",
                    "title": "Deploy Your First Site",
                    "description": "Deploy your website to OrbitHost with just a few clicks.",
                    "action_url": "/deployments/new",
                    "action_text": "Create Deployment"
                })
            elif current_step == "domain":
                recommendations.append({
                    "id": "rec_domain",
                    "title": "Set Up a Domain",
                    "description": "Configure a domain for your site to make it accessible to the world.",
                    "action_url": "/domains/new",
                    "action_text": "Add Domain"
                })
            elif current_step == "invite":
                recommendations.append({
                    "id": "rec_invite",
                    "title": "Invite Your Team",
                    "description": "Collaborate with your team members on your projects.",
                    "action_url": "/teams",
                    "action_text": "Invite Team"
                })
            
            # Add upgrade recommendation if on free tier
            if not onboarding_data["completed"]:
                recommendations.append({
                    "id": "rec_upgrade",
                    "title": "Upgrade to Pro",
                    "description": "Get access to custom domains, more resources, and premium features.",
                    "action_url": "/billing",
                    "action_text": "Upgrade Now"
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting recommendations for user {user_id}: {str(e)}")
            raise
    
    async def skip_onboarding(self, user_id: str) -> Dict[str, Any]:
        """
        Skip the onboarding process for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            Updated onboarding data
        """
        try:
            # Get onboarding data
            onboarding_data = await self.get_onboarding_status(user_id)
            
            # Mark all steps as completed
            for step in onboarding_data["steps"]:
                step["completed"] = True
            
            # Update onboarding status
            onboarding_data["completed"] = True
            onboarding_data["progress_percentage"] = 100
            onboarding_data["updated_at"] = datetime.now().isoformat()
            
            # In a real implementation, we would save to a database
            self.onboarding_data[user_id] = onboarding_data
            
            return onboarding_data
            
        except Exception as e:
            logger.error(f"Error skipping onboarding for user {user_id}: {str(e)}")
            raise
    
    async def reset_onboarding(self, user_id: str) -> Dict[str, Any]:
        """
        Reset the onboarding process for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            Updated onboarding data
        """
        try:
            # Delete existing onboarding data
            if user_id in self.onboarding_data:
                del self.onboarding_data[user_id]
            
            # Initialize new onboarding data
            # In a real implementation, we would fetch the user from the database
            # For now, we'll create a minimal user object
            user = User(
                id=user_id,
                email=f"user_{user_id}@example.com",
                first_name=None,
                last_name=None
            )
            
            return await self.initialize_onboarding(user)
            
        except Exception as e:
            logger.error(f"Error resetting onboarding for user {user_id}: {str(e)}")
            raise
