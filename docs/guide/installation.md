---
title: Installation
description: Install Genie-Forge and configure authentication
---

# Installation

## Requirements

- **Python**: 3.9 or higher
- **Databricks Workspace**: With Genie (AI/BI) enabled
- **Authentication**: Databricks CLI profile or environment variables

## Install from PyPI

=== "pip"

    ```bash
    pip install genie-forge
    ```

=== "pipx (recommended for CLI tools)"

    ```bash
    pipx install genie-forge
    ```

=== "conda"

    ```bash
    # Not yet on conda-forge, use pip in conda environment
    conda create -n genie-forge python=3.11
    conda activate genie-forge
    pip install genie-forge
    ```

## Install from Source

```bash
git clone https://github.com/brij-raghuwanshi-db/genie-forge.git
cd genie-forge
pip install -e ".[dev]"  # Includes development dependencies
```

## Verify Installation

```bash
# Check version
genie-forge --version

# Check available commands
genie-forge --help
```

## Authentication Setup

Genie-Forge uses the same authentication as the Databricks CLI and SDK.

### Option 1: Databricks CLI Profile (Recommended)

```bash
# Configure a profile
databricks configure --profile MY_WORKSPACE

# Use with genie-forge
genie-forge whoami --profile MY_WORKSPACE
```

### Option 2: Environment Variables

```bash
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_TOKEN="dapi..."

genie-forge whoami
```

### Option 3: OAuth (M2M)

```bash
export DATABRICKS_HOST="https://your-workspace.cloud.databricks.com"
export DATABRICKS_CLIENT_ID="..."
export DATABRICKS_CLIENT_SECRET="..."

genie-forge whoami
```

## Verify Authentication

```bash
genie-forge whoami
```

Expected output:
```
Workspace: https://your-workspace.cloud.databricks.com
User: your.email@company.com
Profile: MY_WORKSPACE
```

## Multiple Workspaces

Use profiles to manage multiple workspaces:

```bash
# List configured profiles
genie-forge profiles

# Use a specific profile
genie-forge space-list --profile PROD_WORKSPACE
```

## Databricks Notebooks

When running in Databricks notebooks, authentication is automatic:

```python
from genie_forge import GenieClient

# No credentials needed - uses notebook context
client = GenieClient()
```

## Environment Variables

Genie-Forge supports several environment variables for configuration and debugging:

### Authentication Variables

| Variable | Description |
|----------|-------------|
| `DATABRICKS_HOST` | Workspace URL (e.g., `https://your-workspace.cloud.databricks.com`) |
| `DATABRICKS_TOKEN` | Personal access token for authentication |
| `DATABRICKS_CLIENT_ID` | OAuth client ID (for M2M authentication) |
| `DATABRICKS_CLIENT_SECRET` | OAuth client secret (for M2M authentication) |

### Configuration Variables

| Variable | Description |
|----------|-------------|
| `GENIE_PROFILE` | Default Databricks CLI profile to use |
| `GENIE_WAREHOUSE_ID` | Default SQL warehouse ID |
| `GENIE_CATALOG` | Default Unity Catalog name |
| `GENIE_SCHEMA` | Default schema name |

### Debugging Variables

| Variable | Description |
|----------|-------------|
| `GENIE_FORGE_DEBUG` | Set to `1` to enable verbose debug output |

### Example: Debug Mode

```bash
# Enable debug output for troubleshooting
export GENIE_FORGE_DEBUG=1
genie-forge plan --env dev --profile MY_PROFILE

# Or inline for a single command
GENIE_FORGE_DEBUG=1 genie-forge apply --env dev
```

Debug mode provides:

- Detailed API request/response logging
- Variable substitution tracing
- State file operations
- Error stack traces

## Troubleshooting

### "Authentication failed"

1. Verify your token is valid: `databricks auth token`
2. Check the workspace URL format (include `https://`)
3. Ensure your token has appropriate permissions

### "Module not found"

```bash
# Verify installation
pip show genie-forge

# Reinstall if needed
pip install --force-reinstall genie-forge
```

### "Command not found"

```bash
# Check if installed in PATH
which genie-forge

# Or run as module
python -m genie_forge --help
```

## Next Steps

- [Quick Start Guide](getting-started.md) - Create your first project
- [CLI Reference](cli.md) - Full command documentation
