# Databricks notebook source
# MAGIC %md
# MAGIC # Genie-Forge: Core Workflow
# MAGIC
# MAGIC This notebook demonstrates the **Terraform-like workflow** for managing Genie spaces:
# MAGIC
# MAGIC ```
# MAGIC validate → plan → apply → status
# MAGIC ```
# MAGIC
# MAGIC ## What You'll Learn
# MAGIC 1. **Validate** - Check configuration for errors
# MAGIC 2. **Plan** - Preview what will be created/updated/deleted
# MAGIC 3. **Apply** - Deploy changes to workspace
# MAGIC 4. **Status** - View deployment status
# MAGIC 5. **Destroy** - Remove spaces
# MAGIC
# MAGIC ## Prerequisites
# MAGIC - Complete **Notebook 00** (Setup)
# MAGIC - Configuration file ready
# MAGIC
# MAGIC ## Time: ~10 minutes

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

from genie_forge import GenieClient, StateManager, __version__
from genie_forge.parsers import MetadataParser, validate_config
from genie_forge.models import PlanAction
from databricks.sdk import WorkspaceClient

print(f"✓ Genie-Forge v{__version__}")

# Initialize
w = WorkspaceClient()
client = GenieClient(client=w)
print(f"✓ Connected as: {w.current_user.me().user_name}")

# COMMAND ----------

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
CONFIG_PATH = paths.get_config_path("demo_space")
STATE_FILE = paths.state_file

if is_running_on_databricks():
    print(f"🔷 Running on Databricks - Using Volume: {PROJECT_DIR}")
else:
    print(f"💻 Running locally - Using path: {PROJECT_DIR}")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Step 1: Validate Configuration
# MAGIC
# MAGIC Before deploying, always validate your configuration files.
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC genie-forge validate --config conf/spaces/
# MAGIC ```

# COMMAND ----------

# Validate the config file
errors = validate_config(CONFIG_PATH)

if errors:
    print("❌ VALIDATION FAILED")
    print("-" * 40)
    for error in errors:
        print(f"  • {error}")
    print("\nFix the errors above before proceeding.")
else:
    print("✅ VALIDATION PASSED")
    print("-" * 40)
    print("Configuration is valid and ready for deployment.")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Step 2: Plan Deployment
# MAGIC
# MAGIC Preview what changes will be made **before** actually deploying.
# MAGIC This is similar to `terraform plan`.
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC genie-forge plan --env dev --profile YOUR_PROFILE
# MAGIC ```

# COMMAND ----------

# Load configuration
parser = MetadataParser(env="dev")
configs = parser.parse(CONFIG_PATH)
print(f"✓ Loaded {len(configs)} space configuration(s)")

# Create state manager
state_manager = StateManager(
    state_file=STATE_FILE,
    project_id="demo_project",
    project_name="Genie-Forge Demo"
)

# Generate plan
plan = state_manager.plan(configs, client, env="dev")

# COMMAND ----------

# Display the plan
print("=" * 60)
print("DEPLOYMENT PLAN")
print("=" * 60)
print(f"Environment: {plan.environment}")
print(f"Timestamp:   {plan.timestamp}")
print()

# Summary counts
creates = sum(1 for i in plan.items if i.action == PlanAction.CREATE)
updates = sum(1 for i in plan.items if i.action == PlanAction.UPDATE)
destroys = sum(1 for i in plan.items if i.action == PlanAction.DESTROY)
unchanged = sum(1 for i in plan.items if i.action == PlanAction.NO_CHANGE)

print(f"  ➕ To create:  {creates}")
print(f"  🔄 To update:  {updates}")
print(f"  ❌ To destroy: {destroys}")
print(f"  ⏸️  Unchanged:  {unchanged}")
print()

# Details
print("CHANGES:")
print("-" * 60)
for item in plan.items:
    icons = {
        PlanAction.CREATE: "➕ CREATE",
        PlanAction.UPDATE: "🔄 UPDATE",
        PlanAction.DESTROY: "❌ DESTROY",
        PlanAction.NO_CHANGE: "⏸️  NO CHANGE"
    }
    print(f"{icons.get(item.action, '?')}: {item.logical_id}")
    
    if item.changes:
        for change in item.changes:
            print(f"      • {change}")

print("=" * 60)

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Step 3: Apply Changes
# MAGIC
# MAGIC Deploy the planned changes to your workspace.
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC # With confirmation prompt
# MAGIC genie-forge apply --env dev --profile YOUR_PROFILE
# MAGIC
# MAGIC # Skip confirmation
# MAGIC genie-forge apply --env dev --auto-approve
# MAGIC
# MAGIC # Dry run (preview only)
# MAGIC genie-forge apply --env dev --dry-run
# MAGIC ```

# COMMAND ----------

# Dry run first (safe - no actual changes)
print("DRY RUN MODE")
print("=" * 60)
print("Simulating apply (no actual changes)...")
print()

dry_results = state_manager.apply(plan, client, dry_run=True)

print(f"  Would create:  {len(dry_results['created'])} space(s)")
print(f"  Would update:  {len(dry_results['updated'])} space(s)")
print(f"  Unchanged:     {len(dry_results['unchanged'])} space(s)")
print()
print("To actually apply, set dry_run=False")

# COMMAND ----------

