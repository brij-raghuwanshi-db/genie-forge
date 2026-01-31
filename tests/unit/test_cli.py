"""Unit tests for genie_forge.cli."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from genie_forge.cli import OrderedGroup, main


class TestOrderedGroup:
    """Tests for OrderedGroup class."""

    def test_command_order(self):
        """Test that commands are returned in journey order."""
        group = OrderedGroup()

        # Add commands in random order
        group.add_command(MagicMock(), "apply")
        group.add_command(MagicMock(), "validate")
        group.add_command(MagicMock(), "profiles")
        group.add_command(MagicMock(), "setup-demo")

        ctx = MagicMock()
        commands = group.list_commands(ctx)

        # Should be in journey order
        expected_order = ["profiles", "setup-demo", "validate", "apply"]
        assert commands == expected_order

    def test_unknown_commands_at_end(self):
        """Test that unknown commands are listed at the end."""
        group = OrderedGroup()

        group.add_command(MagicMock(), "apply")
        group.add_command(MagicMock(), "custom-command")  # Not in COMMAND_ORDER

        ctx = MagicMock()
        commands = group.list_commands(ctx)

        # custom-command should be at the end
        assert commands[-1] == "custom-command"


class TestMainGroup:
    """Tests for main CLI group."""

    def test_main_help(self):
        """Test main help message."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Genie-Forge" in result.output
        assert "CORE WORKFLOW" in result.output

    def test_version(self):
        """Test version option."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "genie-forge" in result.output


class TestValidateCommand:
    """Tests for validate command."""

    def test_validate_help(self):
        """Test validate command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["validate", "--help"])

        assert result.exit_code == 0
        assert "--config" in result.output

    def test_validate_missing_config(self):
        """Test validate with nonexistent config."""
        runner = CliRunner()
        result = runner.invoke(main, ["validate", "--config", "/nonexistent/path"])

        assert result.exit_code != 0

    def test_validate_valid_config(self, tmp_path):
        """Test validate with valid config."""
        # Create a valid config file
        config_file = tmp_path / "test_space.yaml"
        config_file.write_text("""
version: 1
spaces:
  - space_id: test_space
    title: Test Space
    warehouse_id: test-warehouse
    data_sources:
      tables:
        - identifier: catalog.schema.table
          description:
            - "Test table"
""")

        runner = CliRunner()
        result = runner.invoke(main, ["validate", "--config", str(config_file)])

        assert result.exit_code == 0
        assert "valid" in result.output.lower() or "✓" in result.output


class TestProfilesCommand:
    """Tests for profiles command."""

    def test_profiles_help(self):
        """Test profiles command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["profiles", "--help"])

        assert result.exit_code == 0

    def test_profiles_list(self):
        """Test listing profiles."""
        import importlib

        profiles_module = importlib.import_module("genie_forge.cli.profiles")
        with patch.object(profiles_module, "list_profiles") as mock_list_profiles:
            mock_list_profiles.return_value = ["DEFAULT", "DEV", "PROD"]

            runner = CliRunner()
            result = runner.invoke(main, ["profiles"])

            assert result.exit_code == 0
            assert "DEFAULT" in result.output or "Available" in result.output


class TestStatusCommand:
    """Tests for status command."""

    def test_status_help(self):
        """Test status command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["status", "--help"])

        assert result.exit_code == 0
        assert "--env" in result.output

    def test_status_no_state(self, tmp_path):
        """Test status when no state file exists."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["status"])
            # Should handle gracefully
            assert result.exit_code == 0


class TestFindCommand:
    """Tests for find command."""

    def test_find_help(self):
        """Test find command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["find", "--help"])

        assert result.exit_code == 0
        assert "--name" in result.output
        assert "--workspace" in result.output

    def test_find_no_name(self):
        """Test find without required name option."""
        runner = CliRunner()
        result = runner.invoke(main, ["find"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()


class TestPlanCommand:
    """Tests for plan command."""

    def test_plan_help(self):
        """Test plan command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["plan", "--help"])

        assert result.exit_code == 0
        assert "--env" in result.output
        assert "--profile" in result.output


class TestApplyCommand:
    """Tests for apply command."""

    def test_apply_help(self):
        """Test apply command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["apply", "--help"])

        assert result.exit_code == 0
        assert "--env" in result.output
        assert "--auto-approve" in result.output
        assert "--dry-run" in result.output


class TestDestroyCommand:
    """Tests for destroy command."""

    def test_destroy_help(self):
        """Test destroy command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["destroy", "--help"])

        assert result.exit_code == 0
        assert "--target" in result.output
        assert "--force" in result.output

    def test_destroy_requires_target(self):
        """Test destroy requires target option."""
        runner = CliRunner()
        result = runner.invoke(main, ["destroy", "--env", "dev"])

        assert result.exit_code != 0


class TestSetupDemoCommand:
    """Tests for setup-demo command."""

    def test_setup_demo_help(self):
        """Test setup-demo command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["setup-demo", "--help"])

        assert result.exit_code == 0
        assert "--catalog" in result.output
        assert "--schema" in result.output
        assert "--warehouse-id" in result.output

    def test_setup_demo_requires_options(self):
        """Test setup-demo requires catalog, schema, warehouse-id."""
        runner = CliRunner()
        result = runner.invoke(main, ["setup-demo"])

        assert result.exit_code != 0
        # Should complain about missing required options


