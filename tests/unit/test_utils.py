"""Tests for genie_forge.utils module."""

import os
from pathlib import Path
from unittest.mock import patch

from genie_forge.utils import (
    ProjectPaths,
    ensure_directory,
    get_databricks_runtime_version,
    get_default_project_path,
    get_volume_path,
    is_running_in_notebook,
    is_running_on_databricks,
    is_volume_path,
    parse_volume_path,
    sanitize_name,
)

# =============================================================================
# Environment Detection Tests
# =============================================================================


class TestIsRunningOnDatabricks:
    """Tests for is_running_on_databricks function."""

    def test_returns_false_when_not_on_databricks(self):
        """Should return False when DATABRICKS_RUNTIME_VERSION is not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure the env var is not present
            os.environ.pop("DATABRICKS_RUNTIME_VERSION", None)
            assert is_running_on_databricks() is False

    def test_returns_true_when_on_databricks(self):
        """Should return True when DATABRICKS_RUNTIME_VERSION is set."""
        with patch.dict(os.environ, {"DATABRICKS_RUNTIME_VERSION": "14.3"}):
            assert is_running_on_databricks() is True

    def test_returns_true_with_empty_version(self):
        """Should return True even if version is empty string."""
        with patch.dict(os.environ, {"DATABRICKS_RUNTIME_VERSION": ""}):
            assert is_running_on_databricks() is True


class TestGetDatabricksRuntimeVersion:
    """Tests for get_databricks_runtime_version function."""

    def test_returns_none_when_not_on_databricks(self):
        """Should return None when not on Databricks."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DATABRICKS_RUNTIME_VERSION", None)
            assert get_databricks_runtime_version() is None

    def test_returns_version_when_on_databricks(self):
        """Should return version string when on Databricks."""
        with patch.dict(os.environ, {"DATABRICKS_RUNTIME_VERSION": "14.3"}):
            assert get_databricks_runtime_version() == "14.3"

    def test_returns_various_version_formats(self):
        """Should return version in various formats."""
        test_versions = ["13.3", "14.0", "14.3.x-scala2.12", "15.0-ml"]
        for version in test_versions:
            with patch.dict(os.environ, {"DATABRICKS_RUNTIME_VERSION": version}):
                assert get_databricks_runtime_version() == version


class TestIsRunningInNotebook:
    """Tests for is_running_in_notebook function."""

    def test_returns_false_when_no_indicators(self):
        """Should return False when no notebook indicators present."""
        with patch.dict(os.environ, {}, clear=True):
            for var in ["DATABRICKS_RUNTIME_VERSION", "DB_IS_DRIVER", "SPARK_HOME"]:
                os.environ.pop(var, None)
            assert is_running_in_notebook() is False

    def test_returns_true_with_runtime_version(self):
        """Should return True when DATABRICKS_RUNTIME_VERSION is set."""
        with patch.dict(os.environ, {"DATABRICKS_RUNTIME_VERSION": "14.3"}):
            assert is_running_in_notebook() is True

    def test_returns_true_with_spark_home(self):
        """Should return True when SPARK_HOME is set."""
        with patch.dict(os.environ, {"SPARK_HOME": "/databricks/spark"}):
            assert is_running_in_notebook() is True

    def test_returns_true_with_db_is_driver(self):
        """Should return True when DB_IS_DRIVER is set."""
        with patch.dict(os.environ, {"DB_IS_DRIVER": "TRUE"}):
            assert is_running_in_notebook() is True


# =============================================================================
# Volume Path Tests
# =============================================================================


class TestGetVolumePath:
    """Tests for get_volume_path function."""

    def test_basic_volume_path(self):
        """Should construct basic Volume path."""
        result = get_volume_path("catalog", "schema", "volume")
        assert result == "/Volumes/catalog/schema/volume"

    def test_volume_path_with_subpath(self):
        """Should construct Volume path with subpath."""
        result = get_volume_path("main", "default", "my_volume", "data")
        assert result == "/Volumes/main/default/my_volume/data"

    def test_volume_path_with_multiple_subpaths(self):
        """Should construct Volume path with multiple subpath components."""
        result = get_volume_path("main", "default", "vol", "a", "b", "c")
        assert result == "/Volumes/main/default/vol/a/b/c"

    def test_volume_path_with_special_characters(self):
        """Should handle names with underscores and hyphens."""
        result = get_volume_path("my_catalog", "my-schema", "volume_name")
        assert result == "/Volumes/my_catalog/my-schema/volume_name"


