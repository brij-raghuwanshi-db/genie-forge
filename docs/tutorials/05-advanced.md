---
title: Advanced Patterns
description: Bulk operations, dynamic configs, and CI/CD integration
---

# 05 - Advanced Patterns

This notebook covers advanced Genie-Forge usage patterns: bulk operations, dynamic configuration generation, CI/CD integration, and advanced YAML configuration features.

!!! tip "Complete Configuration Reference"
    For a **comprehensive YAML example** showing ALL features (SQL snippets, parameters, relationship types, benchmarks), see the [Complete Reference Example](../guide/configuration.md#complete-reference-example) in the Configuration Guide.

## Setup

```python
from genie_forge import ProjectPaths, GenieClient
from pathlib import Path
import yaml

CATALOG = "main"
SCHEMA = "default"
VOLUME_NAME = "genie_forge"
PROJECT_NAME = "advanced"

paths = ProjectPaths(
    project_name=PROJECT_NAME,
    catalog=CATALOG,
    schema=SCHEMA,
    volume_name=VOLUME_NAME
)

paths.ensure_structure()
client = GenieClient()
```

## Bulk Operations

### Create Multiple Spaces from Template

```python
# Template for generating spaces
template = '''
spaces:
  - title: "{department} Analytics Dashboard"
    description: "AI-powered analytics for {department}"
    warehouse_id: ${{WAREHOUSE_ID}}
    tables:
      - {catalog}.{schema}.{department.lower()}_data
      - {catalog}.{schema}.{department.lower()}_metrics
    instructions: |
      You are a helpful analyst for the {department} team.
      Help users understand their data and find insights.
'''

departments = ["Sales", "Marketing", "Finance", "Operations", "HR"]

for dept in departments:
    config = template.format(
        department=dept,
        catalog=CATALOG,
        schema=SCHEMA
    )
    
    filename = f"{dept.lower()}_analytics.yaml"
    config_file = paths.spaces_dir / filename
    config_file.write_text(config)
    print(f"  ✓ Created: {filename}")

print(f"\n✓ Generated {len(departments)} space configurations")
```

### Bulk Validate

```python
!genie-forge validate --config {paths.spaces_dir}
```

### Bulk Deploy

```python
!genie-forge plan --env dev --config {paths.spaces_dir} --state {paths.state_file}
!genie-forge apply --env dev --config {paths.spaces_dir} --state {paths.state_file}
```

## Dynamic Configuration

### Generate from Data Catalog

```python
# Query available tables and generate spaces
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

# Get tables in schema
tables_df = spark.sql(f"SHOW TABLES IN {CATALOG}.{SCHEMA}")
tables = [row.tableName for row in tables_df.collect()]

# Group tables by prefix
from collections import defaultdict
grouped = defaultdict(list)

for table in tables:
    prefix = table.split('_')[0] if '_' in table else 'general'
    grouped[prefix].append(f"{CATALOG}.{SCHEMA}.{table}")

# Generate space for each group
for prefix, table_list in grouped.items():
    if len(table_list) >= 2:  # Only if multiple tables
        config = {
            'spaces': [{
                'title': f'{prefix.title()} Data Explorer',
                'description': f'Explore {prefix} related data',
                'warehouse_id': '${WAREHOUSE_ID}',
                'tables': table_list,
                'instructions': f'Help users analyze {prefix} data.'
            }]
        }
        
        config_file = paths.spaces_dir / f"{prefix}_explorer.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        print(f"  ✓ {prefix}: {len(table_list)} tables")
```

### Environment-Specific Overrides

```python
# Base configuration
base_config = {
    'spaces': [{
        'title': 'Analytics Space',
        'description': '${DESCRIPTION}',
        'warehouse_id': '${WAREHOUSE_ID}',
        'tables': ['${CATALOG}.${SCHEMA}.sales']
    }]
}

# Environment overrides
envs = {
    'dev': {
        'DESCRIPTION': 'Development analytics space',
        'WAREHOUSE_ID': 'dev-warehouse-id',
        'CATALOG': 'dev_catalog',
        'SCHEMA': 'dev_schema'
    },
    'prod': {
        'DESCRIPTION': 'Production analytics space',
        'WAREHOUSE_ID': 'prod-warehouse-id',
        'CATALOG': 'prod_catalog',
        'SCHEMA': 'prod_schema'
    }
}

for env_name, variables in envs.items():
    env_file = paths.root / "conf" / "environments" / f"{env_name}.yaml"
    env_file.parent.mkdir(parents=True, exist_ok=True)
    
    env_config = {'variables': variables}
    with open(env_file, 'w') as f:
        yaml.dump(env_config, f, default_flow_style=False)
    print(f"  ✓ Created: {env_name}.yaml")
```

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/genie-deploy.yml
name: Deploy Genie Spaces

on:
  push:
    branches: [main]
    paths: ['conf/spaces/**']
  pull_request:
    branches: [main]
    paths: ['conf/spaces/**']

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install genie-forge
      - run: genie-forge validate --config conf/spaces/ --strict

  plan:
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install genie-forge
      - run: genie-forge plan --env prod --config conf/spaces/
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}

  deploy:
    needs: plan
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install genie-forge
      - run: genie-forge apply --env prod --config conf/spaces/
        env:
          DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
          DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
