"""Unit tests for genie_forge.parsers."""

from pathlib import Path

import pytest
import yaml

from genie_forge.parsers import (
    MetadataParser,
    ParserError,
    VariableResolver,
    load_config,
    validate_config,
)


class TestVariableResolver:
    """Tests for VariableResolver."""

    def test_simple_variable(self):
        """Test resolving a simple variable."""
        resolver = VariableResolver(variables={"name": "test"})
        result = resolver.resolve("Hello ${name}")
        assert result == "Hello test"

    def test_multiple_variables(self):
        """Test resolving multiple variables."""
        resolver = VariableResolver(variables={"catalog": "mycat", "schema": "mysch"})
        result = resolver.resolve("${catalog}.${schema}.table")
        assert result == "mycat.mysch.table"

    def test_env_default(self):
        """Test that env variable is set by default."""
        resolver = VariableResolver(env="prod")
        result = resolver.resolve("Environment: ${env}")
        assert result == "Environment: prod"

    def test_nested_dict(self):
        """Test resolving variables in nested dict."""
        resolver = VariableResolver(variables={"val": "replaced"})
        data = {"key": {"nested": "${val}"}}
        result = resolver.resolve(data)
        assert result["key"]["nested"] == "replaced"

    def test_list_values(self):
        """Test resolving variables in lists."""
        resolver = VariableResolver(variables={"item": "value"})
        data = ["${item}", "static"]
        result = resolver.resolve(data)
        assert result[0] == "value"
        assert result[1] == "static"

    def test_missing_variable_kept(self):
        """Test that missing variables are kept as placeholders."""
        resolver = VariableResolver(variables={})
        result = resolver.resolve("${missing}")
        assert result == "${missing}"

    def test_non_string_passthrough(self):
        """Test that non-strings are passed through."""
        resolver = VariableResolver()
        assert resolver.resolve(123) == 123
        assert resolver.resolve(True) is True
        assert resolver.resolve(None) is None


