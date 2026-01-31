"""
Utility functions for Genie-Forge.

Provides environment detection, path management, and helper functions
for working across local machines and Databricks environments.
"""

import os
import re
from pathlib import Path
from typing import Optional, Union

# =============================================================================
# Environment Detection
# =============================================================================


def is_running_on_databricks() -> bool:
    """
    Detect if code is running on a Databricks cluster.

    Checks for the DATABRICKS_RUNTIME_VERSION environment variable
    which is set on all Databricks clusters.

    Returns:
        True if running on Databricks, False otherwise.

    Example:
        >>> if is_running_on_databricks():
        ...     print("Running on Databricks!")
        ... else:
        ...     print("Running locally")
    """
    return "DATABRICKS_RUNTIME_VERSION" in os.environ


def get_databricks_runtime_version() -> Optional[str]:
    """
    Get the Databricks Runtime version if running on Databricks.

    Returns:
        Runtime version string (e.g., "14.3") or None if not on Databricks.
    """
    return os.environ.get("DATABRICKS_RUNTIME_VERSION")


def is_running_in_notebook() -> bool:
    """
    Detect if code is running in a Databricks notebook context.

    This checks for notebook-specific environment indicators.

    Returns:
        True if running in a Databricks notebook, False otherwise.
    """
    # Check for notebook-specific indicators
    notebook_indicators = [
        "DATABRICKS_RUNTIME_VERSION",
        "DB_IS_DRIVER",
        "SPARK_HOME",
    ]
    return any(var in os.environ for var in notebook_indicators)


# =============================================================================
# Path Utilities
# =============================================================================


def get_volume_path(
    catalog: str,
    schema: str,
    volume: str,
    *paths: str,
) -> str:
    """
    Construct a Unity Catalog Volume path.

    Volume paths follow the pattern: /Volumes/<catalog>/<schema>/<volume>/<path>

    Args:
        catalog: Unity Catalog name
        schema: Schema name containing the volume
        volume: Volume name
        *paths: Additional path components to append

    Returns:
        Full Volume path string.

    Example:
        >>> get_volume_path("main", "default", "my_volume", "project", "data")
        '/Volumes/main/default/my_volume/project/data'
    """
    base_path = f"/Volumes/{catalog}/{schema}/{volume}"
    if paths:
        return f"{base_path}/{'/'.join(paths)}"
    return base_path


def is_volume_path(path: Union[str, Path]) -> bool:
    """
    Check if a path is a Unity Catalog Volume path.

    Args:
        path: Path to check

    Returns:
        True if path starts with /Volumes/, False otherwise.

    Example:
        >>> is_volume_path("/Volumes/catalog/schema/volume/file.txt")
        True
        >>> is_volume_path("/home/user/file.txt")
        False
    """
    path_str = str(path)
    return path_str.startswith("/Volumes/")


def parse_volume_path(path: Union[str, Path]) -> Optional[dict]:
    """
    Parse a Unity Catalog Volume path into components.

    Args:
        path: Volume path to parse

    Returns:
        Dictionary with keys: catalog, schema, volume, subpath
        Returns None if not a valid Volume path.

    Example:
        >>> parse_volume_path("/Volumes/main/default/my_vol/data/file.txt")
        {'catalog': 'main', 'schema': 'default', 'volume': 'my_vol', 'subpath': 'data/file.txt'}
    """
    path_str = str(path)

    # Pattern: /Volumes/<catalog>/<schema>/<volume>/<optional_subpath>
    pattern = r"^/Volumes/([^/]+)/([^/]+)/([^/]+)(?:/(.*))?$"
    match = re.match(pattern, path_str)

    if not match:
        return None

    return {
        "catalog": match.group(1),
        "schema": match.group(2),
        "volume": match.group(3),
        "subpath": match.group(4) or "",
    }


