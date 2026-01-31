"""Unit tests for genie_forge.models."""

import pytest
from pydantic import ValidationError

from genie_forge.models import (
    ColumnConfig,
    DataSources,
    ExampleQuestionSQL,
    Instructions,
    JoinSpec,
    JoinTableRef,
    ParameterConfig,
    ParameterDefaultValue,
    Plan,
    PlanAction,
    PlanItem,
    SampleQuestion,
    SpaceConfig,
    SpaceState,
    SpaceStatus,
    SqlSnippet,
    SqlSnippets,
    TableConfig,
    TextInstruction,
)


class TestColumnConfig:
    """Tests for ColumnConfig model."""

    def test_minimal_column(self):
        """Test creating a column with minimal fields."""
        col = ColumnConfig(column_name="test_col")
        assert col.column_name == "test_col"
        assert col.description == []
        assert col.synonyms == []
        assert col.enable_format_assistance is False
        assert col.enable_entity_matching is False

    def test_full_column(self):
        """Test creating a column with all fields."""
        col = ColumnConfig(
            column_name="region",
            description=["Sales region"],
            synonyms=["territory", "area"],
            enable_format_assistance=True,
            enable_entity_matching=True,
        )
        assert col.column_name == "region"
        assert col.description == ["Sales region"]
        assert len(col.synonyms) == 2
        assert col.enable_format_assistance is True
        assert col.enable_entity_matching is True

    def test_description_string_to_list(self):
        """Test that string description is normalized to list."""
        col = ColumnConfig(column_name="test", description="Single description")
        assert col.description == ["Single description"]

    def test_description_none_to_empty_list(self):
        """Test that None description becomes empty list."""
        col = ColumnConfig(column_name="test", description=None)
        assert col.description == []


class TestTableConfig:
    """Tests for TableConfig model."""

    def test_minimal_table(self):
        """Test creating a table with minimal fields."""
        table = TableConfig(identifier="catalog.schema.table")
        assert table.identifier == "catalog.schema.table"
        assert table.description == []
        assert table.column_configs == []

    def test_invalid_identifier(self):
        """Test that invalid identifier raises error."""
        with pytest.raises(ValidationError):
            TableConfig(identifier="invalid_table")

    def test_valid_identifier_formats(self):
        """Test valid identifier formats."""
        valid_ids = [
            "cat.sch.tbl",
            "my_catalog.my_schema.my_table",
            "CATALOG.SCHEMA.TABLE",
        ]
        for id_ in valid_ids:
            table = TableConfig(identifier=id_)
            assert table.identifier == id_


class TestSampleQuestion:
    """Tests for SampleQuestion model."""

    def test_sample_question_with_id(self):
        """Test creating a sample question with ID."""
        sq = SampleQuestion(id="q123", question=["What is the total?"])
        assert sq.id == "q123"
        assert sq.question == ["What is the total?"]

    def test_sample_question_string_to_list(self):
        """Test that string question is normalized to list."""
        sq = SampleQuestion(question="Single question")
        assert sq.question == ["Single question"]


class TestTextInstruction:
    """Tests for TextInstruction model."""

    def test_text_instruction_with_id(self):
        """Test creating a text instruction with ID."""
        ti = TextInstruction(id="inst123", content=["Do this", "And that"])
        assert ti.id == "inst123"
        assert ti.content == ["Do this", "And that"]

    def test_text_instruction_string_to_list(self):
        """Test that string content is normalized to list."""
        ti = TextInstruction(content="Single instruction")
        assert ti.content == ["Single instruction"]


class TestParameterConfig:
    """Tests for ParameterConfig model."""

    def test_full_parameter(self):
        """Test creating a parameter with all fields."""
        param = ParameterConfig(
            name="date_param",
            type_hint="DATE",
            description=["Select a date"],
            default_value=ParameterDefaultValue(values=["2024-01-01"]),
        )
        assert param.name == "date_param"
        assert param.type_hint == "DATE"
        assert param.description == ["Select a date"]
        assert param.default_value.values == ["2024-01-01"]

    def test_minimal_parameter(self):
        """Test creating a parameter with minimal fields."""
        param = ParameterConfig(name="test_param")
        assert param.name == "test_param"
        assert param.type_hint == "STRING"
        assert param.description == []
        assert param.default_value is None


