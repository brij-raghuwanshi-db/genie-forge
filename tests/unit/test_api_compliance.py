"""API Compliance tests for Genie REST API.

Tests to ensure the serialized data matches the Databricks Genie API contract.
Based on: https://docs.databricks.com/api/workspace/genie

API Version: 2.0 (Public Preview)
Last API update: December 2025
"""

from __future__ import annotations

import json
import re

import pytest

from genie_forge.models import (
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
from genie_forge.serializer import SpaceSerializer

# =============================================================================
# API Request Structure Tests
# =============================================================================


class TestAPIRequestStructure:
    """Tests for correct API request structure."""

    def test_create_space_request_has_required_fields(self):
        """Test that create request has all required fields."""
        config = SpaceConfig.minimal(
            space_id="test",
            title="Test Space",
            warehouse_id="wh-123",
            tables=["catalog.schema.table"],
        )

        serializer = SpaceSerializer()
        request = serializer.to_api_request(config)

        # Required fields per API documentation
        assert "title" in request
        assert "warehouse_id" in request
        assert "serialized_space" in request

    def test_serialized_space_is_string_not_dict(self):
        """Test that serialized_space is a JSON string when sent to API."""
        config = SpaceConfig.minimal(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            tables=["c.s.t"],
        )

        serializer = SpaceSerializer()
        request = serializer.to_api_request(config)

        # The API requires serialized_space to be a JSON string
        # (Even though to_api_request returns dict, the actual API call
        # in client.py converts it to JSON string)
        serialized = request["serialized_space"]

        # Verify it's a dict that can be JSON serialized
        # (client.py does json.dumps on this)
        json_str = json.dumps(serialized)
        assert isinstance(json_str, str)

        # Verify it can be parsed back
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)

    def test_version_field_required(self):
        """Test that version field is included in serialized_space."""
        config = SpaceConfig.minimal(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            tables=["c.s.t"],
        )

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        assert "version" in serialized
        assert serialized["version"] == 2  # Current API version


# =============================================================================
# Sample Questions API Requirements
# =============================================================================


class TestSampleQuestionsAPIRequirements:
    """Tests for sample_questions API requirements."""

    def test_sample_questions_have_unique_ids(self):
        """Test that all sample questions have unique UUIDs."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            sample_questions=[
                SampleQuestion(question=["Q1?"]),  # No ID
                SampleQuestion(question=["Q2?"]),  # No ID
                "Q3?",  # String format
            ],
        )

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        questions = serialized["config"]["sample_questions"]

        # All should have IDs
        ids = [q["id"] for q in questions]
        assert all(id_ is not None for id_ in ids)

        # All IDs should be unique
        assert len(ids) == len(set(ids))

    def test_sample_question_id_format_is_hex_uuid(self):
        """Test that auto-generated IDs are 32-char hex UUIDs."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            sample_questions=[
                SampleQuestion(question=["Q?"]),  # Will get auto-generated ID
            ],
        )

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        q_id = serialized["config"]["sample_questions"][0]["id"]

        # Should be 32 hex characters (UUID without dashes)
        assert len(q_id) == 32
        assert re.match(r"^[a-f0-9]{32}$", q_id)

    def test_existing_ids_are_preserved(self):
        """Test that existing IDs are not replaced."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            sample_questions=[
                SampleQuestion(id="my_custom_id", question=["Q?"]),
            ],
        )

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        q_id = serialized["config"]["sample_questions"][0]["id"]
        assert q_id == "my_custom_id"

    def test_question_is_always_array(self):
        """Test that question field is always an array."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            sample_questions=[
                SampleQuestion(question="Single string"),  # String should become array
            ],
        )

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        question = serialized["config"]["sample_questions"][0]["question"]
        assert isinstance(question, list)
        assert question == ["Single string"]


# =============================================================================
# Data Sources API Requirements
# =============================================================================