def get_default_project_path(
    project_name: str = "genie-forge",
    catalog: Optional[str] = None,
    schema: Optional[str] = None,
    volume_name: Optional[str] = None,
) -> str:
    """
    Get the default project path based on the execution environment.

    On Databricks (when catalog provided): Uses Unity Catalog Volume
    On local machine: Uses ~/.genie-forge/<project_name>

    Args:
        project_name: Name of the project folder
        catalog: Unity Catalog name (required for Databricks)
        schema: Schema name (defaults to "default")
        volume_name: Volume name (defaults to "genie_forge")

    Returns:
        Appropriate project path for the current environment.

    Example:
        >>> # On local machine
        >>> get_default_project_path("my_project")
        '/Users/you/.genie-forge/my_project'

        >>> # On Databricks with catalog config
        >>> get_default_project_path("my_project", "main", "default", "genie_forge")
        '/Volumes/main/default/genie_forge/my_project'
    """
    if is_running_on_databricks() and catalog:
        schema_name = schema or "default"
        volume = volume_name or "genie_forge"
        return get_volume_path(catalog, schema_name, volume, project_name)
    else:
        # Local machine - use home directory
        return os.path.expanduser(f"~/.genie-forge/{project_name}")


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Works with both local paths and Volume paths.

    Args:
        path: Directory path to ensure exists

    Returns:
        Path object for the directory.

    Raises:
        OSError: If directory cannot be created.
    """
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


# =============================================================================
# Project Path Configuration
# =============================================================================


class ProjectPaths:
    """
    Manages project paths for Genie-Forge.

    Automatically detects the environment and configures appropriate paths
    for configuration files, state files, and exports.

    Note: The same catalog and schema are used for both:
    - Data tables (for Genie spaces)
    - Volume storage (for config/state files)

    Example:
        >>> # Auto-detect environment
        >>> paths = ProjectPaths("my_project")
        >>> print(paths.root)
        '/Users/you/.genie-forge/my_project'

        >>> # Force Databricks Volume
        >>> paths = ProjectPaths(
        ...     "my_project",
        ...     catalog="main",
        ...     schema="default",
        ...     volume_name="genie_forge"
        ... )
        >>> print(paths.root)
        '/Volumes/main/default/genie_forge/my_project'
    """

    def __init__(
        self,
        project_name: str = "genie-forge-project",
        catalog: Optional[str] = None,
        schema: Optional[str] = None,
        volume_name: Optional[str] = None,
        base_path: Optional[str] = None,
    ):
        """
        Initialize project paths.

        Args:
            project_name: Name of the project
            catalog: Unity Catalog name (for Databricks)
            schema: Schema name (defaults to "default")
            volume_name: Volume name (defaults to "genie_forge")
            base_path: Override automatic path detection with custom base path
        """
        self.project_name = project_name
        self._catalog = catalog
        self._schema = schema or "default"
        self._volume_name = volume_name or "genie_forge"

        if base_path:
            self._root = base_path
        else:
            self._root = get_default_project_path(
                project_name,
                catalog,
                schema,
                volume_name,
            )

    @property
    def root(self) -> str:
        """Root project directory."""
        return self._root

    @property
    def catalog(self) -> Optional[str]:
        """Unity Catalog name (same for tables and volume)."""
        return self._catalog

    @property
    def schema(self) -> str:
        """Schema name (same for tables and volume)."""
        return self._schema

    @property
    def volume_name(self) -> str:
        """Volume name for file storage."""
        return self._volume_name

    @property
    def conf_dir(self) -> str:
        """Configuration directory (conf/)."""
        return f"{self._root}/conf"

    @property
    def spaces_dir(self) -> str:
        """Space configurations directory (conf/spaces/)."""
        return f"{self._root}/conf/spaces"

    @property
    def variables_dir(self) -> str:
        """Variables directory (conf/variables/)."""
        return f"{self._root}/conf/variables"

    @property
    def state_file(self) -> str:
        """State file path (.genie-forge.json)."""
        return f"{self._root}/.genie-forge.json"

    @property
    def exports_dir(self) -> str:
        """Exports directory."""
        return f"{self._root}/exports"

    @property
    def is_databricks(self) -> bool:
        """Whether running on Databricks."""
        return is_running_on_databricks()

    @property
    def is_volume_path(self) -> bool:
        """Whether using a Volume path."""
        return is_volume_path(self._root)

    def ensure_structure(self) -> None:
        """
        Create the standard project directory structure.

        Creates:
        - conf/spaces/
        - conf/variables/
        """
        ensure_directory(self.spaces_dir)
        ensure_directory(self.variables_dir)

    def get_config_path(self, name: str) -> str:
        """Get path for a space configuration file."""
        return f"{self.spaces_dir}/{name}.yaml"

    def get_export_path(self, name: str, format: str = "yaml") -> str:
        """Get path for an exported configuration file."""
        return f"{self.exports_dir}/{name}.{format}"

    def __repr__(self) -> str:
        env = "Databricks" if self.is_databricks else "Local"
        path_type = "Volume" if self.is_volume_path else "Filesystem"
        return f"ProjectPaths(root='{self._root}', env={env}, type={path_type})"


# =============================================================================
# String/Naming Utilities
# =============================================================================


def sanitize_name(name: str, max_length: int = 50) -> str:
    """
    Sanitize a name for use as a filename or identifier.

    Removes special characters, converts spaces to underscores,
    and truncates to max length.

    Args:
        name: Name to sanitize
        max_length: Maximum length of result

    Returns:
        Sanitized name string.

    Example:
        >>> sanitize_name("My Sales Analytics Space!")
        'my_sales_analytics_space'
    """
    # Lowercase and replace spaces with underscores
    result = name.lower().strip()
    result = re.sub(r"\s+", "_", result)

    # Remove special characters (keep alphanumeric and underscore)
    result = re.sub(r"[^\w]", "", result)

    # Collapse multiple underscores
    result = re.sub(r"_+", "_", result)

    # Strip leading/trailing underscores
    result = result.strip("_")

    # Truncate
    if len(result) > max_length:
        result = result[:max_length].rstrip("_")

    return result or "unnamed"
