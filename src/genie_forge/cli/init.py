"""Initialize a new Genie-Forge project."""

from __future__ import annotations

from pathlib import Path

import click

from genie_forge.cli.common import console, print_success, print_warning

# Default directory structure
DEFAULT_DIRS = [
    "conf/spaces",
    "conf/variables",
]

# Example space configuration
EXAMPLE_SPACE_YAML = """\
# Example Genie Space Configuration
# Copy this file and customize for your space

# Unique identifier for this space (used in state tracking)
space_id: example_space

# Display title shown in Databricks UI
title: Example Analytics Space

# SQL warehouse ID (get this from Databricks SQL Warehouses page)
warehouse_id: ${warehouse_id}

# Optional: Description of the space
description: |
  An example Genie space for analytics queries.
  This space demonstrates the basic configuration structure.

# Data sources - tables available for querying
data_sources:
  tables:
    - identifier: catalog.schema.table_name
      description: Description of what this table contains
    # Add more tables as needed:
    # - identifier: catalog.schema.another_table
    #   description: Another table description

# Optional: Instructions for the AI assistant
instructions:
  # Text instructions guide the AI's behavior
  text_instructions:
    - text: Always format currency values with $ symbol and 2 decimal places
    - text: When asked about 'revenue', use the sum of the amount column

  # SQL functions available to the AI
  # sql_functions:
  #   - identifier: catalog.schema.my_function

  # Example SQL queries to help the AI
  # sql_examples:
  #   - sql: |
  #       SELECT customer_id, SUM(amount) as total
  #       FROM catalog.schema.orders
  #       GROUP BY customer_id
  #     question: What is the total spend per customer?

# Optional: Sample questions shown to users
sample_questions:
  - question: What are the top 10 items by sales?
  - question: Show me the trend over the last 30 days
"""

# Example variables file
EXAMPLE_VARIABLES_YAML = """\
# Environment-specific variables
# These can be referenced in space configs using ${variable_name}

# Development environment
dev:
  warehouse_id: your_dev_warehouse_id
  catalog: dev_catalog
  schema: dev_schema

# Production environment
prod:
  warehouse_id: your_prod_warehouse_id
  catalog: prod_catalog
  schema: prod_schema
"""

# Gitignore additions
GITIGNORE_CONTENT = """\
# Genie-Forge
.genie-forge.json
*.bak

# Environment-specific secrets (if any)
conf/variables/secrets.yaml
"""

# Initial state file
INITIAL_STATE = """\
{
  "version": "1.0.0",
  "environments": {}
}
"""


