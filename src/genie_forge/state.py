"""
State management for Genie-Forge.

Provides Terraform-like state tracking:
- Tracks deployed spaces with their Databricks IDs
- Detects changes via config hash comparison
- Supports plan/apply/destroy workflow
- Persists state to .genie-forge.json

MVP scope: Basic state tracking with plan/apply/destroy.
Full product will add: Multiple storage backends, backup/rollback, semantic drift detection.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

from genie_forge.client import GenieClient
from genie_forge.models import (
    EnvironmentState,
    Plan,
    PlanAction,
    PlanItem,
    ProjectState,
    SpaceConfig,
    SpaceState,
    SpaceStatus,
)
from genie_forge.serializer import SpaceSerializer

logger = logging.getLogger(__name__)


class StateError(Exception):
    """Raised when state operations fail."""

    pass


class StateManager:
    """Manages state for Genie space deployments.

    The state file tracks:
    - Which spaces have been deployed
    - Their Databricks space IDs
    - Configuration hashes for change detection
    - Last applied timestamps

    Example:
        state = StateManager()

        # Load configs
        configs = parser.parse("conf/spaces/")

        # Plan changes
        plan = state.plan(configs, client, env="prod")
        print(plan.summary())

        # Apply changes
        state.apply(plan, client)
    """

    DEFAULT_STATE_FILE = ".genie-forge.json"

    def __init__(
        self,
        state_file: Optional[Union[str, Path]] = None,
        project_id: str = "genie-forge-project",
        project_name: Optional[str] = None,
    ):
        """Initialize the state manager.

        Args:
            state_file: Path to state file (default: .genie-forge.json)
            project_id: Project identifier
            project_name: Human-readable project name
        """
        self.state_file = Path(state_file or self.DEFAULT_STATE_FILE)
        self.project_id = project_id
        self.project_name = project_name
        self._state: Optional[ProjectState] = None
        self._serializer = SpaceSerializer()

    @property
    def state(self) -> ProjectState:
        """Get the current state, loading from file if needed."""
        if self._state is None:
            self._state = self._load_state()
        return self._state

    # =========================================================================
    # Plan Operations
    # =========================================================================

    def plan(
        self,
        configs: list[SpaceConfig],
        client: GenieClient,
        env: str = "dev",
    ) -> Plan:
        """Create a deployment plan.

        Compares desired state (configs) with current state to determine
        what needs to be created, updated, or is unchanged.

        Args:
            configs: List of SpaceConfig objects (desired state)
            client: GenieClient for the target environment
            env: Environment name

        Returns:
            Plan object with items to create/update
        """
        plan = Plan(environment=env)
        env_state = self._get_or_create_env_state(env, client.workspace_url)

        # Track which configs we've seen
        seen_logical_ids = set()

        for config in configs:
            logical_id = config.space_id
            seen_logical_ids.add(logical_id)

            current_state = env_state.spaces.get(logical_id)
            config_hash = config.config_hash()

            if current_state is None:
                # New space - needs to be created
                plan.items.append(
                    PlanItem(
                        logical_id=logical_id,
                        action=PlanAction.CREATE,
                        config=config,
                        changes=[f"Create new space '{config.title}'"],
                    )
                )
            elif current_state.applied_hash != config_hash:
                # Existing space with changes - needs update
                changes = self._detect_changes(config, current_state)
                plan.items.append(
                    PlanItem(
                        logical_id=logical_id,
                        action=PlanAction.UPDATE,
                        config=config,
                        current_state=current_state,
                        changes=changes,
                    )
                )
            else:
                # No changes
                plan.items.append(
                    PlanItem(
                        logical_id=logical_id,
                        action=PlanAction.NO_CHANGE,
                        config=config,
                        current_state=current_state,
                    )
                )

        return plan

    def _detect_changes(self, config: SpaceConfig, state: SpaceState) -> list[str]:
        """Detect what changed between config and state.

        Returns a list of human-readable change descriptions.
        """
        changes = []

        # Title change
        if config.title != state.title:
            changes.append(f"Title: '{state.title}' → '{config.title}'")

        # Config hash change (general catch-all)
        if config.config_hash() != state.applied_hash:
            changes.append("Configuration updated")

        if not changes:
            changes.append("Hash mismatch (content changed)")

        return changes

    # =========================================================================
    # Apply Operations
    # =========================================================================

    def apply(
        self,
        plan: Plan,
        client: GenieClient,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Apply a deployment plan.

        Args:
            plan: Plan to apply
            client: GenieClient for the target environment
            dry_run: If True, don't make actual changes

        Returns:
            Dict with apply results
        """
        results: dict[str, Any] = {
            "created": [],
            "updated": [],
            "failed": [],
            "unchanged": [],
            "dry_run": dry_run,
        }

        env_state = self._get_or_create_env_state(plan.environment, client.workspace_url)

        for item in plan.items:
            if item.action == PlanAction.NO_CHANGE:
                results["unchanged"].append(item.logical_id)
                continue

            if dry_run:
                if item.action == PlanAction.CREATE:
                    results["created"].append(item.logical_id)
                elif item.action == PlanAction.UPDATE:
                    results["updated"].append(item.logical_id)
                continue

            try:
                if item.action == PlanAction.CREATE:
                    self._apply_create(item, client, env_state)
                    results["created"].append(item.logical_id)
                elif item.action == PlanAction.UPDATE:
                    self._apply_update(item, client, env_state)
                    results["updated"].append(item.logical_id)
            except Exception as e:
                logger.error(f"Failed to apply {item.logical_id}: {e}")
                results["failed"].append(
                    {
                        "logical_id": item.logical_id,
                        "error": str(e),
                    }
                )
                # Update state with error
                if item.logical_id in env_state.spaces:
                    env_state.spaces[item.logical_id].error = str(e)

        # Save state
        if not dry_run:
            env_state.last_applied = datetime.now(timezone.utc)
            self._save_state()

        return results

    def _apply_create(
        self,
        item: PlanItem,
        client: GenieClient,
        env_state: EnvironmentState,
    ) -> None:
        """Apply a CREATE action."""
        if item.config is None:
            raise StateError(f"No config for create action: {item.logical_id}")

        config = item.config
        api_request = self._serializer.to_api_request(config)

        # Create the space
        space_id = client.create_space(
            title=api_request["title"],
            warehouse_id=api_request["warehouse_id"],
            tables=[t.identifier for t in config.data_sources.tables],
            parent_path=api_request.get("parent_path"),
            serialized_space=api_request["serialized_space"],
        )

        # Update state
        env_state.spaces[item.logical_id] = SpaceState(
            logical_id=item.logical_id,
            databricks_space_id=space_id,
            title=config.title,
            config_hash=config.config_hash(),
            applied_hash=config.config_hash(),
            status=SpaceStatus.APPLIED,
            last_applied=datetime.now(timezone.utc),
        )

        logger.info(f"Created space '{config.title}' with ID: {space_id}")

    def _apply_update(
        self,
        item: PlanItem,
        client: GenieClient,
        env_state: EnvironmentState,
    ) -> None:
        """Apply an UPDATE action."""
        if item.config is None:
            raise StateError(f"No config for update action: {item.logical_id}")
        if item.current_state is None or item.current_state.databricks_space_id is None:
            raise StateError(f"No existing space ID for update: {item.logical_id}")

        config = item.config
        space_id = item.current_state.databricks_space_id
        api_request = self._serializer.to_api_request(config)

        # Update the space
        client.update_space(
            space_id=space_id,
            title=api_request["title"],
            warehouse_id=api_request["warehouse_id"],
            serialized_space=api_request["serialized_space"],
        )

        # Update state
        env_state.spaces[item.logical_id].title = config.title
        env_state.spaces[item.logical_id].config_hash = config.config_hash()
        env_state.spaces[item.logical_id].applied_hash = config.config_hash()
        env_state.spaces[item.logical_id].status = SpaceStatus.APPLIED
        env_state.spaces[item.logical_id].last_applied = datetime.now(timezone.utc)
        env_state.spaces[item.logical_id].error = None

        logger.info(f"Updated space '{config.title}'")

    # =========================================================================
    # Destroy Operations
    # =========================================================================

    def destroy(
        self,
        target: str,
        client: GenieClient,
        env: str = "dev",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Destroy a deployed space.

        Args:
            target: Logical ID of the space to destroy
            client: GenieClient for the target environment
            env: Environment name
            dry_run: If True, don't make actual changes

        Returns:
            Dict with destroy results
        """
        env_state = self._get_or_create_env_state(env, client.workspace_url)

        if target not in env_state.spaces:
            return {
                "success": False,
                "error": f"Space '{target}' not found in state for environment '{env}'",
            }

        space_state = env_state.spaces[target]

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "target": target,
                "databricks_space_id": space_state.databricks_space_id,
            }

        # Delete the space
        if space_state.databricks_space_id:
            try:
                client.delete_space(space_state.databricks_space_id)
            except Exception as e:
                logger.error(f"Failed to delete space: {e}")
                return {
                    "success": False,
                    "error": str(e),
                }

        # Update state
        space_state.status = SpaceStatus.DESTROYED
        space_state.last_applied = datetime.now(timezone.utc)

        # Remove from active spaces
        del env_state.spaces[target]

        self._save_state()

        return {
            "success": True,
            "target": target,
            "databricks_space_id": space_state.databricks_space_id,
        }

    # =========================================================================
    # Import Operations
    # =========================================================================

    def import_space(
        self,
        config: SpaceConfig,
        databricks_space_id: str,
        env: str = "dev",
        workspace_url: Optional[str] = None,
    ) -> dict[str, Any]:
        """Import an existing Databricks space into state management.

        This adds a space that was created outside of genie-forge to the
        state file, allowing it to be managed going forward.

        Args:
            config: SpaceConfig generated from the API response
            databricks_space_id: The Databricks-assigned space ID
            env: Environment name to import into
            workspace_url: Optional workspace URL (for state tracking)

        Returns:
            Dict with import result
        """
        # Ensure environment exists
        if env not in self.state.environments:
            self.state.environments[env] = EnvironmentState(
                workspace_url=workspace_url or "",
                spaces={},
            )

        env_state = self.state.environments[env]

        # Update workspace URL if provided
        if workspace_url and not env_state.workspace_url:
            env_state.workspace_url = workspace_url

        # Create space state
        space_state = SpaceState(
            logical_id=config.space_id,
            databricks_space_id=databricks_space_id,
            title=config.title,
            config_hash=config.config_hash(),
            applied_hash=config.config_hash(),  # Treat as already applied
            status=SpaceStatus.APPLIED,
            last_applied=datetime.now(timezone.utc),
        )

        # Add to state
        env_state.spaces[config.space_id] = space_state
        env_state.last_applied = datetime.now(timezone.utc)

        self._save_state()

        logger.info(f"Imported space '{config.space_id}' to environment '{env}'")

        return {
            "success": True,
            "logical_id": config.space_id,
            "databricks_space_id": databricks_space_id,
            "environment": env,
        }

    # =========================================================================
    # Status Operations
    # =========================================================================

    def status(self, env: str = "dev") -> dict[str, Any]:
        """Get status of deployed spaces for an environment.

        Args:
            env: Environment name

        Returns:
            Dict with status information
        """
        if env not in self.state.environments:
            return {
                "environment": env,
                "total": 0,
                "spaces": [],
            }

        env_state = self.state.environments[env]

        spaces = []
        for logical_id, space_state in env_state.spaces.items():
            spaces.append(
                {
                    "logical_id": logical_id,
                    "title": space_state.title,
                    "databricks_space_id": space_state.databricks_space_id,
                    "status": space_state.status.value,
                    "last_applied": space_state.last_applied.isoformat()
                    if space_state.last_applied
                    else None,
                    "error": space_state.error,
                }
            )

        return {
            "environment": env,
            "workspace_url": env_state.workspace_url,
            "total": len(spaces),
            "last_applied": env_state.last_applied.isoformat() if env_state.last_applied else None,
            "spaces": spaces,
        }

    # =========================================================================
    # Drift Detection
    # =========================================================================

    def detect_drift(
        self,
        client: GenieClient,
        env: str = "dev",
    ) -> dict[str, Any]:
        """Detect drift between local state and actual Databricks workspace.

        Compares the state file with the actual Genie spaces in Databricks
        to find differences.

        Args:
            client: GenieClient for the target environment
            env: Environment name

        Returns:
            Dict with drift detection results:
            - drifted: Spaces that exist but differ from state
            - deleted: Spaces in state but deleted from workspace
            - unmanaged: Spaces in workspace but not in state (optional)
            - synced: Spaces that match state
        """
        results: dict[str, Any] = {
            "environment": env,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "drifted": [],
            "deleted": [],
            "synced": [],
            "total_checked": 0,
            "has_drift": False,
        }

        if env not in self.state.environments:
            results["error"] = f"Environment '{env}' not found in state"
            return results

        env_state = self.state.environments[env]
        results["workspace_url"] = env_state.workspace_url

        for logical_id, space_state in env_state.spaces.items():
            results["total_checked"] += 1

            if not space_state.databricks_space_id:
                # Space was never successfully created
                results["deleted"].append(
                    {
                        "logical_id": logical_id,
                        "title": space_state.title,
                        "reason": "No Databricks space ID in state",
                    }
                )
                continue

            # Fetch actual space from Databricks
            try:
                actual_space = client.get_space(
                    space_state.databricks_space_id,
                    include_serialized=True,
                )
            except Exception as e:
                # Space no longer exists in workspace
                results["deleted"].append(
                    {
                        "logical_id": logical_id,
                        "databricks_space_id": space_state.databricks_space_id,
                        "title": space_state.title,
                        "reason": f"Space not found in workspace: {e}",
                    }
                )
                results["has_drift"] = True
                continue

            # Compare actual vs state
            drift_details = self._compare_space(space_state, actual_space)

            if drift_details:
                results["drifted"].append(
                    {
                        "logical_id": logical_id,
                        "databricks_space_id": space_state.databricks_space_id,
                        "title": space_state.title,
                        "changes": drift_details,
                    }
                )
                results["has_drift"] = True
            else:
                results["synced"].append(
                    {
                        "logical_id": logical_id,
                        "databricks_space_id": space_state.databricks_space_id,
                        "title": space_state.title,
                    }
                )

        return results

    def _compare_space(self, state: SpaceState, actual: dict) -> list[str]:
        """Compare a space state with actual Databricks space.

        Args:
            state: SpaceState from local state file
            actual: Actual space dict from Databricks API

        Returns:
            List of differences (empty if no drift)
        """
        differences = []

        # Compare title
        actual_title = actual.get("title") or actual.get("space", {}).get("title", "")
        if state.title != actual_title:
            differences.append(f"Title changed: '{state.title}' → '{actual_title}'")

        # Compare warehouse_id if available
        actual_warehouse = actual.get("warehouse_id")
        if actual_warehouse:
            # We don't store warehouse_id in state, but we could check serialized_space
            pass

        # Check if space was modified (if we can detect it)
        # The API might return last_modified timestamp
        actual_modified = actual.get("last_modified") or actual.get("update_time")
        if actual_modified and state.last_applied:
            try:
                # Parse the timestamp
                if isinstance(actual_modified, str):
                    # Try parsing ISO format
                    from datetime import timezone

                    actual_dt = datetime.fromisoformat(actual_modified.replace("Z", "+00:00"))
                    state_dt = state.last_applied.replace(tzinfo=timezone.utc)
                    if actual_dt > state_dt:
                        differences.append(f"Modified after last apply: {actual_modified}")
            except Exception:
                pass  # Skip timestamp comparison if parsing fails

        return differences

    # =========================================================================
    # State File Operations
    # =========================================================================

    def _get_or_create_env_state(self, env: str, workspace_url: str) -> EnvironmentState:
        """Get or create environment state."""
        if env not in self.state.environments:
            self.state.environments[env] = EnvironmentState(workspace_url=workspace_url)
        return self.state.environments[env]

    def _load_state(self) -> ProjectState:
        """Load state from file."""
        if not self.state_file.exists():
            return ProjectState(
                project_id=self.project_id,
                project_name=self.project_name,
            )

        try:
            content = self.state_file.read_text(encoding="utf-8")
            data = json.loads(content)

            # Parse environments
            environments = {}
            for env_name, env_data in data.get("environments", {}).items():
                spaces = {}
                for space_id, space_data in env_data.get("spaces", {}).items():
                    spaces[space_id] = SpaceState(
                        logical_id=space_data["logical_id"],
                        databricks_space_id=space_data.get("databricks_space_id"),
                        title=space_data["title"],
                        config_hash=space_data["config_hash"],
                        applied_hash=space_data.get("applied_hash"),
                        status=SpaceStatus(space_data.get("status", "PENDING")),
                        last_applied=datetime.fromisoformat(space_data["last_applied"])
                        if space_data.get("last_applied")
                        else None,
                        error=space_data.get("error"),
                    )
                environments[env_name] = EnvironmentState(
                    workspace_url=env_data["workspace_url"],
                    last_applied=datetime.fromisoformat(env_data["last_applied"])
                    if env_data.get("last_applied")
                    else None,
                    spaces=spaces,
                )

            return ProjectState(
                version=data.get("version", "1.0"),
                project_id=data.get("project_id", self.project_id),
                project_name=data.get("project_name", self.project_name),
                created_at=datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else datetime.now(timezone.utc),
                environments=environments,
            )
        except Exception as e:
            logger.warning(f"Failed to load state file, starting fresh: {e}")
            return ProjectState(
                project_id=self.project_id,
                project_name=self.project_name,
            )

    def _save_state(self) -> None:
        """Save state to file."""
        if self._state is None:
            return

        data: dict[str, Any] = {
            "version": self._state.version,
            "project_id": self._state.project_id,
            "project_name": self._state.project_name,
            "created_at": self._state.created_at.isoformat(),
            "environments": {},
        }

        for env_name, env_state in self._state.environments.items():
            env_data: dict[str, Any] = {
                "workspace_url": env_state.workspace_url,
                "last_applied": env_state.last_applied.isoformat()
                if env_state.last_applied
                else None,
                "spaces": {},
            }
            for space_id, space_state in env_state.spaces.items():
                env_data["spaces"][space_id] = {
                    "logical_id": space_state.logical_id,
                    "databricks_space_id": space_state.databricks_space_id,
                    "title": space_state.title,
                    "config_hash": space_state.config_hash,
                    "applied_hash": space_state.applied_hash,
                    "status": space_state.status.value,
                    "last_applied": space_state.last_applied.isoformat()
                    if space_state.last_applied
                    else None,
                    "error": space_state.error,
                }
            data["environments"][env_name] = env_data

        self.state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        logger.debug(f"State saved to {self.state_file}")

    def refresh(self) -> None:
        """Refresh state from file (discard in-memory changes)."""
        self._state = None