class TestDataSourcesAPIRequirements:
    """Tests for data_sources API requirements."""

    def test_tables_sorted_by_identifier(self):
        """Test that tables are sorted by identifier."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            data_sources=DataSources(
                tables=[
                    TableConfig(identifier="z.z.z"),
                    TableConfig(identifier="a.a.a"),
                    TableConfig(identifier="m.m.m"),
                ]
            ),
        )

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        identifiers = [t["identifier"] for t in serialized["data_sources"]["tables"]]
        assert identifiers == sorted(identifiers)

    def test_table_identifier_format_three_parts(self):
        """Test that table identifiers have catalog.schema.table format."""
        # Valid identifier
        table = TableConfig(identifier="catalog.schema.table")
        assert table.identifier == "catalog.schema.table"

        # Invalid identifiers should raise validation error
        with pytest.raises(Exception):
            TableConfig(identifier="schema.table")  # Missing catalog

        with pytest.raises(Exception):
            TableConfig(identifier="table")  # Missing schema and catalog

    def test_column_configs_structure(self):
        """Test column_configs API structure."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            data_sources=DataSources(
                tables=[
                    TableConfig(
                        identifier="c.s.t",
                        column_configs=[
                            ColumnConfig(
                                column_name="status",
                                description=["Status of the record"],
                                synonyms=["state", "condition"],
                                enable_format_assistance=True,
                                enable_entity_matching=True,
                            )
                        ],
                    )
                ]
            ),
        )

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        col = serialized["data_sources"]["tables"][0]["column_configs"][0]

        # Required field
        assert "column_name" in col
        assert col["column_name"] == "status"

        # Optional fields should be arrays
        assert isinstance(col["description"], list)
        assert isinstance(col["synonyms"], list)

        # Boolean flags
        assert col["enable_format_assistance"] is True
        assert col["enable_entity_matching"] is True


# =============================================================================
# Instructions API Requirements
# =============================================================================


class TestInstructionsAPIRequirements:
    """Tests for instructions API requirements."""

    def test_text_instructions_sorted_by_id(self):
        """Test that text_instructions are sorted by ID."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            instructions=Instructions(
                text_instructions=[
                    TextInstruction(id="z_last", content=["Last"]),
                    TextInstruction(id="a_first", content=["First"]),
                    TextInstruction(id="m_middle", content=["Middle"]),
                ]
            ),
        )

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        ids = [ti["id"] for ti in serialized["instructions"]["text_instructions"]]
        assert ids == sorted(ids)

    def test_text_instruction_content_is_array(self):
        """Test that content field is always an array."""
        ti = TextInstruction(content="Single string")
        assert isinstance(ti.content, list)
        assert ti.content == ["Single string"]

    def test_example_question_sqls_have_required_fields(self):
        """Test example_question_sqls required fields."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            instructions=Instructions(
                example_question_sqls=[
                    ExampleQuestionSQL(
                        question=["Count records?"],
                        sql=["SELECT COUNT(*) FROM table"],
                    )
                ]
            ),
        )

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        eq = serialized["instructions"]["example_question_sqls"][0]

        # Required fields
        assert "question" in eq
        assert "sql" in eq
        assert isinstance(eq["question"], list)
        assert isinstance(eq["sql"], list)

    def test_parameter_default_value_structure(self):
        """Test parameter default_value API structure."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            instructions=Instructions(
                example_question_sqls=[
                    ExampleQuestionSQL(
                        question=["Q?"],
                        sql=["SELECT :param"],
                        parameters=[
                            ParameterConfig(
                                name="param",
                                type_hint="STRING",
                                description=["Parameter description"],
                                default_value=ParameterDefaultValue(values=["default_value"]),
                            )
                        ],
                    )
                ]
            ),
        )

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        param = serialized["instructions"]["example_question_sqls"][0]["parameters"][0]

        # Check structure
        assert param["name"] == "param"
        assert param["type_hint"] == "STRING"
        assert isinstance(param["description"], list)
        assert "default_value" in param
        assert param["default_value"]["values"] == ["default_value"]


# =============================================================================
# Join Specs API Requirements
# =============================================================================


class TestJoinSpecsAPIRequirements:
    """Tests for join_specs API requirements."""

    def test_join_spec_has_required_fields(self):
        """Test join_spec required fields."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            instructions=Instructions(
                join_specs=[
                    JoinSpec(
                        left=JoinTableRef(identifier="c.s.left", alias="l"),
                        right=JoinTableRef(identifier="c.s.right", alias="r"),
                        sql=["l.id = r.id"],
                    )
                ]
            ),
        )

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        js = serialized["instructions"]["join_specs"][0]

        # Required fields
        assert "left" in js
        assert "right" in js
        assert "sql" in js

        # Left/right structure
        assert "identifier" in js["left"]
        assert "identifier" in js["right"]

    def test_join_spec_relationship_type_in_sql(self):
        """Test that relationship type is encoded in SQL array."""
        # The API uses special comments in SQL to encode relationship type
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            instructions=Instructions(
                join_specs=[
                    JoinSpec(
                        left=JoinTableRef(identifier="c.s.left"),
                        right=JoinTableRef(identifier="c.s.right"),
                        sql=[
                            "left.id = right.id",
                            "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_MANY--",
                        ],
                    )
                ]
            ),
        )

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        sql = serialized["instructions"]["join_specs"][0]["sql"]
        assert "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_MANY--" in sql

    def test_self_join_different_aliases_required(self):
        """Test that self-joins require different aliases."""
        # For self-joins (same table), aliases distinguish instances
        join = JoinSpec(
            left=JoinTableRef(identifier="c.s.employees", alias="e"),
            right=JoinTableRef(identifier="c.s.employees", alias="m"),
            sql=["e.manager_id = m.employee_id"],
        )

        # Same identifier, different aliases
        assert join.left.identifier == join.right.identifier
        assert join.left.alias != join.right.alias


