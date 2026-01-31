"""Unit tests for HTTP error handling in GenieClient.

Tests API error responses, rate limiting, timeouts, and network failures.
These are critical for production reliability.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from genie_forge.client import (
    BulkResult,
    GenieAPIError,
    GenieClient,
    retry_on_error,
)

# =============================================================================
# HTTP Status Code Error Handling
# =============================================================================


class TestHTTPStatusCodeErrors:
    """Tests for handling various HTTP status codes."""

    @pytest.fixture
    def mock_workspace_client(self):
        """Create a mock WorkspaceClient."""
        mock = MagicMock()
        mock.config.host = "https://test.databricks.com"
        return mock

    @pytest.fixture
    def client(self, mock_workspace_client):
        """Create a GenieClient with mocked workspace client."""
        return GenieClient(client=mock_workspace_client)

    def test_400_bad_request_error(self, client, mock_workspace_client):
        """Test handling 400 Bad Request errors."""
        error = Exception("BAD_REQUEST: Invalid space configuration")
        mock_workspace_client.api_client.do.side_effect = error

        with pytest.raises(GenieAPIError) as exc_info:
            client.create_space(
                title="Test",
                warehouse_id="wh123",
                tables=["cat.sch.tbl"],
            )

        assert "Failed to create space" in str(exc_info.value)

    def test_401_unauthorized_error(self, client, mock_workspace_client):
        """Test handling 401 Unauthorized errors."""
        error = Exception("UNAUTHENTICATED: Invalid token")
        mock_workspace_client.api_client.do.side_effect = error

        with pytest.raises(GenieAPIError) as exc_info:
            client.list_spaces()

        assert "Failed to list spaces" in str(exc_info.value)

    def test_403_forbidden_error(self, client, mock_workspace_client):
        """Test handling 403 Forbidden errors."""
        error = Exception("PERMISSION_DENIED: Access denied to space")
        mock_workspace_client.api_client.do.side_effect = error

        with pytest.raises(GenieAPIError) as exc_info:
            client.get_space("space-123")

        assert "Failed to get space" in str(exc_info.value)

    def test_404_not_found_error(self, client, mock_workspace_client):
        """Test handling 404 Not Found errors."""
        error = Exception("NOT_FOUND: Space 'nonexistent' not found")
        mock_workspace_client.api_client.do.side_effect = error

        with pytest.raises(GenieAPIError) as exc_info:
            client.get_space("nonexistent")

        assert "Failed to get space" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)

    def test_500_internal_server_error(self, client, mock_workspace_client):
        """Test handling 500 Internal Server Error."""
        error = Exception("INTERNAL_ERROR: Unexpected server error")
        mock_workspace_client.api_client.do.side_effect = error

        with pytest.raises(GenieAPIError) as exc_info:
            client.list_spaces()

        assert "Failed to list spaces" in str(exc_info.value)

    def test_502_bad_gateway_error(self, client, mock_workspace_client):
        """Test handling 502 Bad Gateway errors."""
        error = Exception("Bad Gateway")
        mock_workspace_client.api_client.do.side_effect = error

        with pytest.raises(GenieAPIError):
            client.list_spaces()

    def test_503_service_unavailable(self, client, mock_workspace_client):
        """Test handling 503 Service Unavailable."""
        error = Exception("Service Unavailable")
        mock_workspace_client.api_client.do.side_effect = error

        with pytest.raises(GenieAPIError):
            client.list_spaces()


# =============================================================================
# Rate Limiting (429) Tests
# =============================================================================


class TestRateLimiting:
    """Tests for rate limiting handling (HTTP 429)."""

    def test_rate_limit_respected_in_bulk_create(self):
        """Test that rate limiting delays bulk operations."""
        mock_client = MagicMock()
        mock_client.config.host = "https://test.databricks.com"
        mock_client.api_client.do.return_value = {"space": {"id": "new-id"}}

        client = GenieClient(client=mock_client)

        configs = [
            {"title": f"Space {i}", "warehouse_id": "wh", "tables": ["c.s.t"]} for i in range(5)
        ]

        # With rate_limit=10.0, should have ~0.4s of delays (4 delays of 0.1s)
        start = time.time()
        result = client.bulk_create(configs, max_workers=1, rate_limit=10.0)
        elapsed = time.time() - start

        assert result.total == 5
        assert result.success == 5
        # Should have some delay due to rate limiting
        assert elapsed >= 0.3  # At least 4 * 0.1s = 0.4s but with tolerance

    def test_rate_limit_zero_means_unlimited(self):
        """Test that rate_limit=0 or None means no limiting."""
        mock_client = MagicMock()
        mock_client.config.host = "https://test.databricks.com"
        mock_client.api_client.do.return_value = {"space": {"id": "new-id"}}

        client = GenieClient(client=mock_client)

        configs = [
            {"title": f"Space {i}", "warehouse_id": "wh", "tables": ["c.s.t"]} for i in range(3)
        ]

        # Without rate limiting, should be fast
        start = time.time()
        result = client.bulk_create(configs, max_workers=3, rate_limit=None)
        elapsed = time.time() - start

        assert result.total == 3
        # Should be fast (no rate limiting delays)
        assert elapsed < 2.0  # Should complete quickly


# =============================================================================
# Connection and Timeout Tests
# =============================================================================


class TestConnectionErrors:
    """Tests for connection and timeout errors."""

    def test_connection_error_retry(self):
        """Test that ConnectionError triggers retry."""
        call_count = 0

        @retry_on_error(max_retries=2, base_delay=0.01)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection refused")
            return "success"

        result = flaky_func()
        assert result == "success"
        assert call_count == 3  # 2 failures + 1 success

    def test_timeout_error_retry(self):
        """Test that TimeoutError triggers retry."""
        call_count = 0

        @retry_on_error(max_retries=2, base_delay=0.01)
        def timeout_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise TimeoutError("Connection timed out")
            return "success"

        result = timeout_func()
        assert result == "success"
        assert call_count == 3

    def test_max_delay_cap(self):
        """Test that delay is capped at max_delay."""
        delays = []
        call_count = 0

        @retry_on_error(
            max_retries=5,
            base_delay=1.0,
            max_delay=0.05,  # Cap at 0.05s for fast test
            exponential_base=10.0,  # Would normally grow very fast
        )
        def track_delays():
            nonlocal call_count
            call_count += 1
            delays.append(time.time())
            if call_count <= 4:
                raise ConnectionError("Retry")
            return "done"

        start = time.time()
        result = track_delays()
        total_time = time.time() - start

        assert result == "done"
        # With max_delay=0.05, total should be around 4 * 0.05 = 0.2s
        # (plus some execution time)
        assert total_time < 1.0  # Should not have exponential delays

    def test_non_retryable_error_not_retried(self):
        """Test that non-retryable errors are raised immediately."""
        call_count = 0

        @retry_on_error(max_retries=3, base_delay=0.01)
        def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("This should not be retried")

        with pytest.raises(ValueError):
            raises_value_error()

        assert call_count == 1  # No retries for ValueError


# =============================================================================
# API Response Edge Cases
# =============================================================================


class TestAPIResponseEdgeCases:
    """Tests for unusual API responses."""

    @pytest.fixture
    def mock_workspace_client(self):
        """Create a mock WorkspaceClient."""
        mock = MagicMock()
        mock.config.host = "https://test.databricks.com"
        return mock

    @pytest.fixture
    def client(self, mock_workspace_client):
        """Create a GenieClient with mocked workspace client."""
        return GenieClient(client=mock_workspace_client)

    def test_create_space_empty_response(self, client, mock_workspace_client):
        """Test handling empty response from create API."""
        mock_workspace_client.api_client.do.return_value = {}

        with pytest.raises(GenieAPIError) as exc_info:
            client.create_space(
                title="Test",
                warehouse_id="wh123",
                tables=["cat.sch.tbl"],
            )

        assert "No space ID in response" in str(exc_info.value)

    def test_create_space_no_id_in_nested_response(self, client, mock_workspace_client):
        """Test handling response with missing ID."""
        mock_workspace_client.api_client.do.return_value = {"space": {}}

        with pytest.raises(GenieAPIError) as exc_info:
            client.create_space(
                title="Test",
                warehouse_id="wh123",
                tables=["cat.sch.tbl"],
            )

        assert "No space ID in response" in str(exc_info.value)

    def test_create_space_alternate_response_format(self, client, mock_workspace_client):
        """Test handling alternate response format with space_id."""
        mock_workspace_client.api_client.do.return_value = {"space_id": "alt-id-123"}

        space_id = client.create_space(
            title="Test",
            warehouse_id="wh123",
            tables=["cat.sch.tbl"],
        )

        assert space_id == "alt-id-123"

    def test_list_spaces_empty_response(self, client, mock_workspace_client):
        """Test handling empty response from list API."""
        mock_workspace_client.api_client.do.return_value = {}

        spaces = client.list_spaces()
        assert spaces == []

    def test_list_spaces_none_spaces_field(self, client, mock_workspace_client):
        """Test handling None in spaces field.

        The API might return {"spaces": null} instead of {"spaces": []}.
        This should be handled gracefully by returning an empty list.
        """
        mock_workspace_client.api_client.do.return_value = {"spaces": None}

        # Should handle None gracefully and return empty list
        spaces = client.list_spaces()
        assert spaces == []

    def test_list_spaces_non_dict_response(self, client, mock_workspace_client):
        """Test handling non-dict response."""
        # Some APIs might return a list directly
        mock_workspace_client.api_client.do.return_value = [{"id": "1", "title": "Space 1"}]

        spaces = client.list_spaces()
        assert len(spaces) == 1

    def test_get_space_returns_none(self, client, mock_workspace_client):
        """Test handling None response from get API."""
        mock_workspace_client.api_client.do.return_value = None

        space = client.get_space("some-id")
        assert space == {}

    def test_update_space_no_fields(self, client, mock_workspace_client):
        """Test update_space with no fields raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            client.update_space("space-id")

        assert "No fields to update" in str(exc_info.value)