class TestIsVolumePath:
    """Tests for is_volume_path function."""

    def test_valid_volume_path_string(self):
        """Should return True for valid Volume path string."""
        assert is_volume_path("/Volumes/catalog/schema/volume/file.txt") is True

    def test_valid_volume_path_object(self):
        """Should return True for valid Volume path as Path object."""
        assert is_volume_path(Path("/Volumes/catalog/schema/volume")) is True

    def test_local_path_returns_false(self):
        """Should return False for local paths."""
        assert is_volume_path("/home/user/file.txt") is False
        assert is_volume_path("/Users/user/data") is False
        assert is_volume_path("./relative/path") is False

    def test_dbfs_path_returns_false(self):
        """Should return False for DBFS paths."""
        assert is_volume_path("/dbfs/tmp/data") is False

    def test_case_sensitive(self):
        """Volume path detection should be case-sensitive."""
        assert is_volume_path("/volumes/catalog/schema/volume") is False
        assert is_volume_path("/VOLUMES/catalog/schema/volume") is False

    def test_empty_path(self):
        """Should return False for empty path."""
        assert is_volume_path("") is False

    def test_just_volumes_prefix(self):
        """Should return True for path starting with /Volumes/."""
        assert is_volume_path("/Volumes/") is True


class TestParseVolumePath:
    """Tests for parse_volume_path function."""

    def test_parse_basic_volume_path(self):
        """Should parse basic Volume path."""
        result = parse_volume_path("/Volumes/catalog/schema/volume")
        assert result == {
            "catalog": "catalog",
            "schema": "schema",
            "volume": "volume",
            "subpath": "",
        }

    def test_parse_volume_path_with_subpath(self):
        """Should parse Volume path with subpath."""
        result = parse_volume_path("/Volumes/main/default/vol/data/file.txt")
        assert result == {
            "catalog": "main",
            "schema": "default",
            "volume": "vol",
            "subpath": "data/file.txt",
        }

    def test_parse_volume_path_with_deep_subpath(self):
        """Should parse Volume path with deep nested subpath."""
        result = parse_volume_path("/Volumes/cat/sch/vol/a/b/c/d/file.txt")
        assert result == {
            "catalog": "cat",
            "schema": "sch",
            "volume": "vol",
            "subpath": "a/b/c/d/file.txt",
        }

    def test_parse_non_volume_path_returns_none(self):
        """Should return None for non-Volume paths."""
        assert parse_volume_path("/home/user/file.txt") is None
        assert parse_volume_path("/dbfs/tmp/data") is None
        assert parse_volume_path("./relative") is None

    def test_parse_incomplete_volume_path_returns_none(self):
        """Should return None for incomplete Volume paths."""
        assert parse_volume_path("/Volumes/catalog") is None
        assert parse_volume_path("/Volumes/catalog/schema") is None

    def test_parse_path_object(self):
        """Should parse Path object."""
        result = parse_volume_path(Path("/Volumes/cat/sch/vol/data"))
        assert result["catalog"] == "cat"
        assert result["subpath"] == "data"


# =============================================================================
# Default Project Path Tests
# =============================================================================


