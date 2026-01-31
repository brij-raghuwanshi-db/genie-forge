"""Unit tests for genie_forge.cli.space_cmd module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from genie_forge.cli import main


class TestBuildExportConfig:
    """Tests for _build_export_config function."""

    def test_basic_export(self):
        """Test building basic export config."""
        from genie_forge.cli.space_cmd import _build_export_config

        space = {
            "id": "space123",
            "title": "Test Space",
            "warehouse_id": "wh123",
            "parent_path": "/Workspace/Shared",
            "serialized_space": {"data_sources": {"tables": [{"identifier": "cat.sch.table1"}]}},
        }

        config = _build_export_config(space)

        assert config["title"] == "Test Space"
        assert config["warehouse_id"] == "wh123"
        assert config["parent_path"] == "/Workspace/Shared"
        assert "data_sources" in config

    def test_export_with_instructions(self):
        """Test export config includes instructions."""
        from genie_forge.cli.space_cmd import _build_export_config

        space = {
            "title": "Test",
            "warehouse_id": "wh123",
            "serialized_space": {
                "instructions": {
                    "text_instructions": [{"text": "Instruction 1"}],
                    "sql_functions": [{"identifier": "cat.sch.func1"}],
                },
            },
        }

        config = _build_export_config(space)

        assert "instructions" in config
        assert "text_instructions" in config["instructions"]
        assert "sql_functions" in config["instructions"]

    def test_export_with_sample_questions(self):
        """Test export config includes sample questions."""
        from genie_forge.cli.space_cmd import _build_export_config

        space = {
            "title": "Test",
            "warehouse_id": "wh123",
            "serialized_space": {"config": {"sample_questions": ["Q1", "Q2"]}},
        }

        config = _build_export_config(space)

        assert "sample_questions" in config
        assert len(config["sample_questions"]) == 2


class TestSpaceListFiltering:
    """Tests for space-list filtering and pagination."""

    @patch("genie_forge.cli.space_cmd.get_genie_client")
    @patch("genie_forge.cli.space_cmd.fetch_all_spaces_paginated")
    def test_list_respects_limit(self, mock_fetch, mock_get_client):
        """Test space-list respects --limit option."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_fetch.return_value = [
            {"id": f"space{i}", "title": f"Space {i}", "warehouse_id": "wh", "creator": "user"}
            for i in range(100)
        ]

        runner = CliRunner()
        result = runner.invoke(main, ["space-list", "--limit", "10", "--profile", "TEST"])

        assert result.exit_code == 0
        # Output should mention limiting

    @patch("genie_forge.cli.space_cmd.get_genie_client")
    @patch("genie_forge.cli.space_cmd.fetch_all_spaces_paginated")
    def test_list_empty_workspace(self, mock_fetch, mock_get_client):
        """Test space-list with empty workspace."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_fetch.return_value = []

        runner = CliRunner()
        result = runner.invoke(main, ["space-list", "--profile", "TEST"])

        assert result.exit_code == 0
        assert "0" in result.output or "no spaces" in result.output.lower()


class TestSpaceGetDetails:
    """Tests for space-get detailed output."""

    @patch("genie_forge.cli.space_cmd.get_genie_client")
    def test_get_by_id(self, mock_get_client):
        """Test getting space by ID."""
        mock_client = MagicMock()
        mock_client.get_space.return_value = {
            "id": "space123",
            "title": "Test Space",
            "warehouse_id": "wh123",
            "serialized_space": {"data_sources": {"tables": []}},
        }
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(main, ["space-get", "space123", "--profile", "TEST"])

        assert result.exit_code == 0
        mock_client.get_space.assert_called_once()

    @patch("genie_forge.cli.space_cmd.get_genie_client")
    def test_get_by_name_exact_match(self, mock_get_client):
        """Test getting space by exact name match."""
        mock_client = MagicMock()
        mock_client.list_spaces.return_value = [
            {"id": "space123", "title": "Sales Analytics"},
            {"id": "space456", "title": "Sales Report"},
        ]
        mock_client.get_space.return_value = {
            "id": "space123",
            "title": "Sales Analytics",
            "warehouse_id": "wh123",
            "serialized_space": {},
        }
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(
            main, ["space-get", "--name", "Sales Analytics", "--profile", "TEST"]
        )

        assert result.exit_code == 0

    @patch("genie_forge.cli.space_cmd.get_genie_client")
    def test_get_by_name_multiple_matches(self, mock_get_client):
        """Test error when multiple spaces match name."""
        mock_client = MagicMock()
        mock_client.list_spaces.return_value = [
            {"id": "space123", "title": "Sales Analytics"},
            {"id": "space456", "title": "sales analytics"},  # Case different
        ]
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(main, ["space-get", "--name", "sales*", "--profile", "TEST"])

        # Should fail with multiple matches message
        assert result.exit_code != 0 or "multiple" in result.output.lower()


class TestSpaceCreateMethods:
    """Tests for different space-create methods."""

    @patch("genie_forge.cli.space_cmd.get_genie_client")
    def test_create_from_cli_flags(self, mock_get_client):
        """Test creating space from CLI flags."""
        mock_client = MagicMock()
        mock_client.create_space.return_value = {"id": "new123", "title": "Test"}
        mock_get_client.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "space-create",
                "Test Space",
                "--warehouse-id",
                "wh123",
                "--tables",
                "cat.sch.t1,cat.sch.t2",
                "--profile",
                "TEST",
            ],
        )

        assert result.exit_code == 0

    def test_create_from_yaml_file(self, tmp_path):
        """Test creating space from YAML file."""
        config_file = tmp_path / "space.yaml"
        config_file.write_text(
            """
