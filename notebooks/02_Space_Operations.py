# Databricks notebook source
# MAGIC %md
# MAGIC # Genie-Forge: Space Operations
# MAGIC
# MAGIC This notebook covers **space-*** commands for working with Genie spaces:
# MAGIC
# MAGIC | Command | Purpose |
# MAGIC |---------|---------|
# MAGIC | `space-list` | List all spaces in workspace |
# MAGIC | `space-get` | Get detailed space information |
# MAGIC | `space-find` | Search spaces by name pattern |
# MAGIC | `space-create` | Create a new space |
# MAGIC | `space-export` | Export space configs to files |
# MAGIC | `space-clone` | Clone an existing space |
# MAGIC | `space-delete` | Delete a space |
# MAGIC
# MAGIC ## Use Cases
# MAGIC - Explore existing spaces in a workspace
# MAGIC - Export spaces for backup or migration
# MAGIC - Create spaces from CLI or config files
# MAGIC - Clone spaces for testing
# MAGIC
# MAGIC ## Prerequisites
# MAGIC - Complete **Notebook 00** (Setup)
# MAGIC - **On Databricks**: Unity Catalog Volume configured for file exports
# MAGIC - **On Local Machine**: Write access to local directory
# MAGIC
# MAGIC ## Time: ~15 minutes

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

from genie_forge import GenieClient, __version__
from databricks.sdk import WorkspaceClient
import json
import yaml

print(f"✓ Genie-Forge v{__version__}")

w = WorkspaceClient()
client = GenieClient(client=w)
print(f"✓ Connected as: {w.current_user.me().user_name}")
print(f"✓ Workspace: {w.config.host}")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 1. List All Spaces (space-list)
# MAGIC
# MAGIC List all Genie spaces in the workspace with pagination support.
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC genie-forge space-list
# MAGIC genie-forge space-list --limit 50
# MAGIC genie-forge space-list --profile PROD
# MAGIC ```

# COMMAND ----------

# List all spaces (handles pagination automatically)
all_spaces = client.list_spaces()

print(f"WORKSPACE SPACES: {len(all_spaces)} total")
print("=" * 80)
print(f"{'Title':<35} {'Creator':<25} {'ID'}")
print("-" * 80)

for space in all_spaces[:20]:  # Show first 20
    title = (space.get('title') or 'Untitled')[:33]
    creator = (space.get('creator') or 'Unknown')[:23]
    space_id = space.get('id', 'N/A')[:20]
    print(f"{title:<35} {creator:<25} {space_id}...")

if len(all_spaces) > 20:
    print(f"\n... and {len(all_spaces) - 20} more spaces")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 2. Get Space Details (space-get)
# MAGIC
# MAGIC Get detailed information about a specific space.
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC genie-forge space-get <space-id>
# MAGIC genie-forge space-get --name "Sales Analytics"
# MAGIC genie-forge space-get <space-id> --raw  # Full JSON output
# MAGIC ```

# COMMAND ----------

if all_spaces:
    # Get details for the first space
    sample_space_id = all_spaces[0].get('id')
    
    print(f"SPACE DETAILS")
    print("=" * 60)
    
    space = client.get_space(sample_space_id, include_serialized=True)
    
    print(f"Title:       {space.get('title')}")
    print(f"ID:          {space.get('id')}")
    print(f"Warehouse:   {space.get('warehouse_id')}")
    print(f"Creator:     {space.get('creator')}")
    print(f"Parent Path: {space.get('parent_path', 'N/A')}")
    
    # Parse serialized_space for more details
    serialized = space.get('serialized_space', {})
    if isinstance(serialized, str):
        serialized = json.loads(serialized)
    
    # Tables
    data_sources = serialized.get('data_sources', {})
    tables = data_sources.get('tables', [])
    print(f"\nTables ({len(tables)}):")
    for table in tables[:5]:
        identifier = table.get('identifier', 'Unknown')
        print(f"  • {identifier}")
    if len(tables) > 5:
        print(f"  ... and {len(tables) - 5} more")
    
    # Instructions
    instructions = serialized.get('instructions', {})
    text_instructions = instructions.get('text_instructions', [])
    sql_functions = instructions.get('sql_functions', [])
    print(f"\nInstructions: {len(text_instructions)} text, {len(sql_functions)} functions")
    
    # Sample questions
    config = serialized.get('config', {})
    questions = config.get('sample_questions', [])
    print(f"Sample Questions: {len(questions)}")
else:
    print("No spaces found in workspace")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 3. Find Spaces by Name (space-find)
# MAGIC
# MAGIC Search for spaces using name patterns (supports wildcards).
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC genie-forge space-find --name "Sales*"
# MAGIC genie-forge space-find --name "*Analytics*"
# MAGIC genie-forge find --name "Demo"  # Alias
# MAGIC ```

# COMMAND ----------

