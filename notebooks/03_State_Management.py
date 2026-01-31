# Databricks notebook source
# MAGIC %md
# MAGIC # Genie-Forge: State Management
# MAGIC
# MAGIC This notebook covers **state management** and **drift detection**:
# MAGIC
# MAGIC | Command | Purpose |
# MAGIC |---------|---------|
# MAGIC | `state-list` | List tracked spaces |
# MAGIC | `state-show` | View full state details |
# MAGIC | `state-pull` | Refresh state from workspace |
# MAGIC | `state-remove` | Remove space from tracking |
# MAGIC | `state-import` | Import existing space |
# MAGIC | `drift` | Detect configuration drift |
# MAGIC
# MAGIC ## What is State?
# MAGIC
# MAGIC The **state file** (`.genie-forge.json`) tracks:
# MAGIC - Which spaces are managed by Genie-Forge
# MAGIC - Their Databricks space IDs
# MAGIC - Configuration hashes for change detection
# MAGIC - Deployment timestamps
# MAGIC
# MAGIC ## Why State Matters
# MAGIC
# MAGIC 1. **Idempotency** - Apply same config multiple times safely
# MAGIC 2. **Change Detection** - Know what changed since last deploy
# MAGIC 3. **Drift Detection** - Detect manual changes in workspace
# MAGIC 4. **Multi-Environment** - Track dev/staging/prod separately
# MAGIC
# MAGIC ## Prerequisites
# MAGIC - Complete **Notebook 00** (Setup)
# MAGIC
# MAGIC ## Time: ~10 minutes

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

from genie_forge import GenieClient, StateManager, __version__
from databricks.sdk import WorkspaceClient
import json
from pathlib import Path

print(f"✓ Genie-Forge v{__version__}")

w = WorkspaceClient()
client = GenieClient(client=w)
print(f"✓ Connected as: {w.current_user.me().user_name}")

# =============================================================================
# PROJECT CONFIGURATION - UPDATE THESE VALUES
# =============================================================================
from genie_forge import ProjectPaths, is_running_on_databricks

# The same catalog and schema are used for tables and volume storage
PROJECT_NAME = "genie-forge-demo"
CATALOG = "your_catalog"             # Unity Catalog name
SCHEMA = "default"                   # Schema name
VOLUME_NAME = "genie_forge"          # Volume name for file storage

# Create project paths (auto-detects environment)
paths = ProjectPaths(
    project_name=PROJECT_NAME,
    catalog=CATALOG,
    schema=SCHEMA,
    volume_name=VOLUME_NAME,
)

PROJECT_DIR = paths.root
STATE_FILE = paths.state_file

if is_running_on_databricks():
    print(f"🔷 Running on Databricks - Using Volume: {PROJECT_DIR}")
else:
    print(f"💻 Running locally - Using path: {PROJECT_DIR}")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Understanding the State File
# MAGIC
# MAGIC The state file has this structure:
# MAGIC
# MAGIC ```json
# MAGIC {
# MAGIC   "version": "1.0.0",
# MAGIC   "project_id": "my_project",
# MAGIC   "project_name": "My Project",
# MAGIC   "environments": {
# MAGIC     "dev": {
# MAGIC       "workspace_url": "https://dev.databricks.com",
# MAGIC       "last_applied": "2026-01-26T10:00:00",
# MAGIC       "spaces": {
# MAGIC         "sales_analytics": {
# MAGIC           "logical_id": "sales_analytics",
# MAGIC           "databricks_space_id": "01abc123...",
# MAGIC           "title": "Sales Analytics",
# MAGIC           "config_hash": "abc123...",
# MAGIC           "applied_hash": "abc123...",
# MAGIC           "status": "APPLIED",
# MAGIC           "last_applied": "2026-01-26T10:00:00"
# MAGIC         }
# MAGIC       }
# MAGIC     }
# MAGIC   }
# MAGIC }
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 1. List Tracked Spaces (state-list)
# MAGIC
# MAGIC View all spaces tracked in the state file.
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC genie-forge state-list
# MAGIC genie-forge state-list --env dev
# MAGIC genie-forge state-list --show-ids
# MAGIC ```

# COMMAND ----------

