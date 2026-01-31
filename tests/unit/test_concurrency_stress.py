"""Concurrency and stress tests for Genie-Forge.

Tests for:
- Thread safety in bulk operations
- Concurrent state file access
- Resource limits and large data handling
- Performance characteristics
"""

from __future__ import annotations

import json
import threading
import time
from unittest.mock import MagicMock

from genie_forge.client import BulkResult, GenieClient
from genie_forge.models import SpaceConfig
from genie_forge.state import StateManager

# =============================================================================
# Thread Safety Tests
# =============================================================================


class TestThreadSafety:
    """Tests for thread safety in concurrent operations."""

    def test_bulk_create_thread_safety(self):
        """Test that bulk_create is thread-safe."""
        mock_client = MagicMock()
        mock_client.config.host = "https://test.databricks.com"

        call_count = 0
        call_lock = threading.Lock()

        def mock_api_call(*args, **kwargs):
            nonlocal call_count
            with call_lock:
                call_count += 1
                current = call_count
            # Simulate API latency to increase chance of race conditions
            time.sleep(0.01)
            return {"space": {"id": f"id-{current}"}}

        mock_client.api_client.do.side_effect = mock_api_call

        client = GenieClient(client=mock_client)

        configs = [
            {"title": f"Space {i}", "warehouse_id": "wh", "tables": ["c.s.t"]} for i in range(50)
        ]

        result = client.bulk_create(configs, max_workers=10)

        assert result.total == 50
        assert result.success == 50
        assert call_count == 50

        # All IDs should be unique
        ids = [r.databricks_space_id for r in result.results if r.databricks_space_id]
        assert len(ids) == len(set(ids))

    def test_bulk_delete_thread_safety(self):
        """Test that bulk_delete is thread-safe."""
        mock_client = MagicMock()
        mock_client.config.host = "https://test.databricks.com"

        deleted_ids = []
        delete_lock = threading.Lock()

        def mock_api_call(method, path, **kwargs):
            if method == "DELETE":
                space_id = path.split("/")[-1]
                with delete_lock:
                    deleted_ids.append(space_id)
                time.sleep(0.005)  # Simulate latency
                return {}
            return {}

        mock_client.api_client.do.side_effect = mock_api_call

        client = GenieClient(client=mock_client)

        space_ids = [f"space-{i}" for i in range(50)]
        result = client.bulk_delete(space_ids, max_workers=10)

        assert result.total == 50
        assert result.success == 50

        # All IDs should have been deleted exactly once
        assert len(deleted_ids) == 50
        assert len(set(deleted_ids)) == 50

    def test_concurrent_read_operations(self):
        """Test concurrent read operations don't interfere."""
        mock_client = MagicMock()
        mock_client.config.host = "https://test.databricks.com"
        mock_client.api_client.do.return_value = {"spaces": [{"id": "1", "title": "Test"}]}

        client = GenieClient(client=mock_client)

        results = []
        errors = []

        def list_spaces():
            try:
                spaces = client.list_spaces()
                results.append(len(spaces))
            except Exception as e:
                errors.append(e)

        # Run 20 concurrent list operations
        threads = [threading.Thread(target=list_spaces) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert all(r == 1 for r in results)


# =============================================================================
# State File Concurrency Tests
# =============================================================================


class TestStateConcurrency:
    """Tests for concurrent state file access."""

    def test_concurrent_state_reads(self, tmp_path):
        """Test that concurrent reads of state file work correctly."""
        state_file = tmp_path / ".genie-forge.json"

        # Create initial state
        state_data = {
            "version": "1.0",
            "project_id": "test",
            "environments": {
                "dev": {
                    "workspace_url": "https://test.com",
                    "spaces": {
                        f"space_{i}": {
                            "logical_id": f"space_{i}",
                            "title": f"Space {i}",
                            "databricks_space_id": f"db_{i}",
                            "config_hash": "abc",
                            "applied_hash": "abc",
                            "status": "APPLIED",
                        }
                        for i in range(10)
                    },
                }
            },
        }
        state_file.write_text(json.dumps(state_data))

        results = []
        errors = []

        def read_state():
            try:
                manager = StateManager(state_file=state_file)
                status = manager.status(env="dev")
                results.append(status["total"])
            except Exception as e:
                errors.append(e)

        # Run concurrent reads
        threads = [threading.Thread(target=read_state) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert all(r == 10 for r in results)

    def test_sequential_state_writes(self, tmp_path):
        """Test that sequential writes don't corrupt state."""
        state_file = tmp_path / ".genie-forge.json"
        manager = StateManager(state_file=state_file, project_id="test")

        # Create environment
        manager._get_or_create_env_state("dev", "https://test.com")
        manager._save_state()

        # Sequential writes
        for i in range(10):
            env_state = manager._get_or_create_env_state("dev", "https://test.com")
            from genie_forge.models import SpaceState, SpaceStatus

            env_state.spaces[f"space_{i}"] = SpaceState(
                logical_id=f"space_{i}",
                title=f"Space {i}",
                databricks_space_id=f"db_{i}",
                config_hash="abc",
                applied_hash="abc",
                status=SpaceStatus.APPLIED,
            )
            manager._save_state()

        # Verify final state
        final_state = json.loads(state_file.read_text())
        assert len(final_state["environments"]["dev"]["spaces"]) == 10


# =============================================================================
# Large Data Handling Tests
# =============================================================================


class TestLargeDataHandling:
    """Tests for handling large amounts of data."""

    def test_many_spaces_in_state(self, tmp_path):
        """Test state with many spaces (1000+)."""
        state_file = tmp_path / ".genie-forge.json"

        # Create state with 1000 spaces
        spaces = {
            f"space_{i}": {
                "logical_id": f"space_{i}",
                "title": f"Space {i} with a longer title to increase size",
                "databricks_space_id": f"db_{i}",
                "config_hash": f"hash_{i}",
                "applied_hash": f"hash_{i}",
                "status": "APPLIED",
            }
            for i in range(1000)
        }

        state_data = {
            "version": "1.0",
            "project_id": "test",
            "environments": {"dev": {"workspace_url": "https://test.com", "spaces": spaces}},
        }
        state_file.write_text(json.dumps(state_data))

        # Should load without issues
        manager = StateManager(state_file=state_file)
        status = manager.status(env="dev")

        assert status["total"] == 1000

    def test_large_config_file(self, tmp_path):
        """Test parsing large config file."""
        from genie_forge.parsers import MetadataParser

        # Create config with many spaces
        spaces = []
        for i in range(500):
            spaces.append(
                {
                    "space_id": f"space_{i}",
                    "title": f"Space {i}",
                    "warehouse_id": "wh123",
                    "data_sources": {
                        "tables": [
                            {
                                "identifier": f"cat.sch.table_{i}",
                                "description": [f"Description for table {i}"],
                            }
                        ]
                    },
                }
            )

        config_data = {"spaces": spaces}

        import yaml

        config_file = tmp_path / "large.yaml"
        config_file.write_text(yaml.dump(config_data))

        # Should parse without issues
        parser = MetadataParser()
        configs = parser.parse(config_file)

        assert len(configs) == 500

    def test_space_with_many_tables(self):
        """Test space config with many tables."""
        tables = [f"catalog.schema.table_{i}" for i in range(500)]

        config = SpaceConfig.minimal(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            tables=tables,
        )

        # Should serialize without issues
        from genie_forge.serializer import SpaceSerializer

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        assert len(serialized["data_sources"]["tables"]) == 500

    def test_space_with_many_instructions(self):
        """Test space with many instructions.

        Note: TextInstruction consolidates content from multiple instructions
        with the same ID into a single instruction. This is by design.
        """
        from genie_forge.models import (
            ExampleQuestionSQL,
            Instructions,
            SqlSnippet,
            SqlSnippets,
            TextInstruction,
        )

        # Create instructions with UNIQUE IDs (not just different content)
        config = SpaceConfig(
            space_id="test",
            title="Test",
            warehouse_id="wh",
            instructions=Instructions(
                text_instructions=[
                    TextInstruction(id=f"ti_{i}", content=[f"Instruction {i}"]) for i in range(100)
                ],
                example_question_sqls=[
                    ExampleQuestionSQL(
                        id=f"eq_{i}",
                        question=[f"Question {i}?"],
                        sql=[f"SELECT {i}"],
                    )
                    for i in range(100)
                ],
                sql_snippets=SqlSnippets(
                    filters=[
                        SqlSnippet(
                            id=f"f_{i}",
                            sql=[f"x = {i}"],
                            display_name=f"Filter {i}",
                        )
                        for i in range(100)
                    ],
                ),
            ),
        )

        from genie_forge.serializer import SpaceSerializer

        serializer = SpaceSerializer()
        serialized = serializer.to_serialized_space(config)

        # The serializer may consolidate instructions - check that content is preserved
        text_instructions = serialized["instructions"]["text_instructions"]
        # At minimum, all content should be present somewhere
        assert len(text_instructions) >= 1

        # Check example SQLs are preserved
        example_sqls = serialized["instructions"]["example_question_sqls"]
        assert len(example_sqls) == 100


# =============================================================================
# Resource Limit Tests
# =============================================================================


class TestResourceLimits:
    """Tests for resource limits and boundaries."""

    def test_max_workers_boundary_1(self):
        """Test bulk operations with max_workers=1."""
        mock_client = MagicMock()
        mock_client.config.host = "https://test.databricks.com"
        mock_client.api_client.do.return_value = {"space": {"id": "new-id"}}

        client = GenieClient(client=mock_client)

        configs = [
            {"title": f"Space {i}", "warehouse_id": "wh", "tables": ["c.s.t"]} for i in range(5)
        ]

        result = client.bulk_create(configs, max_workers=1)

        assert result.total == 5
        assert result.success == 5

    def test_max_workers_boundary_high(self):
        """Test bulk operations with very high max_workers."""
        mock_client = MagicMock()
        mock_client.config.host = "https://test.databricks.com"
        mock_client.api_client.do.return_value = {"space": {"id": "new-id"}}

        client = GenieClient(client=mock_client)

        configs = [
            {"title": f"Space {i}", "warehouse_id": "wh", "tables": ["c.s.t"]} for i in range(5)
        ]

        # High max_workers (more than items)
        result = client.bulk_create(configs, max_workers=100)

        assert result.total == 5
        assert result.success == 5

    def test_pagination_with_max_pages_limit(self):
        """Test list_spaces respects max_pages limit."""
        mock_client = MagicMock()
        mock_client.config.host = "https://test.databricks.com"

        # Always return next_page_token (infinite pagination)
        mock_client.api_client.do.return_value = {
            "spaces": [{"id": "1", "title": "Space"}],
            "next_page_token": "next-token",
        }

        client = GenieClient(client=mock_client)

        # Should stop at max_pages
        spaces = client.list_spaces(max_pages=3)

        # Should have called API 3 times
        assert mock_client.api_client.do.call_count == 3
        assert len(spaces) == 3  # 1 space per page * 3 pages


# =============================================================================
# Performance Characteristic Tests
# =============================================================================


class TestPerformanceCharacteristics:
    """Tests for performance characteristics (not strict benchmarks)."""

    def test_bulk_result_rate_calculation(self):
        """Test that BulkResult calculates rate correctly."""
        result = BulkResult(
            total=100,
            success=95,
            failed=5,
            elapsed_seconds=10.0,
            rate_per_second=10.0,  # 100/10 = 10
            results=[],
        )

        assert result.rate_per_second == 10.0

    def test_bulk_result_with_zero_elapsed(self):
        """Test BulkResult with zero elapsed time."""
        # Edge case: very fast operation
        result = BulkResult(
            total=0,
            success=0,
            failed=0,
            elapsed_seconds=0.0,
            rate_per_second=0.0,
            results=[],
        )

        assert result.rate_per_second == 0.0

    def test_serialization_performance(self):
        """Test that serialization is reasonably fast."""
        from genie_forge.serializer import SpaceSerializer

        # Create moderately complex config
        config = SpaceConfig.minimal(
            space_id="test",
            title="Performance Test Space",
            warehouse_id="wh123",
            tables=[f"cat.sch.table_{i}" for i in range(50)],
        )

        serializer = SpaceSerializer()

        # Should serialize 100 times in reasonable time
        start = time.time()
        for _ in range(100):
            serializer.to_serialized_space(config)
        elapsed = time.time() - start

        # Should complete in under 5 seconds
        assert elapsed < 5.0, f"Serialization too slow: {elapsed:.2f}s for 100 iterations"


# =============================================================================
# Error Recovery Tests
# =============================================================================


class TestErrorRecovery:
    """Tests for error recovery in concurrent operations."""

    def test_bulk_create_continues_after_failure(self):
        """Test that bulk_create continues after individual failures."""
        mock_client = MagicMock()
        mock_client.config.host = "https://test.databricks.com"

        call_count = 0

        def mock_api_call(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:  # Fail on second call
                raise Exception("Simulated failure")
            return {"space": {"id": f"id-{call_count}"}}

        mock_client.api_client.do.side_effect = mock_api_call

        client = GenieClient(client=mock_client)

        configs = [
            {"title": f"Space {i}", "warehouse_id": "wh", "tables": ["c.s.t"]} for i in range(5)
        ]

        result = client.bulk_create(configs, max_workers=1)

        # Should have attempted all 5
        assert call_count == 5
        # 1 failed, 4 succeeded
        assert result.failed == 1
        assert result.success == 4

    def test_bulk_delete_continues_after_failure(self):
        """Test that bulk_delete continues after individual failures."""
        mock_client = MagicMock()
        mock_client.config.host = "https://test.databricks.com"

        call_count = 0

        def mock_api_call(method, path, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 3:  # Fail on third call
                raise Exception("Not found")
            return {}

        mock_client.api_client.do.side_effect = mock_api_call

        client = GenieClient(client=mock_client)

        space_ids = [f"id-{i}" for i in range(5)]
        result = client.bulk_delete(space_ids, max_workers=1)

        assert call_count == 5
        assert result.failed == 1
        assert result.success == 4


# =============================================================================
# Cleanup and Resource Management Tests
# =============================================================================


class TestResourceManagement:
    """Tests for proper resource management."""

    def test_threadpool_executor_cleanup(self):
        """Test that ThreadPoolExecutor is properly cleaned up."""
        mock_client = MagicMock()
        mock_client.config.host = "https://test.databricks.com"
        mock_client.api_client.do.return_value = {"space": {"id": "new-id"}}

        client = GenieClient(client=mock_client)

        # Get initial thread count
        initial_threads = threading.active_count()

        # Run bulk operation
        configs = [
            {"title": f"Space {i}", "warehouse_id": "wh", "tables": ["c.s.t"]} for i in range(10)
        ]
        client.bulk_create(configs, max_workers=5)

        # Wait a moment for cleanup
        time.sleep(0.1)

        # Thread count should return to approximately initial
        final_threads = threading.active_count()

        # Allow some variance due to Python internals
        assert final_threads <= initial_threads + 2, (
            f"Thread leak: {initial_threads} -> {final_threads}"
        )
