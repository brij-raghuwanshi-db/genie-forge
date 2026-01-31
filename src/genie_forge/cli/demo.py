"""Demo table setup and cleanup commands."""

from __future__ import annotations

import sys
from typing import Any, Optional

import click
from rich.panel import Panel
from rich.table import Table

from genie_forge.cli.common import (
    console,
    get_genie_client,
    print_error,
    print_info,
    print_success,
    print_warning,
    with_spinner,
)


@click.command("setup-demo")
@click.option("--catalog", "-c", required=True, help="Unity Catalog name.")
@click.option("--schema", "-s", required=True, help="Schema name within the catalog.")
@click.option("--profile", "-p", help="Databricks CLI profile for authentication.")
@click.option("--warehouse-id", "-w", required=True, help="SQL warehouse ID.")
@click.option("--dry-run", is_flag=True, help="Show what would be created without executing.")
def setup_demo(
    catalog: str,
    schema: str,
    profile: Optional[str],
    warehouse_id: str,
    dry_run: bool,
) -> None:
    """Create demo tables for Genie-Forge examples.

    Sets up sample tables in your Unity Catalog for use with the demo
    configurations (employee_analytics.yaml, sales_analytics.yaml).
    """
    from genie_forge.demo_tables import DEMO_TABLES_INFO, create_demo_tables

    console.print()
    console.print(Panel("[bold]Setup Demo Tables[/bold]"))
    console.print()
    console.print(f"  Catalog:   {catalog}")
    console.print(f"  Schema:    {schema}")
    console.print(f"  Warehouse: {warehouse_id}")
    console.print(f"  Profile:   {profile or '(default)'}")
    console.print()

    table = Table(title="Tables to Create")
    table.add_column("Table", style="cyan")
    table.add_column("Rows", justify="right")
    table.add_column("Description")

    for tbl_name, info in DEMO_TABLES_INFO.items():
        table.add_row(f"{catalog}.{schema}.{tbl_name}", str(info["rows"]), info["description"])

    console.print(table)
    console.print()

    if dry_run:
        print_info("Dry run mode - no tables will be created")
        console.print()
        console.print("To create the tables, run without --dry-run")
        return

    client = get_genie_client(profile=profile)

    console.print("Creating tables...")
    console.print()

    try:
        results = create_demo_tables(
            client=client,
            catalog=catalog,
            schema=schema,
            warehouse_id=warehouse_id,
        )

        for tbl_name, status in results["tables"].items():
            if status["success"]:
                print_success(f"{tbl_name}: {status['rows']} rows")
            else:
                print_error(f"{tbl_name}: {status.get('error', 'Failed')}")

        console.print()

        if results["success"]:
            print_success(
                f"Created {results['tables_created']} tables with {results['total_rows']} rows"
            )
            console.print()
            console.print("Next steps:")
            console.print("  1. Update conf/environments/dev.yaml:")
            console.print(f"       catalog: {catalog}")
            console.print(f"       schema: {schema}")
            console.print(f"       warehouse_id: {warehouse_id}")
            console.print("  2. genie-forge validate --config conf/spaces/")
            console.print(f"  3. genie-forge plan --env dev --profile {profile or 'YOUR_PROFILE'}")
        else:
            print_error("Some tables failed to create")
            sys.exit(1)

    except Exception as e:
        print_error(f"Failed to create tables: {e}")
        sys.exit(1)


