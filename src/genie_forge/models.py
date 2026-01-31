"""
Pydantic models for Genie space configuration.

These models map to the Genie Space Serialized Format (version 2):
{
  "version": 2,
  "config": { "sample_questions": [{"id": "...", "question": ["..."]}] },
  "data_sources": { "tables": [...] },
  "instructions": {
    "text_instructions": [...],
    "example_question_sqls": [...],
    "join_specs": [...],
    "sql_snippets": { "filters": [...], "expressions": [...], "measures": [...] }
  },
  "benchmarks": {...}
}
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, field_validator


def _utc_now() -> datetime:
    """Return current UTC time (timezone-aware)."""
    return datetime.now(timezone.utc)


class SpaceStatus(str, Enum):
    """Status of a Genie space in the state file."""

    PENDING = "PENDING"
    APPLIED = "APPLIED"
    MODIFIED = "MODIFIED"
    DRIFT = "DRIFT"
    DESTROYED = "DESTROYED"


# =============================================================================
# Column and Table Configuration
# =============================================================================


class ColumnConfig(BaseModel):
    """Configuration for a table column in Genie space.

    Matches the Genie API column_configs structure exactly.
    """

    column_name: str = Field(..., description="Name of the column")
    description: list[str] = Field(
        default_factory=list, description="Human-readable description (list for API compatibility)"
    )
    synonyms: list[str] = Field(
        default_factory=list, description="Alternative names for the column"
    )
    enable_format_assistance: bool = Field(
        default=False, description="Enable format assistance for this column"
    )
    enable_entity_matching: bool = Field(
        default=False, description="Enable entity matching for this column"
    )
    build_value_dictionary: bool = Field(
        default=False, description="Build a value dictionary for this column"
    )
    get_example_values: bool = Field(
        default=False, description="Get example values for this column"
    )

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, v: Any) -> list[str]:
        """Accept both string and list formats for backward compatibility."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v else []
        return list(v)


class TableConfig(BaseModel):
    """Configuration for a table in Genie space."""

    identifier: str = Field(..., description="Full table path: catalog.schema.table")
    description: list[str] = Field(
        default_factory=list, description="List of description lines for the table"
    )
    column_configs: list[ColumnConfig] = Field(
        default_factory=list, description="Column-level configurations"
    )

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, v: str) -> str:
        """Validate table identifier format."""
        parts = v.split(".")
        if len(parts) != 3:
            raise ValueError(f"Table identifier must be in format 'catalog.schema.table', got: {v}")
        return v

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, v: Any) -> list[str]:
        """Accept both string and list formats for backward compatibility."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v else []
        return list(v)


# =============================================================================
# Sample Questions
# =============================================================================


class SampleQuestion(BaseModel):
    """A sample question shown in the Genie UI.

    Matches the Genie API sample_questions structure.
    """

    id: Optional[str] = Field(None, description="Unique identifier (assigned by Databricks)")
    question: list[str] = Field(..., description="The question text(s)")

    @field_validator("question", mode="before")
    @classmethod
    def normalize_question(cls, v: Any) -> list[str]:
        """Accept both string and list formats for backward compatibility."""
        if isinstance(v, str):
            return [v]
        return list(v)


# =============================================================================
# Instructions - Text Instructions
# =============================================================================


class TextInstruction(BaseModel):
    """A text instruction for Genie.

    Matches the Genie API text_instructions structure.
    """

    id: Optional[str] = Field(None, description="Unique identifier (assigned by Databricks)")
    content: list[str] = Field(..., description="The instruction text(s)")

    @field_validator("content", mode="before")
    @classmethod
    def normalize_content(cls, v: Any) -> list[str]:
        """Accept both string and list formats for backward compatibility."""
        if isinstance(v, str):
            return [v]
        return list(v)


# =============================================================================
# Instructions - Example Question SQLs (with Parameters)
# =============================================================================


class ParameterDefaultValue(BaseModel):
    """Default value for a parameter in example SQL."""

    values: list[str] = Field(default_factory=list, description="Default value(s)")


class ParameterConfig(BaseModel):
    """Configuration for a parameter in an example question SQL.

    Matches the Genie API parameters structure in example_question_sqls.
    """

    name: str = Field(..., description="Parameter name")
    type_hint: str = Field(default="STRING", description="Type hint: STRING, INT, FLOAT, etc.")
    description: list[str] = Field(default_factory=list, description="Description of the parameter")
    default_value: Optional[ParameterDefaultValue] = Field(
        None, description="Default value configuration"
    )

    @field_validator("description", mode="before")
    @classmethod
    def normalize_description(cls, v: Any) -> list[str]:
        """Accept both string and list formats for backward compatibility."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v else []
        return list(v)


