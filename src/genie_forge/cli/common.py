"""Common utilities shared across CLI commands."""

from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterator, Optional, Union

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

if TYPE_CHECKING:
    from genie_forge.client import GenieClient

# Shared console instance for all CLI output
console = Console()


# =============================================================================
# Print Helpers
# =============================================================================


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[red]Error:[/red] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓[/green] {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]⚠[/yellow] {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[blue]ℹ[/blue] {message}")


# =============================================================================
# Progress Indicators
# =============================================================================


def create_progress_bar(description: str = "Processing...") -> Progress:
    """Create a standard progress bar for bulk operations.

    Shows: [spinner] Description [████████░░░░] 60% (12/20) 00:00:45

    Usage:
        with create_progress_bar("Applying...") as progress:
            task = progress.add_task("Applying...", total=len(items))
            for item in items:
                # do work
                progress.update(task, advance=1)
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=30),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        TimeElapsedColumn(),
        console=console,
    )


def create_pagination_progress(description: str = "Fetching...") -> Progress:
    """Create progress bar for pagination (unknown total).

    Shows: [spinner] Page 3 (375 items) 00:00:12

    Usage:
        with create_pagination_progress("Fetching spaces...") as progress:
            task = progress.add_task("Fetching...", total=None)
            while has_more:
                page_num += 1
                progress.update(task, description=f"Page {page_num}", completed=len(items))
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        TextColumn("[dim]({task.completed} items)[/dim]"),
        TimeElapsedColumn(),
        console=console,
    )


@contextmanager
def with_spinner(message: str) -> Iterator[None]:
    """Show spinner for single-item operations.

    Usage:
        with with_spinner("Fetching space details..."):
            space = client.get_space(space_id)
    """
    with console.status(f"[bold blue]{message}"):
        yield


@contextmanager
def with_spinner_result(message: str, success_message: str = "Done") -> Iterator[None]:
    """Spinner that shows success/failure on completion.

    Usage:
        with with_spinner_result("Creating space...", "Space created!"):
            space = client.create_space(config)
    """
    try:
        with console.status(f"[bold blue]{message}"):
            yield
        console.print(f"[green]✓[/green] {success_message}")
    except Exception:
        console.print("[red]✗[/red] Failed")
        raise


# =============================================================================
# Operation Counter
# =============================================================================


@dataclass
class OperationCounter:
    """Track operation results with counters.

    Usage:
        counter = OperationCounter()
        counter.created += 1
        counter.add_detail("created", "sales_analytics", "Space created successfully")
        print(counter.summary())
    """

    created: int = 0
    updated: int = 0
    deleted: int = 0
    failed: int = 0
    skipped: int = 0
    unchanged: int = 0
    details: list[dict] = field(default_factory=list)

    def add_detail(self, operation: str, item: str, message: str = "", error: str = "") -> None:
        """Add a detail record for reporting."""
        self.details.append(
            {"operation": operation, "item": item, "message": message, "error": error}
        )

    @property
    def total(self) -> int:
        """Total operations performed."""
        return (
            self.created + self.updated + self.deleted + self.failed + self.skipped + self.unchanged
        )

    @property
    def success_count(self) -> int:
        """Total successful operations."""
        return self.created + self.updated + self.deleted

    def summary(self) -> str:
        """Return formatted summary string."""
        parts = []
        if self.created:
            parts.append(f"[green]{self.created} created[/green]")
        if self.updated:
            parts.append(f"[yellow]{self.updated} updated[/yellow]")
        if self.deleted:
            parts.append(f"[red]{self.deleted} deleted[/red]")
        if self.failed:
            parts.append(f"[red bold]{self.failed} failed[/red bold]")
        if self.skipped:
            parts.append(f"[dim]{self.skipped} skipped[/dim]")
        if self.unchanged:
            parts.append(f"[dim]{self.unchanged} unchanged[/dim]")
        return " | ".join(parts) if parts else "No operations"

    def print_summary(self, title: str = "SUMMARY") -> None:
        """Print a formatted summary box."""
        console.print()
        console.print(f"[bold]{title}[/bold]")
        console.print("─" * 60)
        if self.created:
            console.print(f"  [green]Created:[/green]   {self.created}")
        if self.updated:
            console.print(f"  [yellow]Updated:[/yellow]   {self.updated}")
        if self.deleted:
            console.print(f"  [red]Deleted:[/red]   {self.deleted}")
        if self.failed:
            console.print(f"  [red bold]Failed:[/red bold]    {self.failed}")
        if self.skipped:
            console.print(f"  [dim]Skipped:[/dim]   {self.skipped}")
        if self.unchanged:
            console.print(f"  [dim]Unchanged:[/dim] {self.unchanged}")
        console.print("─" * 60)
        console.print(f"  [bold]Total:[/bold]     {self.total}")


def print_section_header(title: str, char: str = "═") -> None:
    """Print a section header."""
    console.print()
    console.print(f"[bold]{title}[/bold]")
    console.print(char * 60)