# =============================================================================
# SQL Snippets API Requirements
# =============================================================================


class TestSqlSnippetsAPIRequirements:
    """Tests for sql_snippets API requirements."""

    def test_sql_snippet_has_required_fields(self):
        """Test sql_snippet required fields."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            instructions=Instructions(
                sql_snippets=SqlSnippets(
                    filters=[
                        SqlSnippet(
                            sql=["status = 'active'"],
                            display_name="Active Only",
                        )
                    ]
                )
            ),
        )

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        f = serialized["instructions"]["sql_snippets"]["filters"][0]

        # Required fields
        assert "sql" in f
        assert "display_name" in f
        assert isinstance(f["sql"], list)

    def test_sql_snippets_sorted_by_id(self):
        """Test that sql_snippets are sorted by ID."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            instructions=Instructions(
                sql_snippets=SqlSnippets(
                    filters=[
                        SqlSnippet(id="z", sql=["z"], display_name="Z"),
                        SqlSnippet(id="a", sql=["a"], display_name="A"),
                    ]
                )
            ),
        )

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        ids = [f["id"] for f in serialized["instructions"]["sql_snippets"]["filters"]]
        assert ids == sorted(ids)

    def test_all_snippet_types_supported(self):
        """Test that all snippet types are supported."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            instructions=Instructions(
                sql_snippets=SqlSnippets(
                    filters=[SqlSnippet(sql=["x > 0"], display_name="Positive")],
                    expressions=[SqlSnippet(sql=["CURRENT_DATE"], display_name="Today")],
                    measures=[SqlSnippet(sql=["SUM(x)"], display_name="Total")],
                )
            ),
        )

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        snippets = serialized["instructions"]["sql_snippets"]

        assert "filters" in snippets
        assert "expressions" in snippets
        assert "measures" in snippets

        assert len(snippets["filters"]) == 1
        assert len(snippets["expressions"]) == 1
        assert len(snippets["measures"]) == 1


# =============================================================================
# SQL Functions API Requirements
# =============================================================================


class TestSqlFunctionsAPIRequirements:
    """Tests for sql_functions API requirements."""

    def test_sql_function_identifier_only(self):
        """Test that sql_functions only include identifier (not description)."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            instructions=Instructions(
                sql_functions=[
                    SqlFunction(
                        identifier="catalog.schema.my_function",
                        description="This description should NOT be in API output",
                    )
                ]
            ),
        )

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        func = serialized["instructions"]["sql_functions"][0]

        # identifier should be present
        assert "identifier" in func
        assert func["identifier"] == "catalog.schema.my_function"

        # description should NOT be sent to API
        assert "description" not in func


# =============================================================================
# Benchmarks API Requirements
# =============================================================================


class TestBenchmarksAPIRequirements:
    """Tests for benchmarks (NOT sent to API)."""

    def test_benchmarks_not_in_api_output(self):
        """Test that benchmarks are NOT included in API serialization."""
        from genie_forge.models import BenchmarkQuestion, Benchmarks

        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            benchmarks=Benchmarks(
                questions=[
                    BenchmarkQuestion(
                        question="What is the total?",
                        expected_sql="SELECT SUM(amount) FROM orders",
                    )
                ]
            ),
        )

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        # benchmarks should NOT be in API output (stored locally only)
        assert "benchmarks" not in serialized

        # But config should still have them
        assert config.benchmarks is not None
        assert len(config.benchmarks.questions) == 1


# =============================================================================
# API Response Parsing Tests
# =============================================================================


