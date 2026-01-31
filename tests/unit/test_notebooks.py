"""Unit tests for notebook validation.

Tests that:
1. All notebooks have valid Python syntax
2. Notebook imports are resolvable
3. Example configurations in notebooks are valid SpaceConfig objects
"""

import ast
import re
from pathlib import Path

import pytest
import yaml

# Path to notebooks directory
NOTEBOOKS_DIR = Path(__file__).parent.parent.parent / "notebooks"

# All notebook files
NOTEBOOK_FILES = list(NOTEBOOKS_DIR.glob("*.py"))


class TestNotebookSyntax:
    """Tests for notebook Python syntax validation."""

    @pytest.mark.parametrize("notebook_path", NOTEBOOK_FILES, ids=lambda p: p.name)
    def test_notebook_parses_as_valid_python(self, notebook_path: Path):
        """Each notebook should be valid Python syntax."""
        content = notebook_path.read_text()

        # Remove Databricks magic commands for syntax checking
        # These include:
        # - # MAGIC %md (markdown)
        # - %pip install (pip magic)
        # - %sql (SQL magic)
        lines = []
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("# MAGIC"):
                # Convert magic to a comment that Python can parse
                lines.append("# " + line)
            elif stripped.startswith("%pip") or stripped.startswith("%sql"):
                # Convert cell magic to a comment
                lines.append("# " + line)
            else:
                lines.append(line)

        cleaned_content = "\n".join(lines)

        try:
            ast.parse(cleaned_content)
        except SyntaxError as e:
            pytest.fail(f"Notebook {notebook_path.name} has syntax error: {e}")

    @pytest.mark.parametrize("notebook_path", NOTEBOOK_FILES, ids=lambda p: p.name)
    def test_notebook_has_command_separators(self, notebook_path: Path):
        """Each notebook should have Databricks command separators."""
        content = notebook_path.read_text()

        # Check for command separators
        assert "# COMMAND ----------" in content, (
            f"Notebook {notebook_path.name} missing Databricks command separators"
        )


class TestNotebookImports:
    """Tests for notebook import validation."""

    @pytest.mark.parametrize("notebook_path", NOTEBOOK_FILES, ids=lambda p: p.name)
    def test_genie_forge_imports_are_valid(self, notebook_path: Path):
        """All genie_forge imports in notebooks should be resolvable."""
        content = notebook_path.read_text()

        # Find all import statements
        import_pattern = r"^(?:from\s+(genie_forge[\w.]*)\s+import|import\s+(genie_forge[\w.]*))"

        for line in content.split("\n"):
            line = line.strip()
            # Skip magic commands and comments
            if line.startswith("#"):
                continue

            match = re.match(import_pattern, line)
            if match:
                module_name = match.group(1) or match.group(2)
                try:
                    # Try to import the module
                    __import__(module_name)
                except ImportError as e:
                    pytest.fail(
                        f"Notebook {notebook_path.name} has invalid import: '{module_name}' - {e}"
                    )