class TestCleanupDemoCommand:
    """Tests for cleanup-demo command."""

    def test_cleanup_demo_help(self):
        """Test cleanup-demo command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["cleanup-demo", "--help"])

        assert result.exit_code == 0
        assert "--catalog" in result.output
        assert "--execute" in result.output
        assert "--list-only" in result.output

    def test_cleanup_demo_dry_run_default(self, tmp_path):
        """Test cleanup-demo defaults to dry run."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "cleanup-demo",
                "--catalog",
                "test_cat",
                "--schema",
                "test_sch",
            ],
        )

        # Should show dry run message, not actually delete
        assert "DRY-RUN" in result.output or "would be deleted" in result.output.lower()

    def test_cleanup_demo_list_only(self):
        """Test cleanup-demo with --list-only."""
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "cleanup-demo",
                "--catalog",
                "test_cat",
                "--schema",
                "test_sch",
                "--list-only",
            ],
        )

        assert result.exit_code == 0
        # Should show SQL for manual cleanup
        assert "DROP TABLE" in result.output or "SQL" in result.output


class TestParseDestroyTargets:
    """Tests for _parse_destroy_targets function."""

    def test_parse_single_target(self):
        """Test parsing single target."""
        from genie_forge.cli.spaces import _parse_destroy_targets

        targets, excluded = _parse_destroy_targets("my_space", ["my_space", "other_space"])

        assert targets == ["my_space"]
        assert excluded == []

    def test_parse_multiple_targets(self):
        """Test parsing comma-separated targets."""
        from genie_forge.cli.spaces import _parse_destroy_targets

        targets, excluded = _parse_destroy_targets(
            "space1, space2, space3", ["space1", "space2", "space3", "space4"]
        )

        assert sorted(targets) == ["space1", "space2", "space3"]
        assert excluded == []

    def test_parse_wildcard_all(self):
        """Test parsing wildcard for all spaces."""
        from genie_forge.cli.spaces import _parse_destroy_targets

        targets, excluded = _parse_destroy_targets("*", ["space1", "space2", "space3"])

        assert sorted(targets) == ["space1", "space2", "space3"]
        assert excluded == []

    def test_parse_wildcard_with_exclusion(self):
        """Test parsing wildcard with exclusion."""
        from genie_forge.cli.spaces import _parse_destroy_targets

        targets, excluded = _parse_destroy_targets(
            "* [keep_this]", ["space1", "space2", "keep_this"]
        )

        assert sorted(targets) == ["space1", "space2"]
        assert excluded == ["keep_this"]

    def test_parse_multiple_exclusions(self):
        """Test parsing with multiple exclusions."""
        from genie_forge.cli.spaces import _parse_destroy_targets

        targets, excluded = _parse_destroy_targets(
            "* [keep1, keep2]", ["space1", "keep1", "keep2", "space2"]
        )

        assert sorted(targets) == ["space1", "space2"]
        assert sorted(excluded) == ["keep1", "keep2"]

    def test_parse_mixed_pattern(self):
        """Test parsing mixed pattern with inline exclusions."""
        from genie_forge.cli.spaces import _parse_destroy_targets

        targets, excluded = _parse_destroy_targets(
            "space1, [skip], space2", ["space1", "space2", "skip", "space3"]
        )

        assert sorted(targets) == ["space1", "space2"]
        assert excluded == ["skip"]


class TestImportCommand:
    """Tests for import command."""

    def test_import_help(self):
        """Test import command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["import", "--help"])

        assert result.exit_code == 0
        assert "--pattern" in result.output
        assert "--env" in result.output
        assert "--as" in result.output

    def test_import_requires_space_id_or_pattern(self):
        """Test import requires either space_id or --pattern."""
        runner = CliRunner()
        result = runner.invoke(main, ["import", "--env", "dev"])

        assert result.exit_code == 1
        assert "Either SPACE_ID or --pattern is required" in result.output

    def test_import_cannot_use_both_space_id_and_pattern(self):
        """Test import cannot use both space_id and --pattern."""
        runner = CliRunner()
        result = runner.invoke(main, ["import", "space123", "--pattern", "Sales*", "--env", "dev"])

        assert result.exit_code == 1
        assert "Cannot specify both SPACE_ID and --pattern" in result.output


class TestSanitizeLogicalId:
    """Tests for _sanitize_logical_id function."""

    def test_simple_title(self):
        """Test simple title conversion."""
        from genie_forge.cli.import_cmd import _sanitize_logical_id

        assert _sanitize_logical_id("Sales Analytics") == "sales_analytics"

    def test_special_characters(self):
        """Test title with special characters."""
        from genie_forge.cli.import_cmd import _sanitize_logical_id

        assert _sanitize_logical_id("HR - Employee Dashboard!") == "hr_employee_dashboard"

    def test_numeric_prefix(self):
        """Test title starting with number."""
        from genie_forge.cli.import_cmd import _sanitize_logical_id

        result = _sanitize_logical_id("2024 Sales Report")
        assert result.startswith("space_")
        assert not result[0].isdigit()

    def test_empty_result(self):
        """Test title that becomes empty."""
        from genie_forge.cli.import_cmd import _sanitize_logical_id

        assert _sanitize_logical_id("!!!") == "imported_space"
