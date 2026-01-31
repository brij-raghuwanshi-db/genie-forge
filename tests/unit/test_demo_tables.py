"""Unit tests for genie_forge.demo_tables."""

from unittest.mock import MagicMock

import pytest

from genie_forge.demo_tables import (
    DEMO_FUNCTIONS_INFO,
    DEMO_TABLES_INFO,
    check_demo_objects_exist,
    cleanup_demo_tables,
    create_demo_tables,
    get_demo_objects_summary,
)


class TestDemoTablesInfo:
    """Tests for demo table metadata."""

    def test_demo_tables_info_structure(self):
        """Test that DEMO_TABLES_INFO has required fields."""
        assert isinstance(DEMO_TABLES_INFO, dict)
        assert len(DEMO_TABLES_INFO) == 6  # 6 demo tables

        for table_name, info in DEMO_TABLES_INFO.items():
            assert "rows" in info
            assert "description" in info
            assert isinstance(info["rows"], int)
            assert isinstance(info["description"], str)

    def test_demo_tables_names(self):
        """Test expected table names exist."""
        expected_tables = [
            "locations",
            "departments",
            "employees",
            "customers",
            "products",
            "sales",
        ]
        for table in expected_tables:
            assert table in DEMO_TABLES_INFO

    def test_demo_functions_info_structure(self):
        """Test that DEMO_FUNCTIONS_INFO has required fields."""
        assert isinstance(DEMO_FUNCTIONS_INFO, dict)
        assert len(DEMO_FUNCTIONS_INFO) == 2  # 2 demo functions

        for func_name, info in DEMO_FUNCTIONS_INFO.items():
            assert "description" in info
            assert isinstance(info["description"], str)

    def test_demo_functions_names(self):
        """Test expected function names exist."""
        expected_functions = [
            "calculate_tenure_years",
            "percent_change",
        ]
        for func in expected_functions:
            assert func in DEMO_FUNCTIONS_INFO

    def test_total_rows(self):
        """Test total row count across all tables."""
        total = sum(info["rows"] for info in DEMO_TABLES_INFO.values())
        assert total == 96  # 8 + 8 + 30 + 10 + 10 + 30


class TestGetDemoObjectsSummary:
    """Tests for get_demo_objects_summary function."""

    def test_summary_structure(self):
        """Test the structure of the summary."""
        summary = get_demo_objects_summary("my_catalog", "my_schema")

        assert "tables" in summary
        assert "functions" in summary
        assert "total_count" in summary

    def test_summary_table_names(self):
        """Test that full table names are correct."""
        summary = get_demo_objects_summary("cat", "sch")

        for table in summary["tables"]:
            assert table["full_name"].startswith("cat.sch.")
            assert "drop_sql" in table
            assert "DROP TABLE IF EXISTS" in table["drop_sql"]

    def test_summary_function_names(self):
        """Test that full function names are correct."""
        summary = get_demo_objects_summary("cat", "sch")

        for func in summary["functions"]:
            assert func["full_name"].startswith("cat.sch.")
            assert "drop_sql" in func
            assert "DROP FUNCTION IF EXISTS" in func["drop_sql"]

    def test_summary_total_count(self):
        """Test total count is correct."""
        summary = get_demo_objects_summary("cat", "sch")

        expected_count = len(DEMO_TABLES_INFO) + len(DEMO_FUNCTIONS_INFO)
        assert summary["total_count"] == expected_count


