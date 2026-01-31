"""Unit tests for genie_forge.cli.common utilities."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest


class TestOperationCounter:
    """Tests for OperationCounter class."""

    def test_initial_values(self):
        """Test counter initializes with zeros."""
        from genie_forge.cli.common import OperationCounter

        counter = OperationCounter()
        assert counter.created == 0
        assert counter.updated == 0
        assert counter.deleted == 0
        assert counter.failed == 0
        assert counter.skipped == 0
        assert counter.unchanged == 0
        assert counter.total == 0

    def test_increment_counters(self):
        """Test incrementing counters."""
        from genie_forge.cli.common import OperationCounter

        counter = OperationCounter()
        counter.created = 5
        counter.updated = 3
        counter.failed = 1

        assert counter.total == 9
        assert counter.success_count == 8  # created + updated + deleted

    def test_add_detail(self):
        """Test adding operation details."""
        from genie_forge.cli.common import OperationCounter

        counter = OperationCounter()
        counter.add_detail("created", "space1", "Created successfully")
        counter.add_detail("failed", "space2", error="API error")

        assert len(counter.details) == 2
        assert counter.details[0]["operation"] == "created"
        assert counter.details[0]["item"] == "space1"
        assert counter.details[1]["error"] == "API error"

    def test_summary_format(self):
        """Test summary string formatting."""
        from genie_forge.cli.common import OperationCounter

        counter = OperationCounter()
        counter.created = 5
        counter.updated = 2
        counter.failed = 1

        summary = counter.summary()
        assert "5 created" in summary
        assert "2 updated" in summary
        assert "1 failed" in summary

    def test_summary_empty(self):
        """Test summary with no operations."""
        from genie_forge.cli.common import OperationCounter

        counter = OperationCounter()
        summary = counter.summary()
        assert summary == "No operations"


class TestTruncateString:
    """Tests for truncate_string function."""

    def test_no_truncation_needed(self):
        """Test string shorter than max length."""
        from genie_forge.cli.common import truncate_string

        result = truncate_string("hello", max_length=10)
        assert result == "hello"

    def test_truncation_with_default_suffix(self):
        """Test truncation with default ellipsis."""
        from genie_forge.cli.common import truncate_string

        result = truncate_string("this is a long string", max_length=10)
        assert len(result) == 10
        assert result.endswith("...")

    def test_truncation_with_custom_suffix(self):
        """Test truncation with custom suffix."""
        from genie_forge.cli.common import truncate_string

        result = truncate_string("this is long", max_length=8, suffix="~")
        assert len(result) == 8
        assert result.endswith("~")

    def test_exact_length(self):
        """Test string exactly at max length."""
        from genie_forge.cli.common import truncate_string

        result = truncate_string("exactly10!", max_length=10)
        assert result == "exactly10!"


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_simple_title(self):
        """Test simple title conversion."""
        from genie_forge.cli.common import sanitize_filename

        result = sanitize_filename("Sales Analytics")
        assert result == "sales_analytics"

    def test_special_characters(self):
        """Test title with special characters."""
        from genie_forge.cli.common import sanitize_filename

        result = sanitize_filename("HR - Employee Dashboard!")
        assert result == "hr_employee_dashboard"
        assert "!" not in result
        assert "-" not in result

    def test_max_length(self):
        """Test filename truncation."""
        from genie_forge.cli.common import sanitize_filename

        long_title = "This is a very long title that exceeds the maximum length"
        result = sanitize_filename(long_title, max_length=20)
        assert len(result) <= 20

    def test_unicode_characters(self):
        """Test title with unicode characters."""
        from genie_forge.cli.common import sanitize_filename

        result = sanitize_filename("Café Analytics")
        assert "_" in result or "caf" in result.lower()


class TestParseCommaSeparated:
    """Tests for parse_comma_separated function."""

    def test_simple_list(self):
        """Test simple comma-separated list."""
        from genie_forge.cli.common import parse_comma_separated

        result = parse_comma_separated("a,b,c")
        assert result == ["a", "b", "c"]

    def test_with_spaces(self):
        """Test list with spaces around values."""
        from genie_forge.cli.common import parse_comma_separated

        result = parse_comma_separated("  a , b , c  ")
        assert result == ["a", "b", "c"]

    def test_empty_values_filtered(self):
        """Test empty values are filtered out."""
        from genie_forge.cli.common import parse_comma_separated

        result = parse_comma_separated("a,,b, ,c")
        assert result == ["a", "b", "c"]

    def test_single_value(self):
        """Test single value without comma."""
        from genie_forge.cli.common import parse_comma_separated

        result = parse_comma_separated("single")
        assert result == ["single"]


class TestApplyKeyValueOverrides:
    """Tests for apply_key_value_overrides function."""

    def test_simple_override(self):
        """Test simple key=value override."""
        from genie_forge.cli.common import apply_key_value_overrides

        config = {"title": "Original"}
        result = apply_key_value_overrides(config, ["title=New Title"])
        assert result["title"] == "New Title"

    def test_nested_override(self):
        """Test nested key override with dot notation."""
        from genie_forge.cli.common import apply_key_value_overrides

        config = {"data_sources": {"tables": []}}
        result = apply_key_value_overrides(config, ["data_sources.description=New desc"])
        assert result["data_sources"]["description"] == "New desc"

    def test_create_nested_path(self):
        """Test creating nested path that doesn't exist."""
        from genie_forge.cli.common import apply_key_value_overrides

        config = {}
        result = apply_key_value_overrides(config, ["a.b.c=value"])
        assert result["a"]["b"]["c"] == "value"

    def test_multiple_overrides(self):
        """Test multiple overrides."""
        from genie_forge.cli.common import apply_key_value_overrides

        config = {}
        result = apply_key_value_overrides(config, ["title=Test", "warehouse_id=abc123"])
        assert result["title"] == "Test"
        assert result["warehouse_id"] == "abc123"

    def test_invalid_format_raises_error(self):
        """Test invalid format raises UsageError."""
        import click

        from genie_forge.cli.common import apply_key_value_overrides

        config = {}
        with pytest.raises(click.UsageError):
            apply_key_value_overrides(config, ["invalid_no_equals"])