# Search patterns to try
search_patterns = ["*Demo*", "*Analytics*", "*Sales*", "*Test*"]

for pattern in search_patterns:
    matches = client.find_spaces_by_name(pattern)
    
    print(f"\nPattern: '{pattern}' → {len(matches)} match(es)")
    if matches:
        for space in matches[:3]:
            print(f"  • {space.get('title')} (ID: {space.get('id')[:12]}...)")
        if len(matches) > 3:
            print(f"  ... and {len(matches) - 3} more")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 4. Create a Space (space-create)
# MAGIC
# MAGIC Create a new Genie space using CLI flags or a config file.
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC # From CLI flags
# MAGIC genie-forge space-create "My Space" \
# MAGIC     --warehouse-id abc123 \
# MAGIC     --tables "catalog.schema.table1,catalog.schema.table2"
# MAGIC
# MAGIC # From config file
# MAGIC genie-forge space-create --from-file config.yaml
# MAGIC
# MAGIC # From file with overrides
# MAGIC genie-forge space-create --from-file template.yaml \
# MAGIC     --set "title=Custom Title" \
# MAGIC     --set "warehouse_id=new_wh"
# MAGIC
# MAGIC # Dry run (preview only)
# MAGIC genie-forge space-create --from-file config.yaml --dry-run
# MAGIC ```

# COMMAND ----------

# Example: Build a space config programmatically
from genie_forge.models import SpaceConfig

# Method 1: Minimal config
minimal_config = SpaceConfig.minimal(
    space_id="notebook_demo_space",
    title="Notebook Demo Space",
    warehouse_id="your_warehouse_id",  # Replace with actual ID
    tables=["catalog.schema.table"],    # Replace with actual table
)

print("MINIMAL SPACE CONFIG")
print("=" * 60)
print(f"Space ID:  {minimal_config.space_id}")
print(f"Title:     {minimal_config.title}")
print(f"Warehouse: {minimal_config.warehouse_id}")
print(f"Tables:    {len(minimal_config.data_sources.tables)}")

# COMMAND ----------

# Method 2: Full config with all options
full_config = {
    "title": "Full Demo Space",
    "warehouse_id": "your_warehouse_id",
    "description": "A comprehensive demo space",
    "data_sources": {
        "tables": [
            {
                "identifier": "catalog.schema.table1",
                "description": ["Main data table"]
            }
        ]
    },
    "sample_questions": [
        "Show me the top 10 records",
        "What is the total count?"
    ],
    "instructions": {
        "text_instructions": [
            {"content": "Always include relevant context in answers"}
        ]
    }
}

print("\nFULL SPACE CONFIG (YAML format)")
print("=" * 60)
print(yaml.dump(full_config, default_flow_style=False))

# COMMAND ----------

# To actually create the space:
# result = client.create_space(full_config)
# print(f"Created space: {result['id']}")

print("⚠️ Uncomment the code above to actually create the space")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 5. Export Spaces (space-export)
# MAGIC
# MAGIC Export existing space configurations to YAML/JSON files.
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC # Export all spaces
# MAGIC # Local:      genie-forge space-export --output-dir ./exports/
# MAGIC # Databricks: genie-forge space-export --output-dir /Volumes/<catalog>/<schema>/<volume>/exports/
# MAGIC
# MAGIC # Export by pattern
# MAGIC genie-forge space-export --pattern "Sales*" --output-dir ./exports/
# MAGIC
# MAGIC # Export specific space
# MAGIC genie-forge space-export --space-id abc123 --output-dir ./exports/
# MAGIC
# MAGIC # Export with exclusions
# MAGIC genie-forge space-export --pattern "*" --exclude "*Test*" --output-dir ./exports/
# MAGIC
# MAGIC # JSON format
# MAGIC genie-forge space-export --output-dir ./exports/ --format json
# MAGIC ```

# COMMAND ----------

def build_export_config(space: dict) -> dict:
    """Build an export-ready configuration from a space (lossless).
    
    Preserves all API v2 fields including:
    - sql_snippets (filters, expressions, measures)
    - parameters and usage_guidance in example questions
    - join aliases and relationship types
    - enable_format_assistance and enable_entity_matching
    """
    # Parse serialized_space
    serialized = space.get('serialized_space', {})
    if isinstance(serialized, str):
        serialized = json.loads(serialized)
    
    config = {
        "version": serialized.get('version', 2),
        "title": space.get('title'),
        "warehouse_id": space.get('warehouse_id'),
    }
    
    # Add optional fields if present
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
    if serialized.get('config', {}).get('sample_questions'):
        config['sample_questions'] = serialized['config']['sample_questions']
    
    return config

# COMMAND ----------

