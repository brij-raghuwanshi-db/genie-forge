# CLI Reference

Complete reference for all Genie-Forge CLI commands.

## Command Summary

Commands are organized by functionality and typical user journey:

| # | Command | Purpose | Progress |
|---|---------|---------|----------|
| **Setup** ||||
| 1 | `init` | Initialize new genie-forge project | - |
| 2 | `profiles` | List available Databricks CLI profiles | - |
| 3 | `whoami` | Show current user and workspace | Spinner |
| **Demo** ||||
| 4 | `setup-demo` | Create demo tables in Unity Catalog | Progress bar |
| 5 | `demo-status` | Check if demo objects exist | Spinner |
| 6 | `cleanup-demo` | Remove demo tables (dry-run by default) | Progress bar |
| **Configuration** ||||
| 7 | `validate` | Check config syntax and schema | Progress bar |
| **Deployment** ||||
| 8 | `plan` | Preview what will be created/updated | - |
| 9 | `apply` | Deploy Genie spaces to workspace | Progress bar |
| 10 | `status` | View deployment status from state file | - |
| 11 | `drift` | Detect drift between state and workspace | Progress bar |
| 12 | `destroy` | Delete spaces from workspace | Progress bar |
| **Space Operations** ||||
| 13 | `space-list` | List all spaces in workspace | Pagination |
| 14 | `space-get` | Display detailed space information | Spinner |
| 15 | `space-find` | Search spaces by name pattern | Pagination |
| 16 | `space-create` | Create space via CLI or file | Spinner |
| 17 | `space-clone` | Clone space locally or to workspace | Spinner |
| 18 | `space-export` | Export spaces to YAML files | Two-phase |
| 19 | `space-delete` | Delete spaces (alias for destroy) | Progress bar |
| **State Operations** ||||
| 20 | `state-list` | List tracked spaces in state | - |
| 21 | `state-show` | View detailed state information | - |
| 22 | `state-pull` | Refresh state from workspace | Progress bar |
| 23 | `state-remove` | Remove space from state tracking | - |
| 24 | `state-import` | Import existing spaces (alias for import) | - |

**Get help for any command**: `genie-forge <command> --help`

---

## Workflow Diagram

