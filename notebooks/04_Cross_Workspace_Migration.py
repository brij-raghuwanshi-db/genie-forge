# Databricks notebook source
# MAGIC %md
# MAGIC # Genie-Forge: Cross-Workspace Migration
# MAGIC
# MAGIC This notebook demonstrates how to **migrate Genie spaces between workspaces**.
# MAGIC
# MAGIC ## Use Cases
# MAGIC - Promote spaces from **dev → staging → prod**
# MAGIC - Copy spaces between **different Databricks workspaces**
# MAGIC - **Backup** space configurations
# MAGIC - **Disaster recovery** - recreate spaces from config
# MAGIC
# MAGIC ## Migration Flow
# MAGIC
# MAGIC ```
# MAGIC ┌─────────────┐     export      ┌─────────────┐     apply      ┌─────────────┐
# MAGIC │   Source    │ ──────────────► │   Config    │ ──────────────► │   Target    │
# MAGIC │  Workspace  │                 │   (YAML)    │                 │  Workspace  │
# MAGIC └─────────────┘                 └─────────────┘                 └─────────────┘
# MAGIC ```
# MAGIC
# MAGIC ## Prerequisites
# MAGIC - Access to both source and target workspaces
# MAGIC - Profiles configured in `~/.databrickscfg`
# MAGIC - Target warehouse ID in destination workspace
# MAGIC
# MAGIC ## Time: ~15 minutes

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

from genie_forge import GenieClient, StateManager, __version__
from genie_forge.parsers import MetadataParser
from databricks.sdk import WorkspaceClient
import json
import yaml
import re
from pathlib import Path

print(f"✓ Genie-Forge v{__version__}")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Step 1: Configure Source and Target
# MAGIC
# MAGIC Define your source and target workspace details.

# COMMAND ----------

# Configuration - UPDATE THESE VALUES
SOURCE_PROFILE = "DEV"           # Profile name in ~/.databrickscfg
TARGET_PROFILE = "PROD"          # Profile name in ~/.databrickscfg
TARGET_WAREHOUSE_ID = "your_prod_warehouse_id"  # Warehouse in target workspace

# Catalog/Schema mapping (if different between workspaces)
CATALOG_MAPPING = {
    "dev_catalog": "prod_catalog",
    "staging_catalog": "prod_catalog",
}

SCHEMA_MAPPING = {
    "dev_schema": "prod_schema",
}

print("MIGRATION CONFIGURATION")
print("=" * 60)
print(f"Source Profile:     {SOURCE_PROFILE}")
print(f"Target Profile:     {TARGET_PROFILE}")
print(f"Target Warehouse:   {TARGET_WAREHOUSE_ID}")
print()
print("Catalog Mapping:")
for src, tgt in CATALOG_MAPPING.items():
    print(f"  {src} → {tgt}")
print()
print("Schema Mapping:")
for src, tgt in SCHEMA_MAPPING.items():
    print(f"  {src} → {tgt}")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Step 2: Connect to Source Workspace
# MAGIC
# MAGIC Connect and list spaces available for migration.

# COMMAND ----------

# For notebook context, we use the current workspace
# In production, you would use profiles:
#   source_client = GenieClient(profile=SOURCE_PROFILE)

w = WorkspaceClient()
source_client = GenieClient(client=w)

print(f"✓ Connected to source workspace")
print(f"  URL: {w.config.host}")
print(f"  User: {w.current_user.me().user_name}")

# List available spaces
source_spaces = source_client.list_spaces()
print(f"\n✓ Found {len(source_spaces)} spaces in source workspace")

# COMMAND ----------

# Show spaces available for migration
print("SPACES AVAILABLE FOR MIGRATION")
print("=" * 70)
print(f"{'#':<4} {'Title':<40} {'ID'}")
print("-" * 70)

for i, space in enumerate(source_spaces[:20], 1):
    title = (space.get('title') or 'Untitled')[:38]
    space_id = space.get('id', 'N/A')[:24]
    print(f"{i:<4} {title:<40} {space_id}...")

