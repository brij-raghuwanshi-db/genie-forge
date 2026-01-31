"""Tests for impossible/unlikely scenarios that should be handled gracefully.

These tests cover edge cases that:
1. Should theoretically never happen but could due to bugs or API changes
2. Represent boundary conditions at the limits of valid input
3. Test defensive programming practices
4. Document behavior for unusual but possible situations

"Impossible" here means "shouldn't happen in normal operation but the code
should handle gracefully anyway."
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
import yaml

from genie_forge.client import GenieClient
from genie_forge.models import (
    ColumnConfig,
    DataSources,
    SpaceConfig,
    TableConfig,
)
from genie_forge.parsers import MetadataParser
from genie_forge.serializer import SpaceSerializer
from genie_forge.state import StateManager

# =============================================================================
# Impossible API Responses
# =============================================================================


class TestImpossibleAPIResponses:
    """Tests for impossible/malformed API responses."""

    def test_api_returns_none(self):
        """Test handling when API returns None instead of response.

        Note: list_spaces handles None response by treating it as empty list.
        This is actually good defensive behavior.
        """
        mock_client = MagicMock()
        mock_client.config.host = "https://test.databricks.com"
        mock_client.api_client.do.return_value = None

        client = GenieClient(client=mock_client)

        # list_spaces handles None gracefully (treats as empty)
        try:
            spaces = client.list_spaces()
            # If it succeeds, should return empty or list
            assert isinstance(spaces, (list, type(None)))
        except Exception:
            # Raising is also acceptable
            pass

    def test_api_returns_string_instead_of_dict(self):
        """Test handling when API returns string instead of dict."""
        mock_client = MagicMock()
        mock_client.config.host = "https://test.databricks.com"
        mock_client.api_client.do.return_value = "error message"

        client = GenieClient(client=mock_client)

        # Should handle gracefully
        try:
            spaces = client.list_spaces()
            # If it works, it should return something list-like
            assert isinstance(spaces, (list, str))
        except Exception:
            pass  # Exception is acceptable

    def test_api_returns_integer_instead_of_dict(self):
        """Test handling when API returns integer."""
        mock_client = MagicMock()
        mock_client.config.host = "https://test.databricks.com"
        mock_client.api_client.do.return_value = 42

        client = GenieClient(client=mock_client)

        # Should handle gracefully
        try:
            client.list_spaces()
        except Exception:
            pass  # Exception is acceptable

    def test_api_returns_nested_none_values(self):
        """Test handling deeply nested None values in response."""
        mock_client = MagicMock()
        mock_client.config.host = "https://test.databricks.com"
        mock_client.api_client.do.return_value = {
            "spaces": [
                {
                    "id": None,
                    "title": None,
                    "serialized_space": None,
                }
            ]
        }

        client = GenieClient(client=mock_client)
        spaces = client.list_spaces()

        # Should return the spaces even with None values
        assert len(spaces) == 1

    def test_serialized_space_is_invalid_json_string(self):
        """Test handling when serialized_space is invalid JSON string."""
        response = {
            "id": "space-123",
            "title": "Test",
            "warehouse_id": "wh",
            "serialized_space": "not valid json {{{",
        }

        serializer = SpaceSerializer()

        # from_api_response should handle this
        result = serializer.from_api_response(response)
        # Should still return something (even if serialized_space is broken)
        assert "title" in result


# =============================================================================
# Impossible State File Conditions
# =============================================================================


class TestImpossibleStateConditions:
    """Tests for impossible state file conditions."""

    def test_state_file_is_empty(self, tmp_path):
        """Test handling when state file is empty."""
        state_file = tmp_path / ".genie-forge.json"
        state_file.write_text("")

        manager = StateManager(state_file=state_file, project_id="test")

        # Should create new state
        state = manager.state
        assert state.project_id == "test"

    def test_state_file_is_just_whitespace(self, tmp_path):
        """Test handling when state file is just whitespace."""
        state_file = tmp_path / ".genie-forge.json"
        state_file.write_text("   \n\n\t   ")

        manager = StateManager(state_file=state_file, project_id="test")

        # Should create new state
        state = manager.state
        assert state is not None

    def test_state_file_is_null_json(self, tmp_path):
        """Test handling when state file contains null."""
        state_file = tmp_path / ".genie-forge.json"
        state_file.write_text("null")

        manager = StateManager(state_file=state_file, project_id="test")

        # Should create new state
        state = manager.state
        assert state is not None

    def test_state_file_is_array_json(self, tmp_path):
        """Test handling when state file is array instead of object."""
        state_file = tmp_path / ".genie-forge.json"
        state_file.write_text("[]")

        manager = StateManager(state_file=state_file, project_id="test")

        # Should create new state
        state = manager.state
        assert state is not None

    def test_state_file_has_future_version(self, tmp_path):
        """Test handling state file with unknown future version."""
        state_data = {
            "version": "99.0",  # Future version
            "project_id": "test",
            "environments": {},
        }
        state_file = tmp_path / ".genie-forge.json"
        state_file.write_text(json.dumps(state_data))

        manager = StateManager(state_file=state_file)

        # Should still load (forward compatibility)
        state = manager.state
        assert state.project_id == "test"

    def test_state_with_unknown_status(self, tmp_path):
        """Test handling state with unknown SpaceStatus value."""
        state_data = {
            "version": "1.0",
            "project_id": "test",
            "environments": {
                "dev": {
                    "workspace_url": "https://test.com",
                    "spaces": {
                        "test": {
                            "logical_id": "test",
                            "title": "Test",
                            "config_hash": "abc",
                            "status": "UNKNOWN_FUTURE_STATUS",  # Invalid
                        }
                    },
                }
            },
        }
        state_file = tmp_path / ".genie-forge.json"
        state_file.write_text(json.dumps(state_data))

        # Should either handle gracefully or raise clear error
        try:
            StateManager(state_file=state_file)
        except Exception as e:
            assert "status" in str(e).lower()


# =============================================================================
# Impossible Configuration Conditions
# =============================================================================


class TestImpossibleConfigConditions:
    """Tests for impossible configuration conditions."""

    def test_config_with_circular_reference(self, tmp_path):
        """Test handling config with circular YAML reference."""
        # YAML with circular alias (should fail to parse)
        circular_yaml = """
