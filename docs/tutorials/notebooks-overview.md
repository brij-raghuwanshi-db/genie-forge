---
title: Notebooks Overview
description: Running Genie-Forge in Databricks notebooks
---

# Databricks Notebooks

Genie-Forge provides ready-to-use notebooks for running workflows directly in Databricks. These notebooks automatically detect the environment and use Unity Catalog Volumes for file storage.

## Available Notebooks

| Notebook | Purpose | Key Features |
|----------|---------|--------------|
| [00 - Setup Prerequisites](00-setup.md) | Initial configuration | Authentication, paths, demo data |
| [01 - Core Workflow](01-core-workflow.md) | Main deployment flow | validate → plan → apply → status |
| [02 - Space Operations](02-space-operations.md) | Space management | list, get, find, export, clone |
| [03 - State Management](03-state-management.md) | State file operations | import, show, remove |
| [04 - Cross-Workspace Migration](04-migration.md) | Workspace migration | Export and redeploy |
| [05 - Advanced Patterns](05-advanced.md) | Advanced usage | Bulk ops, CI/CD, dynamic configs |

## Environment-Aware Paths

All notebooks use `ProjectPaths` for automatic environment detection:

```python
from genie_forge import ProjectPaths, is_running_on_databricks

# Configuration - same catalog/schema for tables AND volume storage
CATALOG = "main"
SCHEMA = "default" 
VOLUME_NAME = "genie_forge"
PROJECT_NAME = "demo"

# Auto-configures paths based on environment
paths = ProjectPaths(
    project_name=PROJECT_NAME,
    catalog=CATALOG,
    schema=SCHEMA,
    volume_name=VOLUME_NAME
)

print(f"Environment: {'Databricks' if is_running_on_databricks() else 'Local'}")
print(f"Project root: {paths.root}")
print(f"State file: {paths.state_file}")
print(f"Configs: {paths.spaces_dir}")
```

**On Databricks:**
```
/Volumes/main/default/genie_forge/demo/
├── conf/spaces/
├── exports/
└── .genie-forge.json
```

**On Local Machine:**
```
~/.genie-forge/demo/
├── conf/spaces/
├── exports/
└── .genie-forge.json
```

## Workflow Overview

