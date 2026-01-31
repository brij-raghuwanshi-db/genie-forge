"""Space operations commands (space-* group).

This module provides commands for listing, viewing, finding, and managing
Genie spaces in the Databricks workspace.

Commands:
- space-list: List all spaces in workspace (with pagination)
- space-get: Display full details of a space
- space-find: Search spaces by name pattern (alias for find)
- space-create: Create a new space from CLI flags or config file
- space-export: Export spaces to YAML files
- space-clone: Clone a space locally or in workspace
- space-delete: Delete spaces (alias for destroy)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

import click
from rich.table import Table

from genie_forge.cli.common import (
    apply_key_value_overrides,
    console,
    create_progress_bar,
    fetch_all_spaces_paginated,
    get_genie_client,
    load_config_file,
    parse_comma_separated,
    parse_serialized_space,
    print_error,
    print_section_header,
    print_success,
    print_warning,
    sanitize_filename,
    save_config_file,
    truncate_string,
    with_spinner,
)

# =============================================================================
# space-list Command
# =============================================================================


@click.command("space-list")
@click.option(
    "--profile",
    "-p",
    help="Databricks CLI profile to use",
)
@click.option(
    "--limit",
    "-l",
    type=int,
    default=100,
    help="Maximum spaces to display (0 = no limit)",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="Output format",
)
def space_list(profile: Optional[str], limit: int, output_format: str) -> None:
    """List all Genie spaces in the workspace.

    Fetches all spaces from the Databricks workspace with pagination
    and displays them in the specified format.

    \b
    EXAMPLES:
    ─────────
    # List all spaces (table format, first 100)
    $ genie-forge space-list --profile PROD

    # List all spaces with no limit
    $ genie-forge space-list --profile PROD --limit 0

    # Export to JSON for scripting
    $ genie-forge space-list --profile PROD --format json > spaces.json

    # Export to CSV for Excel/reporting
    $ genie-forge space-list --profile PROD --format csv > spaces.csv
    """
    client = get_genie_client(profile=profile)

    # Fetch spaces with pagination progress
    all_spaces = fetch_all_spaces_paginated(client, show_progress=True)

    console.print(f"\nFound [bold]{len(all_spaces)}[/bold] spaces in workspace\n")

    if not all_spaces:
        print_warning("No spaces found in workspace")
        return

    # Apply limit
    display_spaces = all_spaces if limit == 0 else all_spaces[:limit]

    # Output based on format
    if output_format == "json":
        console.print(json.dumps(display_spaces, indent=2))
    elif output_format == "csv":
        # CSV header
        console.print("id,title,warehouse_id,created_at,creator")
        for space in display_spaces:
            space_id = space.get("id", "")
            title = space.get("title", "").replace(",", ";")  # Escape commas
            warehouse_id = space.get("warehouse_id", "")
            created_at = space.get("create_time", "")
            creator = space.get("creator", "")
            console.print(f"{space_id},{title},{warehouse_id},{created_at},{creator}")
    else:
        # Table format
        table = Table(title=f"Genie Spaces ({len(display_spaces)} shown)")
        table.add_column("Title", style="cyan", no_wrap=True, max_width=40)
        table.add_column("Space ID", style="dim", max_width=30)
        table.add_column("Warehouse ID", style="dim", max_width=20)
        table.add_column("Creator", style="dim", max_width=25)

        for space in display_spaces:
            table.add_row(
                space.get("title", "Untitled"),
                truncate_string(space.get("id", ""), 24),
                truncate_string(space.get("warehouse_id", ""), 16),
                space.get("creator", ""),
            )

        console.print(table)

        if limit > 0 and len(all_spaces) > limit:
            console.print(
                f"\n[dim]Showing {limit} of {len(all_spaces)} spaces. "
                f"Use --limit 0 to show all.[/dim]"
            )


# Alias: list-spaces -> space-list
@click.command("list-spaces")
@click.pass_context
def list_spaces(ctx: click.Context, **kwargs: Any) -> None:
    """List all Genie spaces in the workspace. (Alias for space-list)"""
    ctx.invoke(space_list, **kwargs)


# Copy options from space_list to list_spaces
list_spaces.params = space_list.params.copy()


# =============================================================================
# space-get Command
# =============================================================================


@click.command("space-get")
@click.argument("space_id", required=False)
@click.option(
    "--name",
    "-n",
    help="Find space by name (exact or pattern)",
)
@click.option(
    "--profile",
    "-p",
    help="Databricks CLI profile to use",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format",
)
@click.option(
    "--raw",
    is_flag=True,
    help="Include raw serialized_space in output",
)
def space_get(
    space_id: Optional[str],
    name: Optional[str],
    profile: Optional[str],
    output_format: str,
    raw: bool,
) -> None:
    """Display full details of a Genie space.

    Fetches the complete space configuration from Databricks and displays
    it in your chosen format. Useful for inspection, debugging, and export.

    \b
    EXAMPLES:
    ─────────
    # Get by space ID
    $ genie-forge space-get 01abc123def456 --profile PROD

    # Get by name
    $ genie-forge space-get --name "Sales Analytics" --profile PROD

    # Export as YAML
    $ genie-forge space-get 01abc123 --format yaml > space.yaml

    # Export as JSON (including raw serialized_space)
    $ genie-forge space-get 01abc123 --format json --raw
    """
    import fnmatch

    if not space_id and not name:
        raise click.UsageError("Either provide SPACE_ID or use --name")

    client = get_genie_client(profile=profile)

    # Find space by name if needed
    if name:
        with with_spinner(f"Searching for '{name}'..."):
            spaces = client.list_spaces()
            # Try exact match first
            matching = [s for s in spaces if s.get("title") == name]
            # If no exact match, try pattern
            if not matching:
                matching = [
                    s for s in spaces if fnmatch.fnmatch(s.get("title", "").lower(), name.lower())
                ]

        if len(matching) == 0:
            print_error(f"No space found matching '{name}'")
            sys.exit(1)
        elif len(matching) > 1:
            print_error(f"Multiple spaces match '{name}':")
            for m in matching[:10]:
                console.print(f"  • {m.get('title')} ({truncate_string(m.get('id', ''), 16)})")
            console.print("\nUse the exact space ID instead.")
            sys.exit(1)

        space_id = matching[0].get("id")

    if not space_id:
        print_error("Could not determine space ID")
        sys.exit(1)

    # Fetch full space details
    with with_spinner("Fetching space details..."):
        space = client.get_space(space_id, include_serialized=raw)

    # Parse serialized_space if present
    serialized = parse_serialized_space(space)

    # Output based on format
    if output_format == "json":
        output_data = dict(space)
        if serialized and raw:
            output_data["parsed_serialized_space"] = serialized
        console.print(json.dumps(output_data, indent=2, default=str))

    elif output_format == "yaml":
        import yaml

        output_data = {
            "space_id": space.get("id"),
            "title": space.get("title"),
            "warehouse_id": space.get("warehouse_id"),
            "parent_path": space.get("parent_path"),
            "creator": space.get("creator"),
            "create_time": space.get("create_time"),
        }
        if serialized:
            # Extract useful parts from serialized space
            if "data_sources" in serialized:
                output_data["data_sources"] = serialized["data_sources"]
            if "instructions" in serialized:
                output_data["instructions"] = serialized["instructions"]
            if "config" in serialized and serialized["config"].get("sample_questions"):
                output_data["sample_questions"] = serialized["config"]["sample_questions"]
        console.print(yaml.dump(output_data, default_flow_style=False, sort_keys=False))

    else:
        # Table format
        print_section_header(f"Space: {space.get('title', 'Untitled')}")

        console.print("\n[bold]BASIC INFO[/bold]")
        console.print(f"  Space ID:     {space.get('id')}")
        console.print(f"  Title:        {space.get('title')}")
        console.print(f"  Warehouse:    {space.get('warehouse_id')}")
        if space.get("parent_path"):
            console.print(f"  Parent Path:  {space.get('parent_path')}")
        console.print(f"  Creator:      {space.get('creator')}")
        console.print(f"  Created:      {space.get('create_time')}")

        if serialized:
            # Data sources
            data_sources = serialized.get("data_sources", {})
            tables = data_sources.get("tables", [])
            if tables:
                console.print(f"\n[bold]DATA SOURCES ({len(tables)} tables)[/bold]")
                console.print("─" * 50)
                for table in tables[:10]:
                    identifier = table.get("identifier", "unknown")
                    desc = table.get("description", "")
                    if isinstance(desc, list):
                        desc = desc[0] if desc else ""
                    console.print(f"  • {identifier}")
                    if desc:
                        console.print(f"      [dim]{desc}[/dim]")
                if len(tables) > 10:
                    console.print(f"  ... and {len(tables) - 10} more")

            # Instructions
            instructions = serialized.get("instructions", {})
            text_instructions = instructions.get("text_instructions", [])
            sql_functions = instructions.get("sql_functions", [])
            sql_examples = instructions.get("example_question_sqls", [])

            if text_instructions or sql_functions or sql_examples:
                console.print("\n[bold]INSTRUCTIONS[/bold]")
                console.print("─" * 50)
                if text_instructions:
                    console.print(f"  Text Instructions: {len(text_instructions)}")
                    for ti in text_instructions[:3]:
                        text = ti.get("text", "") if isinstance(ti, dict) else str(ti)
                        console.print(
                            f"    • {text[:60]}..." if len(text) > 60 else f"    • {text}"
                        )
                if sql_functions:
                    console.print(f"  SQL Functions: {len(sql_functions)}")
                if sql_examples:
                    console.print(f"  SQL Examples: {len(sql_examples)}")

            # Sample questions
            config = serialized.get("config", {})
            sample_questions = config.get("sample_questions", [])
            if sample_questions:
                console.print(f"\n[bold]SAMPLE QUESTIONS ({len(sample_questions)})[/bold]")
                console.print("─" * 50)
                for q in sample_questions[:5]:
                    console.print(f"  • {q}")
                if len(sample_questions) > 5:
                    console.print(f"  ... and {len(sample_questions) - 5} more")

        console.print()


# Alias: show -> space-get
@click.command("show")
@click.pass_context
def show(ctx: click.Context, **kwargs: Any) -> None:
    """Display full details of a Genie space. (Alias for space-get)"""
    ctx.invoke(space_get, **kwargs)


# Copy options from space_get to show
show.params = space_get.params.copy()


# =============================================================================
# space-find Command (Alias for find)
# =============================================================================


@click.command("space-find")
@click.option(
    "--name",
    "-n",
    required=True,
    help="Name pattern to search for (glob-style: 'Sales*')",
)
@click.option(
    "--profile",
    "-p",
    help="Databricks CLI profile to use",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="Output format",
)
@click.option(
    "--workspace",
    "-w",
    is_flag=True,
    help="Search in workspace (implied when using --profile)",
)
def space_find(
    name: str,
    profile: Optional[str],
    output_format: str,
    workspace: bool,
) -> None:
    """Search for spaces by name pattern. (Alias for find)

    Uses glob-style pattern matching to find spaces. The search
    is case-insensitive by default.

    \b
    EXAMPLES:
    ─────────
    # Find all spaces starting with "Sales"
    $ genie-forge space-find --name "Sales*" --profile PROD

    # Find all spaces containing "analytics"
    $ genie-forge space-find --name "*analytics*" --profile PROD

    # Output as JSON
    $ genie-forge space-find --name "Prod*" --format json --profile PROD
    """
    # Import the existing find command and invoke it
    from genie_forge.cli.find import find

    # The existing find command handles the logic
    ctx = click.get_current_context()
    ctx.invoke(find, name=name, profile=profile, workspace=workspace or bool(profile))


# =============================================================================
# space-create Command
# =============================================================================


@click.command("space-create")
@click.argument("title", required=False)
@click.option(
    "--from-file",
    "from_file",
    type=click.Path(exists=True),
    help="Load configuration from YAML/JSON file",
)
@click.option(
    "--warehouse-id",
    "-w",
    help="SQL warehouse ID (required if not using --from-file)",
)
@click.option(
    "--tables",
    "-t",
    help="Comma-separated table identifiers (catalog.schema.table)",
)
@click.option(
    "--description",
    "-d",
    help="Space description",
)
@click.option(
    "--instructions",
    "-i",
    multiple=True,
    help="Text instructions (can repeat for multiple)",
)
@click.option(
    "--functions",
    help="Comma-separated SQL function identifiers",
)
@click.option(
    "--questions",
    "-q",
    multiple=True,
    help="Sample questions (can repeat for multiple)",
)
@click.option(
    "--parent-path",
    help="Workspace path for the space",
)
@click.option(
    "--set",
    "overrides",
    multiple=True,
    help="Override config values (key=value, can repeat)",
)
@click.option(
    "--profile",
    "-p",
    help="Databricks CLI profile to use",
)
@click.option(
    "--save-config",
    type=click.Path(),
    help="Save the final config to YAML file",
)
@click.option(
    "--env",
    "-e",
    help="Environment for state tracking (adds to state file)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would be created without creating",
)
def space_create(
    title: Optional[str],
    from_file: Optional[str],
    warehouse_id: Optional[str],
    tables: Optional[str],
    description: Optional[str],
    instructions: tuple,
    functions: Optional[str],
    questions: tuple,
    parent_path: Optional[str],
    overrides: tuple,
    profile: Optional[str],
    save_config: Optional[str],
    env: Optional[str],
    dry_run: bool,
) -> None:
    """Create a new Genie space.

    Supports three methods of creation:
    1. CLI FLAGS: Provide title, warehouse, tables directly
    2. FROM FILE: Load config from YAML/JSON file
    3. HYBRID: Load from file + override specific values

    \b
    EXAMPLES:
    ─────────
    # Method 1: CLI flags
    $ genie-forge space-create "Sales Analytics" \\
        --warehouse-id abc123 \\
        --tables "catalog.schema.sales,catalog.schema.customers" \\
        --questions "What were total sales?" \\
        --profile PROD

    # Method 2: From file
    $ genie-forge space-create --from-file conf/spaces/sales.yaml --profile PROD

    # Method 3: Hybrid (file + overrides)
    $ genie-forge space-create --from-file conf/spaces/sales.yaml \\
        --set warehouse_id=prod_warehouse \\
        --set title="Production Sales" \\
        --profile PROD

    # Dry run (preview without creating)
    $ genie-forge space-create "Test Space" --warehouse-id abc123 \\
        --tables "catalog.schema.test" --dry-run

    # Create and save config for future use
    $ genie-forge space-create "My Space" --warehouse-id abc123 \\
        --tables "catalog.schema.table" \\
        --save-config conf/spaces/my_space.yaml --profile PROD
    """
    import yaml

    # Validate input - either from_file or (title + warehouse_id + tables)
    if not from_file and not title:
        raise click.UsageError("Either provide TITLE or use --from-file")
    if not from_file and not (warehouse_id and tables):
        raise click.UsageError(
            "--warehouse-id and --tables are required when not using --from-file"
        )

    config: dict = {}

    # Load from file if specified
    if from_file:
        config = load_config_file(from_file)

        # Apply --set overrides
        if overrides:
            config = apply_key_value_overrides(config, list(overrides))

    # CLI flags override/supplement file values
    if title:
        config["title"] = title
    if warehouse_id:
        config["warehouse_id"] = warehouse_id
    if description:
        config["description"] = description
    if parent_path:
        config["parent_path"] = parent_path

    # Handle tables
    if tables:
        table_list = parse_comma_separated(tables)
        config["data_sources"] = config.get("data_sources", {})
        config["data_sources"]["tables"] = [{"identifier": t} for t in table_list]

    # Handle instructions
    if instructions:
        config["instructions"] = config.get("instructions", {})
        # Combine multiple instructions into one (API only allows 1 text_instruction)
        combined_text = "\n\n".join(instructions)
        config["instructions"]["text_instructions"] = [{"text": combined_text}]

    # Handle functions
    if functions:
        function_list = parse_comma_separated(functions)
        config["instructions"] = config.get("instructions", {})
        config["instructions"]["sql_functions"] = [{"identifier": f} for f in function_list]

    # Handle sample questions
    if questions:
        config["sample_questions"] = [{"question": q} for q in questions]

    # Validate required fields
    if not config.get("title"):
        raise click.UsageError(
            "Title is required (provide TITLE argument or include in config file)"
        )
    if not config.get("warehouse_id"):
        raise click.UsageError(
            "warehouse_id is required (use --warehouse-id or include in config file)"
        )
    if not config.get("data_sources", {}).get("tables"):
        raise click.UsageError(
            "At least one table is required (use --tables or include in config file)"
        )

    # Display what will be created
    console.print()
    print_section_header("Space Configuration")

    console.print(f"\n  [bold]Title:[/bold]        {config.get('title')}")
    console.print(f"  [bold]Warehouse:[/bold]    {config.get('warehouse_id')}")
    description = config.get("description")
    if description:
        console.print(f"  [bold]Description:[/bold]  {str(description)[:50]}...")
    if config.get("parent_path"):
        console.print(f"  [bold]Parent Path:[/bold] {config.get('parent_path')}")

    # Tables
    tables_config = config.get("data_sources", {}).get("tables", [])
    console.print(f"\n  [bold]Tables ({len(tables_config)}):[/bold]")
    for t in tables_config[:5]:
        identifier = t.get("identifier") if isinstance(t, dict) else t
        console.print(f"    • {identifier}")
    if len(tables_config) > 5:
        console.print(f"    ... and {len(tables_config) - 5} more")

    # Instructions summary
    instr = config.get("instructions", {})
    if instr:
        text_instr = instr.get("text_instructions", [])
        sql_funcs = instr.get("sql_functions", [])
        if text_instr:
            console.print(f"\n  [bold]Text Instructions:[/bold] {len(text_instr)}")
        if sql_funcs:
            console.print(f"  [bold]SQL Functions:[/bold] {len(sql_funcs)}")

    # Sample questions
    sample_q = config.get("sample_questions", [])
    if sample_q:
        console.print(f"\n  [bold]Sample Questions:[/bold] {len(sample_q)}")

    console.print()

    # Dry run - just show config
    if dry_run:
        console.print("[bold]Dry run - configuration preview:[/bold]")
        console.print("─" * 60)
        console.print(yaml.dump(config, default_flow_style=False, sort_keys=False))
        console.print("─" * 60)
        console.print("\n[dim]No changes made (dry run).[/dim]")
        return

    # Save config if requested (before creating to ensure we have it)
    if save_config:
        save_config_file(config, save_config, file_format="yaml")
        print_success(f"Config saved: {save_config}")

    # Create the space
    client = get_genie_client(profile=profile)

    # Use the proper serializer to build serialized_space
    from genie_forge.parsers import MetadataParser
    from genie_forge.serializer import SpaceSerializer

    try:
        # Parse config dict into SpaceConfig model
        parser = MetadataParser()
        # Ensure space_id exists for parsing
        if "space_id" not in config:
            config["space_id"] = config["title"].lower().replace(" ", "_")
        space_config = parser._dict_to_space_config(config)

        # Serialize using the proper serializer (handles all API v2 fields)
        serializer = SpaceSerializer()
        serialized_space = serializer.to_serialized_space(space_config)
    except Exception as e:
        # Fallback to simple serialization for basic configs
        console.print(f"[dim]Note: Using basic serialization ({e})[/dim]")
        serialized_space = {
            "version": 2,
            "config": {
                "sample_questions": [
                    {"question": [q.get("question") if isinstance(q, dict) else q]}
                    if isinstance(q, dict)
                    else {"question": [q]}
                    for q in config.get("sample_questions", [])
                ],
            },
            "data_sources": {
                "tables": [
                    {
                        "identifier": t.get("identifier") if isinstance(t, dict) else t,
                        "description": t.get("description", []) if isinstance(t, dict) else [],
                        "column_configs": t.get("column_configs", [])
                        if isinstance(t, dict)
                        else [],
                    }
                    for t in config.get("data_sources", {}).get("tables", [])
                ]
            },
            "instructions": config.get("instructions", {}),
        }

    table_identifiers: list[str] = [
        str(t.get("identifier") if isinstance(t, dict) else t)
        for t in config.get("data_sources", {}).get("tables", [])
        if (t.get("identifier") if isinstance(t, dict) else t)
    ]

    with with_spinner("Creating space..."):
        space_id = client.create_space(
            title=str(config["title"]),
            warehouse_id=str(config["warehouse_id"]),
            tables=table_identifiers,
            parent_path=config.get("parent_path"),
            serialized_space=serialized_space,
        )

    print_success(f"Space created: {space_id}")
    console.print(f"  URL: {client.workspace_url}/#genie/spaces/{space_id}")

    # Add to state if env specified
    if env:
        from genie_forge.models import SpaceConfig
        from genie_forge.state import StateManager

        try:
            # Create minimal SpaceConfig for state
            space_config = SpaceConfig(
                space_id=config.get("space_id", config["title"].lower().replace(" ", "_")),
                title=config["title"],
                warehouse_id=config["warehouse_id"],
                data_sources=config.get("data_sources", {}),
            )

            state = StateManager()
            result = state.import_space(
                config=space_config,
                databricks_space_id=space_id,
                env=env,
                workspace_url=client.workspace_url,
            )

            if result.get("success"):
                print_success(f"Added to state: {env} (logical_id: {result.get('logical_id')})")
        except Exception as e:
            print_warning(f"Space created but failed to add to state: {e}")

    console.print()


# =============================================================================
# space-export Command
# =============================================================================


@click.command("space-export")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default="conf/spaces",
    help="Output directory for YAML files",
)
@click.option(
    "--pattern",
    help="Filter spaces by name pattern (glob-style: 'Sales*')",
)
@click.option(
    "--space-id",
    multiple=True,
    help="Specific space IDs to export (can repeat)",
)
@click.option(
    "--exclude",
    multiple=True,
    help="Patterns to exclude (can repeat)",
)
@click.option(
    "--profile",
    "-p",
    help="Databricks CLI profile to use",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite existing files",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    help="Output format",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be exported without writing files",
)
def space_export(
    output_dir: str,
    pattern: Optional[str],
    space_id: tuple,
    exclude: tuple,
    profile: Optional[str],
    overwrite: bool,
    output_format: str,
    dry_run: bool,
) -> None:
    """Export Genie spaces to YAML/JSON files.

    Fetches spaces from Databricks and saves their configuration
    to local files for version control and editing.

    \b
    PERMISSION NOTE:
    ────────────────
    The --pattern option uses the Databricks list spaces API which requires
    "Can Edit" permission on the workspace. If you only have "Can View"
    permission, use --space-id instead to export specific spaces.

    \b
    EXAMPLES:
    ─────────
    # Export all spaces (requires "Can Edit" permission)
    $ genie-forge space-export --profile PROD

    # Export to specific directory
    $ genie-forge space-export --output-dir ./backup/spaces --profile PROD

    # Export only spaces matching pattern (requires "Can Edit" permission)
    $ genie-forge space-export --pattern "Sales*" --profile PROD

    # Export specific spaces by ID (works with "Can View" permission)
    $ genie-forge space-export --space-id abc123 --space-id def456 --profile PROD

    # Export all except certain patterns
    $ genie-forge space-export --exclude "Test*" --exclude "Draft*" --profile PROD

    # Dry run
    $ genie-forge space-export --pattern "Prod*" --dry-run --profile PROD
    """
    import fnmatch

    client = get_genie_client(profile=profile)

    # Phase 1: Fetch spaces
    console.print()
    spaces_to_export = []

    if space_id:
        # Fetch specific spaces by ID
        with create_progress_bar("Fetching spaces...") as progress:
            task = progress.add_task("Fetching...", total=len(space_id))
            for sid in space_id:
                try:
                    space = client.get_space(sid, include_serialized=True)
                    spaces_to_export.append(space)
                except Exception as e:
                    print_warning(f"Could not fetch space {sid}: {e}")
                progress.update(task, advance=1)
    else:
        # Fetch all spaces with pagination
        all_spaces = fetch_all_spaces_paginated(client, show_progress=True)

        # Apply filters
        for space in all_spaces:
            title = space.get("title", "")

            # Check pattern match
            if pattern and not fnmatch.fnmatch(title.lower(), pattern.lower()):
                continue

            # Check exclusions
            excluded = False
            for excl in exclude:
                if fnmatch.fnmatch(title.lower(), excl.lower()):
                    excluded = True
                    break
            if excluded:
                continue

            spaces_to_export.append(space)

    if not spaces_to_export:
        print_warning("No spaces matched the criteria")
        return

    console.print(f"Found [bold]{len(spaces_to_export)}[/bold] spaces to export\n")

    # Dry run - just list what would be exported
    if dry_run:
        console.print("[bold]Dry run - would export:[/bold]")
        console.print("─" * 60)
        for space in spaces_to_export:
            filename = sanitize_filename(space.get("title", "untitled"))
            console.print(f"  • {space.get('title')} → {output_dir}/{filename}.{output_format}")
        console.print("─" * 60)
        console.print(f"\n[dim]Total: {len(spaces_to_export)} files would be created[/dim]")
        return

    # Phase 2: Export to files
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    exported = 0
    skipped = 0
    failed = 0

    with create_progress_bar("Exporting spaces...") as progress:
        task = progress.add_task("Exporting...", total=len(spaces_to_export))

        for space in spaces_to_export:
            progress.update(task, advance=1)

            space_id_val = space.get("id")
            if not space_id_val:
                skipped += 1
                continue

            title = space.get("title", "untitled")
            filename = sanitize_filename(title)
            file_ext = "yaml" if output_format == "yaml" else "json"
            file_path = output_path / f"{filename}.{file_ext}"

            # Check if file exists
            if file_path.exists() and not overwrite:
                skipped += 1
                continue

            try:
                # Fetch full space details if needed
                if "serialized_space" not in space:
                    space = client.get_space(str(space_id_val), include_serialized=True)

                # Build export config
                export_config = _build_export_config(space)

                # Write file
                save_config_file(export_config, file_path, file_format=output_format)

                exported += 1
            except Exception as e:
                print_warning(f"Failed to export '{title}': {e}")
                failed += 1

    # Summary
    console.print()
    print_section_header("Export Summary")
    console.print(f"\n  [green]Exported:[/green]  {exported}")
    if skipped:
        console.print(f"  [yellow]Skipped:[/yellow]   {skipped} (use --overwrite to replace)")
    if failed:
        console.print(f"  [red]Failed:[/red]    {failed}")
    console.print(f"\n  Output: {output_path.absolute()}")
    console.print()


def _build_export_config(space: dict) -> dict:
    """Build export configuration from space data.

    Performs lossless export of all Genie space fields including:
    - Column configs with enable_format_assistance, enable_entity_matching
    - SQL snippets (filters, expressions, measures)
    - Parameters and usage_guidance in example questions
    - Join specs with aliases and relationship types
    """
    config: dict = {
        "space_id": sanitize_filename(space.get("title", "untitled")),
        "title": space.get("title"),
        "warehouse_id": space.get("warehouse_id"),
        "version": 2,  # Use current API version
    }

    if space.get("parent_path"):
        config["parent_path"] = space.get("parent_path")

    # Parse serialized_space
    serialized = parse_serialized_space(space)

    # Version from API
    if serialized.get("version"):
        config["version"] = serialized["version"]

    # Sample questions (preserve full structure with id)
    sample_q = serialized.get("config", {}).get("sample_questions", [])
    if sample_q:
        config["sample_questions"] = sample_q

    # Data sources (preserve full column config)
    if serialized.get("data_sources", {}).get("tables"):
        config["data_sources"] = {"tables": serialized["data_sources"]["tables"]}

    # Instructions (preserve all fields)
    instructions = serialized.get("instructions", {})
    if any(
        [
            instructions.get("text_instructions"),
            instructions.get("sql_functions"),
            instructions.get("example_question_sqls"),
            instructions.get("join_specs"),
            instructions.get("sql_snippets"),
        ]
    ):
        config["instructions"] = {}

        # Text instructions (preserve id and content as list)
        if instructions.get("text_instructions"):
            config["instructions"]["text_instructions"] = instructions["text_instructions"]

        # SQL functions
        if instructions.get("sql_functions"):
            config["instructions"]["sql_functions"] = instructions["sql_functions"]

        # Example question SQLs (preserve parameters, usage_guidance)
        if instructions.get("example_question_sqls"):
            config["instructions"]["example_question_sqls"] = instructions["example_question_sqls"]

        # Join specs (preserve left/right structure, sql, instruction)
        if instructions.get("join_specs"):
            config["instructions"]["join_specs"] = instructions["join_specs"]

        # SQL snippets (filters, expressions, measures)
        sql_snippets = instructions.get("sql_snippets", {})
        if any(
            [
                sql_snippets.get("filters"),
                sql_snippets.get("expressions"),
                sql_snippets.get("measures"),
            ]
        ):
            config["instructions"]["sql_snippets"] = {}
            if sql_snippets.get("filters"):
                config["instructions"]["sql_snippets"]["filters"] = sql_snippets["filters"]
            if sql_snippets.get("expressions"):
                config["instructions"]["sql_snippets"]["expressions"] = sql_snippets["expressions"]
            if sql_snippets.get("measures"):
                config["instructions"]["sql_snippets"]["measures"] = sql_snippets["measures"]

    return config


# =============================================================================
# space-clone Command
# =============================================================================


@click.command("space-clone")
@click.argument("source")
@click.option(
    "--name",
    "-n",
    help="New name for cloned space (default: 'Copy of <original>')",
)
@click.option(
    "--to-workspace",
    is_flag=True,
    help="Clone to same workspace (create a copy in Databricks)",
)
@click.option(
    "--to-file",
    type=click.Path(),
    help="Clone to local file (YAML config)",
)
@click.option(
    "--warehouse-id",
    "-w",
    help="Override warehouse ID in clone",
)
@click.option(
    "--profile",
    "-p",
    help="Databricks CLI profile to use",
)
@click.option(
    "--target-profile",
    help="Profile for target workspace (cross-workspace clone)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview without creating",
)
def space_clone(
    source: str,
    name: Optional[str],
    to_workspace: bool,
    to_file: Optional[str],
    warehouse_id: Optional[str],
    profile: Optional[str],
    target_profile: Optional[str],
    dry_run: bool,
) -> None:
    """Clone a Genie space.

    Create a copy of an existing space either in the same workspace,
    to a different workspace, or export to a local config file.

    SOURCE can be a space ID or space name (exact match).

    \b
    EXAMPLES:
    ─────────
    # Clone to same workspace
    $ genie-forge space-clone "Sales Analytics" --to-workspace --profile PROD

    # Clone with new name
    $ genie-forge space-clone "Sales Analytics" --to-workspace \\
        --name "Sales Analytics - Test" --profile PROD

    # Clone to local file
    $ genie-forge space-clone "Sales Analytics" --to-file conf/spaces/sales_copy.yaml --profile PROD

    # Clone with different warehouse
    $ genie-forge space-clone abc123 --to-workspace \\
        --warehouse-id new_warehouse_id --profile PROD
    """
    import yaml

    if not to_workspace and not to_file:
        raise click.UsageError("Specify --to-workspace or --to-file")

    client = get_genie_client(profile=profile)

    # Find source space
    space_id: str | None = source
    space = None

    with with_spinner("Fetching source space..."):
        # Try as space ID first
        try:
            space = client.get_space(source, include_serialized=True)
        except Exception:
            # Try as name
            spaces = client.list_spaces()
            for s in spaces:
                if s.get("title") == source:
                    space_id = s.get("id")
                    if space_id:
                        space = client.get_space(space_id, include_serialized=True)
                    break

    if not space:
        print_error(f"Space not found: {source}")
        sys.exit(1)

    original_title = space.get("title", "Untitled")
    new_title = name or f"Copy of {original_title}"

    console.print()
    print_section_header("Clone Space")
    console.print(f"\n  [bold]Source:[/bold]      {original_title}")
    console.print(f"  [bold]Source ID:[/bold]   {space.get('id')}")
    console.print(f"  [bold]New Title:[/bold]   {new_title}")
    if warehouse_id:
        console.print(f"  [bold]Warehouse:[/bold]   {warehouse_id} (overridden)")
    else:
        console.print(f"  [bold]Warehouse:[/bold]   {space.get('warehouse_id')}")
    console.print()

    # Build clone config
    clone_config = _build_export_config(space)
    clone_config["title"] = new_title
    clone_config["space_id"] = sanitize_filename(new_title)

    if warehouse_id:
        clone_config["warehouse_id"] = warehouse_id

    if dry_run:
        console.print("[bold]Dry run - clone configuration:[/bold]")
        console.print("─" * 60)
        console.print(yaml.dump(clone_config, default_flow_style=False, sort_keys=False))
        console.print("─" * 60)
        console.print("\n[dim]No changes made (dry run).[/dim]")
        return

    # Clone to file
    if to_file:
        save_config_file(clone_config, to_file, file_format="yaml")
        print_success(f"Cloned to file: {to_file}")
        console.print("\nTo create this space, run:")
        console.print(
            f"  genie-forge space-create --from-file {to_file} --profile {profile or 'YOUR_PROFILE'}"
        )
        return

    # Clone to workspace
    if to_workspace:
        target_client = client
        if target_profile:
            target_client = get_genie_client(profile=target_profile)

        # Parse serialized space
        serialized = parse_serialized_space(space)

        # Get table list
        tables: list[str] = [
            str(t.get("identifier"))
            for t in serialized.get("data_sources", {}).get("tables", [])
            if t.get("identifier")
        ]
        resolved_warehouse_id = warehouse_id or space.get("warehouse_id")
        if not resolved_warehouse_id:
            print_error("Could not determine warehouse ID for clone")
            sys.exit(1)

        with with_spinner("Creating clone in workspace..."):
            new_space_id = target_client.create_space(
                title=new_title,
                warehouse_id=str(resolved_warehouse_id),
                tables=tables,
                parent_path=space.get("parent_path"),
                serialized_space=serialized,
            )

        print_success(f"Space cloned: {new_space_id}")
        console.print(f"  URL: {target_client.workspace_url}/#genie/spaces/{new_space_id}")

    console.print()


# =============================================================================
# space-delete Command (Alias for destroy)
# =============================================================================


@click.command("space-delete")
@click.pass_context
def space_delete(ctx: click.Context, **kwargs: Any) -> None:
    """Delete Genie spaces from workspace. (Alias for destroy)

    Removes the specified spaces from Databricks and updates the local
    state file. Use with caution as this operation cannot be undone.

    \b
    EXAMPLES:
    ─────────
    # Delete all spaces in dev environment
    $ genie-forge space-delete --env dev --profile DEV

    # Delete specific space
    $ genie-forge space-delete --space-id 01abc123 --env dev --profile DEV
    """
    from genie_forge.cli.spaces import destroy

    ctx.invoke(destroy, **kwargs)


# We need to copy params from destroy - will be done during registration
