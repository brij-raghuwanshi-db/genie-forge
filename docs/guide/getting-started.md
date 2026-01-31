---
title: Quick Start
description: Get up and running with Genie-Forge in 5 minutes
---

# Quick Start Guide

Get up and running with Genie-Forge in under 5 minutes.

## When to Use Genie-Forge

Genie-Forge is ideal when you need to:

| Scenario | Benefit |
|----------|---------|
| Manage **10+ Genie spaces** | Bulk operations save hours of clicking |
| Deploy across **multiple environments** | Same YAML, different variables |
| **Migrate** spaces between workspaces | Export → Apply workflow |
| Track **who changed what** | Git history for all changes |
| Ensure **consistency** between dev and prod | Identical configurations |
| **Collaborate** with a team | Pull request reviews for space changes |

!!! tip "Not sure?"
    If you're managing spaces through the UI and find yourself copy-pasting between environments, Genie-Forge will save you significant time.

## Prerequisites

- Python 3.9+
- Access to a Databricks workspace with Genie enabled
- Databricks CLI configured with a profile (or environment variables)

## Installation

=== "pip"

    ```bash
    pip install genie-forge
    ```

=== "pipx (isolated)"

    ```bash
    pipx install genie-forge
    ```

=== "From source"

    ```bash
    git clone https://github.com/brij-raghuwanshi-db/genie-forge.git
    cd genie-forge
    pip install -e .
    ```

## Verify Installation

```bash
genie-forge --version
genie-forge whoami
```

You should see your Databricks workspace URL and username.

## Initialize a Project

```bash
genie-forge init my-genie-project
cd my-genie-project
```

This creates:

```
my-genie-project/
├── conf/
│   ├── spaces/           # Space configurations
│   │   └── example.yaml
│   └── environments/     # Environment configs
│       ├── dev.yaml
│       └── prod.yaml
├── .genie-forge.json     # State file
└── .gitignore
```

## Create Your First Space

Edit `conf/spaces/my_space.yaml`:

```yaml
spaces:
  - title: My First Genie Space
    description: An AI-powered analytics dashboard
    warehouse_id: ${WAREHOUSE_ID}
    tables:
      - my_catalog.my_schema.sales
      - my_catalog.my_schema.customers
    instructions: |
      You are a helpful sales analyst. Help users understand
      their sales data and customer patterns.
```

## Set Environment Variables

Create `conf/environments/dev.yaml`:

```yaml
variables:
  WAREHOUSE_ID: "abc123def456"  # Your SQL Warehouse ID
```

## The Core Workflow