@click.command("cleanup-demo")
@click.option("--catalog", "-c", required=True, help="Unity Catalog name.")
@click.option("--schema", "-s", required=True, help="Schema name within the catalog.")
@click.option("--profile", "-p", help="Databricks CLI profile for authentication.")
@click.option("--warehouse-id", "-w", help="SQL warehouse ID. Required with --execute.")
@click.option("--list-only", "-l", is_flag=True, help="Only list objects without deleting.")
@click.option("--execute", is_flag=True, help="Actually delete objects (required to delete).")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt.")
def cleanup_demo(
    catalog: str,
    schema: str,
    profile: Optional[str],
    warehouse_id: Optional[str],
    list_only: bool,
    execute: bool,
    force: bool,
) -> None:
    """Remove demo tables created by setup-demo.

    By default, runs in DRY-RUN mode. Use --execute to actually delete.
    """
    from genie_forge.demo_tables import DEMO_FUNCTIONS_INFO, DEMO_TABLES_INFO, cleanup_demo_tables

    console.print()
    console.print(Panel("[bold]Cleanup Demo Objects[/bold]"))
    console.print()
    console.print(f"  Catalog: {catalog}")
    console.print(f"  Schema:  {schema}")
    console.print()

    tables: list[dict[str, Any]] = [
        {
            "name": f"{catalog}.{schema}.{tbl_name}",
            "type": "TABLE",
            "description": info["description"],
            "rows": info["rows"],
        }
        for tbl_name, info in DEMO_TABLES_INFO.items()
    ]

    functions: list[dict[str, Any]] = [
        {
            "name": f"{catalog}.{schema}.{func_name}",
            "type": "FUNCTION",
            "description": info["description"],
        }
        for func_name, info in DEMO_FUNCTIONS_INFO.items()
    ]

    table_display = Table(title="Demo Tables")
    table_display.add_column("Object Name", style="cyan")
    table_display.add_column("Type")
    table_display.add_column("Rows", justify="right")
    table_display.add_column("Description")

    for obj in tables:
        table_display.add_row(obj["name"], obj["type"], str(obj["rows"]), obj["description"])

    console.print(table_display)
    console.print()

    func_display = Table(title="Demo Functions")
    func_display.add_column("Object Name", style="cyan")
    func_display.add_column("Type")
    func_display.add_column("Description")

    for obj in functions:
        func_display.add_row(obj["name"], obj["type"], obj["description"])

    console.print(func_display)
    console.print()

    if list_only:
        console.print(Panel("[bold]SQL for Manual Cleanup[/bold]"))
        console.print()
        console.print("[yellow]-- Run these statements to delete demo objects:[/yellow]")
        console.print()

        drop_order = ["sales", "employees", "customers", "products", "departments", "locations"]
        for tbl_name in drop_order:
            console.print(f"DROP TABLE IF EXISTS {catalog}.{schema}.{tbl_name};")

        console.print()
        for func_name in DEMO_FUNCTIONS_INFO.keys():
            console.print(f"DROP FUNCTION IF EXISTS {catalog}.{schema}.{func_name};")

        console.print()
        print_info("Use these SQL statements to manually clean up the demo objects.")
        return

    total_objects = len(tables) + len(functions)

    if not execute:
        print_info(f"DRY-RUN MODE: {total_objects} object(s) would be deleted")
        console.print()
        console.print("[yellow]No objects were deleted.[/yellow]")
        console.print()
        console.print("To actually delete, run with [bold]--execute[/bold]:")
        console.print(
            f"  genie-forge cleanup-demo -c {catalog} -s {schema} -w <warehouse-id> --execute"
        )
        return

    if not warehouse_id:
        print_error("--warehouse-id is required when using --execute")
        console.print()
        console.print("Example:")
        console.print(
            f"  genie-forge cleanup-demo -c {catalog} -s {schema} -w <warehouse-id> --execute"
        )
        sys.exit(1)

    client = get_genie_client(profile=profile)

    if not force:
        console.print(
            f"[bold red]⚠ WARNING:[/bold red] This will [bold]PERMANENTLY DELETE[/bold] {total_objects} objects:"
        )
        console.print()
        for obj in tables:
            console.print(f"  • {obj['name']}")
        for obj in functions:
            console.print(f"  • {obj['name']}")
        console.print()
        console.print("[red]The underlying data in these tables will be LOST.[/red]")
        console.print()

        if not click.confirm("Are you sure you want to delete these demo objects?"):
            print_info("Cleanup cancelled")
            return

    console.print()
    console.print("[bold]Checking for existing demo objects...[/bold]")
    console.print()

    try:
        results = cleanup_demo_tables(
            client=client,
            catalog=catalog,
            schema=schema,
            warehouse_id=warehouse_id,
        )

        if results.get("already_clean"):
            console.print()
            console.print(
                Panel(
                    "[green]✓ Nothing to clean up![/green]\n\n"
                    "The demo objects have already been removed from this location.",
                    title="Already Clean",
                    border_style="green",
                )
            )
            console.print()
            console.print(f"  Catalog: {catalog}")
            console.print(f"  Schema:  {schema}")
            return

        for obj_name, status in results["objects"].items():
            if status.get("skipped"):
                print_info(f"Skipped (not found): {obj_name}")
            elif status["success"]:
                print_success(f"Deleted: {obj_name}")
            else:
                print_warning(f"Failed: {obj_name} - {status.get('error', 'Unknown error')}")

        console.print()

        if results["deleted_count"] > 0:
            print_success(f"Cleanup complete: {results['deleted_count']} object(s) deleted")
            if results["skipped_count"] > 0:
                print_info(f"{results['skipped_count']} object(s) were already removed")
        else:
            print_info("No objects were deleted (all were already removed)")

    except Exception as e:
        print_error(f"Failed to cleanup: {e}")
        sys.exit(1)


