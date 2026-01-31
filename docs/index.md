---
title: Home
description: Infrastructure as Code for Databricks Genie Spaces
---

<div class="hero-section" markdown>

# Genie-Forge

**Infrastructure as Code for Databricks Genie Spaces**

[![Version](https://img.shields.io/badge/version-0.3.0-blue.svg)](changelog.md)
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)](guide/installation.md)
[![License](https://img.shields.io/badge/license-Apache%202.0-orange.svg)](https://opensource.org/licenses/Apache-2.0)

Define, version, and deploy Genie AI/BI dashboard spaces with a Terraform-like workflow.

<div class="hero-buttons">
  <a href="guide/getting-started/" class="primary">Get Started</a>
  <a href="tutorials/cli-playground/" class="secondary">Try Interactive Demo</a>
</div>

</div>

## Why Genie-Forge?

Managing Genie spaces manually through the UI doesn't scale. Genie-Forge brings **Infrastructure as Code** principles to Databricks Genie, enabling:

<div class="feature-grid" markdown>

<div class="feature-card" markdown>
### :material-file-code: Version Control
Define spaces in YAML files, track changes in Git, and collaborate with your team.
</div>

<div class="feature-card" markdown>
### :material-eye: Plan Before Apply  
Preview exactly what will change before deploying—no surprises.
</div>

<div class="feature-card" markdown>
### :material-sync: Drift Detection
Detect when spaces have been modified outside of your configuration.
</div>

<div class="feature-card" markdown>
### :material-rocket-launch: Multi-Environment
Deploy to dev, staging, and prod with environment-specific configurations.
</div>

<div class="feature-card" markdown>
### :material-lightning-bolt: Bulk Operations
Create or update hundreds of spaces in seconds with progress tracking.
</div>

<div class="feature-card" markdown>
### :material-laptop: Dual Environment
Run locally or in Databricks notebooks with automatic path detection.
</div>

<div class="feature-card" markdown>
### :material-swap-horizontal: Cross-Workspace Migration
Export from dev, deploy to prod. Same YAML, different environments. [Learn more](tutorials/04-migration.md)
</div>

</div>

## At a Glance

| Task | Manual UI | Genie-Forge |
|------|-----------|-------------|
| Create 100 spaces | Hours of clicking | `genie-forge apply` (seconds) |
| Track who changed what | Not possible | Git history |
| Deploy to production | Copy-paste from dev | `--env prod` |
| Migrate between workspaces | Recreate from scratch | Export → Apply |
| Detect configuration drift | Unknown | `genie-forge drift` |

## How It Works

<div class="workflow-diagram">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 280" style="max-width: 100%; height: auto;">
  <defs>
    <marker id="arrH" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#7c3aed"/>
    </marker>
    <filter id="shadowH" x="-10%" y="-10%" width="120%" height="130%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#000" flood-opacity="0.3"/>
    </filter>
    <linearGradient id="purpleH" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#8b5cf6"/><stop offset="100%" style="stop-color:#6d28d9"/>
    </linearGradient>
    <linearGradient id="greenH" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#10b981"/><stop offset="100%" style="stop-color:#059669"/>
    </linearGradient>
    <linearGradient id="blueH" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#3b82f6"/><stop offset="100%" style="stop-color:#2563eb"/>
    </linearGradient>
    <linearGradient id="orangeH" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#f59e0b"/><stop offset="100%" style="stop-color:#d97706"/>
    </linearGradient>
    <linearGradient id="pinkH" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#ec4899"/><stop offset="100%" style="stop-color:#db2777"/>
    </linearGradient>
  </defs>
  <style>
    .stageH { filter: url(#shadowH); }
    .stageTitleH { fill: white; font-family: system-ui, sans-serif; font-size: 11px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; }
    .nodeTextH { fill: white; font-family: system-ui, sans-serif; font-size: 12px; font-weight: 500; }
    .smallTextH { fill: #a1a1aa; font-family: system-ui, sans-serif; font-size: 10px; }
    .flowH { stroke: #7c3aed; stroke-width: 2; fill: none; stroke-dasharray: 8 4; animation: dashH 0.5s linear infinite; }
    .flowSlowH { stroke: #ec4899; stroke-width: 2; fill: none; stroke-dasharray: 8 4; animation: dashRevH 0.5s linear infinite; }
    @keyframes dashH { 0% { stroke-dashoffset: 0; } 100% { stroke-dashoffset: -12; } }
    @keyframes dashRevH { 0% { stroke-dashoffset: -12; } 100% { stroke-dashoffset: 0; } }
    .liveH { animation: blinkH 1.5s ease-in-out infinite; }
    @keyframes blinkH { 50% { opacity: 0.5; } }
  </style>
  <g class="liveH"><rect x="820" y="10" width="60" height="22" rx="11" fill="#10b981"/><text x="850" y="25" text-anchor="middle" fill="white" font-family="system-ui" font-size="11" font-weight="bold">LIVE</text></g>
  <g transform="translate(20, 40)">
    <rect class="stageH" width="150" height="120" rx="10" fill="url(#purpleH)" opacity="0.15"/>
    <rect width="150" height="28" rx="10" fill="url(#purpleH)"/>
    <text class="stageTitleH" x="75" y="19" text-anchor="middle">1. DEFINE</text>
    <rect x="15" y="45" width="120" height="28" rx="6" fill="url(#purpleH)"/>
    <text class="nodeTextH" x="75" y="64" text-anchor="middle">YAML Config</text>
    <rect x="15" y="85" width="120" height="28" rx="6" fill="url(#purpleH)" opacity="0.7"/>
    <text class="nodeTextH" x="75" y="104" text-anchor="middle">Variables</text>
  </g>
  <path class="flowH" d="M 170 100 L 200 100" marker-end="url(#arrH)"/>
  <g transform="translate(200, 40)">
    <rect class="stageH" width="150" height="120" rx="10" fill="url(#greenH)" opacity="0.15"/>
    <rect width="150" height="28" rx="10" fill="url(#greenH)"/>
    <text class="stageTitleH" x="75" y="19" text-anchor="middle">2. VALIDATE</text>
    <polygon points="75,55 130,85 75,115 20,85" fill="url(#greenH)" filter="url(#shadowH)"/>
    <text class="nodeTextH" x="75" y="90" text-anchor="middle">validate</text>
  </g>
  <path class="flowH" d="M 350 100 L 380 100" marker-end="url(#arrH)"/>
  <text x="360" y="90" class="smallTextH" fill="#10b981">Valid</text>
  <g transform="translate(380, 40)">
    <rect class="stageH" width="150" height="120" rx="10" fill="url(#blueH)" opacity="0.15"/>
    <rect width="150" height="28" rx="10" fill="url(#blueH)"/>
    <text class="stageTitleH" x="75" y="19" text-anchor="middle">3. PLAN</text>
    <rect x="15" y="45" width="120" height="28" rx="6" fill="url(#blueH)"/>
    <text class="nodeTextH" x="75" y="64" text-anchor="middle">plan</text>
    <rect x="15" y="85" width="120" height="28" rx="6" fill="url(#blueH)" opacity="0.7"/>
    <text class="nodeTextH" x="75" y="104" text-anchor="middle">Review</text>
  </g>
  <path class="flowH" d="M 530 100 L 560 100" marker-end="url(#arrH)"/>
  <text x="538" y="90" class="smallTextH" fill="#10b981">Approve</text>
  <g transform="translate(560, 40)">
    <rect class="stageH" width="150" height="120" rx="10" fill="url(#orangeH)" opacity="0.15"/>
    <rect width="150" height="28" rx="10" fill="url(#orangeH)"/>
    <text class="stageTitleH" x="75" y="19" text-anchor="middle">4. APPLY</text>
    <rect x="15" y="45" width="120" height="28" rx="6" fill="url(#orangeH)"/>
    <text class="nodeTextH" x="75" y="64" text-anchor="middle">apply</text>
    <rect x="15" y="85" width="120" height="28" rx="6" fill="url(#orangeH)" opacity="0.7"/>
    <text class="nodeTextH" x="75" y="104" text-anchor="middle">Deployed!</text>
  </g>
  <path class="flowH" d="M 710 100 L 740 100" marker-end="url(#arrH)"/>
  <g transform="translate(740, 40)">
    <rect class="stageH" width="150" height="120" rx="10" fill="url(#pinkH)" opacity="0.15"/>
    <rect width="150" height="28" rx="10" fill="url(#pinkH)"/>
    <text class="stageTitleH" x="75" y="19" text-anchor="middle">5. MONITOR</text>
    <rect x="15" y="45" width="120" height="28" rx="6" fill="url(#pinkH)"/>
    <text class="nodeTextH" x="75" y="64" text-anchor="middle">status</text>
    <rect x="15" y="85" width="120" height="28" rx="6" fill="url(#pinkH)" opacity="0.7"/>
    <text class="nodeTextH" x="75" y="104" text-anchor="middle">drift</text>
  </g>
  <path class="flowSlowH" d="M 815 170 C 815 230, 815 250, 600 250 L 200 250 C 95 250, 95 230, 95 180" marker-end="url(#arrH)"/>
  <text x="450" y="265" text-anchor="middle" class="smallTextH" fill="#ec4899">Changes Detected - Update Config</text>
</svg>
</div>

## Quick Start

=== "Install"

    ```bash
    pip install genie-forge
    ```

=== "Initialize"

    ```bash
    genie-forge init my-project
    cd my-project
    ```

=== "Configure"

    ```yaml title="conf/spaces/analytics.yaml"
    spaces:
      - title: Sales Analytics
        description: AI-powered sales insights
        warehouse_id: ${WAREHOUSE_ID}
        tables:
          - catalog.schema.sales
          - catalog.schema.customers
    ```

=== "Deploy"

    ```bash
    genie-forge plan --env dev
    genie-forge apply --env dev
    ```

## Command Overview

| Command | Description |
|---------|-------------|
| `genie-forge init` | Initialize a new project |
| `genie-forge validate` | Validate configuration files |
| `genie-forge plan` | Preview deployment changes |
| `genie-forge apply` | Deploy configuration |
| `genie-forge status` | Show deployment status |
| `genie-forge drift` | Detect configuration drift |
| `genie-forge destroy` | Remove deployed spaces |
| `genie-forge space-list` | List all workspace spaces |
| `genie-forge space-export` | Export space to YAML |

[View Full CLI Reference :material-arrow-right:](guide/cli.md){ .md-button }

## Use Cases

<div class="feature-grid" markdown>

<div class="feature-card" markdown>
### :material-source-branch: Dev → Staging → Prod
Promote Genie spaces through environments with confidence. Same YAML, different variables.
</div>

<div class="feature-card" markdown>
### :material-earth: Regional Deployment
Deploy identical spaces to US, EU, and APAC workspaces with environment-specific configs.
</div>

<div class="feature-card" markdown>
### :material-shield-refresh: Disaster Recovery
Rebuild your entire Genie space portfolio in a new workspace from version-controlled configs.
</div>

<div class="feature-card" markdown>
### :material-account-group: Team Collaboration
Multiple engineers can work on space configurations with Git branching and pull request reviews.
</div>

</div>

## Learn More

<div class="feature-grid" markdown>

<div class="feature-card" markdown>
### :material-book-open-variant: Architecture
Understand how Genie-Forge works under the hood.

[Explore Architecture :material-arrow-right:](reference/architecture.md)
</div>

<div class="feature-card" markdown>
### :material-notebook: Notebooks
Run Genie-Forge directly in Databricks notebooks.

[View Notebooks :material-arrow-right:](tutorials/notebooks-overview.md)
</div>

</div>
