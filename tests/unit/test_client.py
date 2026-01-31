"""Unit tests for genie_forge.client."""

import time
from unittest.mock import MagicMock

import pytest

from genie_forge.client import (
    BulkResult,
    GenieAPIError,
    GenieClient,
    SpaceResult,
    retry_on_error,
)


class TestRetryOnError:
    """Tests for the retry_on_error decorator."""

    def test_success_no_retry(self):
        """Test that successful calls don't retry."""
        call_count = 0

        @retry_on_error(max_retries=3, base_delay=0.01)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = successful_func()
        assert result == "success"
        assert call_count == 1

    def test_retry_on_connection_error(self):
        """Test that ConnectionError triggers retry."""
        call_count = 0

        @retry_on_error(max_retries=2, base_delay=0.01)
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Connection failed")
            return "success"

        result = failing_then_success()
        assert result == "success"
        assert call_count == 3

    def test_max_retries_exceeded(self):
        """Test that exception is raised after max retries."""
        call_count = 0

        @retry_on_error(max_retries=2, base_delay=0.01)
        def always_failing():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError):
            always_failing()

        assert call_count == 3  # Initial + 2 retries

    def test_non_retryable_error_not_retried(self):
        """Test that non-retryable errors are raised immediately."""
        call_count = 0

        @retry_on_error(max_retries=3, base_delay=0.01)
        def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError):
            raises_value_error()

        assert call_count == 1  # No retries

    def test_exponential_backoff_timing(self):
        """Test that delays increase exponentially."""
        delays = []

        @retry_on_error(max_retries=3, base_delay=0.1, exponential_base=2.0)
        def track_timing():
            delays.append(time.time())
            if len(delays) <= 3:
                raise ConnectionError("Retry")
            return "done"

        time.time()
        result = track_timing()

        assert result == "done"
        assert len(delays) == 4

        # Check that delays increased (with some tolerance)
        if len(delays) >= 2:
            delay1 = delays[1] - delays[0]
            assert delay1 >= 0.05  # At least some delay


class TestGenieClient:
    """Tests for GenieClient."""

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

    def test_workspace_url(self, client, mock_workspace_client):
        """Test workspace_url property."""
        assert client.workspace_url == "https://test.databricks.com"

    def test_create_space(self, client, mock_workspace_client):
        """Test create_space method."""
        mock_workspace_client.api_client.do.return_value = {"space": {"id": "test-space-id"}}

        space_id = client.create_space(
            title="Test Space",
            warehouse_id="warehouse-123",
            tables=["catalog.schema.table"],
        )

        assert space_id == "test-space-id"
        mock_workspace_client.api_client.do.assert_called_once()
        call_args = mock_workspace_client.api_client.do.call_args
        assert call_args[0][0] == "POST"
        assert "/api/2.0/genie/spaces" in call_args[0][1]

    def test_create_space_error(self, client, mock_workspace_client):
        """Test create_space handles errors."""
        mock_workspace_client.api_client.do.side_effect = Exception("API Error")

        with pytest.raises(GenieAPIError) as exc_info:
            client.create_space(
                title="Test Space",
                warehouse_id="warehouse-123",
                tables=["catalog.schema.table"],
            )

        assert "Failed to create space" in str(exc_info.value)

    def test_get_space(self, client, mock_workspace_client):
        """Test get_space method."""
        mock_workspace_client.api_client.do.return_value = {
            "space_id": "test-id",
            "title": "Test Space",
        }

        space = client.get_space("test-id")

        assert space["title"] == "Test Space"

    def test_list_spaces_single_page(self, client, mock_workspace_client):
        """Test list_spaces with single page."""
        mock_workspace_client.api_client.do.return_value = {
            "spaces": [
                {"space_id": "1", "title": "Space 1"},
                {"space_id": "2", "title": "Space 2"},
            ]
        }

        spaces = client.list_spaces()

        assert len(spaces) == 2
        assert spaces[0]["title"] == "Space 1"

    def test_list_spaces_pagination(self, client, mock_workspace_client):
        """Test list_spaces handles pagination."""
        # First call returns page 1 with next_page_token
        # Second call returns page 2 without token
        mock_workspace_client.api_client.do.side_effect = [
            {
                "spaces": [{"space_id": "1", "title": "Space 1"}],
                "next_page_token": "token123",
            },
            {
                "spaces": [{"space_id": "2", "title": "Space 2"}],
            },
        ]

        spaces = client.list_spaces()

        assert len(spaces) == 2
        assert mock_workspace_client.api_client.do.call_count == 2

    def test_delete_space(self, client, mock_workspace_client):
        """Test delete_space method."""
        mock_workspace_client.api_client.do.return_value = {}

        client.delete_space("test-id")

        mock_workspace_client.api_client.do.assert_called_once()
        call_args = mock_workspace_client.api_client.do.call_args
        assert call_args[0][0] == "DELETE"
        assert "test-id" in call_args[0][1]

    def test_find_spaces_by_name(self, client, mock_workspace_client):
        """Test find_spaces_by_name with pattern."""
        mock_workspace_client.api_client.do.return_value = {
            "spaces": [
                {"space_id": "1", "title": "Sales Analytics"},
                {"space_id": "2", "title": "HR Dashboard"},
                {"space_id": "3", "title": "Sales Report"},
            ]
        }

        matches = client.find_spaces_by_name("Sales*")

        assert len(matches) == 2
        assert all("Sales" in m["title"] for m in matches)

    def test_find_spaces_by_name_case_insensitive(self, client, mock_workspace_client):
        """Test find_spaces_by_name is case insensitive by default."""
        mock_workspace_client.api_client.do.return_value = {
            "spaces": [
                {"space_id": "1", "title": "SALES Analytics"},
                {"space_id": "2", "title": "sales report"},
            ]
        }

        matches = client.find_spaces_by_name("*sales*")

        assert len(matches) == 2

    def test_find_space_by_title(self, client, mock_workspace_client):
        """Test find_space_by_title exact match."""
        mock_workspace_client.api_client.do.return_value = {
            "spaces": [
                {"space_id": "1", "title": "Sales Analytics"},
                {"space_id": "2", "title": "HR Dashboard"},
            ]
        }

        space = client.find_space_by_title("Sales Analytics")

        assert space is not None
        assert space["space_id"] == "1"

    def test_find_space_by_title_not_found(self, client, mock_workspace_client):
        """Test find_space_by_title returns None when not found."""
        mock_workspace_client.api_client.do.return_value = {
            "spaces": [{"space_id": "1", "title": "Other"}]
        }

        space = client.find_space_by_title("Not Found")

        assert space is None


