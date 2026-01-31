"""Unit tests for new v0.3.0 CLI commands (init, whoami, demo-status)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from genie_forge.cli import main


class TestInitCommand:
    """Tests for init command."""

    def test_init_help(self):
        """Test init command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["init", "--help"])

        assert result.exit_code == 0
        assert "--path" in result.output
        assert "--force" in result.output
        assert "--minimal" in result.output

    def test_init_creates_structure(self, tmp_path):
        """Test init creates correct directory structure."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["init", "--yes"])

            assert result.exit_code == 0

            # Check directories created
            assert Path("conf/spaces").exists()
            assert Path("conf/variables").exists()

            # Check state file created
            assert Path(".genie-forge.json").exists()

            # Check example files created
            assert Path("conf/spaces/example.yaml").exists()
            assert Path("conf/variables/env.yaml").exists()

    def test_init_minimal(self, tmp_path):
        """Test init with --minimal flag."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["init", "--yes", "--minimal"])

            assert result.exit_code == 0

            # Check directories created
            assert Path("conf/spaces").exists()

            # Check example files NOT created
            assert not Path("conf/spaces/example.yaml").exists()

    def test_init_custom_path(self, tmp_path):
        """Test init with custom path."""
        runner = CliRunner()
        custom_path = tmp_path / "my-project"

        result = runner.invoke(main, ["init", "--path", str(custom_path), "--yes"])

        assert result.exit_code == 0
        assert (custom_path / "conf" / "spaces").exists()
        assert (custom_path / ".genie-forge.json").exists()

    def test_init_already_exists(self, tmp_path):
        """Test init when project already exists."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # First init
            runner.invoke(main, ["init", "--yes"])

            # Second init without force
            result = runner.invoke(main, ["init", "--yes"])

            # Should still succeed (with warning)
            assert result.exit_code == 0

    def test_init_force_overwrite(self, tmp_path):
        """Test init with --force overwrites existing files."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # First init
            runner.invoke(main, ["init", "--yes"])

            # Modify a file
            example_file = Path("conf/spaces/example.yaml")
            example_file.write_text("modified content")

            # Second init with force
            result = runner.invoke(main, ["init", "--yes", "--force"])

            assert result.exit_code == 0
            # File should be overwritten
            assert example_file.read_text() != "modified content"

    def test_init_state_file_valid_json(self, tmp_path):
        """Test that created state file is valid JSON."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            runner.invoke(main, ["init", "--yes"])

            state_file = Path(".genie-forge.json")
            content = state_file.read_text()
            data = json.loads(content)

            assert "version" in data
            assert "environments" in data

    def test_init_updates_gitignore(self, tmp_path):
        """Test init updates .gitignore."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create existing .gitignore
            Path(".gitignore").write_text("*.pyc\n")

            runner.invoke(main, ["init", "--yes"])

            gitignore = Path(".gitignore").read_text()
            assert "*.pyc" in gitignore  # Original content preserved
            assert ".genie-forge.json" in gitignore  # New content added


class TestWhoamiCommand:
    """Tests for whoami command."""

    def test_whoami_help(self):
        """Test whoami command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["whoami", "--help"])

        assert result.exit_code == 0
        assert "--profile" in result.output
        assert "--json" in result.output

    # Note: Detailed whoami functionality tests are skipped because
    # mocking get_genie_client across different Python versions is complex.
    # The whoami command is tested through integration tests instead.


class TestDemoStatusCommand:
    """Tests for demo-status command."""

    def test_demo_status_help(self):
        """Test demo-status command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["demo-status", "--help"])

        assert result.exit_code == 0
        assert "--catalog" in result.output
        assert "--schema" in result.output
        assert "--warehouse-id" in result.output

    def test_demo_status_requires_options(self):
        """Test demo-status requires required options."""
        runner = CliRunner()
        result = runner.invoke(main, ["demo-status"])

        assert result.exit_code != 0
        # Should complain about missing required options

    @patch("genie_forge.demo_tables.check_demo_objects_exist")
    @patch("genie_forge.cli.demo.get_genie_client")
    def test_demo_status_shows_status(self, mock_get_client, mock_check):
        """Test demo-status shows object status."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_check.return_value = {
            "existing_tables": ["cat.sch.employees"],
            "missing_tables": ["cat.sch.sales"],
            "existing_functions": [],
            "missing_functions": ["cat.sch.func1"],
            "total_existing": 1,
            "total_missing": 2,
        }

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "demo-status",
                "--catalog",
                "cat",
                "--schema",
                "sch",
                "--warehouse-id",
                "wh123",
            ],
        )

        assert result.exit_code == 0

    @patch("genie_forge.demo_tables.check_demo_objects_exist")
    @patch("genie_forge.cli.demo.get_genie_client")
    def test_demo_status_json_output(self, mock_get_client, mock_check):
        """Test demo-status with JSON output."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_check.return_value = {
            "existing_tables": [],
            "missing_tables": [],
            "existing_functions": [],
            "missing_functions": [],
            "total_existing": 0,
            "total_missing": 0,
        }

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "demo-status",
                "--catalog",
                "cat",
                "--schema",
                "sch",
                "--warehouse-id",
                "wh123",
                "--json",
            ],
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "tables" in data
        assert "functions" in data


