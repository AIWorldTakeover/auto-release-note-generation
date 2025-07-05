# Test Strategy Refactoring Plan

## Overview

This document outlines the plan to refactor test strategies from `tests/data_models/strategies/` to co-locate them with their corresponding data models, while also introducing a standardized test interface for all models.

## Goals

1. **Reduce coupling distance** between models and their test strategies
2. **Standardize test data generation** across all models
3. **Unify** hypothesis strategies, test factories, and mock patterns
4. **Improve maintainability** by keeping related code together
5. **Enhance discoverability** through consistent interfaces

## Part 1: Co-location Strategy

### Chosen Approach: Separate Files in Same Directory

- **Pattern**: `<module>.py` and `<module>_strategies.py` in the same directory
- **Location**: `src/auto_release_note_generation/data_models/`
- **Benefits**:
  - Clear separation of concerns
  - Easy to locate related files
  - Maintains production/test code separation
  - Minimal refactoring required

### Directory Structure After Refactoring

```
src/auto_release_note_generation/data_models/
├── __init__.py
├── commit.py
├── commit_strategies.py
├── shared.py
├── shared_strategies.py
├── utils.py
├── utils_strategies.py
├── validation_rules.py      # New: Shared validation constants
└── strategies/             # New: Convenient imports
    └── __init__.py
```

## Part 2: Standardized Test Interface

### Core Concept: Companion Strategy Pattern

**Key Design Decision**: Production models remain completely unchanged - no inheritance from test base classes, no test methods. All test functionality lives in companion strategy modules with a standardized interface.

This avoids mixing test and production code while still providing:
- Standardized test data generation interface
- Easy discovery of available strategies
- Type-safe strategy and factory methods
- Clear separation of concerns

```python
# Production models remain pure data models
class Commit(BaseModel):  # Only extends pydantic BaseModel
    # ... fields and business logic only ...

# Test functionality lives in companion modules
# commit_strategies.py provides standardized test interface
```

### Strategy Module Pattern

Each model gets a companion `<model>_strategies.py` module that provides both hypothesis strategies and factory methods. The key insight is that **production models remain unchanged** - all test functionality lives in the strategy modules.

```python
# data_models/base_strategies.py - Base classes for strategy modules
from hypothesis import strategies as st
from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class ModelStrategies(ABC, Generic[T]):
    """Standard interface for model test strategies.

    This lives in the test layer, not production code!
    """

    # Core strategies - REQUIRED
    @abstractmethod
    def valid(self) -> st.SearchStrategy[T]:
        """Generate valid instances."""
        pass

    @abstractmethod
    def invalid(self) -> st.SearchStrategy[dict[str, Any]]:
        """Generate invalid data that should fail validation."""
        pass

    # Semantic strategies - REQUIRED  
    @abstractmethod
    def minimal(self) -> st.SearchStrategy[T]:
        """Generate minimal valid instances (all optional fields None/empty)."""
        pass

    @abstractmethod
    def realistic(self) -> st.SearchStrategy[T]:
        """Generate realistic instances matching real-world patterns."""
        pass

    @abstractmethod
    def edge_cases(self) -> st.SearchStrategy[T]:
        """Generate valid edge cases (max lengths, special chars, etc)."""
        pass

    # Specialized strategies - OPTIONAL but recommended
    def with_constraint(self, **constraints) -> st.SearchStrategy[T]:
        """Generate instances matching specific constraints."""
        raise NotImplementedError

    def without_fields(self, *fields: str) -> st.SearchStrategy[dict[str, Any]]:
        """Generate data missing specified fields (for validation testing)."""
        raise NotImplementedError


class ModelFactory(ABC, Generic[T]):
    """Standard interface for deterministic test data creation."""

    @abstractmethod
    def create(self, **overrides) -> T:
        """Create instance with defaults and overrides."""
        pass

    @abstractmethod
    def create_minimal(self) -> T:
        """Create minimal valid instance."""
        pass

    @abstractmethod
    def create_realistic(self) -> T:
        """Create realistic instance."""
        pass

    def create_batch(self, count: int, **shared_attrs) -> list[T]:
        """Create multiple related instances."""
        return [self.create(**shared_attrs) for _ in range(count)]


# Each strategy module exports these standardized objects
class BaseStrategyModule:
    """Base class for strategy modules."""

    def __init__(self, model_class: type[T]):
        self.model_class = model_class
        self.strategies = self._create_strategies()
        self.factory = self._create_factory()

    @abstractmethod
    def _create_strategies(self) -> ModelStrategies[T]:
        """Create the strategies instance."""
        pass

    @abstractmethod
    def _create_factory(self) -> ModelFactory[T]:
        """Create the factory instance."""
        pass
```

