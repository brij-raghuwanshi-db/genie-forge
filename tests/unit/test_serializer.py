"""Unit tests for genie_forge.serializer."""

import pytest

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
from genie_forge.serializer import (
    SpaceSerializer,
    configs_to_api_requests,
    serialize_config,
    serialize_for_api,
    space_to_yaml,
)


@pytest.fixture
def full_space_config() -> SpaceConfig:
    """Create a fully populated SpaceConfig for testing."""
    return SpaceConfig(
        space_id="test_space",
        title="Test Space",
        warehouse_id="wh123",
        parent_path="/Workspace/Test",
        version=2,
        sample_questions=[
            SampleQuestion(id="sq1", question=["Q1?"]),
            "Q2?",  # String format for backward compat
        ],
        data_sources=DataSources(
            tables=[
                TableConfig(
                    identifier="cat.sch.tbl",
                    description=["Table description"],
                    column_configs=[
                        ColumnConfig(
                            column_name="col1",
                            description=["Column 1"],
                            synonyms=["c1", "column_one"],
                            enable_format_assistance=True,
                            enable_entity_matching=True,
                        )
                    ],
                )
            ]
        ),
        instructions=Instructions(
            text_instructions=[TextInstruction(id="ti1", content=["Do this"])],
            example_question_sqls=[
                ExampleQuestionSQL(
                    id="ex1",
                    question=["Count?"],
                    sql=["SELECT COUNT(*)"],
                    parameters=[
                        ParameterConfig(
                            name="status",
                            type_hint="STRING",
                            description=["Filter by status"],
                            default_value=ParameterDefaultValue(values=["active"]),
                        )
                    ],
                    usage_guidance=["Use for counting"],
                )
            ],
            sql_functions=[SqlFunction(identifier="cat.sch.func", description="A function")],
            join_specs=[
                JoinSpec(
                    id="js1",
                    left=JoinTableRef(identifier="cat.sch.left", alias="l"),
                    right=JoinTableRef(identifier="cat.sch.right", alias="r"),
                    sql=["l.id = r.id", "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_MANY--"],
                    instruction=["Join description"],
                )
            ],
            sql_snippets=SqlSnippets(
                filters=[
                    SqlSnippet(
                        id="f1",
                        sql=["status = 'active'"],
                        display_name="Active Only",
                        instruction=["Filter to active records"],
                        synonyms=["active", "live"],
                    )
                ],
                expressions=[
                    SqlSnippet(
                        id="e1",
                        sql=["CURRENT_DATE"],
                        display_name="Today",
                        instruction=["Get today's date"],
                    )
                ],
                measures=[
                    SqlSnippet(
                        id="m1",
                        sql=["SUM(amount)"],
                        display_name="Total Amount",
                        synonyms=["total"],
                    )
                ],
            ),
        ),
        benchmarks=Benchmarks(
            questions=[BenchmarkQuestion(question="Benchmark Q", expected_sql="SELECT 1")]
        ),
    )