<div class="workflow-diagram">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 700 150" style="max-width: 100%; height: auto;">
  <defs>
    <marker id="arr2" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#7c3aed"/>
    </marker>
    <linearGradient id="grad2" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#8b5cf6"/>
      <stop offset="100%" style="stop-color:#6d28d9"/>
    </linearGradient>
    <linearGradient id="gradGreen2" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#10b981"/>
      <stop offset="100%" style="stop-color:#059669"/>
    </linearGradient>
    <filter id="sh2"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#000" flood-opacity="0.2"/></filter>
  </defs>
  <style>
    .box2 { filter: url(#sh2); }
    .txt2 { fill: white; font-family: system-ui, sans-serif; font-size: 13px; font-weight: 600; }
    .flow2 { stroke: #7c3aed; stroke-width: 2; fill: none; stroke-dasharray: 8 4; animation: move2 0.5s linear infinite; }
    @keyframes move2 { 0% { stroke-dashoffset: 0; } 100% { stroke-dashoffset: -12; } }
    .live2 { animation: pulse2 1.5s infinite; }
    @keyframes pulse2 { 50% { opacity: 0.6; } }
  </style>
  <g class="live2"><rect x="630" y="8" width="55" height="20" rx="10" fill="#10b981"/><text x="657" y="22" text-anchor="middle" fill="white" font-family="system-ui" font-size="10" font-weight="bold">LIVE</text></g>
  <rect class="box2" x="20" y="50" width="90" height="45" rx="8" fill="url(#grad2)"/>
  <text class="txt2" x="65" y="78" text-anchor="middle">validate</text>
  <path class="flow2" d="M 110 72 L 145 72" marker-end="url(#arr2)"/>
  <rect class="box2" x="150" y="50" width="70" height="45" rx="8" fill="url(#grad2)"/>
  <text class="txt2" x="185" y="78" text-anchor="middle">plan</text>
  <path class="flow2" d="M 220 72 L 255 72" marker-end="url(#arr2)"/>
  <polygon class="box2" points="305,50 355,72 305,95 255,72" fill="url(#gradGreen2)"/>
  <text class="txt2" x="305" y="77" text-anchor="middle" font-size="12">Review</text>
  <path class="flow2" d="M 355 72 L 390 72" marker-end="url(#arr2)"/>
  <text x="367" y="62" fill="#10b981" font-size="9">Approve</text>
  <rect class="box2" x="395" y="50" width="70" height="45" rx="8" fill="url(#grad2)"/>
  <text class="txt2" x="430" y="78" text-anchor="middle">apply</text>
  <path class="flow2" d="M 465 72 L 500 72" marker-end="url(#arr2)"/>
  <rect class="box2" x="505" y="50" width="70" height="45" rx="8" fill="url(#grad2)"/>
  <text class="txt2" x="540" y="78" text-anchor="middle">status</text>
  <path class="flow2" d="M 575 72 L 610 72" marker-end="url(#arr2)"/>
  <rect class="box2" x="615" y="50" width="60" height="45" rx="8" fill="url(#grad2)"/>
  <text class="txt2" x="645" y="78" text-anchor="middle">drift</text>
  <path class="flow2" d="M 305 95 L 305 125 L 65 125 L 65 100" marker-end="url(#arr2)"/>
  <text x="185" y="138" text-anchor="middle" fill="#ef4444" font-family="system-ui" font-size="9">Reject - Edit Config</text>
</svg>
</div>

### Step 1: Validate

Check your configuration for errors:

```bash
genie-forge validate --config conf/spaces/
```

### Step 2: Plan

Preview what will be created/updated:

```bash
genie-forge plan --env dev
```

Output:
```
Planning changes for environment: dev

+ my_first_genie_space (CREATE)
  title: My First Genie Space
  tables: 2

Plan: 1 to create, 0 to update, 0 to destroy
```

### Step 3: Apply

Deploy your configuration:

```bash
genie-forge apply --env dev
```

### Step 4: Verify

Check the deployment status:

```bash
genie-forge status --env dev
```

## Interactive CLI Demo

Try the commands in this interactive terminal:

<style>
.cli-terminal {
  background: #1e1e1e;
  border-radius: 8px;
  overflow: hidden;
  font-family: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
  font-size: 14px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
}
.cli-terminal-header {
  background: #3c3c3c;
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.cli-terminal-header .dot { width: 12px; height: 12px; border-radius: 50%; }
.cli-terminal-header .dot.red { background: #ff5f56; }
.cli-terminal-header .dot.yellow { background: #ffbd2e; }
.cli-terminal-header .dot.green { background: #27ca40; }
.cli-terminal-header .title { color: #888; margin-left: auto; margin-right: auto; font-size: 12px; }
.cli-terminal-body {
  padding: 16px;
  min-height: 250px;
  max-height: 400px;
  overflow-y: auto;
}
.cli-terminal-output {
  white-space: pre-wrap;
  word-wrap: break-word;
  color: #d4d4d4;
  line-height: 1.5;
  margin-bottom: 8px;
}
.cli-terminal-input-line {
  display: flex;
  align-items: center;
}
.cli-terminal-prompt {
  color: #4ec9b0;
  margin-right: 8px;
  user-select: none;
}
.cli-terminal-input {
  background: transparent;
  border: none;
  color: #d4d4d4;
  font-family: inherit;
  font-size: inherit;
  flex: 1;
  outline: none;
  caret-color: #4ec9b0;
}
</style>

<div class="cli-terminal">
  <div class="cli-terminal-header">
    <span class="dot red"></span>
    <span class="dot yellow"></span>
    <span class="dot green"></span>
    <span class="title">genie-forge demo</span>
  </div>
  <div class="cli-terminal-body">
    <div class="cli-terminal-output" id="cli-output"></div>
    <div class="cli-terminal-input-line">
      <span class="cli-terminal-prompt">$</span>
      <input type="text" class="cli-terminal-input" id="cli-input" placeholder="Type a command..." autocomplete="off" spellcheck="false">
    </div>
  </div>
</div>

<script>
(function() {
  function initTerminal() {
    const input = document.getElementById('cli-input');
    const output = document.getElementById('cli-output');
    if (!input || !output || input.dataset.initialized) return;
    input.dataset.initialized = 'true';
    
    const commands = {
      'help': `<span style="color:#4ec9b0">Available commands:</span>
  genie-forge --help     Show CLI help
  genie-forge whoami     Display workspace info
  genie-forge plan       Preview changes
  genie-forge apply      Deploy configuration
  genie-forge status     Show deployment status`,
      'genie-forge --help': `<span style="color:#4ec9b0">Usage:</span> genie-forge [OPTIONS] COMMAND [ARGS]...

  Genie-Forge: Infrastructure as Code for Databricks Genie Spaces

<span style="color:#4ec9b0">Setup Commands:</span>
  init           Initialize a new project
  profiles       List available Databricks CLI profiles
  whoami         Show current user and workspace

<span style="color:#4ec9b0">Demo Commands:</span>
  setup-demo     Create demo tables in Unity Catalog
  demo-status    Check if demo objects exist
  cleanup-demo   Remove demo tables

<span style="color:#4ec9b0">Deployment Commands:</span>
  validate       Validate configuration files
  plan           Preview deployment changes
  apply          Apply configuration to workspace
  status         Show deployment status
  drift          Detect configuration drift
  destroy        Remove deployed spaces

<span style="color:#4ec9b0">Space Commands:</span>
  space-list     List all Genie spaces
  space-get      Get detailed space information
  space-find     Search spaces by name
  space-create   Create a new space
  space-clone    Clone an existing space
  space-export   Export space to YAML
  space-delete   Delete a space

<span style="color:#4ec9b0">State Commands:</span>
  state-list     List tracked spaces in state
  state-show     Show detailed state info
  state-pull     Refresh state from workspace
  state-remove   Remove space from state
  state-import   Import existing spaces`,
      'genie-forge whoami': `<span style="color:#4ec9b0">Workspace:</span> https://dbc-example.cloud.databricks.com
<span style="color:#4ec9b0">User:</span> user@example.com
<span style="color:#4ec9b0">Profile:</span> DEFAULT`,
      'genie-forge plan': `<span style="color:#4ec9b0">Planning changes for environment: dev</span>

<span style="color:#6a9955">+ sales_analytics (CREATE)</span>
  title: Sales Analytics Dashboard
  tables: 3 tables

<span style="color:#dcdcaa">Plan: 1 to create, 0 to update, 0 to destroy</span>`,
      'genie-forge status': `<span style="color:#4ec9b0">Environment:</span> dev
<span style="color:#4ec9b0">Deployed spaces:</span> 2

  <span style="color:#6a9955">sales_analytics</span>    DEPLOYED    2024-01-15
  <span style="color:#6a9955">customer_insights</span>  DEPLOYED    2024-01-14`,
      'genie-forge apply': `<span style="color:#4ec9b0">Applying changes to environment: dev</span>

<span style="color:#6a9955">✓</span> Created: sales_analytics
  Space ID: abc123def456

<span style="color:#dcdcaa">Apply complete! 1 created, 0 updated, 0 destroyed.</span>`,
      'clear': ''
    };
    
    function runCommand(cmd) {
      if (cmd === 'clear') {
        output.innerHTML = '';
        return;
      }
      const result = commands[cmd] || `<span style="color:#f14c4c">Unknown command: ${cmd}</span>
Type <span style="color:#dcdcaa">help</span> for available commands.`;
      output.innerHTML += `<span style="color:#569cd6">$ ${cmd}</span>
${result}

`;
      const body = output.parentElement;
      body.scrollTop = body.scrollHeight;
    }
    
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        const cmd = this.value.trim();
        if (cmd) {
          runCommand(cmd);
          this.value = '';
        }
      }
    });
    
    // Show welcome message
    output.innerHTML = `<span style="color:#569cd6">Welcome to Genie-Forge CLI Demo!</span>
Type <span style="color:#dcdcaa">help</span> for available commands, or try:
  <span style="color:#dcdcaa">genie-forge whoami</span>
  <span style="color:#dcdcaa">genie-forge plan</span>
  <span style="color:#dcdcaa">genie-forge apply</span>

`;
    // Focus the input
    input.focus();
  }
  
  // Initialize on page load and navigation
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTerminal);
  } else {
    initTerminal();
  }
  setTimeout(initTerminal, 100);
  setTimeout(initTerminal, 500);
})();
</script>

## Next Steps

- [CLI Reference](cli.md) - Full command documentation
- [Configuration Guide](configuration.md) - YAML schema and options
- [User Journeys](user-journeys.md) - Common workflows
- [Architecture](../reference/architecture.md) - How it works under the hood

!!! tip "Using Databricks Notebooks?"
    Check out our [Notebook Guides](../tutorials/notebooks-overview.md) for running Genie-Forge directly in Databricks with automatic Volume path support.
