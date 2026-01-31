"""
Serializer for converting SpaceConfig to Genie API format.

The Genie API expects a specific JSON structure for the serialized_space field.
This module handles the conversion from our SpaceConfig models to that format.

Genie Space Serialized Format (version 2):
{
  "version": 2,
  "config": {
    "sample_questions": [{"id": "...", "question": ["..."]}]
  },
  "data_sources": {
    "tables": [
      {
        "identifier": "catalog.schema.table",
        "description": ["..."],
        "column_configs": [{
          "column_name": "...",
          "description": ["..."],
          "synonyms": ["..."],
          "enable_format_assistance": true,
          "enable_entity_matching": true
        }]
      }
    ]
  },
  "instructions": {
    "text_instructions": [{"id": "...", "content": ["..."]}],
    "example_question_sqls": [{
      "id": "...",
      "question": ["..."],
      "sql": ["..."],
      "parameters": [{"name": "...", "type_hint": "STRING", "description": ["..."], "default_value": {...}}],
      "usage_guidance": ["..."]
    }],
    "sql_functions": [...],
    "join_specs": [{
      "id": "...",
      "left": {"identifier": "...", "alias": "..."},
      "right": {"identifier": "...", "alias": "..."},
      "sql": ["..."],
      "instruction": ["..."]
    }],
    "sql_snippets": {
      "filters": [{"id": "...", "sql": ["..."], "display_name": "...", "instruction": ["..."], "synonyms": ["..."]}],
      "expressions": [...],
      "measures": [...]
    }
  },
  "benchmarks": {...}
}
"""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING, Any

from genie_forge.models import SampleQuestion, SpaceConfig

if TYPE_CHECKING:
    from genie_forge.models import SqlSnippet, SqlSnippets


class SerializerError(Exception):
    """Raised when serialization fails."""

    pass


