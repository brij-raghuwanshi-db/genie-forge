# Databricks notebook source
# MAGIC %md
# MAGIC # Genie-Forge: Setup and Prerequisites
# MAGIC
# MAGIC This notebook guides you through setting up Genie-Forge for programmatic Genie space management.
# MAGIC
# MAGIC ## What You'll Learn
# MAGIC 1. Install genie-forge package
# MAGIC 2. Configure authentication
# MAGIC 3. Verify connectivity
# MAGIC 4. Initialize a project
# MAGIC 5. Create your first configuration file
# MAGIC
# MAGIC ## Prerequisites
# MAGIC - Databricks workspace with Genie enabled
# MAGIC - SQL Warehouse running
# MAGIC - Unity Catalog tables for your Genie spaces
# MAGIC - **On Databricks**: Unity Catalog Volume for storing files (`/Volumes/<catalog>/<schema>/<volume_name>/`)
# MAGIC - **On Local Machine**: Local directory (e.g., `~/.genie-forge/` or project folder)
# MAGIC
# MAGIC ## Version
# MAGIC This notebook is compatible with **Genie-Forge v0.3.0+**
# MAGIC
# MAGIC ## Time: ~15 minutes

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Install Genie-Forge
# MAGIC
# MAGIC Install the genie-forge package from PyPI or local source.

# COMMAND ----------

# Install from PyPI (recommended)
%pip install genie-forge>=0.3.0

# Or install from local source (during development)
# %pip install -e /Workspace/Repos/your-username/genie-forge

# COMMAND ----------

# Restart Python to pick up new packages
dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Verify Installation

# COMMAND ----------

# Verify import works
from genie_forge import __version__, GenieClient, SpaceConfig, StateManager
print(f"✓ Genie-Forge version: {__version__}")

# List available CLI commands
print("\n✓ CLI commands available:")
print("  - init, profiles, whoami")
print("  - validate, plan, apply, destroy")
print("  - status, drift, find")
print("  - space-list, space-get, space-create, space-export, space-clone")
print("  - state-list, state-show, state-pull, state-remove, state-import")
print("  - setup-demo, demo-status, cleanup-demo")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Configure Authentication
# MAGIC
# MAGIC Genie-Forge supports multiple authentication methods:
# MAGIC 1. **Notebook context** (automatic in Databricks notebooks)
# MAGIC 2. **Environment variables** (`DATABRICKS_HOST`, `DATABRICKS_TOKEN`)
# MAGIC 3. **databrickscfg profile** (from `~/.databrickscfg`)
# MAGIC
# MAGIC In Databricks notebooks, authentication happens automatically using your current session.

# COMMAND ----------

# In a Databricks notebook, authentication is automatic
# The SDK uses the notebook's execution context

from databricks.sdk import WorkspaceClient

# Create a client - uses notebook context automatically
w = WorkspaceClient()

