# Architecture

This document explains how Genie-Forge works internally, including code flow and module dependencies.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              GENIE-FORGE ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐          │
│   │   CLI (bash)    │     │ Python Script   │     │ Databricks      │          │
│   │                 │     │                 │     │ Notebook        │          │
│   │ $ genie-forge   │     │ from genie_forge│     │ %pip install    │          │
│   │   <command>     │     │ import ...      │     │ genie-forge     │          │
│   └────────┬────────┘     └────────┬────────┘     └────────┬────────┘          │
│            │                       │                       │                    │
│            ▼                       ▼                       ▼                    │
│   ┌────────────────────────────────────────────────────────────────────┐       │
│   │                         ENTRY POINTS                                │       │
│   │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │       │
│   │  │   cli.py     │    │ __init__.py  │    │ __init__.py          │  │       │
│   │  │   main()     │    │ GenieClient  │    │ (package imports)    │  │       │
│   │  │   (Click)    │    │ StateManager │    │                      │  │       │
│   │  └──────┬───────┘    └──────┬───────┘    └──────────┬───────────┘  │       │
│   └─────────┼───────────────────┼───────────────────────┼──────────────┘       │
│             │                   │                       │                       │
│             ▼                   ▼                       ▼                       │
│   ┌────────────────────────────────────────────────────────────────────┐       │
│   │                         CORE MODULES                                │       │
│   │                                                                     │       │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐  │       │
│   │  │  auth.py    │  │ parsers.py  │  │  state.py   │  │ models.py │  │       │
│   │  │             │  │             │  │             │  │           │  │       │
│   │  │ - Profile   │  │ - YAML/JSON │  │ - Plan      │  │ - Pydantic│  │       │
│   │  │   loading   │  │   parsing   │  │ - Apply     │  │   schemas │  │       │
│   │  │ - Env vars  │  │ - Variable  │  │ - Destroy   │  │ - Config  │  │       │
│   │  │ - Workspace │  │   substit.  │  │ - State I/O │  │   models  │  │       │
│   │  │   client    │  │ - Validation│  │             │  │           │  │       │
│   │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘  │       │
│   └─────────┼────────────────┼────────────────┼────────────────┼────────┘       │
│             │                │                │                │                │
│             ▼                ▼                ▼                ▼                │
│   ┌────────────────────────────────────────────────────────────────────┐       │
│   │                         API LAYER                                   │       │
│   │  ┌───────────────────────────────────────────────────────────────┐ │       │
│   │  │                     client.py (GenieClient)                   │ │       │
│   │  │  - create_space()    - list_spaces()      - delete_space()    │ │       │
│   │  │  - update_space()    - find_spaces_by_name()                  │ │       │
│   │  └───────────────────────────────┬───────────────────────────────┘ │       │
│   │                                  │                                  │       │
│   │  ┌───────────────────────────────┴───────────────────────────────┐ │       │
│   │  │                  serializer.py (SpaceSerializer)              │ │       │
│   │  │  - to_api_format()   - Convert Pydantic → API request body    │ │       │
│   │  └───────────────────────────────────────────────────────────────┘ │       │
│   └────────────────────────────────────────────────────────────────────┘       │
│                                      │                                          │
│                                      ▼                                          │
│   ┌────────────────────────────────────────────────────────────────────┐       │
│   │                    DATABRICKS WORKSPACE                             │       │
│   │  ┌─────────────────────────────────────────────────────────────┐   │       │
│   │  │              Databricks SDK (WorkspaceClient)               │   │       │
│   │  │                                                             │   │       │
│   │  │   Genie API:  /api/2.0/genie/spaces                         │   │       │
│   │  │   SQL API:    /api/2.0/sql/statements (for demo tables)     │   │       │
│   │  └─────────────────────────────────────────────────────────────┘   │       │
│   └────────────────────────────────────────────────────────────────────┘       │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## CLI Command Flow

