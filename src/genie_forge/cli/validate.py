"""Validate command for configuration files."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from genie_forge.cli.common import (
    OperationCounter,
    console,
    create_progress_bar,
    print_error,
    print_success,
    print_warning,
)
from genie_forge.parsers import validate_config


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    required=True,
    help="Path to a YAML/JSON config file or directory containing configs. "
    "When a directory is given, all *.yaml and *.json files are validated.",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Enable strict mode: treat warnings as errors and fail if any warnings exist. "
    "Useful for CI/CD pipelines where you want to enforce best practices.",
)
def validate(config: str, strict: bool) -> None:
    """Validate configuration files for syntax and schema errors.

    Performs comprehensive validation of your Genie space configurations:

    \b
    WHAT IT CHECKS:
    ───────────────
    • YAML/JSON syntax errors (malformed files)
    • Required fields (space_id, title, warehouse_id, data_sources)
    • Schema validation (correct types, valid enums)
    • Variable syntax (${variable_name} placeholders)
    • Reference consistency (table identifiers format)

    \b
    VALIDATION LEVELS:
    ──────────────────
    • ERRORS   → Invalid configs that will fail deployment
    • WARNINGS → Valid but potentially problematic configs

    \b
    USE CASES:
    ──────────
    • Pre-commit hooks: Validate before committing changes
    • CI/CD pipelines: Use --strict to enforce quality gates
    • Development: Quick syntax check during authoring

    \b
    EXAMPLES:
    ─────────
    # Validate a single configuration file
    $ genie-forge validate --config conf/spaces/sales_analytics.yaml

    # Validate all configs in a directory
    $ genie-forge validate --config conf/spaces/

    # Strict mode for CI/CD (fail on warnings)
    $ genie-forge validate --config conf/spaces/ --strict

    \b
    EXIT CODES:
    ───────────
    0 = All validations passed
    1 = Errors found (or warnings in strict mode)
    """
    config_path = Path(config)

    if config_path.is_dir():
        files = list(config_path.glob("*.yaml")) + list(config_path.glob("*.json"))
        if not files:
            print_warning(f"No YAML or JSON files found in {config_path}")
            return
    else:
        files = [config_path]

    console.print(f"\nValidating {len(files)} file(s)...\n")

    # Track results
    counter = OperationCounter()
    validation_results: list[dict] = []

    with create_progress_bar("Validating...") as progress:
        task = progress.add_task("Validating...", total=len(files))

        for file_path in sorted(files):
            errors = validate_config(file_path)

            if errors:
                counter.failed += 1
                validation_results.append(
                    {
                        "file": file_path.name,
                        "status": "failed",
                        "errors": errors,
                    }
                )
            else:
                counter.created += 1  # Using 'created' as 'passed'
                validation_results.append(
                    {
                        "file": file_path.name,
                        "status": "passed",
                        "errors": [],
                    }
                )

            progress.update(task, advance=1)

    console.print()

    # Display results
    for result in validation_results:
        if result["status"] == "failed":
            console.print(f"[red]✗[/red] {result['file']}")
            for error in result["errors"]:
                console.print(f"    [red]{error}[/red]")
        else:
            console.print(f"[green]✓[/green] {result['file']}")

    # Summary
    console.print()
    console.print("[bold]VALIDATION SUMMARY[/bold]")
    console.print("─" * 60)
    console.print(f"  [green]Passed:[/green]  {counter.created}")
    if counter.failed:
        console.print(f"  [red]Failed:[/red]  {counter.failed}")
    console.print("─" * 60)
    console.print(f"  [bold]Total:[/bold]   {len(files)}")

    total_errors = sum(len(r["errors"]) for r in validation_results)

    if counter.failed > 0:
        console.print()
        print_error(f"Validation failed: {total_errors} error(s) in {counter.failed} file(s)")
        sys.exit(1)
    elif strict and counter.skipped > 0:
        console.print()
        print_error(f"Validation failed (strict mode): {counter.skipped} warning(s)")
        sys.exit(1)
    else:
        console.print()
        print_success(f"All {len(files)} file(s) valid")
