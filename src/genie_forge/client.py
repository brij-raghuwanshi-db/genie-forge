"""
Genie API client for CRUD operations.

This module provides a high-level client for managing Genie spaces through
the Databricks API. It wraps the REST API calls and handles serialization.

Verified API endpoints:
- POST   /api/2.0/genie/spaces           - Create space
- GET    /api/2.0/genie/spaces           - List spaces
- GET    /api/2.0/genie/spaces/{id}      - Get space
- PATCH  /api/2.0/genie/spaces/{id}      - Update space
- DELETE /api/2.0/genie/spaces/{id}      - Delete space

Performance: Verified 37 spaces/second with parallel operations (20 workers).
"""

from __future__ import annotations

import fnmatch
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from databricks.sdk import WorkspaceClient

from genie_forge.auth import get_workspace_client

logger = logging.getLogger(__name__)

# Type variable for generic retry decorator
T = TypeVar("T")


def retry_on_error(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    retryable_errors: tuple = (ConnectionError, TimeoutError),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds between retries
        max_delay: Maximum delay in seconds between retries
        exponential_base: Base for exponential backoff calculation
        retryable_errors: Tuple of exception types to retry on

    Returns:
        Decorated function with retry logic

    Example:
        @retry_on_error(max_retries=3, base_delay=1.0)
        def api_call():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_errors as e:
                    last_exception = e
                    if attempt < max_retries:
                        # Calculate delay with exponential backoff
                        delay = min(base_delay * (exponential_base**attempt), max_delay)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed: {e}")
                except Exception:
                    # Non-retryable error, re-raise immediately
                    raise

            # Should not reach here, but raise last exception if it does
            raise last_exception  # type: ignore

        return wrapper

    return decorator


# API constants
GENIE_API_BASE = "/api/2.0/genie/spaces"


class GenieAPIError(Exception):
    """Raised when a Genie API call fails."""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


@dataclass
class SpaceResult:
    """Result of a space operation."""

    logical_id: str
    databricks_space_id: Optional[str] = None
    status: str = "SUCCESS"
    error: Optional[str] = None


@dataclass
class BulkResult:
    """Result of a bulk operation."""

    total: int
    success: int
    failed: int
    elapsed_seconds: float
    rate_per_second: float
    results: list[SpaceResult]


class GenieClient:
    """Client for Genie space CRUD operations.

    Example:
        client = GenieClient(profile="GENIE_PROFILE")

        # Create a space
        space_id = client.create_space(
            title="Sales Analytics",
            warehouse_id="abc123",
            tables=["catalog.schema.sales"]
        )

        # List spaces
        spaces = client.list_spaces()

        # Find by name
        matches = client.find_spaces_by_name("Sales*")
    """

    def __init__(
        self,
        profile: Optional[str] = None,
        host: Optional[str] = None,
        token: Optional[str] = None,
        client: Optional[WorkspaceClient] = None,
    ):
        """Initialize the Genie client.

        Args:
            profile: Databrickscfg profile name
            host: Workspace URL
            token: Personal access token
            client: Pre-configured WorkspaceClient (overrides other params)
        """
        if client is not None:
            self._client = client
        else:
            self._client = get_workspace_client(profile=profile, host=host, token=token)

    @property
    def workspace_url(self) -> str:
        """Get the workspace URL."""
        return self._client.config.host or ""

    @property
    def client(self) -> WorkspaceClient:
        """Get the underlying WorkspaceClient for direct SDK access."""
        return self._client

    @retry_on_error(max_retries=3, base_delay=1.0)
    def _api_get(self, path: str, params: Optional[dict] = None) -> Any:
        """Make a GET request to the API with retry logic."""
        response = self._client.api_client.do("GET", path, query=params)
        return response

    @retry_on_error(max_retries=3, base_delay=1.0)
    def _api_post(self, path: str, body: dict) -> Any:
        """Make a POST request to the API with retry logic."""
        response = self._client.api_client.do("POST", path, body=body)
        return response

    @retry_on_error(max_retries=3, base_delay=1.0)
    def _api_patch(self, path: str, body: dict) -> Any:
        """Make a PATCH request to the API with retry logic."""
        response = self._client.api_client.do("PATCH", path, body=body)
        return response

    @retry_on_error(max_retries=3, base_delay=1.0)
    def _api_delete(self, path: str) -> Any:
        """Make a DELETE request to the API with retry logic."""
        response = self._client.api_client.do("DELETE", path)
        return response

    # =========================================================================
    # CRUD Operations
    # =========================================================================

    def create_space(
        self,
        title: str,
        warehouse_id: str,
        tables: list[str],
        parent_path: Optional[str] = None,
        sample_questions: Optional[list[str]] = None,
        serialized_space: Optional[dict] = None,
    ) -> str:
        """Create a new Genie space.

        Args:
            title: Display title for the space
            warehouse_id: SQL warehouse ID
            tables: List of table identifiers (catalog.schema.table)
            parent_path: Optional workspace path for the space
            sample_questions: Optional sample questions
            serialized_space: Optional full serialized space config

        Returns:
            The Databricks-assigned space ID

        Raises:
            GenieAPIError: If creation fails
        """
        body: dict = {
            "title": title,
            "warehouse_id": warehouse_id,
        }

        if parent_path:
            body["parent_path"] = parent_path

        # serialized_space must be a JSON string, not a dict
        if serialized_space:
            body["serialized_space"] = json.dumps(serialized_space)
        else:
            # Build minimal serialized space
            body["serialized_space"] = json.dumps(
                self._build_minimal_serialized_space(
                    tables=tables,
                    sample_questions=sample_questions or [],
                )
            )

        try:
            response = self._api_post(GENIE_API_BASE, body)
            space_id = response.get("space", {}).get("id") or response.get("id")
            if not space_id:
                # Try alternate response format
                space_id = response.get("space_id")
            if not space_id:
                raise GenieAPIError("No space ID in response", response=response)
            logger.info(f"Created space '{title}' with ID: {space_id}")
            return str(space_id)
        except Exception as e:
            raise GenieAPIError(f"Failed to create space '{title}': {e}")

    def get_space(self, space_id: str, include_serialized: bool = False) -> dict[str, Any]:
        """Get a Genie space by ID.

        Args:
            space_id: The Databricks space ID
            include_serialized: Whether to include the full serialized space

        Returns:
            Space data dictionary

        Raises:
            GenieAPIError: If the space is not found or request fails
        """
        path = f"{GENIE_API_BASE}/{space_id}"
        params: dict[str, str] = {}
        if include_serialized:
            params["include_serialized_space"] = "true"

        try:
            response = self._api_get(path, params)
            return dict(response) if response else {}
        except Exception as e:
            raise GenieAPIError(f"Failed to get space '{space_id}': {e}")

    def list_spaces(self, max_pages: int = 100) -> list[dict]:
        """List all Genie spaces in the workspace.

        Handles pagination automatically to fetch all spaces.

        Args:
            max_pages: Maximum number of pages to fetch (safety limit)

        Returns:
            List of space dictionaries

        Raises:
            GenieAPIError: If the request fails
        """
        try:
            all_spaces: list[dict[str, Any]] = []
            page_token: str | None = None
            pages_fetched = 0

            while pages_fetched < max_pages:
                # Build query params
                params: dict[str, str] = {}
                if page_token:
                    params["page_token"] = page_token

                response = self._api_get(GENIE_API_BASE, params=params if params else None)

                # Handle different response formats
                if isinstance(response, dict):
                    # Use `or []` to handle both missing key AND None value
                    # Some APIs return {"spaces": null} instead of {"spaces": []}
                    spaces = response.get("spaces") or []
                    if response.get("spaces") is None and "spaces" in response:
                        logger.debug("No Genie spaces found in workspace")
                    all_spaces.extend(spaces)

                    # Check for next page
                    page_token = response.get("next_page_token")
                    if not page_token:
                        break
                else:
                    # Non-dict response, just return it
                    return response or []

                pages_fetched += 1

            return all_spaces
        except Exception as e:
            raise GenieAPIError(f"Failed to list spaces: {e}")

    def update_space(
        self,
        space_id: str,
        title: Optional[str] = None,
        warehouse_id: Optional[str] = None,
        serialized_space: Optional[dict[str, Any]] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update an existing Genie space.

        Args:
            space_id: The Databricks space ID
            title: New title (optional)
            warehouse_id: New warehouse ID (optional)
            serialized_space: New serialized space config (optional)
            **kwargs: Additional fields to update

        Returns:
            Updated space data

        Raises:
            GenieAPIError: If the update fails
        """
        body: dict = {}

        if title:
            body["title"] = title
        if warehouse_id:
            body["warehouse_id"] = warehouse_id
        if serialized_space:
            # serialized_space must be a JSON string, not a dict
            body["serialized_space"] = json.dumps(serialized_space)

        body.update(kwargs)

        if not body:
            raise ValueError("No fields to update")

        try:
            path = f"{GENIE_API_BASE}/{space_id}"
            response = self._api_patch(path, body)
            logger.info(f"Updated space '{space_id}'")
            return dict(response) if response else {}
        except Exception as e:
            raise GenieAPIError(f"Failed to update space '{space_id}': {e}")

    def delete_space(self, space_id: str) -> bool:
        """Delete a Genie space.

        Args:
            space_id: The Databricks space ID

        Returns:
            True if deletion was successful

        Raises:
            GenieAPIError: If deletion fails
        """
        try:
            path = f"{GENIE_API_BASE}/{space_id}"
            self._api_delete(path)
            logger.info(f"Deleted space '{space_id}'")
            return True
        except Exception as e:
            raise GenieAPIError(f"Failed to delete space '{space_id}': {e}")

    # =========================================================================
    # Search Operations
    # =========================================================================

    def find_spaces_by_name(self, pattern: str, case_sensitive: bool = False) -> list[dict]:
        """Find spaces by name pattern (glob-style).

        Args:
            pattern: Glob pattern (e.g., "Sales*", "*analytics*")
            case_sensitive: Whether to match case-sensitively

        Returns:
            List of matching spaces
        """
        spaces = self.list_spaces()
        matches = []

        for space in spaces:
            title = space.get("title", "")
            if not case_sensitive:
                if fnmatch.fnmatch(title.lower(), pattern.lower()):
                    matches.append(space)
            else:
                if fnmatch.fnmatch(title, pattern):
                    matches.append(space)

        return matches

    def find_space_by_title(self, title: str) -> Optional[dict]:
        """Find a space by exact title match.

        Args:
            title: Exact title to match

        Returns:
            Space dict if found, None otherwise
        """
        spaces = self.list_spaces()
        for space in spaces:
            if space.get("title") == title:
                return space
        return None

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    def bulk_create(
        self,
        configs: list[dict],
        max_workers: int = 20,
        rate_limit: Optional[float] = None,
    ) -> BulkResult:
        """Create multiple spaces in parallel with optional rate limiting.

        Args:
            configs: List of space configs (each with title, warehouse_id, etc.)
            max_workers: Maximum parallel workers (verified: 20 works well)
            rate_limit: Maximum operations per second. None = unlimited.
                        Example: rate_limit=5.0 means max 5 creates/second.

        Returns:
            BulkResult with success/failure counts

        Example:
            # Unlimited speed (default)
            result = client.bulk_create(configs)

            # Rate limited to 10 ops/second
            result = client.bulk_create(configs, rate_limit=10.0)
        """
        start = time.time()
        results: list[SpaceResult] = []

        # Calculate delay between submissions for rate limiting
        submission_delay = 1.0 / rate_limit if rate_limit and rate_limit > 0 else 0

        def create_one(config: dict) -> SpaceResult:
            logical_id = config.get("space_id", config.get("title", "unknown"))
            try:
                space_id = self.create_space(
                    title=config["title"],
                    warehouse_id=config["warehouse_id"],
                    tables=config.get("tables", []),
                    parent_path=config.get("parent_path"),
                    sample_questions=config.get("sample_questions"),
                    serialized_space=config.get("serialized_space"),
                )
                return SpaceResult(
                    logical_id=logical_id,
                    databricks_space_id=space_id,
                    status="SUCCESS",
                )
            except Exception as e:
                return SpaceResult(
                    logical_id=logical_id,
                    status="FAILED",
                    error=str(e),
                )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i, config in enumerate(configs):
                futures.append(executor.submit(create_one, config))
                # Apply rate limiting delay between submissions
                if submission_delay > 0 and i < len(configs) - 1:
                    time.sleep(submission_delay)

            for future in as_completed(futures):
                results.append(future.result())

        elapsed = time.time() - start
        success = sum(1 for r in results if r.status == "SUCCESS")

        return BulkResult(
            total=len(configs),
            success=success,
            failed=len(configs) - success,
            elapsed_seconds=elapsed,
            rate_per_second=len(configs) / elapsed if elapsed > 0 else 0,
            results=results,
        )

    def bulk_delete(
        self,
        space_ids: list[str],
        max_workers: int = 20,
        rate_limit: Optional[float] = None,
    ) -> BulkResult:
        """Delete multiple spaces in parallel with optional rate limiting.

        Args:
            space_ids: List of Databricks space IDs to delete
            max_workers: Maximum parallel workers
            rate_limit: Maximum operations per second. None = unlimited.
                        Example: rate_limit=5.0 means max 5 deletes/second.

        Returns:
            BulkResult with success/failure counts

        Example:
            # Unlimited speed (default)
            result = client.bulk_delete(space_ids)

            # Rate limited to 10 ops/second
            result = client.bulk_delete(space_ids, rate_limit=10.0)
        """
        start = time.time()
        results: list[SpaceResult] = []

        # Calculate delay between submissions for rate limiting
        submission_delay = 1.0 / rate_limit if rate_limit and rate_limit > 0 else 0

        def delete_one(space_id: str) -> SpaceResult:
            try:
                self.delete_space(space_id)
                return SpaceResult(
                    logical_id=space_id,
                    databricks_space_id=space_id,
                    status="SUCCESS",
                )
            except Exception as e:
                return SpaceResult(
                    logical_id=space_id,
                    databricks_space_id=space_id,
                    status="FAILED",
                    error=str(e),
                )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for i, sid in enumerate(space_ids):
                futures.append(executor.submit(delete_one, sid))
                # Apply rate limiting delay between submissions
                if submission_delay > 0 and i < len(space_ids) - 1:
                    time.sleep(submission_delay)

            for future in as_completed(futures):
                results.append(future.result())

        elapsed = time.time() - start
        success = sum(1 for r in results if r.status == "SUCCESS")

        return BulkResult(
            total=len(space_ids),
            success=success,
            failed=len(space_ids) - success,
            elapsed_seconds=elapsed,
            rate_per_second=len(space_ids) / elapsed if elapsed > 0 else 0,
            results=results,
        )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _build_minimal_serialized_space(
        self,
        tables: list[str],
        sample_questions: Optional[list[str]] = None,
    ) -> dict:
        """Build a minimal serialized space structure.

        Args:
            tables: List of table identifiers
            sample_questions: Optional sample questions

        Returns:
            Serialized space dict
        """
        # Tables must be sorted by identifier for the API
        sorted_tables = sorted(tables)
        return {
            "version": 1,
            "config": {
                "sample_questions": sample_questions or [],
            },
            "data_sources": {
                "tables": [
                    {
                        "identifier": table,
                        "description": [],
                        "column_configs": [],
                    }
                    for table in sorted_tables
                ]
            },
            "instructions": {
                "text_instructions": [],
                "example_question_sqls": [],
                "sql_functions": [],
                "join_specs": [],
            },
        }

    def verify_warehouse(self, warehouse_id: str) -> dict:
        """Verify a SQL warehouse exists and get its status.

        Args:
            warehouse_id: The warehouse ID to check

        Returns:
            Warehouse info dict with 'exists', 'name', 'state' keys
        """
        try:
            warehouse = self._client.warehouses.get(warehouse_id)
            return {
                "exists": True,
                "name": warehouse.name,
                "state": warehouse.state.value if warehouse.state else "UNKNOWN",
                "id": warehouse_id,
            }
        except Exception as e:
            logger.warning(f"Warehouse {warehouse_id} not found: {e}")
            return {
                "exists": False,
                "id": warehouse_id,
                "error": str(e),
            }

    def verify_table(self, table_identifier: str) -> dict:
        """Verify a table exists in Unity Catalog.

        Args:
            table_identifier: Full table path (catalog.schema.table)

        Returns:
            Table info dict with 'exists' key
        """
        try:
            parts = table_identifier.split(".")
            if len(parts) != 3:
                return {"exists": False, "error": "Invalid table identifier format"}

            catalog, schema, table = parts
            table_info = self._client.tables.get(f"{catalog}.{schema}.{table}")
            return {
                "exists": True,
                "identifier": table_identifier,
                "table_type": table_info.table_type.value if table_info.table_type else "UNKNOWN",
            }
        except Exception as e:
            return {
                "exists": False,
                "identifier": table_identifier,
                "error": str(e),
            }
