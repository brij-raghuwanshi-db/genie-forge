"""Profiles command for listing Databricks CLI profiles."""

from __future__ import annotations

import click

from genie_forge.auth import list_profiles
from genie_forge.cli.common import console, print_info


@click.command()
def profiles() -> None:
    """List available Databricks CLI profiles from ~/.databrickscfg.

    Shows all authentication profiles configured in your Databricks CLI
    configuration file. Use these profile names with the --profile option
    in other commands.

    \b
    PROFILE CONFIGURATION:
    ──────────────────────
    Profiles are defined in ~/.databrickscfg:

    [PROFILE_NAME]
    host = https://your-workspace.azuredatabricks.net
    token = dapi12345...

    \b
    AUTHENTICATION PRIORITY:
    ────────────────────────
    When connecting to Databricks, Genie-Forge checks (in order):
    1. Environment variables: DATABRICKS_HOST, DATABRICKS_TOKEN
    2. --profile option: Uses specified profile from ~/.databrickscfg
    3. Default profile: [DEFAULT] section in ~/.databrickscfg
    """
    available = list_profiles()

    if not available:
        print_info("No profiles found in ~/.databrickscfg")
        console.print("\nTo create a profile:")
        console.print("  1. Run: databricks configure --profile PROFILE_NAME")
        console.print("  2. Or edit ~/.databrickscfg manually")
        return

    console.print("Available profiles:")
    for profile_name in available:
        console.print(f"  - {profile_name}")
