"""Pytest configuration and fixtures for Genie-Forge tests."""

import json
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_dict() -> dict:
    """Sample configuration dictionary using API version 2 format."""
    return {
        "version": 2,
        "spaces": [
            {
                "space_id": "test_space",
                "title": "Test Space",
                "warehouse_id": "test_warehouse_123",
                "sample_questions": [
                    {"id": "sq1", "question": ["What is test?"]},
                ],
                "data_sources": {
                    "tables": [
                        {
                            "identifier": "catalog.schema.table",
                            "description": ["Test table"],
                            "column_configs": [
                                {
                                    "column_name": "id",
                                    "description": ["Primary key"],
                                    "synonyms": ["identifier"],
                                    "enable_format_assistance": True,
                                    "enable_entity_matching": False,
                                }
                            ],
                        }
                    ]
                },
                "instructions": {
                    "text_instructions": [{"id": "ti1", "content": ["Always filter by date"]}],
                    "example_question_sqls": [
                        {
                            "id": "ex1",
                            "question": ["Count rows"],
                            "sql": ["SELECT COUNT(*) FROM table"],
                            "parameters": [],
                            "usage_guidance": ["Use for counting records"],
                        }
                    ],
                    "sql_functions": [
                        {"identifier": "catalog.schema.func", "description": "Test function"}
                    ],
                    "join_specs": [
                        {
                            "id": "js1",
                            "left": {"identifier": "catalog.schema.left", "alias": "left"},
                            "right": {"identifier": "catalog.schema.right", "alias": "right"},
                            "sql": ["left.id = right.id"],
                            "instruction": ["Standard join"],
                        }
                    ],
                    "sql_snippets": {
                        "filters": [
                            {
                                "id": "f1",
                                "sql": ["status = 'active'"],
                                "display_name": "Active Only",
                                "instruction": ["Filter to active records"],
                                "synonyms": ["active", "live"],
                            }
                        ],
                        "expressions": [],
                        "measures": [],
                    },
                },
            }
        ],
    }


@pytest.fixture
def sample_yaml_file(temp_dir: Path, sample_config_dict: dict) -> Path:
    """Create a sample YAML config file."""
    import yaml

    file_path = temp_dir / "test_config.yaml"
    file_path.write_text(yaml.dump(sample_config_dict))
    return file_path


@pytest.fixture
def sample_json_file(temp_dir: Path, sample_config_dict: dict) -> Path:
    """Create a sample JSON config file."""
    file_path = temp_dir / "test_config.json"
    file_path.write_text(json.dumps(sample_config_dict, indent=2))
    return file_path


@pytest.fixture
def mock_workspace_client() -> MagicMock:
    """Create a mock WorkspaceClient."""
    mock_client = MagicMock()

    # Mock current_user.me()
    mock_user = MagicMock()
    mock_user.user_name = "test@example.com"
    mock_user.id = "user123"
    mock_client.current_user.me.return_value = mock_user

    # Mock config
    mock_client.config.host = "https://test.databricks.com"
    mock_client.config.auth_type = "pat"

    # Mock api_client.do()
    def mock_do(method: str, path: str, **kwargs) -> dict:
        if method == "GET" and path == "/api/2.0/genie/spaces":
            return {"spaces": []}
        elif method == "POST" and path == "/api/2.0/genie/spaces":
            return {"space": {"id": "new_space_123"}}
        elif method == "PATCH":
            return {"id": "updated_space"}
        elif method == "DELETE":
            return {}
        return {}

    mock_client.api_client.do = MagicMock(side_effect=mock_do)

    return mock_client


@pytest.fixture
def sample_state_dict() -> dict:
    """Sample state file dictionary."""
    return {
        "version": "1.0",
        "project_id": "test_project",
        "project_name": "Test Project",
        "created_at": "2026-01-25T10:00:00",
        "environments": {
            "dev": {
                "workspace_url": "https://dev.databricks.com",
                "last_applied": "2026-01-25T12:00:00",
                "spaces": {
                    "test_space": {
                        "logical_id": "test_space",
                        "databricks_space_id": "db_space_123",
                        "title": "Test Space",
                        "config_hash": "abc123",
                        "applied_hash": "abc123",
                        "status": "APPLIED",
                        "last_applied": "2026-01-25T12:00:00",
                        "error": None,
                    }
                },
            }
        },
    }


@pytest.fixture
def sample_state_file(temp_dir: Path, sample_state_dict: dict) -> Path:
    """Create a sample state file."""
    file_path = temp_dir / ".genie-forge.json"
    file_path.write_text(json.dumps(sample_state_dict, indent=2))
    return file_path