# Read state file
try:
    with open(STATE_FILE, 'r') as f:
        state_data = json.load(f)
    
    print("STATE FILE: Tracked Spaces")
    print("=" * 70)
    
    environments = state_data.get('environments', {})
    
    if not environments:
        print("No environments tracked yet.")
        print("Run 'apply' to deploy spaces and create state entries.")
    else:
        for env_name, env_data in environments.items():
            spaces = env_data.get('spaces', {})
            workspace = env_data.get('workspace_url', 'N/A')
            last_applied = env_data.get('last_applied', 'Never')
            
            print(f"\n📁 Environment: {env_name}")
            print(f"   Workspace: {workspace}")
            print(f"   Last Applied: {last_applied}")
            print(f"   Spaces: {len(spaces)}")
            print("-" * 70)
            
            if spaces:
                print(f"   {'Logical ID':<25} {'Status':<12} {'Title'}")
                print("   " + "-" * 65)
                for space_id, space_info in spaces.items():
                    status = space_info.get('status', 'UNKNOWN')
                    title = space_info.get('title', 'Untitled')[:30]
                    status_icon = {
                        "APPLIED": "✅",
                        "PENDING": "⏳",
                        "MODIFIED": "🔄",
                        "DRIFT": "⚠️",
                        "DESTROYED": "❌"
                    }.get(status, "❓")
                    print(f"   {space_id:<25} {status_icon} {status:<10} {title}")
            else:
                print("   (no spaces)")
                
except FileNotFoundError:
    print("State file not found.")
    print(f"Expected location: {STATE_FILE}")
    print("\nTo create state file:")
    print("  1. Run 'genie-forge init' to initialize project")
    print("  2. Run 'genie-forge apply' to deploy spaces")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 2. Show Full State (state-show)
# MAGIC
# MAGIC View the complete state file with all details.
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC genie-forge state-show
# MAGIC genie-forge state-show --env dev
# MAGIC genie-forge state-show --format json
# MAGIC ```

# COMMAND ----------

try:
    with open(STATE_FILE, 'r') as f:
        state_data = json.load(f)
    
    print("FULL STATE FILE")
    print("=" * 70)
    print(json.dumps(state_data, indent=2))
    
except FileNotFoundError:
    print("State file not found.")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 3. Pull/Refresh State (state-pull)
# MAGIC
# MAGIC Refresh state from the actual workspace (useful after manual changes).
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC genie-forge state-pull --env dev
# MAGIC genie-forge state-pull --env dev --verify-only  # Don't update, just check
# MAGIC ```

# COMMAND ----------

# State pull refreshes local state from workspace
state_manager = StateManager(
    state_file=STATE_FILE,
    project_id="demo_project",
    project_name="Genie-Forge Demo"
)

print("STATE PULL")
print("=" * 70)
print("This operation:")
print("  1. Reads each tracked space from the workspace")
print("  2. Updates local state with current information")
print("  3. Detects if spaces were deleted manually")
print()
print("CLI command:")
print("  genie-forge state-pull --env dev --profile YOUR_PROFILE")
print()
print("Verify-only mode (no changes):")
print("  genie-forge state-pull --env dev --verify-only")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 4. Remove from State (state-remove)
# MAGIC
# MAGIC Remove a space from state tracking (does NOT delete the space).
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC genie-forge state-remove my_space --env dev
# MAGIC genie-forge state-remove my_space --env dev --force  # Skip confirmation
# MAGIC ```

# COMMAND ----------

print("STATE REMOVE")
print("=" * 70)
print("⚠️  This removes a space from state tracking ONLY.")
print("    The actual space in Databricks is NOT deleted.")
print()
print("Use cases:")
print("  • Space was manually deleted in Databricks")
print("  • You want to stop managing a space with Genie-Forge")
print("  • Cleaning up old/abandoned entries")
print()
print("Example:")
print("  genie-forge state-remove old_space --env dev --force")
print()
print("To DELETE the space AND remove from state, use:")
print("  genie-forge destroy --env dev --target old_space")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 5. Import Existing Space (state-import / import)
# MAGIC
# MAGIC Bring an existing Databricks space under Genie-Forge management.
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC # Import by space ID
# MAGIC genie-forge import <space-id> --env dev --as my_space
# MAGIC
# MAGIC # Import by pattern
# MAGIC genie-forge import --pattern "Sales*" --env dev
# MAGIC
# MAGIC # Import and generate config file
# MAGIC genie-forge import <space-id> --env dev --as my_space --output-dir ./conf/spaces/
# MAGIC
# MAGIC # Dry run
# MAGIC genie-forge import <space-id> --env dev --dry-run
# MAGIC ```

# COMMAND ----------

