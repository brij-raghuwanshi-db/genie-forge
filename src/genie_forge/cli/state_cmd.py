"""State operations commands (state-* group).

This module provides commands for viewing and managing the local state file
that tracks deployed Genie spaces.

Commands:
- state-list: Simple list of tracked spaces
- state-show: Detailed view of state file
- state-pull: Refresh state from workspace
- state-remove: Remove a space from state tracking
- state-import: Alias for import command
"""

from __future__ import annotations

import json
import sys
from typing import Optional

import click
from rich.table import Table

from genie_forge.cli.common import (
    console,
    create_progress_bar,
    get_genie_client,
    get_state_environment,
    load_state_file,
    print_error,
    print_section_header,
    print_success,
    print_warning,
    save_state_file,
    truncate_string,
)

# =============================================================================
# state-list Command
# =============================================================================


@click.command("state-list")
@click.option(
    "--env",
    "-e",
    help="Filter by environment (default: all)",
)
@click.option(
    "--state-file",
    "-s",
    type=click.Path(),
    default=".genie-forge.json",
    help="Path to state file",
)
@click.option(
    "--show-ids",
    is_flag=True,
    help="Show Databricks space IDs",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "plain", "json"]),
    default="table",
    help="Output format",
)
def state_list(
    env: Optional[str],
    state_file: str,
    show_ids: bool,
    output_format: str,
) -> None:
    """List tracked spaces in the state file.

    Shows a simple list of all spaces that genie-forge is tracking.
    This is the state file's view of what's deployed.

    \b
    EXAMPLES:
    ─────────
    # List all tracked spaces
    $ genie-forge state-list

    # List spaces in specific environment
    $ genie-forge state-list --env dev

    # Show with Databricks IDs
    $ genie-forge state-list --env prod --show-ids

    # Output as plain list (for scripting)
    $ genie-forge state-list --env dev --format plain
    """
    data = load_state_file(state_file)
    if data is None:
        return

    environments = data.get("environments", {})

    if not environments:
        print_warning("No environments found in state file")
        return

    # Filter by environment if specified
    if env:
        if env not in environments:
            print_error(f"Environment '{env}' not found in state file")
            console.print(f"\nAvailable environments: {', '.join(environments.keys())}")
            sys.exit(1)
        environments = {env: environments[env]}

    # Collect all spaces
    all_spaces = []
    for env_name, env_data in environments.items():
        for space_id, space_data in env_data.get("spaces", {}).items():
            all_spaces.append(
                {
                    "env": env_name,
                    "logical_id": space_id,
                    "title": space_data.get("title", ""),
                    "databricks_id": space_data.get("databricks_space_id", ""),
                    "status": space_data.get("status", ""),
                }
            )

    if not all_spaces:
        print_warning("No spaces tracked in state file")
        return

    # Output based on format
    if output_format == "json":
        console.print(json.dumps(all_spaces, indent=2))

    elif output_format == "plain":
        for space in all_spaces:
            if show_ids:
                console.print(f"{space['logical_id']}\t{space['databricks_id']}")
            else:
                console.print(space["logical_id"])

    else:
        # Table format
        for env_name in sorted(environments.keys()):
            env_spaces = [s for s in all_spaces if s["env"] == env_name]
            if not env_spaces:
                continue

            console.print(f"\n[bold]Tracked Spaces in '{env_name}'[/bold]")
            console.print("═" * 50)

            if show_ids:
                table = Table()
                table.add_column("Logical ID", style="cyan")
                table.add_column("Title")
                table.add_column("Databricks ID", style="dim")

                for space in env_spaces:
                    table.add_row(
                        space["logical_id"],
                        space["title"],
                        truncate_string(space["databricks_id"], 20),
                    )
                console.print(table)
            else:
                for space in env_spaces:
                    console.print(f"  • {space['logical_id']}")

            console.print(f"\nTotal: {len(env_spaces)} spaces")


# =============================================================================
# state-show Command
# =============================================================================