```

### Databricks Workflow Job

```python
# Create a job to run genie-forge on schedule
job_config = {
    "name": "Genie Space Drift Detection",
    "tasks": [{
        "task_key": "drift_check",
        "notebook_task": {
            "notebook_path": "/Repos/team/genie-forge/notebooks/drift_check"
        },
        "existing_cluster_id": "your-cluster-id"
    }],
    "schedule": {
        "quartz_cron_expression": "0 0 8 * * ?",  # Daily at 8 AM
        "timezone_id": "America/New_York"
    },
    "email_notifications": {
        "on_failure": ["team@company.com"]
    }
}
```

## Monitoring & Alerting

### Drift Detection Notebook

```python
# drift_check.py - Run on schedule
from genie_forge import StateManager, GenieClient
import json

state = StateManager()
client = GenieClient()

# Check all environments
for env in ['dev', 'staging', 'prod']:
    drift = state.detect_drift(client, env=env)
    
    if drift:
        print(f"⚠️ Drift detected in {env}:")
        for space_key, changes in drift.items():
            print(f"  - {space_key}: {changes}")
        
        # Send alert (e.g., Slack, email)
        # send_alert(f"Genie drift detected in {env}", drift)
    else:
        print(f"✓ No drift in {env}")
```

### Space Health Check

```python
def check_space_health():
    """Verify all deployed spaces are accessible."""
    results = []
    
    spaces = client.list_spaces()
    for space in spaces:
        try:
            details = client.get_space(space['space_id'])
            results.append({
                'space_id': space['space_id'],
                'title': space['title'],
                'status': 'healthy'
            })
        except Exception as e:
            results.append({
                'space_id': space['space_id'],
                'title': space['title'],
                'status': 'error',
                'error': str(e)
            })
    
    return results

health = check_space_health()
healthy = sum(1 for r in health if r['status'] == 'healthy')
print(f"Space health: {healthy}/{len(health)} healthy")
```

## Advanced YAML Configuration

Beyond bulk operations, Genie-Forge supports several advanced configuration features.

!!! tip "Complete Configuration Reference"
    For a **comprehensive YAML example** showing ALL features, see the [Complete Reference Example](../guide/configuration.md#complete-reference-example) in the Configuration Guide.

### Key Advanced Features

| Feature | Description |
|---------|-------------|
| **Parameterized Queries** | Use `:param` syntax in SQL with `parameters` config |
| **Relationship Types** | Add `--rt=FROM_RELATIONSHIP_TYPE_*--` annotations to join_specs |
| **SQL Snippets** | Define reusable filters, expressions, and measures |
| **Benchmarks** | Local-only test cases for SQL validation |

### Quick Example: Relationship Types

```yaml
join_specs:
  - id: js_sales_customers
    left: { identifier: "${catalog}.${schema}.sales", alias: "s" }
    right: { identifier: "${catalog}.${schema}.customers", alias: "c" }
    sql:
      - "s.customer_id = c.customer_id"
      - "--rt=FROM_RELATIONSHIP_TYPE_MANY_TO_ONE--"
```

**Available relationship types:**

- `FROM_RELATIONSHIP_TYPE_ONE_TO_ONE`
- `FROM_RELATIONSHIP_TYPE_MANY_TO_ONE`
- `FROM_RELATIONSHIP_TYPE_MANY_TO_MANY`

### Benchmarks (Local Testing)

Validate your configuration generates correct SQL:

```yaml
benchmarks:
  questions:
    - question: "What was total revenue last month?"
      expected_sql: |
        SELECT SUM(amount) FROM sales
        WHERE transaction_date >= DATEADD(MONTH, -1, CURRENT_DATE)
```

!!! info "Benchmarks are Local-Only"
    Benchmarks are stored in your config but **never sent to the Databricks API**. Use them to test your space configuration before deployment.

---

## Best Practices

1. **Version Control**: Keep all configs in Git
2. **Environment Separation**: Use separate profiles for dev/prod
3. **Validation in CI**: Always validate before merging
4. **Drift Monitoring**: Schedule regular drift checks
5. **State Backup**: Include state file in version control
6. **Incremental Changes**: Small, frequent deployments over big bangs
7. **Use Complete Reference**: Start from the [Complete Reference Example](../guide/configuration.md#complete-reference-example) for new spaces