def print_section_separator(char: str = "─") -> None:
    """Print a section separator."""
    console.print(char * 60)


# =============================================================================
# Client Helpers
# =============================================================================


def get_genie_client(
    profile: Optional[str] = None,
    exit_on_error: bool = True,
) -> "GenieClient":
    """Get an authenticated GenieClient instance.

    Args:
        profile: Databricks CLI profile name
        exit_on_error: If True, print error and exit on failure.
                       If False, raise the exception.

    Returns:
        Authenticated GenieClient instance

    Raises:
        Exception: If exit_on_error is False and authentication fails
    """
    from genie_forge.client import GenieClient

    try:
        return GenieClient(profile=profile)
    except Exception as e:
        if exit_on_error:
            print_error(f"Authentication failed: {e}")
            sys.exit(1)
        raise


def fetch_all_spaces_paginated(
    client: "GenieClient",
    show_progress: bool = True,
    progress_description: str = "Fetching spaces...",
    max_pages: int = 100,
    on_page_fetched: Optional[Callable[[int, list], None]] = None,
) -> list[dict]:
    """Fetch all Genie spaces with pagination.

    Args:
        client: GenieClient instance
        show_progress: Whether to show progress indicator
        progress_description: Description for progress bar
        max_pages: Maximum number of pages to fetch (safety limit)
        on_page_fetched: Optional callback(page_num, spaces) called after each page

    Returns:
        List of all space dictionaries
    """
    all_spaces: list[dict] = []
    page_token: Optional[str] = None
    page_num = 0

    if show_progress:
        with create_pagination_progress(progress_description) as progress:
            task = progress.add_task("Fetching...", total=None)

            while page_num < max_pages:
                page_num += 1
                progress.update(
                    task,
                    description=f"Page {page_num}",
                    completed=len(all_spaces),
                )

                params = {"page_token": page_token} if page_token else None
                response = client._api_get("/api/2.0/genie/spaces", params=params)

                if isinstance(response, dict):
                    spaces = response.get("spaces", [])
                    all_spaces.extend(spaces)

                    if on_page_fetched:
                        on_page_fetched(page_num, spaces)

                    page_token = response.get("next_page_token")
                    if not page_token:
                        break
                else:
                    break

            progress.update(task, description="Complete", completed=len(all_spaces))
    else:
        while page_num < max_pages:
            page_num += 1
            params = {"page_token": page_token} if page_token else None
            response = client._api_get("/api/2.0/genie/spaces", params=params)

            if isinstance(response, dict):
                spaces = response.get("spaces") or []
                all_spaces.extend(spaces)

                if on_page_fetched:
                    on_page_fetched(page_num, spaces)

                page_token = response.get("next_page_token")
                if not page_token:
                    break
            else:
                break

    return all_spaces


# =============================================================================
# State File Helpers
# =============================================================================


def load_state_file(
    state_file: Union[str, Path] = ".genie-forge.json",
    exit_on_error: bool = True,
    show_not_found_message: bool = True,
) -> Optional[dict]:
    """Load and parse a state file.

    Args:
        state_file: Path to state file
        exit_on_error: If True, exit on read/parse errors. If False, raise exception.
        show_not_found_message: If True, show helpful message when file not found

    Returns:
        Parsed state data dict, or None if file doesn't exist (when not exit_on_error)

    Raises:
        FileNotFoundError: If file doesn't exist and exit_on_error is False
        json.JSONDecodeError: If file is invalid JSON and exit_on_error is False
    """
    state_path = Path(state_file)

    if not state_path.exists():
        if show_not_found_message:
            print_warning(f"State file not found: {state_file}")
            console.print("\nNo spaces are being tracked yet.")
            console.print("Run 'genie-forge apply' to deploy spaces and create the state file.")
        if exit_on_error:
            return None
        raise FileNotFoundError(f"State file not found: {state_file}")

    try:
        content = state_path.read_text(encoding="utf-8")
        result: dict[Any, Any] = json.loads(content)
        return result
    except json.JSONDecodeError as e:
        if exit_on_error:
            print_error(f"Invalid JSON in state file: {e}")
            sys.exit(1)
        raise
    except Exception as e:
        if exit_on_error:
            print_error(f"Failed to read state file: {e}")
            sys.exit(1)
        raise


def save_state_file(
    data: dict,
    state_file: Union[str, Path] = ".genie-forge.json",
    exit_on_error: bool = True,
) -> bool:
    """Save data to state file.

    Args:
        data: State data to save
        state_file: Path to state file
        exit_on_error: If True, exit on error. If False, raise exception.

    Returns:
        True if successful

    Raises:
        Exception: If exit_on_error is False and save fails
    """
    state_path = Path(state_file)

    try:
        state_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        if exit_on_error:
            print_error(f"Failed to save state file: {e}")
            sys.exit(1)
        raise


