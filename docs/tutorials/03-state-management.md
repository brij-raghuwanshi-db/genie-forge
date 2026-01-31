---
title: State Management
description: Manage the Genie-Forge state file
---

# 03 - State Management

This notebook covers state file management: listing environments, viewing state, importing existing spaces, and removing entries.

## Setup

```python
from genie_forge import ProjectPaths

CATALOG = "main"
SCHEMA = "default"
VOLUME_NAME = "genie_forge"
PROJECT_NAME = "demo"

paths = ProjectPaths(
    project_name=PROJECT_NAME,
    catalog=CATALOG,
    schema=SCHEMA,
    volume_name=VOLUME_NAME
)

print(f"State file: {paths.state_file}")
```

## Understanding State

The state file (`.genie-forge.json`) tracks:

- Which spaces are deployed in each environment
- Space IDs and their configuration keys
- Last deployment timestamps
- Drift detection baselines

## List Environments

View all environments in the state file:

```python
!genie-forge state-list --state {paths.state_file}
```

## Show Environment State

View detailed state for a specific environment:

```python
# Show dev environment state
!genie-forge state-show --env dev --state {paths.state_file}

# Output as JSON
!genie-forge state-show --env dev --state {paths.state_file} --output json
```

## Import Existing Space

Bring an existing Genie space under Genie-Forge management:

```python
# Import a single space
!genie-forge state-import --space-id "01abc123def456" --env dev --state {paths.state_file}

# Import with a custom config key
!genie-forge state-import --space-id "01abc123def456" --env dev --state {paths.state_file} --config-key sales_analytics
```

### Import Multiple Spaces

```python
# Import all spaces in workspace to dev environment
from genie_forge import GenieClient

client = GenieClient()
spaces = client.list_spaces()

for space in spaces:
    space_id = space['space_id']
    # Create a config key from the title
    config_key = space['title'].lower().replace(' ', '_').replace('-', '_')
    
    !genie-forge state-import --space-id {space_id} --env dev --state {paths.state_file} --config-key {config_key}
```

## Remove State Entry

Remove a space from state (does not delete the actual space):

```python
# Remove from state
!genie-forge state-remove --config-key sales_analytics --env dev --state {paths.state_file}
```

## Pull Latest State

Update state with current space information:

```python
# Pull latest for all spaces in dev
!genie-forge state-pull --env dev --state {paths.state_file}
```

## Programmatic State Management

```python
from genie_forge import StateManager
import json

# Load state
state = StateManager(state_file=paths.state_file)

# Get environment data
dev_state = state.get_environment("dev")
if dev_state:
    print(f"Spaces in dev: {len(dev_state.get('spaces', {}))}")
    for key, space in dev_state.get('spaces', {}).items():
        print(f"  - {key}: {space.get('space_id')}")

# View raw state
with open(paths.state_file) as f:
    raw_state = json.load(f)
    print(json.dumps(raw_state, indent=2))
```

## State File Structure

```json
{
  "version": "0.3.0",
  "environments": {
    "dev": {
      "spaces": {
        "sales_analytics": {
          "space_id": "01abc123def456",
          "title": "Sales Analytics",
          "last_applied": "2024-01-15T10:30:00Z",
          "config_hash": "abc123..."
        }
      },
      "last_applied": "2024-01-15T10:30:00Z"
    },
    "prod": {
      "spaces": { ... }
    }
  }
}
```

## Next Steps

- [04 - Cross-Workspace Migration](04-migration.md) - Migrate spaces between workspaces
- [05 - Advanced Patterns](05-advanced.md) - Bulk operations and CI/CD