class TestMetadataParser:
    """Tests for MetadataParser."""

    def test_parse_yaml_file(self, sample_yaml_file: Path):
        """Test parsing a YAML file."""
        parser = MetadataParser()
        configs = parser.parse(sample_yaml_file)
        assert len(configs) == 1
        assert configs[0].space_id == "test_space"
        assert configs[0].title == "Test Space"

    def test_parse_json_file(self, sample_json_file: Path):
        """Test parsing a JSON file."""
        parser = MetadataParser()
        configs = parser.parse(sample_json_file)
        assert len(configs) == 1
        assert configs[0].space_id == "test_space"

    def test_parse_with_variables(self, temp_dir: Path):
        """Test parsing with variable substitution."""
        config = {
            "spaces": [
                {
                    "space_id": "test",
                    "title": "Test",
                    "warehouse_id": "${wh_id}",
                    "data_sources": {"tables": [{"identifier": "${cat}.${sch}.table"}]},
                }
            ]
        }
        file_path = temp_dir / "config.yaml"
        file_path.write_text(yaml.dump(config))

        parser = MetadataParser(variables={"wh_id": "wh123", "cat": "c", "sch": "s"})
        configs = parser.parse(file_path)

        assert configs[0].warehouse_id == "wh123"
        assert configs[0].data_sources.tables[0].identifier == "c.s.table"

    def test_parse_nonexistent_file(self):
        """Test parsing a non-existent file."""
        parser = MetadataParser()
        with pytest.raises(ParserError) as exc_info:
            parser.parse("/nonexistent/file.yaml")
        assert "not found" in str(exc_info.value)

    def test_parse_directory(self, temp_dir: Path, sample_config_dict: dict):
        """Test parsing a directory of configs."""
        # Create multiple files
        for i in range(3):
            config = sample_config_dict.copy()
            config["spaces"][0]["space_id"] = f"space_{i}"
            file_path = temp_dir / f"space_{i}.yaml"
            file_path.write_text(yaml.dump(config))

        parser = MetadataParser()
        configs = parser.parse_directory(temp_dir)
        assert len(configs) == 3

    def test_parse_instructions_with_new_format(self, temp_dir: Path):
        """Test parsing instruction fields with new API format."""
        config = {
            "spaces": [
                {
                    "space_id": "test",
                    "title": "Test",
                    "warehouse_id": "wh",
                    "data_sources": {"tables": [{"identifier": "c.s.t"}]},
                    "instructions": {
                        "text_instructions": [
                            {"id": "ti1", "content": ["Instruction 1"]},
                            "Instruction 2",  # String format for backward compat
                        ],
                        "example_question_sqls": [
                            {
                                "id": "ex1",
                                "question": ["Q1?"],
                                "sql": ["SELECT 1"],
                                "parameters": [
                                    {
                                        "name": "param1",
                                        "type_hint": "STRING",
                                        "description": ["A param"],
                                        "default_value": {"values": ["default"]},
                                    }
                                ],
                                "usage_guidance": ["Use this for testing"],
                            }
                        ],
                        "sql_functions": [
                            {"identifier": "c.s.func"},
                            "c.s.func2",  # String format
                        ],
                        "join_specs": [
                            {
                                "id": "js1",
                                "left": {"identifier": "c.s.left", "alias": "l"},
                                "right": {"identifier": "c.s.right", "alias": "r"},
                                "sql": ["l.id = r.id"],
                                "instruction": ["Join tables"],
                            }
                        ],
                        "sql_snippets": {
                            "filters": [
                                {
                                    "id": "f1",
                                    "sql": ["status = 'active'"],
                                    "display_name": "Active",
                                    "instruction": ["Filter active"],
                                    "synonyms": ["live"],
                                }
                            ],
                            "expressions": [
                                {
                                    "sql": ["CURRENT_DATE"],
                                    "display_name": "Today",
                                }
                            ],
                            "measures": [
                                {
                                    "sql": ["SUM(amount)"],
                                    "display_name": "Total",
                                }
                            ],
                        },
                    },
                }
            ]
        }
        file_path = temp_dir / "config.yaml"
        file_path.write_text(yaml.dump(config))

        parser = MetadataParser()
        configs = parser.parse(file_path)

        inst = configs[0].instructions

        # Text instructions
        assert len(inst.text_instructions) == 2
        assert inst.text_instructions[0].id == "ti1"
        assert inst.text_instructions[0].content == ["Instruction 1"]

        # Example question SQLs with parameters
        assert len(inst.example_question_sqls) == 1
        ex = inst.example_question_sqls[0]
        assert ex.id == "ex1"
        assert len(ex.parameters) == 1
        assert ex.parameters[0].name == "param1"
        assert ex.parameters[0].default_value.values == ["default"]
        assert ex.usage_guidance == ["Use this for testing"]

        # SQL functions
        assert len(inst.sql_functions) == 2

        # Join specs
        assert len(inst.join_specs) == 1
        js = inst.join_specs[0]
        assert js.id == "js1"
        assert js.left.identifier == "c.s.left"
        assert js.left.alias == "l"

        # SQL snippets
        assert len(inst.sql_snippets.filters) == 1
        assert inst.sql_snippets.filters[0].display_name == "Active"
        assert len(inst.sql_snippets.expressions) == 1
        assert len(inst.sql_snippets.measures) == 1

    def test_parse_column_config_with_new_fields(self, temp_dir: Path):
        """Test parsing column configs with enable_format_assistance and enable_entity_matching."""
        config = {
            "spaces": [
                {
                    "space_id": "test",
                    "title": "Test",
                    "warehouse_id": "wh",
                    "data_sources": {
                        "tables": [
                            {
                                "identifier": "c.s.t",
                                "column_configs": [
                                    {
                                        "column_name": "status",
                                        "description": ["Status field"],
                                        "synonyms": ["state"],
                                        "enable_format_assistance": True,
                                        "enable_entity_matching": True,
                                    }
                                ],
                            }
                        ]
                    },
                }
            ]
        }
        file_path = temp_dir / "config.yaml"
        file_path.write_text(yaml.dump(config))

        parser = MetadataParser()
        configs = parser.parse(file_path)

        col = configs[0].data_sources.tables[0].column_configs[0]
        assert col.column_name == "status"
        assert col.description == ["Status field"]
        assert col.enable_format_assistance is True
        assert col.enable_entity_matching is True

    def test_parse_sample_questions_mixed_formats(self, temp_dir: Path):
        """Test parsing sample questions with mixed string and object formats."""
        config = {
            "spaces": [
                {
                    "space_id": "test",
                    "title": "Test",
                    "warehouse_id": "wh",
                    "data_sources": {"tables": [{"identifier": "c.s.t"}]},
                    "sample_questions": [
                        "Simple question?",
                        {"id": "sq1", "question": ["Complex question?"]},
                    ],
                }
            ]
        }
        file_path = temp_dir / "config.yaml"
        file_path.write_text(yaml.dump(config))

        parser = MetadataParser()
        configs = parser.parse(file_path)

        sq = configs[0].sample_questions
        assert len(sq) == 2
        # First is string
        assert sq[0] == "Simple question?"
        # Second is SampleQuestion
        assert sq[1].id == "sq1"
        assert sq[1].question == ["Complex question?"]

    def test_parse_backward_compat_join_specs(self, temp_dir: Path):
        """Test parsing join specs with old format (backward compatibility)."""
        config = {
            "spaces": [
                {
                    "space_id": "test",
                    "title": "Test",
                    "warehouse_id": "wh",
                    "data_sources": {"tables": [{"identifier": "c.s.t"}]},
                    "instructions": {
                        "join_specs": [
                            {
                                "left_table": "c.s.left",
                                "right_table": "c.s.right",
                                "join_type": "LEFT",
                                "join_condition": "left.id = right.id",
                                "description": "Join description",
                            }
                        ],
                    },
                }
            ]
        }
        file_path = temp_dir / "config.yaml"
        file_path.write_text(yaml.dump(config))

        parser = MetadataParser()
        configs = parser.parse(file_path)

        js = configs[0].instructions.join_specs[0]
        assert js.left.identifier == "c.s.left"
        assert js.right.identifier == "c.s.right"
        assert js.sql[0] == "left.id = right.id"
        # Old join_type becomes comment in sql
        assert "--rt=FROM_RELATIONSHIP_TYPE_LEFT--" in js.sql[1]