### Strategy Registry Pattern

To make strategies easily discoverable without modifying production code:

```python
# data_models/strategies/__init__.py
from typing import TypeVar, Type
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)

class StrategyRegistry:
    """Registry for model strategies - keeps production code clean."""

    def __init__(self):
        self._strategies = {}
        self._factories = {}

    def register(self, model_class: Type[T], module: BaseStrategyModule):
        """Register strategies and factory for a model."""
        self._strategies[model_class] = module.strategies
        self._factories[model_class] = module.factory

    def get_strategies(self, model_class: Type[T]) -> ModelStrategies[T]:
        """Get strategies for a model."""
        if model_class not in self._strategies:
            raise ValueError(f"No strategies registered for {model_class.__name__}")
        return self._strategies[model_class]

    def get_factory(self, model_class: Type[T]) -> ModelFactory[T]:
        """Get factory for a model."""
        if model_class not in self._factories:
            raise ValueError(f"No factory registered for {model_class.__name__}")
        return self._factories[model_class]

# Global registry instance
registry = StrategyRegistry()

# Convenience functions
def strategies_for(model_class: Type[T]) -> ModelStrategies[T]:
    """Get strategies for a model class."""
    return registry.get_strategies(model_class)

def factory_for(model_class: Type[T]) -> ModelFactory[T]:
    """Get factory for a model class."""
    return registry.get_factory(model_class)

# Auto-registration when importing
from ..commit_strategies import commit_module
from ..shared_strategies import git_actor_module, git_metadata_module

registry.register(Commit, commit_module)
registry.register(GitActor, git_actor_module)
registry.register(GitMetadata, git_metadata_module)
```

## Implementation Example

### Model Definition (commit.py)

```python
from pydantic import BaseModel, Field
# ... other imports ...

class Commit(BaseModel):
    """Represents a comprehensive Git commit with metadata, changes, and AI summary.

    NOTE: This model remains UNCHANGED - no test methods or dependencies!
    """

    # ... existing model fields remain exactly as they are ...
    metadata: GitMetadata = Field(...)
    summary: str = Field(...)
    message: str = Field(...)
    branches: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    diff: Diff = Field(...)
    ai_summary: str | None = Field(default=None)

    # ... existing methods remain unchanged ...
```

### Strategy Implementation (commit_strategies.py)

