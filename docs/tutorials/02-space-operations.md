---
title: Space Operations
description: List, get, find, export, and clone Genie spaces
---

# 02 - Space Operations

This notebook covers space management commands: listing, viewing, finding, exporting, and cloning spaces.

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
```

## List All Spaces

View all Genie spaces in your workspace:

```python
# List spaces as table
!genie-forge space-list

# Output as JSON for processing
!genie-forge space-list --output json
```

With filtering:

```python
# Limit results
!genie-forge space-list --limit 10
```

## Get Space Details

View detailed information about a specific space:

```python
# Get by space ID
!genie-forge space-get --space-id "01abc123def456"

# Output as JSON
!genie-forge space-get --space-id "01abc123def456" --output json
```

## Find Spaces

Search for spaces by title pattern:

```python
# Find spaces containing "sales"
!genie-forge space-find --pattern "sales"

# Case-insensitive search
!genie-forge space-find --pattern "ANALYTICS" --ignore-case
```

## Export Space to YAML

Export an existing space to a YAML configuration file:

```python
# Export to default location
!genie-forge space-export --space-id "01abc123def456" --output-dir {paths.exports_dir}

# Export with custom filename
!genie-forge space-export --space-id "01abc123def456" --output-dir {paths.exports_dir} --filename my_space.yaml
```

## Clone a Space

Create a copy of an existing space:

```python
# Clone with new title
!genie-forge space-clone --space-id "01abc123def456" --new-title "Sales Analytics (Copy)"

# Clone and export config
!genie-forge space-clone --space-id "01abc123def456" --new-title "Sales Analytics (Dev)" --output-dir {paths.exports_dir}
```

## Programmatic Access

Use the Python API for more control:

```python
from genie_forge import GenieClient
import json

client = GenieClient()

# List spaces
spaces = client.list_spaces()
print(f"Total spaces: {len(spaces)}")

# Find by pattern
sales_spaces = [s for s in spaces if "sales" in s.get("title", "").lower()]
for space in sales_spaces:
    print(f"  - {space['title']} ({space['space_id']})")
```

### Export Programmatically

```python
from genie_forge import space_to_yaml  # Also available from genie_forge.serializer

# Get a space
space = client.get_space("01abc123def456")

# Convert to YAML
yaml_content = space_to_yaml(space)

# Save to file
output_file = paths.exports_dir / f"{space['title'].lower().replace(' ', '_')}.yaml"
output_file.write_text(yaml_content)
print(f"✓ Exported to: {output_file}")
```

### Bulk Export

```python
# Export all spaces
for space in client.list_spaces():
    yaml_content = space_to_yaml(space)
    filename = f"{space['space_id']}.yaml"
    output_file = paths.exports_dir / filename
    output_file.write_text(yaml_content)
    print(f"  ✓ {space['title']}")

print(f"\n✓ Exported {len(spaces)} spaces to {paths.exports_dir}")
```

## Next Steps

- [03 - State Management](03-state-management.md) - Import spaces to state
- [04 - Cross-Workspace Migration](04-migration.md) - Migrate between workspaces