@click.command()
@click.option(
    "--path",
    "-p",
    type=click.Path(),
    default=".",
    help="Directory to initialize (default: current directory)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing files",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation prompts",
)
@click.option(
    "--minimal",
    is_flag=True,
    help="Create minimal structure without examples",
)
def init(path: str, force: bool, yes: bool, minimal: bool) -> None:
    """Initialize a new Genie-Forge project.

    Creates the directory structure and example configuration files
    needed to start managing Genie spaces with Genie-Forge.

    \b
    CREATED STRUCTURE:
    ──────────────────
    ./
    ├── conf/
    │   ├── spaces/           # Space configuration files
    │   │   └── example.yaml  # Example space config
    │   └── variables/        # Environment variables
    │       └── env.yaml      # Environment-specific values
    ├── .genie-forge.json     # State file (tracks deployments)
    └── .gitignore            # Git ignore patterns (updated)

    \b
    EXAMPLES:
    ─────────
    # Initialize in current directory
    $ genie-forge init

    # Initialize in a specific directory
    $ genie-forge init --path ./my-genie-project

    # Initialize without prompts
    $ genie-forge init --yes

    # Minimal structure (no example files)
    $ genie-forge init --minimal
    """
    project_path = Path(path).resolve()

    # Check if already initialized
    state_file = project_path / ".genie-forge.json"
    spaces_dir = project_path / "conf" / "spaces"

    if state_file.exists() or spaces_dir.exists():
        if not force:
            if not yes:
                console.print("\n[yellow]Project appears to already be initialized at:[/yellow]")
                console.print(f"  {project_path}\n")
                if not click.confirm("Do you want to continue and overwrite?"):
                    console.print("[dim]Cancelled.[/dim]")
                    return
            else:
                print_warning(f"Project already initialized at {project_path}")

    # Show what will be created
    if not yes:
        console.print("\n[bold]Genie-Forge Project Initialization[/bold]")
        console.print("═" * 50)
        console.print(f"\n[bold]Location:[/bold] {project_path}\n")
        console.print("[bold]Will create:[/bold]")
        for dir_path in DEFAULT_DIRS:
            console.print(f"  [blue]📁[/blue] {dir_path}/")
        console.print("  [green]📄[/green] .genie-forge.json")
        if not minimal:
            console.print("  [green]📄[/green] conf/spaces/example.yaml")
            console.print("  [green]📄[/green] conf/variables/env.yaml")
        console.print()

        if not click.confirm("Proceed with initialization?"):
            console.print("[dim]Cancelled.[/dim]")
            return

    # Create directories
    console.print()
    for dir_path in DEFAULT_DIRS:
        full_path = project_path / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print_success(f"Created {dir_path}/")

    # Create state file
    if not state_file.exists() or force:
        state_file.write_text(INITIAL_STATE)
        print_success("Created .genie-forge.json")
    else:
        print_warning(".genie-forge.json already exists (skipped)")

    # Create example files (unless minimal)
    if not minimal:
        # Example space config
        example_space = project_path / "conf" / "spaces" / "example.yaml"
        if not example_space.exists() or force:
            example_space.write_text(EXAMPLE_SPACE_YAML)
            print_success("Created conf/spaces/example.yaml")
        else:
            print_warning("conf/spaces/example.yaml already exists (skipped)")

        # Example variables file
        variables_file = project_path / "conf" / "variables" / "env.yaml"
        if not variables_file.exists() or force:
            variables_file.write_text(EXAMPLE_VARIABLES_YAML)
            print_success("Created conf/variables/env.yaml")
        else:
            print_warning("conf/variables/env.yaml already exists (skipped)")

    # Update .gitignore
    gitignore_path = project_path / ".gitignore"
    gitignore_marker = "# Genie-Forge"

    if gitignore_path.exists():
        existing_content = gitignore_path.read_text()
        if gitignore_marker not in existing_content:
            # Append to existing .gitignore
            with gitignore_path.open("a") as f:
                f.write(f"\n{GITIGNORE_CONTENT}")
            print_success("Updated .gitignore")
        else:
            print_warning(".gitignore already has Genie-Forge entries (skipped)")
    else:
        gitignore_path.write_text(GITIGNORE_CONTENT)
        print_success("Created .gitignore")

    # Print success message
    console.print()
    console.print("[bold green]✓ Project initialized successfully![/bold green]")
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print("─" * 50)
    console.print()
    console.print("1. [bold]Check your Databricks profiles:[/bold]")
    console.print("   $ genie-forge profiles")
    console.print()
    console.print("2. [bold]Edit the example space configuration:[/bold]")
    console.print("   $ vi conf/spaces/example.yaml")
    console.print()
    console.print("3. [bold]Set your environment variables:[/bold]")
    console.print("   $ vi conf/variables/env.yaml")
    console.print()
    console.print("4. [bold]Validate your configuration:[/bold]")
    console.print("   $ genie-forge validate --config conf/spaces/")
    console.print()
    console.print("5. [bold]Plan your deployment:[/bold]")
    console.print("   $ genie-forge plan --env dev --profile YOUR_PROFILE")
    console.print()
    console.print("6. [bold]Deploy:[/bold]")
    console.print("   $ genie-forge apply --env dev --profile YOUR_PROFILE")
    console.print()