# ACTUAL APPLY (uncomment to run)
# ⚠️ WARNING: This will create/modify actual Genie spaces!

"""
print("APPLYING CHANGES")
print("=" * 60)

results = state_manager.apply(plan, client, dry_run=False)

# Results summary
print()
print("RESULTS:")
print("-" * 60)

if results['created']:
    print(f"✅ Created ({len(results['created'])}):")
    for space_id in results['created']:
        print(f"     • {space_id}")

if results['updated']:
    print(f"🔄 Updated ({len(results['updated'])}):")
    for space_id in results['updated']:
        print(f"     • {space_id}")

if results['unchanged']:
    print(f"⏸️  Unchanged ({len(results['unchanged'])}):")
    for space_id in results['unchanged']:
        print(f"     • {space_id}")

if results['failed']:
    print(f"❌ Failed ({len(results['failed'])}):")
    for failure in results['failed']:
        print(f"     • {failure['logical_id']}: {failure['error']}")

print("=" * 60)
"""

print("⚠️ Uncomment the code above to actually apply changes")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Step 4: View Status
# MAGIC
# MAGIC Check what's currently deployed.
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC genie-forge status --env dev
# MAGIC ```

# COMMAND ----------

# Get deployment status
status = state_manager.status(env="dev")

print("DEPLOYMENT STATUS")
print("=" * 60)
print(f"Environment:  {status['environment']}")
print(f"Workspace:    {status.get('workspace_url', 'N/A')}")
print(f"Total Spaces: {status['total']}")
print(f"Last Applied: {status.get('last_applied', 'Never')}")
print()

if status['spaces']:
    print("DEPLOYED SPACES:")
    print("-" * 60)
    
    status_icons = {
        "APPLIED": "✅",
        "PENDING": "⏳",
        "MODIFIED": "🔄",
        "DRIFT": "⚠️",
        "DESTROYED": "❌",
        "ERROR": "💥"
    }
    
    for space in status['spaces']:
        icon = status_icons.get(space['status'], "❓")
        print(f"{icon} {space['logical_id']}")
        print(f"      Title:    {space['title']}")
        print(f"      Space ID: {space['databricks_space_id'] or 'Not deployed'}")
        print(f"      Status:   {space['status']}")
        if space.get('error'):
            print(f"      Error:    {space['error']}")
        print()
else:
    print("No spaces deployed yet.")
    print("Run apply (with dry_run=False) to deploy spaces.")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Step 5: Destroy (Optional)
# MAGIC
# MAGIC Remove a deployed space from the workspace.
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC # Destroy specific space
# MAGIC genie-forge destroy --env dev --target demo_space
# MAGIC
# MAGIC # Destroy all spaces (with confirmation)
# MAGIC genie-forge destroy --env dev --target "*"
# MAGIC
# MAGIC # Destroy all except some
# MAGIC genie-forge destroy --env dev --target "* [keep_this_one]"
# MAGIC ```

# COMMAND ----------

# Preview destroy (dry run)
target_space = "demo_space"

print(f"DESTROY PREVIEW: {target_space}")
print("-" * 40)

destroy_result = state_manager.destroy(
    target=target_space,
    client=client,
    env="dev",
    dry_run=True  # Safe - just preview
)

if destroy_result['success']:
    print(f"✓ Would destroy: {target_space}")
    if destroy_result.get('databricks_space_id'):
        print(f"  Space ID: {destroy_result['databricks_space_id']}")
else:
    print(f"✗ Cannot destroy: {destroy_result.get('error', 'Unknown error')}")

# COMMAND ----------

# ACTUAL DESTROY (uncomment to run)
# ⚠️ WARNING: This will DELETE the space from your workspace!

"""
destroy_result = state_manager.destroy(
    target=target_space,
    client=client,
    env="dev",
    dry_run=False
)

if destroy_result['success']:
    print(f"✅ Destroyed: {target_space}")
else:
    print(f"❌ Failed: {destroy_result.get('error')}")
"""

print("⚠️ Uncomment the code above to actually destroy the space")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Summary
# MAGIC
# MAGIC You've learned the core Genie-Forge workflow:
# MAGIC
# MAGIC | Step | Command | Purpose |
# MAGIC |------|---------|---------|
# MAGIC | 1 | `validate` | Check configuration for errors |
# MAGIC | 2 | `plan` | Preview changes before applying |
# MAGIC | 3 | `apply` | Deploy changes to workspace |
# MAGIC | 4 | `status` | View what's deployed |
# MAGIC | 5 | `destroy` | Remove deployed spaces |
# MAGIC
# MAGIC ## CLI Quick Reference
# MAGIC
# MAGIC ```bash
# MAGIC # Full workflow
# MAGIC genie-forge validate --config conf/spaces/
# MAGIC genie-forge plan --env dev
# MAGIC genie-forge apply --env dev --auto-approve
# MAGIC genie-forge status --env dev
# MAGIC genie-forge destroy --env dev --target my_space
# MAGIC ```
# MAGIC
# MAGIC ## Next Steps
# MAGIC
# MAGIC - **Notebook 02**: Space Operations (list, get, create, export, clone)
# MAGIC - **Notebook 03**: State Management (state-list, drift detection)
# MAGIC - **Notebook 04**: Cross-Workspace Migration
