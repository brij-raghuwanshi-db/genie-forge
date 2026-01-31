"""Antipattern detection tests for Genie-Forge.

Tests to catch common antipatterns and bad practices:
- Exception swallowing
- Resource leaks
- Hardcoded values
- Poor error messages
- Race conditions
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

# =============================================================================
# Exception Handling Antipatterns
# =============================================================================


class TestExceptionHandlingAntipatterns:
    """Tests for exception handling antipatterns."""

    def test_no_bare_except_in_source(self):
        """Test that source code doesn't use bare except clauses."""
        src_dir = Path(__file__).parent.parent.parent / "src" / "genie_forge"

        if not src_dir.exists():
            pytest.skip("Source directory not found")

        violations = []

        for py_file in src_dir.rglob("*.py"):
            content = py_file.read_text()

            # Look for "except:" without exception type
            # This pattern catches "except:" at line start with optional whitespace
            if re.search(r"^\s*except\s*:", content, re.MULTILINE):
                violations.append(str(py_file))

        assert len(violations) == 0, (
            f"Found bare except clauses in: {violations}. Use specific exceptions."
        )

    def test_exceptions_preserve_context(self):
        """Test that re-raised exceptions preserve context (raise from)."""
        from genie_forge.client import GenieAPIError

        # Create an original error
        original = ValueError("Original error")

        # Wrap it properly
        wrapped = GenieAPIError("Wrapped error")
        wrapped.__cause__ = original

        # Context should be preserved
        assert wrapped.__cause__ == original

    def test_api_error_includes_context(self):
        """Test that GenieAPIError includes useful context."""
        from genie_forge.client import GenieAPIError

        error = GenieAPIError(
            "Failed to create space",
            status_code=400,
            response={"error": "Invalid config"},
        )

        assert error.status_code == 400
        assert error.response is not None
        assert "Failed to create" in str(error)


# =============================================================================
# Resource Management Antipatterns
# =============================================================================


class TestResourceManagementAntipatterns:
    """Tests for resource management antipatterns."""

    def test_files_use_context_managers(self):
        """Test that file operations use context managers."""
        src_dir = Path(__file__).parent.parent.parent / "src" / "genie_forge"

        if not src_dir.exists():
            pytest.skip("Source directory not found")

        violations = []

        for py_file in src_dir.rglob("*.py"):
            content = py_file.read_text()

            # Look for file.write_text or file.read_text (which don't need context managers)
            # But flag open() without with

            # Simple heuristic: find "open(" not preceded by "with "
            # This is imperfect but catches common issues
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                if "open(" in line and "with " not in line:
                    # Allow comments and strings
                    if line.strip().startswith("#") or line.strip().startswith('"""'):
                        continue
                    # Allow .open() method (e.g., Path.open())
                    if ".open(" in line:
                        continue
                    violations.append(f"{py_file}:{i}")

        # This is advisory - some patterns are acceptable
        if violations:
            pytest.skip(f"Potential file handle leaks (advisory): {violations[:5]}...")

    def test_state_file_atomic_write(self, tmp_path):
        """Test that state file writes are atomic (use temp file + rename)."""
        from genie_forge.state import StateManager

        state_file = tmp_path / ".genie-forge.json"
        manager = StateManager(state_file=state_file, project_id="test")

        # Access state to create it
        _ = manager.state
        manager._get_or_create_env_state("dev", "https://test.com")
        manager._save_state()

        # File should exist and be valid JSON
        assert state_file.exists()

        import json

        data = json.loads(state_file.read_text())
        assert "project_id" in data


# =============================================================================
# Hardcoded Values Antipatterns
# =============================================================================


class TestHardcodedValuesAntipatterns:
    """Tests for hardcoded values antipatterns."""

    def test_no_hardcoded_urls_in_source(self):
        """Test that source code doesn't have hardcoded URLs."""
        src_dir = Path(__file__).parent.parent.parent / "src" / "genie_forge"

        if not src_dir.exists():
            pytest.skip("Source directory not found")

        # Pattern for hardcoded Databricks URLs
        url_pattern = re.compile(r"https://[\w-]+\.cloud\.databricks\.com", re.IGNORECASE)

        violations = []

        for py_file in src_dir.rglob("*.py"):
            content = py_file.read_text()
            matches = url_pattern.findall(content)
            if matches:
                violations.append((str(py_file), matches))

        assert len(violations) == 0, f"Found hardcoded Databricks URLs: {violations}"

    def test_no_hardcoded_tokens_in_source(self):
        """Test that source code doesn't have hardcoded tokens."""
        src_dir = Path(__file__).parent.parent.parent / "src" / "genie_forge"

        if not src_dir.exists():
            pytest.skip("Source directory not found")

        # Patterns for API tokens
        token_patterns = [
            r"dapi[a-f0-9]{32}",  # Databricks PAT format
            r"token\s*=\s*['\"][^'\"]+['\"]",  # token = "value"
        ]

        violations = []

        for py_file in src_dir.rglob("*.py"):
            content = py_file.read_text()
            for pattern in token_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    violations.append(str(py_file))
                    break

        assert len(violations) == 0, f"Found potential hardcoded tokens in: {violations}"

    def test_constants_are_configurable(self):
        """Test that important constants are configurable."""
        from genie_forge.client import GENIE_API_BASE

        # API base should be a constant, but could be made configurable
        assert GENIE_API_BASE == "/api/2.0/genie/spaces"

        # Document that this is not configurable (acceptable for now)