<div class="workflow-diagram">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 750 400" style="max-width: 100%; height: auto;">
  <defs>
    <marker id="nArr" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#7c3aed"/>
    </marker>
    <linearGradient id="nbStart" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#10b981"/><stop offset="100%" style="stop-color:#059669"/>
    </linearGradient>
    <linearGradient id="nbPurple" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#8b5cf6"/><stop offset="100%" style="stop-color:#6d28d9"/>
    </linearGradient>
    <linearGradient id="nbBlue" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#3b82f6"/><stop offset="100%" style="stop-color:#2563eb"/>
    </linearGradient>
    <linearGradient id="nbOrange" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#f59e0b"/><stop offset="100%" style="stop-color:#d97706"/>
    </linearGradient>
    <filter id="nbSh"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#000" flood-opacity="0.2"/></filter>
  </defs>
  <style>
    .nbNode { filter: url(#nbSh); }
    .nbText { fill: white; font-family: system-ui, sans-serif; font-size: 11px; font-weight: 500; }
    .nbLabel { fill: #71717a; font-family: system-ui, sans-serif; font-size: 10px; }
    .nbFlow { stroke: #7c3aed; stroke-width: 2; fill: none; stroke-dasharray: 8 4; animation: nbMove 0.6s linear infinite; }
    @keyframes nbMove { 0% { stroke-dashoffset: 0; } 100% { stroke-dashoffset: -12; } }
    .liveNb { animation: nbPulse 1.5s infinite; }
    @keyframes nbPulse { 50% { opacity: 0.5; } }
  </style>
  <g class="liveNb"><rect x="680" y="10" width="55" height="20" rx="10" fill="#10b981"/><text x="707" y="24" text-anchor="middle" fill="white" font-family="system-ui" font-size="10" font-weight="bold">LIVE</text></g>
  <ellipse class="nbNode" cx="375" cy="35" rx="40" ry="20" fill="url(#nbStart)"/>
  <text class="nbText" x="375" y="40" text-anchor="middle">Start</text>
  <path class="nbFlow" d="M 375 55 L 375 75" marker-end="url(#nArr)"/>
  <rect class="nbNode" x="275" y="80" width="200" height="35" rx="6" fill="url(#nbPurple)"/>
  <text class="nbText" x="375" y="103" text-anchor="middle">00_Setup_Prerequisites</text>
  <path class="nbFlow" d="M 375 115 L 375 135" marker-end="url(#nArr)"/>
  <polygon class="nbNode" points="375,145 440,175 375,205 310,175" fill="url(#nbStart)"/>
  <text class="nbText" x="375" y="180" text-anchor="middle" font-size="10">Environment?</text>
  <path class="nbFlow" d="M 310 175 L 200 175" marker-end="url(#nArr)"/>
  <text class="nbLabel" x="255" y="165">Databricks</text>
  <rect class="nbNode" x="60" y="155" width="130" height="40" rx="6" fill="url(#nbBlue)"/>
  <text class="nbText" x="125" y="172" text-anchor="middle" font-size="10">Unity Catalog</text>
  <text class="nbText" x="125" y="186" text-anchor="middle" font-size="10">Volume</text>
  <path class="nbFlow" d="M 440 175 L 550 175" marker-end="url(#nArr)"/>
  <text class="nbLabel" x="480" y="165">Local</text>
  <rect class="nbNode" x="560" y="155" width="130" height="40" rx="6" fill="url(#nbBlue)"/>
  <text class="nbText" x="625" y="172" text-anchor="middle" font-size="10">~/.genie-forge/</text>
  <text class="nbText" x="625" y="186" text-anchor="middle" font-size="10">local files</text>
  <path class="nbFlow" d="M 125 195 L 125 230 L 330 230" marker-end="url(#nArr)"/>
  <path class="nbFlow" d="M 625 195 L 625 230 L 420 230" marker-end="url(#nArr)"/>
  <rect class="nbNode" x="275" y="215" width="200" height="35" rx="6" fill="url(#nbPurple)"/>
  <text class="nbText" x="375" y="238" text-anchor="middle">01_Core_Workflow</text>
  <path class="nbFlow" d="M 375 250 L 375 270" marker-end="url(#nArr)"/>
  <polygon class="nbNode" points="375,280 440,305 375,330 310,305" fill="url(#nbOrange)"/>
  <text class="nbText" x="375" y="310" text-anchor="middle" font-size="9">What next?</text>
  <path class="nbFlow" d="M 310 305 L 120 305 L 120 340" marker-end="url(#nArr)"/>
  <rect class="nbNode" x="40" y="345" width="160" height="35" rx="6" fill="url(#nbBlue)"/>
  <text class="nbText" x="120" y="368" text-anchor="middle" font-size="10">02_Space_Operations</text>
  <path class="nbFlow" d="M 340 330 L 260 355 L 260 345" marker-end="url(#nArr)"/>
  <rect class="nbNode" x="180" y="345" width="160" height="35" rx="6" fill="url(#nbBlue)"/>
  <text class="nbText" x="260" y="368" text-anchor="middle" font-size="10">03_State_Management</text>
  <path class="nbFlow" d="M 410 330 L 490 355 L 490 345" marker-end="url(#nArr)"/>
  <rect class="nbNode" x="410" y="345" width="160" height="35" rx="6" fill="url(#nbBlue)"/>
  <text class="nbText" x="490" y="368" text-anchor="middle" font-size="10">04_Migration</text>
  <path class="nbFlow" d="M 440 305 L 630 305 L 630 340" marker-end="url(#nArr)"/>
  <rect class="nbNode" x="550" y="345" width="160" height="35" rx="6" fill="url(#nbBlue)"/>
  <text class="nbText" x="630" y="368" text-anchor="middle" font-size="10">05_Advanced_Patterns</text>
</svg>
</div>

## Unified Catalog/Schema

A key principle in the notebooks: **the same catalog and schema are used for both data tables and Volume storage**.

```python
# This catalog/schema is used for:
# 1. Data tables that Genie spaces query
# 2. Volume storage for config and state files

CATALOG = "main"
SCHEMA = "default"

# Tables: main.default.employees, main.default.sales
# Volume: /Volumes/main/default/genie_forge/project/
```

This simplifies configuration—define catalog and schema once, use everywhere.

## Running CLI Commands

From notebooks, run CLI commands using `!` or `%sh`:

```python
# Using shell magic
!genie-forge whoami

# Or with subprocess for capturing output
import subprocess
result = subprocess.run(
    ["genie-forge", "space-list", "--output", "json"],
    capture_output=True, text=True
)
spaces = json.loads(result.stdout)
```

## Installing in Notebooks

```python
# Install genie-forge in notebook
%pip install genie-forge

# Or from a wheel file in Volume
%pip install /Volumes/main/default/genie_forge/wheels/genie_forge-0.3.0-py3-none-any.whl
```

## Getting Started

1. **Import the notebook** to your Databricks workspace
2. **Configure variables** at the top (catalog, schema, volume)
3. **Run setup cells** to initialize paths and authentication
4. **Follow the workflow** step by step

[Start with Setup Prerequisites →](00-setup.md){ .md-button .md-button--primary }
