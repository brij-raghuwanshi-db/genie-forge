"""Import command for bringing existing Genie spaces under management."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import click
import yaml
from rich.panel import Panel
from rich.table import Table

from genie_forge.cli.common import (
    console,
    get_genie_client,
    print_error,
    print_info,
    print_success,
    print_warning,
)
from genie_forge.serializer import SpaceSerializer
from genie_forge.state import StateManager

if TYPE_CHECKING:
    from genie_forge.models import SpaceConfig


def _sanitize_logical_id(title: str) -> str:
    """Convert a space title to a valid logical ID.

    Args:
        title: The space title

    Returns:
        A sanitized string suitable for use as a logical ID
    """
    # Convert to lowercase, replace spaces and special chars with underscores
    sanitized = re.sub(r"[^a-zA-Z0-9]+", "_", title.lower())
    # Remove leading/trailing underscores
    sanitized = sanitized.strip("_")
    # Ensure it doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = f"space_{sanitized}"
    return sanitized or "imported_space"


def _config_to_yaml(config: SpaceConfig) -> str:
    """Convert a SpaceConfig to YAML string.

    Args:
        config: SpaceConfig object

    Returns:
        YAML string representation
    """
    # Build the YAML structure
    yaml_dict: dict[str, Any] = {
        "space_id": config.space_id,
        "title": config.title,
        "warehouse_id": config.warehouse_id,
    }

    if config.parent_path:
        yaml_dict["parent_path"] = config.parent_path

    if config.sample_questions:
        yaml_dict["sample_questions"] = config.sample_questions

    # Data sources
    if config.data_sources.tables:
        tables: list[dict[str, Any]] = []
        for tbl in config.data_sources.tables:
            tbl_dict: dict[str, Any] = {"identifier": tbl.identifier}
            if tbl.description:
                tbl_dict["description"] = tbl.description
            if tbl.column_configs:
                cols: list[dict[str, Any]] = []
                for col in tbl.column_configs:
                    col_dict: dict[str, Any] = {"column_name": col.column_name}
                    if col.description:
                        col_dict["description"] = col.description
                    if col.synonyms:
                        col_dict["synonyms"] = col.synonyms
                    if col.build_value_dictionary:
                        col_dict["build_value_dictionary"] = True
                    if col.get_example_values:
                        col_dict["get_example_values"] = True
                    cols.append(col_dict)
                tbl_dict["column_configs"] = cols
            tables.append(tbl_dict)
        yaml_dict["data_sources"] = {"tables": tables}

    # Instructions
    instructions: dict[str, Any] = {}
    if config.instructions.text_instructions:
        instructions["text_instructions"] = [
            {"content": inst.content} for inst in config.instructions.text_instructions
        ]
    if config.instructions.example_question_sqls:
        instructions["example_question_sqls"] = [
            {"question": ex.question, "sql": ex.sql}
            for ex in config.instructions.example_question_sqls
        ]
    if config.instructions.sql_functions:
        instructions["sql_functions"] = [
            {"identifier": f.identifier, "description": f.description}
            if f.description
            else {"identifier": f.identifier}
            for f in config.instructions.sql_functions
        ]
    if config.instructions.join_specs:
        instructions["join_specs"] = [
            {
                "id": j.id,
                "left": {
                    "identifier": j.left.identifier,
                    **({"alias": j.left.alias} if j.left.alias else {}),
                },
                "right": {
                    "identifier": j.right.identifier,
                    **({"alias": j.right.alias} if j.right.alias else {}),
                },
                "sql": j.sql,
                **({"instruction": j.instruction} if j.instruction else {}),
            }
            for j in config.instructions.join_specs
        ]
    if instructions:
        yaml_dict["instructions"] = instructions

    # Benchmarks
    if config.benchmarks and config.benchmarks.questions:
        yaml_dict["benchmarks"] = {
            "questions": [
                {"question": q.question, "expected_sql": q.expected_sql}
                for q in config.benchmarks.questions
            ]
        }

    return yaml.dump(yaml_dict, default_flow_style=False, sort_keys=False, allow_unicode=True)


@click.command("import")
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
def import_space(
    space_id: Optional[str],
    pattern: Optional[str],
    env: str,
    logical_id: Optional[str],
    profile: Optional[str],
    state_file: str,
    output_dir: str,
    dry_run: bool,
    force: bool,
) -> None:
    """Import existing Genie spaces into genie-forge management.

    Fetches space configuration from Databricks and generates YAML config files
    plus state entries. This allows you to manage previously UI-created spaces
    with genie-forge.

    \b
    IMPORT MODES:
    ─────────────
    1. Single space by ID:
       $ genie-forge import 01ABC123DEF456 --env prod --as my_space

    2. Multiple spaces by pattern:
       $ genie-forge import --pattern "Sales*" --env prod

    \b
    WHAT IT DOES:
    ─────────────
    1. Connects to Databricks workspace
    2. Fetches space configuration via API
    3. Generates YAML config file(s) in output directory
    4. Adds space(s) to state file for tracking

    \b
    EXAMPLES:
    ─────────
    # Import a single space with custom logical ID
    $ genie-forge import 01ABCDEF123456 --env prod --as sales_dashboard --profile PROD

    # Import all spaces matching pattern
    $ genie-forge import --pattern "*Analytics*" --env dev --profile DEV

    # Preview what would be imported
    $ genie-forge import --pattern "*" --env prod --dry-run --profile PROD

    # Import to custom directory
    $ genie-forge import 01ABC123 --env prod --output-dir conf/imported/ --profile PROD
    """
    # Validate arguments
    if not space_id and not pattern:
        print_error("Either SPACE_ID or --pattern is required")
        console.print("\nUsage:")
        console.print("  genie-forge import <space_id> --env <env>")
        console.print("  genie-forge import --pattern '<pattern>' --env <env>")
        sys.exit(1)

    if space_id and pattern:
        print_error("Cannot specify both SPACE_ID and --pattern")
        sys.exit(1)

    if logical_id and pattern:
        print_error("--as can only be used with a single SPACE_ID, not with --pattern")
        sys.exit(1)

    # Connect to Databricks
    client = get_genie_client(profile=profile)

    console.print()
    console.print(Panel("[bold]Import Genie Spaces[/bold]"))
    console.print(f"  Workspace: {client.workspace_url}")
    console.print(f"  Environment: {env}")
    console.print(f"  Output: {output_dir}/")
    console.print()

    # Find spaces to import
    spaces_to_import = []
    serializer = SpaceSerializer()

    if space_id:
        # Import single space by ID
        console.print(f"Fetching space {space_id}...")
        try:
            response = client.get_space(space_id, include_serialized=True)
            spaces_to_import.append(response)
        except Exception as e:
            print_error(f"Failed to fetch space {space_id}: {e}")
            sys.exit(1)
    else:
        # Import by pattern (pattern is guaranteed to be str here due to validation above)
        assert pattern is not None  # For type checker
        console.print(f"Searching for spaces matching '{pattern}'...")
        try:
            matches = client.find_spaces_by_name(pattern)
            if not matches:
                print_info(f"No spaces found matching '{pattern}'")
                return

            console.print(f"  Found {len(matches)} matching space(s)")
            console.print()

            # Fetch full details for each match
            for match in matches:
                match_id = match.get("space_id") or match.get("id")
                if match_id:
                    try:
                        response = client.get_space(match_id, include_serialized=True)
                        spaces_to_import.append(response)
                    except Exception as e:
                        print_warning(f"Could not fetch {match_id}: {e}")
        except Exception as e:
            print_error(f"Failed to search spaces: {e}")
            sys.exit(1)

    if not spaces_to_import:
        print_info("No spaces to import")
        return

    # Show what will be imported
    table = Table(title="Spaces to Import")
    table.add_column("Databricks ID", style="cyan")
    table.add_column("Title")
    table.add_column("Logical ID", style="green")
    table.add_column("Config File")

    state_manager = StateManager(state_file=state_file)
    output_path = Path(output_dir)

    import_plan = []
    for space in spaces_to_import:
        db_id = space.get("id") or space.get("space", {}).get("id")
        title = space.get("title") or space.get("space", {}).get("title")

        # Determine logical ID
        if logical_id and len(spaces_to_import) == 1:
            lid = logical_id
        else:
            lid = _sanitize_logical_id(title)

        # Check for conflicts
        config_file = output_path / f"{lid}.yaml"
        conflict = False

        # Check state conflict
        env_state = state_manager.state.environments.get(env)
        if env_state is not None and lid in env_state.spaces and not force:
            conflict = True
            lid = f"{lid} [yellow](exists in state)[/yellow]"

        # Check file conflict
        if config_file.exists() and not force:
            conflict = True
            lid = f"{lid} [yellow](file exists)[/yellow]"

        import_plan.append(
            {
                "db_id": db_id,
                "title": title,
                "logical_id": lid if not conflict else lid.split(" [")[0],
                "config_file": config_file,
                "response": space,
                "conflict": conflict,
                "display_lid": lid,
            }
        )

        table.add_row(db_id, title, lid, str(config_file))

    console.print(table)
    console.print()

    # Check for conflicts
    conflicts = [p for p in import_plan if p["conflict"]]
    if conflicts and not force:
        print_warning(f"{len(conflicts)} space(s) have conflicts (use --force to overwrite)")

    if dry_run:
        print_info(f"Dry run mode - {len(import_plan)} space(s) would be imported")
        return

    # Create output directory
    output_path.mkdir(parents=True, exist_ok=True)

    # Import each space
    console.print("Importing spaces...")
    console.print()

    imported = 0
    skipped = 0
    failed = 0

    for plan in import_plan:
        if plan["conflict"] and not force:
            print_warning(f"Skipped: {plan['logical_id']} (conflict)")
            skipped += 1
            continue

        try:
            # Convert API response to SpaceConfig
            config = serializer.from_api_to_config(plan["response"], plan["logical_id"])

            # Generate YAML
            yaml_content = _config_to_yaml(config)

            # Write config file
            plan["config_file"].write_text(yaml_content)

            # Add to state
            state_manager.import_space(
                config=config,
                databricks_space_id=plan["db_id"],
                env=env,
            )

            print_success(f"Imported: {plan['logical_id']} → {plan['config_file']}")
            imported += 1

        except Exception as e:
            print_error(f"Failed: {plan['logical_id']} - {e}")
            failed += 1

    # Summary
    console.print()
    console.print(f"Import complete: {imported} imported, {skipped} skipped, {failed} failed")

    if imported > 0:
        console.print()
        console.print("Next steps:")
        console.print(f"  1. Review generated configs in {output_dir}/")
        console.print(f"  2. genie-forge status --env {env}")
        console.print(f"  3. genie-forge drift --env {env} --profile {profile or 'YOUR_PROFILE'}")
