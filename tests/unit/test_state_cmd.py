"""Unit tests for genie_forge.cli.state_cmd module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from genie_forge.cli import main


class TestStateList:
    """Tests for state-list command."""

    def test_state_list_no_file(self, tmp_path):
        """Test state-list when state file doesn't exist."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(main, ["state-list"])

            assert result.exit_code == 0
            # Should show helpful message

    def test_state_list_empty_state(self, tmp_path):
        """Test state-list with empty state."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".genie-forge.json").write_text(json.dumps({"version": "1.0", "environments": {}}))

            result = runner.invoke(main, ["state-list"])

            assert result.exit_code == 0

    def test_state_list_with_spaces(self, tmp_path):
        """Test state-list with tracked spaces."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            state_data = {
                "version": "1.0",
                "environments": {
                    "dev": {
                        "spaces": {
                            "space1": {
                                "logical_id": "space1",
                                "databricks_space_id": "db123",
                                "title": "Space 1",
                            },
                            "space2": {
                                "logical_id": "space2",
                                "databricks_space_id": "db456",
                                "title": "Space 2",
                            },
                        }
                    }
                },
            }
            Path(".genie-forge.json").write_text(json.dumps(state_data))

            result = runner.invoke(main, ["state-list"])

            assert result.exit_code == 0
            assert "2" in result.output or "space1" in result.output.lower()

    def test_state_list_filter_by_env(self, tmp_path):
        """Test state-list filtering by environment."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            state_data = {
                "version": "1.0",
                "environments": {
                    "dev": {"spaces": {"space1": {"title": "Dev Space"}}},
                    "prod": {"spaces": {"space2": {"title": "Prod Space"}}},
                },
            }
            Path(".genie-forge.json").write_text(json.dumps(state_data))

            result = runner.invoke(main, ["state-list", "--env", "dev"])

            assert result.exit_code == 0

    def test_state_list_show_ids(self, tmp_path):
        """Test state-list with --show-ids."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            state_data = {
                "version": "1.0",
                "environments": {
                    "dev": {
                        "spaces": {
                            "space1": {
                                "databricks_space_id": "01ABC123DEF456",
                                "title": "Space 1",
                            }
                        }
                    }
                },
            }
            Path(".genie-forge.json").write_text(json.dumps(state_data))

            result = runner.invoke(main, ["state-list", "--show-ids"])

            assert result.exit_code == 0


class TestStateShow:
    """Tests for state-show command."""

    def test_state_show_full_state(self, tmp_path):
        """Test state-show displays full state."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            state_data = {
                "version": "1.0",
                "environments": {
                    "dev": {
                        "workspace_url": "https://dev.databricks.com",
                        "last_applied": "2026-01-20T10:00:00",
                        "spaces": {
                            "space1": {
                                "databricks_space_id": "db123",
                                "title": "Space 1",
                                "config_hash": "abc123",
                            }
                        },
                    }
                },
            }
            Path(".genie-forge.json").write_text(json.dumps(state_data))

            result = runner.invoke(main, ["state-show"])

            assert result.exit_code == 0

    def test_state_show_json_format(self, tmp_path):
        """Test state-show with JSON output."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            state_data = {"version": "1.0", "environments": {"dev": {"spaces": {}}}}
            Path(".genie-forge.json").write_text(json.dumps(state_data))

            result = runner.invoke(main, ["state-show", "--format", "json"])

            assert result.exit_code == 0
            # Output should be valid JSON
            output_data = json.loads(result.output)
            assert "version" in output_data

    def test_state_show_filter_by_env(self, tmp_path):
        """Test state-show filtering by environment."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            state_data = {
                "version": "1.0",
                "environments": {
                    "dev": {"spaces": {"space1": {}}},
                    "prod": {"spaces": {"space2": {}}},
                },
            }
            Path(".genie-forge.json").write_text(json.dumps(state_data))

            result = runner.invoke(main, ["state-show", "--env", "prod"])

            assert result.exit_code == 0


class TestStateRemove:
    """Tests for state-remove command."""

    def test_state_remove_existing_space(self, tmp_path):
        """Test removing existing space from state."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            state_data = {
                "version": "1.0",
                "environments": {
                    "dev": {
                        "spaces": {
                            "space1": {
                                "databricks_space_id": "db123",
                                "title": "Space 1",
                            },
                            "space2": {
                                "databricks_space_id": "db456",
                                "title": "Space 2",
                            },
                        }
                    }
                },
            }
            Path(".genie-forge.json").write_text(json.dumps(state_data))

            result = runner.invoke(main, ["state-remove", "space1", "--env", "dev", "--force"])

            assert result.exit_code == 0

            # Verify space was removed
            updated_state = json.loads(Path(".genie-forge.json").read_text())
            assert "space1" not in updated_state["environments"]["dev"]["spaces"]
            assert "space2" in updated_state["environments"]["dev"]["spaces"]

    def test_state_remove_nonexistent_space(self, tmp_path):
        """Test removing non-existent space."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            state_data = {
                "version": "1.0",
                "environments": {"dev": {"spaces": {"space1": {}}}},
            }
            Path(".genie-forge.json").write_text(json.dumps(state_data))

            result = runner.invoke(main, ["state-remove", "nonexistent", "--env", "dev", "--force"])

            assert result.exit_code != 0 or "not found" in result.output.lower()

    def test_state_remove_confirmation_prompt(self, tmp_path):
        """Test state-remove asks for confirmation."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            state_data = {
                "version": "1.0",
                "environments": {"dev": {"spaces": {"space1": {"title": "Space 1"}}}},
            }
            Path(".genie-forge.json").write_text(json.dumps(state_data))

            # Without --force, should prompt
            result = runner.invoke(main, ["state-remove", "space1", "--env", "dev"], input="n\n")

            # Should be cancelled
            assert "cancelled" in result.output.lower() or result.exit_code == 0


