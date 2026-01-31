"""
Authentication module for Genie-Forge.

Supports:
- databrickscfg profiles (~/.databrickscfg)
- Environment variables (DATABRICKS_HOST, DATABRICKS_TOKEN)
- Direct host/token parameters

MVP scope: Basic auth with profile and env var support.
Full product will add: U2M OAuth, M2M OAuth, Azure CLI support.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from databricks.sdk import WorkspaceClient

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails.

    Automatically masks sensitive tokens in error messages.
    """

    # Patterns for sensitive data that should be masked
    _SENSITIVE_PATTERNS = [
        (r"dapi[a-f0-9]{32}", "dapi****"),  # Databricks PAT
        (r"(token[:\s=]+)['\"]?([a-zA-Z0-9_-]{20,})['\"]?", r"\1****"),  # Generic tokens
        (r"(Bearer\s+)[a-zA-Z0-9_.-]+", r"\1****"),  # Bearer tokens
    ]

    def __init__(self, message: str):
        self.original_message = message
        self.masked_message = self._mask_sensitive(message)
        super().__init__(self.masked_message)

    def _mask_sensitive(self, text: str) -> str:
        """Mask sensitive tokens in text."""
        import re

        result = text
        for pattern, replacement in self._SENSITIVE_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        return result

    def __str__(self) -> str:
        return self.masked_message

    def __repr__(self) -> str:
        return f"AuthenticationError({self.masked_message!r})"


@dataclass
class AuthConfig:
    """Authentication configuration."""

    host: Optional[str] = None
    token: Optional[str] = None
    profile: Optional[str] = None
    config_file: Optional[Path] = None

    @classmethod
    def from_profile(cls, profile: str, config_file: Optional[Path] = None) -> AuthConfig:
        """Create auth config from a databrickscfg profile.

        Args:
            profile: Profile name from ~/.databrickscfg
            config_file: Optional path to config file (defaults to ~/.databrickscfg)

        Returns:
            AuthConfig configured for the profile
        """
        return cls(profile=profile, config_file=config_file)

    @classmethod
    def from_env(cls) -> AuthConfig:
        """Create auth config from environment variables.

        Uses DATABRICKS_HOST and DATABRICKS_TOKEN environment variables.

        Returns:
            AuthConfig from environment
        """
        host = os.environ.get("DATABRICKS_HOST")
        token = os.environ.get("DATABRICKS_TOKEN")
        return cls(host=host, token=token)

    @classmethod
    def from_direct(cls, host: str, token: str) -> AuthConfig:
        """Create auth config from direct host/token.

        Args:
            host: Databricks workspace URL
            token: Personal access token

        Returns:
            AuthConfig with direct credentials
        """
        return cls(host=host, token=token)


def get_workspace_client(
    profile: Optional[str] = None,
    host: Optional[str] = None,
    token: Optional[str] = None,
    config_file: Optional[Path] = None,
) -> WorkspaceClient:
    """Get an authenticated WorkspaceClient.

    Authentication priority:
    1. Direct host/token if both provided
    2. Profile from databrickscfg if provided
    3. Environment variables (DATABRICKS_HOST, DATABRICKS_TOKEN)
    4. Default SDK authentication (databrickscfg DEFAULT profile)

    Args:
        profile: Optional databrickscfg profile name
        host: Optional workspace URL
        token: Optional personal access token
        config_file: Optional path to databrickscfg file

    Returns:
        Authenticated WorkspaceClient

    Raises:
        AuthenticationError: If authentication fails
    """
    try:
        # Build config kwargs
        config_kwargs: dict = {}

        if host and token:
            # Direct credentials
            logger.debug("Using direct host/token authentication")
            config_kwargs["host"] = host
            config_kwargs["token"] = token
        elif profile:
            # Profile-based auth
            logger.debug(f"Using profile authentication: {profile}")
            config_kwargs["profile"] = profile
            if config_file:
                config_kwargs["config_file"] = str(config_file)
        else:
            # Try environment variables
            env_host = os.environ.get("DATABRICKS_HOST")
            env_token = os.environ.get("DATABRICKS_TOKEN")
            if env_host and env_token:
                logger.debug("Using environment variable authentication")
                config_kwargs["host"] = env_host
                config_kwargs["token"] = env_token
            else:
                # Fall back to default SDK auth
                logger.debug("Using default SDK authentication")

        # Create client
        client = WorkspaceClient(**config_kwargs)

        # Verify authentication by getting current user
        try:
            current_user = client.current_user.me()
            logger.info(f"Authenticated as: {current_user.user_name}")
        except Exception as e:
            raise AuthenticationError(f"Failed to verify authentication: {e}")

        return client

    except AuthenticationError:
        raise
    except Exception as e:
        raise AuthenticationError(f"Failed to create workspace client: {e}")


def verify_auth(client: WorkspaceClient) -> dict:
    """Verify authentication and return user info.

    Args:
        client: WorkspaceClient to verify

    Returns:
        Dict with user info (user_name, user_id, workspace_url)

    Raises:
        AuthenticationError: If verification fails
    """
    try:
        user = client.current_user.me()
        config = client.config

        return {
            "user_name": user.user_name,
            "user_id": user.id,
            "workspace_url": config.host,
            "auth_type": config.auth_type,
        }
    except Exception as e:
        raise AuthenticationError(f"Failed to verify authentication: {e}")


def list_profiles(config_file: Optional[Path] = None) -> list[str]:
    """List available profiles from databrickscfg.

    Args:
        config_file: Optional path to config file

    Returns:
        List of profile names
    """
    if config_file is None:
        config_file = Path.home() / ".databrickscfg"

    if not config_file.exists():
        return []

    profiles = []
    try:
        import configparser

        config = configparser.ConfigParser()
        config.read(config_file)
        profiles = config.sections()
    except Exception as e:
        logger.warning(f"Failed to read config file: {e}")

    return profiles


class AuthManager:
    """Manager for authentication across environments.

    This class helps manage authentication for multiple environments
    (dev, staging, prod) from configuration files.
    """

    def __init__(self) -> None:
        self._clients: dict[str, WorkspaceClient] = {}

    def get_client(
        self,
        env: str,
        profile: Optional[str] = None,
        host: Optional[str] = None,
        token: Optional[str] = None,
    ) -> WorkspaceClient:
        """Get or create a client for an environment.

        Args:
            env: Environment name (for caching)
            profile: Optional profile name
            host: Optional workspace URL
            token: Optional token

        Returns:
            Authenticated WorkspaceClient
        """
        cache_key = f"{env}:{profile or 'default'}"

        if cache_key not in self._clients:
            self._clients[cache_key] = get_workspace_client(profile=profile, host=host, token=token)

        return self._clients[cache_key]

    def clear_cache(self) -> None:
        """Clear the client cache."""
        self._clients.clear()