# =============================================================================
# Bulk Operation Error Handling
# =============================================================================


class TestBulkOperationErrors:
    """Tests for error handling in bulk operations."""

    @pytest.fixture
    def mock_workspace_client(self):
        """Create a mock WorkspaceClient."""
        mock = MagicMock()
        mock.config.host = "https://test.databricks.com"
        return mock

    @pytest.fixture
    def client(self, mock_workspace_client):
        """Create a GenieClient with mocked workspace client."""
        return GenieClient(client=mock_workspace_client)

    def test_bulk_create_all_failures(self, client, mock_workspace_client):
        """Test bulk_create when all operations fail."""
        mock_workspace_client.api_client.do.side_effect = Exception("All fail")

        configs = [
            {"title": f"Space {i}", "warehouse_id": "wh", "tables": ["c.s.t"]} for i in range(3)
        ]

        result = client.bulk_create(configs, max_workers=2)

        assert isinstance(result, BulkResult)
        assert result.total == 3
        assert result.success == 0
        assert result.failed == 3
        # All results should have FAILED status
        assert all(r.status == "FAILED" for r in result.results)

    def test_bulk_create_mixed_success_failure(self, client, mock_workspace_client):
        """Test bulk_create with mixed success/failure."""
        call_count = 0

        def mock_api_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:  # Fail every other call
                raise Exception("Failed")
            return {"space": {"id": f"id-{call_count}"}}

        mock_workspace_client.api_client.do.side_effect = mock_api_call

        configs = [
            {"title": f"Space {i}", "warehouse_id": "wh", "tables": ["c.s.t"]} for i in range(4)
        ]

        result = client.bulk_create(configs, max_workers=1)

        assert result.total == 4
        assert result.success == 2
        assert result.failed == 2

    def test_bulk_delete_all_failures(self, client, mock_workspace_client):
        """Test bulk_delete when all operations fail."""
        mock_workspace_client.api_client.do.side_effect = Exception("Delete failed")

        space_ids = ["id1", "id2", "id3"]
        result = client.bulk_delete(space_ids, max_workers=2)

        assert result.total == 3
        assert result.success == 0
        assert result.failed == 3

    def test_bulk_delete_empty_list(self, client, mock_workspace_client):
        """Test bulk_delete with empty list."""
        result = client.bulk_delete([], max_workers=2)

        assert result.total == 0
        assert result.success == 0
        assert result.failed == 0

    def test_bulk_create_empty_list(self, client, mock_workspace_client):
        """Test bulk_create with empty list."""
        result = client.bulk_create([], max_workers=2)

        assert result.total == 0
        assert result.success == 0
        assert result.failed == 0