@click.command("state-show")
@click.option(
    "--env",
    "-e",
    help="Filter by environment (default: all)",
)
@click.option(
    "--state-file",
    "-s",
    type=click.Path(),
    default=".genie-forge.json",
    help="Path to state file",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
def state_show(
    env: Optional[str],
    state_file: str,
    output_format: str,
) -> None:
    """View detailed state file information.

    Shows the full state file contents including config hashes,
    timestamps, and Databricks IDs. Useful for debugging state issues.

    \b
    EXAMPLES:
    ─────────
    # Show all environments
    $ genie-forge state-show

    # Show only dev environment
    $ genie-forge state-show --env dev

    # Export as JSON (for backup or scripting)
    $ genie-forge state-show --format json > state_backup.json
    """
    data = load_state_file(state_file)
    if data is None:
        return

    # Filter by environment if specified
    if env:
        env_data = get_state_environment(data, env)
        if env_data is None:
            return
        data["environments"] = {env: env_data}

    if output_format == "json":
        console.print(json.dumps(data, indent=2))
        return

    # Table format
    print_section_header(f"State File: {state_file}")

    console.print(f"\n  Version:    {data.get('version', 'N/A')}")
    console.print(f"  Project ID: {data.get('project_id', 'N/A')}")
    if data.get("project_name"):
        console.print(f"  Project:    {data.get('project_name')}")
    console.print(f"  Created:    {data.get('created_at', 'N/A')}")

    environments = data.get("environments", {})

    for env_name, env_data in sorted(environments.items()):
        console.print(f"\n[bold]ENVIRONMENT: {env_name}[/bold]")
        console.print("─" * 60)
        console.print(f"  Workspace:    {env_data.get('workspace_url', 'N/A')}")
        console.print(f"  Last Applied: {env_data.get('last_applied', 'Never')}")
        console.print(f"  Spaces:       {len(env_data.get('spaces', {}))}")

        spaces = env_data.get("spaces", {})
        if spaces:
            console.print()

            table = Table()
            table.add_column("Logical ID", style="cyan")
            table.add_column("Databricks ID", style="dim", max_width=24)
            table.add_column("Status")
            table.add_column("Config Hash", style="dim", max_width=12)
            table.add_column("Last Applied")

            for space_id, space_data in spaces.items():
                db_id_display = truncate_string(space_data.get("databricks_space_id", ""), 20)
                config_hash = (
                    truncate_string(space_data.get("config_hash", ""), 8)
                    if space_data.get("config_hash")
                    else ""
                )

                status = space_data.get("status", "UNKNOWN")
                if status == "APPLIED":
                    status_display = "[green]APPLIED[/green]"
                elif status == "PENDING":
                    status_display = "[yellow]PENDING[/yellow]"
                elif status == "FAILED":
                    status_display = "[red]FAILED[/red]"
                else:
                    status_display = status

                last_applied = space_data.get("last_applied", "")
                if last_applied:
                    # Shorten timestamp
                    last_applied = last_applied[:19].replace("T", " ")

                table.add_row(
                    space_id,
                    db_id_display,
                    status_display,
                    config_hash,
                    last_applied,
                )

            console.print(table)

            # Show any errors
            for space_id, space_data in spaces.items():
                if space_data.get("error"):
                    console.print(f"\n  [red]Error in {space_id}:[/red] {space_data['error']}")

    console.print()


# =============================================================================
# state-remove Command
# =============================================================================


@click.command("state-remove")
@click.argument("space_id")
@click.option(
    "--env",
    "-e",
    required=True,
    help="Environment to remove from",
)
@click.option(
    "--state-file",
    "-s",
    type=click.Path(),
    default=".genie-forge.json",
    help="Path to state file",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompt",
)
def state_remove(
    space_id: str,
    env: str,
    state_file: str,
    force: bool,
) -> None:
    """Remove a space from state tracking.

    This removes the space from the local state file WITHOUT deleting it
    from Databricks. The space will continue to exist in the workspace
    but will no longer be managed by genie-forge.

    Use this when you want to:
    - Stop managing a space with genie-forge
    - Fix state file corruption
    - Remove orphaned entries

    \b
    EXAMPLES:
    ─────────
    # Remove a space from dev environment
    $ genie-forge state-remove my_space --env dev

    # Skip confirmation prompt
    $ genie-forge state-remove old_space --env prod --force
    """
    data = load_state_file(state_file, show_not_found_message=False)
    if data is None:
        print_error(f"State file not found: {state_file}")
        sys.exit(1)

    # Check if environment exists
    env_data = get_state_environment(data, env)
    if env_data is None:
        sys.exit(1)
    spaces = env_data.get("spaces", {})

    # Check if space exists
    if space_id not in spaces:
        print_error(f"Space '{space_id}' not found in state for environment '{env}'")
        if spaces:
            console.print(f"\nAvailable spaces in '{env}':")
            for s in spaces.keys():
                console.print(f"  - {s}")
        sys.exit(1)

    space_data = spaces[space_id]

    # Show what will be removed
    print_section_header(f"Remove from State: {space_id}")
    console.print()
    console.print(f"  Environment:    {env}")
    console.print(f"  Logical ID:     {space_id}")
    console.print(f"  Databricks ID:  {space_data.get('databricks_space_id', 'N/A')}")
    console.print(f"  Title:          {space_data.get('title', 'N/A')}")
    console.print()

    if not force:
        console.print(
            "[yellow]⚠ WARNING:[/yellow] This will remove the space from genie-forge tracking."
        )
        console.print("  The space will [bold]CONTINUE TO EXIST[/bold] in Databricks.")
        console.print("  Genie-forge will no longer manage or track this space.")
        console.print()

        if not click.confirm(f"Remove '{space_id}' from state?"):
            console.print("[dim]Cancelled.[/dim]")
            return

    # Remove the space
    del spaces[space_id]

    # Save updated state
    save_state_file(data, state_file)

    print_success(f"Removed '{space_id}' from state")
    console.print()
    console.print("  The space still exists in Databricks.")
    if space_data.get("databricks_space_id"):
        console.print("  To delete it, use 'genie-forge destroy' or delete via Databricks UI.")


# =============================================================================
# state-pull Command
# =============================================================================


@click.command("state-pull")
@click.option(
    "--env",
    "-e",
    required=True,
    help="Environment to refresh",
)
@click.option(
    "--profile",
    "-p",
    help="Databricks CLI profile to use",
)
@click.option(
    "--state-file",
    "-s",
    type=click.Path(),
    default=".genie-forge.json",
    help="Path to state file",
)
@click.option(
    "--verify-only",
    is_flag=True,
    help="Only verify spaces exist without updating state",
)
def state_pull(
    env: str,
    profile: Optional[str],
    state_file: str,
    verify_only: bool,
) -> None:
    """Refresh local state from workspace.

    Verifies tracked spaces still exist in Databricks and updates
    the state file with current information. Useful for syncing
    state after manual changes or detecting deleted spaces.

    \b
    EXAMPLES:
    ─────────
    # Refresh state for dev environment
    $ genie-forge state-pull --env dev --profile DEV

    # Verify spaces without updating state
    $ genie-forge state-pull --env prod --profile PROD --verify-only
    """
    from datetime import datetime, timezone

    data = load_state_file(state_file, show_not_found_message=False)
    if data is None:
        print_error(f"State file not found: {state_file}")
        sys.exit(1)

    # Check if environment exists
    env_data = get_state_environment(data, env)
    if env_data is None:
        sys.exit(1)

    spaces = env_data.get("spaces", {})

    if not spaces:
        print_warning(f"No spaces tracked in environment '{env}'")
        return

    client = get_genie_client(profile=profile)

    console.print()
    print_section_header(f"Refreshing State: {env}")
    console.print(f"\n  Workspace:  {client.workspace_url}")
    console.print(f"  Spaces:     {len(spaces)}")
    console.print()

    # Track results
    verified = 0
    updated = 0
    missing = 0
    errors = []

    with create_progress_bar("Verifying spaces...") as progress:
        task = progress.add_task("Verifying...", total=len(spaces))

        for logical_id, space_data in list(spaces.items()):
            progress.update(task, advance=1)

            db_space_id = space_data.get("databricks_space_id")
            if not db_space_id:
                errors.append(
                    {
                        "logical_id": logical_id,
                        "error": "No Databricks space ID in state",
                    }
                )
                continue

            try:
                # Fetch current space from Databricks
                actual_space = client.get_space(db_space_id)

                # Compare and update
                actual_title = actual_space.get("title", "")
                state_title = space_data.get("title", "")

                if actual_title != state_title:
                    if not verify_only:
                        spaces[logical_id]["title"] = actual_title
                    updated += 1

                verified += 1

            except Exception as e:
                # Space no longer exists
                missing += 1
                errors.append(
                    {
                        "logical_id": logical_id,
                        "databricks_id": db_space_id,
                        "error": f"Not found in workspace: {e}",
                    }
                )

    # Summary
    console.print()
    print_section_header("Pull Summary")
    console.print(f"\n  [green]Verified:[/green]  {verified}")
    if updated:
        console.print(f"  [yellow]Updated:[/yellow]   {updated}")
    if missing:
        console.print(f"  [red]Missing:[/red]   {missing}")

    # Show missing/error details
    if errors:
        console.print("\n[bold]Issues Found:[/bold]")
        console.print("─" * 60)
        for err in errors:
            console.print(f"  [red]✗[/red] {err['logical_id']}: {err['error']}")

    if verify_only:
        console.print("\n[dim]Verify-only mode: No changes made to state file[/dim]")
    elif updated > 0 or missing > 0:
        # Update last_applied timestamp
        env_data["last_applied"] = datetime.now(timezone.utc).isoformat()

        # Save state
        save_state_file(data, state_file)
        print_success("State file updated")

        if missing > 0:
            console.print()
            console.print("[yellow]Note:[/yellow] Missing spaces are still in state.")
            console.print("  Use 'genie-forge state-remove' to remove them, or")
            console.print("  'genie-forge apply' to recreate them from config.")
    else:
        print_success("State is in sync with workspace")

    console.print()


# =============================================================================
# state-import Command (Alias for import)
# =============================================================================


@click.command("state-import")
@click.argument("space_id", required=False)
@click.option(
    "--pattern",
    "-n",
    help="Import spaces matching this name pattern (e.g., 'Sales*'). "
    "Use instead of SPACE_ID to import multiple spaces.",
)
@click.option(
    "--env",
    "-e",
    default="dev",
    help="Environment to import into (e.g., dev, staging, prod).",
)
@click.option(
    "--as",
    "logical_id",
    help="Logical ID for the imported space. If not provided, derived from title. "
    "Only valid when importing a single space by ID.",
)
@click.option(
    "--profile",
    "-p",
    help="Databricks CLI profile for authentication.",
)
@click.option(
    "--state-file",
    "-s",
    default=".genie-forge.json",
    help="Path to state file. Default: .genie-forge.json.",
)
@click.option(
    "--output-dir",
    "-o",
    default="conf/spaces",
    help="Directory to write YAML config files. Default: conf/spaces.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be imported without making changes.",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing config files and state entries.",
)
@click.pass_context
def state_import(
    ctx: click.Context,
    space_id: str | None,
    pattern: str | None,
    env: str,
    logical_id: str | None,
    profile: str | None,
    state_file: str,
    output_dir: str,
    dry_run: bool,
    force: bool,
) -> None:
    """Import existing spaces into management. (Alias for import)

    Brings existing Databricks Genie spaces under genie-forge management
    by adding them to the state file and optionally generating config files.

    \b
    EXAMPLES:
    ─────────
    # Import a single space by ID
    $ genie-forge state-import 01abc123 --env prod --as sales_analytics --profile PROD

    # Import by pattern
    $ genie-forge state-import --pattern "Sales*" --env prod --profile PROD
    """
    from genie_forge.cli.import_cmd import import_space

    ctx.invoke(
        import_space,
        space_id=space_id,
        pattern=pattern,
        env=env,
        logical_id=logical_id,
        profile=profile,
        state_file=state_file,
        output_dir=output_dir,
        dry_run=dry_run,
        force=force,
    )