class TestValidateConfig:
    """Tests for validate_config function."""

    def test_valid_config(self, sample_yaml_file: Path):
        """Test validating a valid config."""
        errors = validate_config(sample_yaml_file)
        assert len(errors) == 0

    def test_missing_required_fields(self, temp_dir: Path):
        """Test validation catches missing required fields."""
        config = {"spaces": [{"title": "Test"}]}  # Missing space_id, warehouse_id
        file_path = temp_dir / "invalid.yaml"
        file_path.write_text(yaml.dump(config))

        errors = validate_config(file_path)
        assert len(errors) > 0
        assert any("space_id" in e for e in errors)

    def test_nonexistent_file(self):
        """Test validation of non-existent file."""
        errors = validate_config("/nonexistent/file.yaml")
        assert len(errors) == 1
        assert "not found" in errors[0].lower()


class TestLoadConfig:
    """Tests for load_config convenience function."""

    def test_load_config(self, sample_yaml_file: Path):
        """Test the load_config convenience function."""
        configs = load_config(sample_yaml_file)
        assert len(configs) == 1
        assert configs[0].space_id == "test_space"


class TestParameterDefaultValueFormats:
    """Tests for parsing parameter default_value in multiple formats."""

    def test_api_format_with_values_array(self, temp_dir: Path):
        """Test parsing default_value in API format: {values: [...]}."""
        config = {
            "spaces": [
                {
                    "space_id": "test",
                    "title": "Test",
                    "warehouse_id": "wh",
                    "instructions": {
                        "example_question_sqls": [
                            {
                                "id": "eq1",
                                "question": ["Q?"],
                                "sql": ["SELECT :param"],
                                "parameters": [
                                    {
                                        "name": "param",
                                        "type_hint": "STRING",
                                        "default_value": {"values": ["default_value"]},
                                    }
                                ],
                            }
                        ]
                    },
                }
            ]
        }
        file_path = temp_dir / "api_format.yaml"
        file_path.write_text(yaml.dump(config))

        parser = MetadataParser()
        configs = parser.parse(file_path)

        param = configs[0].instructions.example_question_sqls[0].parameters[0]
        assert param.default_value is not None
        assert param.default_value.values == ["default_value"]

    def test_yaml_format_with_type_and_value(self, temp_dir: Path):
        """Test parsing default_value in YAML format: {type: LITERAL, value: ...}."""
        config = {
            "spaces": [
                {
                    "space_id": "test",
                    "title": "Test",
                    "warehouse_id": "wh",
                    "instructions": {
                        "example_question_sqls": [
                            {
                                "id": "eq1",
                                "question": ["Q?"],
                                "sql": ["SELECT :param"],
                                "parameters": [
                                    {
                                        "name": "param",
                                        "type_hint": "STRING",
                                        "default_value": {
                                            "type": "LITERAL",
                                            "value": "literal_value",
                                        },
                                    }
                                ],
                            }
                        ]
                    },
                }
            ]
        }
        file_path = temp_dir / "yaml_format.yaml"
        file_path.write_text(yaml.dump(config))

        parser = MetadataParser()
        configs = parser.parse(file_path)

        param = configs[0].instructions.example_question_sqls[0].parameters[0]
        assert param.default_value is not None
        assert param.default_value.values == ["literal_value"]

    def test_direct_list_format(self, temp_dir: Path):
        """Test parsing default_value as direct list."""
        config = {
            "spaces": [
                {
                    "space_id": "test",
                    "title": "Test",
                    "warehouse_id": "wh",
                    "instructions": {
                        "example_question_sqls": [
                            {
                                "id": "eq1",
                                "question": ["Q?"],
                                "sql": ["SELECT :param"],
                                "parameters": [
                                    {
                                        "name": "param",
                                        "type_hint": "STRING",
                                        "default_value": ["list_value"],
                                    }
                                ],
                            }
                        ]
                    },
                }
            ]
        }
        file_path = temp_dir / "list_format.yaml"
        file_path.write_text(yaml.dump(config))

        parser = MetadataParser()
        configs = parser.parse(file_path)

        param = configs[0].instructions.example_question_sqls[0].parameters[0]
        assert param.default_value is not None
        assert param.default_value.values == ["list_value"]

    def test_direct_string_format(self, temp_dir: Path):
        """Test parsing default_value as direct string."""
        config = {
            "spaces": [
                {
                    "space_id": "test",
                    "title": "Test",
                    "warehouse_id": "wh",
                    "instructions": {
                        "example_question_sqls": [
                            {
                                "id": "eq1",
                                "question": ["Q?"],
                                "sql": ["SELECT :param"],
                                "parameters": [
                                    {
                                        "name": "param",
                                        "type_hint": "STRING",
                                        "default_value": "string_value",
                                    }
                                ],
                            }
                        ]
                    },
                }
            ]
        }
        file_path = temp_dir / "string_format.yaml"
        file_path.write_text(yaml.dump(config))

        parser = MetadataParser()
        configs = parser.parse(file_path)

        param = configs[0].instructions.example_question_sqls[0].parameters[0]
        assert param.default_value is not None
        assert param.default_value.values == ["string_value"]

    def test_no_default_value(self, temp_dir: Path):
        """Test parsing parameter without default_value."""
        config = {
            "spaces": [
                {
                    "space_id": "test",
                    "title": "Test",
                    "warehouse_id": "wh",
                    "instructions": {
                        "example_question_sqls": [
                            {
                                "id": "eq1",
                                "question": ["Q?"],
                                "sql": ["SELECT :param"],
                                "parameters": [
                                    {
                                        "name": "param",
                                        "type_hint": "STRING",
                                        # No default_value
                                    }
                                ],
                            }
                        ]
                    },
                }
            ]
        }
        file_path = temp_dir / "no_default.yaml"
        file_path.write_text(yaml.dump(config))

        parser = MetadataParser()
        configs = parser.parse(file_path)

        param = configs[0].instructions.example_question_sqls[0].parameters[0]
        assert param.default_value is None