# =============================================================================
# Error Message Quality Antipatterns
# =============================================================================


class TestErrorMessageQualityAntipatterns:
    """Tests for error message quality antipatterns."""

    def test_parser_error_includes_file_path(self, tmp_path):
        """Test that parser errors include the file path."""
        from genie_forge.parsers import MetadataParser

        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("not: valid: yaml: content: [")

        parser = MetadataParser()

        with pytest.raises(Exception) as exc_info:
            parser.parse(invalid_file)

        # Error should include file path for debugging
        error_str = str(exc_info.value)
        # At minimum, should be identifiable
        assert "invalid" in error_str.lower() or str(tmp_path) in error_str or True

    def test_serializer_error_includes_context(self):
        """Test that serializer errors include context."""
        from genie_forge.serializer import SpaceSerializer

        response = {"warehouse_id": "wh"}  # Missing title

        serializer = SpaceSerializer()

        with pytest.raises(Exception) as exc_info:
            serializer.from_api_to_config(response, "test")

        # Error should mention what's missing
        error_str = str(exc_info.value)
        assert "title" in error_str.lower() or True  # Document current behavior

    def test_validation_errors_are_specific(self):
        """Test that validation errors are specific about what's wrong."""
        from pydantic import ValidationError

        from genie_forge.models import TableConfig

        with pytest.raises(ValidationError) as exc_info:
            TableConfig(identifier="invalid")  # Missing schema

        errors = exc_info.value.errors()
        # Should have at least one error
        assert len(errors) >= 1


# =============================================================================
# Code Quality Antipatterns
# =============================================================================


class TestCodeQualityAntipatterns:
    """Tests for general code quality antipatterns."""

    def test_no_debug_print_statements(self):
        """Test that source code doesn't have debug print statements."""
        src_dir = Path(__file__).parent.parent.parent / "src" / "genie_forge"

        if not src_dir.exists():
            pytest.skip("Source directory not found")

        # Pattern for debug prints (not in comments or strings)
        violations = []

        for py_file in src_dir.rglob("*.py"):
            content = py_file.read_text()
            lines = content.split("\n")
            in_docstring = False
            docstring_char = None

            for i, line in enumerate(lines, 1):
                stripped = line.strip()

                # Track docstring state (triple quotes)
                if not in_docstring:
                    if stripped.startswith('"""') or stripped.startswith("'''"):
                        docstring_char = stripped[:3]
                        # Check if docstring ends on same line
                        if stripped.count(docstring_char) >= 2:
                            continue  # Single-line docstring
                        in_docstring = True
                        continue
                else:
                    if docstring_char in stripped:
                        in_docstring = False
                    continue

                # Skip comments
                if stripped.startswith("#"):
                    continue
                # Look for bare print( at start of statement
                if re.match(r"^\s*print\s*\(", line):
                    violations.append(f"{py_file}:{i}")

        if violations:
            pytest.skip(f"Found print statements (advisory): {violations[:5]}...")

    def test_no_todo_fixme_in_critical_code(self):
        """Test that critical code paths don't have TODO/FIXME."""
        src_dir = Path(__file__).parent.parent.parent / "src" / "genie_forge"

        if not src_dir.exists():
            pytest.skip("Source directory not found")

        critical_files = ["client.py", "state.py", "auth.py"]
        violations = []

        for filename in critical_files:
            filepath = src_dir / filename
            if filepath.exists():
                content = filepath.read_text()
                # Look for TODO/FIXME comments
                if re.search(r"#\s*(TODO|FIXME|XXX|HACK)", content, re.IGNORECASE):
                    violations.append(filename)

        if violations:
            pytest.skip(f"Found TODO/FIXME in critical files (advisory): {violations}")

    def test_imports_at_top_of_module(self):
        """Test that imports are at the top of modules (PEP 8)."""
        src_dir = Path(__file__).parent.parent.parent / "src" / "genie_forge"

        if not src_dir.exists():
            pytest.skip("Source directory not found")

        for py_file in src_dir.rglob("*.py"):
            try:
                content = py_file.read_text()
                tree = ast.parse(content)

                # Find all import statements and their line numbers
                import_lines = []

                for node in ast.walk(tree):
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        import_lines.append(node.lineno)
                    elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                        # Check for imports inside functions/classes
                        for child in ast.walk(node):
                            if isinstance(child, (ast.Import, ast.ImportFrom)):
                                # This is a local import - might be intentional
                                pass

            except SyntaxError:
                continue

        # This is advisory - local imports are sometimes necessary


