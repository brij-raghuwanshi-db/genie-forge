# Configuration Guide

This guide covers YAML configuration for Genie spaces and environment setup.

## Table of Contents

- [API Limitations and Behaviors](#api-limitations-and-behaviors) - **Important to understand**
- [Path Management](#path-management)
- [Space Configuration](#space-configuration)
- [Creating Spaces from Files](#creating-spaces-from-files)
- [Table Configuration](#table-configuration)
- [Instructions](#instructions)
- [Join Specifications](#join-specifications)
- [Environment Configuration](#environment-configuration)
- [Variable Substitution](#variable-substitution)
- [Complete Reference Example](#complete-reference-example) - **Full YAML with ALL features**
- [Advanced Column Configuration](#advanced-column-configuration)
- [Example Question SQLs with Parameters](#example-question-sqls-with-parameters)
- [Join Specifications (Advanced)](#join-specifications-advanced)
- [SQL Snippets](#sql-snippets)
- [Benchmarks](#benchmarks)
- [Complete Examples](#complete-examples)

---

## API Limitations and Behaviors

Understanding these Databricks Genie API behaviors will help you write correct configurations.

### Text Instructions: Only ONE Allowed

!!! warning "API Limitation"
    The Genie API only accepts **ONE** text_instruction. If you define multiple text_instructions, Genie-Forge automatically **combines them** into a single instruction.

```yaml
# Your configuration (multiple instructions)
text_instructions:
  - id: ti_format
    content: ["Format currency with $ symbol"]
  - id: ti_dates
    content: ["Use ISO date format"]

# What gets sent to API (combined into one)
text_instructions:
  - id: ti_format  # First ID with an ID is used
    content:
      - "Format currency with $ symbol"
      - "Use ISO date format"
```

### UUID Auto-Generation

Items without an `id` field get automatically generated UUIDs (32-character hex strings):

| Item Type | Auto-Generated If Missing |
|-----------|---------------------------|
| `sample_questions` | Yes |
| `text_instructions` | Yes |
| `example_question_sqls` | Yes |
| `join_specs` | Yes |
| `sql_snippets` (all types) | Yes |

**Best Practice:** Always provide explicit IDs for tracking and debugging.

### Array Sorting Requirement

All instruction arrays are **automatically sorted by ID** before being sent to the API. This is an API requirement. You don't need to worry about ordering in your config files.

### Table Identifier Validation

Table identifiers must be in the format `catalog.schema.table` (exactly 3 parts):

```yaml
# Valid
identifier: "main.default.sales"

# Invalid - will cause validation error
identifier: "sales"              # Missing catalog and schema
identifier: "default.sales"      # Missing catalog
```

### String-to-List Normalization

For convenience, several fields accept either strings or lists. Strings are automatically converted to single-item lists:

```yaml
# Both are equivalent
description: "Sales data"
description: ["Sales data"]

# Both are equivalent
question: "What is revenue?"
question: ["What is revenue?"]
```

### Default Values

Many fields have sensible defaults if not specified:

| Field | Default | Location |
|-------|---------|----------|
| `version` | `2` | Root/SpaceConfig level |
| `type_hint` | `"STRING"` | ParameterConfig |
| `enable_format_assistance` | `false` | ColumnConfig |
| `enable_entity_matching` | `false` | ColumnConfig |
| `build_value_dictionary` | `false` | ColumnConfig |
| `get_example_values` | `false` | ColumnConfig |

**Note:** Column config flags default to `false` and are only sent to the API when set to `true`.

### Local-Only Fields

Some fields are stored in your config but **not sent to the Databricks API**:

| Field | Location | Purpose |
|-------|----------|---------|
| `SqlFunction.description` | `sql_functions[].description` | Local documentation only |
| `benchmarks` | Root level | Local testing only |
| `author` | Root level | Configuration metadata |
| `tags` | SpaceConfig level | Configuration metadata |

### Serialization Behaviors

When Genie-Forge sends your configuration to the API:

1. **Tables are sorted** - Tables are sorted alphabetically by identifier for consistent API requests
2. **False flags are omitted** - Column config flags (like `enable_format_assistance: false`) are not sent when `false`
3. **Empty arrays are omitted** - Fields with empty arrays (`[]`) are not included in the request
4. **Round-trip preservation** - When exporting a space and re-importing, existing IDs and structures are preserved

!!! tip "Export and Compare"
    Use `genie-forge space-export` to see exactly what's deployed and compare against your local config.

---

## Path Management

Genie-Forge automatically manages file paths based on the execution environment.

### Dual Environment Support

| Environment | Config/State Location | Example |
|-------------|----------------------|---------|
| **Local Machine** | `~/.genie-forge/<project>/` | `~/.genie-forge/my_project/conf/spaces/` |
| **Databricks** | `/Volumes/<catalog>/<schema>/<volume>/<project>/` | `/Volumes/main/default/genie_forge/my_project/conf/spaces/` |

### Using ProjectPaths (Python API)

```python
from genie_forge import ProjectPaths, is_running_on_databricks

# Configuration - same catalog/schema for tables AND volume storage
CATALOG = "main"
SCHEMA = "default"
VOLUME_NAME = "genie_forge"
PROJECT_NAME = "my_project"

# ProjectPaths auto-detects the environment
paths = ProjectPaths(
    project_name=PROJECT_NAME,
    catalog=CATALOG,
    schema=SCHEMA,
    volume_name=VOLUME_NAME,
)

# Access paths
print(paths.root)         # Project root directory
print(paths.spaces_dir)   # conf/spaces/
print(paths.state_file)   # .genie-forge.json
print(paths.exports_dir)  # exports/

# Access catalog/schema for table references
print(f"{paths.catalog}.{paths.schema}.my_table")

# Create directory structure
paths.ensure_structure()
```

### Key Principle: Unified Catalog/Schema

The same `catalog` and `schema` are used for:
1. **Data tables** - Tables that Genie spaces query (e.g., `main.default.employees`)
2. **Volume storage** - Where config and state files are stored (e.g., `/Volumes/main/default/genie_forge/`)

This simplifies configuration - you only need to specify catalog and schema once.

### CLI Path Options

When using CLI commands with `--output-dir`:

```bash
# Local machine - use relative or absolute paths
genie-forge space-export --output-dir ./exports/

# Databricks - use Volume paths
genie-forge space-export --output-dir /Volumes/main/default/genie_forge/exports/
```

---

## Space Configuration

Space configurations define the Genie spaces to be deployed. They are typically stored in `conf/spaces/`.

### Basic Structure

```yaml
version: 1
author: "your_name"

spaces:
  - space_id: "unique_logical_id"        # Used for state tracking
    title: "Display Title in Genie UI"
    description: "Optional description"
    warehouse_id: "${warehouse_id}"       # Variable substitution
    
    data_sources:
      tables:
        - identifier: "${catalog}.${schema}.table_name"
          description:
            - "Description of this table"
          column_configs:
            - column_name: "column_name"
              description: "What this column contains"
    
    instructions:
      text_instructions:
        - content: "Natural language instructions for Genie"
      
      sample_questions:
        - question: "Example question users might ask"
```

### Required Fields

| Field | Description |
|-------|-------------|
| `space_id` | Unique logical identifier (used in state tracking) |
| `title` | Display title shown in Genie UI |
| `warehouse_id` | SQL warehouse ID for query execution |
| `data_sources.tables` | At least one table must be defined |

### Optional Fields

| Field | Description | Default |
|-------|-------------|---------|
| `version` | Configuration format version | `2` |
| `description` | Space description shown in UI | None |
| `parent_path` | Workspace folder path for the space | None |
| `author` | Configuration author (metadata only) | None |
| `tags` | List of tags for categorization (metadata only) | `[]` |
| `column_configs` | Column-level descriptions and synonyms | `[]` |
| `text_instructions` | Natural language guidance for Genie | `[]` |
| `sample_questions` | Example questions shown to users | `[]` |
| `join_specs` | How tables should be joined | `[]` |
| `sql_functions` | UDF references for Genie to use | `[]` |
| `sql_snippets` | Reusable SQL fragments | `{}` |
| `benchmarks` | Local-only test cases (not sent to API) | None |

---

## Creating Spaces from Files

v0.3.0 introduces the `space-create` command with `--from-file` support, allowing you to create spaces directly from YAML or JSON configuration files.

### Quick Create Format

For quick space creation without the full `version` and `spaces` wrapper:

```yaml
# conf/spaces/quick_space.yaml
title: "Sales Analytics"
warehouse_id: "abc123def456"
description: "Analyze sales performance"

data_sources:
  tables:
    - identifier: "catalog.schema.sales"
      description:
        - "Sales transaction data"
    - identifier: "catalog.schema.customers"
      description:
        - "Customer master data"

instructions:
  text_instructions:
    - text: "Focus on revenue and customer metrics"
  sql_functions:
    - identifier: "catalog.schema.calculate_margin"

sample_questions:
  - question: "Top 10 customers by revenue?"
  - question: "Monthly sales trend by region?"
```

### Using `--from-file`

```bash
# Create space from YAML file
genie-forge space-create --from-file conf/spaces/quick_space.yaml --profile PROD

# Create from JSON file
genie-forge space-create --from-file conf/spaces/quick_space.json --profile PROD

# Dry run to preview
genie-forge space-create --from-file conf/spaces/quick_space.yaml --dry-run --profile PROD
```

### Using `--set` for Overrides

The `--set` option allows you to override any value in the configuration file:

```bash
# Override the title
genie-forge space-create --from-file template.yaml \
    --set title="Custom Title" \
    --profile PROD

# Override multiple values
genie-forge space-create --from-file template.yaml \
    --set title="Production Space" \
    --set warehouse_id="prod_warehouse_123" \
    --profile PROD

# Override nested values (use dot notation)
genie-forge space-create --from-file template.yaml \
    --set data_sources.description="Updated description" \
    --profile PROD
```

### Template Pattern

Create a base template and use `--set` to customize for different environments or use cases:

**Template** (`conf/templates/analytics_template.yaml`):

```yaml
title: "${title}"
warehouse_id: "${warehouse_id}"
description: "Analytics space for ${department}"

data_sources:
  tables:
    - identifier: "${catalog}.${schema}.metrics"
      description:
        - "Department metrics"

sample_questions:
  - question: "What are the key metrics?"
```

**Usage:**

```bash
# Sales team space
genie-forge space-create --from-file conf/templates/analytics_template.yaml \
    --set title="Sales Analytics" \
    --set warehouse_id="sales_warehouse" \
    --profile PROD

# Marketing team space
genie-forge space-create --from-file conf/templates/analytics_template.yaml \
    --set title="Marketing Analytics" \
    --set warehouse_id="marketing_warehouse" \
    --profile PROD
```

### JSON Format

You can also use JSON format:

```json
{
  "title": "Sales Analytics",
  "warehouse_id": "abc123def456",
  "data_sources": {
    "tables": [
      {
        "identifier": "catalog.schema.sales",
        "description": ["Sales transaction data"]
      }
    ]
  },
  "sample_questions": [
    {"question": "Top 10 customers?"}
  ]
}
```

### Saving Created Space Config

After creating a space via CLI flags, save the config for future use:

```bash
# Create and save config
genie-forge space-create "My Space" \
    --warehouse-id abc123 \
    --tables "catalog.schema.table1,catalog.schema.table2" \
    --save-config conf/spaces/my_space.yaml \
    --profile PROD
```

This generates a YAML file you can version control and reuse:

```yaml
# Generated: conf/spaces/my_space.yaml
title: "My Space"
warehouse_id: "abc123"
data_sources:
  tables:
    - identifier: "catalog.schema.table1"
    - identifier: "catalog.schema.table2"
```

### Three Creation Methods Compared

| Method | Best For | Command |
|--------|----------|---------|
| CLI Flags | Quick tests, prototypes | `space-create "Title" --warehouse-id W --tables T` |
| From File | Complex configs, production | `space-create --from-file config.yaml` |
| Hybrid | Templates with customization | `space-create --from-file template.yaml --set key=value` |

---

## Table Configuration

### Basic Table

```yaml
tables:
  - identifier: "${catalog}.${schema}.employees"
    description:
      - "Employee master data"
      - "Contains all current employees"
```

### Table with Column Configs

```yaml
tables:
  - identifier: "${catalog}.${schema}.employees"
    description:
      - "Employee master data with manager hierarchy"
    column_configs:
      - column_name: "employee_id"
        description: "Unique employee identifier"
      - column_name: "manager_id"
        description: "References employee_id of the employee's manager (self-join)"
        synonyms:
          - "supervisor"
          - "reports_to"
      - column_name: "hire_date"
        description: "Date employee was hired"
        dictionary:
          - value: "2020-01-01"
            description: "Company founding date"
```

### Column Config Options

| Field | Description |
|-------|-------------|
| `column_name` | Name of the column |
| `description` | What the column contains |
| `synonyms` | Alternative names users might use |
| `dictionary` | Specific value meanings |

---

## Instructions

### Text Instructions

Provide natural language guidance to help Genie understand your data:

```yaml
instructions:
  text_instructions:
    - content: |
        SELF-JOIN: The employees table has a self-referential manager_id.
        To find manager names:
        SELECT e.*, m.first_name as manager_name
        FROM employees e
        LEFT JOIN employees m ON e.manager_id = m.employee_id
    
    - content: |
        REGIONS: Sales data uses these region codes:
        - NA = North America
        - EMEA = Europe, Middle East, Africa
        - APAC = Asia Pacific
```

### Sample Questions

Show users example questions they can ask:

```yaml
instructions:
  sample_questions:
    - question: "Who are the top 10 employees by sales this quarter?"
    - question: "Show me the management chain for John Smith"
    - question: "What's the average deal size by region?"
```

### SQL Instructions

Provide example SQL patterns:

```yaml
instructions:
  sql_instructions:
    - content: |
        -- Calculate year-over-year growth
        SELECT 
          YEAR(sale_date) as year,
          SUM(amount) as total,
          LAG(SUM(amount)) OVER (ORDER BY YEAR(sale_date)) as prev_year
        FROM sales
        GROUP BY YEAR(sale_date)
```

---

## Join Specifications

Define how tables should be joined for multi-table queries.

!!! tip "Complete Example"
    See the [Complete Reference Example](#complete-reference-example) for full join_specs with relationship types.

```yaml
instructions:
  join_specs:
    # Standard join between tables
    - id: js_sales_customers
      left:
        identifier: "${catalog}.${schema}.sales"
        alias: "s"
      right:
        identifier: "${catalog}.${schema}.customers"
        alias: "c"
      sql:
        - "s.customer_id = c.customer_id"
        - "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"
      instruction:
        - "Link sales to customer details"
    
    # Self-join for hierarchical data
    - id: js_employee_manager
      left:
        identifier: "${catalog}.${schema}.employees"
        alias: "e"
      right:
        identifier: "${catalog}.${schema}.employees"
        alias: "m"
      sql:
        - "e.manager_id = m.employee_id"
        - "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"
      instruction:
        - "Self-join for manager hierarchy"
```

### Relationship Types

Add relationship type annotations to help Genie understand table cardinality:

| Annotation | Meaning |
|------------|---------|
| `--rt=FROM_RELATIONSHIP_TYPE_ONE_TO_ONE--` | 1:1 relationship |
| `--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--` | Many:1 relationship |
| `--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_MANY--` | Many:Many relationship |

---

## SQL Functions

Reference User Defined Functions (UDFs) from your Unity Catalog that Genie can use.

### SqlFunction Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | No | Unique identifier (auto-generated if not provided) |
| `identifier` | string | **Yes** | Full UDF path: `catalog.schema.function_name` |
| `description` | string | No | What the function does (local-only, not sent to API) |

### Example

```yaml
instructions:
  sql_functions:
    - id: fn_profit_margin
      identifier: "${catalog}.${schema}.calculate_profit_margin"
      description: "Calculates profit margin percentage given revenue and cost"
    
    - id: fn_format_currency
      identifier: "${catalog}.${schema}.format_currency"
      description: "Formats a number as USD currency string"
```

!!! info "Local-Only Description"
    The `description` field is for your documentation only—it is not sent to the Databricks API.

---

## Environment Configuration

Environment configs define variables for different deployment targets. They are stored in `conf/environments/`.

### Structure

```yaml
# conf/environments/dev.yaml
workspace_url: "https://your-dev-workspace.azuredatabricks.net"

auth:
  profile: "DEV_PROFILE"  # Profile name from ~/.databrickscfg

variables:
  env: "dev"
  warehouse_id: "abc123def456"
  catalog: "dev_catalog"
  schema: "genie_demo"
```

### Production Environment

```yaml
# conf/environments/prod.yaml
workspace_url: "https://your-prod-workspace.azuredatabricks.net"

auth:
  profile: "PROD_PROFILE"

variables:
  env: "prod"
  warehouse_id: "xyz789prod"
  catalog: "prod_catalog"
  schema: "genie_prod"
```

### Finding Your Values

| Value | Where to Find |
|-------|---------------|
| `workspace_url` | Browser URL when logged into Databricks |
| `profile` | Run `genie-forge profiles` to list available |
| `warehouse_id` | SQL Warehouses → Select warehouse → Copy ID from URL |
| `catalog` | Data Explorer → Catalogs |
| `schema` | Data Explorer → Catalog → Schemas |

---

## Variable Substitution

Use `${variable_name}` syntax to reference environment variables:

```yaml
# In space config
warehouse_id: "${warehouse_id}"
tables:
  - identifier: "${catalog}.${schema}.employees"
```

When you run `genie-forge plan --env dev`, the parser:
1. Loads `conf/environments/dev.yaml`
2. Extracts the `variables` section
3. Replaces all `${...}` references in space configs

---

## Complete Reference Example

This section provides a **comprehensive, copy-paste ready YAML** that demonstrates **every available configuration option**. Use this as your reference when building production configurations.

!!! tip "Version 2 Format"
    Use `version: 2` for full feature support including explicit IDs, SQL snippets, parameters, and lossless round-trip serialization.

```yaml
# =============================================================================
# COMPLETE GENIE SPACE CONFIGURATION - ALL FEATURES REFERENCE
# =============================================================================
# This example demonstrates EVERY available configuration option.
# Copy and modify for your use case.
#
# Required fields: space_id, title, warehouse_id, data_sources.tables
# Everything else is optional but recommended for production use.
# =============================================================================

version: 2  # Use version 2 for full feature support

spaces:
  - space_id: complete_reference_space    # Unique logical ID (lowercase, alphanumeric, underscores)
    title: "Complete Reference Space"      # Display name shown in Genie UI
    description: "A fully-configured example demonstrating all available features"
    warehouse_id: "${warehouse_id}"        # SQL warehouse ID (use variable substitution)
    # parent_path: "/Workspace/Users/you@company.com"  # Optional: folder path for the space

    # =========================================================================
    # SAMPLE QUESTIONS - Suggested questions shown to users in the UI
    # =========================================================================
    sample_questions:
      # Simple string format (backward compatible with version 1)
      - "What are the total sales by region?"
      
      # Object format with ID (recommended for version 2 - enables tracking)
      - id: sq_revenue_analysis
        question:
          - "What is our total revenue?"
          - "How much did we make this quarter?"  # Multiple phrasings supported
      
      - id: sq_top_customers
        question:
          - "Who are our top 10 customers?"
          - "Show me our best customers by revenue"

    # =========================================================================
    # DATA SOURCES - Tables and their column configurations
    # =========================================================================
    data_sources:
      tables:
        # -------------------------------------------------------------------
        # Table 1: Sales Transactions (comprehensive column config example)
        # -------------------------------------------------------------------
        - identifier: "${catalog}.${schema}.sales"
          description:
            - "Sales transaction records"
            - "Updated daily at midnight UTC"
            - "Primary key: transaction_id"
          
          column_configs:
            - column_name: transaction_id
              description:
                - "Unique transaction identifier"
              synonyms:
                - "sale_id"
                - "order_id"
                - "txn_id"
              # Advanced column flags (all optional)
              enable_format_assistance: true   # Help Genie format values (dates, currency)
              enable_entity_matching: true     # Enable entity recognition for this column
              # build_value_dictionary: true   # Build dictionary of distinct values
              # get_example_values: true       # Extract example values for context
            
            - column_name: transaction_date
              description:
                - "Date when the transaction occurred"
              synonyms:
                - "sale_date"
                - "order_date"
              enable_format_assistance: true
            
            - column_name: customer_id
              description:
                - "Foreign key to customers table"
              synonyms:
                - "client_id"
                - "buyer_id"
              enable_entity_matching: true
            
            - column_name: amount
              description:
                - "Transaction amount in USD"
                - "Includes tax and discounts applied"
              synonyms:
                - "total"
                - "revenue"
                - "price"
                - "sale_amount"
              enable_format_assistance: true
            
            - column_name: status
              description:
                - "Transaction status"
                - "Values: PENDING, COMPLETED, REFUNDED, CANCELLED"
              synonyms:
                - "order_status"
                - "txn_status"
            
            - column_name: region
              description:
                - "Sales region code (NA, EMEA, APAC, LATAM)"
              synonyms:
                - "territory"
                - "area"
              enable_entity_matching: true

        # -------------------------------------------------------------------
        # Table 2: Customers
        # -------------------------------------------------------------------
        - identifier: "${catalog}.${schema}.customers"
          description:
            - "Customer master data"
            - "Contains both B2B and B2C customers"
          
          column_configs:
            - column_name: customer_id
              description:
                - "Unique customer identifier"
              enable_format_assistance: true
            
            - column_name: customer_name
              description:
                - "Full name or company name"
              synonyms:
                - "name"
                - "client_name"
              enable_entity_matching: true
            
            - column_name: segment
              description:
                - "Customer segment: Enterprise, SMB, or Consumer"
              synonyms:
                - "type"
                - "category"

        # -------------------------------------------------------------------
        # Table 3: Employees (for self-join example)
        # -------------------------------------------------------------------
        - identifier: "${catalog}.${schema}.employees"
          description:
            - "Employee directory with manager hierarchy"
            - "The manager_id column references employee_id (self-referential)"
          
          column_configs:
            - column_name: employee_id
              description:
                - "Unique employee identifier"
              enable_format_assistance: true
            
            - column_name: employee_name
              description:
                - "Full name of the employee"
              synonyms:
                - "name"
                - "full_name"
              enable_entity_matching: true
            
            - column_name: manager_id
              description:
                - "References employee_id of this person's manager"
                - "NULL for top-level executives (CEO)"
              synonyms:
                - "reports_to"
                - "supervisor_id"
              enable_entity_matching: true
            
            - column_name: department
              description:
                - "Department name"
              synonyms:
                - "dept"
                - "team"
              enable_entity_matching: true
            
            - column_name: salary
              description:
                - "Annual salary in USD"
              synonyms:
                - "compensation"
                - "pay"
              enable_format_assistance: true

    # =========================================================================
    # INSTRUCTIONS - Guide Genie's behavior and understanding
    # =========================================================================
    instructions:
      # -----------------------------------------------------------------------
      # TEXT INSTRUCTIONS - Natural language guidance for Genie
      # -----------------------------------------------------------------------
      text_instructions:
        - id: ti_currency_format
          content:
            - "CURRENCY FORMATTING: Always format monetary values with $ symbol and 2 decimal places."
            - "Example: $1,234.56"
        
        - id: ti_date_handling
          content:
            - "DATE HANDLING: Use ISO format (YYYY-MM-DD) for date comparisons."
            - "When users say 'this month', use CURRENT_DATE functions."
            - "When users say 'last quarter', calculate the appropriate date range."
        
        - id: ti_self_join
          content:
            - |
              EMPLOYEE HIERARCHY (Self-Join Pattern):
              The employees table has a self-referential manager_id column.
              To find an employee's manager:
              
              SELECT e.employee_name, m.employee_name AS manager_name
              FROM employees e
              LEFT JOIN employees m ON e.manager_id = m.employee_id
        
        - id: ti_default_filters
          content:
            - "ALWAYS exclude cancelled and refunded transactions unless specifically asked."
            - "Default time range is last 30 days if not specified by the user."

      # -----------------------------------------------------------------------
      # EXAMPLE QUESTION SQLS - Teach Genie specific query patterns
      # -----------------------------------------------------------------------
      example_question_sqls:
        # Simple example WITHOUT parameters
        - id: eq_total_revenue
          question:
            - "What is our total revenue?"
            - "How much did we make?"
          sql:
            - |
              SELECT 
                SUM(amount) AS total_revenue,
                COUNT(*) AS transaction_count,
                AVG(amount) AS average_order_value
              FROM ${catalog}.${schema}.sales
              WHERE status = 'COMPLETED'
                AND transaction_date >= DATEADD(DAY, -30, CURRENT_DATE)
          usage_guidance:
            - "Use this pattern for revenue aggregation queries"
            - "Modify date filter based on user's specified time range"
        
        # Advanced example WITH parameters
        - id: eq_sales_by_region
          question:
            - "Show sales for a specific region"
            - "What are sales in NA?"
          sql:
            - |
              SELECT 
                region,
                transaction_date,
                COUNT(*) AS transactions,
                SUM(amount) AS daily_revenue
              FROM ${catalog}.${schema}.sales
              WHERE region = :region_filter
                AND transaction_date BETWEEN :start_date AND :end_date
                AND status = 'COMPLETED'
              GROUP BY region, transaction_date
              ORDER BY transaction_date
          parameters:
            - name: region_filter
              type_hint: STRING
              description:
                - "Region code to filter by (NA, EMEA, APAC, LATAM)"
              default_value:
                values:
                  - "NA"
            - name: start_date
              type_hint: DATE
              description:
                - "Start date for the analysis period"
              default_value:
                values:
                  - "TODAY - 30 DAYS"
            - name: end_date
              type_hint: DATE
              description:
                - "End date for the analysis period"
              default_value:
                values:
                  - "TODAY"
          usage_guidance:
            - "Parameters are extracted from the user's natural language"
            - "Default to last 30 days if no date range specified"
        
        # Self-join example
        - id: eq_manager_hierarchy
          question:
            - "Who reports to whom?"
            - "Show me the org chart"
          sql:
            - |
              SELECT 
                e.employee_id,
                e.employee_name,
                e.department,
                m.employee_name AS manager_name
              FROM ${catalog}.${schema}.employees e
              LEFT JOIN ${catalog}.${schema}.employees m 
                ON e.manager_id = m.employee_id
              ORDER BY COALESCE(e.manager_id, 0), e.employee_name
          usage_guidance:
            - "This is a self-join example for hierarchical data"
            - "NULL manager_id indicates top-level executive"

      # -----------------------------------------------------------------------
      # SQL FUNCTIONS - Reference UDFs from your catalog
      # -----------------------------------------------------------------------
      sql_functions:
        - identifier: "${catalog}.${schema}.calculate_profit_margin"
          description: "Calculates profit margin percentage given revenue and cost"
        
        - identifier: "${catalog}.${schema}.format_currency"
          description: "Formats a number as USD currency string"

      # -----------------------------------------------------------------------
      # JOIN SPECIFICATIONS - Define table relationships
      # -----------------------------------------------------------------------
      join_specs:
        # Standard join between different tables
        - id: js_sales_customers
          left:
            identifier: "${catalog}.${schema}.sales"
            alias: "s"
          right:
            identifier: "${catalog}.${schema}.customers"
            alias: "c"
          sql:
            - "s.customer_id = c.customer_id"
            - "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"  # Relationship type annotation
          instruction:
            - "Join sales transactions to customer master data"
            - "Use for customer-level analysis"
        
        # Self-join for hierarchical data (employee -> manager)
        - id: js_employee_manager
          left:
            identifier: "${catalog}.${schema}.employees"
            alias: "e"
          right:
            identifier: "${catalog}.${schema}.employees"
            alias: "m"
          sql:
            - "e.manager_id = m.employee_id"
            - "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"
          instruction:
            - "SELF-JOIN: Link employees to their managers"
            - "Use LEFT JOIN to include employees without managers (executives)"

      # -----------------------------------------------------------------------
      # SQL SNIPPETS - Reusable SQL fragments (filters, expressions, measures)
      # -----------------------------------------------------------------------
      sql_snippets:
        # Filters - Common WHERE clause conditions
        filters:
          - id: filter_completed
            sql:
              - "status = 'COMPLETED'"
            display_name: "Completed Only"
            instruction:
              - "Filter to only completed transactions"
              - "Apply by default unless user asks for all statuses"
            synonyms:
              - "successful"
              - "finished"
              - "done"
          
          - id: filter_last_30_days
            sql:
              - "transaction_date >= DATEADD(DAY, -30, CURRENT_DATE)"
            display_name: "Last 30 Days"
            instruction:
              - "Default time filter when no date range specified"
            synonyms:
              - "recent"
              - "this month"
              - "lately"
          
          - id: filter_high_value
            sql:
              - "amount >= 1000"
            display_name: "High Value Orders"
            instruction:
              - "Filter to orders $1000 or more"
            synonyms:
              - "large orders"
              - "big orders"
              - "high ticket"
        
        # Expressions - Calculated fields
        expressions:
          - id: expr_current_date
            sql:
              - "CURRENT_DATE"
            display_name: "Today"
            instruction:
              - "Current date value"
            synonyms:
              - "now"
              - "today"
          
          - id: expr_profit
            sql:
              - "(amount - (cost * quantity))"
            display_name: "Profit"
            instruction:
              - "Calculate profit per transaction"
            synonyms:
              - "margin"
              - "earnings"
              - "net"
        
        # Measures - Aggregation functions
        measures:
          - id: measure_total_revenue
            sql:
              - "SUM(amount)"
            display_name: "Total Revenue"
            instruction:
              - "Sum of all transaction amounts"
            synonyms:
              - "total sales"
              - "revenue"
              - "sales"
          
          - id: measure_avg_order
            sql:
              - "AVG(amount)"
            display_name: "Average Order Value"
            instruction:
              - "Mean transaction amount"
            synonyms:
              - "aov"
              - "average sale"
              - "avg order"
          
          - id: measure_order_count
            sql:
              - "COUNT(DISTINCT transaction_id)"
            display_name: "Order Count"
            instruction:
              - "Number of unique orders"
            synonyms:
              - "transactions"
              - "orders"
              - "sales count"

    # =========================================================================
    # BENCHMARKS - Local-only testing (NOT sent to Databricks API)
    # =========================================================================
    # Use benchmarks to validate your space configuration generates correct SQL.
    # These are stored locally and never sent to the API.
    benchmarks:
      questions:
        - question: "What was total revenue last month?"
          expected_sql: |
            SELECT SUM(amount) AS total_revenue
            FROM ${catalog}.${schema}.sales
            WHERE status = 'COMPLETED'
              AND transaction_date >= DATEADD(MONTH, -1, CURRENT_DATE)
        
        - question: "Who are our top 5 customers?"
          expected_sql: |
            SELECT c.customer_name, SUM(s.amount) AS total_spent
            FROM ${catalog}.${schema}.sales s
            JOIN ${catalog}.${schema}.customers c ON s.customer_id = c.customer_id
            WHERE s.status = 'COMPLETED'
            GROUP BY c.customer_name
            ORDER BY total_spent DESC
            LIMIT 5
        
        - question: "Show me John's manager"
          expected_sql: |
            SELECT e.employee_name, m.employee_name AS manager_name
            FROM ${catalog}.${schema}.employees e
            LEFT JOIN ${catalog}.${schema}.employees m 
              ON e.manager_id = m.employee_id
            WHERE e.employee_name = 'John'
```

---

## Advanced Column Configuration

Column configs support several advanced flags that enhance Genie's understanding and formatting capabilities.

### Column Config Options (Complete Reference)

| Field | Type | Description |
|-------|------|-------------|
| `column_name` | string | **Required.** Name of the column |
| `description` | string or list | What the column contains (supports multiple lines) |
| `synonyms` | list | Alternative names users might use to refer to this column |
| `enable_format_assistance` | boolean | Help Genie format values (dates, currency, numbers) |
| `enable_entity_matching` | boolean | Enable entity recognition for better natural language understanding |
| `build_value_dictionary` | boolean | Build a dictionary of distinct values in this column |
| `get_example_values` | boolean | Extract example values to provide context |

### Example: Full Column Configuration

```yaml
column_configs:
  - column_name: amount
    description:
      - "Transaction amount in USD"
      - "Includes tax and any discounts applied"
    synonyms:
      - "total"
      - "revenue"
      - "price"
      - "sale_amount"
    enable_format_assistance: true   # Format as currency
    enable_entity_matching: false    # Not needed for numeric values
  
  - column_name: customer_name
    description:
      - "Full customer name or company name"
    synonyms:
      - "name"
      - "client"
      - "account"
    enable_format_assistance: false
    enable_entity_matching: true     # Enable entity recognition
    build_value_dictionary: true     # Build dictionary of customer names
    get_example_values: true         # Show example customer names
```

---

## Example Question SQLs with Parameters

Example question SQLs teach Genie specific query patterns. You can include **parameters** to handle dynamic values from user queries.

### ExampleQuestionSQL Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | No | Unique identifier (auto-generated if not provided) |
| `question` | list | **Yes** | Natural language questions this SQL answers |
| `sql` | list | **Yes** | SQL query pattern (use `:param` for parameters) |
| `parameters` | list | No | Parameter definitions for dynamic values |
| `usage_guidance` | list | No | Instructions for when/how to use this pattern |

### Parameter Configuration

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | **Yes** | - | Parameter name (used as `:name` in SQL) |
| `type_hint` | string | No | `"STRING"` | Data type: `STRING`, `DATE`, `INTEGER`, `FLOAT`, `BOOLEAN` |
| `description` | list | No | `[]` | What this parameter represents |
| `default_value.values` | list | No | - | Default value(s) for the parameter |

### Example: Parameterized Query

!!! tip "Complete Example"
    See the [Complete Reference Example](#complete-reference-example) for a full parameterized query with all options including `usage_guidance`.

```yaml
example_question_sqls:
  - id: eq_regional_sales
    question: ["Show sales for a specific region"]
    sql: ["SELECT region, SUM(amount) FROM sales WHERE region = :region_filter"]
    parameters:
      - name: region_filter
        type_hint: STRING
        description: ["Region code (NA, EMEA, APAC, LATAM)"]
        default_value:
          values: ["NA"]
```

---

## Join Specifications (Advanced)

Join specs define how tables relate to each other. Version 2 supports **relationship type annotations** that help Genie understand cardinality.

!!! tip "Complete Example"
    See the [Complete Reference Example](#complete-reference-example) for full join_specs with self-joins and relationship types.

### Join Spec Structure

```yaml
join_specs:
  - id: js_unique_id           # Unique identifier (auto-generated if not provided)
    left:
      identifier: "${catalog}.${schema}.table_a"
      alias: "a"               # Table alias used in SQL
    right:
      identifier: "${catalog}.${schema}.table_b"
      alias: "b"
    sql:
      - "a.foreign_key = b.primary_key"
      - "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"  # Relationship type
    instruction:
      - "Description of this join relationship"
```

### Relationship Types

Add relationship type annotations in the `sql` array to help Genie understand cardinality:

| Annotation | Meaning | Example |
|------------|---------|---------|
| `--rt=FROM_RELATIONSHIP_TYPE_ONE_TO_ONE--` | 1:1 relationship | User to UserProfile |
| `--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--` | Many:1 relationship | Orders to Customer |
| `--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_MANY--` | Many:Many relationship | Students to Courses |

### Example: Self-Join with Relationship Type

```yaml
join_specs:
  # Self-join for hierarchical data (employee -> manager)
  - id: js_employee_manager
    left:
      identifier: "${catalog}.${schema}.employees"
      alias: "e"
    right:
      identifier: "${catalog}.${schema}.employees"
      alias: "m"
    sql:
      - "e.manager_id = m.employee_id"
      - "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"
    instruction:
      - "Self-join to link employees to their managers"
      - "Use LEFT JOIN to include employees without managers"
```

---

## SQL Snippets

SQL snippets are reusable SQL fragments that Genie can apply when appropriate.

!!! tip "Complete Example"
    See the [Complete Reference Example](#complete-reference-example) for full sql_snippets with filters, expressions, and measures.

### Snippet Categories

| Category | Purpose | Example |
|----------|---------|---------|
| **filters** | Common WHERE conditions | `status = 'COMPLETED'` |
| **expressions** | Calculated fields | `(amount - cost)` |
| **measures** | Aggregation functions | `SUM(amount)` |

### Snippet Structure

| Field | Description | Required |
|-------|-------------|----------|
| `id` | Unique identifier | Optional (auto-generated) |
| `sql` | The SQL fragment (as a list) | **Required** |
| `display_name` | Human-readable name | **Required** |
| `instruction` | When/how to use this snippet | Optional |
| `synonyms` | Alternative trigger words | Optional |

### Quick Example

```yaml
sql_snippets:
  filters:
    - id: filter_completed
      sql: ["status = 'COMPLETED'"]
      display_name: "Completed Only"
      instruction: ["Filter to only completed transactions"]
      synonyms: ["successful", "finished"]
  
  measures:
    - id: measure_total_revenue
      sql: ["SUM(amount)"]
      display_name: "Total Revenue"
```

---

## Benchmarks

Benchmarks allow you to define test cases for your Genie space configuration. They are **stored locally only** and are **never sent to the Databricks API**.

!!! info "Local-Only Feature"
    Benchmarks help you validate your configuration generates correct SQL patterns. They are useful for testing before deployment but do not affect the deployed Genie space.

### Benchmark Structure

```yaml
benchmarks:
  questions:
    - question: "Natural language question"
      expected_sql: |
        SELECT ...
        FROM ...
        WHERE ...
```

### Example: Benchmarks for Testing

```yaml
benchmarks:
  questions:
    - question: "What was total revenue last month?"
      expected_sql: |
        SELECT SUM(amount) AS total_revenue
        FROM ${catalog}.${schema}.sales
        WHERE status = 'COMPLETED'
          AND transaction_date >= DATEADD(MONTH, -1, CURRENT_DATE)
    
    - question: "Show the top 10 customers by spending"
      expected_sql: |
        SELECT c.customer_name, SUM(s.amount) AS total_spent
        FROM ${catalog}.${schema}.sales s
        JOIN ${catalog}.${schema}.customers c 
          ON s.customer_id = c.customer_id
        WHERE s.status = 'COMPLETED'
        GROUP BY c.customer_name
        ORDER BY total_spent DESC
        LIMIT 10
    
    - question: "Who is John's manager?"
      expected_sql: |
        SELECT e.employee_name, m.employee_name AS manager_name
        FROM ${catalog}.${schema}.employees e
        LEFT JOIN ${catalog}.${schema}.employees m 
          ON e.manager_id = m.employee_id
        WHERE e.employee_name = 'John'
```

---

## Complete Examples

### Minimal Space

```yaml
version: 1

spaces:
  - space_id: "simple_space"
    title: "Simple Analytics"
    warehouse_id: "${warehouse_id}"
    
    data_sources:
      tables:
        - identifier: "${catalog}.${schema}.sales"
          description:
            - "Sales transactions"
```

### Employee Analytics (with Self-Join)

```yaml
version: 2
author: "data_team"

spaces:
  - space_id: "employee_analytics"
    title: "Employee Analytics Dashboard"
    description: "Analyze employee data including management hierarchy"
    warehouse_id: "${warehouse_id}"
    
    data_sources:
      tables:
        - identifier: "${catalog}.${schema}.employees"
          description:
            - "Employee master data with self-referential manager_id"
          column_configs:
            - column_name: "employee_id"
              description: "Unique employee identifier"
            - column_name: "manager_id"
              description: "References employee_id of this employee's manager"
            - column_name: "department_id"
              description: "Foreign key to departments table"
        
        - identifier: "${catalog}.${schema}.departments"
          description:
            - "Department reference data"
          column_configs:
            - column_name: "department_id"
              description: "Unique department identifier"
            - column_name: "budget"
              description: "Annual department budget in USD"
    
    instructions:
      text_instructions:
        - content: |
            SELF-JOIN for Manager Hierarchy:
            The employees table has a self-referential manager_id column.
            To find an employee's manager:
            
            SELECT e.first_name, e.last_name, m.first_name as manager_name
            FROM employees e
            LEFT JOIN employees m ON e.manager_id = m.employee_id
      
      sample_questions:
        - question: "Who reports to Sarah Johnson?"
        - question: "What is the average salary by department?"
        - question: "Show me the complete management chain for employee ID 42"
      
      join_specs:
        - id: js_employee_manager
          left:
            identifier: "${catalog}.${schema}.employees"
            alias: "e"
          right:
            identifier: "${catalog}.${schema}.employees"
            alias: "m"
          sql:
            - "e.manager_id = m.employee_id"
            - "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"
          instruction:
            - "Self-join to get manager information"
        
        - id: js_employee_department
          left:
            identifier: "${catalog}.${schema}.employees"
            alias: "e"
          right:
            identifier: "${catalog}.${schema}.departments"
            alias: "d"
          sql:
            - "e.department_id = d.department_id"
            - "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"
          instruction:
            - "Join employees to their department"
```

### Sales Analytics (Multi-Table)

```yaml
version: 2
author: "data_team"

spaces:
  - space_id: "sales_analytics"
    title: "Sales Analytics Space"
    description: "Analyze sales performance across regions and products"
    warehouse_id: "${warehouse_id}"
    
    data_sources:
      tables:
        - identifier: "${catalog}.${schema}.sales"
          description:
            - "Sales transactions with customer and product references"
        
        - identifier: "${catalog}.${schema}.customers"
          description:
            - "Customer master data"
          column_configs:
            - column_name: "segment"
              description: "Customer segment"
              dictionary:
                - value: "Enterprise"
                  description: "Large enterprise customers (>1000 employees)"
                - value: "SMB"
                  description: "Small and medium businesses"
                - value: "Consumer"
                  description: "Individual consumers"
        
        - identifier: "${catalog}.${schema}.products"
          description:
            - "Product catalog with categories and pricing"
    
    instructions:
      text_instructions:
        - content: |
            REGIONS: The sales table uses these region codes:
            - NA: North America
            - EMEA: Europe, Middle East, and Africa
            - APAC: Asia Pacific
            - LATAM: Latin America
      
      sample_questions:
        - question: "What are the top 10 products by revenue this quarter?"
        - question: "Compare sales performance across regions"
        - question: "Which customers have the highest lifetime value?"
      
      join_specs:
        - id: js_sales_customers
          left:
            identifier: "${catalog}.${schema}.sales"
            alias: "s"
          right:
            identifier: "${catalog}.${schema}.customers"
            alias: "c"
          sql:
            - "s.customer_id = c.customer_id"
            - "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"
          instruction:
            - "Join sales to customer details"
        
        - id: js_sales_products
          left:
            identifier: "${catalog}.${schema}.sales"
            alias: "s"
          right:
            identifier: "${catalog}.${schema}.products"
            alias: "p"
          sql:
            - "s.product_id = p.product_id"
            - "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"
          instruction:
            - "Join sales to product catalog"
```