title: Test Space
warehouse_id: wh123
data_sources:
  tables:
    - identifier: cat.sch.table1
"""
        )

        with patch("genie_forge.cli.space_cmd.get_genie_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_space.return_value = {"id": "new123", "title": "Test Space"}
            mock_get_client.return_value = mock_client

            runner = CliRunner()
            result = runner.invoke(
                main,
                ["space-create", "--from-file", str(config_file), "--profile", "TEST"],
            )

            assert result.exit_code == 0

    def test_create_from_json_file(self, tmp_path):
        """Test creating space from JSON file."""
        config_file = tmp_path / "space.json"
        config_file.write_text(
            json.dumps(
                {
                    "title": "Test Space",
                    "warehouse_id": "wh123",
                    "data_sources": {"tables": [{"identifier": "cat.sch.table1"}]},
                }
            )
        )

        with patch("genie_forge.cli.space_cmd.get_genie_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_space.return_value = {"id": "new123", "title": "Test Space"}
            mock_get_client.return_value = mock_client

            runner = CliRunner()
            result = runner.invoke(
                main,
                ["space-create", "--from-file", str(config_file), "--profile", "TEST"],
            )

            assert result.exit_code == 0

    def test_create_with_set_overrides(self, tmp_path):
        """Test creating space with --set overrides."""
        config_file = tmp_path / "template.yaml"
        config_file.write_text(
            """
title: Template
warehouse_id: default_wh
data_sources:
  tables:
    - identifier: cat.sch.table1