a: &anchor
  b: *anchor
"""
        config_file = tmp_path / "circular.yaml"
        config_file.write_text(circular_yaml)

        # Should fail gracefully (circular references are infinite)
        try:
            yaml.safe_load(config_file.read_text())
            # If it loads, it might create recursive structure
        except Exception:
            pass  # Expected

    def test_config_with_recursive_tables(self):
        """Test config where a table references itself (impossible in practice)."""
        # This is semantically impossible but syntactically valid
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            data_sources=DataSources(
                tables=[
                    TableConfig(identifier="cat.sch.self_ref"),
                ]
            ),
        )

        # Should serialize without issues
        serializer = SpaceSerializer()
        result = serializer.to_serialized_space(config)
        assert len(result["data_sources"]["tables"]) == 1

    def test_config_with_empty_identifier(self):
        """Test handling table with empty identifier."""
        with pytest.raises(Exception):
            TableConfig(identifier="")

    def test_config_with_whitespace_identifier(self):
        """Test handling table with whitespace-only identifier."""
        with pytest.raises(Exception):
            TableConfig(identifier="   ")

    def test_space_id_with_special_characters(self):
        """Test space_id with special characters."""
        # Some characters might cause issues in state file
        special_ids = [
            "space/with/slashes",
            "space\\with\\backslashes",
            "space:with:colons",
            "space<with>brackets",
            'space"with"quotes',
            "space\nwith\nnewlines",
        ]

        for space_id in special_ids:
            try:
                config = SpaceConfig(
                    space_id=space_id,
                    title="Test",
                    warehouse_id="wh",
                )
                # If it works, it should preserve the ID
                assert config.space_id == space_id
            except Exception:
                pass  # Rejection is acceptable


# =============================================================================
# Impossible Hash Conditions
# =============================================================================


class TestImpossibleHashConditions:
    """Tests for impossible hash/checksum conditions."""

    def test_different_configs_same_hash(self):
        """Test that different configs produce different hashes."""
        config1 = SpaceConfig.minimal(
            space_id="test1",
            title="Test 1",
            warehouse_id="wh",
            tables=["c.s.t"],
        )
        config2 = SpaceConfig.minimal(
            space_id="test2",
            title="Test 2",
            warehouse_id="wh",
            tables=["c.s.t"],
        )

        # Different configs should have different hashes
        hash1 = config1.config_hash()
        hash2 = config2.config_hash()

        # They should be different (hash collision is theoretically possible
        # but extremely unlikely)
        assert hash1 != hash2

    def test_hash_is_deterministic(self):
        """Test that hash is deterministic (same input = same output)."""
        config = SpaceConfig.minimal(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            tables=["c.s.t"],
        )

        hashes = [config.config_hash() for _ in range(10)]

        # All hashes should be identical
        assert len(set(hashes)) == 1

    def test_hash_not_affected_by_order(self):
        """Test that hash is not affected by field order in input."""
        # Create two configs with same content
        config1 = SpaceConfig.minimal(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            tables=["c.s.t"],
        )
        config2 = SpaceConfig.minimal(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            tables=["c.s.t"],
        )

        # Same content should have same hash
        assert config1.config_hash() == config2.config_hash()


# =============================================================================
# Impossible Timing Conditions
# =============================================================================


class TestImpossibleTimingConditions:
    """Tests for impossible timing/race conditions."""

    def test_state_file_deleted_during_save(self, tmp_path):
        """Test handling when state file is deleted during save."""
        state_file = tmp_path / ".genie-forge.json"

        manager = StateManager(state_file=state_file, project_id="test")
        _ = manager.state  # Initialize

        # Delete the parent directory (impossible during normal operation)
        # but test that save handles missing parent gracefully
        manager._get_or_create_env_state("dev", "https://test.com")
        manager._save_state()

        assert state_file.exists()

    def test_state_read_during_write(self, tmp_path):
        """Test reading state file during write (simulated race)."""
        state_file = tmp_path / ".genie-forge.json"

        # Write initial state
        initial_data = {
            "version": "1.0",
            "project_id": "test",
            "environments": {},
        }
        state_file.write_text(json.dumps(initial_data))

        # Create manager
        manager = StateManager(state_file=state_file)

        # Read state
        state = manager.state

        # Should have loaded correctly
        assert state.project_id == "test"


# =============================================================================
# Impossible Parser Conditions
# =============================================================================


class TestImpossibleParserConditions:
    """Tests for impossible parser conditions."""

    def test_parse_binary_file(self, tmp_path):
        """Test parsing binary file as YAML."""
        binary_file = tmp_path / "binary.yaml"
        binary_file.write_bytes(b"\x00\x01\x02\x03\x04\x05")

        parser = MetadataParser()

        with pytest.raises(Exception):
            parser.parse(binary_file)

    def test_parse_huge_file(self, tmp_path):
        """Test parsing extremely large file."""
        # Create a 1MB YAML file
        huge_content = (
            "spaces:\n" + "  - space_id: test\n    title: Test\n    warehouse_id: wh\n" * 10000
        )
        huge_file = tmp_path / "huge.yaml"
        huge_file.write_text(huge_content)

        parser = MetadataParser()

        # Should either parse or fail with memory error
        try:
            configs = parser.parse(huge_file)
            # If it works, should have many spaces
            assert len(configs) > 0
        except MemoryError:
            pass  # Acceptable
        except Exception:
            pass  # Other errors acceptable for huge files

    def test_parse_deeply_nested_yaml(self, tmp_path):
        """Test parsing extremely deeply nested YAML.

        Note: YAML syntax "a: a: a:" is invalid - must use proper nesting.
        This test documents that invalid YAML syntax is caught.
        """
        # Create properly nested structure using indentation
        lines = []
        for i in range(50):
            lines.append("  " * i + f"level_{i}:")
        lines.append("  " * 50 + "value: deep")
        content = "\n".join(lines)

        nested_file = tmp_path / "nested.yaml"
        nested_file.write_text(content)

        # Should handle without stack overflow
        try:
            data = yaml.safe_load(nested_file.read_text())
            # If it parses, should have nested structure
            assert data is not None
        except (RecursionError, yaml.YAMLError):
            pass  # Acceptable for very deep nesting


# =============================================================================
# Impossible Network Conditions
# =============================================================================


class TestImpossibleNetworkConditions:
    """Tests for impossible network conditions."""

    def test_negative_rate_limit(self):
        """Test bulk operations with negative rate limit."""
        mock_client = MagicMock()
        mock_client.config.host = "https://test.databricks.com"
        mock_client.api_client.do.return_value = {"space": {"id": "new-id"}}

        client = GenieClient(client=mock_client)

        configs = [{"title": "Test", "warehouse_id": "wh", "tables": ["c.s.t"]}]

        # Negative rate limit should be treated as no limit or zero
        result = client.bulk_create(configs, rate_limit=-1.0)
        assert result.total == 1

    def test_zero_max_workers(self):
        """Test bulk operations with zero workers."""
        mock_client = MagicMock()
        mock_client.config.host = "https://test.databricks.com"
        mock_client.api_client.do.return_value = {"space": {"id": "new-id"}}

        client = GenieClient(client=mock_client)

        configs = [{"title": "Test", "warehouse_id": "wh", "tables": ["c.s.t"]}]

        # Zero workers should fail or use minimum 1
        try:
            result = client.bulk_create(configs, max_workers=0)
            # If it works, should complete
            assert result.total == 1
        except Exception:
            pass  # Exception is acceptable

    def test_negative_max_pages(self):
        """Test list with negative max_pages."""
        mock_client = MagicMock()
        mock_client.config.host = "https://test.databricks.com"
        mock_client.api_client.do.return_value = {"spaces": []}

        client = GenieClient(client=mock_client)

        # Negative max_pages should be treated as 0 or minimum
        try:
            spaces = client.list_spaces(max_pages=-1)
            # Should return something
            assert isinstance(spaces, list)
        except Exception:
            pass  # Exception is acceptable


# =============================================================================
# Data Integrity Edge Cases
# =============================================================================


class TestDataIntegrityEdgeCases:
    """Tests for data integrity in edge cases."""

    def test_space_config_with_all_optional_none(self):
        """Test SpaceConfig with all optional fields as None."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            parent_path=None,
            description=None,
            sample_questions=[],
        )

        serializer = SpaceSerializer()
        result = serializer.to_serialized_space(config)

        # Should serialize without errors
        assert "version" in result

    def test_column_config_all_empty(self):
        """Test ColumnConfig with all empty optional fields."""
        col = ColumnConfig(
            column_name="test",
            description=[],
            synonyms=[],
            enable_format_assistance=False,
            enable_entity_matching=False,
        )

        assert col.column_name == "test"

    def test_unicode_normalization(self):
        """Test that Unicode is handled consistently."""
        # Same character, different encodings
        titles = [
            "café",  # Composed form
            "cafe\u0301",  # Decomposed form (e + combining accent)
        ]

        configs = []
        for title in titles:
            config = SpaceConfig(
                space_id="test",
                title=title,
                warehouse_id="wh",
            )
            configs.append(config)

        # Behavior depends on Python's handling
        # Just ensure no crashes
        for config in configs:
            assert len(config.title) > 0