class TestSpaceListCommand:
    """Tests for space-list command."""

    def test_space_list_help(self):
        """Test space-list command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["space-list", "--help"])

        assert result.exit_code == 0
        assert "--profile" in result.output
        assert "--limit" in result.output

    @patch("genie_forge.cli.space_cmd.get_genie_client")
    @patch("genie_forge.cli.space_cmd.fetch_all_spaces_paginated")
    def test_space_list_displays_spaces(self, mock_fetch, mock_get_client):
        """Test space-list displays spaces."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_fetch.return_value = [
            {"id": "space1", "title": "Space 1", "warehouse_id": "wh1", "creator": "user1"},
            {"id": "space2", "title": "Space 2", "warehouse_id": "wh2", "creator": "user2"},
        ]

        runner = CliRunner()
        result = runner.invoke(main, ["space-list", "--profile", "TEST"])

        assert result.exit_code == 0
        assert "Space 1" in result.output or "2" in result.output


class TestSpaceGetCommand:
    """Tests for space-get command."""

    def test_space_get_help(self):
        """Test space-get command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["space-get", "--help"])

        assert result.exit_code == 0
        assert "--name" in result.output
        assert "--raw" in result.output

    def test_space_get_requires_id_or_name(self):
        """Test space-get requires either ID or --name."""
        runner = CliRunner()
        result = runner.invoke(main, ["space-get", "--profile", "TEST"])

        assert result.exit_code != 0


class TestSpaceFindCommand:
    """Tests for space-find command."""

    def test_space_find_help(self):
        """Test space-find command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["space-find", "--help"])

        assert result.exit_code == 0
        assert "--name" in result.output

    def test_space_find_requires_name(self):
        """Test space-find requires --name."""
        runner = CliRunner()
        result = runner.invoke(main, ["space-find"])

        assert result.exit_code != 0


class TestSpaceCreateCommand:
    """Tests for space-create command."""

    def test_space_create_help(self):
        """Test space-create command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["space-create", "--help"])

        assert result.exit_code == 0
        assert "--from-file" in result.output
        assert "--warehouse-id" in result.output
        assert "--tables" in result.output
        assert "--set" in result.output

    def test_space_create_requires_title_or_file(self):
        """Test space-create requires title or --from-file."""
        runner = CliRunner()
        result = runner.invoke(main, ["space-create", "--profile", "TEST"])

        assert result.exit_code != 0

    def test_space_create_requires_warehouse_without_file(self):
        """Test space-create requires --warehouse-id when not using --from-file."""
        runner = CliRunner()
        result = runner.invoke(main, ["space-create", "Test Space", "--profile", "TEST"])

        assert result.exit_code != 0

    @patch("genie_forge.cli.space_cmd.get_genie_client")
    def test_space_create_dry_run(self, mock_get_client, tmp_path):
        """Test space-create with --dry-run."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Create a config file
        config_file = tmp_path / "space.yaml"
        config_file.write_text(
            """
title: Test Space
warehouse_id: wh123
data_sources:
  tables:
    - identifier: cat.sch.table
"""
        )

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["space-create", "--from-file", str(config_file), "--dry-run", "--profile", "TEST"],
        )

        assert result.exit_code == 0
        assert "dry" in result.output.lower() or "preview" in result.output.lower()