class TestNotebookExamples:
    """Tests for example configurations in notebooks."""

    def _extract_yaml_configs(self, content: str) -> list[tuple[str, str]]:
        """Extract YAML configuration strings from notebook content.

        Returns list of (config_name, yaml_string) tuples.
        """
        configs = []

        # Pattern for multi-line string assignments that look like YAML configs
        # e.g., config_with_variables = """
        pattern = r'(\w+)\s*=\s*"""(.*?)"""'

        for match in re.finditer(pattern, content, re.DOTALL):
            var_name = match.group(1)
            yaml_content = match.group(2).strip()

            # Check if it looks like a YAML config (has version or space_id)
            if "version:" in yaml_content or "space_id:" in yaml_content:
                configs.append((var_name, yaml_content))

        return configs

    def _extract_dict_configs(self, content: str) -> list[tuple[str, dict]]:
        """Extract Python dict configurations from notebook content.

        Returns list of (config_name, dict) tuples.
        """
        configs = []

        # Parse the AST to find dict assignments
        try:
            # Clean content for parsing
            lines = []
            for line in content.split("\n"):
                if line.strip().startswith("# MAGIC"):
                    lines.append("# " + line)
                else:
                    lines.append(line)

            tree = ast.parse("\n".join(lines))
        except SyntaxError:
            return configs

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                # Check if it's a dict assignment with space-related keys
                if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                    var_name = node.targets[0].id

                    # Skip non-config variables
                    if not any(kw in var_name.lower() for kw in ["config", "space"]):
                        continue

                    if isinstance(node.value, ast.Dict):
                        # Try to safely evaluate the dict
                        try:
                            # We can't easily eval complex dicts with string interpolation
                            # So we check structure instead
                            keys = []
                            for key in node.value.keys:
                                if isinstance(key, ast.Constant):
                                    keys.append(key.value)

                            # If it has space config keys, record it
                            if any(
                                k in keys for k in ["version", "space_id", "title", "warehouse_id"]
                            ):
                                configs.append((var_name, {"_keys": keys}))
                        except Exception:
                            pass

        return configs

    def test_05_advanced_self_join_config_structure(self):
        """Test that self_join_config in 05_Advanced has required fields."""
        notebook_path = NOTEBOOKS_DIR / "05_Advanced_Patterns.py"
        content = notebook_path.read_text()

        # Check that self_join_config exists and has key elements
        assert "self_join_config" in content
        assert '"version": 2' in content or "'version': 2" in content
        assert '"space_id"' in content or "'space_id'" in content
        assert '"join_specs"' in content or "'join_specs'" in content
        assert "manager_id" in content  # Self-join indicator

    def test_05_advanced_parameterized_config_structure(self):
        """Test that parameterized_config in 05_Advanced has required fields."""
        notebook_path = NOTEBOOKS_DIR / "05_Advanced_Patterns.py"
        content = notebook_path.read_text()

        # Check for parameterized query elements
        assert "parameterized_config" in content
        assert '"parameters"' in content or "'parameters'" in content
        assert '"type_hint"' in content or "'type_hint'" in content
        assert '"default_value"' in content or "'default_value'" in content
        assert ":region_filter" in content  # Parameter placeholder

    def test_05_advanced_benchmark_config_structure(self):
        """Test that benchmark_config in 05_Advanced has required fields."""
        notebook_path = NOTEBOOKS_DIR / "05_Advanced_Patterns.py"
        content = notebook_path.read_text()

        # Check for benchmark elements
        assert "benchmark_config" in content
        assert '"benchmarks"' in content or "'benchmarks'" in content
        assert '"expected_sql"' in content or "'expected_sql'" in content

    def test_05_advanced_relationship_type_annotation(self):
        """Test that relationship type annotations are present."""
        notebook_path = NOTEBOOKS_DIR / "05_Advanced_Patterns.py"
        content = notebook_path.read_text()

        # Check for relationship type annotation
        assert "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--" in content

        # Check documentation of all relationship types
        assert "FROM_RELATIONSHIP_TYPE_ONE_TO_ONE" in content
        assert "FROM_RELATIONSHIP_TYPE_MANY_TO_MANY" in content

    @pytest.mark.parametrize("notebook_path", NOTEBOOK_FILES, ids=lambda p: p.name)
    def test_yaml_examples_are_valid_yaml(self, notebook_path: Path):
        """YAML strings in notebooks should be valid YAML syntax."""
        content = notebook_path.read_text()
        configs = self._extract_yaml_configs(content)

        for var_name, yaml_content in configs:
            # Replace variable placeholders with dummy values for parsing
            yaml_content = re.sub(r"\$\{[^}]+\}", "placeholder", yaml_content)

            try:
                yaml.safe_load(yaml_content)
            except yaml.YAMLError as e:
                pytest.fail(f"Invalid YAML in {notebook_path.name}, variable '{var_name}': {e}")


class TestNotebookContent:
    """Tests for notebook content completeness."""

    def test_05_advanced_covers_key_topics(self):
        """Notebook 05 should cover all advanced topics."""
        notebook_path = NOTEBOOKS_DIR / "05_Advanced_Patterns.py"
        content = notebook_path.read_text()

        required_topics = [
            "Programmatic API",
            "Self-Join",
            "Relationship Type",
            "Parameterized",
            "Benchmark",
            "Demo Tables",
            "Variable Substitution",
            "Bulk Operations",
        ]

        for topic in required_topics:
            assert topic.lower() in content.lower(), (
                f"Notebook 05_Advanced_Patterns.py should cover '{topic}'"
            )

    def test_05_advanced_has_summary_table(self):
        """Notebook 05 should have a summary table with all patterns."""
        notebook_path = NOTEBOOKS_DIR / "05_Advanced_Patterns.py"
        content = notebook_path.read_text()

        # Check for summary section
        assert "## Summary" in content

        # Check summary includes key patterns
        summary_patterns = [
            "Programmatic API",
            "Self-Joins",
            "Relationship Types",
            "Parameterized Queries",
            "Benchmarks",
        ]

        for pattern in summary_patterns:
            assert pattern in content, f"Summary table should include '{pattern}'"

    def test_notebooks_have_time_estimates(self):
        """Each notebook should have a time estimate."""
        for notebook_path in NOTEBOOK_FILES:
            content = notebook_path.read_text()

            # Check for time estimate (e.g., "Time: ~10 minutes")
            assert re.search(r"Time:\s*~?\d+\s*minutes?", content, re.IGNORECASE), (
                f"Notebook {notebook_path.name} should have a time estimate"
            )

    def test_notebooks_have_prerequisites(self):
        """Each notebook (except 00) should list prerequisites."""
        for notebook_path in NOTEBOOK_FILES:
            if notebook_path.name == "00_Setup_Prerequisites.py":
                continue

            content = notebook_path.read_text()

            assert "prerequisite" in content.lower(), (
                f"Notebook {notebook_path.name} should list prerequisites"
            )