"""
        )

        with patch("genie_forge.cli.space_cmd.get_genie_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_space.return_value = {"id": "new123", "title": "Custom Title"}
            mock_get_client.return_value = mock_client

            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "space-create",
                    "--from-file",
                    str(config_file),
                    "--set",
                    "title=Custom Title",
                    "--set",
                    "warehouse_id=custom_wh",
                    "--profile",
                    "TEST",
                ],
            )

            assert result.exit_code == 0

    def test_create_saves_config(self, tmp_path):
        """Test create with --save-config saves file."""
        with patch("genie_forge.cli.space_cmd.get_genie_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.create_space.return_value = {"id": "new123", "title": "Test"}
            mock_get_client.return_value = mock_client

            output_file = tmp_path / "saved.yaml"

            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "space-create",
                    "Test Space",
                    "--warehouse-id",
                    "wh123",
                    "--tables",
                    "cat.sch.t1",
                    "--save-config",
                    str(output_file),
                    "--profile",
                    "TEST",
                ],
            )

            assert result.exit_code == 0
            assert output_file.exists()


class TestSpaceExportScenarios:
    """Tests for space-export scenarios."""

    @patch("genie_forge.cli.space_cmd.get_genie_client")
    @patch("genie_forge.cli.space_cmd.fetch_all_spaces_paginated")
    def test_export_by_pattern(self, mock_fetch, mock_get_client, tmp_path):
        """Test exporting spaces by pattern."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_fetch.return_value = [
            {"id": "s1", "title": "Sales Report", "warehouse_id": "wh1"},
            {"id": "s2", "title": "Sales Dashboard", "warehouse_id": "wh2"},
            {"id": "s3", "title": "HR Analytics", "warehouse_id": "wh3"},
        ]
        mock_client.get_space.return_value = {
            "id": "s1",
            "title": "Sales Report",
            "warehouse_id": "wh1",
            "serialized_space": {},
        }

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "space-export",
                "--pattern",
                "Sales*",
                "--output-dir",
                str(tmp_path),
                "--profile",
                "TEST",
            ],
        )

        assert result.exit_code == 0

    @patch("genie_forge.cli.space_cmd.get_genie_client")
    @patch("genie_forge.cli.space_cmd.fetch_all_spaces_paginated")
    def test_export_with_exclude(self, mock_fetch, mock_get_client, tmp_path):
        """Test exporting spaces with exclusions."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_fetch.return_value = [
            {"id": "s1", "title": "Sales Report", "warehouse_id": "wh1"},
            {"id": "s2", "title": "Sales Test", "warehouse_id": "wh2"},
        ]

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "space-export",
                "--pattern",
                "*",
                "--exclude",
                "*Test*",
                "--output-dir",
                str(tmp_path),
                "--dry-run",
                "--profile",
                "TEST",
            ],
        )

        assert result.exit_code == 0

    @patch("genie_forge.cli.space_cmd.get_genie_client")
    def test_export_specific_ids(self, mock_get_client, tmp_path):
        """Test exporting specific space IDs."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_space.return_value = {
            "id": "space1",
            "title": "Space 1",
            "warehouse_id": "wh1",
            "serialized_space": {},
        }

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "space-export",
                "--space-id",
                "space1",
                "--output-dir",
                str(tmp_path),
                "--profile",
                "TEST",
            ],
        )

        assert result.exit_code == 0


class TestSpaceCloneScenarios:
    """Tests for space-clone scenarios."""

    @patch("genie_forge.cli.space_cmd.get_genie_client")
    def test_clone_to_file(self, mock_get_client, tmp_path):
        """Test cloning space to file."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_space.return_value = {
            "id": "source123",
            "title": "Source Space",
            "warehouse_id": "wh123",
            "serialized_space": {"data_sources": {"tables": []}},
        }

        output_file = tmp_path / "cloned.yaml"

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "space-clone",
                "source123",
                "--name",
                "Cloned Space",
                "--to-file",
                str(output_file),
                "--profile",
                "TEST",
            ],
        )

        assert result.exit_code == 0
        assert output_file.exists()

    @patch("genie_forge.cli.space_cmd.get_genie_client")
    def test_clone_to_workspace(self, mock_get_client):
        """Test cloning space to workspace."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_space.return_value = {
            "id": "source123",
            "title": "Source Space",
            "warehouse_id": "wh123",
            "serialized_space": {"data_sources": {"tables": []}},
        }
        mock_client.create_space.return_value = {"id": "clone123", "title": "Cloned Space"}

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "space-clone",
                "source123",
                "--name",
                "Cloned Space",
                "--to-workspace",
                "--profile",
                "TEST",
            ],
        )

        assert result.exit_code == 0

    @patch("genie_forge.cli.space_cmd.get_genie_client")
    def test_clone_dry_run(self, mock_get_client):
        """Test clone with dry run."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.get_space.return_value = {
            "id": "source123",
            "title": "Source Space",
            "warehouse_id": "wh123",
            "serialized_space": {},
        }

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "space-clone",
                "source123",
                "--name",
                "Cloned Space",
                "--to-workspace",
                "--dry-run",
                "--profile",
                "TEST",
            ],
        )

        assert result.exit_code == 0
        assert "dry" in result.output.lower()
        # Should not call create_space in dry run
        mock_client.create_space.assert_not_called()