class TestGetDefaultProjectPath:
    """Tests for get_default_project_path function."""

    def test_local_path_when_not_on_databricks(self):
        """Should return local path when not on Databricks."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DATABRICKS_RUNTIME_VERSION", None)
            result = get_default_project_path("my_project")
            assert "/.genie-forge/my_project" in result
            assert "/Volumes/" not in result

    def test_volume_path_when_on_databricks_with_catalog(self):
        """Should return Volume path when on Databricks with catalog provided."""
        with patch.dict(os.environ, {"DATABRICKS_RUNTIME_VERSION": "14.3"}):
            result = get_default_project_path(
                "my_project",
                catalog="main",
                schema="default",
                volume_name="genie_forge",
            )
            assert result == "/Volumes/main/default/genie_forge/my_project"

    def test_local_path_when_on_databricks_without_catalog(self):
        """Should return local path when on Databricks but no catalog provided."""
        with patch.dict(os.environ, {"DATABRICKS_RUNTIME_VERSION": "14.3"}):
            result = get_default_project_path("my_project")
            # Without catalog, falls back to local
            assert "/.genie-forge/my_project" in result

    def test_default_schema_and_volume(self):
        """Should use default schema and volume name."""
        with patch.dict(os.environ, {"DATABRICKS_RUNTIME_VERSION": "14.3"}):
            result = get_default_project_path(
                "test",
                catalog="my_catalog",
            )
            assert result == "/Volumes/my_catalog/default/genie_forge/test"

    def test_custom_schema_and_volume(self):
        """Should use custom schema and volume name."""
        with patch.dict(os.environ, {"DATABRICKS_RUNTIME_VERSION": "14.3"}):
            result = get_default_project_path(
                "test",
                catalog="cat",
                schema="custom_schema",
                volume_name="custom_volume",
            )
            assert result == "/Volumes/cat/custom_schema/custom_volume/test"


# =============================================================================
# Ensure Directory Tests
# =============================================================================


class TestEnsureDirectory:
    """Tests for ensure_directory function."""

    def test_creates_directory(self, tmp_path):
        """Should create directory if it doesn't exist."""
        new_dir = tmp_path / "new" / "nested" / "dir"
        assert not new_dir.exists()

        result = ensure_directory(new_dir)

        assert new_dir.exists()
        assert new_dir.is_dir()
        assert result == new_dir

    def test_idempotent_for_existing_directory(self, tmp_path):
        """Should not fail if directory already exists."""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        result = ensure_directory(existing_dir)

        assert existing_dir.exists()
        assert result == existing_dir

    def test_accepts_string_path(self, tmp_path):
        """Should accept string path."""
        path_str = str(tmp_path / "string_path")

        result = ensure_directory(path_str)

        assert Path(path_str).exists()
        assert result == Path(path_str)


# =============================================================================
# ProjectPaths Tests
# =============================================================================


