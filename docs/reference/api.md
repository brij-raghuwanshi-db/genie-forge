---
title: API Reference
description: Python API documentation for Genie-Forge
---

# API Reference

Genie-Forge provides a Python API for programmatic control over Genie space management.

## Core Classes

### GenieClient

::: genie_forge.client.GenieClient
    options:
      show_root_heading: true
      show_source: true
      members:
        - create_space
        - get_space
        - update_space
        - delete_space
        - list_spaces

### StateManager

::: genie_forge.state.StateManager
    options:
      show_root_heading: true
      show_source: true

## Models

### SpaceConfig

::: genie_forge.models.SpaceConfig
    options:
      show_root_heading: true
      members:
        - title
        - description
        - warehouse_id
        - tables
        - instructions

#### SpaceConfig Utility Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `config_hash()` | `str` | Generate a consistent hash of the configuration for change detection |
| `get_table_identifiers()` | `list[str]` | Extract all table identifiers from the config |
| `get_sample_questions_as_objects()` | `list[SampleQuestion]` | Convert mixed-format sample questions to objects |

```python
# Example usage
config = SpaceConfig(...)

# Check if config changed
old_hash = config.config_hash()
# ... modify config ...
if config.config_hash() != old_hash:
    print("Config changed!")

# List all tables
tables = config.get_table_identifiers()
# Returns: ["catalog.schema.table1", "catalog.schema.table2"]
```

### Plan

::: genie_forge.models.Plan
    options:
      show_root_heading: true

#### Plan Utility Properties

| Property | Type | Description |
|----------|------|-------------|
| `has_changes` | `bool` | `True` if plan has any creates, updates, or deletes |
| `creates` | `list` | Spaces to be created |
| `updates` | `list` | Spaces to be updated |
| `deletes` | `list` | Spaces to be deleted |
| `unchanged` | `list` | Spaces with no changes |

```python
# Example usage
plan = state_manager.plan(configs, client)

if plan.has_changes:
    print(f"Creating: {len(plan.creates)} spaces")
    print(f"Updating: {len(plan.updates)} spaces")
    print(f"Deleting: {len(plan.deletes)} spaces")
    
    # Print summary
    print(plan.summary())
```

### ProjectState

::: genie_forge.models.ProjectState
    options:
      show_root_heading: true

## Utilities

### Environment Detection

::: genie_forge.utils
    options:
      show_root_heading: true
      members:
        - is_running_on_databricks
        - is_running_in_notebook
        - get_databricks_runtime_version

### Path Management

::: genie_forge.utils.ProjectPaths
    options:
      show_root_heading: true
      show_source: true

### Volume Utilities

::: genie_forge.utils
    options:
      members:
        - get_volume_path
        - is_volume_path
        - parse_volume_path
        - ensure_directory
        - sanitize_name

### Serialization

Convert between API responses and YAML configuration:

```python
from genie_forge import space_to_yaml, GenieClient

client = GenieClient(profile="MY_PROFILE")

# Export a space to YAML
space = client.get_space("01abc123def456")
yaml_content = space_to_yaml(space)

# Save to file
from pathlib import Path
Path("exported_space.yaml").write_text(yaml_content)
```

::: genie_forge.serializer.space_to_yaml
    options:
      show_root_heading: true

## Parsers

### MetadataParser

::: genie_forge.parsers.MetadataParser
    options:
      show_root_heading: true
      show_source: true

## Authentication

### Auth Module

::: genie_forge.auth
    options:
      show_root_heading: true
      members:
        - get_workspace_client
        - get_profile_config

## Quick Examples

### Basic Usage

```python
from genie_forge import GenieClient, StateManager
from genie_forge.parsers import MetadataParser

# Parse configuration files
parser = MetadataParser(env="dev")
configs = parser.parse_directory("conf/spaces/")

# Create client and plan deployment
client = GenieClient(profile="DEV_PROFILE")
state = StateManager()

# Plan changes
plan = state.plan(configs, client, env="dev")
print(f"Changes: {len(plan.creates)} creates, {len(plan.updates)} updates")

# Apply if changes exist
if plan.has_changes:
    results = state.apply(plan, client)
```

### Environment-Aware Paths

```python
from genie_forge import ProjectPaths, is_running_on_databricks

# Auto-detect environment and configure paths
paths = ProjectPaths(
    project_name="my_project",
    catalog="main",
    schema="default",
    volume_name="genie_forge"
)

# Works on both local machine and Databricks
print(f"Config dir: {paths.spaces_dir}")
print(f"State file: {paths.state_file}")

# Ensure directory structure exists
paths.ensure_structure()
```

### Direct API Calls

```python
from genie_forge import GenieClient

client = GenieClient()

# List all spaces
spaces = client.list_spaces()
for space in spaces:
    print(f"{space['title']} - {space['space_id']}")

# Get a specific space
space = client.get_space("space_id_here")

# Create a new space
new_space = client.create_space(
    title="My Space",
    description="Created via API",
    warehouse_id="warehouse_id",
    table_identifiers=["catalog.schema.table"]
)
```
