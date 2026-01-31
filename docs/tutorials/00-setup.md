---
title: Setup Prerequisites
description: Initial setup and configuration for Genie-Forge notebooks
---

# 00 - Setup Prerequisites

This notebook guides you through the initial setup for running Genie-Forge in Databricks.

## Prerequisites

- Databricks workspace with Genie (AI/BI) enabled
- Access to create Unity Catalog Volumes
- Python environment with `genie-forge` installed

## Installation

```python
# Install genie-forge
%pip install genie-forge --quiet

# Restart Python to pick up new packages
dbutils.library.restartPython()
```

## Configuration

```python
from genie_forge import ProjectPaths, is_running_on_databricks

# =============================================================================
# CONFIGURATION - Edit these values for your environment
# =============================================================================

# Unity Catalog location (used for BOTH tables AND volume storage)
CATALOG = "main"
SCHEMA = "default"

# Volume for storing config and state files
VOLUME_NAME = "genie_forge"

# Project name (creates subdirectory in volume)
PROJECT_NAME = "demo"

# =============================================================================
# PATH SETUP - Automatic based on environment
# =============================================================================

paths = ProjectPaths(
    project_name=PROJECT_NAME,
    catalog=CATALOG,
    schema=SCHEMA,
    volume_name=VOLUME_NAME
)

print(f"Environment: {'Databricks' if is_running_on_databricks() else 'Local'}")
print(f"Project root: {paths.root}")
print(f"State file: {paths.state_file}")
print(f"Spaces config: {paths.spaces_dir}")
print(f"Exports: {paths.exports_dir}")
```

## Create Directory Structure

```python
# Create all required directories
paths.ensure_structure()
print("✓ Directory structure created")
```

## Verify Authentication

```python
from genie_forge import GenieClient

# Authentication is automatic in Databricks notebooks
client = GenieClient()

# Verify connection
!genie-forge whoami
```

## Create Demo Tables (Optional)

If you want to test with sample data:

```python
# Create demo tables in your catalog/schema
!genie-forge setup-demo --catalog {CATALOG} --schema {SCHEMA}
```

To check demo status:

```python
!genie-forge demo-status --catalog {CATALOG} --schema {SCHEMA}
```

## Create Sample Configuration

```python
from pathlib import Path

sample_config = f'''
spaces:
  - title: Demo Analytics Space
    description: A demo Genie space for testing
    warehouse_id: ${{WAREHOUSE_ID}}
    tables:
      - {CATALOG}.{SCHEMA}.demo_employees
      - {CATALOG}.{SCHEMA}.demo_sales
    instructions: |
      You are a helpful data analyst. Help users explore
      the demo employee and sales data.
'''

config_file = paths.spaces_dir / "demo_space.yaml"
config_file.write_text(sample_config)
print(f"✓ Created: {config_file}")
```

## Create Environment File

```python
# Get your SQL Warehouse ID from the Databricks UI
# SQL Warehouses -> Select warehouse -> Copy ID

env_config = '''
variables:
  WAREHOUSE_ID: "your-warehouse-id-here"  # Replace with your warehouse ID
'''

env_file = paths.root / "conf" / "environments" / "dev.yaml"
env_file.parent.mkdir(parents=True, exist_ok=True)
env_file.write_text(env_config)
print(f"✓ Created: {env_file}")
print("\n⚠️  Remember to update WAREHOUSE_ID with your actual warehouse ID!")
```

## Verify Setup

```python
# Validate the configuration
!genie-forge validate --config {paths.spaces_dir}
```

## Next Steps

You're now ready to use Genie-Forge! Continue with:

1. **[01 - Core Workflow](01-core-workflow.md)** - Learn validate → plan → apply
2. **[02 - Space Operations](02-space-operations.md)** - Explore space commands
3. **[03 - State Management](03-state-management.md)** - Manage state files

## Cleanup Demo (When Done)

```python
# Remove demo tables when finished testing
!genie-forge cleanup-demo --catalog {CATALOG} --schema {SCHEMA}
```