@click.command("demo-status")
@click.option("--catalog", "-c", required=True, help="Unity Catalog name.")
@click.option("--schema", "-s", required=True, help="Schema name within the catalog.")
@click.option("--profile", "-p", help="Databricks CLI profile for authentication.")
@click.option("--warehouse-id", "-w", required=True, help="SQL warehouse ID.")
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output as JSON.",
)
def demo_status(
    catalog: str,
    schema: str,
    profile: Optional[str],
    warehouse_id: str,
    output_json: bool,
) -> None:
    """Check if demo tables and functions exist.

    Verifies whether the demo objects (tables and functions) created by
    setup-demo exist in the specified catalog and schema. Useful for
    checking if you need to run setup-demo before using the examples.

    \b
    EXAMPLES:
    ─────────
    # Check demo status
    $ genie-forge demo-status -c my_catalog -s my_schema -w warehouse123

    # Output as JSON (for scripting)
    $ genie-forge demo-status -c my_catalog -s my_schema -w warehouse123 --json
    """
    from genie_forge.demo_tables import (
        DEMO_FUNCTIONS_INFO,
        DEMO_TABLES_INFO,
        check_demo_objects_exist,
    )

    client = get_genie_client(profile=profile)

    # Check which objects exist
    with with_spinner("Checking demo objects..."):
        results = check_demo_objects_exist(
            client=client,
            catalog=catalog,
            schema=schema,
            warehouse_id=warehouse_id,
        )

    if output_json:
        import json

        output = {
            "catalog": catalog,
            "schema": schema,
            "tables": {
                "existing": results["existing_tables"],
                "missing": results["missing_tables"],
                "total": len(DEMO_TABLES_INFO),
            },
            "functions": {
                "existing": results["existing_functions"],
                "missing": results["missing_functions"],
                "total": len(DEMO_FUNCTIONS_INFO),
            },
            "total_existing": results["total_existing"],
            "total_missing": results["total_missing"],
            "demo_setup_complete": results["total_missing"] == 0,
        }
        console.print(json.dumps(output, indent=2))
        return

    # Display results
    console.print()
    console.print(Panel("[bold]Demo Objects Status[/bold]"))
    console.print()
    console.print(f"  Catalog: {catalog}")
    console.print(f"  Schema:  {schema}")
    console.print()

    # Tables section
    console.print("[bold]TABLES[/bold]")
    console.print("─" * 50)

    for tbl_name, info in DEMO_TABLES_INFO.items():
        full_name = f"{catalog}.{schema}.{tbl_name}"
        if full_name in results["existing_tables"]:
            console.print(f"  [green]✓[/green] {tbl_name}")
        else:
            console.print(f"  [red]✗[/red] {tbl_name} [dim](NOT FOUND)[/dim]")

    console.print()

    # Functions section
    console.print("[bold]FUNCTIONS[/bold]")
    console.print("─" * 50)

    for func_name, info in DEMO_FUNCTIONS_INFO.items():  # type: ignore[assignment]
        full_name = f"{catalog}.{schema}.{func_name}"
        if full_name in results["existing_functions"]:
            console.print(f"  [green]✓[/green] {func_name}")
        else:
            console.print(f"  [red]✗[/red] {func_name} [dim](NOT FOUND)[/dim]")

    console.print()
    console.print("─" * 50)

    # Summary
    total_objects = len(DEMO_TABLES_INFO) + len(DEMO_FUNCTIONS_INFO)
    existing_count = results["total_existing"]
    missing_count = results["total_missing"]

    console.print(
        f"[bold]SUMMARY:[/bold] {existing_count}/{total_objects} objects exist | "
        f"{len(results['existing_tables'])}/{len(DEMO_TABLES_INFO)} tables | "
        f"{len(results['existing_functions'])}/{len(DEMO_FUNCTIONS_INFO)} functions"
    )
    console.print()

    if missing_count == 0:
        print_success("Demo is fully set up!")
    elif existing_count == 0:
        print_warning("Demo not set up")
        console.print()
        console.print("Run 'genie-forge setup-demo' to create demo objects:")
        console.print(f"  genie-forge setup-demo -c {catalog} -s {schema} -w {warehouse_id}")
    else:
        print_warning(f"Demo is partially set up ({missing_count} objects missing)")
        console.print()
        console.print("You may want to run 'genie-forge setup-demo' to complete setup:")
        console.print(f"  genie-forge setup-demo -c {catalog} -s {schema} -w {warehouse_id}")