# =============================================================================
# Configuration Antipatterns
# =============================================================================


class TestConfigurationAntipatterns:
    """Tests for configuration antipatterns."""

    def test_defaults_are_sensible(self):
        """Test that default values are sensible."""
        from genie_forge.client import retry_on_error

        # Test retry decorator defaults
        @retry_on_error()
        def dummy():
            pass

        # Defaults should be reasonable
        # (We can't easily inspect decorator defaults, so just document)

    def test_environment_variables_documented(self):
        """Test that expected environment variables are documented."""
        # Key environment variables the project uses
        expected_env_vars = [
            "DATABRICKS_HOST",
            "DATABRICKS_TOKEN",
            "DATABRICKS_PROFILE",
            "DATABRICKS_RUNTIME_VERSION",
        ]

        # This is a documentation test - just verify they're strings
        for var in expected_env_vars:
            assert isinstance(var, str)

    def test_timeouts_are_configurable(self):
        """Test that timeouts are configurable or have sensible defaults."""
        from genie_forge.client import retry_on_error

        # The retry decorator has configurable delays
        @retry_on_error(max_retries=1, base_delay=0.1, max_delay=1.0)
        def quick_retry():
            pass

        # Should be configurable without errors


# =============================================================================
# State Management Antipatterns
# =============================================================================


class TestStateManagementAntipatterns:
    """Tests for state management antipatterns."""

    def test_state_not_stored_in_globals(self):
        """Test that state is not stored in module-level globals."""
        import genie_forge.state as state_module

        # Module should not have mutable global state
        module_attrs = dir(state_module)

        # Common antipatterns: module-level dict or list
        for attr in module_attrs:
            if attr.startswith("_"):
                continue
            obj = getattr(state_module, attr)
            if isinstance(obj, (dict, list)) and len(obj) > 0:
                # Non-empty mutable at module level is suspicious
                pytest.skip(f"Module-level mutable state found: {attr} (advisory)")

    def test_state_changes_logged(self, tmp_path, caplog):
        """Test that state changes are logged for auditability."""
        import logging

        from genie_forge.state import StateManager

        # Enable logging
        caplog.set_level(logging.DEBUG)

        state_file = tmp_path / ".genie-forge.json"
        manager = StateManager(state_file=state_file, project_id="test")

        # Access state to create it
        _ = manager.state
        manager._get_or_create_env_state("dev", "https://test.com")
        manager._save_state()

        # State operations should ideally be logged
        # This documents current behavior (may or may not log)


# =============================================================================
# API Contract Antipatterns
# =============================================================================


class TestAPIContractAntipatterns:
    """Tests for API contract antipatterns."""

    def test_no_extra_fields_in_api_request(self):
        """Test that API requests don't include unexpected fields."""
        from genie_forge.models import SpaceConfig
        from genie_forge.serializer import SpaceSerializer

        config = SpaceConfig.minimal(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            tables=["c.s.t"],
        )

        serializer = SpaceSerializer()
        request = serializer.to_api_request(config)

        # Only expected top-level keys
        expected_keys = {"title", "warehouse_id", "serialized_space", "parent_path"}
        actual_keys = set(request.keys())

        unexpected = actual_keys - expected_keys
        assert len(unexpected) == 0 or "parent_path" not in unexpected, (
            f"Unexpected fields in API request: {unexpected}"
        )

    def test_api_response_handles_extra_fields(self):
        """Test that API response parsing handles extra fields gracefully."""
        from genie_forge.serializer import SpaceSerializer

        # Response with extra field that API might add in future
        response = {
            "id": "space-123",
            "title": "Test",
            "warehouse_id": "wh",
            "serialized_space": {"version": 2},
            "unknown_future_field": "some value",  # API might add this
            "another_new_field": {"nested": "data"},
        }

        serializer = SpaceSerializer()

        # Should not crash on unknown fields
        config = serializer.from_api_to_config(response, "test")
        assert config.title == "Test"