<div class="workflow-diagram">
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 700" style="max-width: 100%; height: auto;">
  <defs>
    <marker id="cliArr" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#7c3aed"/>
    </marker>
    <linearGradient id="cliPurple" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#8b5cf6"/><stop offset="100%" style="stop-color:#6d28d9"/>
    </linearGradient>
    <linearGradient id="cliGreen" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#10b981"/><stop offset="100%" style="stop-color:#059669"/>
    </linearGradient>
    <linearGradient id="cliBlue" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#3b82f6"/><stop offset="100%" style="stop-color:#2563eb"/>
    </linearGradient>
    <linearGradient id="cliOrange" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#f59e0b"/><stop offset="100%" style="stop-color:#d97706"/>
    </linearGradient>
    <linearGradient id="cliPink" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#ec4899"/><stop offset="100%" style="stop-color:#db2777"/>
    </linearGradient>
    <linearGradient id="cliRed" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#ef4444"/><stop offset="100%" style="stop-color:#dc2626"/>
    </linearGradient>
    <filter id="cliSh"><feDropShadow dx="0" dy="1" stdDeviation="2" flood-color="#000" flood-opacity="0.2"/></filter>
  </defs>
  <style>
    .cliBox { filter: url(#cliSh); }
    .cliText { fill: white; font-family: system-ui, sans-serif; font-size: 11px; font-weight: 600; }
    .cliTitle { fill: white; font-family: system-ui, sans-serif; font-size: 10px; font-weight: bold; }
    .cliFlow { stroke: #7c3aed; stroke-width: 2; fill: none; stroke-dasharray: 6 3; animation: cliMove 0.5s linear infinite; }
    @keyframes cliMove { 0% { stroke-dashoffset: 0; } 100% { stroke-dashoffset: -9; } }
    .cliLive { animation: cliPulse 1.5s infinite; }
    @keyframes cliPulse { 50% { opacity: 0.5; } }
  </style>
  
  <!-- LIVE Badge -->
  <g class="cliLive"><rect x="730" y="10" width="55" height="20" rx="10" fill="#10b981"/><text x="757" y="24" text-anchor="middle" fill="white" font-family="system-ui" font-size="10" font-weight="bold">LIVE</text></g>
  
  <!-- Setup Phase -->
  <g transform="translate(550, 40)">
    <rect width="180" height="150" rx="8" fill="url(#cliPurple)" opacity="0.1" stroke="url(#cliPurple)" stroke-width="2"/>
    <rect x="40" y="-12" width="100" height="24" rx="4" fill="url(#cliPurple)"/>
    <text class="cliTitle" x="90" y="4" text-anchor="middle">Setup Phase</text>
    <rect class="cliBox" x="55" y="25" width="70" height="28" rx="5" fill="url(#cliPurple)"/>
    <text class="cliText" x="90" y="44" text-anchor="middle">init</text>
    <path class="cliFlow" d="M 90 53 L 90 68" marker-end="url(#cliArr)"/>
    <rect class="cliBox" x="55" y="70" width="70" height="28" rx="5" fill="url(#cliPurple)"/>
    <text class="cliText" x="90" y="89" text-anchor="middle">whoami</text>
    <path class="cliFlow" d="M 90 98 L 90 113" marker-end="url(#cliArr)"/>
    <rect class="cliBox" x="55" y="115" width="70" height="28" rx="5" fill="url(#cliPurple)"/>
    <text class="cliText" x="90" y="134" text-anchor="middle">profiles</text>
  </g>
  
  <!-- Arrow: Setup -> Discovery -->
  <path class="cliFlow" d="M 640 190 L 640 210" marker-end="url(#cliArr)"/>
  
  <!-- Discovery Phase -->
  <g transform="translate(550, 220)">
    <rect width="180" height="150" rx="8" fill="url(#cliGreen)" opacity="0.1" stroke="url(#cliGreen)" stroke-width="2"/>
    <rect x="30" y="-12" width="120" height="24" rx="4" fill="url(#cliGreen)"/>
    <text class="cliTitle" x="90" y="4" text-anchor="middle">Discovery Phase</text>
    <rect class="cliBox" x="55" y="25" width="70" height="28" rx="5" fill="url(#cliGreen)"/>
    <text class="cliText" x="90" y="44" text-anchor="middle">space-list</text>
    <path class="cliFlow" d="M 90 53 L 90 68" marker-end="url(#cliArr)"/>
    <rect class="cliBox" x="55" y="70" width="70" height="28" rx="5" fill="url(#cliGreen)"/>
    <text class="cliText" x="90" y="89" text-anchor="middle">space-find</text>
    <path class="cliFlow" d="M 90 98 L 90 113" marker-end="url(#cliArr)"/>
    <rect class="cliBox" x="55" y="115" width="70" height="28" rx="5" fill="url(#cliGreen)"/>
    <text class="cliText" x="90" y="134" text-anchor="middle">space-get</text>
  </g>
  
  <!-- Arrow: Discovery -> Creation -->
  <path class="cliFlow" d="M 550 320 L 430 320" marker-end="url(#cliArr)"/>
  
  <!-- Creation Phase -->
  <g transform="translate(180, 250)">
    <rect width="240" height="180" rx="8" fill="url(#cliBlue)" opacity="0.1" stroke="url(#cliBlue)" stroke-width="2"/>
    <rect x="60" y="-12" width="120" height="24" rx="4" fill="url(#cliBlue)"/>
    <text class="cliTitle" x="120" y="4" text-anchor="middle">Creation Phase</text>
    <rect class="cliBox" x="20" y="30" width="85" height="28" rx="5" fill="url(#cliBlue)"/>
    <text class="cliText" x="62" y="49" text-anchor="middle">space-create</text>
    <rect class="cliBox" x="120" y="30" width="85" height="28" rx="5" fill="url(#cliBlue)"/>
    <text class="cliText" x="162" y="49" text-anchor="middle">space-clone</text>
    <rect class="cliBox" x="70" y="75" width="100" height="28" rx="5" fill="url(#cliBlue)"/>
    <text class="cliText" x="120" y="94" text-anchor="middle">space-export</text>
    <path class="cliFlow" d="M 62 58 L 62 80 L 100 120 L 100 135" marker-end="url(#cliArr)"/>
    <path class="cliFlow" d="M 162 58 L 162 80 L 140 120 L 140 135" marker-end="url(#cliArr)"/>
    <path class="cliFlow" d="M 120 103 L 120 135" marker-end="url(#cliArr)"/>
    <rect class="cliBox" x="70" y="140" width="100" height="28" rx="5" fill="url(#cliBlue)"/>
    <text class="cliText" x="120" y="159" text-anchor="middle">validate</text>
  </g>
  
  <!-- Arrow: Creation -> Deployment -->
  <path class="cliFlow" d="M 300 430 L 300 450" marker-end="url(#cliArr)"/>
  
  <!-- Deployment Phase -->
  <g transform="translate(220, 460)">
    <rect width="160" height="150" rx="8" fill="url(#cliOrange)" opacity="0.1" stroke="url(#cliOrange)" stroke-width="2"/>
    <rect x="20" y="-12" width="120" height="24" rx="4" fill="url(#cliOrange)"/>
    <text class="cliTitle" x="80" y="4" text-anchor="middle">Deployment Phase</text>
    <rect class="cliBox" x="45" y="25" width="70" height="28" rx="5" fill="url(#cliOrange)"/>
    <text class="cliText" x="80" y="44" text-anchor="middle">plan</text>
    <path class="cliFlow" d="M 80 53 L 80 68" marker-end="url(#cliArr)"/>
    <rect class="cliBox" x="45" y="70" width="70" height="28" rx="5" fill="url(#cliOrange)"/>
    <text class="cliText" x="80" y="89" text-anchor="middle">apply</text>
    <path class="cliFlow" d="M 80 98 L 80 113" marker-end="url(#cliArr)"/>
    <rect class="cliBox" x="45" y="115" width="70" height="28" rx="5" fill="url(#cliOrange)"/>
    <text class="cliText" x="80" y="134" text-anchor="middle">status</text>
  </g>
  
  <!-- Arrow: Deployment -> Management -->
  <path class="cliFlow" d="M 380 560 L 450 560" marker-end="url(#cliArr)"/>
  
  <!-- Management Phase -->
  <g transform="translate(460, 460)">
    <rect width="160" height="200" rx="8" fill="url(#cliPink)" opacity="0.1" stroke="url(#cliPink)" stroke-width="2"/>
    <rect x="10" y="-12" width="140" height="24" rx="4" fill="url(#cliPink)"/>
    <text class="cliTitle" x="80" y="4" text-anchor="middle">Management Phase</text>
    <rect class="cliBox" x="45" y="25" width="70" height="28" rx="5" fill="url(#cliPink)"/>
    <text class="cliText" x="80" y="44" text-anchor="middle">drift</text>
    <path class="cliFlow" d="M 80 53 L 80 68" marker-end="url(#cliArr)"/>
    <rect class="cliBox" x="40" y="70" width="80" height="28" rx="5" fill="url(#cliPink)"/>
    <text class="cliText" x="80" y="89" text-anchor="middle">state-show</text>
    <path class="cliFlow" d="M 80 98 L 80 113" marker-end="url(#cliArr)"/>
    <rect class="cliBox" x="40" y="115" width="80" height="28" rx="5" fill="url(#cliPink)"/>
    <text class="cliText" x="80" y="134" text-anchor="middle">state-pull</text>
    <path class="cliFlow" d="M 80 143 L 80 158" marker-end="url(#cliArr)"/>
    <rect class="cliBox" x="35" y="160" width="90" height="28" rx="5" fill="url(#cliPink)"/>
    <text class="cliText" x="80" y="179" text-anchor="middle">state-import</text>
  </g>
  
  <!-- Arrow: Management -> Cleanup -->
  <path class="cliFlow" d="M 460 560 L 180 560 L 180 500" marker-end="url(#cliArr)"/>
  
  <!-- Cleanup Phase -->
  <g transform="translate(80, 380)">
    <rect width="130" height="115" rx="8" fill="url(#cliRed)" opacity="0.1" stroke="url(#cliRed)" stroke-width="2"/>
    <rect x="10" y="-12" width="110" height="24" rx="4" fill="url(#cliRed)"/>
    <text class="cliTitle" x="65" y="4" text-anchor="middle">Cleanup Phase</text>
    <rect class="cliBox" x="30" y="25" width="70" height="28" rx="5" fill="url(#cliRed)"/>
    <text class="cliText" x="65" y="44" text-anchor="middle">destroy</text>
    <path class="cliFlow" d="M 65 53 L 65 68" marker-end="url(#cliArr)"/>
    <rect class="cliBox" x="15" y="70" width="100" height="28" rx="5" fill="url(#cliRed)"/>
    <text class="cliText" x="65" y="89" text-anchor="middle">state-remove</text>
  </g>
</svg>
</div>

---

## Progress Indicators

v0.3.0 adds real-time feedback for all long-running operations:

### Progress Bar (Known Total)

Used by: `apply`, `destroy`, `drift`, `validate`, `state-pull`, `setup-demo`, `cleanup-demo`

```
⠋ Applying...  ████████████████████████░░░░░░  75% (15/20) 0:00:45
```

### Pagination Progress (Unknown Total)

Used by: `space-list`, `space-find`, `space-export`

```
⠋ Page 3... (87 items) 0:00:12
```

### Spinner (Single Operations)

Used by: `whoami`, `space-get`, `space-create`, `space-clone`, `demo-status`

```
⠋ Fetching space details...
```

### Summary Reports

After bulk operations, you'll see a summary:

```
═══════════════════════════════════════════════════════════════
OPERATION SUMMARY
───────────────────────────────────────────────────────────────
  Created:    12 space(s)
  Updated:     3 space(s)
  Failed:      1 space(s)
  Unchanged:   4 space(s)
───────────────────────────────────────────────────────────────
Total: 20 space(s) processed in 45.2s
═══════════════════════════════════════════════════════════════
```

---

## Setup Commands

### `genie-forge init`

Initialize a new genie-forge project with standard directory structure.

```bash
Usage: genie-forge init [OPTIONS]

Options:
  --path TEXT     Project directory [default: current directory]
  --force         Overwrite existing files
  -y, --yes       Skip confirmation prompts
  --minimal       Create minimal structure (no example files)
  --help          Show help
```

**What it creates:**

```
your-project/
├── conf/
│   ├── spaces/              # Space configurations go here
│   │   └── example.yaml     # Example space config
│   └── environments/        # Environment configs
│       ├── dev.yaml         # Development environment
│       └── prod.yaml        # Production environment
├── .genie-forge.json        # State file (empty)
└── .gitignore               # Updated with genie-forge patterns
```

**Examples:**

```bash
# Initialize in current directory
genie-forge init

# Initialize in a specific directory
genie-forge init --path /path/to/my-project

# Skip confirmation prompts (for CI/CD)
genie-forge init --yes

# Create minimal structure without example files
genie-forge init --minimal

# Force overwrite existing files
genie-forge init --force
```

---

### `genie-forge profiles`

List available Databricks CLI profiles from `~/.databrickscfg`.

```bash
Usage: genie-forge profiles [OPTIONS]

Options:
  --help  Show help
```

**Output:**

```
Available Databricks Profiles:
  • DEFAULT
  • DEV_WORKSPACE
  • PROD_WORKSPACE
```

---

### `genie-forge whoami`

Show current authenticated user and workspace. Useful for verifying you're connected to the correct environment.

```bash
Usage: genie-forge whoami [OPTIONS]

Options:
  -p, --profile TEXT  Databricks CLI profile to use
  --json              Output as JSON (for scripting)
  --help              Show help
```

**Examples:**

```bash
# Show current identity
genie-forge whoami

# Use a specific profile
genie-forge whoami --profile PROD

# Output as JSON (for scripting)
genie-forge whoami --json
```

**Output:**

```
Current Identity
══════════════════════════════════════════════════

  User:        john.doe@company.com
  Display Name: John Doe
  User ID:     123456789
  Workspace:   https://my-workspace.cloud.databricks.com
  Profile:     PROD
```

---

## Demo Commands

### `genie-forge setup-demo`

Create demo tables in Unity Catalog for use with the example configurations.

```bash
Usage: genie-forge setup-demo [OPTIONS]

Options:
  -c, --catalog TEXT       Unity Catalog name [required]
  -s, --schema TEXT        Schema name [required]
  -w, --warehouse-id TEXT  SQL warehouse ID [required]
  -p, --profile TEXT       Databricks CLI profile
  --dry-run                Preview only, no changes
  --help                   Show help
```

**Tables Created:**

| Table | Rows | Description |
|-------|------|-------------|
| `employees` | 30 | Employee master with self-join (manager_id → employee_id) |
| `departments` | 8 | Department reference (name, budget, cost center) |
| `locations` | 8 | Office locations (city, state, country) |
| `customers` | 10 | Customer master (name, segment) |
| `products` | 10 | Product catalog (name, category, price) |
| `sales` | 30 | Sales transactions (customer, product, amount, region) |

**Examples:**

```bash
# Preview what would be created
genie-forge setup-demo \
    --catalog my_catalog \
    --schema my_schema \
    --warehouse-id abc123 \
    --dry-run

# Create the demo tables
genie-forge setup-demo \
    --catalog my_catalog \
    --schema my_schema \
    --warehouse-id abc123 \
    --profile MY_PROFILE
```

---

### `genie-forge demo-status`

Check if demo tables and functions exist. Useful for verifying setup before running examples.

```bash
Usage: genie-forge demo-status [OPTIONS]

Options:
  -c, --catalog TEXT       Unity Catalog name [required]
  -s, --schema TEXT        Schema name [required]
  -w, --warehouse-id TEXT  SQL warehouse ID [required]
  -p, --profile TEXT       Databricks CLI profile
  --json                   Output as JSON
  --help                   Show help
```

**Examples:**

```bash
# Check demo status
genie-forge demo-status \
    --catalog my_catalog \
    --schema my_schema \
    --warehouse-id abc123 \
    --profile MY_PROFILE

# Output as JSON (for scripting)
genie-forge demo-status \
    --catalog my_catalog \
    --schema my_schema \
    --warehouse-id abc123 \
    --json
```

---

### `genie-forge cleanup-demo`

Remove demo tables and functions created by `setup-demo`.

**Safety**: By default, this command runs in **DRY-RUN mode**. You MUST pass `--execute` to actually delete objects.

```bash
Usage: genie-forge cleanup-demo [OPTIONS]

Options:
  -c, --catalog TEXT       Unity Catalog name [required]
  -s, --schema TEXT        Schema name [required]
  -w, --warehouse-id TEXT  SQL warehouse ID (required with --execute)
  -p, --profile TEXT       Databricks CLI profile
  -l, --list-only          List objects + SQL for manual cleanup (no auth)
  --execute                REQUIRED to actually delete objects
  -f, --force              Skip confirmation (only with --execute)
  --help                   Show help
```

**Examples:**

```bash
# Default: DRY-RUN - preview what would be deleted (safe)
genie-forge cleanup-demo \
    --catalog my_catalog \
    --schema my_schema \
    --warehouse-id abc123 \
    --profile MY_PROFILE

# List objects + get SQL for manual cleanup
genie-forge cleanup-demo \
    --catalog my_catalog \
    --schema my_schema \
    --list-only

# Actually delete demo objects
genie-forge cleanup-demo \
    --catalog my_catalog \
    --schema my_schema \
    --warehouse-id abc123 \
    --profile MY_PROFILE \
    --execute
```

---

## Configuration Commands

### `genie-forge validate`

Check your YAML/JSON configuration files for syntax errors and schema violations.

```bash
Usage: genie-forge validate [OPTIONS]

Options:
  -c, --config PATH  Config file or directory [required]
  --strict           Treat warnings as errors (for CI/CD)
  --help             Show help
```

**Validation Report:**

```
═══════════════════════════════════════════════════════════════
VALIDATION SUMMARY
───────────────────────────────────────────────────────────────
  Passed:    8 file(s)
  Warnings:  2 file(s)
  Failed:    1 file(s)
───────────────────────────────────────────────────────────────
```

**Examples:**

```bash
# Validate a single file
genie-forge validate --config conf/spaces/employee_analytics.yaml

# Validate all configs in directory
genie-forge validate --config conf/spaces/

# Strict mode (fail on warnings) - useful for CI/CD
genie-forge validate --config conf/spaces/ --strict
```

---

## Deployment Commands

### `genie-forge plan`

Preview what changes would be made without actually deploying. This is a safe, read-only operation.

```bash
Usage: genie-forge plan [OPTIONS]

Options:
  -e, --env TEXT         Target environment [default: dev]
  -c, --config PATH      Config file/directory [default: conf/spaces]
  -p, --profile TEXT     Databricks CLI profile [required for auth]
  -s, --state-file TEXT  State file [default: .genie-forge.json]
  --help                 Show help
```

**Plan Actions:**

| Symbol | Action | Meaning |
|--------|--------|---------|
| `+` | CREATE | New spaces to be created |
| `~` | UPDATE | Existing spaces to be modified |
| `-` | DESTROY | Spaces in state but not in config |
| `=` | NO CHANGE | Already in sync |

**Examples:**

```bash
# Plan for dev environment
genie-forge plan --env dev --profile MY_PROFILE

# Plan for specific config only
genie-forge plan --env dev --config conf/spaces/employee_analytics.yaml --profile MY_PROFILE
```

---

### `genie-forge apply`

Deploy your Genie spaces to the Databricks workspace.

```bash
Usage: genie-forge apply [OPTIONS]

Options:
  -e, --env TEXT         Target environment [default: dev]
  -c, --config PATH      Config file/directory [default: conf/spaces]
  -p, --profile TEXT     Databricks CLI profile [required]
  --auto-approve         Skip confirmation (for CI/CD)
  --dry-run              Preview only, no changes
  -t, --target TEXT      Apply only specific space
  -s, --state-file TEXT  State file [default: .genie-forge.json]
  --help                 Show help
```

**Examples:**

```bash
# Interactive apply (prompts for confirmation)
genie-forge apply --env dev --profile MY_PROFILE

# Automated apply (no prompt - for CI/CD)
genie-forge apply --env prod --profile PROD_PROFILE --auto-approve

# Dry run (preview without making changes)
genie-forge apply --env dev --profile MY_PROFILE --dry-run

# Apply only a specific space
genie-forge apply --env dev --target employee_analytics --profile MY_PROFILE
```

---

### `genie-forge status`

Display deployment status from the local state file.

```bash
Usage: genie-forge status [OPTIONS]

Options:
  -e, --env TEXT         Filter by environment (default: all)
  -s, --state-file TEXT  State file [default: .genie-forge.json]
  --help                 Show help
```

**Status Values:**

| Status | Meaning |
|--------|---------|
| `APPLIED` | Space deployed and in sync |
| `PENDING` | Defined but not yet deployed |
| `MODIFIED` | Config changed since last deploy |
| `DESTROYED` | Destroyed but still in state |

---

### `genie-forge drift`

Detect drift between local state and the live workspace.

```bash
Usage: genie-forge drift [OPTIONS]

Options:
  -e, --env TEXT         Target environment [required]
  -p, --profile TEXT     Databricks CLI profile [required]
  -s, --state-file TEXT  State file [default: .genie-forge.json]
  --help                 Show help
```

**Drift Report:**

```
═══════════════════════════════════════════════════════════════
DRIFT DETECTION SUMMARY
───────────────────────────────────────────────────────────────
  Synced:     8 space(s)
  Drifted:    2 space(s)
  Deleted:    1 space(s)
───────────────────────────────────────────────────────────────
```

---

### `genie-forge destroy`

Delete deployed Genie spaces from the workspace.

```bash
Usage: genie-forge destroy [OPTIONS]

Options:
  -e, --env TEXT         Environment [default: dev]
  -t, --target TEXT      Target pattern [required]
  -p, --profile TEXT     Databricks CLI profile
  --dry-run              Preview only, don't delete
  -f, --force            Skip confirmation prompt
  -s, --state-file TEXT  State file [default: .genie-forge.json]
  --help                 Show help
```

**Target Patterns:**

| Pattern | Description |
|---------|-------------|
| `old_space` | Delete single space |
| `space1, space2, space3` | Delete multiple spaces |
| `*` | Delete ALL spaces in environment |
| `* [keep_this]` | Delete all EXCEPT `keep_this` |
| `* [keep1, keep2]` | Delete all EXCEPT `keep1` and `keep2` |

**Examples:**

```bash
# Destroy single space (dry run first)
genie-forge destroy --env dev --target old_space --dry-run

# Destroy ALL spaces in dev (careful!)
genie-forge destroy --env dev --target "*" --dry-run

# Destroy all EXCEPT critical spaces
genie-forge destroy --env prod --target "* [production_dashboard, main_reports]" --dry-run

# Force destroy without confirmation
genie-forge destroy --env dev --target "test_*" --force --profile MY_PROFILE
```

---

## Space Operations (`space-*`)

### `genie-forge space-list`

List all Genie spaces in the workspace with pagination.

```bash
Usage: genie-forge space-list [OPTIONS]

Options:
  -p, --profile TEXT    Databricks CLI profile
  --limit INT           Max spaces to display [default: 100]
  --format TEXT         Output format: table, json, csv [default: table]
  --help                Show help
```

**Examples:**

```bash
# List all spaces (table format)
genie-forge space-list --profile MY_PROFILE

# Limit output
genie-forge space-list --profile MY_PROFILE --limit 20

# Output as JSON
genie-forge space-list --profile MY_PROFILE --format json

# Output as CSV (for spreadsheets)
genie-forge space-list --profile MY_PROFILE --format csv
```

---

### `genie-forge space-get`

Display detailed information about a specific space.

```bash
Usage: genie-forge space-get [SPACE_ID] [OPTIONS]

Arguments:
  SPACE_ID              Databricks space ID (optional if using --name)

Options:
  --name, -n TEXT       Find space by name instead of ID
  -p, --profile TEXT    Databricks CLI profile
  --raw                 Include raw serialized_space data
  --format TEXT         Output format: table, json, yaml [default: table]
  --help                Show help
```

**Examples:**

```bash
# Get by space ID (table format)
genie-forge space-get 01ABC123DEF456 --profile MY_PROFILE

# Get by name
genie-forge space-get --name "Sales Analytics" --profile MY_PROFILE

# Output as JSON
genie-forge space-get 01ABC123DEF456 --format json --profile MY_PROFILE

# Output as YAML (for config files)
genie-forge space-get 01ABC123DEF456 --format yaml --profile MY_PROFILE

# Include raw API data
genie-forge space-get 01ABC123DEF456 --raw --profile MY_PROFILE
```

---

### `genie-forge space-find`

Search for spaces by name pattern with wildcard support.

```bash
Usage: genie-forge space-find [OPTIONS]

Options:
  -n, --name TEXT       Name pattern with wildcards (* = any chars) [required]
  -e, --env TEXT        Environment to search in state
  -p, --profile TEXT    Databricks profile (searches workspace)
  --workspace           Search live workspace instead of state
  --help                Show help
```

**Wildcard Patterns:**

- `*` - Match any characters
- `Sales*` - Starts with "Sales"
- `*Analytics` - Ends with "Analytics"
- `*HR*` - Contains "HR"

**Examples:**

```bash
# List ALL spaces in live workspace
genie-forge space-find --name "*" --profile MY_PROFILE

# Find spaces containing "analytics" (case-insensitive)
genie-forge space-find --name "*analytics*" --profile MY_PROFILE

# Search local state only (no network call)
genie-forge space-find --name "Sales*" --env dev
```

---

### `genie-forge space-create`

Create a Genie space via CLI flags, YAML file, or JSON file.

```bash
Usage: genie-forge space-create [TITLE] [OPTIONS]

Arguments:
  TITLE                   Space title (optional if using --from-file)

Options:
  --from-file PATH        Load config from YAML/JSON file
  --warehouse-id TEXT     SQL warehouse ID
  --tables TEXT           Comma-separated table identifiers
  --description TEXT      Space description
  --instructions TEXT     Text instructions (can be used multiple times)
  --functions TEXT        Comma-separated function identifiers
  --questions TEXT        Sample questions (can be used multiple times)
  --parent-path TEXT      Workspace folder path
  --set KEY=VALUE         Override config values (can be used multiple times)
  --save-config PATH      Save config to YAML file
  --env TEXT              Add to state for environment
  -p, --profile TEXT      Databricks CLI profile
  --dry-run               Preview without creating
  --help                  Show help
```

**Three Creation Methods:**

1. **CLI FLAGS** (Quick prototyping):
   ```bash
   genie-forge space-create "My Space" \
       --warehouse-id abc123 \
       --tables "catalog.schema.table1,catalog.schema.table2" \
       --profile PROD
   ```

2. **FROM FILE** (Complex configurations):
   ```bash
   genie-forge space-create --from-file conf/spaces/my_space.yaml --profile PROD
   ```

3. **HYBRID** (Template with overrides):
   ```bash
   genie-forge space-create --from-file template.yaml \
       --set title="Custom Name" \
       --set warehouse_id="new_warehouse" \
       --profile PROD
   ```

**Examples:**

```bash
# Quick creation with CLI flags
genie-forge space-create "Sales Analytics" \
    --warehouse-id abc123 \
    --tables "catalog.schema.sales,catalog.schema.customers" \
    --instructions "Focus on revenue metrics" \
    --questions "Top 10 customers by revenue?" \
    --profile PROD

# Create from YAML file
genie-forge space-create --from-file conf/spaces/sales.yaml --profile PROD

# Create and save config for later
genie-forge space-create "Test Space" \
    --warehouse-id abc123 \
    --tables "catalog.schema.test" \
    --save-config conf/spaces/test_space.yaml \
    --profile DEV

# Dry run to preview
genie-forge space-create --from-file config.yaml --dry-run --profile PROD
```

---

### `genie-forge space-clone`

Clone an existing space within the same workspace or to another workspace.

```bash
Usage: genie-forge space-clone SOURCE_ID [OPTIONS]

Arguments:
  SOURCE_ID              Source space ID to clone

Options:
  --name TEXT            Name for the cloned space [required]
  --to-workspace         Clone to workspace (creates new space)
  --to-file PATH         Clone to YAML file (export)
  --warehouse-id TEXT    Override warehouse ID for clone
  -p, --profile TEXT     Source workspace profile
  --target-profile TEXT  Target workspace profile (for cross-workspace)
  --dry-run              Preview without cloning
  --help                 Show help
```

**Examples:**

```bash
# Clone to a new space in the same workspace
genie-forge space-clone 01ABC123DEF \
    --name "Sales Analytics (Copy)" \
    --to-workspace \
    --profile PROD

# Clone to a YAML file for editing
genie-forge space-clone 01ABC123DEF \
    --name "My Clone" \
    --to-file conf/spaces/cloned_space.yaml \
    --profile PROD

# Cross-workspace clone
genie-forge space-clone 01ABC123DEF \
    --name "Production Space" \
    --to-workspace \
    --profile DEV \
    --target-profile PROD \
    --warehouse-id prod_warehouse_123
```

---

### `genie-forge space-export`

Export spaces from workspace to YAML files.

```bash
Usage: genie-forge space-export [OPTIONS]

Options:
  --output-dir PATH      Output directory [default: conf/spaces]
  --pattern TEXT         Name pattern to filter (e.g., "Sales*")
  --space-id TEXT        Specific space ID(s) to export (can be repeated)
  --exclude TEXT         Pattern(s) to exclude (can be repeated)
  -p, --profile TEXT     Databricks CLI profile
  --overwrite            Overwrite existing files
  --format TEXT          Output format: yaml or json [default: yaml]
  --dry-run              Preview without writing files
  --help                 Show help
```

**Examples:**

```bash
# Export all spaces
genie-forge space-export --profile PROD --output-dir conf/exported/

# Export spaces matching pattern
genie-forge space-export --pattern "Sales*" --profile PROD

# Export specific spaces
genie-forge space-export \
    --space-id 01ABC123 \
    --space-id 01DEF456 \
    --profile PROD

# Export all except some
genie-forge space-export \
    --pattern "*" \
    --exclude "Test*" \
    --exclude "*_backup" \
    --profile PROD

# Dry run to see what would be exported
genie-forge space-export --pattern "*" --dry-run --profile PROD
```

---

### `genie-forge space-delete`

Delete spaces from the workspace. This is an alias for `destroy`.

```bash
Usage: genie-forge space-delete [OPTIONS]

# Same options as 'destroy' command
```

---

## State Operations (`state-*`)

### `genie-forge state-list`

List all spaces tracked in the state file.

```bash
Usage: genie-forge state-list [OPTIONS]

Options:
  -e, --env TEXT         Filter by environment (default: all)
  -s, --state-file TEXT  State file [default: .genie-forge.json]
  --show-ids             Show Databricks space IDs
  --format TEXT          Output format: table, plain, json [default: table]
  --help                 Show help
```

**Examples:**

```bash
# List all tracked spaces
genie-forge state-list

# Filter by environment
genie-forge state-list --env prod

# Show Databricks IDs
genie-forge state-list --env dev --show-ids

# Output as JSON
genie-forge state-list --format json
```

---

### `genie-forge state-show`

Display detailed state file information.

```bash
Usage: genie-forge state-show [OPTIONS]

Options:
  -e, --env TEXT         Filter by environment
  -s, --state-file TEXT  State file [default: .genie-forge.json]
  --format TEXT          Output format: table or json [default: table]
  --help                 Show help
```

**Examples:**

```bash
# Show full state
genie-forge state-show

# Show specific environment
genie-forge state-show --env prod

# Output as JSON (for backup or scripting)
genie-forge state-show --format json > state_backup.json
```

---

### `genie-forge state-pull`

Refresh local state from the live workspace. Useful for syncing after manual changes.

```bash
Usage: genie-forge state-pull [OPTIONS]

Options:
  -e, --env TEXT         Environment to refresh [required]
  -p, --profile TEXT     Databricks CLI profile
  -s, --state-file TEXT  State file [default: .genie-forge.json]
  --verify-only          Check without updating state
  --help                 Show help
```

**Examples:**

```bash
# Refresh state for dev environment
genie-forge state-pull --env dev --profile DEV

# Verify spaces without updating state
genie-forge state-pull --env prod --profile PROD --verify-only
```

---

### `genie-forge state-remove`

Remove a space from state tracking WITHOUT deleting it from Databricks.

```bash
Usage: genie-forge state-remove SPACE_ID [OPTIONS]

Arguments:
  SPACE_ID               Logical ID of the space to remove

Options:
  -e, --env TEXT         Environment [required]
  -s, --state-file TEXT  State file [default: .genie-forge.json]
  -f, --force            Skip confirmation prompt
  --help                 Show help
```

**Use Cases:**

- Space was deleted manually in Databricks
- You want to stop managing a space with genie-forge
- Cleaning up orphaned state entries

**Examples:**

```bash
# Remove space from state (interactive confirmation)
genie-forge state-remove old_space --env dev

# Force remove without confirmation
genie-forge state-remove old_space --env dev --force
```

---

### `genie-forge state-import`

Import existing Databricks spaces into genie-forge management. This is an alias for the `import` command.

```bash
Usage: genie-forge state-import [SPACE_ID] [OPTIONS]

Arguments:
  SPACE_ID              Databricks space ID (optional if using --pattern)

Options:
  --pattern TEXT        Import spaces matching this name pattern
  -e, --env TEXT        Environment to import into [default: dev]
  --as TEXT             Logical ID for the imported space
  -p, --profile TEXT    Databricks CLI profile
  -s, --state-file TEXT State file [default: .genie-forge.json]
  -o, --output-dir TEXT Directory for YAML configs [default: conf/spaces]
  --dry-run             Preview without making changes
  -f, --force           Overwrite existing entries
  --help                Show help
```

**Examples:**

```bash
# Import a single space with custom logical ID
genie-forge state-import 01ABCDEF123456 --env prod --as sales_dashboard --profile PROD

# Import all spaces matching pattern
genie-forge state-import --pattern "*Analytics*" --env dev --profile DEV

# Preview what would be imported
genie-forge state-import --pattern "*" --env prod --dry-run --profile PROD

# Import to custom directory
genie-forge state-import 01ABC123 --env prod --output-dir conf/imported/ --profile PROD
```

---

## Authentication

Genie-Forge supports multiple authentication methods, checked in this order:

1. **`--profile` flag** - Explicitly specify a Databricks CLI profile
2. **Environment variables** - `DATABRICKS_HOST` and `DATABRICKS_TOKEN`
3. **Default profile** - `DEFAULT` profile in `~/.databrickscfg`

### Setting Up Profiles

Create or edit `~/.databrickscfg`:

```ini
[DEFAULT]
host = https://your-default-workspace.cloud.databricks.com
token = dapi_default_xxx

[DEV]
host = https://dev-workspace.cloud.databricks.com
token = dapi_dev_xxx

[PROD]
host = https://prod-workspace.cloud.databricks.com
token = dapi_prod_xxx
```

### Using Environment Variables

```bash
export DATABRICKS_HOST="https://my-workspace.cloud.databricks.com"
export DATABRICKS_TOKEN="dapi_xxx"

genie-forge plan --env dev  # No --profile needed
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (authentication, API, validation, etc.) |
| 2 | Invalid arguments or usage |

---

## Path Formats

Genie-Forge supports both local and Databricks Volume paths:

### Local Machine

```bash
# Relative paths
genie-forge space-export --output-dir ./exports/
genie-forge validate --config ./conf/spaces/

# Absolute paths
genie-forge space-export --output-dir /home/user/genie-forge/exports/
```

### Databricks (Unity Catalog Volumes)

```bash
# Volume paths follow: /Volumes/<catalog>/<schema>/<volume>/<path>
genie-forge space-export --output-dir /Volumes/main/default/genie_forge/exports/
genie-forge validate --config /Volumes/main/default/genie_forge/conf/spaces/
```

### Auto-Detection in Notebooks

When using the Python API in Databricks notebooks, `ProjectPaths` automatically uses Volume paths:

```python
from genie_forge import ProjectPaths

paths = ProjectPaths(
    project_name="my_project",
    catalog="main",
    schema="default",
    volume_name="genie_forge"
)
# Automatically uses /Volumes/main/default/genie_forge/my_project/
```

---

## Tips and Best Practices

1. **Always plan before apply**: Review changes with `plan` before running `apply`
2. **Use dry-run mode**: Add `--dry-run` to preview any destructive operation
3. **Version control your state**: Include `.genie-forge.json` in git for team collaboration
4. **Use environment profiles**: Create separate profiles for dev/staging/prod
5. **Validate in CI/CD**: Add `genie-forge validate --strict` to your pipeline
6. **Export before modifying**: Use `space-export` to backup spaces before changes
7. **Use ProjectPaths in notebooks**: Auto-detect environment for correct paths
8. **Unified catalog/schema**: Use the same catalog and schema for tables and volume storage