# Verify we're connected
current_user = w.current_user.me()
print(f"✓ Connected as: {current_user.user_name}")
print(f"✓ Workspace: {w.config.host}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Test Genie API Access (whoami equivalent)
# MAGIC
# MAGIC Let's verify we can access the Genie API.

# COMMAND ----------

from genie_forge.client import GenieClient

# Create a GenieClient using the workspace client
client = GenieClient(client=w)

# List existing Genie spaces (with pagination support)
spaces = client.list_spaces()
print(f"✓ Found {len(spaces)} existing Genie space(s)")

if spaces:
    print("\n  First 5 spaces:")
    for space in spaces[:5]:
        title = space.get('title', 'Untitled')
        space_id = space.get('id', 'N/A')
        print(f"    - {title} (ID: {space_id[:16]}...)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Verify SQL Warehouse
# MAGIC
# MAGIC Genie spaces require a SQL warehouse. Let's verify we have one available.

# COMMAND ----------

# List available warehouses
warehouses = list(w.warehouses.list())
print(f"✓ Found {len(warehouses)} SQL warehouse(s)")

for wh in warehouses:
    state = wh.state.value if wh.state else "UNKNOWN"
    state_emoji = "🟢" if state == "RUNNING" else "🔴"
    print(f"  {state_emoji} {wh.name} (ID: {wh.id}, State: {state})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Initialize Project (genie-forge init)
# MAGIC
# MAGIC Genie-Forge uses a standard project structure. Let's initialize it.
# MAGIC
# MAGIC **Note:** File storage paths are automatically detected:
# MAGIC - **Databricks**: Unity Catalog Volume (`/Volumes/<catalog>/<schema>/<volume_name>/<project_name>/`)
# MAGIC - **Local Machine**: Local directory (`~/.genie-forge/<project_name>/`)

# COMMAND ----------

from pathlib import Path

# Import environment utilities from genie-forge
from genie_forge import ProjectPaths, is_running_on_databricks

# =============================================================================
# PROJECT CONFIGURATION - UPDATE THESE VALUES
# =============================================================================
# The same catalog and schema are used for:
# - Data tables (for Genie spaces to query)
# - Volume storage (for config/state files on Databricks)

PROJECT_NAME = "genie-forge-demo"
CATALOG = "your_catalog"             # Unity Catalog name
SCHEMA = "default"                   # Schema name
VOLUME_NAME = "genie_forge"          # Volume name for file storage

# Create project paths (auto-detects environment)
# On Databricks: Uses /Volumes/CATALOG/SCHEMA/VOLUME_NAME/PROJECT_NAME/
# On Local: Uses ~/.genie-forge/PROJECT_NAME/
paths = ProjectPaths(
    project_name=PROJECT_NAME,
    catalog=CATALOG,
    schema=SCHEMA,
    volume_name=VOLUME_NAME,
)

PROJECT_DIR = paths.root

if is_running_on_databricks():
    print(f"🔷 Running on Databricks - Using Unity Catalog Volume: {PROJECT_DIR}")
else:
    print(f"💻 Running locally - Using local path: {PROJECT_DIR}")

# Create the project directory structure
paths.ensure_structure()

# Create project structure (equivalent to `genie-forge init`)
(Path(PROJECT_DIR) / "conf/spaces").mkdir(parents=True, exist_ok=True)
(Path(PROJECT_DIR) / "conf/variables").mkdir(parents=True, exist_ok=True)

# Create initial state file
import json
state_file = Path(PROJECT_DIR) / ".genie-forge.json"
if not state_file.exists():
    state_file.write_text(json.dumps({
        "version": "1.0.0",
        "environments": {}
    }, indent=2))

print(f"✓ Project initialized at: {PROJECT_DIR}")
print("\n  Directory structure:")
print("  ├── conf/")
print("  │   ├── spaces/        # Space configuration files")
print("  │   └── variables/     # Environment variables")
print("  └── .genie-forge.json  # State file")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Set Up Your Configuration Variables
# MAGIC
# MAGIC Define the variables for your environment. These will be used in YAML configs.

# COMMAND ----------

# SQL Warehouse configuration
# Replace with your actual warehouse ID
WAREHOUSE_ID = "your_warehouse_id_here"  # e.g., "6c5c02379eea0732"

# Quick verification (CATALOG and SCHEMA were defined earlier)
print("Configuration:")
print(f"  CATALOG:      {CATALOG}")
print(f"  SCHEMA:       {SCHEMA}")
print(f"  WAREHOUSE_ID: {WAREHOUSE_ID}")
print(f"  VOLUME_NAME:  {VOLUME_NAME}")

if WAREHOUSE_ID != "your_warehouse_id_here" and CATALOG != "your_catalog":
    # Verify the warehouse exists
    try:
        wh = w.warehouses.get(WAREHOUSE_ID)
        print(f"\n✓ Warehouse found: {wh.name} (State: {wh.state.value})")
    except Exception as e:
        print(f"\n✗ Warehouse not found: {e}")
else:
    print("\n⚠️ Please update CATALOG, SCHEMA, and WAREHOUSE_ID above")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 8: Create a Sample Configuration
# MAGIC
# MAGIC Let's create a YAML configuration file for a Genie space.

# COMMAND ----------

import yaml

# Sample configuration (v0.3.0 format)
sample_config = {
    "version": 1,
    "spaces": [
        {
            "space_id": "demo_space",
            "title": "Demo Analytics Space",
            "warehouse_id": WAREHOUSE_ID,
            "description": "A demo space created with Genie-Forge",
            "sample_questions": [
                "Show all records",
                "Count total rows",
                "What are the column names?"
            ],
            "data_sources": {
                "tables": [
                    {
                        "identifier": f"{CATALOG}.{SCHEMA}.your_table",
                        "description": ["Demo table for Genie space"],
                    }
                ]
            },
            "instructions": {
                "text_instructions": [
                    {"content": "Provide clear and concise answers."},
                    {"content": "When asked about counts, use COUNT(*) for totals."},
                ],
            },
        }
    ]
}

print("Sample configuration:")
print("-" * 50)
print(yaml.dump(sample_config, default_flow_style=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 9: Save Configuration

# COMMAND ----------

# Save to project directory
config_path = f"{PROJECT_DIR}/conf/spaces/demo_space.yaml"

with open(config_path, 'w') as f:
    yaml.dump(sample_config, f, default_flow_style=False)

print(f"✓ Configuration saved to: {config_path}")

# Also create environment variables file
# Environment-specific variables (for multi-environment deployments)
env_config = {
    "dev": {
        "warehouse_id": WAREHOUSE_ID,
        "catalog": CATALOG,
        "schema": SCHEMA,
    },
    "prod": {
        "warehouse_id": "your_prod_warehouse_id",
        "catalog": CATALOG,  # Same catalog, or change for prod
        "schema": SCHEMA,    # Same schema, or change for prod
    }
}

env_path = f"{PROJECT_DIR}/conf/variables/env.yaml"
with open(env_path, 'w') as f:
    yaml.dump(env_config, f, default_flow_style=False)

print(f"✓ Environment config saved to: {env_path}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 10: Demo Tables Setup (Optional)
# MAGIC
# MAGIC If you want to use the built-in demo, you can set up demo tables.

# COMMAND ----------

# The CLI command for setting up demo tables:
print("To set up demo tables, run:")
print(f"  genie-forge setup-demo -c {CATALOG} -s {SCHEMA} -w {WAREHOUSE_ID}")
print()
print("To check demo status:")
print(f"  genie-forge demo-status -c {CATALOG} -s {SCHEMA} -w {WAREHOUSE_ID}")
print()
print("To clean up demo tables:")
print(f"  genie-forge cleanup-demo -c {CATALOG} -s {SCHEMA} -w {WAREHOUSE_ID} --execute")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC You've completed the setup! Here's what we accomplished:
# MAGIC
# MAGIC | Step | Action | Status |
# MAGIC |------|--------|--------|
# MAGIC | 1 | Install genie-forge | ✓ |
# MAGIC | 2 | Verify installation | ✓ |
# MAGIC | 3 | Configure authentication | ✓ |
# MAGIC | 4 | Test Genie API | ✓ |
# MAGIC | 5 | Verify SQL warehouse | ✓ |
# MAGIC | 6 | Initialize project | ✓ |
# MAGIC | 7 | Set configuration variables | ✓ |
# MAGIC | 8 | Create sample config | ✓ |
# MAGIC | 9 | Save configuration | ✓ |
# MAGIC
# MAGIC ## Next Steps
# MAGIC
# MAGIC Continue to **Notebook 01: Plan and Apply Demo** to:
# MAGIC - Validate the configuration
# MAGIC - Plan deployment
# MAGIC - Apply changes to create Genie spaces
# MAGIC - View status and manage spaces
# MAGIC
# MAGIC ## CLI Quick Reference (v0.3.0)
# MAGIC
# MAGIC ```bash
# MAGIC # Setup
# MAGIC genie-forge init                    # Initialize project
# MAGIC genie-forge profiles                # List available profiles
# MAGIC genie-forge whoami                  # Show current identity
# MAGIC
# MAGIC # Core Workflow
# MAGIC genie-forge validate --config conf/spaces/
# MAGIC genie-forge plan --env dev
# MAGIC genie-forge apply --env dev --auto-approve
# MAGIC genie-forge status --env dev
# MAGIC genie-forge drift --env dev
# MAGIC
# MAGIC # Space Operations
# MAGIC genie-forge space-list              # List all spaces
# MAGIC genie-forge space-get <id>          # Get space details
# MAGIC genie-forge space-create --from-file config.yaml
# MAGIC # Local: genie-forge space-export --output-dir ./exports/
# MAGIC # Databricks: genie-forge space-export --output-dir /Volumes/<catalog>/<schema>/<volume>/exports/
# MAGIC genie-forge space-clone <id> --name "Clone"
# MAGIC
# MAGIC # State Operations  
# MAGIC genie-forge state-list              # List tracked spaces
# MAGIC genie-forge state-show --env dev    # Show state details
# MAGIC genie-forge state-pull --env dev    # Refresh from workspace
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Troubleshooting
# MAGIC
# MAGIC ### Authentication Issues
# MAGIC ```python
# MAGIC # Use explicit token (not recommended for production)
# MAGIC import os
# MAGIC os.environ['DATABRICKS_HOST'] = 'https://your-workspace.databricks.com'
# MAGIC os.environ['DATABRICKS_TOKEN'] = dbutils.secrets.get(scope="your-scope", key="your-token")
# MAGIC ```
# MAGIC
# MAGIC ### Warehouse Not Found
# MAGIC - Ensure the warehouse exists and is running
# MAGIC - Check you have permissions to use the warehouse
# MAGIC - Use `genie-forge space-list --profile YOUR_PROFILE` to test connectivity
# MAGIC
# MAGIC ### Import Errors
# MAGIC - Restart Python after installing packages: `dbutils.library.restartPython()`
# MAGIC - Verify installation: `pip show genie-forge`