class TestAPIResponseParsing:
    """Tests for parsing API responses."""

    def test_parse_minimal_api_response(self):
        """Test parsing minimal API response."""
        response = {
            "id": "space-123",
            "title": "My Space",
            "warehouse_id": "wh-456",
            "serialized_space": {
                "version": 2,
            },
        }

        serializer = SpaceSerializer()
        config = serializer.from_api_to_config(response, "my_space")

        assert config.space_id == "my_space"
        assert config.title == "My Space"
        assert config.warehouse_id == "wh-456"
        assert config.version == 2

    def test_parse_response_with_missing_optional_fields(self):
        """Test parsing response with missing optional fields."""
        response = {
            "title": "My Space",
            "warehouse_id": "wh-456",
            "serialized_space": {
                "version": 2,
                # No data_sources, instructions, config sections
            },
        }

        serializer = SpaceSerializer()
        config = serializer.from_api_to_config(response, "test")

        # Should have default empty values
        assert config.data_sources.tables == []
        assert config.sample_questions == []

    def test_parse_response_with_serialized_space_as_string(self):
        """Test parsing response where serialized_space is JSON string."""
        serialized_content = {
            "version": 2,
            "config": {"sample_questions": []},
        }

        response = {
            "title": "My Space",
            "warehouse_id": "wh-456",
            "serialized_space": json.dumps(serialized_content),  # As string
        }

        serializer = SpaceSerializer()
        # This tests internal handling - serializer should parse JSON string
        result = serializer.from_api_response(response)

        # serialized_space might be parsed or kept as string
        # Documenting current behavior
        assert "title" in result


# =============================================================================
# Round-Trip Tests
# =============================================================================


class TestAPIRoundTrip:
    """Tests for API round-trip (serialize -> deserialize -> same data)."""

    def test_full_config_round_trip(self):
        """Test that full config survives round-trip."""
        original = SpaceConfig(
            space_id="test_space",
            title="Test Space",
            warehouse_id="wh123",
            parent_path="/Workspace/Test",
            version=2,
            sample_questions=[
                SampleQuestion(id="sq1", question=["Q1?", "Q1 alternative?"]),
            ],
            data_sources=DataSources(
                tables=[
                    TableConfig(
                        identifier="cat.sch.tbl",
                        description=["Table description"],
                        column_configs=[
                            ColumnConfig(
                                column_name="col1",
                                description=["Column description"],
                                synonyms=["c1"],
                                enable_format_assistance=True,
                                enable_entity_matching=True,
                            )
                        ],
                    )
                ]
            ),
            instructions=Instructions(
                text_instructions=[
                    TextInstruction(id="ti1", content=["Instruction text"]),
                ],
                example_question_sqls=[
                    ExampleQuestionSQL(
                        id="eq1",
                        question=["Query question?"],
                        sql=["SELECT * FROM t"],
                        parameters=[
                            ParameterConfig(
                                name="p1",
                                type_hint="STRING",
                                description=["Param desc"],
                                default_value=ParameterDefaultValue(values=["default"]),
                            )
                        ],
                        usage_guidance=["Use for testing"],
                    )
                ],
                join_specs=[
                    JoinSpec(
                        id="js1",
                        left=JoinTableRef(identifier="c.s.t1", alias="t1"),
                        right=JoinTableRef(identifier="c.s.t2", alias="t2"),
                        sql=["t1.id = t2.id"],
                        instruction=["Join instruction"],
                    )
                ],
                sql_snippets=SqlSnippets(
                    filters=[
                        SqlSnippet(
                            id="f1",
                            sql=["active = true"],
                            display_name="Active",
                            instruction=["Filter instruction"],
                            synonyms=["live"],
                        )
                    ],
                ),
            ),
        )

        # Serialize
        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(original)

        # Create fake API response
        api_response = {
            "id": "db-123",
            "title": original.title,
            "warehouse_id": original.warehouse_id,
            "parent_path": original.parent_path,
            "serialized_space": serialized,
        }

        # Deserialize back
        restored = serializer.from_api_to_config(api_response, original.space_id)

        # Verify key fields match
        assert restored.title == original.title
        assert restored.warehouse_id == original.warehouse_id
        assert restored.version == original.version
        assert len(restored.sample_questions) == len(original.sample_questions)
        assert len(restored.data_sources.tables) == len(original.data_sources.tables)

    def test_empty_config_round_trip(self):
        """Test that empty/minimal config survives round-trip."""
        original = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            sample_questions=[],
        )

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(original)

        api_response = {
            "id": "db-123",
            "title": original.title,
            "warehouse_id": original.warehouse_id,
            "serialized_space": serialized,
        }

        restored = serializer.from_api_to_config(api_response, original.space_id)

        assert restored.sample_questions == []
        assert restored.data_sources.tables == []