if len(source_spaces) > 20:
    print(f"\n... and {len(source_spaces) - 20} more")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Step 3: Select Spaces to Migrate
# MAGIC
# MAGIC Choose which spaces to migrate using patterns or specific IDs.

# COMMAND ----------

# Option 1: Select by pattern
pattern = "*Analytics*"  # Change this pattern
matches = source_client.find_spaces_by_name(pattern)

print(f"Spaces matching '{pattern}': {len(matches)}")
for space in matches:
    print(f"  • {space.get('title')}")

# COMMAND ----------

# Option 2: Select specific space IDs
# SELECTED_SPACE_IDS = ["01abc123...", "01def456..."]

# For this demo, we'll use the first space if available
SELECTED_SPACE_IDS = [source_spaces[0]['id']] if source_spaces else []

print(f"Selected {len(SELECTED_SPACE_IDS)} space(s) for migration")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Step 4: Export Space Configurations
# MAGIC
# MAGIC Export the selected spaces to YAML configuration files.
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC # Export space configuration
# MAGIC # Local:      genie-forge space-export --space-id <id> --output-dir ./migration/ --profile DEV
# MAGIC # Databricks: genie-forge space-export --space-id <id> --output-dir /Volumes/.../migration/ --profile DEV
# MAGIC ```

# COMMAND ----------

def export_space_config(client, space_id: str) -> dict:
    """Export a space to a configuration dictionary (lossless).
    
    Preserves all API v2 fields including:
    - sql_snippets (filters, expressions, measures)
    - parameters and usage_guidance in example questions
    - join aliases and relationship types
    - enable_format_assistance and enable_entity_matching
    """
    space = client.get_space(space_id, include_serialized=True)
    
    # Parse serialized_space
    serialized = space.get('serialized_space', {})
    if isinstance(serialized, str):
        serialized = json.loads(serialized)
    
    config = {
        "version": serialized.get('version', 2),
        "title": space.get('title'),
        "warehouse_id": space.get('warehouse_id'),
    }
    
    if space.get('description'):
        config['description'] = space['description']
    
    if space.get('parent_path'):
        config['parent_path'] = space['parent_path']
    
    # Data sources (includes column configs with all flags)
    if serialized.get('data_sources'):
        config['data_sources'] = serialized['data_sources']
    
    # Instructions (includes sql_snippets, parameters, etc.)
    if serialized.get('instructions'):
        config['instructions'] = serialized['instructions']
    
    # Sample questions
    sample_questions = serialized.get('config', {}).get('sample_questions', [])
    if sample_questions:
        config['sample_questions'] = sample_questions
    
    return config

# COMMAND ----------

# Export selected spaces
exported_configs = {}

print("EXPORTING SPACES")
print("=" * 60)

for space_id in SELECTED_SPACE_IDS:
    try:
        config = export_space_config(source_client, space_id)
        title = config.get('title', 'Unknown')
        
        # Create safe filename
        safe_name = re.sub(r'[^\w\s-]', '', title.lower())
        safe_name = re.sub(r'[\s-]+', '_', safe_name)[:50]
        
        exported_configs[safe_name] = config
        print(f"✓ Exported: {title}")
        
    except Exception as e:
        print(f"✗ Failed to export {space_id}: {e}")

print(f"\n✓ Exported {len(exported_configs)} space(s)")

# COMMAND ----------

# Show exported config
if exported_configs:
    first_key = list(exported_configs.keys())[0]
    print(f"EXPORTED CONFIG: {first_key}")
    print("=" * 60)
    print(yaml.dump(exported_configs[first_key], default_flow_style=False)[:1000])

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Step 5: Transform for Target Workspace
# MAGIC
# MAGIC Update configurations for the target workspace:
# MAGIC - Replace warehouse ID
# MAGIC - Map catalog/schema names
# MAGIC - Update any workspace-specific references

