"""Integration tests for Genie-Forge.

These tests require a real Databricks workspace connection.

To run:
    # Set the profile to use
    export GENIE_PROFILE=your-profile-name

    # Run integration tests only
    pytest tests/integration -v

    # Or run with marker
    pytest -m integration -v

Required environment:
    GENIE_PROFILE: Name of profile in ~/.databrickscfg with Genie access

Optional environment:
    GENIE_CATALOG: Unity Catalog for demo table tests (default: main)
    GENIE_SCHEMA: Schema for demo table tests (default: default)
    GENIE_WAREHOUSE_ID: SQL Warehouse ID for tests
"""
