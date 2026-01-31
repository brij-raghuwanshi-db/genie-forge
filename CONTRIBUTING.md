# Contributing to Genie-Forge

Thank you for your interest in contributing to Genie-Forge!

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/brij-raghuwanshi-db/genie-forge.git
cd genie-forge

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with development dependencies
make dev
# Or: pip install -e ".[dev]"
```

## Development Workflow

### Running Checks Locally

Before submitting a PR, run the same checks that CI runs:

```bash
# Run all checks (lint, type-check, test)
make all

# Or run individually:
make lint        # Ruff linting and format check
make type-check  # MyPy type checking
make test        # Unit tests
make coverage    # Tests with coverage report
```

### Formatting Code

```bash
# Auto-format code
make fmt
```

### Available Make Commands

```bash
make help  # Show all available commands
```

| Command | Description |
|---------|-------------|
| `make install` | Install package in editable mode |
| `make dev` | Install with dev dependencies |
| `make lint` | Run linting checks |
| `make fmt` | Auto-format code |
| `make type-check` | Run MyPy type checking |
| `make test` | Run unit tests |
| `make test-integration` | Run integration tests (requires GENIE_PROFILE) |
| `make coverage` | Run tests with coverage |
| `make build` | Build distribution packages |
| `make clean` | Clean build artifacts |
| `make all` | Run lint + type-check + test |

## Pull Request Process

1. **Fork** the repository and create a feature branch
2. **Make changes** and ensure all checks pass locally (`make all`)
3. **Write tests** for new functionality
4. **Update documentation** if needed
5. **Submit PR** with a clear description of changes

### PR Requirements

- All CI checks must pass
- Code must be formatted with Ruff
- No MyPy type errors
- Tests must pass on all Python versions (3.9-3.12)
- New code should have tests

## Code Style

- We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting
- Line length: 100 characters
- Type hints are required (enforced by MyPy)
- Follow existing code patterns

## Testing

### Test Structure

```
tests/
├── conftest.py      # Shared fixtures
├── fixtures/        # Test data files
├── unit/            # Unit tests (no API calls)
└── integration/     # Integration tests (requires Databricks)
```

### Test Markers

```python
@pytest.mark.unit        # Fast tests, no external dependencies
@pytest.mark.integration # Tests requiring real Databricks API
```

### Running Unit Tests

```bash
# Run all unit tests
make test

# Run a specific test file
pytest tests/unit/test_models.py -v

# Run tests matching a pattern
pytest -k "test_validate" -v

# Run with verbose output
pytest tests/unit -v --tb=long
```

### Running Integration Tests

Integration tests require a Databricks workspace with Genie/AI-BI access.

```bash
# Set the profile from ~/.databrickscfg
export GENIE_PROFILE=your-profile-name

# Optional: Set catalog/schema for demo table tests
export GENIE_CATALOG=your_catalog
export GENIE_SCHEMA=your_schema
export GENIE_WAREHOUSE_ID=your_warehouse_id

# Run integration tests
make test-integration

# Or directly with pytest
pytest tests/integration -v -m integration
```

**Required Environment Variables:**
- `GENIE_PROFILE`: Profile name from `~/.databrickscfg` with Genie access

**Optional Environment Variables:**
- `GENIE_CATALOG`: Unity Catalog name (default: `main`)
- `GENIE_SCHEMA`: Schema name (default: `default`)
- `GENIE_WAREHOUSE_ID`: SQL Warehouse ID for demo table tests

## Questions?

Open an issue or reach out to the maintainers.
