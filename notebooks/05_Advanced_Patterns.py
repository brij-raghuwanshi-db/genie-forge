# Databricks notebook source
# MAGIC %md
# MAGIC # Genie-Forge: Advanced Patterns
# MAGIC
# MAGIC This notebook covers **advanced usage patterns** for power users:
# MAGIC
# MAGIC 1. **Programmatic API** - Build custom workflows
# MAGIC 2. **Self-Joins & Relationship Types** - Configure hierarchical data
# MAGIC 3. **Parameterized Queries** - Dynamic values in example SQLs
# MAGIC 4. **Benchmarks** - Local-only testing
# MAGIC 5. **Demo Tables** - Set up sample data
# MAGIC 6. **Variable Substitution** - Multi-environment configs
# MAGIC 7. **Bulk Operations** - Manage many spaces
# MAGIC 8. **Custom Workflows** - Automation scripts
# MAGIC
# MAGIC ## Prerequisites
# MAGIC - Familiarity with Notebooks 00-04
# MAGIC - Understanding of Genie space concepts
# MAGIC
# MAGIC ## Time: ~25 minutes

# COMMAND ----------

# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------

from genie_forge import GenieClient, SpaceConfig, StateManager, __version__
from genie_forge.models import DataSources, TableConfig, Instructions, TextInstruction
from genie_forge.serializer import SpaceSerializer
from genie_forge.parsers import MetadataParser
from databricks.sdk import WorkspaceClient
import json
import yaml

print(f"✓ Genie-Forge v{__version__}")