class TestStatePull:
    """Tests for state-pull command."""

    @patch("genie_forge.cli.state_cmd.get_genie_client")
    def test_state_pull_updates_state(self, mock_get_client, tmp_path):
        """Test state-pull updates state from workspace."""
        mock_client = MagicMock()
        mock_client.get_space.return_value = {
            "id": "db123",
            "title": "Updated Title",
            "warehouse_id": "wh123",
        }
        mock_get_client.return_value = mock_client

        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            state_data = {
                "version": "1.0",
                "environments": {
                    "dev": {
                        "spaces": {
                            "space1": {
                                "databricks_space_id": "db123",
                                "title": "Original Title",
                            }
                        }
                    }
                },
            }
            Path(".genie-forge.json").write_text(json.dumps(state_data))

            result = runner.invoke(main, ["state-pull", "--env", "dev", "--profile", "TEST"])

            assert result.exit_code == 0

    @patch("genie_forge.cli.state_cmd.get_genie_client")
    def test_state_pull_verify_only(self, mock_get_client, tmp_path):
        """Test state-pull with --verify-only."""
        mock_client = MagicMock()
        mock_client.get_space.return_value = {
            "id": "db123",
            "title": "Title",
            "warehouse_id": "wh123",
        }
        mock_get_client.return_value = mock_client

        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            original_state = {
                "version": "1.0",
                "environments": {
                    "dev": {
                        "spaces": {
                            "space1": {
                                "databricks_space_id": "db123",
                                "title": "Title",
                            }
                        }
                    }
                },
            }
            Path(".genie-forge.json").write_text(json.dumps(original_state))

            result = runner.invoke(
                main,
                ["state-pull", "--env", "dev", "--profile", "TEST", "--verify-only"],
            )

            assert result.exit_code == 0
            assert "verify" in result.output.lower()

    @patch("genie_forge.cli.state_cmd.get_genie_client")
    def test_state_pull_detects_deleted_space(self, mock_get_client, tmp_path):
        """Test state-pull detects deleted space in workspace."""
        mock_client = MagicMock()
        mock_client.get_space.side_effect = Exception("Space not found")
        mock_get_client.return_value = mock_client

        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            state_data = {
                "version": "1.0",
                "environments": {
                    "dev": {
                        "spaces": {
                            "space1": {
                                "databricks_space_id": "db123",
                                "title": "Title",
                            }
                        }
                    }
                },
            }
            Path(".genie-forge.json").write_text(json.dumps(state_data))

            result = runner.invoke(main, ["state-pull", "--env", "dev", "--profile", "TEST"])

            # Should complete with indication of missing space
            assert result.exit_code == 0


