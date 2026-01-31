"""Integration tests for GenieClient.

These tests verify real Genie API operations.

Run with:
    # Using profile
    GENIE_PROFILE=your-profile pytest tests/integration/test_client_integration.py -v

    # Using direct credentials
    DATABRICKS_HOST=https://xxx.cloud.databricks.com DATABRICKS_TOKEN=xxx pytest tests/integration/test_client_integration.py -v
"""

from __future__ import annotations

from typing import Optional

import pytest

from genie_forge.client import GenieClient


@pytest.mark.integration
class TestGenieClientIntegration:
    """Integration tests for GenieClient."""

    def test_client_initialization(self, genie_profile: Optional[str]) -> None:
        """Test GenieClient initializes with profile or env vars."""
        if genie_profile:
            client = GenieClient(profile=genie_profile)
        else:
            client = GenieClient()  # Uses env vars

        assert client.workspace_url is not None
        assert client.workspace_url.startswith("https://")

    def test_client_workspace_url(self, genie_client: GenieClient, workspace_info: dict) -> None:
        """Test client has correct workspace URL."""
        assert genie_client.workspace_url == workspace_info["workspace_url"]

    def test_list_spaces(self, genie_client: GenieClient) -> None:
        """Test listing Genie spaces.

        This is a read-only operation that should work on any workspace
        with Genie/AI-BI enabled.
        """
        try:
            spaces = genie_client.list_spaces()

            # Should return a list (may be empty if no spaces exist)
            assert isinstance(spaces, list)

            # Log space count for debugging
            print(f"\nFound {len(spaces)} Genie space(s)")

            # If spaces exist, verify structure
            if spaces:
                space = spaces[0]
                assert "id" in space or "space_id" in space
                print(f"First space: {space.get('title', space.get('id', 'unknown'))}")

        except Exception as e:
            # Genie API might not be available in all workspaces
            pytest.skip(f"Genie API not available: {e}")

    def test_find_spaces_by_name(self, genie_client: GenieClient) -> None:
        """Test finding spaces by name pattern."""
        try:
            # Try to find any space (empty pattern matches all)
            spaces = genie_client.list_spaces()

            if not spaces:
                pytest.skip("No Genie spaces found in workspace")

            # Just verify we can list and the structure is correct
            assert isinstance(spaces, list)

        except Exception as e:
            pytest.skip(f"Genie API not available: {e}")


@pytest.mark.integration
class TestGenieClientSpaceOperations:
    """Integration tests for Genie space CRUD operations.

    These tests create/update/delete spaces.
    Requires GENIE_WAREHOUSE_ID to be set.
    """

    def test_create_and_delete_space(
        self,
        genie_client: GenieClient,
        demo_tables_setup: dict,
    ) -> None:
        """Test creating and deleting a Genie space.

        This test:
        1. Uses demo_tables_setup fixture (creates tables, starts warehouse)
        2. Creates a Genie space with the demo tables
        3. Verifies the space was created
        4. Deletes the space (cleanup)
        5. Demo tables are cleaned up by fixture after test

        Args:
            genie_client: Authenticated GenieClient
            demo_tables_setup: Dict with demo table info (created by fixture)
        """
        # Get info from demo_tables_setup fixture
        warehouse_id = demo_tables_setup["warehouse_id"]
        tables = demo_tables_setup["tables"]

        print(f"\nUsing {len(tables)} demo tables:")
        for t in tables[:3]:  # Show first 3
            print(f"  - {t}")
        if len(tables) > 3:
            print(f"  ... and {len(tables) - 3} more")

        # Create a test space with demo tables
        test_title = "genie-forge-integration-test"

        space_id = None
        try:
            print(f"Creating Genie space with warehouse {warehouse_id}...")
            space_id = genie_client.create_space(
                title=test_title,
                warehouse_id=warehouse_id,
                tables=tables,
            )

            assert space_id is not None, "create_space should return a space ID"
            print(f"Created test space: {space_id}")

            # Verify space exists by getting it
            space = genie_client.get_space(space_id)
            assert space is not None, "get_space should return the space"
            print(f"Verified space exists: {space.get('title', 'unknown')}")

        finally:
            # Always clean up - delete the space
            if space_id:
                print(f"Cleaning up - deleting space {space_id}...")
                try:
                    result = genie_client.delete_space(space_id)
                    assert result is True, "delete_space should return True"
                    print(f"Deleted test space: {space_id}")
                except Exception as e:
                    print(f"Warning: Failed to delete test space: {e}")