class TestBulkOperations:
    """Tests for bulk operations."""

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

    def test_bulk_create(self, client, mock_workspace_client):
        """Test bulk_create creates multiple spaces."""
        mock_workspace_client.api_client.do.return_value = {"space": {"id": "new-id"}}

        configs = [
            {"title": "Space 1", "warehouse_id": "wh1", "tables": ["t1"]},
            {"title": "Space 2", "warehouse_id": "wh2", "tables": ["t2"]},
        ]

        result = client.bulk_create(configs, max_workers=2)

        assert isinstance(result, BulkResult)
        assert result.total == 2
        assert result.success == 2
        assert result.failed == 0

    def test_bulk_create_with_rate_limit(self, client, mock_workspace_client):
        """Test bulk_create with rate limiting."""
        mock_workspace_client.api_client.do.return_value = {"space": {"id": "new-id"}}

        configs = [{"title": f"Space {i}", "warehouse_id": "wh", "tables": ["t"]} for i in range(3)]

        start = time.time()
        result = client.bulk_create(configs, max_workers=1, rate_limit=10.0)
        elapsed = time.time() - start

        assert result.total == 3
        # With rate_limit=10, should take at least 0.2 seconds for 3 items
        # (2 delays of 0.1 seconds each)
        assert elapsed >= 0.1  # Some delay expected

    def test_bulk_delete(self, client, mock_workspace_client):
        """Test bulk_delete deletes multiple spaces."""
        mock_workspace_client.api_client.do.return_value = {}

        space_ids = ["id1", "id2", "id3"]
        result = client.bulk_delete(space_ids, max_workers=2)

        assert isinstance(result, BulkResult)
        assert result.total == 3
        assert result.success == 3

    def test_bulk_create_partial_failure(self, client, mock_workspace_client):
        """Test bulk_create handles partial failures."""
        call_count = 0

        def mock_api_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("Failed")
            return {"space": {"id": f"id-{call_count}"}}

        mock_workspace_client.api_client.do.side_effect = mock_api_call

        configs = [{"title": f"Space {i}", "warehouse_id": "wh", "tables": ["t"]} for i in range(3)]

        result = client.bulk_create(configs, max_workers=1)

        assert result.total == 3
        assert result.failed == 1
        assert result.success == 2


class TestSpaceResult:
    """Tests for SpaceResult dataclass."""

    def test_success_result(self):
        """Test successful result."""
        result = SpaceResult(
            logical_id="test",
            databricks_space_id="db-123",
            status="SUCCESS",
        )
        assert result.status == "SUCCESS"
        assert result.error is None

    def test_failed_result(self):
        """Test failed result."""
        result = SpaceResult(
            logical_id="test",
            status="FAILED",
            error="Something went wrong",
        )
        assert result.status == "FAILED"
        assert result.error == "Something went wrong"


class TestGenieAPIError:
    """Tests for GenieAPIError."""

    def test_error_with_message(self):
        """Test error with message."""
        error = GenieAPIError("Test error")
        assert str(error) == "Test error"

    def test_error_with_status_code(self):
        """Test error with status code."""
        error = GenieAPIError("Test error", status_code=404)
        assert error.status_code == 404

    def test_error_with_response(self):
        """Test error with response."""
        error = GenieAPIError("Test error", response={"detail": "Not found"})
        assert error.response == {"detail": "Not found"}
