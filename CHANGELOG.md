# Changelog

All notable changes to Genie-Forge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.0] - 2026-01-28

### Added

- **Project Initialization** (`genie-forge init`): Scaffold a new Genie-Forge project
  - Creates directory structure (`conf/spaces/`, `conf/variables/`)
  - Generates example configuration files
  - Creates initial state file (`.genie-forge.json`)
  - Updates `.gitignore` automatically
  - Supports `--minimal` for bare-bones setup

- **User Identity Command** (`genie-forge whoami`): Display current authenticated user
  - Shows user name, display name, user ID
  - Shows workspace URL
  - Shows active profile
  - Supports `--json` output for scripting

- **Demo Status Command** (`genie-forge demo-status`): Check demo objects existence
  - Verifies if demo tables and functions exist
  - Shows detailed status for each object
  - Helpful before running setup-demo

- **Space Operations Group** (`space-*` commands):
  - `space-list`: List all spaces with pagination progress (alias: `list-spaces`)
  - `space-get`: Display full space details with spinner (alias: `show`)
  - `space-find`: Search by pattern with pagination (alias for `find`)
  - `space-create`: Create spaces from CLI flags OR YAML/JSON file
    - Three input methods: CLI flags, `--from-file`, or hybrid
    - Supports `--set key=value` overrides
    - `--dry-run` to preview
    - `--save-config` to export config
    - `--env` to add to state tracking
  - `space-clone`: Clone existing spaces
    - Clone to same workspace (`--to-workspace`)
    - Clone to local file (`--to-file`)
    - Cross-workspace cloning with `--target-profile`
  - `space-export`: Bulk export spaces to YAML/JSON files
    - Export all or filter by `--pattern`
    - Export specific spaces by `--space-id`
    - Exclude patterns with `--exclude`
    - Two-phase progress (Fetching + Writing)
  - `space-delete`: Delete spaces (alias for `destroy`)

- **State Operations Group** (`state-*` commands):
  - `state-list`: Simple list of tracked spaces
  - `state-show`: Detailed view of state file
  - `state-pull`: Refresh local state from workspace
    - Verifies tracked spaces still exist
    - Updates titles if changed
    - Reports missing/deleted spaces
    - `--verify-only` to check without updating
  - `state-remove`: Remove space from state (keeps in Databricks)
  - `state-import`: Import existing spaces (alias for `import`)

- **Progress Indicators**: Rich progress bars and spinners throughout CLI
  - Progress bars for bulk operations (`apply`, `destroy`, `validate`)
  - Pagination progress for listing/fetching operations
  - Spinners for single-item operations (`whoami`, `space-get`, `space-create`)
  - Operation counters with summary reports (Created/Updated/Failed)

### Changed

- **Plan Output Enhanced**: Better operation summary before plan details
  - Shows counts by operation type (Create/Update/Destroy/Unchanged)
  - Clear visual hierarchy

- **Apply Output Enhanced**: Progress bar during deployment
  - Real-time progress indicator
  - Summary report with counts

- **Destroy Output Enhanced**: Progress bar during deletion
  - Real-time progress indicator
  - Summary report with counts

- **Validate Output Enhanced**: Progress bar and summary
  - Shows passed/failed counts
  - Cleaner output format

- **Find Command Enhanced**: Pagination progress when searching workspace
  - Shows pages fetched
  - Shows total spaces scanned

- **CLI Command Order**: Commands organized by user journey
  - Project Setup: `init`, `profiles`, `whoami`
  - Demo Management: `setup-demo`, `demo-status`, `cleanup-demo`
  - Configuration: `validate`
  - Deployment: `plan`, `apply`, `status`, `drift`
  - Space Operations: `space-*` commands
  - State Operations: `state-*` commands
  - Legacy/Aliases: `find`, `list-spaces`, `show`, `import`
  - Cleanup: `destroy`

### Internal

- Added shared progress utilities in `cli/common.py`:
  - `create_progress_bar()` for bulk operations
  - `create_pagination_progress()` for unknown totals
  - `with_spinner()` context manager for single operations
  - `OperationCounter` class for tracking results

## [0.2.0] - 2026-01-27

### Added