class TestParseSerializedSpace:
    """Tests for parse_serialized_space function."""

    def test_dict_input(self):
        """Test with dict input (already parsed)."""
        from genie_forge.cli.common import parse_serialized_space

        space = {"serialized_space": {"tables": ["t1", "t2"]}}
        result = parse_serialized_space(space)
        assert result == {"tables": ["t1", "t2"]}

    def test_string_input(self):
        """Test with JSON string input."""
        from genie_forge.cli.common import parse_serialized_space

        space = {"serialized_space": '{"tables": ["t1"]}'}
        result = parse_serialized_space(space)
        assert result == {"tables": ["t1"]}

    def test_empty_serialized_space(self):
        """Test with empty or missing serialized_space."""
        from genie_forge.cli.common import parse_serialized_space

        assert parse_serialized_space({}) == {}
        assert parse_serialized_space({"serialized_space": None}) == {}
        assert parse_serialized_space({"serialized_space": ""}) == {}

    def test_invalid_json_string(self):
        """Test with invalid JSON string."""
        from genie_forge.cli.common import parse_serialized_space

        space = {"serialized_space": "not valid json"}
        result = parse_serialized_space(space)
        assert result == {}


class TestLoadStateFile:
    """Tests for load_state_file function."""

    def test_load_valid_state(self, tmp_path):
        """Test loading valid state file."""
        from genie_forge.cli.common import load_state_file

        state_data = {"version": "1.0", "environments": {"dev": {}}}
        state_file = tmp_path / ".genie-forge.json"
        state_file.write_text(json.dumps(state_data))

        result = load_state_file(state_file, exit_on_error=False)
        assert result == state_data

    def test_file_not_found_exit_on_error(self, tmp_path):
        """Test file not found with exit_on_error=True."""
        from genie_forge.cli.common import load_state_file

        # Should return None (not exit due to test environment)
        result = load_state_file(
            tmp_path / "nonexistent.json",
            exit_on_error=True,
            show_not_found_message=False,
        )
        assert result is None

    def test_file_not_found_raise_exception(self, tmp_path):
        """Test file not found with exit_on_error=False."""
        from genie_forge.cli.common import load_state_file

        with pytest.raises(FileNotFoundError):
            load_state_file(
                tmp_path / "nonexistent.json",
                exit_on_error=False,
                show_not_found_message=False,
            )

    def test_invalid_json(self, tmp_path):
        """Test loading invalid JSON."""
        from genie_forge.cli.common import load_state_file

        state_file = tmp_path / ".genie-forge.json"
        state_file.write_text("not valid json")

        with pytest.raises(json.JSONDecodeError):
            load_state_file(state_file, exit_on_error=False)


class TestSaveStateFile:
    """Tests for save_state_file function."""

    def test_save_state(self, tmp_path):
        """Test saving state file."""
        from genie_forge.cli.common import save_state_file

        state_data = {"version": "1.0", "environments": {}}
        state_file = tmp_path / ".genie-forge.json"

        result = save_state_file(state_data, state_file)
        assert result is True
        assert state_file.exists()

        # Verify content
        loaded = json.loads(state_file.read_text())
        assert loaded == state_data


class TestGetStateEnvironment:
    """Tests for get_state_environment function."""

    def test_existing_environment(self):
        """Test getting existing environment."""
        from genie_forge.cli.common import get_state_environment

        data = {"environments": {"dev": {"spaces": {}}, "prod": {"spaces": {}}}}
        result = get_state_environment(data, "dev", exit_on_error=False)
        assert result == {"spaces": {}}

    def test_missing_environment(self):
        """Test getting missing environment."""
        from genie_forge.cli.common import get_state_environment

        data = {"environments": {"dev": {}}}
        result = get_state_environment(data, "prod", exit_on_error=False)
        assert result is None