class TestExampleQuestionSQL:
    """Tests for ExampleQuestionSQL model."""

    def test_full_example_question(self):
        """Test creating an example question with all fields."""
        eq = ExampleQuestionSQL(
            id="ex123",
            question=["How many orders?"],
            sql=["SELECT COUNT(*) FROM orders"],
            parameters=[ParameterConfig(name="status")],
            usage_guidance=["Use for order counts"],
        )
        assert eq.id == "ex123"
        assert eq.question == ["How many orders?"]
        assert eq.sql == ["SELECT COUNT(*) FROM orders"]
        assert len(eq.parameters) == 1
        assert eq.usage_guidance == ["Use for order counts"]

    def test_string_normalization(self):
        """Test that strings are normalized to lists."""
        eq = ExampleQuestionSQL(question="Q?", sql="SELECT 1")
        assert eq.question == ["Q?"]
        assert eq.sql == ["SELECT 1"]


class TestJoinSpec:
    """Tests for JoinSpec model."""

    def test_valid_join(self):
        """Test creating a valid join spec with new structure."""
        join = JoinSpec(
            id="join123",
            left=JoinTableRef(identifier="cat.sch.left", alias="l"),
            right=JoinTableRef(identifier="cat.sch.right", alias="r"),
            sql=["l.id = r.id", "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_MANY--"],
            instruction=["Use for aggregation"],
        )
        assert join.id == "join123"
        assert join.left.identifier == "cat.sch.left"
        assert join.left.alias == "l"
        assert join.right.identifier == "cat.sch.right"
        assert len(join.sql) == 2
        assert join.instruction == ["Use for aggregation"]

    def test_minimal_join(self):
        """Test creating a join with minimal fields."""
        join = JoinSpec(
            left=JoinTableRef(identifier="cat.sch.left"),
            right=JoinTableRef(identifier="cat.sch.right"),
            sql=["left.id = right.id"],
        )
        assert join.id is None
        assert join.left.alias is None
        assert join.instruction == []


class TestSqlSnippet:
    """Tests for SqlSnippet model."""

    def test_full_snippet(self):
        """Test creating a snippet with all fields."""
        snippet = SqlSnippet(
            id="snip123",
            sql=["SUM(amount)"],
            display_name="Total Amount",
            instruction=["Use for sum calculations"],
            synonyms=["total", "sum_amount"],
        )
        assert snippet.id == "snip123"
        assert snippet.sql == ["SUM(amount)"]
        assert snippet.display_name == "Total Amount"
        assert len(snippet.synonyms) == 2


class TestSqlSnippets:
    """Tests for SqlSnippets container model."""

    def test_all_snippet_types(self):
        """Test creating snippets with all types."""
        snippets = SqlSnippets(
            filters=[SqlSnippet(sql=["status = 'active'"], display_name="Active Only")],
            expressions=[SqlSnippet(sql=["CURRENT_DATE"], display_name="Today")],
            measures=[SqlSnippet(sql=["SUM(sales)"], display_name="Total Sales")],
        )
        assert len(snippets.filters) == 1
        assert len(snippets.expressions) == 1
        assert len(snippets.measures) == 1


class TestInstructions:
    """Tests for Instructions model."""

    def test_instructions_with_snippets(self):
        """Test creating instructions with sql_snippets."""
        inst = Instructions(
            text_instructions=[TextInstruction(content=["Do this"])],
            sql_snippets=SqlSnippets(filters=[SqlSnippet(sql=["x > 0"], display_name="Positive")]),
        )
        assert len(inst.text_instructions) == 1
        assert len(inst.sql_snippets.filters) == 1


