# Developer Quick Reference

## 🚀 First Time Setup

```bash
# 1. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Clone and setup
git clone <repo-url>
cd auto-release-note-generation
uv sync --locked --extra dev
uv run pre-commit install --install-hooks

# 3. Verify setup
make check
```

## 📋 Daily Development Commands

### Using Make (Recommended)
```bash
make help         # Show all commands
make format       # Auto-format code
make check        # Run all checks (lint + type-check + test)
make test         # Run tests
make coverage     # Generate coverage report
make all          # Full workflow (format + check + coverage)
```

### Using uv directly
```bash
uv run pytest                    # Run tests
uv run pytest -xvs              # Debug mode (stop on first failure, verbose)
uv run ruff format src/ tests/   # Format code
uv run mypy src/                # Type check
```

## 🧪 Testing Across Python Versions

### Quick test all versions
```bash
make test-all
# OR
./scripts/test-all-pythons.sh
```

### Test specific version
```bash
uv run --python 3.11 pytest
```

### Using tox
```bash
# First time only
uv tool install tox --with tox-uv

# Run all tests
uvx tox -p auto

# Run specific environment
uvx tox -e py311-unit
```

## 🔧 Common Tasks

### Adding a new dependency
```bash
# Add to pyproject.toml dependencies
# Then sync:
uv sync --locked
```

### Updating dependencies
```bash
uv lock --upgrade-package <package-name>
uv sync
```

### Running specific tests
```bash
# Run tests matching a pattern
uv run pytest -k "test_git_metadata"

# Run tests in a specific file
uv run pytest tests/data_models/test_git_metadata.py

# Run with coverage for specific module
uv run pytest --cov=auto_release_note_generation.data_models tests/data_models/
```

### Debugging test failures
```bash
# Verbose output with print statements
uv run pytest -xvs

# Drop into debugger on failure
uv run pytest --pdb

# Show local variables on failure
uv run pytest -l
```

## 📝 Pre-commit Hooks

### Run manually
```bash
uv run pre-commit run --all-files
```

### Skip hooks temporarily
```bash
git commit --no-verify -m "WIP: debugging"
```

### Update hooks
```bash
uv run pre-commit autoupdate
```

## 🐛 Troubleshooting

### Reset environment
```bash
rm -rf .venv
uv sync --locked --extra dev
```

### Clear caches
```bash
make clean
```

### Check Python versions
```bash
uv python list
```

### Validate CI config
```bash
python scripts/check-ci-config.py
```

## 📊 Code Quality

### Check coverage
```bash
make coverage
open htmlcov/index.html
```

### Check docstring coverage
```bash
uv run interrogate src/ -v
```

### Security scan
```bash
uv run detect-secrets scan
```

## 🔑 Key Files

- `pyproject.toml` - Project configuration and dependencies
- `tox.ini` - Multi-version test configuration
- `.pre-commit-config.yaml` - Git hook configuration
- `Makefile` - Common command shortcuts
- `.github/workflows/test.yml` - CI/CD pipeline

## 💡 Tips

1. **Always use `--locked` with uv sync** to ensure reproducible builds
2. **Run `make check` before pushing** to catch issues early
3. **Use `make all` for complete code quality workflow** (format, check, coverage)
4. **Use `uvx` for tools** instead of installing globally
5. **Python 3.11 is the default** for linting and type checking
6. **Tests run in parallel** by default with pytest-xdist

## 🆘 Getting Help

- Run `make help` for available commands
- Check `README.md` for detailed documentation
- Look at existing tests for patterns
- Use `git blame` to find context for code
