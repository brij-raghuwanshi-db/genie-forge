"""
Genie-Forge: Metadata-driven framework for programmatic Databricks Genie space management.

This package provides a Terraform-like workflow for managing Databricks Genie spaces
through YAML configuration files with support for:
- YAML/JSON configuration with variable substitution
- Plan/Apply/Destroy workflow
- State tracking via .genie-forge.json
- Cross-environment deployments (dev/staging/prod)
- Bulk operations with parallel execution

Example usage:
    from genie_forge import GenieClient, SpaceConfig, StateManager

    # Create a client
    client = GenieClient(profile="GENIE_PROFILE")

    # Load and deploy spaces
    from genie_forge.parsers import MetadataParser
    parser = MetadataParser()
    configs = parser.parse("conf/spaces/sales.yaml", env="dev")

    # Use state manager for plan/apply
    state = StateManager()
    plan = state.plan(configs, client)
    state.apply(plan, client)
"""

import logging
import re

from genie_forge.__about__ import __version__


class SensitiveDataFilter(logging.Filter):
    """Filter that masks sensitive data in log messages.

    Masks tokens, passwords, and other sensitive patterns to prevent
    accidental exposure in logs.
    """

    # Patterns for sensitive data that should be masked
    SENSITIVE_PATTERNS = [
        (re.compile(r"dapi[a-f0-9]{32}", re.IGNORECASE), "dapi****"),
        (re.compile(r"(token[:\s=]+)['\"]?([a-zA-Z0-9_-]{20,})['\"]?", re.IGNORECASE), r"\1****"),
        (re.compile(r"(Bearer\s+)[a-zA-Z0-9_.-]+", re.IGNORECASE), r"\1****"),
        (re.compile(r"(password[:\s=]+)['\"]?([^\s'\"]+)['\"]?", re.IGNORECASE), r"\1****"),
        (re.compile(r"(secret[:\s=]+)['\"]?([^\s'\"]+)['\"]?", re.IGNORECASE), r"\1****"),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        """Mask sensitive data in the log record message."""
        if record.msg:
            msg = str(record.msg)
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                msg = pattern.sub(replacement, msg)
            record.msg = msg

        # Also mask args if present
        if record.args:
            masked_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    for pattern, replacement in self.SENSITIVE_PATTERNS:
                        arg = pattern.sub(replacement, arg)
                masked_args.append(arg)
            record.args = tuple(masked_args)

        return True  # Always allow the record through (after masking)


# Imports placed after SensitiveDataFilter to avoid circular imports
from genie_forge.client import GenieClient  # noqa: E402
from genie_forge.models import (  # noqa: E402
    ColumnConfig,
    DataSources,
    ExampleQuestionSQL,
    Instructions,
    JoinSpec,
    SpaceConfig,
    SqlFunction,
    TableConfig,
    TextInstruction,
)
from genie_forge.serializer import space_to_yaml  # noqa: E402
from genie_forge.state import StateManager  # noqa: E402
from genie_forge.utils import (  # noqa: E402
    ProjectPaths,
    ensure_directory,
    get_databricks_runtime_version,
    get_default_project_path,
    get_volume_path,
    is_running_in_notebook,
    is_running_on_databricks,
    is_volume_path,
    parse_volume_path,
    sanitize_name,
)

__all__ = [
    "__version__",
    # Security
    "SensitiveDataFilter",
    # Models
    "SpaceConfig",
    "TableConfig",
    "ColumnConfig",
    "Instructions",
    "TextInstruction",
    "ExampleQuestionSQL",
    "SqlFunction",
    "JoinSpec",
    "DataSources",
    # Client
    "GenieClient",
    # State
    "StateManager",
    # Serializer
    "space_to_yaml",
    # Utils
    "ProjectPaths",
    "is_running_on_databricks",
    "is_running_in_notebook",
    "get_databricks_runtime_version",
    "get_volume_path",
    "is_volume_path",
    "parse_volume_path",
    "get_default_project_path",
    "ensure_directory",
    "sanitize_name",
]

# Setup logging with sensitive data filtering
logger = logging.getLogger(__name__)

# Apply sensitive data filter to all genie_forge loggers
_sensitive_filter = SensitiveDataFilter()
logging.getLogger("genie_forge").addFilter(_sensitive_filter)
logging.getLogger("genie_forge.client").addFilter(_sensitive_filter)
logging.getLogger("genie_forge.auth").addFilter(_sensitive_filter)
logging.getLogger("genie_forge.state").addFilter(_sensitive_filter)


def _register_product() -> None:
    """Register product with Databricks SDK for usage tracking.

    This follows the standard Databricks Labs pattern used by UCX, DQX, etc.
    User-Agent headers are sent with every API request, allowing Databricks
    to track product adoption server-side.

    This is non-invasive:
    - No customer data is collected
    - No external telemetry endpoints
    - Only product name and version in HTTP headers
    """
    try:
        import databricks.sdk.useragent as ua

        ua.with_product("genie-forge", __version__)
        ua.with_extra("genie-forge", __version__)
        logger.debug(f"Registered genie-forge/{__version__} with SDK user-agent")
    except Exception as e:
        # Silent fallback - never fail due to telemetry
        logger.debug(f"Could not register user-agent (non-critical): {e}")


# Initialize on import
_register_product()
