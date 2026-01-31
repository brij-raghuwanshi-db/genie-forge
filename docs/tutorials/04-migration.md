---
title: Cross-Workspace Migration
description: Migrate Genie spaces between Databricks workspaces
---

# 04 - Cross-Workspace Migration

This notebook demonstrates migrating Genie spaces from one Databricks workspace to another.

## Why Migrate with Genie-Forge?

Migrating Genie spaces manually means recreating each space from scratch in the target workspace. With Genie-Forge, you export once and deploy anywhere.

### Time Savings

| Scenario | Manual Migration | With Genie-Forge |
|----------|------------------|------------------|
| Migrate 50 spaces to prod | Days of manual work | ~10 minutes |
| Ensure consistency | "Hope it matches dev" | Exact same YAML |
| Audit trail | None | Git commits |
| Rollback a migration | Recreate manually | `git revert` + `apply` |
| Deploy to new region | Repeat everything | Add environment file |

### Common Use Cases

- **Dev → Staging → Prod** — Standard CI/CD promotion
- **Regional deployment** — US, EU, APAC workspaces with same spaces
- **Disaster recovery** — Rebuild portfolio from Git in new workspace
- **Tenant migration** — Move customer spaces between isolated workspaces
- **Workspace consolidation** — Merge multiple workspaces

!!! tip "Key Benefit"
    The same YAML configuration works across all environments. Only the variables (warehouse IDs, catalogs, schemas) change.

## Migration Overview