# COMMAND ----------

def transform_config_for_target(config: dict, 
                                 target_warehouse_id: str,
                                 catalog_mapping: dict = None,
                                 schema_mapping: dict = None) -> dict:
    """Transform a config for the target workspace."""
    import copy
    
    transformed = copy.deepcopy(config)
    
    # Update warehouse ID
    transformed['warehouse_id'] = target_warehouse_id
    
    # Helper to transform table identifiers
    def transform_identifier(identifier: str) -> str:
        parts = identifier.split('.')
        if len(parts) >= 2:
            catalog = parts[0]
            schema = parts[1]
            
            # Apply mappings
            if catalog_mapping and catalog in catalog_mapping:
                parts[0] = catalog_mapping[catalog]
            if schema_mapping and schema in schema_mapping:
                parts[1] = schema_mapping[schema]
        
        return '.'.join(parts)
    
    # Transform table identifiers
    if 'data_sources' in transformed:
        tables = transformed['data_sources'].get('tables', [])
        for table in tables:
            if 'identifier' in table:
                table['identifier'] = transform_identifier(table['identifier'])
    
    # Transform function identifiers
    if 'instructions' in transformed:
        functions = transformed['instructions'].get('sql_functions', [])
        for func in functions:
            if 'identifier' in func:
                func['identifier'] = transform_identifier(func['identifier'])
    
    return transformed

# COMMAND ----------

# Transform configs for target
transformed_configs = {}

print("TRANSFORMING CONFIGS FOR TARGET")
print("=" * 60)

for name, config in exported_configs.items():
    transformed = transform_config_for_target(
        config,
        target_warehouse_id=TARGET_WAREHOUSE_ID,
        catalog_mapping=CATALOG_MAPPING,
        schema_mapping=SCHEMA_MAPPING
    )
    transformed_configs[name] = transformed
    
    print(f"✓ Transformed: {config.get('title')}")
    print(f"    Warehouse: {config.get('warehouse_id')} → {TARGET_WAREHOUSE_ID}")

# COMMAND ----------

# Show transformed config
if transformed_configs:
    first_key = list(transformed_configs.keys())[0]
    print(f"TRANSFORMED CONFIG: {first_key}")
    print("=" * 60)
    print(yaml.dump(transformed_configs[first_key], default_flow_style=False)[:1000])

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Step 6: Save Migration Configs
# MAGIC
# MAGIC Save the transformed configurations for deployment.

# COMMAND ----------

# =============================================================================
# PROJECT CONFIGURATION - UPDATE THESE VALUES
# =============================================================================
from genie_forge import ProjectPaths, is_running_on_databricks, ensure_directory

# The same catalog and schema are used for tables and volume storage
CATALOG = "your_catalog"             # Unity Catalog name
SCHEMA = "default"                   # Schema name
VOLUME_NAME = "genie_forge"          # Volume name for file storage

# Create project paths for migration output
paths = ProjectPaths(
    project_name="migration",
    catalog=CATALOG,
    schema=SCHEMA,
    volume_name=VOLUME_NAME,
)

MIGRATION_DIR = paths.root

if is_running_on_databricks():
    print(f"🔷 Running on Databricks - Using Volume: {MIGRATION_DIR}")
else:
    print(f"💻 Running locally - Using path: {MIGRATION_DIR}")

ensure_directory(MIGRATION_DIR)

print("SAVING MIGRATION CONFIGS")
print("=" * 60)

for name, config in transformed_configs.items():
    file_path = f"{MIGRATION_DIR}/{name}.yaml"
    
    # Wrap in spaces array for genie-forge format
    genie_config = {
        "version": 1,
        "spaces": [{
            "space_id": name,
            **config
        }]
    }
    
    with open(file_path, 'w') as f:
        yaml.dump(genie_config, f, default_flow_style=False)
    
    print(f"✓ Saved: {file_path}")