w = WorkspaceClient()
client = GenieClient(client=w)
print(f"✓ Connected as: {w.current_user.me().user_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 1. Programmatic API
# MAGIC
# MAGIC Build spaces programmatically instead of using YAML files.

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1a. Minimal Space Config

# COMMAND ----------

# Create a minimal space with just required fields
minimal_config = SpaceConfig.minimal(
    space_id="programmatic_minimal",
    title="Minimal Programmatic Space",
    warehouse_id="your_warehouse_id",
    tables=["catalog.schema.table1", "catalog.schema.table2"]
)

print("MINIMAL CONFIG")
print("=" * 60)
print(f"Space ID:    {minimal_config.space_id}")
print(f"Title:       {minimal_config.title}")
print(f"Warehouse:   {minimal_config.warehouse_id}")
print(f"Tables:      {len(minimal_config.data_sources.tables)}")
print(f"Config Hash: {minimal_config.config_hash()[:20]}...")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1b. Full Space Config with All Options

# COMMAND ----------

# Create a comprehensive config with all options
from genie_forge.models import (
    SpaceConfig, DataSources, TableConfig, ColumnConfig,
    Instructions, TextInstruction, ExampleQuestionSQL,
    SqlFunction, JoinSpec, JoinTableRef, SampleQuestion,
    SqlSnippet, SqlSnippets
)

# Define tables with column configurations
tables = [
    TableConfig(
        identifier="catalog.schema.employees",
        description=["Employee master data with hierarchy"],
        column_configs=[
            ColumnConfig(
                column_name="employee_id",
                description=["Unique employee identifier"],
                enable_format_assistance=True
            ),
            ColumnConfig(
                column_name="manager_id",
                description=["References employee_id of manager (self-join)"],
                enable_entity_matching=True
            ),
            ColumnConfig(
                column_name="salary",
                description=["Annual salary in USD"],
                synonyms=["pay", "compensation"],
                enable_format_assistance=True
            )
        ]
    ),
    TableConfig(
        identifier="catalog.schema.departments",
        description=["Department reference data"]
    )
]

# Define instructions with full API v2 structure
instructions = Instructions(
    text_instructions=[
        TextInstruction(content=["Always format currency with $ and 2 decimal places"]),
        TextInstruction(content=["When asked about 'direct reports', use manager_id relationship"])
    ],
    example_question_sqls=[
        ExampleQuestionSQL(
            question=["Who are the top 5 highest paid employees?"],
            sql=["""
SELECT employee_id, first_name, last_name, salary
FROM catalog.schema.employees
ORDER BY salary DESC
LIMIT 5
            """.strip()],
            usage_guidance=["Use for top performer queries"]
        )
    ],
    sql_functions=[
        SqlFunction(
            identifier="catalog.schema.calculate_bonus",
            description="Calculates annual bonus based on performance"
        )
    ],
    join_specs=[
        JoinSpec(
            left=JoinTableRef(
                identifier="catalog.schema.employees",
                alias="e"
            ),
            right=JoinTableRef(
                identifier="catalog.schema.departments",
                alias="d"
            ),
            sql=["e.department_id = d.department_id"],
            instruction=["Link employees to their department"]
        )
    ],
    sql_snippets=SqlSnippets(
        filters=[
            SqlSnippet(
                sql=["salary > 100000"],
                display_name="High Earners",
                instruction=["Filter to high-earning employees"],
                synonyms=["top earners", "well paid"]
            )
        ],
        measures=[
            SqlSnippet(
                sql=["AVG(salary)"],
                display_name="Average Salary",
                instruction=["Calculate average salary"]
            )
        ]
    )
)

# Create full config
full_config = SpaceConfig(
    space_id="programmatic_full",
    title="Full Programmatic Space",
    warehouse_id="your_warehouse_id",
    description="A comprehensive space built programmatically",
    data_sources=DataSources(tables=tables),
    instructions=instructions,
    sample_questions=[
        SampleQuestion(question=["Show me the organizational hierarchy"]),
        SampleQuestion(question=["What is the average salary by department?"])
    ]
)

print("FULL CONFIG")
print("=" * 60)
print(f"Space ID:         {full_config.space_id}")
print(f"Title:            {full_config.title}")
print(f"Tables:           {len(full_config.data_sources.tables)}")
print(f"Text Instructions:{len(full_config.instructions.text_instructions)}")
print(f"SQL Examples:     {len(full_config.instructions.example_question_sqls)}")
print(f"Functions:        {len(full_config.instructions.sql_functions)}")
print(f"Join Specs:       {len(full_config.instructions.join_specs)}")
print(f"SQL Snippets:     {len(full_config.instructions.sql_snippets.filters)} filters, {len(full_config.instructions.sql_snippets.measures)} measures")
print(f"Sample Questions: {len(full_config.sample_questions)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1c. Serialize to API Request

# COMMAND ----------

# Convert SpaceConfig to API request format
serializer = SpaceSerializer()
api_request = serializer.to_api_request(full_config)

print("API REQUEST BODY (preview)")
print("=" * 60)
print(json.dumps(api_request, indent=2)[:1500])
print("\n... (truncated)")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 1d. Create Space via API

# COMMAND ----------

# To create the space:
# result = client.create_space(api_request)
# print(f"Created space: {result['id']}")

print("To create this space, uncomment the code above.")
print()
print("Or use CLI:")
print("  # First export to YAML")
print("  # Then create from file")
print("  genie-forge space-create --from-file exported.yaml")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 2. Self-Joins (Hierarchical Data)
# MAGIC
# MAGIC Configure Genie to understand self-referential relationships
# MAGIC like employee → manager hierarchies.

# COMMAND ----------

# Self-join configuration example (API v2 format)
self_join_config = {
    "version": 2,
    "space_id": "employee_hierarchy",
    "title": "Employee Analytics with Hierarchy",
    "warehouse_id": "${warehouse_id}",
    "data_sources": {
        "tables": [
            {
                "identifier": "${catalog}.${schema}.employees",
                "description": [
                    "Employee data with self-referential manager relationship.",
                    "The manager_id column references employee_id in the same table."
                ],
                "column_configs": [
                    {"column_name": "employee_id", "description": ["Unique identifier"], "enable_format_assistance": True},
                    {"column_name": "manager_id", "description": ["FK to employee_id of this employee's manager"], "enable_entity_matching": True},
                    {"column_name": "first_name", "description": ["Employee first name"]},
                    {"column_name": "last_name", "description": ["Employee last name"]},
                    {"column_name": "job_title", "description": ["Current job title"]}
                ]
            }
        ]
    },
    "instructions": {
        "text_instructions": [
            {
                "content": ["""IMPORTANT: Self-Join Pattern for Manager Hierarchy

The employees table has a SELF-REFERENTIAL relationship:
- manager_id column references another row's employee_id
- CEO/top-level employees have manager_id = NULL

To find an employee's manager:
  SELECT e.*, m.first_name as manager_name
  FROM employees e
  LEFT JOIN employees m ON e.manager_id = m.employee_id

To find direct reports:
  SELECT * FROM employees WHERE manager_id = <employee_id>
"""]
            }
        ],
        "example_question_sqls": [
            {
                "question": ["Who does John Smith report to?"],
                "sql": ["""
SELECT m.first_name || ' ' || m.last_name AS manager_name,
       m.job_title AS manager_title
FROM employees e
INNER JOIN employees m ON e.manager_id = m.employee_id
WHERE e.first_name = 'John' AND e.last_name = 'Smith'
                """.strip()],
                "usage_guidance": ["Use for manager lookup queries"]
            },
            {
                "question": ["List all employees and their managers"],
                "sql": ["""
SELECT 
    e.employee_id,
    e.first_name || ' ' || e.last_name AS employee_name,
    e.job_title,
    COALESCE(m.first_name || ' ' || m.last_name, 'No Manager') AS manager_name
FROM employees e
LEFT JOIN employees m ON e.manager_id = m.employee_id
ORDER BY COALESCE(e.manager_id, 0), e.employee_id
                """.strip()]
            }
        ],
        "join_specs": [
            {
                "left": {"identifier": "${catalog}.${schema}.employees", "alias": "e"},
                "right": {"identifier": "${catalog}.${schema}.employees", "alias": "m"},
                "sql": [
                    "e.manager_id = m.employee_id",
                    "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"  # Relationship type annotation
                ],
                "instruction": ["SELF-JOIN: Link employees to their manager in the same table"]
            }
        ]
    },
    "sample_questions": [
        {"question": ["Who are the direct reports of the CEO?"]},
        {"question": ["Show the complete organizational hierarchy"]},
        {"question": ["Which managers have the most direct reports?"]}
    ]
}

print("SELF-JOIN CONFIGURATION")
print("=" * 60)
print(yaml.dump(self_join_config, default_flow_style=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ### 2b. Relationship Type Annotations
# MAGIC
# MAGIC Add relationship type hints to help Genie understand table cardinality:
# MAGIC
# MAGIC | Annotation | Meaning |
# MAGIC |------------|---------|
# MAGIC | `--rt=FROM_RELATIONSHIP_TYPE_ONE_TO_ONE--` | 1:1 relationship |
# MAGIC | `--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--` | Many:1 relationship |
# MAGIC | `--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_MANY--` | Many:Many relationship |

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 3. Parameterized Queries
# MAGIC
# MAGIC Use parameters in example SQLs for dynamic queries.

# COMMAND ----------

from genie_forge.models import ParameterConfig, ParameterDefaultValue

# Parameterized query example
parameterized_config = {
    "version": 2,
    "space_id": "parameterized_queries",
    "title": "Sales Analytics with Parameters",
    "warehouse_id": "${warehouse_id}",
    "data_sources": {
        "tables": [
            {
                "identifier": "${catalog}.${schema}.sales",
                "description": ["Sales transaction data"]
            }
        ]
    },
    "instructions": {
        "example_question_sqls": [
            {
                "id": "eq_regional_sales",
                "question": ["Show sales for a specific region"],
                "sql": ["""
SELECT region, SUM(amount) AS revenue, COUNT(*) AS orders
FROM ${catalog}.${schema}.sales
WHERE region = :region_filter
  AND transaction_date BETWEEN :start_date AND :end_date
  AND status = 'COMPLETED'
GROUP BY region
                """.strip()],
                "parameters": [
                    {
                        "name": "region_filter",
                        "type_hint": "STRING",
                        "description": ["Region code (NA, EMEA, APAC, LATAM)"],
                        "default_value": {
                            "values": ["NA"]
                        }
                    },
                    {
                        "name": "start_date",
                        "type_hint": "DATE",
                        "description": ["Start of analysis period"],
                        "default_value": {
                            "values": ["TODAY - 30 DAYS"]
                        }
                    },
                    {
                        "name": "end_date",
                        "type_hint": "DATE",
                        "description": ["End of analysis period"],
                        "default_value": {
                            "values": ["TODAY"]
                        }
                    }
                ],
                "usage_guidance": [
                    "Parameters are extracted from natural language",
                    "Default to last 30 days if no date range specified"
                ]
            }
        ]
    }
}

print("PARAMETERIZED QUERY CONFIGURATION")
print("=" * 60)
print(yaml.dump(parameterized_config, default_flow_style=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Parameter Type Hints
# MAGIC
# MAGIC | Type Hint | Description | Example |
# MAGIC |-----------|-------------|---------|
# MAGIC | `STRING` | Text values | "NA", "EMEA" |
# MAGIC | `DATE` | Date values | "2024-01-01", "TODAY" |
# MAGIC | `INTEGER` | Whole numbers | 100, 500 |
# MAGIC | `FLOAT` | Decimal numbers | 99.99 |
# MAGIC | `BOOLEAN` | True/False | true, false |

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 4. Benchmarks (Local Testing)
# MAGIC
# MAGIC Benchmarks validate your space generates correct SQL. They are **local-only** and never sent to the API.

# COMMAND ----------

# Benchmark configuration example
benchmark_config = {
    "version": 2,
    "space_id": "sales_with_benchmarks",
    "title": "Sales Analytics",
    "warehouse_id": "${warehouse_id}",
    "data_sources": {
        "tables": [
            {"identifier": "${catalog}.${schema}.sales"}
        ]
    },
    # Benchmarks are LOCAL ONLY - not sent to Databricks API
    "benchmarks": {
        "questions": [
            {
                "question": "What was total revenue last month?",
                "expected_sql": """
SELECT SUM(amount) AS total_revenue
FROM ${catalog}.${schema}.sales
WHERE status = 'COMPLETED'
  AND transaction_date >= DATEADD(MONTH, -1, CURRENT_DATE)
                """.strip()
            },
            {
                "question": "Who are our top 5 customers?",
                "expected_sql": """
SELECT customer_id, SUM(amount) AS total_spent
FROM ${catalog}.${schema}.sales
WHERE status = 'COMPLETED'
GROUP BY customer_id
ORDER BY total_spent DESC
LIMIT 5
                """.strip()
            }
        ]
    }
}

print("BENCHMARK CONFIGURATION")
print("=" * 60)
print(yaml.dump(benchmark_config, default_flow_style=False))
print()
print("NOTE: Benchmarks are stored locally and NOT sent to the Databricks API.")
print("Use them to validate your space configuration generates correct SQL patterns.")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 5. Demo Tables Setup
# MAGIC
# MAGIC Use the built-in demo tables for testing.

# COMMAND ----------

# Demo tables available
from genie_forge.demo_tables import DEMO_TABLES_INFO, DEMO_FUNCTIONS_INFO

print("AVAILABLE DEMO TABLES")
print("=" * 60)
for name, info in DEMO_TABLES_INFO.items():
    print(f"  {name:<20} {info['rows']:>6} rows  {info['description']}")

print()
print("AVAILABLE DEMO FUNCTIONS")
print("-" * 60)
for name, info in DEMO_FUNCTIONS_INFO.items():
    print(f"  {name:<30} {info['description']}")

# COMMAND ----------

# CLI commands for demo setup
print("DEMO SETUP COMMANDS")
print("=" * 60)
print()
print("# Create demo tables")
print("genie-forge setup-demo \\")
print("    --catalog your_catalog \\")
print("    --schema your_schema \\")
print("    --warehouse-id your_warehouse_id \\")
print("    --profile YOUR_PROFILE")
print()
print("# Check demo status")
print("genie-forge demo-status \\")
print("    --catalog your_catalog \\")
print("    --schema your_schema \\")
print("    --warehouse-id your_warehouse_id")
print()
print("# Cleanup demo tables")
print("genie-forge cleanup-demo \\")
print("    --catalog your_catalog \\")
print("    --schema your_schema \\")
print("    --warehouse-id your_warehouse_id \\")
print("    --execute")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 6. Variable Substitution
# MAGIC
# MAGIC Use variables for multi-environment configurations.

# COMMAND ----------

# Configuration with variables
config_with_variables = """
version: 2

# Variables are substituted from environment files
# or command line: --var catalog=prod_catalog

spaces:
  - space_id: sales_analytics
    title: "Sales Analytics - ${env}"
    warehouse_id: "${warehouse_id}"
    
    data_sources:
      tables:
        - identifier: "${catalog}.${schema}.sales"
          description:
            - "Sales transactions"
        - identifier: "${catalog}.${schema}.customers"
          description:
            - "Customer master data"
        - identifier: "${catalog}.${schema}.products"
          description:
            - "Product catalog"
    
    instructions:
      text_instructions:
        - content:
            - "Data is refreshed daily at midnight ${timezone}"
"""

# Environment variable files
dev_variables = """
env: Development
warehouse_id: dev_warehouse_123
catalog: dev_catalog
schema: dev_schema
timezone: UTC
"""

prod_variables = """
env: Production
warehouse_id: prod_warehouse_456
catalog: prod_catalog
schema: prod_schema
timezone: America/New_York
"""

print("CONFIG WITH VARIABLES")
print("=" * 60)
print(config_with_variables)
print()
print("DEV VARIABLES (conf/variables/dev.yaml)")
print("-" * 60)
print(dev_variables)
print()
print("PROD VARIABLES (conf/variables/prod.yaml)")
print("-" * 60)
print(prod_variables)

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 7. Bulk Operations
# MAGIC
# MAGIC Manage many spaces efficiently.

# COMMAND ----------

# Bulk export all spaces matching pattern
print("BULK EXPORT")
print("=" * 60)
print()
print("# Export all spaces")
print("genie-forge space-export --output-dir ./exports/")
print()
print("# Export by pattern")
print("genie-forge space-export --pattern 'Sales*' --output-dir ./exports/")
print()
print("# Export with exclusions")
print("genie-forge space-export --pattern '*' --exclude '*Test*' --output-dir ./exports/")
print()
print("# Note: On Databricks, use /Volumes/<catalog>/<schema>/<volume>/exports/")

# COMMAND ----------

# Bulk destroy with wildcard
print("BULK DESTROY")
print("=" * 60)
print()
print("# Destroy all spaces in dev environment")
print("genie-forge destroy --env dev --target '*'")
print()
print("# Destroy all except specific ones")
print("genie-forge destroy --env dev --target '* [production_space, critical_space]'")
print()
print("# Destroy multiple specific spaces")
print("genie-forge destroy --env dev --target 'space1, space2, space3'")

# COMMAND ----------

# Bulk import by pattern
print("BULK IMPORT")
print("=" * 60)
print()
print("# Import all spaces matching pattern")
print("genie-forge import --pattern 'Sales*' --env prod --profile PROD")
print()
print("# Import and generate config files")
print("genie-forge import --pattern '*Analytics*' --env prod \\")
print("    --output-dir ./conf/spaces/ --profile PROD")
print()
print("# Note: On Databricks, use /Volumes/<catalog>/<schema>/<volume>/conf/spaces/")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## 8. Custom Workflows
# MAGIC
# MAGIC Build custom automation scripts.

# COMMAND ----------

def migrate_spaces_workflow(
    source_client: GenieClient,
    target_client: GenieClient,
    pattern: str,
    target_warehouse_id: str,
    dry_run: bool = True
) -> dict:
    """
    Custom workflow to migrate spaces between workspaces.
    
    Args:
        source_client: Client for source workspace
        target_client: Client for target workspace
        pattern: Pattern to match space names
        target_warehouse_id: Warehouse ID in target workspace
        dry_run: If True, don't actually create spaces
        
    Returns:
        Dictionary with migration results
    """
    results = {
        "matched": 0,
        "migrated": 0,
        "failed": 0,
        "details": []
    }
    
    # Find matching spaces
    matches = source_client.find_spaces_by_name(pattern)
    results["matched"] = len(matches)
    
    for space in matches:
        try:
            # Export config with full serialized_space
            full_space = source_client.get_space(space['id'], include_serialized=True)
            serialized = full_space.get('serialized_space', {})
            if isinstance(serialized, str):
                serialized = json.loads(serialized)
            
            # Build target config (preserves all fields for lossless migration)
            target_config = {
                "title": full_space.get('title'),
                "warehouse_id": target_warehouse_id,
            }
            
            if serialized.get('data_sources'):
                target_config['data_sources'] = serialized['data_sources']
            if serialized.get('instructions'):
                target_config['instructions'] = serialized['instructions']
            if serialized.get('config', {}).get('sample_questions'):
                target_config['sample_questions'] = serialized['config']['sample_questions']
            
            if dry_run:
                results["details"].append({
                    "space": space.get('title'),
                    "status": "would_migrate"
                })
            else:
                # Create in target
                result = target_client.create_space(target_config)
                results["migrated"] += 1
                results["details"].append({
                    "space": space.get('title'),
                    "status": "migrated",
                    "new_id": result.get('id')
                })
                
        except Exception as e:
            results["failed"] += 1
            results["details"].append({
                "space": space.get('title'),
                "status": "failed",
                "error": str(e)
            })
    
    return results

# Example usage (commented out to avoid actual execution)
# results = migrate_spaces_workflow(
#     source_client=client,
#     target_client=target_client,
#     pattern="Sales*",
#     target_warehouse_id="target_wh_123",
#     dry_run=True
# )
# print(json.dumps(results, indent=2))

print("Custom workflow function defined: migrate_spaces_workflow()")
print("See code above for implementation details.")

# COMMAND ----------

# MAGIC %md
# MAGIC ---
# MAGIC ## Summary
# MAGIC
# MAGIC | Pattern | Use Case |
# MAGIC |---------|----------|
# MAGIC | Programmatic API | Build configs in code |
# MAGIC | Self-Joins | Hierarchical data relationships |
# MAGIC | Relationship Types | Define table cardinality (1:1, M:1, M:M) |
# MAGIC | Parameterized Queries | Dynamic values from natural language |
# MAGIC | Benchmarks | Local-only testing of SQL generation |
# MAGIC | Demo Tables | Quick testing setup |
# MAGIC | Variable Substitution | Multi-environment configs |
# MAGIC | Bulk Operations | Manage many spaces at once |
# MAGIC | Custom Workflows | Automation scripts |
# MAGIC
# MAGIC ## Key Classes (API v2)
# MAGIC
# MAGIC ```python
# MAGIC from genie_forge import GenieClient, SpaceConfig, StateManager
# MAGIC from genie_forge.models import (
# MAGIC     DataSources, TableConfig, ColumnConfig,
# MAGIC     Instructions, TextInstruction, ExampleQuestionSQL,
# MAGIC     SqlFunction, JoinSpec, JoinTableRef, SampleQuestion,
# MAGIC     SqlSnippet, SqlSnippets, 
# MAGIC     ParameterConfig, ParameterDefaultValue,  # For parameterized queries
# MAGIC     Benchmarks, BenchmarkQuestion  # For local testing
# MAGIC )
# MAGIC from genie_forge.serializer import SpaceSerializer
# MAGIC from genie_forge.parsers import MetadataParser
# MAGIC ```
# MAGIC
# MAGIC ## Complete Configuration Reference
# MAGIC
# MAGIC For a **complete YAML example** showing ALL features, see the
# MAGIC [Configuration Guide - Complete Reference Example](../docs/guide/configuration.md#complete-reference-example)
# MAGIC
# MAGIC ## Resources
# MAGIC
# MAGIC - **Documentation**: See `docs/` folder
# MAGIC - **Examples**: See `conf/spaces/` for YAML examples
# MAGIC - **CLI Help**: `genie-forge --help`