class TestSpaceConfig:
    """Tests for SpaceConfig model."""

    def test_minimal_space(self):
        """Test creating a minimal space config."""
        space = SpaceConfig.minimal(
            space_id="test",
            title="Test Space",
            warehouse_id="wh123",
            tables=["cat.sch.tbl"],
        )
        assert space.space_id == "test"
        assert space.title == "Test Space"
        assert len(space.data_sources.tables) == 1
        assert space.version == 2  # Default is now version 2

    def test_sample_questions_mixed_formats(self):
        """Test sample questions with mixed string and object formats."""
        space = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            sample_questions=[
                "Simple question?",
                SampleQuestion(id="q1", question=["Complex question?"]),
            ],
        )
        assert len(space.sample_questions) == 2
        # First is string
        assert space.sample_questions[0] == "Simple question?"
        # Second is SampleQuestion
        assert isinstance(space.sample_questions[1], SampleQuestion)

    def test_get_sample_questions_as_objects(self):
        """Test converting sample questions to objects."""
        space = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            sample_questions=["Q1?", SampleQuestion(question=["Q2?"])],
        )
        objs = space.get_sample_questions_as_objects()
        assert len(objs) == 2
        assert all(isinstance(q, SampleQuestion) for q in objs)

    def test_config_hash_consistency(self):
        """Test that config hash is consistent."""
        space = SpaceConfig.minimal(
            space_id="test",
            title="Test Space",
            warehouse_id="wh123",
            tables=["cat.sch.tbl"],
        )
        hash1 = space.config_hash()
        hash2 = space.config_hash()
        assert hash1 == hash2

    def test_config_hash_changes_with_content(self):
        """Test that config hash changes when content changes."""
        space1 = SpaceConfig.minimal(
            space_id="test",
            title="Test Space",
            warehouse_id="wh123",
            tables=["cat.sch.tbl"],
        )
        space2 = SpaceConfig.minimal(
            space_id="test",
            title="Different Title",
            warehouse_id="wh123",
            tables=["cat.sch.tbl"],
        )
        assert space1.config_hash() != space2.config_hash()

    def test_get_table_identifiers(self):
        """Test getting table identifiers."""
        space = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            data_sources=DataSources(
                tables=[
                    TableConfig(identifier="cat.sch.tbl1"),
                    TableConfig(identifier="cat.sch.tbl2"),
                ]
            ),
        )
        tables = space.get_table_identifiers()
        assert len(tables) == 2
        assert "cat.sch.tbl1" in tables


class TestPlan:
    """Tests for Plan model."""

    def test_empty_plan(self):
        """Test empty plan properties."""
        plan = Plan(environment="dev")
        assert plan.has_changes is False
        assert len(plan.creates) == 0
        assert len(plan.updates) == 0
        assert len(plan.destroys) == 0

    def test_plan_with_items(self):
        """Test plan with various items."""
        plan = Plan(
            environment="dev",
            items=[
                PlanItem(logical_id="new", action=PlanAction.CREATE),
                PlanItem(logical_id="existing", action=PlanAction.UPDATE),
                PlanItem(logical_id="same", action=PlanAction.NO_CHANGE),
            ],
        )
        assert plan.has_changes is True
        assert len(plan.creates) == 1
        assert len(plan.updates) == 1
        assert len(plan.no_changes) == 1

    def test_plan_summary(self):
        """Test plan summary string."""
        plan = Plan(
            environment="dev",
            items=[
                PlanItem(logical_id="new", action=PlanAction.CREATE),
                PlanItem(logical_id="existing", action=PlanAction.UPDATE),
            ],
        )
        summary = plan.summary()
        assert "1 to create" in summary
        assert "1 to update" in summary


class TestSpaceState:
    """Tests for SpaceState model."""

    def test_space_state_defaults(self):
        """Test default values for space state."""
        state = SpaceState(
            logical_id="test",
            title="Test",
            config_hash="abc123",
        )
        assert state.status == SpaceStatus.PENDING
        assert state.databricks_space_id is None
        assert state.error is None


# =============================================================================
# Edge Case Tests for API v2 Model Structures
# =============================================================================


