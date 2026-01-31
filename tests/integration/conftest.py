"""Pytest configuration for integration tests.

Integration tests require ONE of:
- GENIE_PROFILE: Profile name from ~/.databrickscfg
- DATABRICKS_HOST + DATABRICKS_TOKEN: Direct credentials

Optional:
- GENIE_CATALOG: Unity Catalog name (default: main)
- GENIE_SCHEMA: Schema name (default: default)
- GENIE_WAREHOUSE_ID: SQL Warehouse ID for demo table tests
"""

from __future__ import annotations

import os
from typing import Generator, Optional

import pytest

from genie_forge.auth import get_workspace_client, list_profiles
from genie_forge.client import GenieClient
from genie_forge.demo_tables import cleanup_demo_tables, create_demo_tables


def _has_databricks_auth() -> bool:
    """Check if Databricks authentication is available.

    Returns True if either:
    - GENIE_PROFILE is set (profile-based auth)
    - DATABRICKS_HOST and DATABRICKS_TOKEN are set (direct auth)
    """
    if os.environ.get("GENIE_PROFILE"):
        return True
    if os.environ.get("DATABRICKS_HOST") and os.environ.get("DATABRICKS_TOKEN"):
        return True
    return False


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest for integration tests."""
    # Add integration marker
    config.addinivalue_line(
        "markers",
        "integration: Tests requiring real Databricks API (requires GENIE_PROFILE or DATABRICKS_HOST/TOKEN)",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip integration tests if no Databricks auth is available."""
    if not _has_databricks_auth():
        skip_integration = pytest.mark.skip(
            reason="No Databricks auth: set GENIE_PROFILE or DATABRICKS_HOST/TOKEN"
        )
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)


@pytest.fixture(scope="session")
def genie_profile() -> Optional[str]:
    """Get the GENIE_PROFILE from environment.

    Returns:
        Profile name from GENIE_PROFILE env var, or None if using direct auth
    """
    return os.environ.get("GENIE_PROFILE")


@pytest.fixture(scope="session")
def genie_catalog() -> str:
    """Get the catalog name for tests.

    Returns:
        Catalog name from GENIE_CATALOG or 'main'
    """
    return os.environ.get("GENIE_CATALOG") or "main"


@pytest.fixture(scope="session")
def genie_schema() -> str:
    """Get the schema name for tests.

    Returns:
        Schema name from GENIE_SCHEMA or 'default'
    """
    return os.environ.get("GENIE_SCHEMA") or "default"


@pytest.fixture(scope="session")
def genie_warehouse_id() -> Optional[str]:
    """Get the warehouse ID for tests.

    Returns:
        Warehouse ID from GENIE_WAREHOUSE_ID or None
    """
    return os.environ.get("GENIE_WAREHOUSE_ID")


@pytest.fixture(scope="session")
def running_warehouse(workspace_client, genie_warehouse_id: Optional[str]) -> Generator:
    """Ensure warehouse is running for tests that need it.

    Starts the warehouse if stopped, waits for it to be ready.
    Does NOT stop the warehouse after tests (to avoid long startup times).

    Args:
        workspace_client: Authenticated WorkspaceClient
        genie_warehouse_id: Warehouse ID from GENIE_WAREHOUSE_ID

    Yields:
        Warehouse ID (or skips if not available)
    """
    import time

    if not genie_warehouse_id:
        pytest.skip("GENIE_WAREHOUSE_ID not set")

    # Get warehouse status
    try:
        warehouse = workspace_client.warehouses.get(genie_warehouse_id)
        state = warehouse.state.value if warehouse.state else "UNKNOWN"
        print(f"\nWarehouse {genie_warehouse_id} state: {state}")

        if state == "RUNNING":
            yield genie_warehouse_id
            return

        if state in ("STOPPED", "STOPPING"):
            print(f"Starting warehouse {genie_warehouse_id}...")
            workspace_client.warehouses.start(genie_warehouse_id)

        # Wait for warehouse to be running (max 5 minutes)
        max_wait = 300  # 5 minutes
        poll_interval = 10  # 10 seconds
        waited = 0

        while waited < max_wait:
            warehouse = workspace_client.warehouses.get(genie_warehouse_id)
            state = warehouse.state.value if warehouse.state else "UNKNOWN"
            print(f"Warehouse state: {state} (waited {waited}s)")

            if state == "RUNNING":
                print(f"Warehouse {genie_warehouse_id} is ready!")
                yield genie_warehouse_id
                return

            if state in ("DELETED", "DELETING"):
                pytest.fail(f"Warehouse {genie_warehouse_id} is {state}")

            time.sleep(poll_interval)
            waited += poll_interval

        pytest.fail(f"Warehouse did not start within {max_wait}s")

    except Exception as e:
        pytest.fail(f"Failed to manage warehouse: {e}")


