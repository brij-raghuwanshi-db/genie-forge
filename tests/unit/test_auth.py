"""Unit tests for genie_forge.auth."""

import os
from unittest.mock import MagicMock, patch

import pytest

from genie_forge.auth import (
    AuthConfig,
    AuthenticationError,
    get_workspace_client,
    list_profiles,
    verify_auth,
)


class TestAuthConfig:
    """Tests for AuthConfig dataclass."""

    def test_from_profile(self):
        """Test creating auth config from profile."""
        config = AuthConfig.from_profile("TEST_PROFILE")
        assert config.profile == "TEST_PROFILE"
        assert config.host is None
        assert config.token is None

    def test_from_profile_with_config_file(self, tmp_path):
        """Test creating auth config with custom config file."""
        config_file = tmp_path / ".databrickscfg"
        config = AuthConfig.from_profile("TEST", config_file=config_file)
        assert config.profile == "TEST"
        assert config.config_file == config_file

    def test_from_env(self):
        """Test creating auth config from environment variables."""
        with patch.dict(
            os.environ,
            {
                "DATABRICKS_HOST": "https://test.databricks.com",
                "DATABRICKS_TOKEN": "test-token",
            },
        ):
            config = AuthConfig.from_env()
            assert config.host == "https://test.databricks.com"
            assert config.token == "test-token"

    def test_from_env_missing_vars(self):
        """Test from_env when environment variables are not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove any existing vars
            env = os.environ.copy()
            env.pop("DATABRICKS_HOST", None)
            env.pop("DATABRICKS_TOKEN", None)

            with patch.dict(os.environ, env, clear=True):
                config = AuthConfig.from_env()
                # Should still create config, just with None values
                assert config.host is None or config.host == ""
                assert config.token is None or config.token == ""

    def test_from_direct(self):
        """Test creating auth config with direct credentials."""
        config = AuthConfig.from_direct(
            host="https://test.databricks.com",
            token="test-token",
        )
        assert config.host == "https://test.databricks.com"
        assert config.token == "test-token"


class TestGetWorkspaceClient:
    """Tests for get_workspace_client function."""

    @patch("genie_forge.auth.WorkspaceClient")
    def test_with_profile(self, mock_ws_client):
        """Test creating client with profile."""
        mock_instance = MagicMock()
        mock_ws_client.return_value = mock_instance

        get_workspace_client(profile="TEST_PROFILE")

        mock_ws_client.assert_called_once()
        call_kwargs = mock_ws_client.call_args[1]
        assert call_kwargs.get("profile") == "TEST_PROFILE"

    @patch("genie_forge.auth.WorkspaceClient")
    def test_with_direct_credentials(self, mock_ws_client):
        """Test creating client with direct host/token."""
        mock_instance = MagicMock()
        mock_ws_client.return_value = mock_instance

        get_workspace_client(
            host="https://test.databricks.com",
            token="test-token",
        )

        mock_ws_client.assert_called_once()
        call_kwargs = mock_ws_client.call_args[1]
        assert call_kwargs.get("host") == "https://test.databricks.com"
        assert call_kwargs.get("token") == "test-token"

    @patch("genie_forge.auth.WorkspaceClient")
    def test_with_env_vars(self, mock_ws_client):
        """Test creating client with environment variables."""
        mock_instance = MagicMock()
        mock_ws_client.return_value = mock_instance

        with patch.dict(
            os.environ,
            {
                "DATABRICKS_HOST": "https://env.databricks.com",
                "DATABRICKS_TOKEN": "env-token",
            },
        ):
            get_workspace_client()

        mock_ws_client.assert_called_once()

    @patch("genie_forge.auth.WorkspaceClient")
    def test_client_creation_failure(self, mock_ws_client):
        """Test handling of client creation failure."""
        mock_ws_client.side_effect = Exception("Connection failed")

        with pytest.raises(AuthenticationError) as exc_info:
            get_workspace_client(profile="INVALID")

        assert "Failed to create workspace client" in str(exc_info.value)


class TestListProfiles:
    """Tests for list_profiles function."""

    def test_list_profiles_with_file(self, tmp_path):
        """Test listing profiles from config file."""
        config_file = tmp_path / ".databrickscfg"
        # Note: [DEFAULT] is a special section in ConfigParser, not listed as a regular section
        config_file.write_text("""
[DEV_PROFILE]
host = https://dev.databricks.com
token = dev-token

[PROD_PROFILE]
host = https://prod.databricks.com
token = prod-token

[TEST_PROFILE]
host = https://test.databricks.com
token = test-token
""")

        profiles = list_profiles(config_file=config_file)

        assert "DEV_PROFILE" in profiles
        assert "PROD_PROFILE" in profiles
        assert "TEST_PROFILE" in profiles
        assert len(profiles) == 3

    def test_list_profiles_empty_file(self, tmp_path):
        """Test listing profiles from empty config file."""
        config_file = tmp_path / ".databrickscfg"
        config_file.write_text("")

        profiles = list_profiles(config_file=config_file)

        assert profiles == []

    def test_list_profiles_no_file(self, tmp_path):
        """Test listing profiles when file doesn't exist."""
        config_file = tmp_path / "nonexistent"

        profiles = list_profiles(config_file=config_file)

        assert profiles == []


class TestVerifyAuth:
    """Tests for verify_auth function."""

    def test_verify_success(self):
        """Test successful authentication verification."""
        mock_client = MagicMock()
        mock_client.current_user.me.return_value = MagicMock(user_name="test@example.com")

        result = verify_auth(mock_client)

        assert "user_name" in result or result is not None

    def test_verify_failure(self):
        """Test failed authentication verification."""
        mock_client = MagicMock()
        mock_client.current_user.me.side_effect = Exception("Auth failed")

        with pytest.raises(AuthenticationError) as exc_info:
            verify_auth(mock_client)

        assert "Failed to verify authentication" in str(exc_info.value)


class TestAuthenticationError:
    """Tests for AuthenticationError exception."""

    def test_error_message(self):
        """Test error with message."""
        error = AuthenticationError("Test error message")
        assert str(error) == "Test error message"

    def test_error_inheritance(self):
        """Test that AuthenticationError is an Exception."""
        error = AuthenticationError("Test")
        assert isinstance(error, Exception)