class SpaceSerializer:
    """Serializes SpaceConfig to Genie API format.

    Example:
        serializer = SpaceSerializer()
        api_body = serializer.to_api_request(config)
        # api_body can be passed to GenieClient.create_space()

    API Limitations (handled automatically):
        - All IDs must be lowercase 32-hex UUIDs (auto-generated if not provided)
        - All instruction arrays must be sorted by ID
        - sql_functions only supports "identifier" (description stored locally only)
        - benchmarks are NOT sent to API (stored locally for testing only)
    """

    def to_api_request(self, config: SpaceConfig) -> dict:
        """Convert SpaceConfig to full API request body.

        Args:
            config: SpaceConfig to serialize

        Returns:
            Dict suitable for API create/update request
        """
        return {
            "title": config.title,
            "warehouse_id": config.warehouse_id,
            "parent_path": config.parent_path,
            "serialized_space": self.to_serialized_space(config),
        }

    def to_serialized_space(self, config: SpaceConfig) -> dict:
        """Convert SpaceConfig to serialized_space format.

        Args:
            config: SpaceConfig to serialize

        Returns:
            Dict in Genie serialized_space format (version 2)
        """
        serialized: dict[str, Any] = {
            "version": config.version,
            "config": {
                "sample_questions": self._serialize_sample_questions(config),
            },
            "data_sources": self._serialize_data_sources(config),
            "instructions": self._serialize_instructions(config),
        }

        # Note: Benchmarks are stored locally for testing but are NOT sent to the API
        # The Genie API does not support the benchmarks field in create/update operations
        # if config.benchmarks:
        #     serialized["benchmarks"] = self._serialize_benchmarks(config)

        return serialized

    def _serialize_sample_questions(self, config: SpaceConfig) -> list[dict]:
        """Serialize sample questions to API format.

        Note: The Genie API requires each sample question to have an 'id' field
        that is a lowercase 32-hex UUID without hyphens. IDs are auto-generated
        if not provided.
        """
        result = []
        for item in config.sample_questions:
            if isinstance(item, str):
                # Convert string to SampleQuestion format with auto-generated ID
                result.append(
                    {
                        "id": uuid.uuid4().hex,  # 32-char hex string
                        "question": [item],
                    }
                )
            elif isinstance(item, SampleQuestion):
                q_dict: dict[str, Any] = {"question": item.question}
                # Generate ID if not provided (required by API)
                q_dict["id"] = item.id if item.id else uuid.uuid4().hex
                result.append(q_dict)
            elif isinstance(item, dict):
                # Ensure dict has an ID
                if "id" not in item or not item["id"]:
                    item["id"] = uuid.uuid4().hex
                result.append(item)
        return result

    def _serialize_data_sources(self, config: SpaceConfig) -> dict:
        """Serialize data sources to API format."""
        tables = []
        # Sort tables by identifier (required by Genie API)
        sorted_tables = sorted(config.data_sources.tables, key=lambda t: t.identifier)
        for table in sorted_tables:
            table_dict: dict[str, Any] = {
                "identifier": table.identifier,
            }

            # Only include description if non-empty
            if table.description:
                table_dict["description"] = table.description

            # Serialize column configs
            column_configs = []
            for col in table.column_configs:
                col_dict: dict[str, Any] = {
                    "column_name": col.column_name,
                }
                if col.description:
                    col_dict["description"] = col.description
                if col.synonyms:
                    col_dict["synonyms"] = col.synonyms
                if col.enable_format_assistance:
                    col_dict["enable_format_assistance"] = True
                if col.enable_entity_matching:
                    col_dict["enable_entity_matching"] = True

                column_configs.append(col_dict)

            if column_configs:
                # Sort by column_name alphabetically (required by Genie API)
                table_dict["column_configs"] = sorted(
                    column_configs, key=lambda x: x["column_name"]
                )

            tables.append(table_dict)

        return {"tables": tables}

    def _serialize_instructions(self, config: SpaceConfig) -> dict:
        """Serialize instructions to API format.

        Note: The Genie API requires all instruction arrays to be sorted by ID.
        """
        instructions = config.instructions
        result: dict[str, Any] = {}

        # Helper to sort by ID (items without ID come last)
        def sort_key(item: dict[str, Any]) -> str:
            return str(item.get("id", "zzz_no_id"))

        # Text instructions (API only allows ONE text_instruction)
        if instructions.text_instructions:
            # Combine all instructions into one (API limitation)
            all_content = []
            first_id = None
            for inst in instructions.text_instructions:
                if isinstance(inst.content, list):
                    all_content.extend(inst.content)
                else:
                    all_content.append(inst.content)
                if first_id is None and inst.id:
                    first_id = inst.id

            # Create single combined instruction
            combined_inst: dict[str, Any] = {
                "content": all_content,
                "id": first_id if first_id else uuid.uuid4().hex,
            }
            result["text_instructions"] = [combined_inst]

        # Example question SQLs (API requires ID for each example)
        if instructions.example_question_sqls:
            example_sqls = []
            for ex in instructions.example_question_sqls:
                ex_dict: dict[str, Any] = {
                    "question": ex.question,
                    "sql": ex.sql,
                }
                # Generate ID if not provided (required by API)
                ex_dict["id"] = ex.id if ex.id else uuid.uuid4().hex
                if ex.parameters:
                    ex_dict["parameters"] = self._serialize_parameters(ex.parameters)
                if ex.usage_guidance:
                    ex_dict["usage_guidance"] = ex.usage_guidance
                example_sqls.append(ex_dict)
            # Sort by ID as required by API
            result["example_question_sqls"] = sorted(example_sqls, key=sort_key)

        # SQL functions (API requires ID and identifier)
        if instructions.sql_functions:
            sql_functions = []
            for func in instructions.sql_functions:
                # Note: The Genie API requires "id" (UUID) and "identifier" for sql_functions
                # The "description" field is stored locally but not sent to the API
                func_dict: dict[str, Any] = {
                    "identifier": func.identifier,
                    "id": func.id if func.id else uuid.uuid4().hex,  # Generate UUID if missing
                }
                sql_functions.append(func_dict)
            # Sort by (id, identifier) as required by API
            result["sql_functions"] = sorted(
                sql_functions, key=lambda x: (x.get("id", ""), x.get("identifier", ""))
            )

        # Join specs (API requires ID for each join spec)
        if instructions.join_specs:
            join_specs = []
            for join in instructions.join_specs:
                join_dict: dict[str, Any] = {
                    "left": {
                        "identifier": join.left.identifier,
                    },
                    "right": {
                        "identifier": join.right.identifier,
                    },
                    "sql": join.sql,
                }
                # Generate ID if not provided (required by API)
                join_dict["id"] = join.id if join.id else uuid.uuid4().hex
                if join.left.alias:
                    join_dict["left"]["alias"] = join.left.alias
                if join.right.alias:
                    join_dict["right"]["alias"] = join.right.alias
                if join.instruction:
                    join_dict["instruction"] = join.instruction
                join_specs.append(join_dict)
            # Sort by ID as required by API
            result["join_specs"] = sorted(join_specs, key=sort_key)

        # SQL snippets
        sql_snippets = self._serialize_sql_snippets(instructions.sql_snippets)
        if sql_snippets:
            result["sql_snippets"] = sql_snippets

        return result

    def _serialize_parameters(self, parameters: list) -> list[dict]:
        """Serialize parameters for example question SQLs."""
        result = []
        for param in parameters:
            param_dict: dict[str, Any] = {
                "name": param.name,
                "type_hint": param.type_hint,
            }
            if param.description:
                param_dict["description"] = param.description
            if param.default_value:
                param_dict["default_value"] = {"values": param.default_value.values}
            result.append(param_dict)
        return result

    def _serialize_sql_snippets(self, sql_snippets: "SqlSnippets") -> dict:
        """Serialize SQL snippets (filters, expressions, measures) to API format.

        Note: The Genie API requires snippets to be sorted by ID.
        """
        result: dict[str, Any] = {}

        # Helper to sort by ID
        def sort_key(item: dict[str, Any]) -> str:
            return str(item.get("id", "zzz_no_id"))

        if sql_snippets.filters:
            filters = [self._serialize_single_snippet(s) for s in sql_snippets.filters]
            result["filters"] = sorted(filters, key=sort_key)

        if sql_snippets.expressions:
            expressions = [self._serialize_single_snippet(s) for s in sql_snippets.expressions]
            result["expressions"] = sorted(expressions, key=sort_key)

        if sql_snippets.measures:
            measures = [self._serialize_single_snippet(s) for s in sql_snippets.measures]
            result["measures"] = sorted(measures, key=sort_key)

        return result

    def _serialize_single_snippet(self, snippet: "SqlSnippet") -> dict:
        """Serialize a single SQL snippet."""
        snippet_dict: dict[str, Any] = {
            "sql": snippet.sql,
            "display_name": snippet.display_name,
        }
        # Generate ID if not provided (required by API)
        snippet_dict["id"] = snippet.id if snippet.id else uuid.uuid4().hex
        if snippet.instruction:
            snippet_dict["instruction"] = snippet.instruction
        if snippet.synonyms:
            snippet_dict["synonyms"] = snippet.synonyms
        return snippet_dict

    def _serialize_benchmarks(self, config: SpaceConfig) -> dict:
        """Serialize benchmarks to API format."""
        if not config.benchmarks:
            return {}

        questions = []
        for q in config.benchmarks.questions:
            # API expects question as array
            question_list = [q.question] if isinstance(q.question, str) else q.question
            questions.append(
                {
                    "question": question_list,
                    "expected_sql": q.expected_sql,
                }
            )

        return {"questions": questions}

    def from_api_response(self, response: dict) -> dict:
        """Parse an API response to extract space info.

        Args:
            response: API response from get_space

        Returns:
            Dict with extracted space information
        """
        space_info = {
            "id": response.get("id") or response.get("space", {}).get("id"),
            "title": response.get("title") or response.get("space", {}).get("title"),
            "warehouse_id": response.get("warehouse_id"),
            "parent_path": response.get("parent_path"),
        }

        # Extract serialized space if present
        serialized = response.get("serialized_space")
        if serialized:
            space_info["serialized_space"] = serialized

        return space_info

    def from_api_to_config(self, response: dict, logical_id: str) -> SpaceConfig:
        """Convert an API response to a SpaceConfig object.

        This enables importing existing spaces from Databricks into genie-forge.
        Performs lossless conversion of all Genie API fields.

        Args:
            response: API response from get_space (with include_serialized=True)
            logical_id: The logical ID to assign to this space in genie-forge

        Returns:
            SpaceConfig object that can be serialized to YAML

        Raises:
            SerializerError: If required fields are missing
        """
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
            SqlSnippets,
            TableConfig,
            TextInstruction,
        )

        # Extract basic info
        title = response.get("title") or response.get("space", {}).get("title")
        warehouse_id = response.get("warehouse_id")
        parent_path = response.get("parent_path")

        if not title:
            raise SerializerError("Missing 'title' in API response")
        if not warehouse_id:
            raise SerializerError("Missing 'warehouse_id' in API response")

        # Get serialized space data (may be JSON string or dict)
        raw_serialized = response.get("serialized_space", {})
        if isinstance(raw_serialized, str):
            try:
                serialized = json.loads(raw_serialized) if raw_serialized else {}
            except (json.JSONDecodeError, TypeError):
                serialized = {}
        else:
            serialized = raw_serialized if raw_serialized else {}

        config_data = serialized.get("config", {})
        data_sources_data = serialized.get("data_sources", {})
        instructions_data = serialized.get("instructions", {})
        benchmarks_data = serialized.get("benchmarks", {})

        # Parse sample questions
        sample_questions = []
        for sq in config_data.get("sample_questions", []):
            if isinstance(sq, dict):
                sample_questions.append(
                    SampleQuestion(
                        id=sq.get("id"),
                        question=sq.get("question", []),
                    )
                )
            elif isinstance(sq, str):
                sample_questions.append(SampleQuestion(question=[sq]))

        # Parse tables with full column config
        tables = []
        for tbl in data_sources_data.get("tables", []):
            columns = []
            for col in tbl.get("column_configs", []):
                columns.append(
                    ColumnConfig(
                        column_name=col.get("column_name", ""),
                        description=col.get("description", []),
                        synonyms=col.get("synonyms", []),
                        enable_format_assistance=col.get("enable_format_assistance", False),
                        enable_entity_matching=col.get("enable_entity_matching", False),
                    )
                )
            tables.append(
                TableConfig(
                    identifier=tbl.get("identifier", ""),
                    description=tbl.get("description", []),
                    column_configs=columns,
                )
            )

        # Parse text instructions
        text_instructions = []
        for inst in instructions_data.get("text_instructions", []):
            text_instructions.append(
                TextInstruction(
                    id=inst.get("id"),
                    content=inst.get("content", []),
                )
            )

        # Parse example question SQLs with parameters and usage_guidance
        example_sqls = []
        for ex in instructions_data.get("example_question_sqls", []):
            # Parse parameters
            parameters = []
            for param in ex.get("parameters", []):
                default_value = None
                if param.get("default_value"):
                    default_value = ParameterDefaultValue(
                        values=param["default_value"].get("values", [])
                    )
                parameters.append(
                    ParameterConfig(
                        name=param.get("name", ""),
                        type_hint=param.get("type_hint", "STRING"),
                        description=param.get("description", []),
                        default_value=default_value,
                    )
                )

            example_sqls.append(
                ExampleQuestionSQL(
                    id=ex.get("id"),
                    question=ex.get("question", []),
                    sql=ex.get("sql", []),
                    parameters=parameters,
                    usage_guidance=ex.get("usage_guidance", []),
                )
            )

        # Parse SQL functions
        sql_functions = [
            SqlFunction(
                identifier=func.get("identifier", ""),
                description=func.get("description"),
            )
            for func in instructions_data.get("sql_functions", [])
        ]

        # Parse join specs with full structure
        join_specs = []
        for join in instructions_data.get("join_specs", []):
            left_data = join.get("left", {})
            right_data = join.get("right", {})
            join_specs.append(
                JoinSpec(
                    id=join.get("id"),
                    left=JoinTableRef(
                        identifier=left_data.get("identifier", ""),
                        alias=left_data.get("alias"),
                    ),
                    right=JoinTableRef(
                        identifier=right_data.get("identifier", ""),
                        alias=right_data.get("alias"),
                    ),
                    sql=join.get("sql", []),
                    instruction=join.get("instruction", []),
                )
            )

        # Parse SQL snippets
        sql_snippets_data = instructions_data.get("sql_snippets", {})
        sql_snippets = SqlSnippets(
            filters=self._parse_snippets(sql_snippets_data.get("filters", [])),
            expressions=self._parse_snippets(sql_snippets_data.get("expressions", [])),
            measures=self._parse_snippets(sql_snippets_data.get("measures", [])),
        )

        # Parse benchmarks
        benchmarks = None
        if benchmarks_data.get("questions"):
            benchmarks = Benchmarks(
                questions=[
                    BenchmarkQuestion(
                        question=q.get("question", ""),
                        expected_sql=q.get("expected_sql", ""),
                    )
                    for q in benchmarks_data.get("questions", [])
                ]
            )

        return SpaceConfig(
            space_id=logical_id,
            title=title,
            warehouse_id=warehouse_id,
            parent_path=parent_path,
            sample_questions=sample_questions,
            data_sources=DataSources(tables=tables),
            instructions=Instructions(
                text_instructions=text_instructions,
                example_question_sqls=example_sqls,
                sql_functions=sql_functions,
                join_specs=join_specs,
                sql_snippets=sql_snippets,
            ),
            benchmarks=benchmarks,
            version=serialized.get("version", 2),
        )

    def _parse_snippets(self, snippets_data: list) -> list:
        """Parse SQL snippets from API response."""
        from genie_forge.models import SqlSnippet

        result = []
        for s in snippets_data:
            result.append(
                SqlSnippet(
                    id=s.get("id"),
                    sql=s.get("sql", []),
                    display_name=s.get("display_name", ""),
                    instruction=s.get("instruction", []),
                    synonyms=s.get("synonyms", []),
                )
            )
        return result


