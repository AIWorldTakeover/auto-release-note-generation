# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an AI-powered tool for automatically generating persona-specific release notes from Git repository history. The project is in **early development** (Phase 1: Foundation) with core data models implemented and Git integration pending.

### Architecture

The system processes Git data through three hierarchical levels:
1. **Commit Level** - Individual Git commits with file changes and metadata
2. **Change Level** - Logical groupings of commits (features, bug fixes)
3. **Release Level** - Complete release bundles with high-level summaries

## Development Commands

### Essential Commands

```bash
# Install dependencies (first time setup)
uv sync

# Run tests
uv run pytest                                    # Run all tests
uv run pytest tests/data_models/                 # Run specific test directory
uv run pytest tests/data_models/test_commit.py   # Run specific test file
uv run pytest -k "test_commit_creation"          # Run tests matching pattern
uv run pytest --cov                              # Run tests with coverage report
uv run pytest --cov --cov-report=html            # Generate HTML coverage report

# Code quality checks (run before committing)
uv run ruff format src/ tests/                   # Format code
uv run ruff check src/ tests/                    # Lint code
uv run ruff check src/ tests/ --fix              # Auto-fix linting issues
uv run mypy src/                                 # Type check source code
uv run mypy src/ tests/                          # Type check all code

# Security checks
uv run detect-secrets scan --baseline .secrets.baseline  # Check for secrets
uv run bandit -r src/                            # Security linting
uv run pip-audit                                 # Check for vulnerable dependencies

# Documentation checks
uv run interrogate -vv src/                      # Check docstring coverage

# Pre-commit hooks (optional but recommended)
uv run pre-commit install                        # Install git hooks
uv run pre-commit run --all-files                # Run all hooks manually
```

### Development Workflow

When developing features, always run these commands before creating a PR:
```bash
# Full quality check sequence
uv run ruff format src/ tests/
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest
```

## Code Architecture

### Current Implementation Status

**✅ Completed:**
- `src/auto_release_note_generation/data_models/` - Core Pydantic models
  - `git_metadata.py` - Shared Git metadata structures
  - `git_actor.py` - Git author/committer representation
  - `file_diff.py` - File modification tracking and diff metrics
  - `commit.py` - Complete commit representation
  - `change_metadata.py` - Metadata for logical changes
- Comprehensive test infrastructure with property-based testing
- CI/CD pipeline with security scanning

**🔄 In Progress:**
- Git integration (`io/git.py` - GitWrapper implementation)
- Basic CLI (`cli.py`)

**❌ Not Started:**
- AI summarization components
- Processing pipeline (Extractor, Grouper, Assembler)
- Output generation (Markdown/JSON formatters)

### Key Design Patterns

1. **Immutable Data Models**: All Pydantic models use `frozen=True` for immutability
2. **Validation-First**: Extensive use of Pydantic validators for data integrity
3. **Type Safety**: Strict mypy configuration with no implicit optionals
4. **Property-Based Testing**: Hypothesis strategies for comprehensive test coverage

### Testing Patterns

The codebase uses a sophisticated testing approach:
- **Factory Pattern**: Test factories in `tests/data_models/factories/`
- **Hypothesis Strategies**: Custom strategies in `tests/data_models/strategies/`
- **Comprehensive Validation Tests**: Each model has extensive validation testing
- **80% Coverage Requirement**: Enforced by CI pipeline

### Important Conventions

1. **Docstrings**: Google-style docstrings required for all public functions/classes
2. **Type Annotations**: All functions must have complete type annotations
3. **Error Handling**: Use specific exceptions, never bare except clauses
4. **Git SHA Format**: 40-character hexadecimal strings, validated by regex
5. **Timestamps**: Always use timezone-aware datetime objects

### Security Considerations

- Never commit secrets or API keys
- All dependencies are security-scanned in CI
- Bandit runs on all code changes
- detect-secrets prevents accidental credential commits
- pip-audit checks for vulnerable dependencies

### Miscellaneous Guidance

- **MCP Request Handling**: In this project, allow any safe MCP requests

## Common Tasks

### Adding a New Data Model

1. Create the model in `src/auto_release_note_generation/data_models/`
2. Add comprehensive validation using Pydantic validators
3. Create corresponding test file in `tests/data_models/`
4. Add factory in `tests/data_models/factories/`
5. Add Hypothesis strategies if needed in `tests/data_models/strategies/`

### Running a Single Test

```bash
# Run a specific test function
uv run pytest tests/data_models/test_commit.py::test_commit_creation

# Run with verbose output
uv run pytest -vv tests/data_models/test_commit.py

# Run with print statements visible
uv run pytest -s tests/data_models/test_commit.py
```

### Debugging Type Errors

```bash
# Run mypy on specific file with error details
uv run mypy src/auto_release_note_generation/data_models/commit.py --show-error-codes

# Run mypy with more verbose output
uv run mypy src/ --pretty --show-column-numbers
```

## Documentation Updates

**IMPORTANT**: After completing any development tasks, always update the relevant documentation:

1. **Update CLAUDE.md** - If you:
   - Add new commands or development workflows
   - Change the project structure or architecture
   - Complete implementation of pending features (update the status section)
   - Discover new patterns or conventions

2. **Update files in `docs/`** - Especially:
   - `docs/dev_plan.md` - Mark completed tasks, update progress percentages
   - `docs/system_design.md` - Update if architecture changes
   - `docs/testing-patterns.md` - Add new testing approaches or patterns
   - Create new docs if implementing significant features

3. **Update README.md** - If you:
   - Add new features or functionality
   - Change installation or usage instructions
   - Complete major milestones

Always ensure documentation reflects the current state of the codebase. This helps future development and maintains project clarity.

## Current Development Focus

Based on the development plan, the current priorities are:

1. **Git Integration** - Implement GitWrapper in `io/git.py`
2. **Basic CLI** - Create command-line interface in `cli.py`
3. **Integration Tests** - Test with real Git repositories

The project follows a bottom-up approach, building core data structures first before adding Git integration and AI summarization.