class TestSpaceSerializer:
    """Tests for SpaceSerializer."""

    def test_to_api_request(self, full_space_config: SpaceConfig):
        """Test converting config to API request body."""
        serializer = SpaceSerializer()
        result = serializer.to_api_request(full_space_config)

        assert result["title"] == "Test Space"
        assert result["warehouse_id"] == "wh123"
        assert result["parent_path"] == "/Workspace/Test"
        assert "serialized_space" in result

    def test_serialized_space_structure(self, full_space_config: SpaceConfig):
        """Test the structure of serialized_space."""
        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(full_space_config)

        assert serialized["version"] == 2
        assert "config" in serialized
        assert "data_sources" in serialized
        assert "instructions" in serialized
        # Note: benchmarks are NOT sent to the API (stored locally only)
        # The Genie API does not support the benchmarks field in create/update
        # assert "benchmarks" in serialized

    def test_sample_questions_serialized(self, full_space_config: SpaceConfig):
        """Test that sample questions are in config section."""
        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(full_space_config)

        sample_q = serialized["config"]["sample_questions"]
        assert len(sample_q) == 2
        # First has id
        assert sample_q[0]["id"] == "sq1"
        assert sample_q[0]["question"] == ["Q1?"]
        # Second is from string
        assert sample_q[1]["question"] == ["Q2?"]

    def test_data_sources_serialized(self, full_space_config: SpaceConfig):
        """Test data sources serialization."""
        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(full_space_config)

        tables = serialized["data_sources"]["tables"]
        assert len(tables) == 1
        assert tables[0]["identifier"] == "cat.sch.tbl"
        assert "column_configs" in tables[0]

    def test_column_config_serialized(self, full_space_config: SpaceConfig):
        """Test column config serialization with new fields."""
        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(full_space_config)

        col = serialized["data_sources"]["tables"][0]["column_configs"][0]
        assert col["column_name"] == "col1"
        assert col["description"] == ["Column 1"]
        assert col["synonyms"] == ["c1", "column_one"]
        assert col["enable_format_assistance"] is True
        assert col["enable_entity_matching"] is True

    def test_instructions_serialized(self, full_space_config: SpaceConfig):
        """Test instructions serialization."""
        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(full_space_config)

        inst = serialized["instructions"]

        # Text instructions
        assert len(inst["text_instructions"]) == 1
        assert inst["text_instructions"][0]["id"] == "ti1"
        assert inst["text_instructions"][0]["content"] == ["Do this"]

        # Example question SQLs with parameters
        assert len(inst["example_question_sqls"]) == 1
        ex = inst["example_question_sqls"][0]
        assert ex["id"] == "ex1"
        assert ex["question"] == ["Count?"]
        assert ex["sql"] == ["SELECT COUNT(*)"]
        assert len(ex["parameters"]) == 1
        assert ex["parameters"][0]["name"] == "status"
        assert ex["usage_guidance"] == ["Use for counting"]

        # SQL functions
        assert len(inst["sql_functions"]) == 1
        assert inst["sql_functions"][0]["identifier"] == "cat.sch.func"

        # Join specs
        assert len(inst["join_specs"]) == 1
        js = inst["join_specs"][0]
        assert js["id"] == "js1"
        assert js["left"]["identifier"] == "cat.sch.left"
        assert js["left"]["alias"] == "l"
        assert js["right"]["identifier"] == "cat.sch.right"
        assert len(js["sql"]) == 2

    def test_sql_snippets_serialized(self, full_space_config: SpaceConfig):
        """Test SQL snippets serialization."""
        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(full_space_config)

        snippets = serialized["instructions"]["sql_snippets"]

        # Filters
        assert len(snippets["filters"]) == 1
        f = snippets["filters"][0]
        assert f["id"] == "f1"
        assert f["sql"] == ["status = 'active'"]
        assert f["display_name"] == "Active Only"
        assert f["instruction"] == ["Filter to active records"]

        # Expressions
        assert len(snippets["expressions"]) == 1
        assert snippets["expressions"][0]["display_name"] == "Today"

        # Measures
        assert len(snippets["measures"]) == 1
        assert snippets["measures"][0]["display_name"] == "Total Amount"

    def test_benchmarks_not_in_api_serialization(self, full_space_config: SpaceConfig):
        """Test that benchmarks are NOT included in API serialization.

        The Genie API does not support the benchmarks field in create/update operations.
        Benchmarks are stored locally for testing purposes only.
        """
        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(full_space_config)

        # Benchmarks should NOT be in the serialized output
        assert "benchmarks" not in serialized
        # But the config should still have benchmarks
        assert full_space_config.benchmarks is not None
        assert len(full_space_config.benchmarks.questions) == 1

    def test_minimal_config_serialized(self):
        """Test serializing a minimal config."""
        config = SpaceConfig.minimal(
            space_id="min",
            title="Minimal",
            warehouse_id="wh",
            tables=["c.s.t"],
        )
        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        assert serialized["version"] == 2
        assert serialized["config"]["sample_questions"] == []
        assert len(serialized["data_sources"]["tables"]) == 1
        assert "benchmarks" not in serialized  # No benchmarks

    def test_from_api_response(self):
        """Test parsing API response."""
        response = {
            "id": "space123",
            "title": "Response Space",
            "warehouse_id": "wh456",
            "serialized_space": {"version": 2},
        }
        serializer = SpaceSerializer()
        result = serializer.from_api_response(response)

        assert result["id"] == "space123"
        assert result["title"] == "Response Space"

    def test_from_api_to_config_full(self):
        """Test converting full API response to SpaceConfig."""
        response = {
            "title": "API Space",
            "warehouse_id": "wh789",
            "parent_path": "/Workspace/API",
            "serialized_space": {
                "version": 2,
                "config": {"sample_questions": [{"id": "sq1", "question": ["What is total?"]}]},
                "data_sources": {
                    "tables": [
                        {
                            "identifier": "cat.sch.tbl",
                            "column_configs": [
                                {
                                    "column_name": "amount",
                                    "description": ["The amount"],
                                    "synonyms": ["value"],
                                    "enable_format_assistance": True,
                                    "enable_entity_matching": True,
                                }
                            ],
                        }
                    ]
                },
                "instructions": {
                    "text_instructions": [{"id": "ti1", "content": ["Instruction"]}],
                    "example_question_sqls": [
                        {
                            "id": "ex1",
                            "question": ["Count?"],
                            "sql": ["SELECT COUNT(*)"],
                            "parameters": [
                                {
                                    "name": "p1",
                                    "type_hint": "INT",
                                    "description": ["A number"],
                                    "default_value": {"values": ["10"]},
                                }
                            ],
                            "usage_guidance": ["Use for counting"],
                        }
                    ],
                    "join_specs": [
                        {
                            "id": "js1",
                            "left": {"identifier": "cat.sch.a", "alias": "a"},
                            "right": {"identifier": "cat.sch.b", "alias": "b"},
                            "sql": ["a.id = b.id"],
                            "instruction": ["Join tables"],
                        }
                    ],
                    "sql_snippets": {
                        "filters": [
                            {
                                "id": "f1",
                                "sql": ["x > 0"],
                                "display_name": "Positive",
                                "instruction": ["Filter positive"],
                                "synonyms": ["pos"],
                            }
                        ],
                        "expressions": [],
                        "measures": [
                            {
                                "id": "m1",
                                "sql": ["SUM(x)"],
                                "display_name": "Sum X",
                            }
                        ],
                    },
                },
            },
        }

        serializer = SpaceSerializer()
        config = serializer.from_api_to_config(response, "test_id")

        # Basic fields
        assert config.space_id == "test_id"
        assert config.title == "API Space"
        assert config.warehouse_id == "wh789"
        assert config.version == 2

        # Sample questions
        assert len(config.sample_questions) == 1
        sq = config.sample_questions[0]
        assert sq.id == "sq1"

        # Column config
        col = config.data_sources.tables[0].column_configs[0]
        assert col.column_name == "amount"
        assert col.enable_format_assistance is True
        assert col.enable_entity_matching is True

        # Example question with parameters
        ex = config.instructions.example_question_sqls[0]
        assert ex.id == "ex1"
        assert len(ex.parameters) == 1
        assert ex.parameters[0].name == "p1"
        assert ex.parameters[0].default_value.values == ["10"]
        assert ex.usage_guidance == ["Use for counting"]

        # Join specs
        js = config.instructions.join_specs[0]
        assert js.left.identifier == "cat.sch.a"
        assert js.left.alias == "a"

        # SQL snippets
        assert len(config.instructions.sql_snippets.filters) == 1
        assert len(config.instructions.sql_snippets.measures) == 1
        assert config.instructions.sql_snippets.filters[0].display_name == "Positive"


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_serialize_config(self, full_space_config: SpaceConfig):
        """Test serialize_config function."""
        result = serialize_config(full_space_config)
        assert "title" in result
        assert "serialized_space" in result

    def test_serialize_for_api(self, full_space_config: SpaceConfig):
        """Test serialize_for_api function."""
        result = serialize_for_api(full_space_config)
        assert "version" in result
        assert "config" in result

    def test_configs_to_api_requests(self, full_space_config: SpaceConfig):
        """Test batch conversion."""
        configs = [full_space_config, full_space_config]
        results = configs_to_api_requests(configs)
        assert len(results) == 2