```python
from hypothesis import strategies as st
from .base_strategies import ModelStrategies, ModelFactory, BaseStrategyModule
from .commit import Commit
from .strategies import strategies_for, factory_for  # For accessing other model strategies

# Mark module as not for pytest collection
__test__ = False

class CommitStrategies(ModelStrategies[Commit]):
    def valid(self) -> st.SearchStrategy[Commit]:
        return st.builds(
            Commit,
            metadata=strategies_for(GitMetadata).valid(),
            summary=self._valid_summary(),
            message=self._valid_message(),
            branches=self._valid_branches(),
            tags=self._valid_tags(),
            diff=strategies_for(Diff).valid(),
            ai_summary=st.one_of(st.none(), self._valid_ai_summary()),
        )

    def invalid(self) -> st.SearchStrategy[dict]:
        return st.one_of(
            # Missing required fields
            self.without_fields("metadata"),
            self.without_fields("summary"),
            # Invalid field values
            st.fixed_dictionaries({
                "metadata": strategies_for(GitMetadata).valid(),
                "summary": st.just(""),  # Empty summary
                "message": st.just("Valid message"),
                "diff": strategies_for(Diff).valid(),
            })
        )

    def minimal(self) -> st.SearchStrategy[Commit]:
        return st.builds(
            Commit,
            metadata=strategies_for(GitMetadata).minimal(),
            summary=st.just("Initial commit"),
            message=st.just("Initial commit"),
            branches=st.just([]),
            tags=st.just([]),
            diff=strategies_for(Diff).minimal(),
            ai_summary=st.none(),
        )

    def realistic(self) -> st.SearchStrategy[Commit]:
        return st.one_of(
            self._conventional_commit(),
            self._merge_commit(),
            self._feature_commit(),
            self._bugfix_commit(),
        )

    # Specialized commit strategies
    def merge_commit(self) -> st.SearchStrategy[Commit]:
        """Generate merge commits with 2+ parents."""
        return st.builds(
            Commit,
            metadata=strategies_for(GitMetadata).merge_commit(),
            summary=self._merge_summary(),
            message=self._merge_message(),
            branches=st.lists(self._branch_name(), min_size=2, max_size=3),
            tags=self._valid_tags(),
            diff=strategies_for(Diff).valid(),
            ai_summary=st.none(),
        )

    def root_commit(self) -> st.SearchStrategy[Commit]:
        """Generate root commits with no parents."""
        return st.builds(
            Commit,
            metadata=strategies_for(GitMetadata).root_commit(),
            summary=st.sampled_from(["Initial commit", "Initialize repository"]),
            message=self._initial_message(),
            branches=st.just(["main"]),
            tags=st.just([]),
            diff=strategies_for(Diff).valid(),
            ai_summary=st.none(),
        )

    # Helper methods
    def _valid_summary(self) -> st.SearchStrategy[str]:
        return non_empty_text(min_size=1, max_size=100)

    def _conventional_commit(self) -> st.SearchStrategy[Commit]:
        # Implementation for conventional commit format
        pass

class CommitFactory(ModelFactory[Commit]):
    def create(self, **overrides) -> Commit:
        defaults = {
            "metadata": factory_for(GitMetadata).create(),
            "summary": "Update implementation",
            "message": "Update implementation\n\nDetailed changes...",
            "branches": ["main"],
            "tags": [],
            "diff": factory_for(Diff).create(),
            "ai_summary": None,
        }
        defaults.update(overrides)
        return Commit(**defaults)

    def create_minimal(self) -> Commit:
        return self.create(
            metadata=factory_for(GitMetadata).create_minimal(),
            summary="Fix",
            message="Fix",
            branches=[],
            tags=[],
            diff=factory_for(Diff).create_minimal(),
        )

    def create_realistic(self) -> Commit:
        return self.create(
            summary="feat: Add user authentication system",
            message="""feat: Add user authentication system

- Implement JWT-based authentication
- Add user registration and login endpoints
- Include password hashing with bcrypt
- Add authentication middleware

Closes #123""",
            branches=["feature/auth", "main"],
            tags=["v1.2.0"],
        )

# Module registration
class CommitStrategyModule(BaseStrategyModule):
    def _create_strategies(self) -> ModelStrategies[Commit]:
        return CommitStrategies()

    def _create_factory(self) -> ModelFactory[Commit]:
        return CommitFactory()

# Export the module instance
commit_module = CommitStrategyModule(Commit)
```

## Detailed Refactoring Checklist

### Pre-Refactoring
- [ ] Document current import paths used by tests
- [ ] Identify all test files using strategies
- [ ] Check for circular import risks
- [ ] Verify no production code imports strategies
- [ ] Ensure all tests pass before starting
- [ ] Create a feature branch for the refactor
- [ ] Run coverage report to baseline

### Phase 1: Infrastructure Setup
- [ ] Create `base_strategies.py` with `ModelStrategies` and `ModelFactory` interfaces
- [ ] Create `StrategyRegistry` class for model-strategy mapping
- [ ] Create `validation_rules.py` for shared constants
- [ ] Add `__test__ = False` convention to pytest config
- [ ] Create `data_models/strategies/__init__.py` with registry and convenience functions

### Phase 2: Model Migration (Per Model)
For each model (utils, shared, commit):
- [ ] Create `<model>_strategies.py` file (models remain unchanged)
- [ ] Implement `ModelStrategies` subclass
- [ ] Implement `ModelFactory` subclass
- [ ] Create `BaseStrategyModule` subclass for registration
- [ ] Copy existing strategies and adapt to new interface
- [ ] Add `__test__ = False` to strategy module
- [ ] Register module in `strategies/__init__.py`
- [ ] Update test imports to use `strategies_for()` and `factory_for()`
- [ ] Run tests for that model

