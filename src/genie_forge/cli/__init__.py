"""
Command-line interface for Genie-Forge.

CLI Commands (ordered by user journey):
1. init: Initialize a new Genie-Forge project
2. profiles: List available Databricks profiles
3. whoami: Show current authenticated user and workspace
4. setup-demo: Create demo tables for examples
5. cleanup-demo: Remove demo tables
6. validate: Validate config file syntax and schema
7. plan: Show what will be created/updated
8. apply: Deploy changes
9. status: Show deployment status
10. drift: Detect drift between local state and workspace
11. find: Find space by name in workspace
12. import: Import existing spaces into management
13. destroy: Delete spaces
"""

from __future__ import annotations

import click

from genie_forge.__about__ import __version__

# Import commands from submodules
from genie_forge.cli.demo import cleanup_demo, demo_status, setup_demo
from genie_forge.cli.find import find
from genie_forge.cli.import_cmd import import_space
from genie_forge.cli.init import init
from genie_forge.cli.profiles import profiles
from genie_forge.cli.space_cmd import (
    list_spaces,
    show,
    space_clone,
    space_create,
    space_delete,
    space_export,
    space_find,
    space_get,
    space_list,
)
from genie_forge.cli.spaces import apply, destroy, drift, plan, status
from genie_forge.cli.state_cmd import state_import, state_list, state_pull, state_remove, state_show
from genie_forge.cli.validate import validate
from genie_forge.cli.whoami import whoami


class OrderedGroup(click.Group):
    """Custom Click Group that orders commands by user journey."""

    COMMAND_ORDER = [
        # Project Setup
        "init",
        "profiles",
        "whoami",
        # Demo Management
        "setup-demo",
        "demo-status",
        "cleanup-demo",
        # Configuration
        "validate",
        # Deployment
        "plan",
        "apply",
        "status",
        "drift",
        # Space Operations (space-* group)
        "space-list",
        "space-find",
        "space-get",
        "space-create",
        "space-clone",
        "space-export",
        "space-delete",
        # State Operations (state-* group)
        "state-list",
        "state-show",
        "state-pull",
        "state-remove",
        "state-import",
        # Legacy/Aliases
        "find",
        "list-spaces",
        "show",
        "import",
        # Cleanup
        "destroy",
    ]

    def list_commands(self, ctx: click.Context) -> list[str]:
        """Return commands in user journey order."""
        ordered = [cmd for cmd in self.COMMAND_ORDER if cmd in self.commands]
        remaining = [cmd for cmd in self.commands if cmd not in ordered]
        return ordered + remaining


@click.group(cls=OrderedGroup)
@click.version_option(version=__version__, prog_name="genie-forge")
@click.pass_context
def main(ctx: click.Context) -> None:
    """Genie-Forge: Forge your Databricks Genie spaces at scale.

    A Terraform-like Infrastructure-as-Code workflow for managing Databricks
    Genie spaces through YAML configuration files.

    \b
    CORE WORKFLOW:
    ─────────────
    1. DEFINE    → Write space configs in conf/spaces/*.yaml
    2. VALIDATE  → genie-forge validate --config conf/spaces/
    3. PLAN      → genie-forge plan --env dev --profile YOUR_PROFILE
    4. APPLY     → genie-forge apply --env dev --profile YOUR_PROFILE
    5. STATUS    → genie-forge status --env dev

    \b
    GETTING STARTED:
    ────────────────
    1. Check available profiles:
       $ genie-forge profiles

    2. (Optional) Set up demo tables:
       $ genie-forge setup-demo --catalog my_cat --schema my_schema --warehouse-id abc123

    3. Validate your configurations:
       $ genie-forge validate --config conf/spaces/

    4. Preview changes:
       $ genie-forge plan --env dev --profile YOUR_PROFILE

    5. Deploy:
       $ genie-forge apply --env dev --profile YOUR_PROFILE
    """
    ctx.ensure_object(dict)


# Register all commands (in order)
# Project Setup
main.add_command(init)
main.add_command(profiles)
main.add_command(whoami)
# Demo Management
main.add_command(setup_demo)
main.add_command(demo_status)
main.add_command(cleanup_demo)
# Configuration
main.add_command(validate)
# Deployment
main.add_command(plan)
main.add_command(apply)
main.add_command(status)
main.add_command(drift)
# Space Operations (space-* group)
main.add_command(space_list)
main.add_command(space_find)
main.add_command(space_get)
main.add_command(space_create)
main.add_command(space_clone)
main.add_command(space_export)
main.add_command(space_delete)
# State Operations (state-* group)
main.add_command(state_list)
main.add_command(state_show)
main.add_command(state_pull)
main.add_command(state_remove)
main.add_command(state_import)
# Legacy/Aliases
main.add_command(find)
main.add_command(list_spaces)
main.add_command(show)
main.add_command(import_space)
# Cleanup
main.add_command(destroy)


if __name__ == "__main__":
    main()
