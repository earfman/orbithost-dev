"""
Dependency injection for database services.

This module provides dependency injection functions for database services.
"""

import logging
from typing import AsyncGenerator

from app.db.services import (
    UserService,
    TeamService,
    ProjectService,
)

# Configure logging
logger = logging.getLogger(__name__)


async def get_user_service() -> AsyncGenerator[UserService, None]:
    """
    Get a UserService instance.
    
    Yields:
        UserService instance
    """
    service = UserService()
    try:
        yield service
    except Exception as e:
        logger.error(f"Error with UserService: {str(e)}")
        raise


async def get_team_service() -> AsyncGenerator[TeamService, None]:
    """
    Get a TeamService instance.
    
    Yields:
        TeamService instance
    """
    service = TeamService()
    try:
        yield service
    except Exception as e:
        logger.error(f"Error with TeamService: {str(e)}")
        raise


async def get_project_service() -> AsyncGenerator[ProjectService, None]:
    """
    Get a ProjectService instance.
    
    Yields:
        ProjectService instance
    """
    service = ProjectService()
    try:
        yield service
    except Exception as e:
        logger.error(f"Error with ProjectService: {str(e)}")
        raise

# Add more dependency injection functions for other services as needed
