import pytest
import asyncio
from unittest.mock import MagicMock, patch

from app.models.github import GitHubPushEvent, GitHubRepository, GitHubUser, GitHubCommit
from app.models.deployment import Deployment, DeploymentStatus

# Import the deployment service - this will use the public version in the GitHub repo
# but can use the full version with monetization features in your private deployment
from app.services.deployment_service import DeploymentService

@pytest.fixture
def mock_push_event():
    """Create a mock GitHub push event for testing"""
    return GitHubPushEvent(
        ref="refs/heads/main",
        before="0000000000000000000000000000000000000000",
        after="1111111111111111111111111111111111111111",
        repository=GitHubRepository(
            id=12345,
            name="test-repo",
            full_name="user/test-repo",
            private=False,
            html_url="https://github.com/user/test-repo",
            description="Test repository",
            default_branch="main"
        ),
        pusher=GitHubUser(
            name="Test User",
            email="test@example.com",
            username="testuser"
        ),
        sender=GitHubUser(
            name="Test User",
            email="test@example.com",
            username="testuser"
        ),
        created=False,
        deleted=False,
        forced=False,
        commits=[
            GitHubCommit(
                id="1111111111111111111111111111111111111111",
                message="Test commit",
                timestamp="2025-05-15T12:00:00Z",
                url="https://github.com/user/test-repo/commit/1111111111111111111111111111111111111111",
                author=GitHubUser(
                    name="Test User",
                    email="test@example.com",
                    username="testuser"
                ),
                committer=GitHubUser(
                    name="Test User",
                    email="test@example.com",
                    username="testuser"
                )
            )
        ],
        head_commit=GitHubCommit(
            id="1111111111111111111111111111111111111111",
            message="Test commit",
            timestamp="2025-05-15T12:00:00Z",
            url="https://github.com/user/test-repo/commit/1111111111111111111111111111111111111111",
            author=GitHubUser(
                name="Test User",
                email="test@example.com",
                username="testuser"
            ),
            committer=GitHubUser(
                name="Test User",
                email="test@example.com",
                username="testuser"
            )
        )
    )

@pytest.mark.asyncio
async def test_process_github_push(mock_push_event):
    """Test the GitHub push event processing"""
    # Create mocks for the services
    mock_fly_service = MagicMock()
    mock_screenshot_service = MagicMock()
    mock_webhook_service = MagicMock()
    
    # Set up the mock return values
    mock_fly_service.deploy.return_value = {
        "id": "deployment_12345678",
        "url": "https://test-repo.fly.dev",
        "status": "success",
        "app_name": "test-repo",
        "region": "sea",
        "created_at": "2025-05-15T12:00:00Z"
    }
    
    mock_screenshot_service.capture.return_value = {
        "screenshot_url": "https://storage.orbithost.example/screenshots/screenshot_12345678.png",
        "dom_content": "<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello World</h1></body></html>",
        "captured_at": "2025-05-15T12:05:00Z",
        "url": "https://test-repo.fly.dev"
    }
    
    # Create the deployment service with mocked dependencies
    deployment_service = DeploymentService()
    deployment_service.fly_service = mock_fly_service
    deployment_service.screenshot_service = mock_screenshot_service
    deployment_service.webhook_service = mock_webhook_service
    
    # Mock the _wait_for_deployment method to return True immediately
    deployment_service._wait_for_deployment = MagicMock(return_value=True)
    
    # Process the push event
    await deployment_service.process_github_push(mock_push_event)
    
    # Verify that the services were called with the correct arguments
    mock_fly_service.deploy.assert_called_once()
    assert mock_fly_service.deploy.call_args[1]["repository"] == "user/test-repo"
    assert mock_fly_service.deploy.call_args[1]["commit_sha"] == "1111111111111111111111111111111111111111"
    assert mock_fly_service.deploy.call_args[1]["branch"] == "main"
    
    mock_screenshot_service.capture.assert_called_once()
    assert mock_screenshot_service.capture.call_args[0][0] == "https://test-repo.fly.dev"
    
    mock_webhook_service.send_deployment_webhook.assert_called_once()
    # Verify the deployment object passed to the webhook service
    deployment = mock_webhook_service.send_deployment_webhook.call_args[0][0]
    assert deployment.repository_name == "user/test-repo"
    assert deployment.commit_sha == "1111111111111111111111111111111111111111"
    assert deployment.branch == "main"
    assert deployment.status == DeploymentStatus.DEPLOYED
    assert deployment.url == "https://test-repo.fly.dev"
    assert deployment.author == "Test User"
    assert deployment.commit_message == "Test commit"
    assert deployment.screenshot_url == "https://storage.orbithost.example/screenshots/screenshot_12345678.png"
    assert deployment.dom_content == "<!DOCTYPE html><html><head><title>Test</title></head><body><h1>Hello World</h1></body></html>"