- **Drift Detection Command** ([#1](https://github.com/brij-raghuwanshi-db/genie-forge/issues/1)): New `genie-forge drift` command to detect differences between local state and actual Databricks workspace
  - Fetches actual space configuration from Databricks API
  - Compares with local state file
  - Reports drifted, deleted, and synced spaces
  - Rich formatted output with actionable resolution suggestions
  - Exit code 1 when drift detected (useful for CI/CD)
  - Usage: `genie-forge drift --env prod --profile PROD_PROFILE`

- **Dry-Run Mode** ([#3](https://github.com/brij-raghuwanshi-db/genie-forge/issues/3)): Added `--dry-run` flag to all mutating commands
  - Preview changes without executing them
  - Available on: `apply`, `destroy`, `import`

- **Import Command** ([#4](https://github.com/brij-raghuwanshi-db/genie-forge/issues/4)): New `genie-forge import` command to bring existing Genie spaces under management
  - Import single space by Databricks ID: `genie-forge import <space_id> --env prod --as my_space`
  - Import multiple spaces by pattern: `genie-forge import --pattern "Sales*" --env prod`
  - Generates YAML config files from API response
  - Adds imported spaces to state file for tracking
  - Supports `--dry-run` to preview imports
  - Supports `--force` to overwrite existing configs

### Changed

- **CLI Refactored** ([#2](https://github.com/brij-raghuwanshi-db/genie-forge/issues/2)): Split monolithic `cli.py` (2000+ lines) into organized `cli/` package
  - `cli/spaces.py` - plan, apply, destroy, status, drift commands
  - `cli/validate.py` - validate command
  - `cli/find.py` - find command
  - `cli/import_cmd.py` - import command
  - `cli/demo.py` - setup-demo, cleanup-demo commands
  - `cli/profiles.py` - profiles command
  - No functionality changes, improved maintainability

- **Retry Logic**: All API calls now automatically retry on transient failures
  - Exponential backoff (1s → 2s → 4s) between retries
  - Retries on connection errors and timeouts
  - Maximum 3 retry attempts by default

- **Rate Limiting**: Bulk operations now support optional rate limiting
  - `bulk_create(configs, rate_limit=10.0)` - max 10 creates/second
  - `bulk_delete(space_ids, rate_limit=5.0)` - max 5 deletes/second

- **API Pagination**: `list_spaces()` now automatically handles pagination
  - Fetches all pages of results automatically
  - Configurable `max_pages` parameter (default: 100)

### Fixed

- Tables now sorted by identifier when creating spaces (Genie API requirement)
- `serialized_space` properly JSON-encoded for API requests
- Empty environment variables now fall back to defaults in CI

### Internal

- Comprehensive test suite with 147+ unit tests
- Integration tests running in GitHub Actions CI
- Removed duplicate `conf/setup/` scripts (use CLI instead)

## [0.1.0] - 2026-01-26

### Added
- Initial MVP release of Genie-Forge
- YAML/JSON configuration with variable substitution (`${variable}`)
- Terraform-like plan/apply/destroy workflow
- State tracking via `.genie-forge.json`
- 9 CLI commands in user journey order:
  - `profiles`: List available Databricks profiles
  - `setup-demo`: Create demo tables for examples
  - `cleanup-demo`: Remove demo tables
  - `validate`: Validate config file syntax and schema
  - `plan`: Show what will be created/updated
  - `apply`: Deploy changes
  - `status`: Show deployment status
  - `find`: Find spaces by name in workspace
  - `destroy`: Delete spaces
- Built-in demo table creation and cleanup
- Support for all Genie space features:
  - Tables with column descriptions
  - Custom instructions
  - Sample questions
  - Table joins (including self-joins)
  - SQL functions
- Self-join support for hierarchical data (e.g., employee → manager)
- Parallel bulk operations (37 spaces/second verified)
- Authentication via:
  - Databricks CLI profiles (`~/.databrickscfg`)
  - Environment variables (`DATABRICKS_HOST`, `DATABRICKS_TOKEN`)
- Multi-environment support (dev/staging/prod)
- Databricks notebooks for interactive learning
- Comprehensive documentation and README

### Security
- No credentials stored in state file
- Profile-based authentication recommended
- Support for environment variable authentication for CI/CD

---

## Version History Summary

| Version | Date | Highlights |
|---------|------|------------|
| 0.3.0 | 2026-01-28 | New space-*/state-* commands, progress indicators, init/whoami |
| 0.2.0 | 2026-01-27 | Drift detection, import command, CLI refactor |
| 0.1.0 | 2026-01-26 | Initial MVP release |