# =============================================================================
# Warehouse and Table Verification
# =============================================================================


class TestVerificationMethods:
    """Tests for warehouse and table verification methods."""

    @pytest.fixture
    def mock_workspace_client(self):
        """Create a mock WorkspaceClient."""
        mock = MagicMock()
        mock.config.host = "https://test.databricks.com"
        return mock

    @pytest.fixture
    def client(self, mock_workspace_client):
        """Create a GenieClient with mocked workspace client."""
        return GenieClient(client=mock_workspace_client)

    def test_verify_warehouse_exists(self, client, mock_workspace_client):
        """Test verifying an existing warehouse."""
        mock_warehouse = MagicMock()
        mock_warehouse.name = "My Warehouse"
        mock_warehouse.state = MagicMock(value="RUNNING")
        mock_workspace_client.warehouses.get.return_value = mock_warehouse

        result = client.verify_warehouse("wh-123")

        assert result["exists"] is True
        assert result["name"] == "My Warehouse"
        assert result["state"] == "RUNNING"

    def test_verify_warehouse_not_found(self, client, mock_workspace_client):
        """Test verifying a non-existent warehouse."""
        mock_workspace_client.warehouses.get.side_effect = Exception("Not found")

        result = client.verify_warehouse("nonexistent")

        assert result["exists"] is False
        assert "error" in result

    def test_verify_warehouse_no_state(self, client, mock_workspace_client):
        """Test verifying warehouse with no state."""
        mock_warehouse = MagicMock()
        mock_warehouse.name = "My Warehouse"
        mock_warehouse.state = None
        mock_workspace_client.warehouses.get.return_value = mock_warehouse

        result = client.verify_warehouse("wh-123")

        assert result["exists"] is True
        assert result["state"] == "UNKNOWN"

    def test_verify_table_exists(self, client, mock_workspace_client):
        """Test verifying an existing table."""
        mock_table = MagicMock()
        mock_table.table_type = MagicMock(value="MANAGED")
        mock_workspace_client.tables.get.return_value = mock_table

        result = client.verify_table("catalog.schema.table")

        assert result["exists"] is True
        assert result["table_type"] == "MANAGED"

    def test_verify_table_not_found(self, client, mock_workspace_client):
        """Test verifying a non-existent table."""
        mock_workspace_client.tables.get.side_effect = Exception("Table not found")

        result = client.verify_table("catalog.schema.nonexistent")

        assert result["exists"] is False
        assert "error" in result

    def test_verify_table_invalid_identifier(self, client, mock_workspace_client):
        """Test verifying table with invalid identifier format."""
        result = client.verify_table("invalid_format")

        assert result["exists"] is False
        assert "Invalid table identifier format" in result["error"]

    def test_verify_table_two_parts(self, client, mock_workspace_client):
        """Test verifying table with only two parts."""
        result = client.verify_table("schema.table")

        assert result["exists"] is False
        assert "Invalid table identifier format" in result["error"]


