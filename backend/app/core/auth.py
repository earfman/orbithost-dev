"""
Authentication middleware for OrbitHost using Clerk.dev.
This is part of the private components that implement user management.
"""

import os
import time
import logging
from typing import Optional, Dict, Any

import jwt
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.models.user import User
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

# Initialize security
security = HTTPBearer()


class ClerkAuth:
    """
    Authentication middleware for Clerk.dev JWT verification.
    """
    
    def __init__(self):
        self.public_key = os.getenv("CLERK_JWT_PUBLIC_KEY", "").replace("\\n", "\n")
        if not self.public_key:
            logger.warning("CLERK_JWT_PUBLIC_KEY not set. Authentication will not work properly.")
        
        self.user_service = UserService()
    
    async def get_current_user(
        self, credentials: HTTPAuthorizationCredentials = Depends(security)
    ) -> User:
        """
        Verify JWT token and return the current user.
        
        Args:
            credentials: HTTP Authorization credentials
            
        Returns:
            User object for the authenticated user
            
        Raises:
            HTTPException: If token is invalid or user not found
        """
        token = credentials.credentials
        
        try:
            # Verify the JWT token using Clerk's public key
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"],
                options={"verify_signature": bool(self.public_key)}
            )
            
            # Check if token is expired
            if payload.get("exp") and time.time() > payload.get("exp"):
                raise HTTPException(status_code=401, detail="Token has expired")
            
            # Get user ID from token
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token payload")
            
            # Get user from database or create if not exists
            user = await self.user_service.get_user(user_id)
            if not user:
                # If we have user data in the token, create the user
                if "email" in payload.get("user", {}):
                    user_data = payload.get("user", {})
                    user = await self.user_service.create_user(
                        id=user_id,
                        email=user_data.get("email"),
                        first_name=user_data.get("first_name"),
                        last_name=user_data.get("last_name"),
                        image_url=user_data.get("image_url")
                    )
                else:
                    raise HTTPException(status_code=404, detail="User not found")
            
            # Update last login time
            await self.user_service.update_last_login(user_id)
            
            return user
            
        except jwt.PyJWTError as e:
            logger.error(f"JWT verification error: {str(e)}")
            raise HTTPException(status_code=401, detail="Invalid authentication token")
    
    async def get_optional_user(
        self, request: Request
    ) -> Optional[User]:
        """
        Get the current user if authenticated, otherwise return None.
        This is useful for endpoints that work both for authenticated and unauthenticated users.
        
        Args:
            request: FastAPI request object
            
        Returns:
            User object if authenticated, None otherwise
        """
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        
        token = auth_header.replace("Bearer ", "")
        
        try:
            # Verify the JWT token using Clerk's public key
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=["RS256"],
                options={"verify_signature": bool(self.public_key)}
            )
            
            # Check if token is expired
            if payload.get("exp") and time.time() > payload.get("exp"):
                return None
            
            # Get user ID from token
            user_id = payload.get("sub")
            if not user_id:
                return None
            
            # Get user from database
            user = await self.user_service.get_user(user_id)
            return user
            
        except jwt.PyJWTError:
            return None


# Create a global instance of ClerkAuth
clerk_auth = ClerkAuth()

# Dependency for protected routes
get_current_user = clerk_auth.get_current_user

# Dependency for routes that work with or without authentication
get_optional_user = clerk_auth.get_optional_user