def get_state_environment(
    data: dict,
    env: str,
    exit_on_error: bool = True,
) -> Optional[dict]:
    """Get environment data from state, with validation.

    Args:
        data: State data dict
        env: Environment name
        exit_on_error: If True, exit if env not found. If False, return None.

    Returns:
        Environment data dict, or None if not found (when not exit_on_error)
    """
    environments: dict[str, dict[Any, Any]] = data.get("environments") or {}

    if env not in environments:
        if exit_on_error:
            print_error(f"Environment '{env}' not found in state file")
            available = list(environments.keys())
            if available:
                console.print(f"\nAvailable environments: {', '.join(available)}")
            sys.exit(1)
        return None

    result: dict[Any, Any] = environments[env]
    return result


# =============================================================================
# Config File Helpers
# =============================================================================


def load_config_file(
    file_path: Union[str, Path],
    exit_on_error: bool = True,
) -> dict:
    """Load configuration from YAML or JSON file.

    Args:
        file_path: Path to config file (.yaml, .yml, or .json)
        exit_on_error: If True, exit on error. If False, raise exception.

    Returns:
        Parsed configuration dict

    Raises:
        click.UsageError: If file format is unsupported
        Exception: If parsing fails and exit_on_error is False
    """
    import click
    import yaml

    path = Path(file_path)

    try:
        content = path.read_text(encoding="utf-8")

        if path.suffix in [".yaml", ".yml"]:
            result: dict[Any, Any] = yaml.safe_load(content) or {}
            return result
        elif path.suffix == ".json":
            result_json: dict[Any, Any] = json.loads(content)
            return result_json
        else:
            raise click.UsageError(
                f"Unsupported file format: {path.suffix}. Use .yaml, .yml, or .json"
            )
    except click.UsageError:
        raise
    except Exception as e:
        if exit_on_error:
            print_error(f"Failed to load config file: {e}")
            sys.exit(1)
        raise


def save_config_file(
    data: dict,
    file_path: Union[str, Path],
    file_format: str = "yaml",
    create_parents: bool = True,
) -> None:
    """Save configuration to YAML or JSON file.

    Args:
        data: Configuration dict to save
        file_path: Output file path
        file_format: "yaml" or "json"
        create_parents: If True, create parent directories
    """
    import yaml

    path = Path(file_path)

    if create_parents:
        path.parent.mkdir(parents=True, exist_ok=True)

    if file_format == "yaml":
        path.write_text(
            yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    else:
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


# =============================================================================
# Data Parsing Helpers
# =============================================================================


def parse_serialized_space(space: dict[str, Any]) -> dict[Any, Any]:
    """Parse the serialized_space field from a space response.

    Handles both string (JSON-encoded) and dict formats.

    Args:
        space: Space dict from API response

    Returns:
        Parsed serialized_space dict, or empty dict if not present/invalid
    """
    raw = space.get("serialized_space")
    if not raw:
        return {}

    if isinstance(raw, dict):
        result: dict[Any, Any] = raw
        return result

    try:
        parsed: dict[Any, Any] = json.loads(raw)
        return parsed
    except (json.JSONDecodeError, TypeError):
        return {}


# =============================================================================
# String Helpers
# =============================================================================


def truncate_string(value: str, max_length: int = 24, suffix: str = "...") -> str:
    """Truncate a string with suffix if it exceeds max length.

    Args:
        value: String to truncate
        max_length: Maximum length before truncation
        suffix: Suffix to add when truncated

    Returns:
        Original string or truncated string with suffix
    """
    if len(value) <= max_length:
        return value
    return value[: max_length - len(suffix)] + suffix


def sanitize_filename(title: str, max_length: int = 50) -> str:
    """Convert a title to a safe filename.

    Args:
        title: Title to convert
        max_length: Maximum filename length

    Returns:
        Safe filename (lowercase, underscores, no special chars)
    """
    import re

    # Replace spaces and special chars with underscores
    filename = re.sub(r"[^\w\s-]", "", title.lower())
    filename = re.sub(r"[\s-]+", "_", filename)
    return filename[:max_length]


def parse_comma_separated(value: str) -> list[str]:
    """Parse a comma-separated string into a list of trimmed values.

    Args:
        value: Comma-separated string

    Returns:
        List of trimmed non-empty strings
    """
    return [item.strip() for item in value.split(",") if item.strip()]


def apply_key_value_overrides(config: dict, overrides: list[str]) -> dict:
    """Apply key=value overrides to a config dict.

    Supports nested keys with dot notation (e.g., "data_sources.tables").

    Args:
        config: Base configuration dict
        overrides: List of "key=value" strings

    Returns:
        Updated config dict

    Raises:
        click.UsageError: If override format is invalid
    """
    import click

    for override in overrides:
        if "=" not in override:
            raise click.UsageError(f"Invalid --set format: '{override}'. Use key=value")

        key, value = override.split("=", 1)

        # Handle nested keys
        if "." in key:
            parts = key.split(".")
            target = config
            for part in parts[:-1]:
                if part not in target:
                    target[part] = {}
                target = target[part]
            target[parts[-1]] = value
        else:
            config[key] = value

    return config