class ExampleQuestionSQL(BaseModel):
    """An example question with its expected SQL.

    Matches the Genie API example_question_sqls structure exactly,
    including parameters and usage_guidance.
    """

    id: Optional[str] = Field(None, description="Unique identifier (assigned by Databricks)")
    question: list[str] = Field(..., description="The natural language question(s)")
    sql: list[str] = Field(..., description="The expected SQL query(ies)")
    parameters: list[ParameterConfig] = Field(
        default_factory=list, description="Parameters for parameterized SQL"
    )
    usage_guidance: list[str] = Field(
        default_factory=list, description="Guidance on when to use this example"
    )

    @field_validator("question", mode="before")
    @classmethod
    def normalize_question(cls, v: Any) -> list[str]:
        """Accept both string and list formats for backward compatibility."""
        if isinstance(v, str):
            return [v]
        return list(v)

    @field_validator("sql", mode="before")
    @classmethod
    def normalize_sql(cls, v: Any) -> list[str]:
        """Accept both string and list formats for backward compatibility."""
        if isinstance(v, str):
            return [v]
        return list(v)

    @field_validator("usage_guidance", mode="before")
    @classmethod
    def normalize_usage_guidance(cls, v: Any) -> list[str]:
        """Accept both string and list formats for backward compatibility."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v else []
        return list(v)


# =============================================================================
# Instructions - SQL Functions
# =============================================================================


class SqlFunction(BaseModel):
    """A SQL function available to Genie."""

    identifier: str = Field(..., description="Full function path: catalog.schema.function")
    description: Optional[str] = Field(None, description="Description of what the function does")
    id: Optional[str] = Field(
        None, description="UUID for the function (auto-generated if not provided)"
    )


# =============================================================================
# Instructions - Join Specs
# =============================================================================


class JoinTableRef(BaseModel):
    """Reference to a table in a join specification.

    Matches the Genie API join_specs left/right structure.
    """

    identifier: str = Field(..., description="Full table path: catalog.schema.table")
    alias: Optional[str] = Field(None, description="Alias for the table in the join")


class JoinSpec(BaseModel):
    """Specification for how tables should be joined.

    Matches the Genie API join_specs structure exactly.
    The relationship type (e.g., MANY_TO_MANY) is embedded in the sql list
    as a comment like: --rt=FROM_RELATIONSHIP_TYPE_MANY_TO_MANY--
    """

    id: Optional[str] = Field(None, description="Unique identifier (assigned by Databricks)")
    left: JoinTableRef = Field(..., description="Left table reference")
    right: JoinTableRef = Field(..., description="Right table reference")
    sql: list[str] = Field(..., description="Join SQL condition(s) and relationship type")
    instruction: list[str] = Field(
        default_factory=list, description="Instructions for using this join"
    )

    @field_validator("sql", mode="before")
    @classmethod
    def normalize_sql(cls, v: Any) -> list[str]:
        """Accept both string and list formats for backward compatibility."""
        if isinstance(v, str):
            return [v]
        return list(v)

    @field_validator("instruction", mode="before")
    @classmethod
    def normalize_instruction(cls, v: Any) -> list[str]:
        """Accept both string and list formats for backward compatibility."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v else []
        return list(v)


# =============================================================================
# Instructions - SQL Snippets (Filters, Expressions, Measures)
# =============================================================================


