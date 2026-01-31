"""Space management commands: plan, apply, destroy, status, drift."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional

import click
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from genie_forge.cli.common import (
    OperationCounter,
    console,
    create_progress_bar,
    get_genie_client,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from genie_forge.models import Plan, PlanAction
from genie_forge.parsers import MetadataParser
from genie_forge.state import StateManager


def _display_plan(plan: Plan) -> None:
    """Display a deployment plan with operation summary."""
    console.print()
    console.print(Panel(f"[bold]Plan for environment: {plan.environment}[/bold]"))
    console.print()

    if not plan.has_changes:
        print_success("No changes. Infrastructure is up-to-date.")
        console.print()
        return

    # Count operations
    creates = sum(1 for i in plan.items if i.action == PlanAction.CREATE)
    updates = sum(1 for i in plan.items if i.action == PlanAction.UPDATE)
    destroys = sum(1 for i in plan.items if i.action == PlanAction.DESTROY)
    unchanged = sum(1 for i in plan.items if i.action == PlanAction.NO_CHANGE)

    # Operation summary header
    console.print("[bold]OPERATION SUMMARY[/bold]")
    console.print("─" * 60)
    if creates:
        console.print(f"  [green]+ Create:[/green]    {creates} space(s)")
    if updates:
        console.print(f"  [yellow]~ Update:[/yellow]    {updates} space(s)")
    if destroys:
        console.print(f"  [red]- Destroy:[/red]   {destroys} space(s)")
    if unchanged:
        console.print(f"  [dim]= Unchanged:[/dim] {unchanged} space(s)")
    console.print("─" * 60)
    console.print()

    # Create table
    table = Table(title="Deployment Plan Details")
    table.add_column("Action", style="bold")
    table.add_column("Space ID", style="cyan")
    table.add_column("Details")

    for item in plan.items:
        if item.action == PlanAction.CREATE:
            action_text = Text("+ CREATE", style="green")
        elif item.action == PlanAction.UPDATE:
            action_text = Text("~ UPDATE", style="yellow")
        elif item.action == PlanAction.DESTROY:
            action_text = Text("- DESTROY", style="red")
        else:
            action_text = Text("= NO CHANGE", style="dim")

        details = "\n".join(item.changes) if item.changes else "-"
        table.add_row(action_text, item.logical_id, details)

    console.print(table)
    console.print()
    console.print(plan.summary())
    console.print()


def _parse_destroy_targets(
    target_pattern: str, available_spaces: list[str]
) -> tuple[list[str], list[str]]:
    """Parse destroy target pattern and return (spaces_to_destroy, excluded_spaces)."""
    # Normalize whitespace
    pattern = target_pattern.strip()

    # Extract all bracketed exclusions [...]
    bracket_pattern = r"\[([^\]]+)\]"
    bracket_matches = re.findall(bracket_pattern, pattern)

    # Get all excluded spaces from brackets
    excluded = set()
    for match in bracket_matches:
        for item in match.split(","):
            item = item.strip()
            if item:
                excluded.add(item)

    # Remove bracket sections from pattern to get includes
    includes_pattern = re.sub(bracket_pattern, "", pattern).strip()

    # Parse includes
    includes = set()
    has_wildcard = False

    if includes_pattern:
        for item in includes_pattern.split(","):
            item = item.strip()
            if item == "*":
                has_wildcard = True
            elif item:
                includes.add(item)

    # Resolve final list
    if has_wildcard:
        to_destroy = [s for s in available_spaces if s not in excluded]
    elif includes:
        to_destroy = [s for s in includes if s not in excluded and s in available_spaces]
    else:
        to_destroy = []

    return sorted(to_destroy), sorted(excluded)


@click.command()
@click.option(
    "--env",
    "-e",
    default="dev",
    help="Target environment name (e.g., dev, staging, prod).",
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default="conf/spaces",
    help="Path to config file or directory. Default: conf/spaces.",
)
@click.option(
    "--profile",
    "-p",
    help="Databricks CLI profile name from ~/.databrickscfg.",
)
@click.option(
    "--state-file",
    "-s",
    default=".genie-forge.json",
    help="Path to state file. Default: .genie-forge.json.",
)
def plan(env: str, config: str, profile: Optional[str], state_file: str) -> None:
    """Preview deployment changes without making any modifications."""
    config_path = Path(config)

    parser = MetadataParser(env=env)
    try:
        if config_path.is_dir():
            configs = parser.parse_directory(config_path, env=env)
        else:
            configs = parser.parse(config_path, env=env)
    except Exception as e:
        print_error(f"Failed to load config: {e}")
        sys.exit(1)

    if not configs:
        print_warning("No space configurations found")
        return

    client = get_genie_client(profile=profile)

    state_manager = StateManager(state_file=state_file)
    deployment_plan = state_manager.plan(configs, client, env=env)
    _display_plan(deployment_plan)


@click.command()
@click.option("--env", "-e", default="dev", help="Target environment name.")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    default="conf/spaces",
    help="Path to config file or directory.",
)
@click.option("--profile", "-p", help="Databricks CLI profile name.")
@click.option("--state-file", "-s", default=".genie-forge.json", help="Path to state file.")
@click.option("--auto-approve", is_flag=True, help="Skip confirmation prompt.")
@click.option("--dry-run", is_flag=True, help="Preview without making changes.")
@click.option("--target", "-t", help="Apply only specific space by ID.")
def apply(
    env: str,
    config: str,
    profile: Optional[str],
    state_file: str,
    auto_approve: bool,
    dry_run: bool,
    target: Optional[str],
) -> None:
    """Deploy Genie spaces to your Databricks workspace."""
    config_path = Path(config)

    parser = MetadataParser(env=env)
    try:
        if config_path.is_dir():
            configs = parser.parse_directory(config_path, env=env)
        else:
            configs = parser.parse(config_path, env=env)
    except Exception as e:
        print_error(f"Failed to load config: {e}")
        sys.exit(1)

    if target:
        configs = [c for c in configs if c.space_id == target]
        if not configs:
            print_error(f"Space '{target}' not found in configuration")
            sys.exit(1)

    if not configs:
        print_warning("No space configurations found")
        return

    client = get_genie_client(profile=profile)

    state_manager = StateManager(state_file=state_file)
    deployment_plan = state_manager.plan(configs, client, env=env)
    _display_plan(deployment_plan)

    if not deployment_plan.has_changes:
        return

    if dry_run:
        print_info("Dry run mode - no changes will be made")
        return

    if not auto_approve:
        if not click.confirm("Do you want to apply these changes?"):
            print_info("Apply cancelled")
            return

    console.print("\n[bold]Applying changes...[/bold]\n")

    # Count items with changes
    items_with_changes = [
        i for i in deployment_plan.items if i.action in (PlanAction.CREATE, PlanAction.UPDATE)
    ]
    counter = OperationCounter()

    with create_progress_bar("Applying...") as progress:
        task = progress.add_task("Applying...", total=len(items_with_changes))

        results = state_manager.apply(deployment_plan, client, dry_run=dry_run)

        # Update counter from results
        counter.created = len(results.get("created", []))
        counter.updated = len(results.get("updated", []))
        counter.failed = len(results.get("failed", []))
        counter.unchanged = len(results.get("unchanged", []))

        # Progress is completed when apply finishes
        progress.update(task, completed=len(items_with_changes))

    console.print()

    # Show details
    if results["created"]:
        for space_id in results["created"]:
            print_success(f"Created: {space_id}")
            counter.add_detail("created", space_id, "Space created successfully")

    if results["updated"]:
        for space_id in results["updated"]:
            print_success(f"Updated: {space_id}")
            counter.add_detail("updated", space_id, "Space updated successfully")

    if results["failed"]:
        for failure in results["failed"]:
            print_error(f"Failed: {failure['logical_id']} - {failure['error']}")
            counter.add_detail("failed", failure["logical_id"], error=failure["error"])

    # Print summary
    counter.print_summary("APPLY SUMMARY")


@click.command()
@click.option("--env", "-e", default="dev", help="Environment where spaces are deployed.")
@click.option("--target", "-t", required=True, help="Target pattern for spaces to destroy.")
@click.option("--profile", "-p", help="Databricks CLI profile for authentication.")
@click.option("--state-file", "-s", default=".genie-forge.json", help="Path to state file.")
@click.option("--dry-run", is_flag=True, help="Preview without deleting.")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt.")
def destroy(
    env: str,
    target: str,
    profile: Optional[str],
    state_file: str,
    dry_run: bool,
    force: bool,
) -> None:
    """Delete Genie spaces from your Databricks workspace."""
    state_manager = StateManager(state_file=state_file)

    status_result = state_manager.status(env=env)
    all_spaces = {s["logical_id"]: s for s in status_result["spaces"]}

    if not all_spaces:
        print_error(f"No spaces found in state for environment '{env}'")
        sys.exit(1)

    spaces_to_destroy, excluded_spaces = _parse_destroy_targets(target, list(all_spaces.keys()))

    not_found = [s for s in spaces_to_destroy if s not in all_spaces]
    if not_found:
        print_error(f"Spaces not found in state: {', '.join(not_found)}")
        console.print(f"\nAvailable spaces in {env}: {', '.join(all_spaces.keys())}")
        sys.exit(1)

    if not spaces_to_destroy:
        if excluded_spaces:
            print_info("All spaces excluded. Nothing to destroy.")
            console.print(f"  Excluded: {', '.join(excluded_spaces)}")
        else:
            print_error(f"No spaces match the target pattern: {target}")
        return

    console.print()
    console.print(Panel(f"[bold red]Destroy {len(spaces_to_destroy)} space(s)[/bold red]"))
    console.print()

    table = Table(title="Spaces to Destroy", title_style="bold red")
    table.add_column("Logical ID", style="cyan")
    table.add_column("Title")
    table.add_column("Databricks ID")

    for space_id in spaces_to_destroy:
        space_info = all_spaces[space_id]
        table.add_row(space_id, space_info["title"], space_info["databricks_space_id"] or "-")

    console.print(table)

    if excluded_spaces:
        actual_excluded = [s for s in excluded_spaces if s in all_spaces]
        if actual_excluded:
            console.print()
            console.print(
                f"[yellow]Excluded (will NOT be destroyed):[/yellow] {', '.join(actual_excluded)}"
            )

    console.print()

    if dry_run:
        print_info(f"Dry run mode - {len(spaces_to_destroy)} space(s) would be destroyed")
        return

    client = get_genie_client(profile=profile)

    if not force:
        if len(spaces_to_destroy) == 1:
            prompt = f"Are you sure you want to destroy '{spaces_to_destroy[0]}'?"
        else:
            prompt = f"Are you sure you want to destroy {len(spaces_to_destroy)} spaces?"

        if not click.confirm(prompt):
            print_info("Destroy cancelled")
            return

    console.print("\n[bold]Destroying spaces...[/bold]\n")

    counter = OperationCounter()

    with create_progress_bar("Destroying...") as progress:
        task = progress.add_task("Destroying...", total=len(spaces_to_destroy))

        for space_id in spaces_to_destroy:
            result = state_manager.destroy(space_id, client, env=env, dry_run=False)

            if result["success"]:
                print_success(f"Destroyed: {space_id}")
                counter.deleted += 1
                counter.add_detail("deleted", space_id, "Space destroyed successfully")
            else:
                error = result.get("error", "Unknown error")
                print_error(f"Failed: {space_id} - {error}")
                counter.failed += 1
                counter.add_detail("failed", space_id, error=error)

            progress.update(task, advance=1)

    # Print summary
    counter.print_summary("DESTROY SUMMARY")

    if counter.failed > 0:
        sys.exit(1)


@click.command()
@click.option("--env", "-e", help="Filter by environment.")
@click.option("--state-file", "-s", default=".genie-forge.json", help="Path to state file.")
def status(env: Optional[str], state_file: str) -> None:
    """Display deployment status from the local state file."""
    state_manager = StateManager(state_file=state_file)

    if env:
        envs = [env]
    else:
        envs = list(state_manager.state.environments.keys())

    if not envs:
        print_info("No deployments found in state file")
        print_info("Run 'genie-forge apply' to deploy spaces")
        return

    for env_name in envs:
        env_status = state_manager.status(env=env_name)

        console.print()
        console.print(Panel(f"[bold]Environment: {env_name}[/bold]"))
        console.print(f"  Workspace: {env_status.get('workspace_url', 'N/A')}")
        console.print(f"  Total Spaces: {env_status['total']}")
        if env_status.get("last_applied"):
            console.print(f"  Last Applied: {env_status['last_applied']}")
        console.print()

        if env_status["spaces"]:
            table = Table()
            table.add_column("Logical ID", style="cyan")
            table.add_column("Title")
            table.add_column("Status")
            table.add_column("Space ID")
            table.add_column("Last Applied")

            for space in env_status["spaces"]:
                status_style = {
                    "APPLIED": "green",
                    "PENDING": "yellow",
                    "MODIFIED": "yellow",
                    "DRIFT": "red",
                    "DESTROYED": "dim",
                }.get(space["status"], "")

                table.add_row(
                    space["logical_id"],
                    space["title"],
                    Text(space["status"], style=status_style),
                    space["databricks_space_id"] or "-",
                    space["last_applied"][:10] if space["last_applied"] else "-",
                )

            console.print(table)
        else:
            print_info("No spaces deployed")


@click.command()
@click.option("--env", "-e", required=True, help="Environment to check for drift.")
@click.option("--profile", "-p", help="Databricks CLI profile name.")
@click.option("--state-file", "-s", default=".genie-forge.json", help="Path to state file.")
def drift(env: str, profile: Optional[str], state_file: str) -> None:
    """Detect drift between local state and Databricks workspace."""
    import os

    if not profile:
        profile = os.environ.get("GENIE_PROFILE")
        if not profile:
            print_error("No profile specified. Use --profile or set GENIE_PROFILE")
            sys.exit(1)

    client = get_genie_client(profile=profile)

    state_manager = StateManager(state_file=state_file)

    console.print()
    console.print(Panel(f"[bold]Drift Detection: {env}[/bold]"))
    console.print(f"  Workspace: {client.workspace_url}")
    console.print(f"  State File: {state_file}")
    console.print()

    # Get state to count spaces for progress bar
    env_status = state_manager.status(env=env)
    space_count = len(env_status.get("spaces", []))

    with create_progress_bar("Checking drift...") as progress:
        task = progress.add_task("Checking...", total=space_count or 1)
        results = state_manager.detect_drift(client=client, env=env)
        progress.update(task, completed=space_count or 1)

    if "error" in results:
        print_error(results["error"])
        sys.exit(1)

    total = results["total_checked"]
    drifted_count = len(results["drifted"])
    deleted_count = len(results["deleted"])
    synced_count = len(results["synced"])

    console.print(f"  Checked: {total} space(s)")
    console.print()

    if results["drifted"]:
        console.print("[yellow bold]⚠ DRIFTED SPACES[/yellow bold]")
        table = Table()
        table.add_column("Logical ID", style="cyan")
        table.add_column("Title")
        table.add_column("Changes", style="yellow")

        for space in results["drifted"]:
            changes = "\n".join(space["changes"]) if space["changes"] else "Unknown"
            table.add_row(space["logical_id"], space["title"], changes)

        console.print(table)
        console.print()

    if results["deleted"]:
        console.print("[red bold]✗ DELETED FROM WORKSPACE[/red bold]")
        table = Table()
        table.add_column("Logical ID", style="cyan")
        table.add_column("Title")
        table.add_column("Reason", style="red")

        for space in results["deleted"]:
            table.add_row(space["logical_id"], space["title"], space.get("reason", "Not found"))

        console.print(table)
        console.print()

    if results["synced"] and not results["has_drift"]:
        console.print("[green bold]✓ ALL SPACES IN SYNC[/green bold]")
        console.print(f"  {synced_count} space(s) match local state")
        console.print()
    elif results["synced"]:
        console.print(f"[dim]{synced_count} space(s) in sync[/dim]")
        console.print()

    if results["has_drift"]:
        console.print(
            Panel(
                f"[yellow]Drift detected![/yellow]\n"
                f"Drifted: {drifted_count}, Deleted: {deleted_count}, Synced: {synced_count}\n\n"
                f"To resolve:\n"
                f"• Apply local config: genie-forge apply --env {env}\n"
                f"• Or update YAML to match remote state",
                title="Summary",
            )
        )
        sys.exit(1)
    else:
        console.print(
            Panel(
                f"[green]No drift detected[/green]\nAll {synced_count} space(s) match local state.",
                title="Summary",
            )
        )
