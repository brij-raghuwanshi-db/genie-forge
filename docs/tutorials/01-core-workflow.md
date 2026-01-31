---
title: Core Workflow
description: The validate → plan → apply → status workflow
---

# 01 - Core Workflow

This notebook demonstrates the core Genie-Forge workflow: **validate → plan → apply → status → destroy**.

## Setup

```python
from genie_forge import ProjectPaths

# Use same configuration as setup notebook
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

## The Workflow

<div class="workflow-diagram">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 150" style="max-width: 100%; height: auto;">
  <defs>
    <marker id="arr1" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#7c3aed"/>
    </marker>
    <linearGradient id="grad1" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#8b5cf6"/>
      <stop offset="100%" style="stop-color:#6d28d9"/>
    </linearGradient>
    <linearGradient id="gradGreen1" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#10b981"/>
      <stop offset="100%" style="stop-color:#059669"/>
    </linearGradient>
    <filter id="sh1"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#000" flood-opacity="0.2"/></filter>
  </defs>
  <style>
    .box1 { filter: url(#sh1); }
    .txt1 { fill: white; font-family: system-ui, sans-serif; font-size: 13px; font-weight: 600; }
    .flow1 { stroke: #7c3aed; stroke-width: 2; fill: none; stroke-dasharray: 8 4; animation: move1 0.5s linear infinite; }
    @keyframes move1 { 0% { stroke-dashoffset: 0; } 100% { stroke-dashoffset: -12; } }
    .live1 { animation: pulse1 1.5s infinite; }
    @keyframes pulse1 { 50% { opacity: 0.6; } }
  </style>
  <g class="live1"><rect x="630" y="8" width="55" height="20" rx="10" fill="#10b981"/><text x="657" y="22" text-anchor="middle" fill="white" font-family="system-ui" font-size="10" font-weight="bold">LIVE</text></g>
  <rect class="box1" x="20" y="50" width="90" height="45" rx="8" fill="url(#grad1)"/>
  <text class="txt1" x="65" y="78" text-anchor="middle">validate</text>
  <path class="flow1" d="M 110 72 L 145 72" marker-end="url(#arr1)"/>
  <rect class="box1" x="150" y="50" width="70" height="45" rx="8" fill="url(#grad1)"/>
  <text class="txt1" x="185" y="78" text-anchor="middle">plan</text>
  <path class="flow1" d="M 220 72 L 255 72" marker-end="url(#arr1)"/>
  <polygon class="box1" points="305,50 355,72 305,95 255,72" fill="url(#gradGreen1)"/>
  <text class="txt1" x="305" y="77" text-anchor="middle" font-size="12">Review</text>
  <path class="flow1" d="M 355 72 L 390 72" marker-end="url(#arr1)"/>
  <text x="367" y="62" fill="#10b981" font-size="9">Approve</text>
  <rect class="box1" x="395" y="50" width="70" height="45" rx="8" fill="url(#grad1)"/>
  <text class="txt1" x="430" y="78" text-anchor="middle">apply</text>
  <path class="flow1" d="M 465 72 L 500 72" marker-end="url(#arr1)"/>
  <rect class="box1" x="505" y="50" width="70" height="45" rx="8" fill="url(#grad1)"/>
  <text class="txt1" x="540" y="78" text-anchor="middle">status</text>
  <path class="flow1" d="M 575 72 L 610 72" marker-end="url(#arr1)"/>
  <rect class="box1" x="615" y="50" width="60" height="45" rx="8" fill="url(#grad1)"/>
  <text class="txt1" x="645" y="78" text-anchor="middle">drift</text>
  <path class="flow1" d="M 305 95 L 305 125 L 65 125 L 65 100" marker-end="url(#arr1)"/>
  <text x="185" y="138" text-anchor="middle" fill="#ef4444" font-family="system-ui" font-size="9">Reject - Edit Config</text>
</svg>
</div>

## Step 1: Validate Configuration

Check your YAML files for syntax errors and schema compliance:

```python
# Validate all configurations
!genie-forge validate --config {paths.spaces_dir}
```

For stricter validation:

```python
# Strict mode fails on warnings too
!genie-forge validate --config {paths.spaces_dir} --strict
```

## Step 2: Plan Changes

Preview what will be created, updated, or destroyed:

```python
# Plan for dev environment
!genie-forge plan --env dev --config {paths.spaces_dir} --state {paths.state_file}
```

The plan shows:

- **CREATE** - New spaces to be created
- **UPDATE** - Existing spaces with changes
- **DESTROY** - Spaces to be removed

## Step 3: Apply Changes

Deploy the configuration to your workspace:

```python
# Apply the plan
!genie-forge apply --env dev --config {paths.spaces_dir} --state {paths.state_file}
```

For safety, you can use `--dry-run` first:

```python
# Preview without making changes
!genie-forge apply --env dev --config {paths.spaces_dir} --state {paths.state_file} --dry-run
```

## Step 4: Check Status

View the current deployment status:

```python
# Show deployed spaces
!genie-forge status --env dev --state {paths.state_file}
```

## Step 5: Detect Drift

Check if spaces have been modified outside of Genie-Forge:

```python
# Check for drift
!genie-forge drift --env dev --state {paths.state_file}
```

## Step 6: Destroy (Optional)

Remove deployed spaces:

```python
# Preview destruction
!genie-forge destroy --env dev --state {paths.state_file} --dry-run

# Actually destroy (uncomment to run)
# !genie-forge destroy --env dev --state {paths.state_file}
```

## Programmatic Workflow

You can also use the Python API:

```python
from genie_forge import GenieClient, StateManager
from genie_forge.parsers import MetadataParser

# Parse configurations
parser = MetadataParser(env="dev")
configs = parser.parse_directory(str(paths.spaces_dir))

# Create client and state manager
client = GenieClient()
state = StateManager(state_file=paths.state_file)

# Plan changes
plan = state.plan(configs, client, env="dev")
print(f"Creates: {len(plan.creates)}")
print(f"Updates: {len(plan.updates)}")
print(f"Destroys: {len(plan.destroys)}")

# Apply if there are changes
if plan.has_changes:
    results = state.apply(plan, client)
    print(f"✓ Applied {len(results['created'])} creates")
```

## Next Steps

- [02 - Space Operations](02-space-operations.md) - Explore and manage spaces
- [03 - State Management](03-state-management.md) - Work with state files
