"""
Configuration parsers for Genie-Forge.

Supports:
- YAML and JSON configuration files
- Variable substitution (${var_name})
- Environment-specific variable resolution
- Reference resolution (file:// and #/ references)
- Full Genie API structure (version 2) including sql_snippets, parameters, etc.

MVP scope: Basic YAML loading with simple variable substitution.
Full product will add: Nested variables, reference resolution, schema validation.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional, Union

import yaml

from genie_forge.models import (
    BenchmarkQuestion,
    Benchmarks,
    ColumnConfig,
    DataSources,
    ExampleQuestionSQL,
    Instructions,
    JoinSpec,
    JoinTableRef,
    ParameterConfig,
    ParameterDefaultValue,
    SampleQuestion,
    SpaceConfig,
    SqlFunction,
    SqlSnippet,
    SqlSnippets,
    TableConfig,
    TextInstruction,
)

logger = logging.getLogger(__name__)


class ParserError(Exception):
    """Raised when parsing fails."""

    pass


class VariableResolver:
    """Resolves ${variable} patterns in configuration.

    Variables are resolved from:
    1. Provided variables dict
    2. Environment variables
    3. Environment-specific configuration
    """

    # Pattern for ${variable_name}
    VAR_PATTERN = re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

    def __init__(
        self,
        variables: Optional[dict[str, str]] = None,
        env: str = "dev",
        use_env_vars: bool = True,
    ):
        """Initialize the variable resolver.

        Args:
            variables: Dict of variable name -> value
            env: Current environment name (dev, staging, prod)
            use_env_vars: Whether to use environment variables as fallback
        """
        self.variables = variables or {}
        self.env = env
        self.use_env_vars = use_env_vars

        # Add default env variable
        self.variables.setdefault("env", env)

    def resolve(self, value: Any) -> Any:
        """Resolve variables in a value recursively.

        Args:
            value: Value that may contain ${variable} patterns

        Returns:
            Value with variables resolved
        """
        if isinstance(value, str):
            return self._resolve_string(value)
        elif isinstance(value, dict):
            return {k: self.resolve(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self.resolve(item) for item in value]
        return value

    def _resolve_string(self, s: str) -> str:
        """Resolve variables in a string."""

        def replacer(match: re.Match) -> str:
            var_name = match.group(1)
            return self._get_variable(var_name, match.group(0))

        return self.VAR_PATTERN.sub(replacer, s)

    def _get_variable(self, name: str, default: str) -> str:
        """Get a variable value.

        Args:
            name: Variable name
            default: Default value if not found

        Returns:
            Variable value or default
        """
        # Check explicit variables first
        if name in self.variables:
            return str(self.variables[name])

        # Check environment variables
        if self.use_env_vars:
            env_value = os.environ.get(name)
            if env_value is not None:
                return env_value

        # Return original placeholder if not found (will cause validation error)
        logger.warning(f"Variable '{name}' not found, keeping placeholder")
        return default


class MetadataParser:
    """Parser for Genie space configuration files.

    Supports YAML and JSON formats with variable substitution.
    Handles full Genie API structure (version 2) including:
    - SQL snippets (filters, expressions, measures)
    - Parameters in example questions
    - Join specs with aliases
    - Entity matching and format assistance flags

    Example:
        parser = MetadataParser()

        # Load single file
        configs = parser.parse("conf/spaces/sales.yaml", env="dev")

        # Load directory
        configs = parser.parse_directory("conf/spaces/", env="dev")
    """

    def __init__(
        self,
        variables: Optional[dict[str, str]] = None,
        env: str = "dev",
    ):
        """Initialize the parser.

        Args:
            variables: Variable overrides
            env: Target environment
        """
        self.variables = variables or {}
        self.env = env

    def parse(
        self,
        config_path: Union[str, Path],
        env: Optional[str] = None,
        variables: Optional[dict[str, str]] = None,
    ) -> list[SpaceConfig]:
        """Parse a configuration file.

        Args:
            config_path: Path to YAML or JSON file
            env: Environment name (overrides instance default)
            variables: Additional variables (merged with instance variables)

        Returns:
            List of SpaceConfig objects

        Raises:
            ParserError: If parsing fails
        """
        path = Path(config_path)
        if not path.exists():
            raise ParserError(f"Config file not found: {path}")

        # Merge variables
        merged_vars = {**self.variables, **(variables or {})}
        current_env = env or self.env

        # Load environment config if exists
        env_vars = self._load_env_config(path.parent, current_env)
        merged_vars = {**env_vars, **merged_vars}

        # Create resolver
        resolver = VariableResolver(merged_vars, current_env)

        # Load and parse file
        raw_data = self._load_file(path)

        # Resolve variables
        resolved_data = resolver.resolve(raw_data)

        # Convert to SpaceConfig objects
        return self._to_space_configs(resolved_data)

    def parse_directory(
        self,
        directory: Union[str, Path],
        env: Optional[str] = None,
        variables: Optional[dict[str, str]] = None,
        pattern: str = "*.yaml",
    ) -> list[SpaceConfig]:
        """Parse all configuration files in a directory.

        Args:
            directory: Directory containing config files
            env: Environment name
            variables: Additional variables
            pattern: Glob pattern for files (default: *.yaml)

        Returns:
            List of all SpaceConfig objects from all files
        """
        dir_path = Path(directory)
        if not dir_path.is_dir():
            raise ParserError(f"Directory not found: {dir_path}")

        configs: list[SpaceConfig] = []
        for file_path in sorted(dir_path.glob(pattern)):
            if file_path.is_file():
                try:
                    file_configs = self.parse(file_path, env, variables)
                    configs.extend(file_configs)
                except Exception as e:
                    logger.error(f"Failed to parse {file_path}: {e}")
                    raise

        # Also check for JSON files
        if pattern == "*.yaml":
            for file_path in sorted(dir_path.glob("*.json")):
                if file_path.is_file():
                    try:
                        file_configs = self.parse(file_path, env, variables)
                        configs.extend(file_configs)
                    except Exception as e:
                        logger.error(f"Failed to parse {file_path}: {e}")
                        raise

        return configs

    def validate(self, config_path: Union[str, Path]) -> list[str]:
        """Validate a configuration file without resolving variables.

        Args:
            config_path: Path to config file

        Returns:
            List of validation errors (empty if valid)
        """
        errors: list[str] = []
        path = Path(config_path)

        if not path.exists():
            return [f"File not found: {path}"]

        try:
            raw_data = self._load_file(path)
        except Exception as e:
            return [f"Failed to load file: {e}"]

        # Check structure
        if not isinstance(raw_data, dict):
            return ["Config must be a dictionary"]

        # Check for spaces key
        if "spaces" not in raw_data and "space_id" not in raw_data:
            errors.append("Config must have 'spaces' list or be a single space config")

        # Get spaces list
        if "spaces" in raw_data:
            spaces = raw_data["spaces"]
            if not isinstance(spaces, list):
                return ["'spaces' must be a list"]
        else:
            # Single space config
            spaces = [raw_data]

        # Validate each space
        for i, space in enumerate(spaces):
            space_errors = self._validate_space(space, i)
            errors.extend(space_errors)

        return errors

    def _load_file(self, path: Path) -> dict:
        """Load a YAML or JSON file."""
        content = path.read_text(encoding="utf-8")

        if path.suffix.lower() in (".yaml", ".yml"):
            try:
                data = yaml.safe_load(content)
            except yaml.YAMLError as e:
                raise ParserError(f"Invalid YAML in {path}: {e}")
        elif path.suffix.lower() == ".json":
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                raise ParserError(f"Invalid JSON in {path}: {e}")
        else:
            # Try YAML first, then JSON
            try:
                data = yaml.safe_load(content)
            except Exception:
                try:
                    data = json.loads(content)
                except Exception as e:
                    raise ParserError(f"Could not parse {path} as YAML or JSON: {e}")

        return data or {}

    def _load_env_config(self, base_path: Path, env: str) -> dict[str, str]:
        """Load environment-specific variables from conf/environments/{env}.yaml."""
        # Look for environments directory
        env_paths = [
            base_path / "environments" / f"{env}.yaml",
            base_path.parent / "environments" / f"{env}.yaml",
            base_path / f"{env}.yaml",
        ]

        for env_path in env_paths:
            if env_path.exists():
                try:
                    data = self._load_file(env_path)
                    # Flatten variables
                    variables = data.get("variables", {})
                    # Also get workspace settings
                    if "workspace_url" in data:
                        variables["workspace_url"] = data["workspace_url"]
                    if "warehouse_id" in data:
                        variables["warehouse_id"] = data["warehouse_id"]
                    return dict(variables)
                except Exception as e:
                    logger.warning(f"Failed to load env config {env_path}: {e}")

        return {}

    def _validate_space(self, space: dict, index: int) -> list[str]:
        """Validate a single space configuration."""
        errors: list[str] = []
        prefix = f"spaces[{index}]"

        # Required fields
        required = ["space_id", "title", "warehouse_id"]
        for field in required:
            if field not in space:
                errors.append(f"{prefix}: Missing required field '{field}'")

        # Validate data_sources
        if "data_sources" in space:
            ds = space["data_sources"]
            if "tables" in ds:
                for j, table in enumerate(ds["tables"]):
                    if "identifier" not in table:
                        errors.append(f"{prefix}.data_sources.tables[{j}]: Missing 'identifier'")

        return errors

    def _to_space_configs(self, data: dict) -> list[SpaceConfig]:
        """Convert parsed data to SpaceConfig objects."""
        configs: list[SpaceConfig] = []

        # Handle single space vs list of spaces
        if "spaces" in data:
            spaces = data["spaces"]
        else:
            # Single space config
            spaces = [data]

        for space_data in spaces:
            try:
                config = self._dict_to_space_config(space_data)
                configs.append(config)
            except Exception as e:
                space_id = space_data.get("space_id", "unknown")
                raise ParserError(f"Failed to parse space '{space_id}': {e}")

        return configs

    def _dict_to_space_config(self, data: dict) -> SpaceConfig:
        """Convert a dictionary to a SpaceConfig object."""
        # Build data sources
        data_sources = self._parse_data_sources(data.get("data_sources", {}))

        # Build instructions
        instructions = self._parse_instructions(data.get("instructions", {}))

        # Build benchmarks
        benchmarks = None
        if "benchmarks" in data:
            benchmarks = self._parse_benchmarks(data["benchmarks"])

        # Parse sample questions (handle both string and object formats)
        sample_questions = self._parse_sample_questions(data.get("sample_questions", []))

        return SpaceConfig(
            space_id=data["space_id"],
            title=data["title"],
            warehouse_id=data["warehouse_id"],
            parent_path=data.get("parent_path"),
            sample_questions=sample_questions,
            data_sources=data_sources,
            instructions=instructions,
            benchmarks=benchmarks,
            version=data.get("version", 2),
            author=data.get("author"),
            description=data.get("description"),
            tags=data.get("tags", []),
        )

    def _parse_sample_questions(self, data: list) -> list[Union[SampleQuestion, str]]:
        """Parse sample questions from list (handles both string and object formats)."""
        result: list[Union[SampleQuestion, str]] = []
        for item in data:
            if isinstance(item, str):
                result.append(item)
            elif isinstance(item, dict):
                result.append(
                    SampleQuestion(
                        id=item.get("id"),
                        question=item.get("question", []),
                    )
                )
        return result

    def _parse_data_sources(self, data: dict) -> DataSources:
        """Parse data sources from dict with full column config support."""
        tables = []
        for table_data in data.get("tables", []):
            columns = []
            for col_data in table_data.get("column_configs", []):
                columns.append(
                    ColumnConfig(
                        column_name=col_data["column_name"],
                        description=col_data.get("description", []),
                        synonyms=col_data.get("synonyms", []),
                        enable_format_assistance=col_data.get("enable_format_assistance", False),
                        enable_entity_matching=col_data.get("enable_entity_matching", False),
                    )
                )

            tables.append(
                TableConfig(
                    identifier=table_data["identifier"],
                    description=table_data.get("description", []),
                    column_configs=columns,
                )
            )

        return DataSources(tables=tables)

    def _parse_instructions(self, data: dict) -> Instructions:
        """Parse instructions from dict with full API support."""
        # Text instructions
        text_instructions = []
        for item in data.get("text_instructions", []):
            if isinstance(item, dict):
                text_instructions.append(
                    TextInstruction(
                        id=item.get("id"),
                        content=item.get("content", []),
                    )
                )
            elif isinstance(item, str):
                text_instructions.append(TextInstruction(content=[item]))

        # Example question SQLs with parameters and usage_guidance
        example_sqls = []
        for item in data.get("example_question_sqls", []):
            parameters = self._parse_parameters(item.get("parameters", []))
            example_sqls.append(
                ExampleQuestionSQL(
                    id=item.get("id"),
                    question=item.get("question", []),
                    sql=item.get("sql", []),
                    parameters=parameters,
                    usage_guidance=item.get("usage_guidance", []),
                )
            )

        # SQL functions
        sql_functions = []
        for item in data.get("sql_functions", []):
            if isinstance(item, dict):
                sql_functions.append(
                    SqlFunction(
                        identifier=item["identifier"],
                        description=item.get("description"),
                    )
                )
            elif isinstance(item, str):
                sql_functions.append(SqlFunction(identifier=item))

        # Join specs with full structure
        join_specs = []
        for item in data.get("join_specs", []):
            join_specs.append(self._parse_join_spec(item))

        # SQL snippets
        sql_snippets = self._parse_sql_snippets(data.get("sql_snippets", {}))

        return Instructions(
            text_instructions=text_instructions,
            example_question_sqls=example_sqls,
            sql_functions=sql_functions,
            join_specs=join_specs,
            sql_snippets=sql_snippets,
        )

    def _parse_parameters(self, data: list) -> list[ParameterConfig]:
        """Parse parameter configurations for example question SQLs.

        Handles multiple default_value formats:
        1. API format: {"values": ["value"]}
        2. YAML format with type: {"type": "LITERAL", "value": "NA"}
        3. Direct list: ["value"]
        """
        parameters = []
        for item in data:
            default_value = None
            if item.get("default_value"):
                dv = item["default_value"]
                if isinstance(dv, dict):
                    if "values" in dv:
                        # API format: {"values": ["..."]}
                        default_value = ParameterDefaultValue(values=dv.get("values", []))
                    elif "value" in dv:
                        # YAML format: {"type": "LITERAL", "value": "NA"}
                        # Convert to API format
                        value = dv.get("value", "")
                        default_value = ParameterDefaultValue(values=[str(value)])
                elif isinstance(dv, list):
                    default_value = ParameterDefaultValue(values=dv)
                elif isinstance(dv, str):
                    # Direct string value
                    default_value = ParameterDefaultValue(values=[dv])

            parameters.append(
                ParameterConfig(
                    name=item["name"],
                    type_hint=item.get("type_hint", "STRING"),
                    description=item.get("description", []),
                    default_value=default_value,
                )
            )
        return parameters

    def _parse_join_spec(self, item: dict) -> JoinSpec:
        """Parse a single join spec with full structure support."""
        # Handle both old format (left_table, right_table) and new format (left, right)
        if "left" in item and isinstance(item["left"], dict):
            # New format
            left = JoinTableRef(
                identifier=item["left"]["identifier"],
                alias=item["left"].get("alias"),
            )
            right = JoinTableRef(
                identifier=item["right"]["identifier"],
                alias=item["right"].get("alias"),
            )
            sql = item.get("sql", [])
            instruction = item.get("instruction", [])
        else:
            # Old format (backward compatibility)
            left = JoinTableRef(
                identifier=item.get("left_table", ""),
                alias=None,
            )
            right = JoinTableRef(
                identifier=item.get("right_table", ""),
                alias=None,
            )
            # Convert old join_condition to sql list
            join_condition = item.get("join_condition", "")
            join_type = item.get("join_type", "INNER")
            sql = [join_condition]
            if join_type != "INNER":
                sql.append(f"--rt=FROM_RELATIONSHIP_TYPE_{join_type}--")
            instruction = [item.get("description", "")] if item.get("description") else []

        return JoinSpec(
            id=item.get("id"),
            left=left,
            right=right,
            sql=sql,
            instruction=instruction,
        )

    def _parse_sql_snippets(self, data: dict) -> SqlSnippets:
        """Parse SQL snippets (filters, expressions, measures)."""
        return SqlSnippets(
            filters=self._parse_snippet_list(data.get("filters", [])),
            expressions=self._parse_snippet_list(data.get("expressions", [])),
            measures=self._parse_snippet_list(data.get("measures", [])),
        )

    def _parse_snippet_list(self, data: list) -> list[SqlSnippet]:
        """Parse a list of SQL snippets."""
        snippets = []
        for item in data:
            snippets.append(
                SqlSnippet(
                    id=item.get("id"),
                    sql=item.get("sql", []),
                    display_name=item.get("display_name", ""),
                    instruction=item.get("instruction", []),
                    synonyms=item.get("synonyms", []),
                )
            )
        return snippets

    def _parse_benchmarks(self, data: dict) -> Benchmarks:
        """Parse benchmarks from dict."""
        questions = []
        for item in data.get("questions", []):
            questions.append(
                BenchmarkQuestion(
                    question=item["question"],
                    expected_sql=item["expected_sql"],
                )
            )
        return Benchmarks(questions=questions)


def load_config(
    path: Union[str, Path],
    env: str = "dev",
    variables: Optional[dict[str, str]] = None,
) -> list[SpaceConfig]:
    """Convenience function to load a configuration file.

    Args:
        path: Path to YAML or JSON config
        env: Environment name
        variables: Variable overrides

    Returns:
        List of SpaceConfig objects
    """
    parser = MetadataParser(variables=variables, env=env)
    return parser.parse(path)


def validate_config(path: Union[str, Path]) -> list[str]:
    """Convenience function to validate a configuration file.

    Args:
        path: Path to config file

    Returns:
        List of validation errors (empty if valid)
    """
    parser = MetadataParser()
    return parser.validate(path)
