"""
Demo table creation for Genie-Forge.

Creates sample tables in Unity Catalog for use with the demo configurations:
- employee_analytics.yaml (employees, departments, locations)
- sales_analytics.yaml (customers, products, sales)

The employees table includes a self-referential manager_id for hierarchical queries.
"""

from __future__ import annotations

from typing import Any

# Table metadata for display
DEMO_TABLES_INFO = {
    "locations": {
        "rows": 8,
        "description": "Office locations (city, state, country)",
    },
    "departments": {
        "rows": 8,
        "description": "Department reference (name, budget)",
    },
    "employees": {
        "rows": 30,
        "description": "Employees with SELF-JOIN manager_id",
    },
    "customers": {
        "rows": 10,
        "description": "Customer master (name, segment)",
    },
    "products": {
        "rows": 10,
        "description": "Product catalog (name, category, price)",
    },
    "sales": {
        "rows": 30,
        "description": "Sales transactions (customer, product, amount)",
    },
}

# Function metadata for display
DEMO_FUNCTIONS_INFO = {
    "calculate_tenure_years": {
        "description": "Calculate employee tenure in years from hire date",
    },
    "percent_change": {
        "description": "Calculate percentage change between two values",
    },
}


def create_demo_tables(
    client: Any,
    catalog: str,
    schema: str,
    warehouse_id: str,
) -> dict[str, Any]:
    """
    Create demo tables using Databricks SQL Statement Execution API.

    Args:
        client: GenieClient instance
        catalog: Unity Catalog name
        schema: Schema name
        warehouse_id: SQL warehouse ID

    Returns:
        dict with creation results
    """
    ws_client = client.client

    results: dict[str, Any] = {
        "success": True,
        "tables_created": 0,
        "total_rows": 0,
        "tables": {},
    }

    def execute_sql(statement: str, description: str = "") -> dict:
        """Execute a SQL statement and return result."""
        try:
            response = ws_client.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=statement,
                catalog=catalog,
                schema=schema,
                wait_timeout="30s",
            )
            # Wait for completion if needed
            if response.status and response.status.state:
                state = response.status.state.value
                if state == "SUCCEEDED":
                    return {"success": True}
                elif state == "FAILED":
                    error = (
                        response.status.error.message if response.status.error else "Unknown error"
                    )
                    return {"success": False, "error": error}
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Create tables in order (respecting foreign key dependencies)
    # =========================================================================

    # 1. LOCATIONS
    result = execute_sql(f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.locations (
            location_id INT,
            city STRING,
            state STRING,
            country STRING,
            address STRING
        )
        COMMENT 'Office locations for HR analytics demo'
    """)

    if result["success"]:
        # Insert data
        execute_sql(f"""
            MERGE INTO {catalog}.{schema}.locations AS target
            USING (
                SELECT * FROM (VALUES
                    (1, 'San Francisco', 'California', 'USA', '123 Market St'),
                    (2, 'New York', 'New York', 'USA', '456 Broadway'),
                    (3, 'Seattle', 'Washington', 'USA', '789 Pike St'),
                    (4, 'Austin', 'Texas', 'USA', '321 Congress Ave'),
                    (5, 'London', NULL, 'UK', '10 Downing St'),
                    (6, 'Berlin', NULL, 'Germany', '1 Unter den Linden'),
                    (7, 'Tokyo', NULL, 'Japan', '1-1-1 Shibuya'),
                    (8, 'Singapore', NULL, 'Singapore', '1 Raffles Place')
                ) AS t(location_id, city, state, country, address)
            ) AS source
            ON target.location_id = source.location_id
            WHEN NOT MATCHED THEN INSERT *
        """)
        results["tables"]["locations"] = {"success": True, "rows": 8}
        results["tables_created"] += 1
        results["total_rows"] += 8
    else:
        results["tables"]["locations"] = result
        results["success"] = False

    # 2. DEPARTMENTS
    result = execute_sql(f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.departments (
            department_id INT,
            department_name STRING,
            budget DECIMAL(15,2),
            cost_center STRING
        )
        COMMENT 'Department reference for HR analytics demo'
    """)

    if result["success"]:
        execute_sql(f"""
            MERGE INTO {catalog}.{schema}.departments AS target
            USING (
                SELECT * FROM (VALUES
                    (1, 'Engineering', 5000000.00, 'CC-ENG-001'),
                    (2, 'Product', 2000000.00, 'CC-PRD-002'),
                    (3, 'Sales', 3000000.00, 'CC-SAL-003'),
                    (4, 'Marketing', 1500000.00, 'CC-MKT-004'),
                    (5, 'Human Resources', 800000.00, 'CC-HR-005'),
                    (6, 'Finance', 1200000.00, 'CC-FIN-006'),
                    (7, 'Operations', 2500000.00, 'CC-OPS-007'),
                    (8, 'Legal', 600000.00, 'CC-LEG-008')
                ) AS t(department_id, department_name, budget, cost_center)
            ) AS source
            ON target.department_id = source.department_id
            WHEN NOT MATCHED THEN INSERT *
        """)
        results["tables"]["departments"] = {"success": True, "rows": 8}
        results["tables_created"] += 1
        results["total_rows"] += 8
    else:
        results["tables"]["departments"] = result
        results["success"] = False

    # 3. EMPLOYEES (with self-referential manager_id)
    result = execute_sql(f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.employees (
            employee_id INT,
            first_name STRING,
            last_name STRING,
            email STRING,
            job_title STRING,
            department_id INT,
            manager_id INT COMMENT 'Self-join: references employee_id of manager',
            hire_date DATE,
            salary DECIMAL(12,2),
            location_id INT,
            is_active BOOLEAN
        )
        COMMENT 'Employee master with self-referential manager hierarchy'
    """)

    if result["success"]:
        # Insert employees in batches to handle the hierarchy
        # CEO first (no manager)
        execute_sql(f"""
            MERGE INTO {catalog}.{schema}.employees AS target
            USING (
                SELECT * FROM (VALUES
                    (1, 'Alice', 'Johnson', 'alice.johnson@company.com', 'Chief Executive Officer',
                     1, NULL, DATE'2015-01-15', 450000.00, 1, true),
                    (2, 'Bob', 'Smith', 'bob.smith@company.com', 'VP of Engineering',
                     1, 1, DATE'2016-03-20', 280000.00, 1, true),
                    (3, 'Carol', 'Williams', 'carol.williams@company.com', 'VP of Product',
                     2, 1, DATE'2016-05-10', 270000.00, 1, true),
                    (4, 'David', 'Brown', 'david.brown@company.com', 'VP of Sales',
                     3, 1, DATE'2017-02-01', 260000.00, 2, true),
                    (5, 'Eva', 'Davis', 'eva.davis@company.com', 'VP of Marketing',
                     4, 1, DATE'2017-08-15', 250000.00, 2, true),
                    (6, 'Frank', 'Miller', 'frank.miller@company.com', 'Director of Backend',
                     1, 2, DATE'2018-01-10', 200000.00, 1, true),
                    (7, 'Grace', 'Wilson', 'grace.wilson@company.com', 'Director of Frontend',
                     1, 2, DATE'2018-04-22', 195000.00, 3, true),
                    (8, 'Henry', 'Taylor', 'henry.taylor@company.com', 'Director of Product',
                     2, 3, DATE'2018-06-15', 190000.00, 1, true),
                    (9, 'Ivy', 'Anderson', 'ivy.anderson@company.com', 'Director of Sales West',
                     3, 4, DATE'2018-09-01', 185000.00, 1, true),
                    (10, 'Jack', 'Thomas', 'jack.thomas@company.com', 'Director of Sales East',
                     3, 4, DATE'2019-01-15', 180000.00, 2, true)
                ) AS t(employee_id, first_name, last_name, email, job_title,
                       department_id, manager_id, hire_date, salary, location_id, is_active)
            ) AS source
            ON target.employee_id = source.employee_id
            WHEN NOT MATCHED THEN INSERT *
        """)

        # More employees (managers and ICs)
        execute_sql(f"""
            MERGE INTO {catalog}.{schema}.employees AS target
            USING (
                SELECT * FROM (VALUES
                    (11, 'Karen', 'Jackson', 'karen.jackson@company.com', 'Engineering Manager',
                     1, 6, DATE'2019-03-20', 160000.00, 1, true),
                    (12, 'Leo', 'White', 'leo.white@company.com', 'Engineering Manager',
                     1, 7, DATE'2019-05-10', 155000.00, 3, true),
                    (13, 'Mia', 'Harris', 'mia.harris@company.com', 'Product Manager',
                     2, 8, DATE'2019-07-01', 150000.00, 1, true),
                    (14, 'Nathan', 'Martin', 'nathan.martin@company.com', 'Sales Manager',
                     3, 9, DATE'2019-09-15', 145000.00, 4, true),
                    (15, 'Olivia', 'Garcia', 'olivia.garcia@company.com', 'Marketing Manager',
                     4, 5, DATE'2020-01-10', 140000.00, 2, true),
                    (16, 'Peter', 'Martinez', 'peter.martinez@company.com', 'Senior Software Engineer',
                     1, 11, DATE'2020-03-15', 175000.00, 1, true),
                    (17, 'Quinn', 'Robinson', 'quinn.robinson@company.com', 'Senior Software Engineer',
                     1, 11, DATE'2020-05-20', 170000.00, 1, true),
                    (18, 'Rachel', 'Clark', 'rachel.clark@company.com', 'Senior Frontend Engineer',
                     1, 12, DATE'2020-07-01', 165000.00, 3, true),
                    (19, 'Samuel', 'Rodriguez', 'samuel.rodriguez@company.com', 'Senior Product Manager',
                     2, 13, DATE'2020-09-10', 160000.00, 1, true),
                    (20, 'Tina', 'Lewis', 'tina.lewis@company.com', 'Senior Sales Rep',
                     3, 14, DATE'2020-11-15', 130000.00, 4, true)
                ) AS t(employee_id, first_name, last_name, email, job_title,
                       department_id, manager_id, hire_date, salary, location_id, is_active)
            ) AS source
            ON target.employee_id = source.employee_id
            WHEN NOT MATCHED THEN INSERT *
        """)

        # Junior employees and recent hires
        execute_sql(f"""
            MERGE INTO {catalog}.{schema}.employees AS target
            USING (
                SELECT * FROM (VALUES
                    (21, 'Uma', 'Lee', 'uma.lee@company.com', 'Software Engineer',
                     1, 11, DATE'2021-01-20', 130000.00, 1, true),
                    (22, 'Victor', 'Walker', 'victor.walker@company.com', 'Software Engineer',
                     1, 11, DATE'2021-03-15', 125000.00, 1, true),
                    (23, 'Wendy', 'Hall', 'wendy.hall@company.com', 'Frontend Engineer',
                     1, 12, DATE'2021-05-10', 120000.00, 3, true),
                    (24, 'Xavier', 'Allen', 'xavier.allen@company.com', 'Associate Product Manager',
                     2, 13, DATE'2021-07-01', 115000.00, 1, true),
                    (25, 'Yara', 'Young', 'yara.young@company.com', 'Sales Representative',
                     3, 14, DATE'2021-09-15', 100000.00, 4, true),
                    (26, 'Zack', 'King', 'zack.king@company.com', 'Junior Software Engineer',
                     1, 11, DATE'2025-10-01', 95000.00, 1, true),
                    (27, 'Amy', 'Wright', 'amy.wright@company.com', 'Junior Software Engineer',
                     1, 12, DATE'2025-11-15', 92000.00, 3, true),
                    (28, 'Brian', 'Scott', 'brian.scott@company.com', 'Marketing Coordinator',
                     4, 15, DATE'2025-12-01', 75000.00, 2, true),
                    (29, 'Chloe', 'Green', 'chloe.green@company.com', 'Sales Development Rep',
                     3, 14, DATE'2026-01-10', 70000.00, 4, true),
                    (30, 'Derek', 'Adams', 'derek.adams@company.com', 'Former Engineer',
                     1, 11, DATE'2019-06-01', 140000.00, 1, false)
                ) AS t(employee_id, first_name, last_name, email, job_title,
                       department_id, manager_id, hire_date, salary, location_id, is_active)
            ) AS source
            ON target.employee_id = source.employee_id
            WHEN NOT MATCHED THEN INSERT *
        """)

        results["tables"]["employees"] = {"success": True, "rows": 30}
        results["tables_created"] += 1
        results["total_rows"] += 30
    else:
        results["tables"]["employees"] = result
        results["success"] = False

    # 4. CUSTOMERS
    result = execute_sql(f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.customers (
            customer_id INT,
            customer_name STRING,
            segment STRING,
            email STRING,
            created_at DATE
        )
        COMMENT 'Customer master for sales analytics demo'
    """)

    if result["success"]:
        execute_sql(f"""
            MERGE INTO {catalog}.{schema}.customers AS target
            USING (
                SELECT * FROM (VALUES
                    (1, 'Acme Corporation', 'Enterprise', 'contact@acme.com', DATE'2020-01-15'),
                    (2, 'TechStart Inc', 'SMB', 'hello@techstart.io', DATE'2020-03-20'),
                    (3, 'Global Retail Ltd', 'Enterprise', 'sales@globalretail.com', DATE'2020-05-10'),
                    (4, 'Local Shop', 'Consumer', 'owner@localshop.com', DATE'2020-07-01'),
                    (5, 'DataDriven Co', 'SMB', 'info@datadriven.co', DATE'2020-09-15'),
                    (6, 'Mega Industries', 'Enterprise', 'procurement@mega.com', DATE'2021-01-10'),
                    (7, 'Startup Labs', 'SMB', 'team@startuplabs.io', DATE'2021-03-20'),
                    (8, 'Consumer Direct', 'Consumer', 'support@consumerdirect.com', DATE'2021-05-15'),
                    (9, 'Enterprise Solutions', 'Enterprise', 'sales@enterprise-solutions.com', DATE'2021-07-01'),
                    (10, 'Small Biz Pro', 'SMB', 'contact@smallbizpro.com', DATE'2021-09-10')
                ) AS t(customer_id, customer_name, segment, email, created_at)
            ) AS source
            ON target.customer_id = source.customer_id
            WHEN NOT MATCHED THEN INSERT *
        """)
        results["tables"]["customers"] = {"success": True, "rows": 10}
        results["tables_created"] += 1
        results["total_rows"] += 10
    else:
        results["tables"]["customers"] = result
        results["success"] = False

    # 5. PRODUCTS
    result = execute_sql(f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.products (
            product_id INT,
            product_name STRING,
            category STRING,
            unit_price DECIMAL(10,2),
            is_active BOOLEAN
        )
        COMMENT 'Product catalog for sales analytics demo'
    """)

    if result["success"]:
        execute_sql(f"""
            MERGE INTO {catalog}.{schema}.products AS target
            USING (
                SELECT * FROM (VALUES
                    (1, 'Basic Analytics Platform', 'Software', 999.99, true),
                    (2, 'Pro Analytics Platform', 'Software', 2499.99, true),
                    (3, 'Enterprise Analytics Suite', 'Software', 9999.99, true),
                    (4, 'Data Integration Tool', 'Software', 499.99, true),
                    (5, 'Reporting Dashboard', 'Software', 299.99, true),
                    (6, 'Consulting - Basic', 'Services', 150.00, true),
                    (7, 'Consulting - Premium', 'Services', 300.00, true),
                    (8, 'Training Workshop', 'Services', 500.00, true),
                    (9, 'Support - Standard', 'Support', 99.99, true),
                    (10, 'Support - Premium', 'Support', 249.99, true)
                ) AS t(product_id, product_name, category, unit_price, is_active)
            ) AS source
            ON target.product_id = source.product_id
            WHEN NOT MATCHED THEN INSERT *
        """)
        results["tables"]["products"] = {"success": True, "rows": 10}
        results["tables_created"] += 1
        results["total_rows"] += 10
    else:
        results["tables"]["products"] = result
        results["success"] = False

    # 6. SALES
    result = execute_sql(f"""
        CREATE TABLE IF NOT EXISTS {catalog}.{schema}.sales (
            sale_id INT,
            customer_id INT,
            product_id INT,
            sale_date DATE,
            quantity INT,
            amount DECIMAL(12,2),
            region STRING
        )
        COMMENT 'Sales transactions for sales analytics demo'
    """)

    if result["success"]:
        execute_sql(f"""
            MERGE INTO {catalog}.{schema}.sales AS target
            USING (
                SELECT * FROM (VALUES
                    (1, 1, 3, DATE'2024-01-15', 2, 19999.98, 'AMER'),
                    (2, 2, 2, DATE'2024-01-20', 1, 2499.99, 'AMER'),
                    (3, 3, 3, DATE'2024-02-10', 5, 49999.95, 'EMEA'),
                    (4, 4, 1, DATE'2024-02-15', 1, 999.99, 'AMER'),
                    (5, 5, 4, DATE'2024-03-01', 3, 1499.97, 'AMER'),
                    (6, 6, 3, DATE'2024-03-20', 10, 99999.90, 'APAC'),
                    (7, 1, 7, DATE'2024-04-05', 20, 6000.00, 'AMER'),
                    (8, 7, 2, DATE'2024-04-15', 2, 4999.98, 'AMER'),
                    (9, 8, 1, DATE'2024-05-10', 1, 999.99, 'APAC'),
                    (10, 9, 3, DATE'2024-05-25', 3, 29999.97, 'EMEA'),
                    (11, 10, 5, DATE'2024-06-01', 5, 1499.95, 'AMER'),
                    (12, 2, 6, DATE'2024-06-15', 10, 1500.00, 'AMER'),
                    (13, 3, 8, DATE'2024-07-10', 8, 4000.00, 'EMEA'),
                    (14, 4, 9, DATE'2024-07-20', 12, 1199.88, 'AMER'),
                    (15, 5, 10, DATE'2024-08-05', 6, 1499.94, 'AMER')
                ) AS t(sale_id, customer_id, product_id, sale_date, quantity, amount, region)
            ) AS source
            ON target.sale_id = source.sale_id
            WHEN NOT MATCHED THEN INSERT *
        """)

        execute_sql(f"""
            MERGE INTO {catalog}.{schema}.sales AS target
            USING (
                SELECT * FROM (VALUES
                    (16, 6, 2, DATE'2024-08-15', 5, 12499.95, 'APAC'),
                    (17, 7, 4, DATE'2024-09-01', 4, 1999.96, 'AMER'),
                    (18, 8, 5, DATE'2024-09-20', 10, 2999.90, 'APAC'),
                    (19, 9, 3, DATE'2024-10-10', 2, 19999.98, 'EMEA'),
                    (20, 10, 7, DATE'2024-10-25', 15, 4500.00, 'AMER'),
                    (21, 1, 3, DATE'2024-11-05', 3, 29999.97, 'AMER'),
                    (22, 2, 8, DATE'2024-11-20', 5, 2500.00, 'AMER'),
                    (23, 3, 10, DATE'2024-12-01', 20, 4999.80, 'EMEA'),
                    (24, 6, 3, DATE'2024-12-15', 8, 79999.92, 'APAC'),
                    (25, 4, 2, DATE'2025-01-10', 1, 2499.99, 'AMER'),
                    (26, 5, 3, DATE'2025-01-20', 2, 19999.98, 'AMER'),
                    (27, 7, 1, DATE'2025-02-05', 3, 2999.97, 'AMER'),
                    (28, 9, 6, DATE'2025-02-15', 10, 1500.00, 'EMEA'),
                    (29, 10, 4, DATE'2025-03-01', 5, 2499.95, 'AMER'),
                    (30, 1, 7, DATE'2025-03-20', 25, 7500.00, 'AMER')
                ) AS t(sale_id, customer_id, product_id, sale_date, quantity, amount, region)
            ) AS source
            ON target.sale_id = source.sale_id
            WHEN NOT MATCHED THEN INSERT *
        """)

        results["tables"]["sales"] = {"success": True, "rows": 30}
        results["tables_created"] += 1
        results["total_rows"] += 30
    else:
        results["tables"]["sales"] = result
        results["success"] = False

    return results


def check_demo_objects_exist(
    client: Any,
    catalog: str,
    schema: str,
    warehouse_id: str,
) -> dict[str, Any]:
    """
    Check which demo objects exist in the catalog.

    Args:
        client: GenieClient instance
        catalog: Unity Catalog name
        schema: Schema name
        warehouse_id: SQL warehouse ID

    Returns:
        dict with existence check results for each object
    """
    ws_client = client.client

    results: dict[str, Any] = {
        "existing_tables": [],
        "existing_functions": [],
        "missing_tables": [],
        "missing_functions": [],
        "total_existing": 0,
        "total_missing": 0,
    }

    def execute_sql(statement: str) -> dict:
        """Execute a SQL statement and return result."""
        try:
            response = ws_client.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=statement,
                catalog=catalog,
                schema=schema,
                wait_timeout="30s",
            )
            if response.status and response.status.state:
                state = response.status.state.value
                if state == "SUCCEEDED":
                    # Check if we got any results
                    if response.result and response.result.data_array:
                        return {"success": True, "data": response.result.data_array}
                    return {"success": True, "data": []}
                elif state == "FAILED":
                    error = (
                        response.status.error.message if response.status.error else "Unknown error"
                    )
                    return {"success": False, "error": error}
            return {"success": True, "data": []}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # Check tables
    for tbl_name in DEMO_TABLES_INFO.keys():
        full_name = f"{catalog}.{schema}.{tbl_name}"
        # Use SHOW TABLES to check existence
        check_result = execute_sql(f"SHOW TABLES IN {catalog}.{schema} LIKE '{tbl_name}'")
        if check_result.get("success") and check_result.get("data"):
            results["existing_tables"].append(full_name)
            results["total_existing"] += 1
        else:
            results["missing_tables"].append(full_name)
            results["total_missing"] += 1

    # Check functions
    for func_name in DEMO_FUNCTIONS_INFO.keys():
        full_name = f"{catalog}.{schema}.{func_name}"
        # Use SHOW FUNCTIONS to check existence
        check_result = execute_sql(f"SHOW USER FUNCTIONS IN {catalog}.{schema} LIKE '{func_name}'")
        if check_result.get("success") and check_result.get("data"):
            results["existing_functions"].append(full_name)
            results["total_existing"] += 1
        else:
            results["missing_functions"].append(full_name)
            results["total_missing"] += 1

    return results


def cleanup_demo_tables(
    client: Any,
    catalog: str,
    schema: str,
    warehouse_id: str,
    skip_existence_check: bool = False,
) -> dict[str, Any]:
    """
    Delete demo tables and functions created by setup-demo.

    Args:
        client: GenieClient instance
        catalog: Unity Catalog name
        schema: Schema name
        warehouse_id: SQL warehouse ID
        skip_existence_check: If True, skip checking if objects exist first

    Returns:
        dict with cleanup results
    """
    ws_client = client.client

    results: dict[str, Any] = {
        "success": True,
        "deleted_count": 0,
        "skipped_count": 0,
        "already_clean": False,
        "objects": {},
    }

    def execute_sql(statement: str) -> dict:
        """Execute a SQL statement and return result."""
        try:
            response = ws_client.statement_execution.execute_statement(
                warehouse_id=warehouse_id,
                statement=statement,
                catalog=catalog,
                schema=schema,
                wait_timeout="30s",
            )
            if response.status and response.status.state:
                state = response.status.state.value
                if state == "SUCCEEDED":
                    return {"success": True}
                elif state == "FAILED":
                    error = (
                        response.status.error.message if response.status.error else "Unknown error"
                    )
                    return {"success": False, "error": error}
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # First, check which objects exist
    if not skip_existence_check:
        existence = check_demo_objects_exist(client, catalog, schema, warehouse_id)
        existing_objects = set(existence["existing_tables"] + existence["existing_functions"])

        # If nothing exists, we're already clean
        if existence["total_existing"] == 0:
            results["already_clean"] = True
            results["success"] = True
            return results
    else:
        existing_objects = None  # Will delete all without checking

    # Drop tables in reverse dependency order
    # (tables with foreign keys should be dropped before referenced tables)
    drop_order = [
        ("sales", "TABLE"),
        ("employees", "TABLE"),  # Has FK to departments and locations
        ("customers", "TABLE"),
        ("products", "TABLE"),
        ("departments", "TABLE"),
        ("locations", "TABLE"),
        ("calculate_tenure_years", "FUNCTION"),
        ("percent_change", "FUNCTION"),
    ]

    for obj_name, obj_type in drop_order:
        full_name = f"{catalog}.{schema}.{obj_name}"

        # Skip if we checked existence and object doesn't exist
        if existing_objects is not None and full_name not in existing_objects:
            results["objects"][full_name] = {
                "success": True,
                "skipped": True,
                "reason": "Does not exist",
            }
            results["skipped_count"] += 1
            continue

        if obj_type == "TABLE":
            result = execute_sql(f"DROP TABLE IF EXISTS {full_name}")
        else:
            result = execute_sql(f"DROP FUNCTION IF EXISTS {full_name}")

        results["objects"][full_name] = result

        if result["success"]:
            results["deleted_count"] += 1
        else:
            # Don't mark overall as failed for "not found" errors
            # since DROP IF EXISTS should handle that
            pass

    return results


def get_demo_objects_summary(catalog: str, schema: str) -> dict[str, Any]:
    """
    Get a summary of all demo objects that would be created/deleted.

    Args:
        catalog: Unity Catalog name
        schema: Schema name

    Returns:
        dict with tables and functions info
    """
    return {
        "tables": [
            {
                "full_name": f"{catalog}.{schema}.{name}",
                "name": name,
                "type": "TABLE",
                "rows": info["rows"],
                "description": info["description"],
                "drop_sql": f"DROP TABLE IF EXISTS {catalog}.{schema}.{name};",
            }
            for name, info in DEMO_TABLES_INFO.items()
        ],
        "functions": [
            {
                "full_name": f"{catalog}.{schema}.{name}",
                "name": name,
                "type": "FUNCTION",
                "description": info["description"],
                "drop_sql": f"DROP FUNCTION IF EXISTS {catalog}.{schema}.{name};",
            }
            for name, info in DEMO_FUNCTIONS_INFO.items()
        ],
        "total_count": len(DEMO_TABLES_INFO) + len(DEMO_FUNCTIONS_INFO),
    }