### Phase 3: Test Updates
- [ ] Update all test files to use new interface
- [ ] Replace old strategy imports with model methods
- [ ] Update factory usage to new interface
- [ ] Verify hypothesis tests still pass
- [ ] Check coverage hasn't decreased

### Phase 4: Cleanup
- [ ] Delete old `tests/data_models/strategies/` directory
- [ ] Remove old factory classes
- [ ] Update documentation
- [ ] Run full test suite
- [ ] Check for any remaining old imports

### Phase 5: Validation
- [ ] All tests pass
- [ ] No circular imports
- [ ] Coverage maintained or improved
- [ ] No test code in production builds
- [ ] Linters and formatters pass

## Usage Examples

### Property-Based Testing

```python
from hypothesis import given
from auto_release_note_generation.data_models import Commit
from auto_release_note_generation.data_models.strategies import strategies_for

@given(strategies_for(Commit).valid())
def test_commit_properties(commit: Commit):
    assert commit.summary.strip() == commit.summary
    assert commit.get_short_sha() == commit.metadata.sha[:8]

@given(strategies_for(Commit).invalid())
def test_commit_validation(invalid_data: dict):
    with pytest.raises(ValidationError):
        Commit(**invalid_data)

@given(strategies_for(Commit).realistic())
def test_realistic_commits(commit: Commit):
    # Test with realistic data patterns
    assert len(commit.summary) <= 100
    assert commit.message.startswith(commit.summary)
```

### Deterministic Testing

```python
from auto_release_note_generation.data_models import Commit
from auto_release_note_generation.data_models.strategies import factory_for

def test_specific_scenario():
    # Create specific test data
    commit = factory_for(Commit).create(
        summary="Fix critical security issue",
        branches=["hotfix/security", "main"],
        tags=["v2.1.1"],
    )

    assert "security" in commit.summary.lower()
    assert "hotfix/security" in commit.branches

def test_batch_processing():
    # Create multiple related commits
    commits = factory_for(Commit).create_batch(
        5,
        branches=["feature/batch-test"],
    )

    assert all(c.branches == ["feature/batch-test"] for c in commits)
```

### Edge Case Testing

```python
@given(strategies_for(Commit).edge_cases())
def test_edge_cases(commit: Commit):
    # Automatically tests with max lengths, special chars, etc.
    assert commit.model_validate(commit.model_dump())

@given(strategies_for(Commit).with_unicode())
def test_unicode_handling(commit: Commit):
    # Ensure unicode is handled properly
    json_str = commit.model_dump_json()
    restored = Commit.model_validate_json(json_str)
    assert restored == commit
```

## Benefits

1. **Unified Interface**: All models have consistent test data methods
2. **Discoverable**: IDEs can autocomplete available strategies
3. **Type-Safe**: Full type hints for all methods
4. **Composable**: Models can use other models' strategies
5. **Flexible**: Combines property-based and example-based testing
6. **Maintainable**: Related code is co-located
7. **Testable**: Can meta-test that all models implement interface

## Migration Path

1. Implement base classes and interfaces
2. Migrate one simple model (e.g., `GitActor`) as proof of concept
3. Validate approach with team
4. Migrate remaining models incrementally
5. Update documentation and examples
6. Remove old structure

## Success Criteria

- All models have companion strategy modules with standard interface
- Tests pass with same or better coverage
- No production imports of test code
- Production models remain pure (no test methods or inheritance)
- Reduced maintenance when updating models
- Team finds new structure more intuitive

## Alternative Approaches Considered

### Why Not TestableModel Base Class?
Initially considered having models inherit from a `TestableModel` base class that would provide `strategies()` and `factory()` methods. This was rejected because:
- Mixes test and production code
- Requires production code to depend on test frameworks (hypothesis)
- Violates separation of concerns
- Makes it harder to use models in production without test dependencies

### Why Not Just Convention?
Could rely purely on convention (each model has a `<model>_strategies.py` file) without any registry or standard interface. This was rejected because:
- No enforcement of standard interface
- Harder to discover available strategies
- No type safety
- Easy to forget to implement required methods

### Final Design Benefits
The registry pattern with companion modules provides:
- Clean separation of production and test code
- Standardized, discoverable interface
- Type safety through abstract base classes
- Flexibility to add new standard methods
- Easy migration path from current structure