class TestColumnConfigEdgeCases:
    """Edge case tests for ColumnConfig."""

    def test_empty_description_list(self):
        """Test column with empty description list."""
        col = ColumnConfig(column_name="test", description=[])
        assert col.description == []

    def test_description_with_empty_string(self):
        """Test column with empty string in description list."""
        col = ColumnConfig(column_name="test", description=[""])
        assert col.description == [""]

    def test_description_with_multiline_content(self):
        """Test column with multiline description."""
        col = ColumnConfig(
            column_name="test",
            description=["Line 1\nLine 2", "Line 3\nLine 4"],
        )
        assert len(col.description) == 2
        assert "\n" in col.description[0]

    def test_all_flags_false(self):
        """Test column with all boolean flags explicitly false."""
        col = ColumnConfig(
            column_name="test",
            enable_format_assistance=False,
            enable_entity_matching=False,
        )
        assert col.enable_format_assistance is False
        assert col.enable_entity_matching is False


class TestSampleQuestionEdgeCases:
    """Edge case tests for SampleQuestion."""

    def test_empty_question_list(self):
        """Test sample question with empty question list."""
        sq = SampleQuestion(question=[])
        assert sq.question == []

    def test_question_with_special_characters(self):
        """Test sample question with special characters."""
        sq = SampleQuestion(question=["What's the revenue for Q1'23?"])
        assert "'" in sq.question[0]

    def test_question_with_unicode(self):
        """Test sample question with unicode characters."""
        sq = SampleQuestion(question=["¿Cuál es el total de ventas?"])
        assert "¿" in sq.question[0]


class TestTextInstructionEdgeCases:
    """Edge case tests for TextInstruction."""

    def test_empty_content_list(self):
        """Test text instruction with empty content list."""
        ti = TextInstruction(content=[])
        assert ti.content == []

    def test_content_with_code_block(self):
        """Test text instruction with SQL code block."""
        ti = TextInstruction(content=["```sql\nSELECT * FROM table\n```"])
        assert "```sql" in ti.content[0]


class TestParameterConfigEdgeCases:
    """Edge case tests for ParameterConfig."""

    def test_parameter_without_default(self):
        """Test parameter without default value."""
        param = ParameterConfig(
            name="filter_date",
            type_hint="DATE",
            description=["Date to filter by"],
        )
        assert param.default_value is None

    def test_parameter_with_empty_description(self):
        """Test parameter with empty description."""
        param = ParameterConfig(
            name="test",
            type_hint="STRING",
            description=[],
        )
        assert param.description == []

    def test_description_string_normalized_to_list(self):
        """Test that string description is normalized to list."""
        param = ParameterConfig(
            name="test",
            type_hint="STRING",
            description="A single description",
        )
        assert param.description == ["A single description"]


class TestExampleQuestionSQLEdgeCases:
    """Edge case tests for ExampleQuestionSQL."""

    def test_empty_parameters_list(self):
        """Test example SQL with empty parameters list."""
        eq = ExampleQuestionSQL(
            question=["Test?"],
            sql=["SELECT 1"],
            parameters=[],
        )
        assert eq.parameters == []

    def test_empty_usage_guidance(self):
        """Test example SQL with empty usage guidance."""
        eq = ExampleQuestionSQL(
            question=["Test?"],
            sql=["SELECT 1"],
            usage_guidance=[],
        )
        assert eq.usage_guidance == []

    def test_multiline_sql_in_list(self):
        """Test example SQL with multiline SQL."""
        eq = ExampleQuestionSQL(
            question=["Complex query?"],
            sql=["SELECT\n  col1,\n  col2\nFROM table\nWHERE x > 0"],
        )
        assert "\n" in eq.sql[0]

    def test_sql_with_parameters_and_guidance(self):
        """Test example SQL with all optional fields."""
        eq = ExampleQuestionSQL(
            id="eq123",
            question=["What is the total?"],
            sql=["SELECT SUM(amount) FROM orders WHERE date > :start_date"],
            parameters=[
                ParameterConfig(
                    name="start_date",
                    type_hint="DATE",
                    description=["Start date for filter"],
                    default_value=ParameterDefaultValue(
                        type="RELATIVE_DATE",
                        value="TODAY - 30 DAYS",
                    ),
                )
            ],
            usage_guidance=["Use for monthly totals"],
        )
        assert eq.id == "eq123"
        assert len(eq.parameters) == 1
        assert eq.parameters[0].default_value is not None


