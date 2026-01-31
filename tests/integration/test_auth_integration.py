"""Integration tests for authentication module.

These tests verify real Databricks authentication.

Run with:
    # Using profile
    GENIE_PROFILE=your-profile pytest tests/integration/test_auth_integration.py -v

    # Using direct credentials
    DATABRICKS_HOST=https://xxx.cloud.databricks.com DATABRICKS_TOKEN=xxx pytest tests/integration/test_auth_integration.py -v
"""

from __future__ import annotations

from typing import Optional

import pytest

from genie_forge.auth import AuthConfig, get_workspace_client, verify_auth


@pytest.mark.integration
class TestAuthIntegration:
    """Integration tests for authentication."""

    def test_profile_exists_in_databrickscfg(
        self, genie_profile: Optional[str], available_profiles: list[str]
    ) -> None:
        """Test that GENIE_PROFILE exists in databrickscfg."""
        if not genie_profile:
            pytest.skip("Using direct auth (DATABRICKS_HOST/TOKEN), not profile")
        assert genie_profile in available_profiles, (
            f"Profile '{genie_profile}' not found in databrickscfg. "
            f"Available profiles: {available_profiles}"
        )

    def test_workspace_client_authentication(self, workspace_client) -> None:
        """Test that workspace client can authenticate."""
        # Should be able to get current user
        user = workspace_client.current_user.me()
        assert user.user_name is not None
        assert user.id is not None

    def test_verify_auth_returns_user_info(self, workspace_client) -> None:
        """Test verify_auth returns correct user information."""
        info = verify_auth(workspace_client)

        assert "user_name" in info
        assert "user_id" in info
        assert "workspace_url" in info
        assert "auth_type" in info

        assert info["user_name"] is not None
        assert info["workspace_url"].startswith("https://")

    def test_get_workspace_client_with_profile(self, genie_profile: Optional[str]) -> None:
        """Test creating workspace client with profile."""
        if not genie_profile:
            pytest.skip("Using direct auth (DATABRICKS_HOST/TOKEN), not profile")
        client = get_workspace_client(profile=genie_profile)

        # Verify authentication works
        user = client.current_user.me()
        assert user.user_name is not None

    def test_auth_config_from_profile(self, genie_profile: Optional[str]) -> None:
        """Test AuthConfig.from_profile creates valid config."""
        if not genie_profile:
            pytest.skip("Using direct auth (DATABRICKS_HOST/TOKEN), not profile")
        config = AuthConfig.from_profile(genie_profile)

        assert config.profile == genie_profile
        assert config.host is None  # Should use profile, not direct host
        assert config.token is None

    def test_workspace_has_genie_access(self, workspace_client, workspace_info: dict) -> None:
        """Test that workspace has Genie/AI-BI access.

        This is a smoke test to verify the workspace supports Genie.
        """
        # Just verify we can access the workspace
        # Actual Genie API access is tested in client integration tests
        assert workspace_info["workspace_url"] is not None
        print(f"\nWorkspace: {workspace_info['workspace_url']}")
        print(f"User: {workspace_info['user_name']}")
