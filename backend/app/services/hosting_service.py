import os
import logging
import asyncio
import subprocess
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.models.deployment import Deployment, DeploymentStatus, DeploymentType
from app.utils.metrics import track_deployment_time, track_deployment_status

logger = logging.getLogger(__name__)

class HostingService:
    """
    Service responsible for hosting user websites on OrbitHost's infrastructure.
    This is the core service that makes OrbitHost a complete hosting platform.
    """
    
    def __init__(self):
        self.base_domain = os.getenv("ORBITHOST_BASE_DOMAIN", "orbithost.app")
        self.hosting_root = os.getenv("ORBITHOST_HOSTING_ROOT", "/var/www/orbithost")
        self.nginx_template_path = os.getenv("NGINX_TEMPLATE_PATH", "templates/nginx.conf")
        
    async def deploy_site(self, deployment: Deployment) -> Dict[str, Any]:
        """
        Deploy a site to OrbitHost's infrastructure.
        
        Args:
            deployment: The deployment to process
            
        Returns:
            A dictionary with deployment information
        """
        logger.info(f"Deploying {deployment.repository_name} @ {deployment.commit_sha} to OrbitHost")
        
        # Start tracking deployment time
        start_time = datetime.now()
        
        try:
            # Generate a subdomain for the site (free tier)
            # For paid tier users, we would use their custom domain
            site_id = self._generate_site_id(deployment.repository_name)
            
            # Clone or update the repository
            repo_path = await self._clone_repository(
                repository=deployment.repository_name,
                commit_sha=deployment.commit_sha,
                site_id=site_id
            )
            
            # Build the site with caching
            build_result = await self._build_site_with_cache(
                repo_path=repo_path,
                site_id=site_id,
                commit_sha=deployment.commit_sha
            )
            
            # Update deployment with cache hit information
            deployment.build_cache_hit = build_result.get("cache_hit", False)
            
            # Configure the web server
            await self._configure_webserver(
                site_id=site_id,
                build_path=build_result["build_path"]
            )
            
            # Generate the site URL
            site_url = f"https://{site_id}.{self.base_domain}"
            
            # For paid tier users with custom domains, we would add:
            # custom_domain = await self._configure_custom_domain(user_id, custom_domain, site_id)
            # if custom_domain:
            #     site_url = f"https://{custom_domain}"
            
            # Update deployment with hosting information
            deployment.url = site_url
            deployment.status = DeploymentStatus.DEPLOYED
            deployment.completed_at = datetime.now()
            
            # Return deployment information
            return {
                "url": site_url,
                "status": "deployed",
                "site_id": site_id,
                "deployed_at": deployment.completed_at.isoformat()
            }
            
        except Exception as e:
            logger.exception(f"Error deploying {deployment.repository_name}: {e}")
            
            # Update deployment with error information
            deployment.status = DeploymentStatus.FAILED
            deployment.error_message = str(e)
            deployment.completed_at = datetime.now()
            
            # Track metrics
            track_deployment_status(
                repository=deployment.repository_name,
                status=deployment.status.value
            )
            
            # Return error information
            return {
                "status": "failed",
                "error": str(e)
            }
        finally:
            # Track deployment time
            duration = (datetime.now() - start_time).total_seconds()
            track_deployment_time(
                repository=deployment.repository_name,
                duration=duration
            )
    
    def _generate_site_id(self, repository_name: str) -> str:
        """
        Generate a site ID from the repository name.
        
        Args:
            repository_name: The repository name (format: owner/repo)
            
        Returns:
            A site ID suitable for use in a subdomain
        """
        # Extract the repository name without the owner
        repo_name = repository_name.split("/")[-1]
        
        # Replace any non-alphanumeric characters with hyphens
        site_id = "".join(c if c.isalnum() else "-" for c in repo_name.lower())
        
        # Ensure the site ID is valid for use in a subdomain
        site_id = site_id.strip("-")
        
        return site_id
    
    async def _clone_repository(self, repository: str, commit_sha: str, site_id: str) -> str:
        """
        Clone or update a repository.
        
        Args:
            repository: The repository to clone (format: owner/repo)
            commit_sha: The commit SHA to checkout
            site_id: The site ID
            
        Returns:
            The path to the cloned repository
        """
        # Create the repository directory
        repo_path = os.path.join(self.hosting_root, "repos", site_id)
        os.makedirs(repo_path, exist_ok=True)
        
        # Check if the repository already exists
        if os.path.exists(os.path.join(repo_path, ".git")):
            # Update the repository
            logger.info(f"Updating repository {repository} in {repo_path}")
            
            # Fetch the latest changes
            await self._run_command(
                command=["git", "fetch", "origin"],
                cwd=repo_path
            )
            
            # Checkout the specified commit
            await self._run_command(
                command=["git", "checkout", commit_sha],
                cwd=repo_path
            )
        else:
            # Clone the repository
            logger.info(f"Cloning repository {repository} to {repo_path}")
            
            # Clone the repository
            await self._run_command(
                command=["git", "clone", f"https://github.com/{repository}.git", "."],
                cwd=repo_path
            )
            
            # Checkout the specified commit
            await self._run_command(
                command=["git", "checkout", commit_sha],
                cwd=repo_path
            )
        
        return repo_path
    
    async def _build_site(self, repo_path: str, site_id: str) -> Dict[str, Any]:
        """
        Build a site from a repository.
        
        Args:
            repo_path: The path to the repository
            site_id: The site ID
            
        Returns:
            A dictionary with build information
        """
        # Detect the site type and build accordingly
        # This is a simplified version that assumes a static site
        # In a real implementation, we would detect the site type (Next.js, React, etc.)
        # and build accordingly
        
        # Create the build directory
        build_path = os.path.join(self.hosting_root, "sites", site_id)
        os.makedirs(build_path, exist_ok=True)
        
        # Check for package.json to detect Node.js projects
        if os.path.exists(os.path.join(repo_path, "package.json")):
            # Install dependencies
            await self._run_command(
                command=["npm", "install"],
                cwd=repo_path
            )
            
            # Build the site
            await self._run_command(
                command=["npm", "run", "build"],
                cwd=repo_path
            )
            
            # Determine the build output directory
            # This varies by framework, so we'll check common directories
            build_output = None
            for directory in ["build", "dist", "out", "public"]:
                if os.path.exists(os.path.join(repo_path, directory)):
                    build_output = os.path.join(repo_path, directory)
                    break
            
            if not build_output:
                raise Exception("Could not determine build output directory")
            
            # Copy the build output to the site directory
            await self._run_command(
                command=["cp", "-r", f"{build_output}/.", build_path],
                cwd=repo_path
            )
        else:
            # Assume a static site
            # Copy the repository contents to the site directory
            await self._run_command(
                command=["cp", "-r", f"{repo_path}/.", build_path],
                cwd=repo_path
            )
        
        return {
            "build_path": build_path,
            "site_id": site_id
        }
    
    async def _configure_webserver(self, site_id: str, build_path: str) -> None:
        """
        Configure the web server for a site.
        
        Args:
            site_id: The site ID
            build_path: The path to the built site
        """
        # In a real implementation, this would configure Nginx or another web server
        # For now, we'll just log the configuration
        logger.info(f"Configuring web server for {site_id} at {build_path}")
        
        # In a real implementation, we would:
        # 1. Generate an Nginx configuration file from a template
        # 2. Reload Nginx to apply the configuration
        
        # For demonstration purposes, we'll just log the configuration
        logger.info(f"Site {site_id} configured at {build_path}")
        logger.info(f"URL: https://{site_id}.{self.base_domain}")
    
    async def _run_command(self, command: List[str], cwd: str) -> str:
        """
        Run a command in a subprocess.
        
        Args:
            command: The command to run
            cwd: The working directory
            
        Returns:
            The command output
        """
        logger.info(f"Running command: {' '.join(command)}")
        
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_message = stderr.decode().strip()
            logger.error(f"Command failed: {error_message}")
            raise Exception(f"Command failed: {error_message}")
        
        return stdout.decode().strip()
    
    async def deploy_preview(self, deployment: Deployment) -> Dict[str, Any]:
        """
        Deploy a preview version of a site.
        
        Args:
            deployment: The deployment to create a preview for
            
        Returns:
            A dictionary with preview deployment information
        """
        logger.info(f"Creating preview for {deployment.repository_name} @ {deployment.commit_sha}")
        
        # Start tracking deployment time
        start_time = datetime.now()
        
        try:
            # Generate a preview site ID
            preview_id = f"preview-{self._generate_site_id(deployment.repository_name)}-{deployment.commit_sha[:7]}"
            
            # Clone or update the repository
            repo_path = await self._clone_repository(
                repository=deployment.repository_name,
                commit_sha=deployment.commit_sha,
                site_id=preview_id
            )
            
            # Build the site with cache if possible
            build_result = await self._build_site_with_cache(
                repo_path=repo_path,
                site_id=preview_id,
                commit_sha=deployment.commit_sha
            )
            
            # Configure the web server for the preview
            await self._configure_webserver(
                site_id=preview_id,
                build_path=build_result["build_path"]
            )
            
            # Generate the preview URL
            preview_url = f"https://{preview_id}.{self.base_domain}"
            
            # Return preview information
            return {
                "url": preview_url,
                "status": "deployed",
                "site_id": preview_id,
                "deployed_at": datetime.now().isoformat(),
                "is_preview": True,
                "build_cache_hit": build_result.get("cache_hit", False)
            }
            
        except Exception as e:
            logger.exception(f"Error creating preview for {deployment.repository_name}: {e}")
            
            # Return error information
            return {
                "status": "failed",
                "error": str(e)
            }
        finally:
            # Track deployment time
            duration = (datetime.now() - start_time).total_seconds()
            track_deployment_time(
                repository=deployment.repository_name,
                duration=duration,
                deployment_type="preview"
            )
    
    async def deploy_rollback(self, deployment: Deployment, target_deployment: Deployment) -> Dict[str, Any]:
        """
        Deploy a rollback to a previous version.
        
        Args:
            deployment: The current deployment
            target_deployment: The deployment to rollback to
            
        Returns:
            A dictionary with rollback deployment information
        """
        logger.info(f"Rolling back {deployment.repository_name} to {target_deployment.commit_sha[:7]}")
        
        # Start tracking deployment time
        start_time = datetime.now()
        
        try:
            # Use the same site ID as the current deployment
            site_id = self._generate_site_id(deployment.repository_name)
            
            # Clone or update the repository to the target commit
            repo_path = await self._clone_repository(
                repository=deployment.repository_name,
                commit_sha=target_deployment.commit_sha,
                site_id=site_id
            )
            
            # Build the site with cache if possible
            build_result = await self._build_site_with_cache(
                repo_path=repo_path,
                site_id=site_id,
                commit_sha=target_deployment.commit_sha
            )
            
            # Configure the web server
            await self._configure_webserver(
                site_id=site_id,
                build_path=build_result["build_path"]
            )
            
            # Generate the site URL
            site_url = f"https://{site_id}.{self.base_domain}"
            
            # Return rollback information
            return {
                "url": site_url,
                "status": "deployed",
                "site_id": site_id,
                "deployed_at": datetime.now().isoformat(),
                "is_rollback": True,
                "build_cache_hit": build_result.get("cache_hit", False)
            }
            
        except Exception as e:
            logger.exception(f"Error rolling back {deployment.repository_name}: {e}")
            
            # Return error information
            return {
                "status": "failed",
                "error": str(e)
            }
        finally:
            # Track deployment time
            duration = (datetime.now() - start_time).total_seconds()
            track_deployment_time(
                repository=deployment.repository_name,
                duration=duration,
                deployment_type="rollback"
            )
    
    async def _build_site_with_cache(self, repo_path: str, site_id: str, commit_sha: str) -> Dict[str, Any]:
        """
        Build a site from a repository with caching.
        
        Args:
            repo_path: The path to the repository
            site_id: The site ID
            commit_sha: The commit SHA
            
        Returns:
            A dictionary with build information
        """
        # Check if we have a cached build for this commit
        cache_path = os.path.join(self.hosting_root, "cache", commit_sha)
        
        if os.path.exists(cache_path):
            logger.info(f"Using cached build for {commit_sha}")
            
            # Create the build directory
            build_path = os.path.join(self.hosting_root, "sites", site_id)
            os.makedirs(build_path, exist_ok=True)
            
            # Copy the cached build to the site directory
            await self._run_command(
                command=["cp", "-r", f"{cache_path}/.", build_path],
                cwd=self.hosting_root
            )
            
            return {
                "build_path": build_path,
                "site_id": site_id,
                "cache_hit": True
            }
        
        # No cached build, build from scratch
        logger.info(f"No cached build found for {commit_sha}, building from scratch")
        
        # Build the site
        build_result = await self._build_site(repo_path, site_id)
        
        # Cache the build
        os.makedirs(cache_path, exist_ok=True)
        await self._run_command(
            command=["cp", "-r", f"{build_result['build_path']}/.", cache_path],
            cwd=self.hosting_root
        )
        
        build_result["cache_hit"] = False
        return build_result
    
    async def delete_site(self, site_id: str) -> bool:
        """
        Delete a site.
        
        Args:
            site_id: The site ID
            
        Returns:
            True if the site was deleted, False otherwise
        """
        logger.info(f"Deleting site {site_id}")
        
        try:
            # Delete the site directory
            site_path = os.path.join(self.hosting_root, "sites", site_id)
            if os.path.exists(site_path):
                await self._run_command(
                    command=["rm", "-rf", site_path],
                    cwd=self.hosting_root
                )
            
            # Delete the repository directory
            repo_path = os.path.join(self.hosting_root, "repos", site_id)
            if os.path.exists(repo_path):
                await self._run_command(
                    command=["rm", "-rf", repo_path],
                    cwd=self.hosting_root
                )
            
            # In a real implementation, we would also:
            # 1. Remove the Nginx configuration
            # 2. Reload Nginx to apply the configuration
            
            return True
        except Exception as e:
            logger.exception(f"Error deleting site {site_id}: {e}")
            return False