class TestProjectPaths:
    """Tests for ProjectPaths class."""

    def test_local_paths_when_not_on_databricks(self):
        """Should use local paths when not on Databricks."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DATABRICKS_RUNTIME_VERSION", None)
            paths = ProjectPaths("my_project")

            assert "/.genie-forge/my_project" in paths.root
            assert paths.state_file.endswith(".genie-forge.json")
            assert "/conf/spaces" in paths.spaces_dir
            assert paths.is_databricks is False
            assert paths.is_volume_path is False

    def test_volume_paths_when_on_databricks(self):
        """Should use Volume paths when on Databricks with catalog."""
        with patch.dict(os.environ, {"DATABRICKS_RUNTIME_VERSION": "14.3"}):
            paths = ProjectPaths(
                "my_project",
                catalog="main",
                schema="default",
                volume_name="genie_forge",
            )

            assert paths.root == "/Volumes/main/default/genie_forge/my_project"
            assert (
                paths.state_file == "/Volumes/main/default/genie_forge/my_project/.genie-forge.json"
            )
            assert paths.spaces_dir == "/Volumes/main/default/genie_forge/my_project/conf/spaces"
            assert paths.is_databricks is True
            assert paths.is_volume_path is True
            assert paths.catalog == "main"
            assert paths.schema == "default"
            assert paths.volume_name == "genie_forge"

    def test_custom_base_path_override(self):
        """Should use custom base path when provided."""
        paths = ProjectPaths("ignored", base_path="/custom/path")

        assert paths.root == "/custom/path"
        assert paths.state_file == "/custom/path/.genie-forge.json"

    def test_all_path_properties(self, tmp_path):
        """Should return correct paths for all properties."""
        paths = ProjectPaths("test", base_path=str(tmp_path))

        assert paths.root == str(tmp_path)
        assert paths.conf_dir == f"{tmp_path}/conf"
        assert paths.spaces_dir == f"{tmp_path}/conf/spaces"
        assert paths.variables_dir == f"{tmp_path}/conf/variables"
        assert paths.state_file == f"{tmp_path}/.genie-forge.json"
        assert paths.exports_dir == f"{tmp_path}/exports"

    def test_get_config_path(self, tmp_path):
        """Should return correct config path."""
        paths = ProjectPaths("test", base_path=str(tmp_path))

        assert paths.get_config_path("sales") == f"{tmp_path}/conf/spaces/sales.yaml"

    def test_get_export_path(self, tmp_path):
        """Should return correct export path."""
        paths = ProjectPaths("test", base_path=str(tmp_path))

        assert paths.get_export_path("space1") == f"{tmp_path}/exports/space1.yaml"
        assert paths.get_export_path("space1", "json") == f"{tmp_path}/exports/space1.json"

    def test_ensure_structure(self, tmp_path):
        """Should create directory structure."""
        paths = ProjectPaths("test", base_path=str(tmp_path))

        paths.ensure_structure()

        assert Path(paths.spaces_dir).exists()
        assert Path(paths.variables_dir).exists()

    def test_repr(self, tmp_path):
        """Should have informative repr."""
        paths = ProjectPaths("test", base_path=str(tmp_path))

        repr_str = repr(paths)
        assert "ProjectPaths" in repr_str
        assert str(tmp_path) in repr_str


# =============================================================================
# Sanitize Name Tests
# =============================================================================


class TestSanitizeName:
    """Tests for sanitize_name function."""

    def test_basic_sanitization(self):
        """Should sanitize basic name."""
        assert sanitize_name("My Sales Analytics") == "my_sales_analytics"

    def test_removes_special_characters(self):
        """Should remove special characters."""
        assert sanitize_name("Sales & Marketing!") == "sales_marketing"

    def test_handles_multiple_spaces(self):
        """Should collapse multiple spaces."""
        assert sanitize_name("Sales   Analytics") == "sales_analytics"

    def test_handles_leading_trailing_whitespace(self):
        """Should strip leading/trailing whitespace."""
        assert sanitize_name("  Sales  ") == "sales"

    def test_truncates_to_max_length(self):
        """Should truncate to max length."""
        long_name = "This is a very long name that should be truncated"
        result = sanitize_name(long_name, max_length=20)
        assert len(result) <= 20

    def test_handles_empty_string(self):
        """Should return 'unnamed' for empty string."""
        assert sanitize_name("") == "unnamed"
        assert sanitize_name("   ") == "unnamed"

    def test_handles_only_special_characters(self):
        """Should return 'unnamed' for string with only special chars."""
        assert sanitize_name("!@#$%^&*()") == "unnamed"

    def test_preserves_numbers(self):
        """Should preserve numbers."""
        assert sanitize_name("Sales 2024 Q1") == "sales_2024_q1"

    def test_collapses_underscores(self):
        """Should collapse multiple underscores."""
        assert sanitize_name("a___b") == "a_b"

    def test_unicode_characters(self):
        """Should handle unicode characters."""
        # Unicode letters are kept by \w
        result = sanitize_name("Café Analytics")
        assert "caf" in result


# =============================================================================
# Integration Tests
# =============================================================================


class TestUtilsIntegration:
    """Integration tests for utils module."""

    def test_full_workflow_local(self, tmp_path):
        """Test full workflow on local machine."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DATABRICKS_RUNTIME_VERSION", None)

            # Create project paths
            paths = ProjectPaths("integration_test", base_path=str(tmp_path))

            # Ensure structure exists
            paths.ensure_structure()

            # Verify paths
            assert Path(paths.spaces_dir).exists()
            assert Path(paths.variables_dir).exists()

            # Create a config file
            config_path = Path(paths.get_config_path("test_space"))
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text("test: config")

            assert config_path.exists()

    def test_volume_path_roundtrip(self):
        """Test creating and parsing Volume paths."""
        # Create a Volume path
        volume_path = get_volume_path("main", "default", "vol", "project", "data")

        # Verify it's a Volume path
        assert is_volume_path(volume_path)

        # Parse it back
        parsed = parse_volume_path(volume_path)
        assert parsed["catalog"] == "main"
        assert parsed["schema"] == "default"
        assert parsed["volume"] == "vol"
        assert parsed["subpath"] == "project/data"

    def test_environment_detection_consistency(self):
        """Test that environment detection functions are consistent."""
        with patch.dict(os.environ, {"DATABRICKS_RUNTIME_VERSION": "14.3"}):
            # All should indicate Databricks environment
            assert is_running_on_databricks() is True
            assert is_running_in_notebook() is True
            assert get_databricks_runtime_version() is not None

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DATABRICKS_RUNTIME_VERSION", None)
            os.environ.pop("DB_IS_DRIVER", None)
            os.environ.pop("SPARK_HOME", None)

            # All should indicate local environment
            assert is_running_on_databricks() is False
            # Note: is_running_in_notebook might still return True if SPARK_HOME is set
            assert get_databricks_runtime_version() is None