# =============================================================================
# Find Operations Edge Cases
# =============================================================================


class TestFindOperations:
    """Tests for find_spaces_by_name edge cases."""

    @pytest.fixture
    def mock_workspace_client(self):
        """Create a mock WorkspaceClient."""
        mock = MagicMock()
        mock.config.host = "https://test.databricks.com"
        return mock

    @pytest.fixture
    def client(self, mock_workspace_client):
        """Create a GenieClient with mocked workspace client."""
        return GenieClient(client=mock_workspace_client)

    def test_find_with_empty_pattern(self, client, mock_workspace_client):
        """Test find with empty pattern."""
        mock_workspace_client.api_client.do.return_value = {
            "spaces": [
                {"space_id": "1", "title": "Space 1"},
                {"space_id": "2", "title": "Space 2"},
            ]
        }

        # Empty string pattern matches nothing with fnmatch
        matches = client.find_spaces_by_name("")
        assert len(matches) == 0

    def test_find_with_star_pattern(self, client, mock_workspace_client):
        """Test find with * pattern (all)."""
        mock_workspace_client.api_client.do.return_value = {
            "spaces": [
                {"space_id": "1", "title": "Space 1"},
                {"space_id": "2", "title": "Space 2"},
            ]
        }

        matches = client.find_spaces_by_name("*")
        assert len(matches) == 2

    def test_find_case_sensitive(self, client, mock_workspace_client):
        """Test case-sensitive search."""
        mock_workspace_client.api_client.do.return_value = {
            "spaces": [
                {"space_id": "1", "title": "Sales Analytics"},
                {"space_id": "2", "title": "SALES Report"},
            ]
        }

        # Case sensitive - should only match first
        matches = client.find_spaces_by_name("Sales*", case_sensitive=True)
        assert len(matches) == 1
        assert matches[0]["title"] == "Sales Analytics"

    def test_find_space_with_missing_title(self, client, mock_workspace_client):
        """Test finding when some spaces have no title."""
        mock_workspace_client.api_client.do.return_value = {
            "spaces": [
                {"space_id": "1", "title": "Sales"},
                {"space_id": "2"},  # No title
            ]
        }

        # Should not crash on missing title
        matches = client.find_spaces_by_name("*")
        assert len(matches) == 2  # Should match empty string too with *

    def test_find_space_by_title_exact_match(self, client, mock_workspace_client):
        """Test exact title match."""
        mock_workspace_client.api_client.do.return_value = {
            "spaces": [
                {"space_id": "1", "title": "Sales Analytics"},
                {"space_id": "2", "title": "Sales Analytics Dashboard"},
            ]
        }

        space = client.find_space_by_title("Sales Analytics")
        assert space is not None
        assert space["space_id"] == "1"

    def test_find_space_by_title_not_substring(self, client, mock_workspace_client):
        """Test that exact match doesn't match substring."""
        mock_workspace_client.api_client.do.return_value = {
            "spaces": [
                {"space_id": "1", "title": "Sales Analytics Dashboard"},
            ]
        }

        space = client.find_space_by_title("Sales Analytics")
        assert space is None