class TestJoinSpecEdgeCases:
    """Edge case tests for JoinSpec."""

    def test_join_without_aliases(self):
        """Test join spec without table aliases."""
        join = JoinSpec(
            left=JoinTableRef(identifier="cat.sch.left_table"),
            right=JoinTableRef(identifier="cat.sch.right_table"),
            sql=["left_table.id = right_table.id"],
        )
        assert join.left.alias is None
        assert join.right.alias is None

    def test_join_with_empty_instruction(self):
        """Test join spec with empty instruction list."""
        join = JoinSpec(
            left=JoinTableRef(identifier="a"),
            right=JoinTableRef(identifier="b"),
            sql=["a.id = b.id"],
            instruction=[],
        )
        assert join.instruction == []

    def test_self_join(self):
        """Test self-join configuration."""
        join = JoinSpec(
            left=JoinTableRef(identifier="cat.sch.employees", alias="e"),
            right=JoinTableRef(identifier="cat.sch.employees", alias="m"),
            sql=["e.manager_id = m.employee_id"],
            instruction=["Self-join for manager hierarchy"],
        )
        assert join.left.identifier == join.right.identifier
        assert join.left.alias != join.right.alias


class TestSqlSnippetEdgeCases:
    """Edge case tests for SqlSnippet."""

    def test_snippet_without_id(self):
        """Test snippet without id."""
        snippet = SqlSnippet(
            sql=["x > 0"],
            display_name="Positive Values",
        )
        assert snippet.id is None

    def test_snippet_with_empty_synonyms(self):
        """Test snippet with empty synonyms list."""
        snippet = SqlSnippet(
            sql=["x > 0"],
            display_name="Test",
            synonyms=[],
        )
        assert snippet.synonyms == []

    def test_snippet_with_complex_sql(self):
        """Test snippet with complex SQL expression."""
        snippet = SqlSnippet(
            sql=["CASE WHEN status = 'active' THEN 1 ELSE 0 END"],
            display_name="Is Active Flag",
            instruction=["Returns 1 for active records, 0 otherwise"],
        )
        assert "CASE" in snippet.sql[0]


class TestSqlSnippetsContainerEdgeCases:
    """Edge case tests for SqlSnippets container."""

    def test_all_empty_lists(self):
        """Test snippets container with all empty lists."""
        snippets = SqlSnippets(filters=[], expressions=[], measures=[])
        assert len(snippets.filters) == 0
        assert len(snippets.expressions) == 0
        assert len(snippets.measures) == 0

    def test_only_filters(self):
        """Test snippets with only filters."""
        snippets = SqlSnippets(
            filters=[SqlSnippet(sql=["x > 0"], display_name="Test")],
        )
        assert len(snippets.filters) == 1
        assert len(snippets.expressions) == 0
        assert len(snippets.measures) == 0

    def test_default_empty_lists(self):
        """Test snippets container defaults to empty lists."""
        snippets = SqlSnippets()
        assert snippets.filters == []
        assert snippets.expressions == []
        assert snippets.measures == []


class TestInstructionsEdgeCases:
    """Edge case tests for Instructions."""

    def test_instructions_all_empty(self):
        """Test instructions with all empty lists."""
        inst = Instructions(
            text_instructions=[],
            example_question_sqls=[],
            sql_functions=[],
            join_specs=[],
        )
        assert len(inst.text_instructions) == 0
        assert len(inst.example_question_sqls) == 0

    def test_instructions_with_empty_sql_snippets(self):
        """Test instructions with empty sql_snippets."""
        inst = Instructions(sql_snippets=SqlSnippets())
        assert inst.sql_snippets.filters == []

    def test_instructions_default_sql_snippets_is_empty(self):
        """Test that default sql_snippets is empty SqlSnippets object."""
        inst = Instructions()
        # Default is an empty SqlSnippets, not None
        assert inst.sql_snippets is not None
        assert inst.sql_snippets.filters == []
        assert inst.sql_snippets.expressions == []
        assert inst.sql_snippets.measures == []