# =============================================================================
# Edge Case Tests for Serializer
# =============================================================================


class TestSerializerEdgeCases:
    """Edge case tests for serialization/deserialization."""

    def test_serialize_empty_instructions(self):
        """Test serializing space with empty instructions."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            instructions=Instructions(
                text_instructions=[],
                example_question_sqls=[],
                join_specs=[],
            ),
        )
        serializer = SpaceSerializer()
        result = serializer.to_serialized_space(config)

        # Empty lists should not be included or should be empty
        instructions = result.get("instructions", {})
        assert instructions.get("text_instructions", []) == []

    def test_serialize_default_instructions(self):
        """Test serializing space with default (empty) instructions."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            # No explicit instructions - uses default empty Instructions
        )
        serializer = SpaceSerializer()
        result = serializer.to_serialized_space(config)

        # Empty instructions should result in empty or no instructions key
        instructions = result.get("instructions", {})
        assert instructions.get("text_instructions", []) == []

    def test_serialize_empty_sql_snippets(self):
        """Test serializing empty sql_snippets."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            instructions=Instructions(
                sql_snippets=SqlSnippets(filters=[], expressions=[], measures=[])
            ),
        )
        serializer = SpaceSerializer()
        result = serializer.to_serialized_space(config)

        # Empty sql_snippets should be handled gracefully
        instructions = result.get("instructions", {})
        snippets = instructions.get("sql_snippets", {})
        # Either all empty or no entry
        assert snippets.get("filters", []) == []

    def test_serialize_column_with_flags_true(self):
        """Test serializing column with flags set to true."""
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
                                column_name="col1",
                                enable_format_assistance=True,
                                enable_entity_matching=True,
                            )
                        ],
                    )
                ]
            ),
        )
        serializer = SpaceSerializer()
        result = serializer.to_serialized_space(config)

        # Flags should be present when true
        col = result["data_sources"]["tables"][0]["column_configs"][0]
        assert col.get("enable_format_assistance") is True
        assert col.get("enable_entity_matching") is True

    def test_serialize_column_with_flags_false_omitted(self):
        """Test that false flags are omitted from serialized output."""
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
                                column_name="col1",
                                enable_format_assistance=False,
                                enable_entity_matching=False,
                            )
                        ],
                    )
                ]
            ),
        )
        serializer = SpaceSerializer()
        result = serializer.to_serialized_space(config)

        # False flags may be omitted to keep output clean
        col = result["data_sources"]["tables"][0]["column_configs"][0]
        # Either not present, or explicitly false
        assert col.get("enable_format_assistance", False) is False
        assert col.get("enable_entity_matching", False) is False

    def test_deserialize_missing_optional_fields(self):
        """Test deserializing API response with missing optional fields."""
        response = {
            "id": "space123",
            "title": "Minimal",
            "warehouse_id": "wh",
            "serialized_space": {
                "version": 2,
                # No data_sources, no instructions, no sample_questions
            },
        }
        serializer = SpaceSerializer()
        config = serializer.from_api_to_config(response, "test_id")

        assert config.space_id == "test_id"
        assert config.title == "Minimal"
        # Should have default empty values
        assert config.data_sources.tables == []
        assert config.sample_questions == []

    def test_deserialize_empty_sample_questions(self):
        """Test deserializing with empty sample_questions array."""
        response = {
            "id": "space123",
            "title": "Test",
            "warehouse_id": "wh",
            "serialized_space": {
                "version": 2,
                "config": {"sample_questions": []},
            },
        }
        serializer = SpaceSerializer()
        config = serializer.from_api_to_config(response, "test_id")

        assert config.sample_questions == []

    def test_round_trip_preserves_empty_lists(self):
        """Test that round-trip preserves empty list fields."""
        original = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            sample_questions=[],
            data_sources=DataSources(
                tables=[
                    TableConfig(
                        identifier="c.s.t",
                        description=[],
                        column_configs=[],
                    )
                ]
            ),
            instructions=Instructions(
                text_instructions=[],
                join_specs=[],
            ),
        )

        serializer = SpaceSerializer()

        # Serialize
        serialized = serializer.to_serialized_space(original)
        api_format = {
            "id": "test123",
            "title": original.title,
            "warehouse_id": original.warehouse_id,
            "serialized_space": serialized,
        }

        # Deserialize back
        restored = serializer.from_api_to_config(api_format, "test")

        # Verify structure preserved
        assert restored.sample_questions == []
        assert restored.data_sources.tables[0].column_configs == []

    def test_deserialize_parameter_without_default(self):
        """Test deserializing parameter without default_value."""
        response = {
            "id": "space123",
            "title": "Test",
            "warehouse_id": "wh",
            "serialized_space": {
                "version": 2,
                "instructions": {
                    "example_question_sqls": [
                        {
                            "question": ["Q?"],
                            "sql": ["SELECT 1"],
                            "parameters": [
                                {
                                    "name": "p1",
                                    "type_hint": "STRING",
                                    "description": ["Desc"],
                                    # No default_value
                                }
                            ],
                        }
                    ]
                },
            },
        }
        serializer = SpaceSerializer()
        config = serializer.from_api_to_config(response, "test_id")

        param = config.instructions.example_question_sqls[0].parameters[0]
        assert param.name == "p1"
        assert param.default_value is None

    def test_deserialize_join_without_aliases(self):
        """Test deserializing join spec without table aliases."""
        response = {
            "id": "space123",
            "title": "Test",
            "warehouse_id": "wh",
            "serialized_space": {
                "version": 2,
                "instructions": {
                    "join_specs": [
                        {
                            "left": {"identifier": "c.s.a"},
                            "right": {"identifier": "c.s.b"},
                            "sql": ["a.id = b.id"],
                        }
                    ]
                },
            },
        }
        serializer = SpaceSerializer()
        config = serializer.from_api_to_config(response, "test_id")

        join = config.instructions.join_specs[0]
        assert join.left.identifier == "c.s.a"
        assert join.left.alias is None
        assert join.right.alias is None

    def test_serialize_multiline_sql(self):
        """Test serializing SQL with multiline content."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            instructions=Instructions(
                example_question_sqls=[
                    ExampleQuestionSQL(
                        question=["Q?"],
                        sql=["SELECT\n  col1,\n  col2\nFROM table"],
                    )
                ]
            ),
        )
        serializer = SpaceSerializer()
        result = serializer.to_serialized_space(config)

        sql = result["instructions"]["example_question_sqls"][0]["sql"]
        assert isinstance(sql, list)
        assert "\n" in sql[0]

    def test_deserialize_sql_snippets_partial(self):
        """Test deserializing sql_snippets with only some types."""
        response = {
            "id": "space123",
            "title": "Test",
            "warehouse_id": "wh",
            "serialized_space": {
                "version": 2,
                "instructions": {
                    "sql_snippets": {
                        "filters": [{"sql": ["x > 0"], "display_name": "Positive"}],
                        # No expressions or measures
                    }
                },
            },
        }
        serializer = SpaceSerializer()
        config = serializer.from_api_to_config(response, "test_id")

        snippets = config.instructions.sql_snippets
        assert len(snippets.filters) == 1
        assert snippets.expressions == []
        assert snippets.measures == []