When you run a CLI command, here's how the code flows:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  CLI COMMAND FLOW: genie-forge apply --env dev --profile MY_PROFILE             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  STEP 1: Entry Point                                                            │
│  ───────────────────                                                            │
│                                                                                 │
│  pyproject.toml:                                                                │
│    [project.scripts]                                                            │
│    genie-forge = "genie_forge.cli:main"                                         │
│                         │                                                       │
│                         ▼                                                       │
│  cli.py:                                                                        │
│    @click.group()                                                               │
│    def main(ctx): ...           ◄── Click framework routes commands             │
│                         │                                                       │
│                         ▼                                                       │
│    @main.command()                                                              │
│    def apply(env, config, profile, ...):  ◄── Specific command handler          │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  STEP 2: Authentication                                                         │
│  ──────────────────────                                                         │
│                                                                                 │
│  cli.py → client.py → auth.py                                                   │
│                                                                                 │
│    client = GenieClient(profile=profile)                                        │
│                         │                                                       │
│                         ▼                                                       │
│    auth.py:get_workspace_client()                                               │
│      1. Check env vars: DATABRICKS_HOST, DATABRICKS_TOKEN                       │
│      2. Check --profile → ~/.databrickscfg                                      │
│      3. Fall back to [DEFAULT] profile                                          │
│                         │                                                       │
│                         ▼                                                       │
│    databricks.sdk.WorkspaceClient(...)                                          │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  STEP 3: Configuration Loading                                                  │
│  ────────────────────────────                                                   │
│                                                                                 │
│  cli.py → parsers.py → models.py                                                │
│                                                                                 │
│    parser = MetadataParser(env=env)                                             │
│    configs = parser.parse_directory(config_path)                                │
│                         │                                                       │
│                         ▼                                                       │
│    parsers.py:MetadataParser                                                    │
│      1. Load env config: conf/environments/{env}.yaml                           │
│      2. Extract variables: ${warehouse_id}, ${catalog}, etc.                    │
│      3. Parse space configs: conf/spaces/*.yaml                                 │
│      4. Substitute variables                                                    │
│                         │                                                       │
│                         ▼                                                       │
│    models.py:SpaceConfig (Pydantic validation)                                  │
│                         │                                                       │
│                         ▼                                                       │
│    List[SpaceConfig]                                                            │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  STEP 4: Planning                                                               │
│  ───────────────                                                                │
│                                                                                 │
│  cli.py → state.py                                                              │
│                                                                                 │
│    state_mgr = StateManager(state_file=".genie-forge.json")                     │
│    plan = state_mgr.plan(configs, client, env=env)                              │
│                         │                                                       │
│                         ▼                                                       │
│    state.py:StateManager.plan()                                                 │
│      1. Load existing state from .genie-forge.json                              │
│      2. Compare configs vs deployed state                                       │
│      3. Determine actions: CREATE, UPDATE, DELETE, NO_CHANGE                    │
│                         │                                                       │
│                         ▼                                                       │
│    models.py:Plan with PlanItems                                                │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  STEP 5: Apply                                                                  │
│  ────────────                                                                   │
│                                                                                 │
│  state.py → client.py → serializer.py → Databricks API                          │
│                                                                                 │
│    results = state_mgr.apply(plan, client)                                      │
│                         │                                                       │
│                         ▼                                                       │
│    for item in plan.items:                                                      │
│        if item.action == CREATE:                                                │
│            space_id = client.create_space(config)                               │
│                         │                                                       │
│                         ▼                                                       │
│    client.py → serializer.py                                                    │
│      SpaceSerializer.to_api_format(config) → API JSON                           │
│                         │                                                       │
│                         ▼                                                       │
│    POST /api/2.0/genie/spaces                                                   │
│                                                                                 │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  STEP 6: State Update                                                           │
│  ───────────────────                                                            │
│                                                                                 │
│    state.py → .genie-forge.json                                                 │
│                                                                                 │
│    Update state with Databricks space ID:                                       │
│    {                                                                            │
│      "employee_analytics": {                                                    │
│        "databricks_space_id": "01ef274d-...",                                   │
│        "status": "APPLIED",                                                     │
│        "last_applied": "2026-01-25T..."                                         │
│      }                                                                          │
│    }                                                                            │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## File Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│  FILE DEPENDENCY GRAPH                                                          │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│                           ┌─────────────────┐                                   │
│                           │  pyproject.toml │                                   │
│                           │  (entry point)  │                                   │
│                           └────────┬────────┘                                   │
│                                    │                                            │
│                                    ▼                                            │
│                           ┌─────────────────┐                                   │
│                           │     cli.py      │◄─────── Click commands            │
│                           └────────┬────────┘                                   │
│                                    │                                            │
│            ┌───────────────────────┼───────────────────────┐                    │
│            │                       │                       │                    │
│            ▼                       ▼                       ▼                    │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│   │    auth.py      │    │   parsers.py    │    │    state.py     │            │
│   │                 │    │                 │    │                 │            │
│   │ - list_profiles │    │ - MetadataParser│    │ - StateManager  │            │
│   │ - get_workspace │    │ - validate_conf │    │ - plan()        │            │
│   │   _client       │    │ - parse_dir     │    │ - apply()       │            │
│   └────────┬────────┘    └────────┬────────┘    │ - destroy()     │            │
│            │                      │             └────────┬────────┘            │
│            │                      │                      │                      │
│            │                      ▼                      │                      │
│            │             ┌─────────────────┐             │                      │
│            │             │   models.py     │◄────────────┘                      │
│            │             │                 │                                    │
│            │             │ - SpaceConfig   │                                    │
│            │             │ - TableConfig   │                                    │
│            │             │ - Plan/PlanItem │                                    │
│            │             │ - SpaceState    │                                    │
│            │             └────────┬────────┘                                    │
│            │                      │                                             │
│            ▼                      ▼                                             │
│   ┌─────────────────────────────────────────┐                                   │
│   │              client.py                  │                                   │
│   │                                         │                                   │
│   │  - GenieClient                          │                                   │
│   │  - create_space() / update_space()      │                                   │
│   │  - delete_space() / list_spaces()       │                                   │
│   │  - find_spaces_by_name()                │                                   │
│   └────────────────┬────────────────────────┘                                   │
│                    │                                                            │
│                    ▼                                                            │
│   ┌─────────────────────────────────────────┐                                   │
│   │            serializer.py                │                                   │
│   │                                         │                                   │
│   │  - SpaceSerializer                      │                                   │
│   │  - to_api_format()                      │                                   │
│   └────────────────┬────────────────────────┘                                   │
│                    │                                                            │
│                    ▼                                                            │
│   ┌─────────────────────────────────────────┐                                   │
│   │         databricks-sdk                  │                                   │
│   │       (WorkspaceClient)                 │                                   │
│   └─────────────────────────────────────────┘                                   │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Modules

| Module | Responsibility |
|--------|----------------|
| `cli.py` | CLI commands using Click framework |
| `auth.py` | Authentication (profiles, env vars, workspace client) |
| `parsers.py` | YAML/JSON parsing, variable substitution, validation |
| `models.py` | Pydantic data models (SpaceConfig, Plan, State) |
| `state.py` | State management (plan, apply, destroy operations) |
| `client.py` | Genie API client (CRUD operations) |
| `serializer.py` | Convert Pydantic models to API format |
| `utils.py` | Environment detection, path management, helpers |
| `demo_tables.py` | Demo table creation/cleanup via SQL API |

---

## State File Format

Genie-Forge tracks deployments in `.genie-forge.json`:

```json
{
  "version": "1.0",
  "project_id": "my_project",
  "environments": {
    "dev": {
      "workspace_url": "https://workspace.databricks.com",
      "last_applied": "2026-01-25T12:00:00",
      "spaces": {
        "employee_analytics": {
          "logical_id": "employee_analytics",
          "databricks_space_id": "01ef274d-...",
          "title": "Employee Analytics Dashboard",
          "config_hash": "sha256:abc...",
          "status": "APPLIED",
          "last_applied": "2026-01-25T12:00:00"
        }
      }
    }
  }
}
```

---

## Authentication Priority

When connecting to Databricks, authentication is resolved in this order:

1. **Direct credentials** - `--host` and `--token` options (rarely used)
2. **`--profile` flag** - Uses specified profile from `~/.databrickscfg` (recommended)
3. **Environment variables** - `DATABRICKS_HOST` + `DATABRICKS_TOKEN`
4. **Default profile** - `[DEFAULT]` section in `~/.databrickscfg`

---

## Reliability Features

1. **Retry Logic**: All API calls automatically retry on transient failures
   - Exponential backoff (1s → 2s → 4s)
   - Retries on connection errors and timeouts
   - Maximum 3 retry attempts by default

2. **Rate Limiting**: Prevent API throttling during bulk operations
   - Configurable requests per second
   - Applied between parallel task submissions

3. **Pagination**: Automatically handles large result sets
   - `list_spaces()` fetches all pages automatically
   - Handles workspaces with thousands of spaces

---

## Environment Detection

Genie-Forge automatically detects the execution environment:

```python
from genie_forge import is_running_on_databricks, ProjectPaths

# Check if running on Databricks
if is_running_on_databricks():
    # Uses Unity Catalog Volumes for file storage
    # Path: /Volumes/<catalog>/<schema>/<volume>/<project>/
    pass
else:
    # Uses local filesystem
    # Path: ~/.genie-forge/<project>/
    pass
```

### Path Management

The `ProjectPaths` class provides automatic path configuration:

| Environment | Root Path | Example |
|-------------|-----------|---------|
| **Databricks** | `/Volumes/<catalog>/<schema>/<volume>/<project>/` | `/Volumes/main/default/genie_forge/demo/` |
| **Local** | `~/.genie-forge/<project>/` | `/Users/you/.genie-forge/demo/` |

**Key Principle**: The same `catalog` and `schema` are used for both:
- Data tables (for Genie spaces to query)
- Volume storage (for configuration and state files)

```python
paths = ProjectPaths(
    project_name="my_project",
    catalog="main",           # Used for tables AND volume
    schema="default",         # Used for tables AND volume
    volume_name="genie_forge"
)

# Tables:  main.default.employees, main.default.sales, etc.
# Volume:  /Volumes/main/default/genie_forge/my_project/
```