@pytest.fixture(scope="session")
def workspace_client(genie_profile: Optional[str]) -> Generator:
    """Create an authenticated WorkspaceClient.

    Uses GENIE_PROFILE if set, otherwise falls back to
    DATABRICKS_HOST/TOKEN environment variables.

    Args:
        genie_profile: Profile name from GENIE_PROFILE (may be None)

    Yields:
        Authenticated WorkspaceClient
    """
    if genie_profile:
        client = get_workspace_client(profile=genie_profile)
    else:
        # Fall back to env vars (DATABRICKS_HOST, DATABRICKS_TOKEN)
        client = get_workspace_client()
    yield client


@pytest.fixture(scope="session")
def genie_client(genie_profile: Optional[str]) -> Generator:
    """Create an authenticated GenieClient.

    Uses GENIE_PROFILE if set, otherwise falls back to
    DATABRICKS_HOST/TOKEN environment variables.

    Args:
        genie_profile: Profile name from GENIE_PROFILE (may be None)

    Yields:
        Authenticated GenieClient
    """
    if genie_profile:
        client = GenieClient(profile=genie_profile)
    else:
        # Fall back to env vars
        client = GenieClient()
    yield client


@pytest.fixture(scope="session")
def workspace_info(workspace_client) -> dict:
    """Get workspace information.

    Args:
        workspace_client: Authenticated WorkspaceClient

    Returns:
        Dict with workspace_url and user info
    """
    user = workspace_client.current_user.me()
    return {
        "workspace_url": workspace_client.config.host,
        "user_name": user.user_name,
        "user_id": user.id,
    }


@pytest.fixture
def available_profiles() -> list[str]:
    """List available profiles from databrickscfg.

    Returns:
        List of profile names
    """
    return list_profiles()


@pytest.fixture(scope="session")
def demo_tables_setup(
    genie_client: GenieClient,
    running_warehouse: str,
    genie_catalog: str,
    genie_schema: str,
) -> Generator:
    """Create demo tables for integration tests.

    Creates 6 demo tables (locations, departments, employees, customers, products, sales)
    in the specified catalog/schema. Cleans up after tests complete.

    Args:
        genie_client: Authenticated GenieClient
        running_warehouse: Warehouse ID (must be running)
        genie_catalog: Unity Catalog name
        genie_schema: Schema name

    Yields:
        Dict with demo table names
    """
    print(f"\n=== Setting up demo tables in {genie_catalog}.{genie_schema} ===")

    # Create demo tables
    result = create_demo_tables(
        client=genie_client,
        catalog=genie_catalog,
        schema=genie_schema,
        warehouse_id=running_warehouse,
    )

    if not result["success"]:
        pytest.fail(f"Failed to create demo tables: {result}")

    print(f"Created {result['tables_created']} tables with {result['total_rows']} total rows")

    # Provide table names to tests
    table_names = [f"{genie_catalog}.{genie_schema}.{name}" for name in result["tables"].keys()]

    yield {
        "catalog": genie_catalog,
        "schema": genie_schema,
        "tables": table_names,
        "warehouse_id": running_warehouse,
    }

    # Cleanup after tests
    print(f"\n=== Cleaning up demo tables from {genie_catalog}.{genie_schema} ===")
    cleanup_result = cleanup_demo_tables(
        client=genie_client,
        catalog=genie_catalog,
        schema=genie_schema,
        warehouse_id=running_warehouse,
    )
    print(f"Deleted {cleanup_result['deleted_count']} objects")