class SqlSnippet(BaseModel):
    """A SQL snippet (filter, expression, or measure).

    Matches the Genie API sql_snippets structure for filters, expressions, and measures.
    """

    id: Optional[str] = Field(None, description="Unique identifier (assigned by Databricks)")
    sql: list[str] = Field(..., description="The SQL expression(s)")
    display_name: str = Field(..., description="Display name shown in UI")
    instruction: list[str] = Field(
        default_factory=list, description="Instructions for when to use this snippet"
    )
    synonyms: list[str] = Field(
        default_factory=list, description="Alternative names/triggers for this snippet"
    )

    @field_validator("sql", mode="before")
    @classmethod
    def normalize_sql(cls, v: Any) -> list[str]:
        """Accept both string and list formats for backward compatibility."""
        if isinstance(v, str):
            return [v]
        return list(v)

    @field_validator("instruction", mode="before")
    @classmethod
    def normalize_instruction(cls, v: Any) -> list[str]:
        """Accept both string and list formats for backward compatibility."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v else []
        return list(v)


class SqlSnippets(BaseModel):
    """Container for all SQL snippets in a Genie space.

    Matches the Genie API sql_snippets structure with filters, expressions, and measures.
    """

    filters: list[SqlSnippet] = Field(default_factory=list, description="SQL filter snippets")
    expressions: list[SqlSnippet] = Field(
        default_factory=list, description="SQL expression snippets"
    )
    measures: list[SqlSnippet] = Field(default_factory=list, description="SQL measure snippets")


# =============================================================================
# Instructions Container
# =============================================================================


class Instructions(BaseModel):
    """All instruction types for a Genie space.

    Matches the Genie API instructions structure exactly.
    """

    text_instructions: list[TextInstruction] = Field(
        default_factory=list, description="Text instructions for Genie"
    )
    example_question_sqls: list[ExampleQuestionSQL] = Field(
        default_factory=list, description="Example questions with SQL"
    )
    sql_functions: list[SqlFunction] = Field(
        default_factory=list, description="SQL functions available to Genie"
    )
    join_specs: list[JoinSpec] = Field(default_factory=list, description="Join specifications")
    sql_snippets: SqlSnippets = Field(
        default_factory=SqlSnippets, description="SQL snippets (filters, expressions, measures)"
    )


# =============================================================================
# Benchmarks
# =============================================================================


class BenchmarkQuestion(BaseModel):
    """A benchmark question for testing Genie accuracy."""

    question: str = Field(..., description="The question to ask")
    expected_sql: str = Field(..., description="The expected SQL response")


class Benchmarks(BaseModel):
    """Benchmarks for testing Genie space accuracy."""

    questions: list[BenchmarkQuestion] = Field(
        default_factory=list, description="Benchmark questions"
    )


# =============================================================================
# Data Sources
# =============================================================================


class DataSources(BaseModel):
    """Data sources configuration for a Genie space."""

    tables: list[TableConfig] = Field(default_factory=list, description="Tables available to Genie")


# =============================================================================
# Main Space Configuration
# =============================================================================


class SpaceConfig(BaseModel):
    """Complete configuration for a Genie space.

    This is the main model that represents a Genie space configuration,
    either loaded from YAML or constructed programmatically.

    Matches the Genie API serialized_space format (version 2).
    """

    # Identity
    space_id: str = Field(..., description="Logical ID for this space (used in state tracking)")
    title: str = Field(..., description="Display title for the space")

    # Deployment settings
    warehouse_id: str = Field(..., description="SQL warehouse ID for queries")
    parent_path: Optional[str] = Field(
        None, description="Workspace path where space will be created"
    )

    # Sample questions (shown in Genie UI)
    sample_questions: list[Union[SampleQuestion, str]] = Field(
        default_factory=list, description="Sample questions shown to users"
    )

    # Data sources
    data_sources: DataSources = Field(
        default_factory=DataSources, description="Data sources configuration"
    )

    # Instructions
    instructions: Instructions = Field(
        default_factory=Instructions, description="Instructions for Genie"
    )

    # Benchmarks (optional)
    benchmarks: Optional[Benchmarks] = Field(None, description="Benchmark tests")

    # Metadata
    version: int = Field(default=2, description="Config version (2 = current API format)")
    author: Optional[str] = Field(None, description="Author of this configuration")
    description: Optional[str] = Field(None, description="Description of this space")
    tags: list[str] = Field(default_factory=list, description="Tags for organizing spaces")

    @field_validator("sample_questions", mode="before")
    @classmethod
    def normalize_sample_questions(cls, v: Any) -> list[Union[SampleQuestion, str]]:
        """Accept both string list and SampleQuestion list formats."""
        if v is None:
            return []
        result = []
        for item in v:
            if isinstance(item, str):
                # Keep as string for backward compatibility - will be converted during serialization
                result.append(item)
            elif isinstance(item, dict):
                result.append(SampleQuestion(**item))
            elif isinstance(item, SampleQuestion):
                result.append(item)
            else:
                result.append(str(item))
        return result

    def get_sample_questions_as_objects(self) -> list[SampleQuestion]:
        """Get sample questions as SampleQuestion objects."""
        result = []
        for item in self.sample_questions:
            if isinstance(item, str):
                result.append(SampleQuestion(question=[item]))
            else:
                result.append(item)
        return result

    def config_hash(self) -> str:
        """Generate a hash of the configuration for change detection.

        Returns a SHA-256 hash of the normalized configuration.
        """
        # Create a sorted, normalized representation
        data = self.model_dump(exclude={"space_id"}, exclude_none=True)
        normalized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def get_table_identifiers(self) -> list[str]:
        """Get list of all table identifiers."""
        return [t.identifier for t in self.data_sources.tables]

    def get_function_identifiers(self) -> list[str]:
        """Get list of all function identifiers."""
        return [f.identifier for f in self.instructions.sql_functions]

    @classmethod
    def minimal(
        cls,
        space_id: str,
        title: str,
        warehouse_id: str,
        tables: list[str],
        parent_path: Optional[str] = None,
    ) -> SpaceConfig:
        """Create a minimal space configuration.

        Args:
            space_id: Logical ID for the space
            title: Display title
            warehouse_id: SQL warehouse ID
            tables: List of table identifiers (catalog.schema.table)
            parent_path: Optional workspace path

        Returns:
            A minimal SpaceConfig with just the required fields
        """
        return cls(
            space_id=space_id,
            title=title,
            warehouse_id=warehouse_id,
            parent_path=parent_path,
            data_sources=DataSources(tables=[TableConfig(identifier=t) for t in tables]),
        )


# =============================================================================
# State Management Models
# =============================================================================


class SpaceState(BaseModel):
    """State of a deployed Genie space."""

    logical_id: str = Field(..., description="Logical ID from configuration")
    databricks_space_id: Optional[str] = Field(
        None, description="Databricks-assigned space ID (alphanumeric)"
    )
    title: str = Field(..., description="Title at time of deployment")
    config_hash: str = Field(..., description="Hash of current YAML config")
    applied_hash: Optional[str] = Field(None, description="Hash when last applied")
    status: SpaceStatus = Field(default=SpaceStatus.PENDING, description="Current status")
    last_applied: Optional[datetime] = Field(None, description="When last applied")
    error: Optional[str] = Field(None, description="Error message if failed")


class EnvironmentState(BaseModel):
    """State for a specific environment (dev/staging/prod)."""

    workspace_url: str = Field(..., description="Workspace URL for this environment")
    last_applied: Optional[datetime] = Field(None, description="Last apply timestamp")
    spaces: dict[str, SpaceState] = Field(
        default_factory=dict, description="Space states keyed by logical_id"
    )


class ProjectState(BaseModel):
    """Complete state file for a genie-forge project."""

    version: str = Field(default="1.0", description="State file version")
    project_id: str = Field(..., description="Project identifier")
    project_name: Optional[str] = Field(None, description="Human-readable project name")
    created_at: datetime = Field(default_factory=_utc_now, description="Creation timestamp")
    environments: dict[str, EnvironmentState] = Field(
        default_factory=dict, description="Environment states keyed by env name"
    )


# =============================================================================
# Plan Models
# =============================================================================


class PlanAction(str, Enum):
    """Action to take for a space."""

    CREATE = "CREATE"
    UPDATE = "UPDATE"
    DESTROY = "DESTROY"
    NO_CHANGE = "NO_CHANGE"


class PlanItem(BaseModel):
    """An item in a deployment plan."""

    logical_id: str = Field(..., description="Logical ID of the space")
    action: PlanAction = Field(..., description="Action to take")
    config: Optional[SpaceConfig] = Field(None, description="Configuration for create/update")
    current_state: Optional[SpaceState] = Field(None, description="Current state if exists")
    changes: list[str] = Field(default_factory=list, description="List of changes")


class Plan(BaseModel):
    """A deployment plan showing what will be created/updated/destroyed."""

    environment: str = Field(..., description="Target environment")
    timestamp: datetime = Field(default_factory=_utc_now, description="Plan timestamp")
    items: list[PlanItem] = Field(default_factory=list, description="Plan items")

    @property
    def creates(self) -> list[PlanItem]:
        """Items to create."""
        return [i for i in self.items if i.action == PlanAction.CREATE]

    @property
    def updates(self) -> list[PlanItem]:
        """Items to update."""
        return [i for i in self.items if i.action == PlanAction.UPDATE]

    @property
    def destroys(self) -> list[PlanItem]:
        """Items to destroy."""
        return [i for i in self.items if i.action == PlanAction.DESTROY]

    @property
    def no_changes(self) -> list[PlanItem]:
        """Items with no changes."""
        return [i for i in self.items if i.action == PlanAction.NO_CHANGE]

    @property
    def has_changes(self) -> bool:
        """Whether the plan has any changes."""
        return len(self.creates) > 0 or len(self.updates) > 0 or len(self.destroys) > 0

    def summary(self) -> str:
        """Get a summary of the plan."""
        return (
            f"Plan: {len(self.creates)} to create, {len(self.updates)} to update, "
            f"{len(self.destroys)} to destroy, {len(self.no_changes)} unchanged"
        )