print(f"\n✓ Configs saved to: {MIGRATION_DIR}")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Step 7: Deploy to Target Workspace
# MAGIC
# MAGIC Use the standard plan/apply workflow to deploy to target.
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC # From CLI with target profile
# MAGIC # Local:
# MAGIC genie-forge plan --env prod --profile PROD --config ./migration/
# MAGIC genie-forge apply --env prod --profile PROD --config ./migration/ --auto-approve
# MAGIC
# MAGIC # Databricks (using Unity Catalog Volume):
# MAGIC # genie-forge plan --env prod --profile PROD --config /Volumes/.../migration/
# MAGIC # genie-forge apply --env prod --profile PROD --config /Volumes/.../migration/ --auto-approve
# MAGIC ```

# COMMAND ----------

# In a real migration, you would:
# 1. Connect to target workspace with target profile
# 2. Run plan to preview
# 3. Run apply to deploy

print("DEPLOY TO TARGET WORKSPACE")
print("=" * 60)
print()
print("To deploy via CLI:")
print()
print(f"  # Preview changes")
print(f"  genie-forge plan --env prod --profile {TARGET_PROFILE} \\")
print(f"      --config {MIGRATION_DIR}/")
print()
print(f"  # Apply changes")
print(f"  genie-forge apply --env prod --profile {TARGET_PROFILE} \\")
print(f"      --config {MIGRATION_DIR}/ --auto-approve")
print()
print("Or use space-create for individual spaces:")
print()
for name in transformed_configs.keys():
    print(f"  genie-forge space-create --from-file {MIGRATION_DIR}/{name}.yaml \\")
    print(f"      --profile {TARGET_PROFILE}")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Alternative: Direct Clone
# MAGIC
# MAGIC For simple migrations, you can use `space-clone` directly:
# MAGIC
# MAGIC ```bash
# MAGIC # Clone to file (for review/editing)
# MAGIC genie-forge space-clone <source-id> \
# MAGIC     --name "Migrated Space" \
# MAGIC     --to-file migration.yaml \
# MAGIC     --profile DEV
# MAGIC
# MAGIC # Create in target from file
# MAGIC genie-forge space-create \
# MAGIC     --from-file migration.yaml \
# MAGIC     --set "warehouse_id=<target_warehouse>" \
# MAGIC     --profile PROD
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Migration Checklist
# MAGIC
# MAGIC Before migrating, verify:
# MAGIC
# MAGIC | Item | Check |
# MAGIC |------|-------|
# MAGIC | Target warehouse exists | `genie-forge space-list --profile TARGET` |
# MAGIC | Tables exist in target | Check Unity Catalog |
# MAGIC | Functions exist in target | If using SQL functions |
# MAGIC | Permissions configured | Users can access tables |
# MAGIC | Catalog/schema names correct | After transformation |

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Summary
# MAGIC
# MAGIC **Migration Steps:**
# MAGIC
# MAGIC 1. **Export** - `space-export` from source workspace
# MAGIC 2. **Transform** - Update warehouse, catalog, schema
# MAGIC 3. **Deploy** - `plan` + `apply` to target workspace
# MAGIC
# MAGIC **CLI Quick Reference:**
# MAGIC
# MAGIC ```bash
# MAGIC # Export from source
# MAGIC genie-forge space-export --pattern "Sales*" --output-dir ./migration/ --profile DEV
# MAGIC
# MAGIC # Deploy to target
# MAGIC genie-forge apply --env prod --profile PROD --config ./migration/ --auto-approve
# MAGIC ```
# MAGIC
# MAGIC **Key Considerations:**
# MAGIC
# MAGIC - Always transform warehouse IDs for target
# MAGIC - Map catalog/schema names if different
# MAGIC - Verify tables exist in target before deploying
# MAGIC - Use `--dry-run` to preview before actual migration
# MAGIC
# MAGIC ## Next Steps
# MAGIC
# MAGIC - **Notebook 05**: Advanced Patterns (programmatic API, self-joins)
