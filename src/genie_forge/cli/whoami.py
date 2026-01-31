"""Show current authenticated user and workspace identity."""

from __future__ import annotations

from typing import Optional

import click

from genie_forge.cli.common import console, get_genie_client, print_error, with_spinner


@click.command()
@click.option(
    "--profile",
    "-p",
    help="Databricks CLI profile to use",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON",
)
def whoami(profile: Optional[str], output_json: bool) -> None:
    """Show current authenticated user and workspace.

    Displays information about the currently authenticated Databricks user
    and workspace. Useful for verifying you're connected to the correct
    environment before running operations.

    \b
    EXAMPLES:
    ─────────
    # Show current identity
    $ genie-forge whoami

    # Use a specific profile
    $ genie-forge whoami --profile PROD

    # Output as JSON (for scripting)
    $ genie-forge whoami --json
    """
    try:
        with with_spinner("Fetching user identity..."):
            client = get_genie_client(profile=profile, exit_on_error=False)
            # Get current user info from the Databricks SDK
            user_info = client.client.current_user.me()

        if output_json:
            import json

            data = {
                "user_name": user_info.user_name,
                "display_name": user_info.display_name,
                "user_id": user_info.id,
                "workspace_url": client.workspace_url,
                "profile": profile or "(default)",
            }
            console.print(json.dumps(data, indent=2))
        else:
            console.print()
            console.print("[bold]Current Identity[/bold]")
            console.print("═" * 50)
            console.print()
            console.print(f"  [bold]User:[/bold]        {user_info.user_name}")
            if user_info.display_name and user_info.display_name != user_info.user_name:
                console.print(f"  [bold]Display Name:[/bold] {user_info.display_name}")
            console.print(f"  [bold]User ID:[/bold]     {user_info.id}")
            console.print(f"  [bold]Workspace:[/bold]   {client.workspace_url}")
            console.print(f"  [bold]Profile:[/bold]     {profile or '(default)'}")
            console.print()

    except Exception as e:
        print_error(f"Failed to get user identity: {e}")
        raise click.Abort()