print("IMPORT EXISTING SPACE")
print("=" * 70)
print("Import brings existing Databricks spaces under management.")
print()
print("What happens during import:")
print("  1. Fetches space details from Databricks")
print("  2. Creates entry in state file")
print("  3. Optionally generates config YAML file")
print()
print("Example workflow:")
print()
print("  # 1. Find spaces to import")
print("  genie-forge space-list")
print()
print("  # 2. Import specific space")
print("  genie-forge import 01abc123... --env prod --as sales_analytics")
print()
print("  # 3. Import multiple by pattern")
print("  genie-forge import --pattern 'Sales*' --env prod")
print()
print("  # 4. Generate config files during import")
print("  genie-forge import 01abc123... --env prod --as sales \\")
print("      --output-dir ./conf/spaces/")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 6. Detect Drift (drift)
# MAGIC
# MAGIC Check if spaces in workspace differ from your configuration.
# MAGIC
# MAGIC **What is Drift?**
# MAGIC - Someone manually edited a space in Databricks UI
# MAGIC - A space was deleted without using Genie-Forge
# MAGIC - Configuration changed but wasn't applied
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC genie-forge drift --env dev
# MAGIC genie-forge drift --env dev --profile PROD
# MAGIC ```

# COMMAND ----------

# Detect drift
print("DRIFT DETECTION")
print("=" * 70)

try:
    drift_results = state_manager.detect_drift(client, env="dev")
    
    print(f"Timestamp: {drift_results['timestamp']}")
    print(f"Environment: dev")
    print(f"Spaces Checked: {drift_results['total']}")
    print()
    
    if drift_results['drifted']:
        print("⚠️  DRIFT DETECTED!")
        print("-" * 70)
        
        for drift in drift_results['drifted']:
            print(f"\n  Space: {drift['logical_id']}")
            print(f"  Type:  {drift['drift_type']}")
            
            if drift.get('changes'):
                print("  Changes:")
                for change in drift['changes']:
                    print(f"    • {change}")
        
        print()
        print("To resolve drift:")
        print("  • Run 'apply' to push your config to workspace")
        print("  • Or run 'state-pull' to update state from workspace")
    else:
        print("✅ NO DRIFT DETECTED")
        print()
        print("Your workspace matches your configuration.")
        
except Exception as e:
    print(f"Could not detect drift: {e}")
    print("\nMake sure you have deployed spaces first (run apply).")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## State Lifecycle Diagram
# MAGIC
# MAGIC ```
# MAGIC ┌─────────────────────────────────────────────────────────────┐
# MAGIC │                      STATE LIFECYCLE                         │
# MAGIC └─────────────────────────────────────────────────────────────┘
# MAGIC
# MAGIC   ┌──────────┐        ┌──────────┐        ┌──────────┐
# MAGIC   │  Config  │──plan──│   Plan   │──apply─│  State   │
# MAGIC   │  (YAML)  │        │ (preview)│        │  (JSON)  │
# MAGIC   └──────────┘        └──────────┘        └──────────┘
# MAGIC        │                                        │
# MAGIC        │                                        │
# MAGIC        └────────────drift detection────────────┘
# MAGIC                          │
# MAGIC                          ▼
# MAGIC                   ┌──────────┐
# MAGIC                   │ Workspace│
# MAGIC                   │(Databricks)│
# MAGIC                   └──────────┘
# MAGIC
# MAGIC   Commands:
# MAGIC   ─────────
# MAGIC   validate  → Check config syntax
# MAGIC   plan      → Compare config vs state
# MAGIC   apply     → Push changes to workspace, update state
# MAGIC   status    → Show state contents
# MAGIC   drift     → Compare state vs workspace
# MAGIC   state-pull→ Update state from workspace
# MAGIC   import    → Add existing space to state
# MAGIC   destroy   → Delete from workspace, update state
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Summary
# MAGIC
# MAGIC | Command | Purpose | When to Use |
# MAGIC |---------|---------|-------------|
# MAGIC | `state-list` | List tracked spaces | Quick overview |
# MAGIC | `state-show` | Full state details | Debugging |
# MAGIC | `state-pull` | Refresh from workspace | After manual changes |
# MAGIC | `state-remove` | Stop tracking | Cleanup |
# MAGIC | `import` | Start tracking | Adopt existing space |
# MAGIC | `drift` | Detect changes | Before deployments |
# MAGIC
# MAGIC ## CLI Quick Reference
# MAGIC
# MAGIC ```bash
# MAGIC # View state
# MAGIC genie-forge state-list
# MAGIC genie-forge state-show --env dev
# MAGIC
# MAGIC # Manage state
# MAGIC genie-forge state-pull --env dev
# MAGIC genie-forge state-remove my_space --env dev
# MAGIC genie-forge import <space-id> --env dev --as my_space
# MAGIC
# MAGIC # Detect drift
# MAGIC genie-forge drift --env dev
# MAGIC ```
# MAGIC
# MAGIC ## Next Steps
# MAGIC
# MAGIC - **Notebook 04**: Cross-Workspace Migration
# MAGIC - **Notebook 05**: Advanced Patterns