<div class="workflow-diagram">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200" style="max-width: 100%; height: auto;">
  <defs>
    <marker id="migArr" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#7c3aed"/>
    </marker>
    <linearGradient id="sourceG" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#3b82f6"/><stop offset="100%" style="stop-color:#2563eb"/>
    </linearGradient>
    <linearGradient id="filesG" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#f59e0b"/><stop offset="100%" style="stop-color:#d97706"/>
    </linearGradient>
    <linearGradient id="targetG" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#10b981"/><stop offset="100%" style="stop-color:#059669"/>
    </linearGradient>
    <filter id="migSh"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#000" flood-opacity="0.2"/></filter>
  </defs>
  <style>
    .stageM { filter: url(#migSh); }
    .stageTitleM { fill: white; font-family: system-ui, sans-serif; font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; }
    .nodeTextM { fill: white; font-family: system-ui, sans-serif; font-size: 12px; font-weight: 500; }
    .flowM { stroke: #7c3aed; stroke-width: 2.5; fill: none; stroke-dasharray: 10 5; animation: flowMig 0.6s linear infinite; }
    @keyframes flowMig { 0% { stroke-dashoffset: 0; } 100% { stroke-dashoffset: -15; } }
    .liveM { animation: livePulseM 1.5s infinite; }
    @keyframes livePulseM { 50% { opacity: 0.5; } }
  </style>
  <g class="liveM"><rect x="725" y="10" width="55" height="20" rx="10" fill="#10b981"/><text x="752" y="24" text-anchor="middle" fill="white" font-family="system-ui" font-size="10" font-weight="bold">LIVE</text></g>
  <g transform="translate(20, 35)">
    <rect class="stageM" width="200" height="130" rx="10" fill="url(#sourceG)" opacity="0.15"/>
    <rect width="200" height="26" rx="10" fill="url(#sourceG)"/>
    <text class="stageTitleM" x="100" y="18" text-anchor="middle">Source Workspace</text>
    <rect x="20" y="45" width="160" height="32" rx="6" fill="url(#sourceG)"/>
    <text class="nodeTextM" x="100" y="66" text-anchor="middle">Existing Space</text>
    <rect x="20" y="90" width="160" height="32" rx="6" fill="url(#sourceG)" opacity="0.8"/>
    <text class="nodeTextM" x="100" y="111" text-anchor="middle">space-export</text>
  </g>
  <path class="flowM" d="M 220 100 L 280 100" marker-end="url(#migArr)"/>
  <g transform="translate(290, 35)">
    <rect class="stageM" width="200" height="130" rx="10" fill="url(#filesG)" opacity="0.15"/>
    <rect width="200" height="26" rx="10" fill="url(#filesG)"/>
    <text class="stageTitleM" x="100" y="18" text-anchor="middle">Config Files</text>
    <rect x="20" y="45" width="160" height="32" rx="6" fill="url(#filesG)"/>
    <text class="nodeTextM" x="100" y="66" text-anchor="middle">YAML Config</text>
    <rect x="20" y="90" width="160" height="32" rx="6" fill="url(#filesG)" opacity="0.8"/>
    <text class="nodeTextM" x="100" y="111" text-anchor="middle">Edit Variables</text>
  </g>
  <path class="flowM" d="M 490 100 L 550 100" marker-end="url(#migArr)"/>
  <g transform="translate(560, 35)">
    <rect class="stageM" width="200" height="130" rx="10" fill="url(#targetG)" opacity="0.15"/>
    <rect width="200" height="26" rx="10" fill="url(#targetG)"/>
    <text class="stageTitleM" x="100" y="18" text-anchor="middle">Target Workspace</text>
    <rect x="20" y="40" width="70" height="28" rx="6" fill="url(#targetG)"/>
    <text class="nodeTextM" x="55" y="59" text-anchor="middle" font-size="11">plan</text>
    <rect x="110" y="40" width="70" height="28" rx="6" fill="url(#targetG)"/>
    <text class="nodeTextM" x="145" y="59" text-anchor="middle" font-size="11">apply</text>
    <path class="flowM" d="M 90 54 L 105 54" marker-end="url(#migArr)" style="stroke-width: 1.5;"/>
    <rect x="20" y="85" width="160" height="35" rx="6" fill="url(#targetG)" opacity="0.9"/>
    <text class="nodeTextM" x="100" y="108" text-anchor="middle">New Space</text>
  </g>
</svg>
</div>

## Setup

```python
from genie_forge import ProjectPaths

CATALOG = "main"
SCHEMA = "default"
VOLUME_NAME = "genie_forge"
PROJECT_NAME = "migration"

paths = ProjectPaths(
    project_name=PROJECT_NAME,
    catalog=CATALOG,
    schema=SCHEMA,
    volume_name=VOLUME_NAME
)

paths.ensure_structure()
```

## Step 1: Export from Source Workspace

Connect to the source workspace and export spaces:

```python
# Using source workspace profile
!genie-forge space-list --profile SOURCE_WORKSPACE

# Export specific spaces
!genie-forge space-export --space-id "01abc123def456" --output-dir {paths.exports_dir} --profile SOURCE_WORKSPACE
```

### Bulk Export

```python
# Export all spaces from source
!genie-forge space-list --profile SOURCE_WORKSPACE --output json > /tmp/source_spaces.json

import json
with open('/tmp/source_spaces.json') as f:
    spaces = json.load(f)

for space in spaces:
    space_id = space['space_id']
    !genie-forge space-export --space-id {space_id} --output-dir {paths.exports_dir} --profile SOURCE_WORKSPACE
    print(f"  ✓ Exported: {space['title']}")
```

## Step 2: Modify Configuration

Update the exported configs for the target workspace:

```python
from pathlib import Path
import yaml

# Read exported config
export_file = paths.exports_dir / "sales_analytics.yaml"
with open(export_file) as f:
    config = yaml.safe_load(f)

# Update for target workspace
# - Change warehouse ID
# - Update table references if catalogs differ
# - Modify any workspace-specific settings

config['spaces'][0]['warehouse_id'] = '${TARGET_WAREHOUSE_ID}'

# If table catalog is different
for i, table in enumerate(config['spaces'][0].get('tables', [])):
    # Replace source catalog with target catalog
    config['spaces'][0]['tables'][i] = table.replace('source_catalog', 'target_catalog')

# Save to spaces directory
target_file = paths.spaces_dir / "sales_analytics.yaml"
with open(target_file, 'w') as f:
    yaml.dump(config, f, default_flow_style=False)

print(f"✓ Updated config saved to: {target_file}")
```

## Step 3: Create Target Environment

```python
# Create environment config for target workspace
env_config = '''
variables:
  TARGET_WAREHOUSE_ID: "target-warehouse-id-here"
'''

env_file = paths.root / "conf" / "environments" / "target.yaml"
env_file.parent.mkdir(parents=True, exist_ok=True)
env_file.write_text(env_config)
print(f"✓ Created: {env_file}")
```

## Step 4: Plan Migration

Preview what will be created in the target workspace:

```python
# Plan using target workspace profile
!genie-forge plan --env target --config {paths.spaces_dir} --state {paths.state_file} --profile TARGET_WORKSPACE
```

## Step 5: Apply to Target

Deploy to the target workspace:

```python
# Apply to target workspace
!genie-forge apply --env target --config {paths.spaces_dir} --state {paths.state_file} --profile TARGET_WORKSPACE
```

## Step 6: Verify Migration

```python
# Verify spaces in target
!genie-forge space-list --profile TARGET_WORKSPACE

# Check status
!genie-forge status --env target --state {paths.state_file} --profile TARGET_WORKSPACE
```

## Handling Different Catalogs

If your source and target workspaces use different Unity Catalogs:

```python
def migrate_table_references(config, source_catalog, target_catalog):
    """Update table references from source to target catalog."""
    for space in config.get('spaces', []):
        tables = space.get('tables', [])
        space['tables'] = [
            table.replace(f'{source_catalog}.', f'{target_catalog}.')
            for table in tables
        ]
    return config

# Usage
config = migrate_table_references(config, 'prod_catalog', 'dev_catalog')
```

## Migration Checklist

- [ ] Export spaces from source workspace
- [ ] Update warehouse IDs for target
- [ ] Update catalog/schema references if different
- [ ] Create target environment config
- [ ] Validate configuration
- [ ] Plan and review changes
- [ ] Apply to target workspace
- [ ] Verify deployment

## Next Steps

- [05 - Advanced Patterns](05-advanced.md) - Automation and CI/CD