class TestSpaceExportCommand:
    """Tests for space-export command."""

    def test_space_export_help(self):
        """Test space-export command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["space-export", "--help"])

        assert result.exit_code == 0
        assert "--output-dir" in result.output
        assert "--pattern" in result.output
        assert "--format" in result.output


class TestSpaceCloneCommand:
    """Tests for space-clone command."""

    def test_space_clone_help(self):
        """Test space-clone command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["space-clone", "--help"])

        assert result.exit_code == 0
        assert "--name" in result.output
        assert "--to-workspace" in result.output
        assert "--to-file" in result.output

    def test_space_clone_requires_destination(self):
        """Test space-clone requires --to-workspace or --to-file."""
        runner = CliRunner()
        result = runner.invoke(
            main, ["space-clone", "space123", "--name", "Clone", "--profile", "TEST"]
        )

        assert result.exit_code != 0


class TestStateListCommand:
    """Tests for state-list command."""

    def test_state_list_help(self):
        """Test state-list command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["state-list", "--help"])

        assert result.exit_code == 0
        assert "--env" in result.output
        assert "--state-file" in result.output

    def test_state_list_no_state_file(self, tmp_path):
        """Test state-list when no state file exists."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["state-list"])

            # Should handle gracefully
            assert result.exit_code == 0
            assert "not found" in result.output.lower() or "no spaces" in result.output.lower()

    def test_state_list_with_state(self, tmp_path):
        """Test state-list with existing state."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create state file
            state_data = {
                "version": "1.0",
                "environments": {
                    "dev": {
                        "spaces": {
                            "space1": {
                                "logical_id": "space1",
                                "databricks_space_id": "db123",
                                "title": "Space 1",
                            }
                        }
                    }
                },
            }
            Path(".genie-forge.json").write_text(json.dumps(state_data))

            result = runner.invoke(main, ["state-list"])

            assert result.exit_code == 0


class TestStateShowCommand:
    """Tests for state-show command."""

    def test_state_show_help(self):
        """Test state-show command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["state-show", "--help"])

        assert result.exit_code == 0
        assert "--env" in result.output
        assert "--format" in result.output


class TestStatePullCommand:
    """Tests for state-pull command."""

    def test_state_pull_help(self):
        """Test state-pull command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["state-pull", "--help"])

        assert result.exit_code == 0
        assert "--env" in result.output
        assert "--verify-only" in result.output

    def test_state_pull_requires_env(self):
        """Test state-pull requires --env."""
        runner = CliRunner()
        result = runner.invoke(main, ["state-pull"])

        assert result.exit_code != 0


class TestStateRemoveCommand:
    """Tests for state-remove command."""

    def test_state_remove_help(self):
        """Test state-remove command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["state-remove", "--help"])

        assert result.exit_code == 0
        assert "--env" in result.output
        assert "--force" in result.output

    def test_state_remove_requires_env(self):
        """Test state-remove requires --env."""
        runner = CliRunner()
        result = runner.invoke(main, ["state-remove", "space1"])

        assert result.exit_code != 0


class TestStateImportCommand:
    """Tests for state-import command."""

    def test_state_import_help(self):
        """Test state-import command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["state-import", "--help"])

        assert result.exit_code == 0
        assert "--pattern" in result.output
        assert "--env" in result.output


class TestDriftCommand:
    """Tests for drift command."""

    def test_drift_help(self):
        """Test drift command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["drift", "--help"])

        assert result.exit_code == 0
        assert "--env" in result.output
        assert "--profile" in result.output


class TestCommandOrdering:
    """Tests for CLI command ordering."""

    def test_commands_available(self):
        """Test that all key commands are available in help."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        output = result.output

        # All key commands should be present in help
        expected_commands = [
            "init",
            "profiles",
            "whoami",
            "validate",
            "plan",
            "apply",
            "destroy",
            "status",
            "drift",
            "find",
            "space-list",
            "space-get",
            "space-create",
            "state-list",
            "state-show",
        ]

        for cmd in expected_commands:
            assert cmd in output, f"Command '{cmd}' not found in help output"

    def test_help_has_sections(self):
        """Test that help output has organized sections."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        # Help should show some commands (specific section names may vary)
        assert "Commands:" in result.output or "CORE" in result.output