class TestCheckDemoObjectsExist:
    """Tests for check_demo_objects_exist function."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock GenieClient."""
        mock = MagicMock()
        mock.client = MagicMock()
        return mock

    def test_all_objects_exist(self, mock_client):
        """Test when all objects exist."""
        # Mock the statement execution to return results
        mock_response = MagicMock()
        mock_response.status.state.value = "SUCCEEDED"
        mock_response.result.data_array = [["some_data"]]
        mock_client.client.statement_execution.execute_statement.return_value = mock_response

        result = check_demo_objects_exist(mock_client, "cat", "sch", "warehouse-id")

        assert "existing_tables" in result
        assert "missing_tables" in result
        assert "existing_functions" in result
        assert "missing_functions" in result
        assert "total_existing" in result
        assert "total_missing" in result

    def test_no_objects_exist(self, mock_client):
        """Test when no objects exist."""
        # Mock the statement execution to return empty results
        mock_response = MagicMock()
        mock_response.status.state.value = "SUCCEEDED"
        mock_response.result.data_array = []
        mock_client.client.statement_execution.execute_statement.return_value = mock_response

        result = check_demo_objects_exist(mock_client, "cat", "sch", "warehouse-id")

        assert result["total_existing"] == 0
        assert result["total_missing"] == len(DEMO_TABLES_INFO) + len(DEMO_FUNCTIONS_INFO)


class TestCleanupDemoTables:
    """Tests for cleanup_demo_tables function."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock GenieClient."""
        mock = MagicMock()
        mock.client = MagicMock()
        return mock

    def test_cleanup_already_clean(self, mock_client):
        """Test cleanup when objects don't exist."""
        # Mock check_demo_objects_exist to return no existing objects
        mock_response = MagicMock()
        mock_response.status.state.value = "SUCCEEDED"
        mock_response.result.data_array = []
        mock_client.client.statement_execution.execute_statement.return_value = mock_response

        result = cleanup_demo_tables(mock_client, "cat", "sch", "warehouse-id")

        assert result["already_clean"] is True
        assert result["success"] is True

    def test_cleanup_success(self, mock_client):
        """Test successful cleanup."""
        call_count = 0

        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            mock_response.status.state.value = "SUCCEEDED"
            # First calls are for checking existence
            if call_count <= len(DEMO_TABLES_INFO) + len(DEMO_FUNCTIONS_INFO):
                mock_response.result.data_array = [["exists"]]
            else:
                mock_response.result.data_array = []
            return mock_response

        mock_client.client.statement_execution.execute_statement.side_effect = mock_execute

        result = cleanup_demo_tables(mock_client, "cat", "sch", "warehouse-id")

        assert result["success"] is True
        assert result["deleted_count"] > 0

    def test_cleanup_skip_existence_check(self, mock_client):
        """Test cleanup with skip_existence_check."""
        mock_response = MagicMock()
        mock_response.status.state.value = "SUCCEEDED"
        mock_client.client.statement_execution.execute_statement.return_value = mock_response

        result = cleanup_demo_tables(
            mock_client,
            "cat",
            "sch",
            "warehouse-id",
            skip_existence_check=True,
        )

        # Should still succeed even without checking
        assert result["success"] is True


class TestCreateDemoTables:
    """Tests for create_demo_tables function."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock GenieClient."""
        mock = MagicMock()
        mock.client = MagicMock()
        return mock

    def test_create_success(self, mock_client):
        """Test successful table creation."""
        mock_response = MagicMock()
        mock_response.status.state.value = "SUCCEEDED"
        mock_client.client.statement_execution.execute_statement.return_value = mock_response

        result = create_demo_tables(mock_client, "cat", "sch", "warehouse-id")

        assert result["success"] is True
        assert result["tables_created"] == 6
        assert result["total_rows"] == 96  # Sum of all rows

    def test_create_with_failure(self, mock_client):
        """Test table creation with one failure."""
        call_count = 0

        def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            # Fail on the 3rd call
            if call_count == 3:
                mock_response.status.state.value = "FAILED"
                mock_response.status.error = MagicMock()
                mock_response.status.error.message = "Table creation failed"
            else:
                mock_response.status.state.value = "SUCCEEDED"
            return mock_response

        mock_client.client.statement_execution.execute_statement.side_effect = mock_execute

        result = create_demo_tables(mock_client, "cat", "sch", "warehouse-id")

        # Should still complete but with failure flag
        assert "tables" in result
