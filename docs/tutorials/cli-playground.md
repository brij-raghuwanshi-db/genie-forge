---
title: CLI Playground
description: Interactive terminal to try Genie-Forge commands
---

# CLI Playground

Try Genie-Forge commands in this interactive terminal demo. This simulates the CLI experience without requiring installation.

<div class="terminal-container" id="main-terminal">
  <div class="terminal-header">
    <span class="terminal-dot red"></span>
    <span class="terminal-dot yellow"></span>
    <span class="terminal-dot green"></span>
    <span class="terminal-title">genie-forge interactive demo</span>
  </div>
  <div class="terminal-body">
    <div id="terminal-output">Welcome to the Genie-Forge CLI demo!
Type 'help' for available commands.

</div>
    <div style="display: flex; align-items: center;">
      <span class="terminal-prompt">$ </span>
      <input type="text" id="terminal-input" placeholder="Type a command and press Enter..." 
             style="background: transparent; border: none; color: #d4d4d4; 
                    font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; 
                    flex: 1; outline: none;"
             autofocus>
    </div>
  </div>
</div>

<script>
(function() {
  const input = document.getElementById('terminal-input');
  const output = document.getElementById('terminal-output');
  
  const commands = {
    'help': `<span style="color:#4ec9b0">Available commands:</span>

  genie-forge --help        Show main help
  genie-forge --version     Show version
  genie-forge whoami        Display workspace info
  genie-forge init          Initialize project
  genie-forge validate      Validate configuration
  genie-forge plan          Preview changes
  genie-forge apply         Deploy configuration
  genie-forge status        Show deployment status
  genie-forge drift         Detect drift
  genie-forge space-list    List all spaces
  genie-forge space-get     Get space details
  genie-forge space-export  Export space to YAML
  clear                     Clear terminal

<span style="color:#888">Try: genie-forge --help</span>`,

    'genie-forge --help': `<span style="color:#569cd6">Usage:</span> genie-forge [OPTIONS] COMMAND [ARGS]...

  <span style="color:#4ec9b0">Genie-Forge: Infrastructure as Code for Databricks Genie Spaces</span>

<span style="color:#569cd6">Options:</span>
  --profile TEXT  Databricks CLI profile to use
  --version       Show version and exit
  --help          Show this message and exit

<span style="color:#569cd6">Commands:</span>
  <span style="color:#dcdcaa">init</span>           Initialize a new Genie-Forge project
  <span style="color:#dcdcaa">validate</span>       Validate configuration files
  <span style="color:#dcdcaa">plan</span>           Preview deployment changes
  <span style="color:#dcdcaa">apply</span>          Apply configuration to workspace
  <span style="color:#dcdcaa">destroy</span>        Remove deployed spaces
  <span style="color:#dcdcaa">status</span>         Show current deployment status
  <span style="color:#dcdcaa">drift</span>          Detect configuration drift
  <span style="color:#dcdcaa">whoami</span>         Display current workspace and user
  <span style="color:#dcdcaa">space-list</span>     List all Genie spaces in workspace
  <span style="color:#dcdcaa">space-get</span>      Get details of a specific space
  <span style="color:#dcdcaa">space-find</span>     Find spaces by title pattern
  <span style="color:#dcdcaa">space-export</span>   Export a space to YAML format
  <span style="color:#dcdcaa">space-clone</span>    Clone an existing space
  <span style="color:#dcdcaa">state-list</span>     List environments in state
  <span style="color:#dcdcaa">state-show</span>     Show state for an environment
  <span style="color:#dcdcaa">state-import</span>   Import existing space to state
  <span style="color:#dcdcaa">setup-demo</span>     Create demo tables for testing
  <span style="color:#dcdcaa">cleanup-demo</span>   Remove demo tables`,

    'genie-forge --version': `genie-forge, version <span style="color:#b5cea8">0.3.0</span>`,

    'genie-forge whoami': `<span style="color:#4ec9b0">Workspace:</span> https://dbc-a1b2c3d4-e5f6.cloud.databricks.com
<span style="color:#4ec9b0">User:</span>      analyst@company.com
<span style="color:#4ec9b0">Profile:</span>   DEFAULT`,

    'genie-forge init': `<span style="color:#4ec9b0">✓</span> Created project structure:

  my-project/
  ├── conf/
  │   ├── spaces/
  │   │   └── example.yaml
  │   └── environments/
  │       ├── dev.yaml
  │       └── prod.yaml
  ├── .genie-forge.json
  └── .gitignore

<span style="color:#888">Next steps:</span>
  1. Edit conf/spaces/example.yaml
  2. Configure conf/environments/dev.yaml
  3. Run: genie-forge validate`,

    'genie-forge validate': `<span style="color:#4ec9b0">Validating configuration...</span>

Checking: conf/spaces/sales_analytics.yaml
  <span style="color:#4ec9b0">✓</span> Schema valid
  <span style="color:#4ec9b0">✓</span> Required fields present
  <span style="color:#4ec9b0">✓</span> Table references valid

Checking: conf/spaces/customer_insights.yaml
  <span style="color:#4ec9b0">✓</span> Schema valid
  <span style="color:#4ec9b0">✓</span> Required fields present
  <span style="color:#4ec9b0">✓</span> Table references valid

<span style="color:#4ec9b0">✓ All configurations valid</span> (2 files checked)`,

    'genie-forge plan': `<span style="color:#4ec9b0">Planning changes for environment: dev</span>

Comparing configuration with deployed state...

<span style="color:#6a9955">+ sales_analytics</span> (CREATE)
    title: Sales Analytics Dashboard
    description: AI-powered sales insights and forecasting
    warehouse_id: abc123def456
    tables: 3 tables
    
<span style="color:#6a9955">+ customer_insights</span> (CREATE)
    title: Customer Insights Portal
    description: Customer behavior analysis
    warehouse_id: abc123def456
    tables: 2 tables

<span style="color:#569cd6">Plan:</span> <span style="color:#6a9955">2 to create</span>, 0 to update, 0 to destroy

<span style="color:#888">Run 'genie-forge apply --env dev' to apply changes</span>`,

    'genie-forge apply': `<span style="color:#4ec9b0">Applying changes for environment: dev</span>

<span style="color:#6a9955">Creating:</span> sales_analytics
  <span style="color:#4ec9b0">✓</span> Space created (id: 01abc123def456)

<span style="color:#6a9955">Creating:</span> customer_insights
  <span style="color:#4ec9b0">✓</span> Space created (id: 01xyz789ghi012)

<span style="color:#4ec9b0">Apply complete!</span>
  Created: 2
  Updated: 0
  Destroyed: 0

State saved to .genie-forge.json`,

    'genie-forge status': `<span style="color:#4ec9b0">Deployment Status: dev</span>

┌─────────────────────┬──────────────┬─────────────────────┐
│ Space               │ Status       │ Last Applied        │
├─────────────────────┼──────────────┼─────────────────────┤
│ sales_analytics     │ <span style="color:#4ec9b0">DEPLOYED</span>     │ 2024-01-15 10:30:00 │
│ customer_insights   │ <span style="color:#4ec9b0">DEPLOYED</span>     │ 2024-01-15 10:30:05 │
└─────────────────────┴──────────────┴─────────────────────┘

<span style="color:#888">Total: 2 spaces deployed</span>`,

    'genie-forge drift': `<span style="color:#4ec9b0">Checking for drift in environment: dev</span>

Comparing deployed spaces with configuration...

<span style="color:#4ec9b0">✓</span> sales_analytics: No drift detected
<span style="color:#dcdcaa">⚠</span> customer_insights: <span style="color:#dcdcaa">DRIFT DETECTED</span>
    - description: Changed in UI
    - instructions: Modified

<span style="color:#569cd6">Summary:</span> 1 of 2 spaces have drifted

<span style="color:#888">Run 'genie-forge plan' to see required changes</span>`,

    'genie-forge space-list': `<span style="color:#4ec9b0">Genie Spaces in Workspace</span>

┌─────────────────────────────┬──────────────────┬─────────────┐
│ Title                       │ Space ID         │ Tables      │
├─────────────────────────────┼──────────────────┼─────────────┤
│ Sales Analytics Dashboard   │ 01abc123def456   │ 3           │
│ Customer Insights Portal    │ 01xyz789ghi012   │ 2           │
│ Finance Reporting           │ 01fin456rep789   │ 5           │
│ HR Analytics                │ 01hr0987ana654   │ 4           │
└─────────────────────────────┴──────────────────┴─────────────┘

<span style="color:#888">Total: 4 spaces</span>`,

    'genie-forge space-get': `<span style="color:#4ec9b0">Space Details</span>

<span style="color:#569cd6">Title:</span>       Sales Analytics Dashboard
<span style="color:#569cd6">Space ID:</span>    01abc123def456
<span style="color:#569cd6">Description:</span> AI-powered sales insights and forecasting

<span style="color:#569cd6">Warehouse:</span>   abc123def456
<span style="color:#569cd6">Tables:</span>
  - main.sales.transactions
  - main.sales.products
  - main.sales.customers

<span style="color:#569cd6">Instructions:</span>
  You are a helpful sales analyst. Help users understand
  their sales data, identify trends, and forecast revenue.

<span style="color:#569cd6">Created:</span>     2024-01-10 09:00:00
<span style="color:#569cd6">Updated:</span>     2024-01-15 10:30:00`,

    'genie-forge space-export': `<span style="color:#4ec9b0">Exporting space: Sales Analytics Dashboard</span>

<span style="color:#888"># Exported from workspace</span>
<span style="color:#888"># Space ID: 01abc123def456</span>

<span style="color:#569cd6">spaces:</span>
  - <span style="color:#569cd6">title:</span> Sales Analytics Dashboard
    <span style="color:#569cd6">description:</span> AI-powered sales insights and forecasting
    <span style="color:#569cd6">warehouse_id:</span> abc123def456
    <span style="color:#569cd6">tables:</span>
      - main.sales.transactions
      - main.sales.products
      - main.sales.customers
    <span style="color:#569cd6">instructions:</span> |
      You are a helpful sales analyst...

<span style="color:#4ec9b0">✓</span> Exported to: exports/sales_analytics.yaml`,

    'clear': 'CLEAR'
  };
  
  let history = [];
  let historyIndex = -1;
  
  input.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') {
      const cmd = this.value.trim();
      if (cmd) {
        history.push(cmd);
        historyIndex = history.length;
        
        const result = commands[cmd] || commands[cmd.split(' ')[0]] || 
          `<span style="color:#f44336">Command not found:</span> ${cmd}
Type 'help' for available commands.`;
        
        if (result === 'CLEAR') {
          output.innerHTML = '';
        } else {
          output.innerHTML += `<span style="color:#4ec9b0">$ </span><span style="color:#dcdcaa">${cmd}</span>\n${result}\n\n`;
        }
        output.scrollTop = output.scrollHeight;
        this.value = '';
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (historyIndex > 0) {
        historyIndex--;
        this.value = history[historyIndex];
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex < history.length - 1) {
        historyIndex++;
        this.value = history[historyIndex];
      } else {
        historyIndex = history.length;
        this.value = '';
      }
    }
  });
})();
</script>

## Try These Commands

1. **`genie-forge --help`** - See all available commands
2. **`genie-forge whoami`** - Check workspace connection
3. **`genie-forge init`** - Initialize a new project
4. **`genie-forge validate`** - Validate configuration files
5. **`genie-forge plan`** - Preview deployment changes
6. **`genie-forge apply`** - Deploy configuration
7. **`genie-forge status`** - Check deployment status
8. **`genie-forge space-list`** - List all Genie spaces

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| ++enter++ | Execute command |
| ++arrow-up++ | Previous command |
| ++arrow-down++ | Next command |
| `clear` | Clear terminal |

## Real Installation

Ready to use the real CLI? Install Genie-Forge:

```bash
pip install genie-forge
genie-forge --help
```

[Installation Guide →](../guide/installation.md){ .md-button }