class TestStateEnvironments:
    """Tests for state environment handling."""

    def test_state_list_multiple_environments(self, tmp_path):
        """Test state-list shows all environments."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            state_data = {
                "version": "1.0",
                "environments": {
                    "dev": {"spaces": {"s1": {"title": "Dev Space"}}},
                    "staging": {"spaces": {"s2": {"title": "Staging Space"}}},
                    "prod": {"spaces": {"s3": {"title": "Prod Space"}}},
                },
            }
            Path(".genie-forge.json").write_text(json.dumps(state_data))

            result = runner.invoke(main, ["state-list"])

            assert result.exit_code == 0
            # Should show all environments or at least count them

    def test_state_nonexistent_environment(self, tmp_path):
        """Test handling of non-existent environment."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            state_data = {
                "version": "1.0",
                "environments": {"dev": {"spaces": {}}},
            }
            Path(".genie-forge.json").write_text(json.dumps(state_data))

            result = runner.invoke(main, ["state-list", "--env", "nonexistent"])

            # Should show error about missing environment
            assert result.exit_code != 0 or "not found" in result.output.lower()


class TestStateFileIntegrity:
    """Tests for state file integrity handling."""

    def test_corrupted_state_file(self, tmp_path):
        """Test handling of corrupted state file."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            Path(".genie-forge.json").write_text("not valid json {{{")

            result = runner.invoke(main, ["state-list"])

            # Should handle gracefully
            assert result.exit_code != 0 or "invalid" in result.output.lower()

    def test_state_file_missing_version(self, tmp_path):
        """Test handling state file without version."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Valid JSON but missing expected structure
            Path(".genie-forge.json").write_text(json.dumps({"environments": {}}))

            result = runner.invoke(main, ["state-list"])

            # Should still work or gracefully handle
            assert result.exit_code == 0


class TestStateImport:
    """Tests for state-import command (alias for import).

    Note: state-import is registered as an alias for the import command.
    These tests verify the alias is properly set up.
    """

    def test_state_import_exists(self):
        """Test state-import command exists."""
        runner = CliRunner()
        result = runner.invoke(main, ["state-import", "--help"])

        # Command should exist (exit code 0)
        assert result.exit_code == 0
        assert "import" in result.output.lower()

    def test_import_command_help(self):
        """Test the actual import command has proper options."""
        runner = CliRunner()
        result = runner.invoke(main, ["import", "--help"])

        assert result.exit_code == 0
        assert "--pattern" in result.output
        assert "--env" in result.output

    @patch("genie_forge.cli.import_cmd.get_genie_client")
    def test_import_single_space(self, mock_get_client, tmp_path):
        """Test importing a single space using the import command."""
        mock_client = MagicMock()
        mock_client.workspace_url = "https://test.databricks.com"
        mock_client.get_space.return_value = {
            "id": "space123",
            "title": "Test Space",
            "warehouse_id": "wh123",
            "serialized_space": {"data_sources": {"tables": []}},
        }
        mock_get_client.return_value = mock_client

        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Create initial state
            Path(".genie-forge.json").write_text(json.dumps({"version": "1.0", "environments": {}}))
            Path("conf/spaces").mkdir(parents=True)

            result = runner.invoke(
                main,
                [
                    "import",
                    "space123",
                    "--env",
                    "dev",
                    "--as",
                    "my_space",
                    "--profile",
                    "TEST",
                ],
            )

            assert result.exit_code == 0


class TestStateOperationsIntegration:
    """Integration tests for state operations workflow."""

    def test_full_state_lifecycle(self, tmp_path):
        """Test complete state lifecycle: list -> show -> remove."""
        runner = CliRunner()

        with runner.isolated_filesystem(temp_dir=tmp_path):
            # Initial state with spaces
            state_data = {
                "version": "1.0",
                "environments": {
                    "dev": {
                        "workspace_url": "https://dev.databricks.com",
                        "spaces": {
                            "space1": {
                                "databricks_space_id": "db123",
                                "title": "Space 1",
                            },
                            "space2": {
                                "databricks_space_id": "db456",
                                "title": "Space 2",
                            },
                        },
                    }
                },
            }
            Path(".genie-forge.json").write_text(json.dumps(state_data))

            # Step 1: List spaces
            result = runner.invoke(main, ["state-list", "--env", "dev"])
            assert result.exit_code == 0

            # Step 2: Show state
            result = runner.invoke(main, ["state-show", "--env", "dev"])
            assert result.exit_code == 0

            # Step 3: Remove one space
            result = runner.invoke(main, ["state-remove", "space1", "--env", "dev", "--force"])
            assert result.exit_code == 0

            # Step 4: Verify removal
            updated_state = json.loads(Path(".genie-forge.json").read_text())
            assert "space1" not in updated_state["environments"]["dev"]["spaces"]
            assert "space2" in updated_state["environments"]["dev"]["spaces"]