class TestLoadConfigFile:
    """Tests for load_config_file function."""

    def test_load_yaml(self, tmp_path):
        """Test loading YAML config."""
        from genie_forge.cli.common import load_config_file

        config_file = tmp_path / "config.yaml"
        config_file.write_text("title: Test\nwarehouse_id: abc123")

        result = load_config_file(config_file, exit_on_error=False)
        assert result["title"] == "Test"
        assert result["warehouse_id"] == "abc123"

    def test_load_json(self, tmp_path):
        """Test loading JSON config."""
        from genie_forge.cli.common import load_config_file

        config_file = tmp_path / "config.json"
        config_file.write_text('{"title": "Test", "warehouse_id": "abc123"}')

        result = load_config_file(config_file, exit_on_error=False)
        assert result["title"] == "Test"

    def test_unsupported_format(self, tmp_path):
        """Test unsupported file format."""
        import click

        from genie_forge.cli.common import load_config_file

        config_file = tmp_path / "config.txt"
        config_file.write_text("some content")

        with pytest.raises(click.UsageError):
            load_config_file(config_file, exit_on_error=False)


class TestSaveConfigFile:
    """Tests for save_config_file function."""

    def test_save_yaml(self, tmp_path):
        """Test saving YAML config."""
        from genie_forge.cli.common import save_config_file

        config = {"title": "Test", "warehouse_id": "abc123"}
        file_path = tmp_path / "output.yaml"

        save_config_file(config, file_path, file_format="yaml")

        assert file_path.exists()
        content = file_path.read_text()
        assert "title: Test" in content

    def test_save_json(self, tmp_path):
        """Test saving JSON config."""
        from genie_forge.cli.common import save_config_file

        config = {"title": "Test"}
        file_path = tmp_path / "output.json"

        save_config_file(config, file_path, file_format="json")

        assert file_path.exists()
        loaded = json.loads(file_path.read_text())
        assert loaded["title"] == "Test"

    def test_create_parent_directories(self, tmp_path):
        """Test creating parent directories."""
        from genie_forge.cli.common import save_config_file

        config = {"title": "Test"}
        file_path = tmp_path / "nested" / "dir" / "config.yaml"

        save_config_file(config, file_path, create_parents=True)
        assert file_path.exists()


class TestGetGenieClient:
    """Tests for get_genie_client function."""

    def test_get_client_success(self):
        """Test getting client successfully."""
        from genie_forge.cli.common import get_genie_client

        with patch("genie_forge.client.GenieClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            result = get_genie_client(profile="TEST", exit_on_error=False)
            assert result == mock_client
            mock_client_class.assert_called_once_with(profile="TEST")

    def test_get_client_auth_failure(self):
        """Test client authentication failure."""
        from genie_forge.cli.common import get_genie_client

        with patch("genie_forge.client.GenieClient") as mock_client_class:
            mock_client_class.side_effect = Exception("Auth failed")

            with pytest.raises(Exception, match="Auth failed"):
                get_genie_client(profile="TEST", exit_on_error=False)


class TestFetchAllSpacesPaginated:
    """Tests for fetch_all_spaces_paginated function."""

    def test_single_page(self):
        """Test fetching single page of results."""
        from genie_forge.cli.common import fetch_all_spaces_paginated

        mock_client = MagicMock()
        mock_client._api_get.return_value = {
            "spaces": [{"id": "1"}, {"id": "2"}],
            "next_page_token": None,
        }

        result = fetch_all_spaces_paginated(mock_client, show_progress=False)
        assert len(result) == 2
        assert result[0]["id"] == "1"

    def test_multiple_pages(self):
        """Test fetching multiple pages."""
        from genie_forge.cli.common import fetch_all_spaces_paginated

        mock_client = MagicMock()
        mock_client._api_get.side_effect = [
            {"spaces": [{"id": "1"}], "next_page_token": "token1"},
            {"spaces": [{"id": "2"}], "next_page_token": "token2"},
            {"spaces": [{"id": "3"}], "next_page_token": None},
        ]

        result = fetch_all_spaces_paginated(mock_client, show_progress=False)
        assert len(result) == 3

    def test_max_pages_limit(self):
        """Test max pages safety limit."""
        from genie_forge.cli.common import fetch_all_spaces_paginated

        mock_client = MagicMock()
        # Always return a next token
        mock_client._api_get.return_value = {
            "spaces": [{"id": "1"}],
            "next_page_token": "always_more",
        }

        result = fetch_all_spaces_paginated(mock_client, show_progress=False, max_pages=3)
        assert len(result) == 3  # Limited to 3 pages

    def test_callback_invoked(self):
        """Test callback is invoked for each page."""
        from genie_forge.cli.common import fetch_all_spaces_paginated

        mock_client = MagicMock()
        mock_client._api_get.side_effect = [
            {"spaces": [{"id": "1"}], "next_page_token": "token1"},
            {"spaces": [{"id": "2"}], "next_page_token": None},
        ]

        callback_calls = []

        def callback(page_num, spaces):
            callback_calls.append((page_num, spaces))

        fetch_all_spaces_paginated(mock_client, show_progress=False, on_page_fetched=callback)

        assert len(callback_calls) == 2
        assert callback_calls[0][0] == 1
        assert callback_calls[1][0] == 2