def serialize_config(config: SpaceConfig) -> dict:
    """Convenience function to serialize a SpaceConfig.

    Args:
        config: SpaceConfig to serialize

    Returns:
        API request body dict
    """
    serializer = SpaceSerializer()
    return serializer.to_api_request(config)


def serialize_for_api(config: SpaceConfig) -> dict:
    """Convenience function to get just the serialized_space dict.

    Args:
        config: SpaceConfig to serialize

    Returns:
        serialized_space dict
    """
    serializer = SpaceSerializer()
    return serializer.to_serialized_space(config)


def configs_to_api_requests(configs: list[SpaceConfig]) -> list[dict]:
    """Convert multiple SpaceConfigs to API request bodies.

    Args:
        configs: List of SpaceConfig objects

    Returns:
        List of API request body dicts
    """
    serializer = SpaceSerializer()
    return [serializer.to_api_request(config) for config in configs]


def space_to_yaml(space: dict, logical_id: str | None = None) -> str:
    """Convert API space response to YAML configuration format.

    This function takes a space dictionary from the Databricks Genie API
    (as returned by GenieClient.get_space()) and converts it to a YAML
    configuration string that can be saved to a file and used with
    genie-forge's plan/apply workflow.

    Args:
        space: Space dict from GenieClient.get_space() containing
               'id', 'title', 'warehouse_id', 'serialized_space', etc.
        logical_id: Optional logical identifier for the space. If not provided,
                   generates one from the space title (sanitized) or uses the
                   Databricks space ID.

    Returns:
        YAML string in genie-forge configuration format (version 2),
        ready to save to a file.

    Example:
        >>> from genie_forge import GenieClient
        >>> from genie_forge.serializer import space_to_yaml
        >>>
        >>> client = GenieClient(profile="MY_PROFILE")
        >>> space = client.get_space("01abc123def456")
        >>> yaml_content = space_to_yaml(space)
        >>> Path("exported_space.yaml").write_text(yaml_content)
    """
    import re

    import yaml

    # Generate logical_id if not provided
    if logical_id is None:
        title = space.get("title", "")
        if title:
            # Sanitize title to create a logical ID
            logical_id = re.sub(r"[^a-zA-Z0-9_]", "_", title.lower())
            logical_id = re.sub(r"_+", "_", logical_id).strip("_")
        else:
            # Fallback to using the Databricks space ID
            logical_id = space.get("id", "unnamed_space")

    serializer = SpaceSerializer()
    config = serializer.from_api_to_config(space, logical_id)

    # Convert to dict, excluding None values for cleaner output
    config_dict = config.model_dump(exclude_none=True)

    # Wrap in version 2 format
    output = {"version": 2, "spaces": [config_dict]}

    return yaml.dump(output, default_flow_style=False, sort_keys=False, allow_unicode=True)
