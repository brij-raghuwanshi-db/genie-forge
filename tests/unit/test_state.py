"""Unit tests for genie_forge.state."""

import json
from pathlib import Path
from unittest.mock import MagicMock

from genie_forge.models import PlanAction, SpaceConfig
from genie_forge.state import StateManager


class TestStateManager:
    """Tests for StateManager."""

    def test_init_creates_default_state(self, temp_dir: Path):
        """Test that init creates default state when file doesn't exist."""
        state_file = temp_dir / ".genie-forge.json"
        manager = StateManager(state_file=state_file, project_id="test")

        state = manager.state
        assert state.project_id == "test"
        assert len(state.environments) == 0

    def test_load_existing_state(self, sample_state_file: Path):
        """Test loading an existing state file."""
        manager = StateManager(state_file=sample_state_file)

        state = manager.state
        assert state.project_id == "test_project"
        assert "dev" in state.environments
        assert "test_space" in state.environments["dev"].spaces

    def test_save_state(self, temp_dir: Path):
        """Test saving state to file."""
        state_file = temp_dir / ".genie-forge.json"
        manager = StateManager(state_file=state_file, project_id="test")

        # Trigger state creation
        _ = manager.state

        # Add some data
        manager._get_or_create_env_state("dev", "https://test.com")
        manager._save_state()

        # Verify file was created
        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["project_id"] == "test"
        assert "dev" in data["environments"]


class TestPlan:
    """Tests for plan operation."""

    def test_plan_new_space(self, temp_dir: Path, mock_workspace_client: MagicMock):
        """Test planning a new space creation."""
        from genie_forge.client import GenieClient

        state_file = temp_dir / ".genie-forge.json"
        manager = StateManager(state_file=state_file)

        client = GenieClient(client=mock_workspace_client)
        config = SpaceConfig.minimal(
            space_id="new_space",
            title="New Space",
            warehouse_id="wh123",
            tables=["c.s.t"],
        )

        plan = manager.plan([config], client, env="dev")

        assert len(plan.creates) == 1
        assert plan.creates[0].logical_id == "new_space"
        assert plan.creates[0].action == PlanAction.CREATE

    def test_plan_existing_unchanged(
        self, sample_state_file: Path, mock_workspace_client: MagicMock
    ):
        """Test planning when space exists and is unchanged."""
        from genie_forge.client import GenieClient

        manager = StateManager(state_file=sample_state_file)
        client = GenieClient(client=mock_workspace_client)

        # Create config with same hash as in state
        config = SpaceConfig.minimal(
            space_id="test_space",
            title="Test Space",
            warehouse_id="test_warehouse_123",
            tables=["catalog.schema.table"],
        )

        # Update state to match config hash
        manager.state.environments["dev"].spaces["test_space"].applied_hash = config.config_hash()
        manager.state.environments["dev"].spaces["test_space"].config_hash = config.config_hash()

        plan = manager.plan([config], client, env="dev")

        assert len(plan.no_changes) == 1
        assert plan.has_changes is False

    def test_plan_existing_changed(self, sample_state_file: Path, mock_workspace_client: MagicMock):
        """Test planning when space exists but config changed."""
        from genie_forge.client import GenieClient

        manager = StateManager(state_file=sample_state_file)
        client = GenieClient(client=mock_workspace_client)

        # Create config with different content
        config = SpaceConfig.minimal(
            space_id="test_space",
            title="Changed Title",  # Different title
            warehouse_id="test_warehouse_123",
            tables=["catalog.schema.table"],
        )

        plan = manager.plan([config], client, env="dev")

        assert len(plan.updates) == 1
        assert plan.updates[0].logical_id == "test_space"


class TestApply:
    """Tests for apply operation."""

    def test_apply_dry_run(self, temp_dir: Path, mock_workspace_client: MagicMock):
        """Test dry run doesn't make changes."""
        from genie_forge.client import GenieClient

        state_file = temp_dir / ".genie-forge.json"
        manager = StateManager(state_file=state_file)

        client = GenieClient(client=mock_workspace_client)
        config = SpaceConfig.minimal(
            space_id="new_space",
            title="New Space",
            warehouse_id="wh123",
            tables=["c.s.t"],
        )

        plan = manager.plan([config], client, env="dev")
        results = manager.apply(plan, client, dry_run=True)

        assert results["dry_run"] is True
        assert len(results["created"]) == 1

        # Verify no state was saved
        assert not state_file.exists()

    def test_apply_create(self, temp_dir: Path, mock_workspace_client: MagicMock):
        """Test applying a create action."""
        from genie_forge.client import GenieClient

        state_file = temp_dir / ".genie-forge.json"
        manager = StateManager(state_file=state_file)

        client = GenieClient(client=mock_workspace_client)
        config = SpaceConfig.minimal(
            space_id="new_space",
            title="New Space",
            warehouse_id="wh123",
            tables=["c.s.t"],
        )

        plan = manager.plan([config], client, env="dev")
        results = manager.apply(plan, client, dry_run=False)

        assert len(results["created"]) == 1
        assert "new_space" in manager.state.environments["dev"].spaces
        assert state_file.exists()