class TestSpaceConfigEdgeCases:
    """Edge case tests for SpaceConfig."""

    def test_space_with_empty_sample_questions(self):
        """Test space with empty sample questions list."""
        space = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            sample_questions=[],
        )
        assert space.sample_questions == []

    def test_space_with_default_instructions(self):
        """Test space without explicit instructions gets default."""
        space = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            # No instructions specified
        )
        # Default is an empty Instructions object
        assert space.instructions is not None
        assert space.instructions.text_instructions == []

    def test_space_description_string_preserved(self):
        """Test that string description is preserved (not converted to list)."""
        space = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            description="A simple description",
        )
        assert space.description == "A simple description"

    def test_get_sample_questions_empty_list(self):
        """Test get_sample_questions_as_objects with empty list."""
        space = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            sample_questions=[],
        )
        objs = space.get_sample_questions_as_objects()
        assert objs == []

    def test_minimal_factory_with_single_table(self):
        """Test minimal factory with single table."""
        space = SpaceConfig.minimal(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            tables=["cat.sch.tbl"],
        )
        assert len(space.data_sources.tables) == 1
        assert space.data_sources.tables[0].identifier == "cat.sch.tbl"


class TestBackwardCompatibilityEdgeCases:
    """Tests for backward compatibility with old API formats."""

    def test_column_config_old_string_description(self):
        """Test ColumnConfig handles old string description format."""
        col = ColumnConfig(column_name="test", description="Old format")
        assert isinstance(col.description, list)
        assert col.description == ["Old format"]

    def test_sample_question_old_string_format(self):
        """Test SampleQuestion handles old string format."""
        sq = SampleQuestion(question="Old string question")
        assert isinstance(sq.question, list)
        assert sq.question == ["Old string question"]

    def test_text_instruction_old_string_content(self):
        """Test TextInstruction handles old string content."""
        ti = TextInstruction(content="Old string content")
        assert isinstance(ti.content, list)
        assert ti.content == ["Old string content"]

    def test_example_sql_old_string_question(self):
        """Test ExampleQuestionSQL handles old string question."""
        eq = ExampleQuestionSQL(question="Old question", sql=["SELECT 1"])
        assert isinstance(eq.question, list)
        assert eq.question == ["Old question"]

    def test_example_sql_old_string_sql(self):
        """Test ExampleQuestionSQL handles old string sql."""
        eq = ExampleQuestionSQL(question=["Q?"], sql="SELECT 1")
        assert isinstance(eq.sql, list)
        assert eq.sql == ["SELECT 1"]

    def test_join_spec_sql_string_normalized(self):
        """Test JoinSpec handles string sql (normalized to list)."""
        join = JoinSpec(
            left=JoinTableRef(identifier="a"),
            right=JoinTableRef(identifier="b"),
            sql="a.id = b.id",
        )
        assert isinstance(join.sql, list)
        assert join.sql == ["a.id = b.id"]


class TestValidationEdgeCases:
    """Tests for validation edge cases."""

    def test_column_config_requires_column_name(self):
        """Test that ColumnConfig requires column_name."""
        with pytest.raises(ValidationError):
            ColumnConfig()

    def test_table_config_requires_identifier(self):
        """Test that TableConfig requires identifier."""
        with pytest.raises(ValidationError):
            TableConfig()

    def test_space_config_requires_space_id(self):
        """Test that SpaceConfig requires space_id."""
        with pytest.raises(ValidationError):
            SpaceConfig(title="Test", warehouse_id="wh")

    def test_join_table_ref_requires_identifier(self):
        """Test that JoinTableRef requires identifier."""
        with pytest.raises(ValidationError):
            JoinTableRef()

    def test_sql_snippet_requires_sql_and_display_name(self):
        """Test that SqlSnippet requires sql and display_name."""
        with pytest.raises(ValidationError):
            SqlSnippet(sql=["x > 0"])  # Missing display_name
        with pytest.raises(ValidationError):
            SqlSnippet(display_name="Test")  # Missing sql