class TestAPIRequirements:
    """Tests for API-specific requirements discovered during integration testing."""

    def test_uuid_auto_generation_for_sample_questions(self):
        """Test that sample questions without IDs get auto-generated UUIDs."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            sample_questions=[
                SampleQuestion(question=["Q1?"]),  # No ID - should get UUID
                SampleQuestion(id="existing_id", question=["Q2?"]),  # Has ID - preserved
                "Q3?",  # String format - should get UUID
            ],
        )
        serializer = SpaceSerializer()
        result = serializer.to_serialized_space(config)

        questions = result["config"]["sample_questions"]
        assert len(questions) == 3
        # All should have IDs
        for q in questions:
            assert "id" in q
            assert len(q["id"]) > 0  # Has some ID
        # Existing ID should be preserved
        assert any(q["id"] == "existing_id" for q in questions)
        # Auto-generated IDs should be 32 chars (UUID hex)
        auto_generated = [q for q in questions if q["id"] != "existing_id"]
        assert len(auto_generated) == 2
        for q in auto_generated:
            assert len(q["id"]) == 32, (
                f"Auto-generated ID should be 32 hex chars, got {len(q['id'])}"
            )

    def test_uuid_auto_generation_for_text_instructions(self):
        """Test that text instructions without IDs get auto-generated UUIDs.

        Note: The Databricks Genie API only allows ONE text_instruction,
        so multiple instructions are combined into a single one.
        The first instruction with an ID is used, otherwise a UUID is generated.
        """
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            instructions=Instructions(
                text_instructions=[
                    TextInstruction(content=["Instruction 1"]),  # No ID
                    TextInstruction(id="ti_existing", content=["Instruction 2"]),
                ]
            ),
        )
        serializer = SpaceSerializer()
        result = serializer.to_serialized_space(config)

        # API limitation: only ONE text_instruction allowed, so they're combined
        instructions = result["instructions"]["text_instructions"]
        assert len(instructions) == 1

        combined = instructions[0]
        assert "id" in combined
        # Content from both instructions should be combined
        assert "Instruction 1" in combined["content"]
        assert "Instruction 2" in combined["content"]
        # First instruction with ID should be used (ti_existing is second but first with ID)
        assert combined["id"] == "ti_existing"

    def test_uuid_auto_generation_for_text_instructions_no_id(self):
        """Test that text instructions without any IDs get auto-generated UUID."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            instructions=Instructions(
                text_instructions=[
                    TextInstruction(content=["Instruction 1"]),  # No ID
                    TextInstruction(content=["Instruction 2"]),  # No ID
                ]
            ),
        )
        serializer = SpaceSerializer()
        result = serializer.to_serialized_space(config)

        instructions = result["instructions"]["text_instructions"]
        assert len(instructions) == 1

        combined = instructions[0]
        assert "id" in combined
        assert len(combined["id"]) == 32  # UUID hex is 32 chars
        # Content from both instructions should be combined
        assert "Instruction 1" in combined["content"]
        assert "Instruction 2" in combined["content"]

    def test_uuid_auto_generation_for_join_specs(self):
        """Test that join specs without IDs get auto-generated UUIDs."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            instructions=Instructions(
                join_specs=[
                    JoinSpec(
                        left=JoinTableRef(identifier="c.s.t1"),
                        right=JoinTableRef(identifier="c.s.t2"),
                        sql=["t1.id = t2.id"],
                    )  # No ID
                ]
            ),
        )
        serializer = SpaceSerializer()
        result = serializer.to_serialized_space(config)

        join_specs = result["instructions"]["join_specs"]
        assert len(join_specs) == 1
        assert "id" in join_specs[0]
        assert len(join_specs[0]["id"]) == 32

    def test_arrays_sorted_by_id(self):
        """Test that instruction arrays are sorted by ID as required by API."""
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
        result = serializer.to_serialized_space(config)

        instructions = result["instructions"]["text_instructions"]
        ids = [inst["id"] for inst in instructions]
        assert ids == sorted(ids), "Text instructions should be sorted by ID"

    def test_sql_functions_identifier_only(self):
        """Test that sql_functions only includes identifier (not description)."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            instructions=Instructions(
                sql_functions=[
                    SqlFunction(
                        identifier="cat.sch.my_func",
                        description="This description should NOT be in output",
                    )
                ]
            ),
        )
        serializer = SpaceSerializer()
        result = serializer.to_serialized_space(config)

        funcs = result["instructions"]["sql_functions"]
        assert len(funcs) == 1
        assert funcs[0]["identifier"] == "cat.sch.my_func"
        assert "description" not in funcs[0], "description should not be sent to API"

    def test_sql_snippets_sorted_by_id(self):
        """Test that SQL snippets are sorted by ID."""
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            instructions=Instructions(
                sql_snippets=SqlSnippets(
                    filters=[
                        SqlSnippet(id="z_filter", sql=["z"], display_name="Z"),
                        SqlSnippet(id="a_filter", sql=["a"], display_name="A"),
                    ]
                )
            ),
        )
        serializer = SpaceSerializer()
        result = serializer.to_serialized_space(config)

        filters = result["instructions"]["sql_snippets"]["filters"]
        ids = [f["id"] for f in filters]
        assert ids == sorted(ids), "Filters should be sorted by ID"

    def test_round_trip_preserves_all_fields(self):
        """Test that serializing and deserializing preserves all data."""
        original = SpaceConfig(
            space_id="test_space",
            title="Test Space",
            warehouse_id="wh123",
            parent_path="/Workspace/Test",
            version=2,
            sample_questions=[
                SampleQuestion(id="sq1", question=["Q1?", "Q1 alt?"]),
            ],
            data_sources=DataSources(
                tables=[
                    TableConfig(
                        identifier="cat.sch.tbl",
                        description=["Table desc"],
                        column_configs=[
                            ColumnConfig(
                                column_name="col1",
                                description=["Col desc"],
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
                    TextInstruction(id="ti1", content=["Do this"]),
                ],
                example_question_sqls=[
                    ExampleQuestionSQL(
                        id="eq1",
                        question=["Q?"],
                        sql=["SELECT 1"],
                        parameters=[
                            ParameterConfig(
                                name="p1",
                                type_hint="STRING",
                                description=["Param desc"],
                                default_value=ParameterDefaultValue(values=["default"]),
                            )
                        ],
                        usage_guidance=["Use this for X"],
                    )
                ],
                join_specs=[
                    JoinSpec(
                        id="js1",
                        left=JoinTableRef(identifier="c.s.t1", alias="t1"),
                        right=JoinTableRef(identifier="c.s.t2", alias="t2"),
                        sql=["t1.id = t2.id"],
                        instruction=["Join desc"],
                    )
                ],
                sql_snippets=SqlSnippets(
                    filters=[
                        SqlSnippet(
                            id="f1",
                            sql=["status = 'active'"],
                            display_name="Active",
                            instruction=["Filter instruction"],
                            synonyms=["live"],
                        )
                    ],
                ),
            ),
        )

        # Serialize to API format
        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(original)

        # Create mock API response
        api_response = {
            "id": "databricks_id",
            "title": original.title,
            "warehouse_id": original.warehouse_id,
            "parent_path": original.parent_path,
            "serialized_space": serialized,
        }

        # Deserialize back to config
        restored = serializer.from_api_to_config(api_response, "test_space")

        # Verify key fields are preserved
        assert restored.title == original.title
        assert restored.warehouse_id == original.warehouse_id
        assert len(restored.sample_questions) == len(original.sample_questions)
        assert restored.sample_questions[0].question == original.sample_questions[0].question

        # Verify table config
        assert len(restored.data_sources.tables) == 1
        assert restored.data_sources.tables[0].identifier == "cat.sch.tbl"
        assert restored.data_sources.tables[0].column_configs[0].enable_format_assistance

        # Verify instructions
        assert len(restored.instructions.text_instructions) == 1
        assert restored.instructions.text_instructions[0].content == ["Do this"]

        # Verify example SQL with parameters
        assert len(restored.instructions.example_question_sqls) == 1
        eq = restored.instructions.example_question_sqls[0]
        assert eq.parameters[0].name == "p1"
        assert eq.parameters[0].default_value.values == ["default"]

        # Verify join specs
        assert len(restored.instructions.join_specs) == 1
        js = restored.instructions.join_specs[0]
        assert js.left.alias == "t1"
        assert js.right.alias == "t2"

        # Verify sql snippets
        assert len(restored.instructions.sql_snippets.filters) == 1
        assert restored.instructions.sql_snippets.filters[0].synonyms == ["live"]


class TestSpaceToYaml:
    """Tests for space_to_yaml convenience function."""

    def test_space_to_yaml_basic(self):
        """Test basic space to YAML conversion."""
        import yaml

        # Create a mock API response
        api_response = {
            "id": "01abc123def456",
            "title": "Test Space",
            "warehouse_id": "wh_123",
            "parent_path": "/Workspace/Users/test",
            "serialized_space": {
                "version": 2,
                "config": {"sample_questions": [{"id": "sq1", "question": ["What is revenue?"]}]},
                "data_sources": {
                    "tables": [
                        {
                            "identifier": "catalog.schema.sales",
                            "description": ["Sales data"],
                        }
                    ]
                },
                "instructions": {},
            },
        }

        # Convert to YAML
        yaml_str = space_to_yaml(api_response)

        # Parse the YAML to verify structure
        data = yaml.safe_load(yaml_str)
        assert data["version"] == 2
        assert "spaces" in data
        assert len(data["spaces"]) == 1

        space = data["spaces"][0]
        assert space["title"] == "Test Space"
        assert space["warehouse_id"] == "wh_123"
        assert len(space["data_sources"]["tables"]) == 1

    def test_space_to_yaml_with_instructions(self):
        """Test space to YAML with full instructions."""
        import yaml

        api_response = {
            "id": "space123",
            "title": "Analytics Space",
            "warehouse_id": "wh_456",
            "serialized_space": {
                "version": 2,
                "config": {},
                "data_sources": {
                    "tables": [{"identifier": "cat.sch.tbl", "description": ["Test table"]}]
                },
                "instructions": {
                    "text_instructions": [{"id": "ti1", "content": ["Format dates properly"]}],
                    "join_specs": [
                        {
                            "id": "js1",
                            "left": {"identifier": "cat.sch.t1", "alias": "a"},
                            "right": {"identifier": "cat.sch.t2", "alias": "b"},
                            "sql": ["a.id = b.id"],
                            "instruction": ["Join tables"],
                        }
                    ],
                },
            },
        }

        yaml_str = space_to_yaml(api_response)
        data = yaml.safe_load(yaml_str)

        space = data["spaces"][0]
        assert "instructions" in space
        assert len(space["instructions"]["text_instructions"]) == 1
        assert len(space["instructions"]["join_specs"]) == 1

    def test_space_to_yaml_is_importable(self):
        """Test that space_to_yaml is importable from main package."""
        from genie_forge import space_to_yaml

        assert callable(space_to_yaml)

    def test_space_to_yaml_empty_optional_fields(self):
        """Test that empty optional fields are excluded from output."""
        import yaml

        api_response = {
            "id": "minimal",
            "title": "Minimal Space",
            "warehouse_id": "wh",
            "serialized_space": {
                "version": 2,
                "config": {},
                "data_sources": {"tables": [{"identifier": "c.s.t", "description": []}]},
                "instructions": {},
            },
        }

        yaml_str = space_to_yaml(api_response)
        data = yaml.safe_load(yaml_str)

        space = data["spaces"][0]
        # Empty fields should be excluded
        assert "parent_path" not in space or space.get("parent_path") is None