class TestDestroy:
    """Tests for destroy operation."""

    def test_destroy_existing_space(
        self, sample_state_file: Path, mock_workspace_client: MagicMock
    ):
        """Test destroying an existing space."""
        from genie_forge.client import GenieClient

        manager = StateManager(state_file=sample_state_file)
        client = GenieClient(client=mock_workspace_client)

        result = manager.destroy("test_space", client, env="dev")

        assert result["success"] is True
        assert "test_space" not in manager.state.environments["dev"].spaces

    def test_destroy_nonexistent_space(
        self, sample_state_file: Path, mock_workspace_client: MagicMock
    ):
        """Test destroying a space that doesn't exist in state."""
        from genie_forge.client import GenieClient

        manager = StateManager(state_file=sample_state_file)
        client = GenieClient(client=mock_workspace_client)

        result = manager.destroy("nonexistent", client, env="dev")

        assert result["success"] is False
        assert "not found" in result["error"]

    def test_destroy_dry_run(self, sample_state_file: Path, mock_workspace_client: MagicMock):
        """Test destroy dry run."""
        from genie_forge.client import GenieClient

        manager = StateManager(state_file=sample_state_file)
        client = GenieClient(client=mock_workspace_client)

        result = manager.destroy("test_space", client, env="dev", dry_run=True)

        assert result["success"] is True
        assert result["dry_run"] is True
        # Space should still exist
        assert "test_space" in manager.state.environments["dev"].spaces


class TestStatus:
    """Tests for status operation."""

    def test_status_existing_env(self, sample_state_file: Path):
        """Test getting status for existing environment."""
        manager = StateManager(state_file=sample_state_file)

        status = manager.status(env="dev")

        assert status["environment"] == "dev"
        assert status["total"] == 1
        assert len(status["spaces"]) == 1
        assert status["spaces"][0]["logical_id"] == "test_space"

    def test_status_nonexistent_env(self, sample_state_file: Path):
        """Test getting status for non-existent environment."""
        manager = StateManager(state_file=sample_state_file)

        status = manager.status(env="prod")

        assert status["environment"] == "prod"
        assert status["total"] == 0
        assert len(status["spaces"]) == 0


class TestDriftDetection:
    """Tests for drift detection."""

    def test_detect_drift_no_drift(self, sample_state_file: Path, mock_workspace_client: MagicMock):
        """Test drift detection when no drift exists."""
        from genie_forge.client import GenieClient

        # Reset side_effect and configure mock to return matching space
        mock_workspace_client.api_client.do.side_effect = None
        mock_workspace_client.api_client.do.return_value = {
            "id": "db_space_123",
            "title": "Test Space",  # Same as in state
            "warehouse_id": "wh_123",
        }

        manager = StateManager(state_file=sample_state_file)
        client = GenieClient(client=mock_workspace_client)

        result = manager.detect_drift(client=client, env="dev")

        assert result["has_drift"] is False
        assert len(result["synced"]) == 1
        assert len(result["drifted"]) == 0
        assert len(result["deleted"]) == 0

    def test_detect_drift_title_changed(
        self, sample_state_file: Path, mock_workspace_client: MagicMock
    ):
        """Test drift detection when title has changed."""
        from genie_forge.client import GenieClient

        # Reset side_effect and configure mock to return space with different title
        mock_workspace_client.api_client.do.side_effect = None
        mock_workspace_client.api_client.do.return_value = {
            "id": "db_space_123",
            "title": "Modified Title",  # Different from state
            "warehouse_id": "wh_123",
        }

        manager = StateManager(state_file=sample_state_file)
        client = GenieClient(client=mock_workspace_client)

        result = manager.detect_drift(client=client, env="dev")

        assert result["has_drift"] is True
        assert len(result["drifted"]) == 1
        assert "Title changed" in result["drifted"][0]["changes"][0]

    def test_detect_drift_space_deleted(
        self, sample_state_file: Path, mock_workspace_client: MagicMock
    ):
        """Test drift detection when space was deleted from workspace."""
        from genie_forge.client import GenieClient

        # Configure mock to raise error (space not found)
        mock_workspace_client.api_client.do.side_effect = Exception("Space not found")

        manager = StateManager(state_file=sample_state_file)
        client = GenieClient(client=mock_workspace_client)

        result = manager.detect_drift(client=client, env="dev")

        assert result["has_drift"] is True
        assert len(result["deleted"]) == 1
        assert result["deleted"][0]["logical_id"] == "test_space"

    def test_detect_drift_nonexistent_env(
        self, sample_state_file: Path, mock_workspace_client: MagicMock
    ):
        """Test drift detection for non-existent environment."""
        from genie_forge.client import GenieClient

        manager = StateManager(state_file=sample_state_file)
        client = GenieClient(client=mock_workspace_client)

        result = manager.detect_drift(client=client, env="nonexistent")

        assert "error" in result
        assert "not found" in result["error"]


