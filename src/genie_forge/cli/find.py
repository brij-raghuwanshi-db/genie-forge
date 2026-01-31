"""Find command for searching Genie spaces."""

from __future__ import annotations

import fnmatch
from typing import Optional

import click
from rich.table import Table

from genie_forge.cli.common import (
    console,
    fetch_all_spaces_paginated,
    get_genie_client,
    print_info,
    print_warning,
)
from genie_forge.state import StateManager


@click.command()
@click.option(
    "--name",
    "-n",
    required=True,
    help="Name pattern to search. Supports wildcards: '*' matches any characters.",
)
@click.option("--env", "-e", help="Filter by environment when searching local state.")
@click.option("--profile", "-p", help="Databricks CLI profile for workspace searches.")
@click.option("--workspace", is_flag=True, help="Search live Databricks workspace.")
def find(
    name: str,
    env: Optional[str],
    profile: Optional[str],
    workspace: bool,
) -> None:
    """Search for Genie spaces by name pattern.

    Find spaces either in your local state file (what Genie-Forge deployed)
    or directly in the live Databricks workspace (all spaces).

    \b
    TWO SEARCH MODES:
    ─────────────────
    1. WORKSPACE SEARCH (when --profile is provided):
       Queries the live Databricks Genie API.

    2. STATE SEARCH (when --env is provided without --profile):
       Searches the local .genie-forge.json state file.
    """
    search_workspace = workspace or (profile is not None)

    if search_workspace:
        client = get_genie_client(profile=profile)

        # Fetch all spaces with pagination progress
        all_spaces = fetch_all_spaces_paginated(
            client,
            show_progress=True,
            progress_description=f"Searching for '{name}'...",
        )

        # Filter by name pattern
        matches = []
        for space in all_spaces:
            title = space.get("title", "")
            if fnmatch.fnmatch(title.lower(), name.lower()):
                matches.append(space)

        console.print()

        if not matches:
            print_info(f"No spaces found matching '{name}' (searched {len(all_spaces)} spaces)")
            return

        table = Table(title=f"Spaces matching '{name}'")
        table.add_column("Title", style="cyan")
        table.add_column("Space ID")
        table.add_column("Warehouse ID")

        for space in matches:
            space_id = space.get("space_id") or space.get("id") or ""
            table.add_row(
                space.get("title", ""),
                space_id,
                space.get("warehouse_id", ""),
            )

        console.print(table)
        console.print(f"\nFound {len(matches)} matching space(s) (out of {len(all_spaces)} total)")
    else:
        state_manager = StateManager()

        if env:
            envs = [env]
        else:
            envs = list(state_manager.state.environments.keys())

        if not envs:
            print_warning("No environments in state. Use --profile to search the workspace.")
            return

        all_matches = []
        for env_name in envs:
            status = state_manager.status(env=env_name)
            for space in status["spaces"]:
                if fnmatch.fnmatch(space["title"].lower(), name.lower()):
                    all_matches.append((env_name, space))

        if not all_matches:
            print_info(f"No spaces found matching '{name}' in state")
            return

        table = Table(title=f"Spaces matching '{name}'")
        table.add_column("Environment", style="blue")
        table.add_column("Logical ID", style="cyan")
        table.add_column("Title")
        table.add_column("Space ID")

        for env_name, space in all_matches:
            table.add_row(
                env_name,
                space["logical_id"],
                space["title"],
                space["databricks_space_id"] or "-",
            )

        console.print(table)
        console.print(f"\nFound {len(all_matches)} space(s)")