# Export example
if all_spaces:
    sample_space = all_spaces[0]
    full_space = client.get_space(sample_space['id'], include_serialized=True)
    
    export_config = build_export_config(full_space)
    
    print("EXPORTED CONFIGURATION")
    print("=" * 60)
    print(yaml.dump(export_config, default_flow_style=False)[:1500])
    if len(yaml.dump(export_config)) > 1500:
        print("... (truncated)")
    
    # To save to file:
    # import re
    # OUTPUT_DIR = "./exports"  # or /Volumes/... on Databricks
    # safe_name = re.sub(r'[^\w\s-]', '', export_config['title'].lower())
    # safe_name = re.sub(r'[\s-]+', '_', safe_name)
    # with open(f'{OUTPUT_DIR}/{safe_name}.yaml', 'w') as f:
    #     yaml.dump(export_config, f)
else:
    print("No spaces to export")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 6. Clone a Space (space-clone)
# MAGIC
# MAGIC Clone an existing space to create a copy (same or different workspace).
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC # Clone to same workspace
# MAGIC genie-forge space-clone <space-id> --name "Cloned Space" --to-workspace
# MAGIC
# MAGIC # Clone to file (for cross-workspace migration)
# MAGIC genie-forge space-clone <space-id> --name "Cloned Space" --to-file clone.yaml
# MAGIC
# MAGIC # Clone with different warehouse
# MAGIC genie-forge space-clone <space-id> --name "Test Clone" \
# MAGIC     --warehouse-id new_wh123 --to-workspace
# MAGIC
# MAGIC # Dry run
# MAGIC genie-forge space-clone <space-id> --name "Clone" --to-workspace --dry-run
# MAGIC ```

# COMMAND ----------

if all_spaces:
    source_space_id = all_spaces[0]['id']
    source_space = client.get_space(source_space_id, include_serialized=True)
    
    print("CLONE PREVIEW")
    print("=" * 60)
    print(f"Source:      {source_space.get('title')}")
    print(f"Source ID:   {source_space_id[:20]}...")
    print()
    
    # Build clone config
    clone_config = build_export_config(source_space)
    clone_config['title'] = f"Clone of {source_space.get('title')}"
    
    print(f"Clone Title: {clone_config['title']}")
    print(f"Tables:      {len(clone_config.get('data_sources', {}).get('tables', []))}")
    
    print()
    print("To clone to workspace:")
    print("  result = client.create_space(clone_config)")
    print()
    print("To clone to file:")
    print("  with open('clone.yaml', 'w') as f:")
    print("      yaml.dump(clone_config, f)")
else:
    print("No spaces to clone")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 7. Delete a Space (space-delete)
# MAGIC
# MAGIC Delete a space from the workspace (not tracked in state).
# MAGIC
# MAGIC **CLI equivalent:**
# MAGIC ```bash
# MAGIC genie-forge space-delete <space-id>
# MAGIC genie-forge space-delete <space-id> --force  # Skip confirmation
# MAGIC ```

# COMMAND ----------

# Delete is a destructive operation - use with caution!
print("SPACE DELETE")
print("=" * 60)
print("⚠️  This operation permanently deletes a space from the workspace.")
print()
print("Usage:")
print("  # Delete by ID")
print("  client.delete_space('space-id-here')")
print()
print("  # CLI")
print("  genie-forge space-delete <space-id> --force")
print()
print("Note: Use 'destroy' command for managed spaces (tracked in state)")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Summary
# MAGIC
# MAGIC | Command | Purpose | Key Options |
# MAGIC |---------|---------|-------------|
# MAGIC | `space-list` | List all spaces | `--limit`, `--profile` |
# MAGIC | `space-get` | Get space details | `--name`, `--raw` |
# MAGIC | `space-find` | Search by pattern | `--name "pattern*"` |
# MAGIC | `space-create` | Create new space | `--from-file`, `--set` |
# MAGIC | `space-export` | Export to files | `--pattern`, `--format` |
# MAGIC | `space-clone` | Clone a space | `--to-workspace`, `--to-file` |
# MAGIC | `space-delete` | Delete a space | `--force` |
# MAGIC
# MAGIC ## CLI Quick Reference
# MAGIC
# MAGIC ```bash
# MAGIC # Exploration
# MAGIC genie-forge space-list
# MAGIC genie-forge space-get <id>
# MAGIC genie-forge space-find --name "Sales*"
# MAGIC
# MAGIC # Creation
# MAGIC genie-forge space-create "Title" --warehouse-id wh123 --tables cat.sch.tbl
# MAGIC genie-forge space-create --from-file config.yaml
# MAGIC
# MAGIC # Export & Clone
# MAGIC genie-forge space-export --output-dir ./exports/
# MAGIC genie-forge space-clone <id> --name "Clone" --to-workspace
# MAGIC ```
# MAGIC
# MAGIC ## Next Steps
# MAGIC
# MAGIC - **Notebook 03**: State Management (tracking, drift detection)
# MAGIC - **Notebook 04**: Cross-Workspace Migration