class TestImportSpace:
    """Tests for import_space method."""

    def test_import_space_new_env(self, temp_dir: Path):
        """Test importing a space to a new environment."""
        state_file = temp_dir / ".genie-forge.json"
        manager = StateManager(state_file=state_file, project_id="test")

        config = SpaceConfig.minimal(
            space_id="imported_space",
            title="Imported Space",
            warehouse_id="wh_123",
            tables=["cat.sch.tbl"],
        )

        result = manager.import_space(
            config=config,
            databricks_space_id="db_space_456",
            env="prod",
            workspace_url="https://test.databricks.com",
        )

        assert result["success"] is True
        assert result["logical_id"] == "imported_space"
        assert result["databricks_space_id"] == "db_space_456"

        # Verify state was updated
        assert "prod" in manager.state.environments
        assert "imported_space" in manager.state.environments["prod"].spaces

        space_state = manager.state.environments["prod"].spaces["imported_space"]
        assert space_state.databricks_space_id == "db_space_456"
        assert space_state.status.value == "APPLIED"

    def test_import_space_existing_env(self, sample_state_file: Path):
        """Test importing a space to existing environment."""
        manager = StateManager(state_file=sample_state_file)

        config = SpaceConfig.minimal(
            space_id="another_space",
            title="Another Space",
            warehouse_id="wh_789",
            tables=["cat.sch.tbl2"],
        )

        result = manager.import_space(
            config=config,
            databricks_space_id="db_space_789",
            env="dev",
        )

        assert result["success"] is True
        # Original space should still exist
        assert "test_space" in manager.state.environments["dev"].spaces
        # New space should be added
        assert "another_space" in manager.state.environments["dev"].spaces


class TestSerializerFromApiToConfig:
    """Tests for serializer.from_api_to_config method."""

    def test_basic_conversion(self):
        """Test basic API response to SpaceConfig conversion."""
        from genie_forge.serializer import SpaceSerializer

        response = {
            "id": "db_123",
            "title": "Test Space",
            "warehouse_id": "wh_456",
            "parent_path": "/Workspace/Shared",
            "serialized_space": {
                "version": 2,
                "config": {"sample_questions": [{"id": "sq1", "question": ["What is sales?"]}]},
                "data_sources": {
                    "tables": [
                        {
                            "identifier": "cat.sch.sales",
                            "description": ["Sales data"],
                            "column_configs": [],
                        }
                    ]
                },
                "instructions": {
                    "text_instructions": [{"id": "ti1", "content": ["Be helpful"]}],
                    "example_question_sqls": [],
                    "sql_functions": [],
                    "join_specs": [],
                },
            },
        }

        serializer = SpaceSerializer()
        config = serializer.from_api_to_config(response, "my_space")

        assert config.space_id == "my_space"
        assert config.title == "Test Space"
        assert config.warehouse_id == "wh_456"
        assert config.parent_path == "/Workspace/Shared"
        # sample_questions are now SampleQuestion objects
        assert len(config.sample_questions) == 1
        assert config.sample_questions[0].id == "sq1"
        assert config.sample_questions[0].question == ["What is sales?"]
        assert len(config.data_sources.tables) == 1
        assert config.data_sources.tables[0].identifier == "cat.sch.sales"
        assert len(config.instructions.text_instructions) == 1
        assert config.instructions.text_instructions[0].id == "ti1"

    def test_missing_title_raises_error(self):
        """Test that missing title raises SerializerError."""
        from genie_forge.serializer import SerializerError, SpaceSerializer

        response = {"warehouse_id": "wh_456", "serialized_space": {}}

        serializer = SpaceSerializer()
        try:
            serializer.from_api_to_config(response, "my_space")
            assert False, "Should have raised SerializerError"
        except SerializerError as e:
            assert "title" in str(e).lower()

    def test_missing_warehouse_raises_error(self):
        """Test that missing warehouse_id raises SerializerError."""
        from genie_forge.serializer import SerializerError, SpaceSerializer

        response = {"title": "Test", "serialized_space": {}}

        serializer = SpaceSerializer()
        try:
            serializer.from_api_to_config(response, "my_space")
            assert False, "Should have raised SerializerError"
        except SerializerError as e:
            assert "warehouse" in str(e).lower()
