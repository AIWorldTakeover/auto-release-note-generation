# Testing Patterns Guide - Modular Strategy System

This guide explains how to add new data models and tests using our modular strategy system. The patterns ensure consistency, maintainability, and comprehensive test coverage.

## Table of Contents

- [Overview](#overview)
- [Modular Strategy Architecture](#modular-strategy-architecture)
- [Adding a New Data Model](#adding-a-new-data-model)
- [Strategy Development Guidelines](#strategy-development-guidelines)
- [Testing Categories](#testing-categories)
- [Best Practices](#best-practices)
- [Examples](#examples)

## Overview

Our testing infrastructure uses a modular strategy system that:
- **Organizes strategies by domain** (actors, commits, files, metadata)
- **Generates model instances** not just raw data
- **Provides composable building blocks** for complex test scenarios
- **Ensures type safety** with proper return types

### Key Principles

1. **Domain-Driven Organization** - Strategies are grouped by their domain
2. **Model-Aware Generation** - Strategies return actual model instances when appropriate
3. **Composability** - Simple strategies combine to create complex scenarios
4. **Reusability** - Common patterns are extracted into base utilities

## Modular Strategy Architecture

```
tests/data_models/
├── strategies/
│   ├── __init__.py         # Public API exports
│   ├── base.py            # Common utilities and helpers
│   ├── utils.py           # GitSHA and GPG signature strategies
│   ├── actors.py          # GitActor strategies
│   ├── metadata.py        # GitMetadata and ChangeMetadata strategies
│   ├── files.py           # FileModification and Diff strategies
│   ├── commits.py         # Commit strategies
│   └── README.md          # Strategy documentation
├── test_*.py              # Test files using strategies
└── conftest.py            # Shared fixtures and configuration
```

## Adding a New Data Model

Follow this step-by-step process when adding a new data model:

### Step 1: Create the Data Model

First, create your Pydantic model in the appropriate module:

```python
# src/auto_release_note_generation/data_models/your_model.py
from pydantic import BaseModel, Field, field_validator

class YourModel(BaseModel):
    """Your model description."""

    name: str = Field(..., min_length=1, max_length=255)
    value: int = Field(..., ge=0)
    optional_field: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        return v.strip()
```

### Step 2: Create Domain-Specific Strategies

Create a new strategy module for your domain:

```python
# tests/data_models/strategies/your_domain.py
"""Hypothesis strategies for YourModel data generation."""

from hypothesis import strategies as st
from auto_release_note_generation.data_models.your_model import YourModel
from .base import non_empty_text, valid_length_filter

# Basic field strategies
def valid_your_model_name():
    """Generate valid names for YourModel."""
    return st.text(
        min_size=1,
        max_size=255,
        alphabet=st.characters(blacklist_categories=("Cc", "Cs"))
    ).filter(valid_length_filter)

def valid_your_model_value():
    """Generate valid values for YourModel."""
    return st.integers(min_value=0, max_value=1000000)

# Invalid data strategies for testing validation
def invalid_your_model_data():
    """Generate invalid data to test validation."""
    return st.one_of(
        st.builds(dict, name=st.just(""), value=valid_your_model_value()),
        st.builds(dict, name=st.just("   "), value=valid_your_model_value()),
        st.builds(dict, name=valid_your_model_name(), value=st.integers(max_value=-1)),
    )

# Complete model strategies
def valid_your_model(**overrides):
    """Generate valid YourModel instances."""
    def build_model(name, value, optional_field):
        data = {
            "name": name,
            "value": value,
            "optional_field": optional_field,
        }
        data.update(overrides)
        return YourModel(**data)

    return st.builds(
        build_model,
        name=valid_your_model_name(),
        value=valid_your_model_value(),
        optional_field=st.one_of(st.none(), non_empty_text(max_size=100))
    )

# Specialized strategies for specific scenarios
def minimal_your_model():
    """Generate YourModel with minimal required fields."""
    return valid_your_model(optional_field=None)

def maximal_your_model():
    """Generate YourModel with all fields populated."""
    def build_model(name, value):
        return YourModel(
            name=name,
            value=value,
            optional_field=f"Optional data for {name}"
        )

    return st.builds(
        build_model,
        name=valid_your_model_name(),
        value=valid_your_model_value()
    )

# Pattern-based strategies
def your_model_by_pattern():
    """Generate YourModel instances based on common patterns."""
    patterns = [
        YourModel(name="Default Pattern", value=100),
        YourModel(name="Edge Case", value=0),
        YourModel(name="Large Value", value=999999),
    ]
    return st.sampled_from(patterns)
```

### Step 3: Update Strategy Exports

Add your strategies to the module's public API:

```python
# tests/data_models/strategies/__init__.py
# ...existing imports...

# Your domain strategies
from .your_domain import (
    valid_your_model_name,
    valid_your_model_value,
    valid_your_model,
    minimal_your_model,
    maximal_your_model,
    your_model_by_pattern,
    invalid_your_model_data,
)
```

### Step 4: Create Test File with Standard Categories

Create a comprehensive test file using the strategies:

```python
# tests/data_models/test_your_model.py
"""Tests for YourModel data model."""

import pytest
from hypothesis import given, strategies as st
from pydantic import ValidationError

from auto_release_note_generation.data_models.your_model import YourModel
from .strategies import (
    valid_your_model,
    minimal_your_model,
    maximal_your_model,
    invalid_your_model_data,
    valid_your_model_name,
    valid_your_model_value,
)

class TestYourModelValidation:
    """Test YourModel field validation and constraints."""

    @given(valid_your_model())
    def test_valid_creation(self, model: YourModel):
        """Test that valid inputs create YourModel successfully."""
        assert isinstance(model, YourModel)
        assert len(model.name.strip()) > 0
        assert model.value >= 0

    @given(invalid_your_model_data())
    def test_invalid_data_rejection(self, invalid_data: dict):
        """Test that invalid data raises ValidationError."""
        with pytest.raises(ValidationError):
            YourModel(**invalid_data)

    def test_field_validation_edge_cases(self):
        """Test specific validation edge cases."""
        # Empty name
        with pytest.raises(ValidationError, match="at least 1 character"):
            YourModel(name="", value=10)

        # Negative value
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            YourModel(name="Test", value=-1)

    @given(st.text())
    def test_name_normalization(self, raw_name: str):
        """Test that names are properly normalized."""
        if not raw_name.strip():
            with pytest.raises(ValidationError):
                YourModel(name=raw_name, value=10)
        else:
            model = YourModel(name=raw_name, value=10)
            assert model.name == raw_name.strip()


class TestYourModelBehavior:
    """Test YourModel behavior and methods."""

    @given(valid_your_model())
    def test_immutability(self, model: YourModel):
        """Test that model is immutable after creation."""
        with pytest.raises(ValidationError):
            model.name = "New Name"

    @given(valid_your_model())
    def test_string_representation(self, model: YourModel):
        """Test string representation format."""
        str_repr = str(model)
        assert model.name in str_repr
        assert str(model.value) in str_repr

    @given(minimal_your_model(), maximal_your_model())
    def test_optional_field_behavior(self, minimal: YourModel, maximal: YourModel):
        """Test behavior with and without optional fields."""
        assert minimal.optional_field is None
        assert maximal.optional_field is not None


class TestYourModelPropertyBased:
    """Property-based tests for YourModel invariants."""

    @given(valid_your_model())
    def test_model_invariants(self, model: YourModel):
        """Test invariants that should always hold."""
        # Name is never empty after stripping
        assert len(model.name.strip()) > 0

        # Value is always non-negative
        assert model.value >= 0

        # Optional field is either None or non-empty
        if model.optional_field is not None:
            assert len(model.optional_field) > 0

    @given(valid_your_model_name(), valid_your_model_value())
    def test_field_combination_validity(self, name: str, value: int):
        """Test that valid fields always create valid models."""
        model = YourModel(name=name, value=value)
        assert model.name == name.strip()
        assert model.value == value


class TestYourModelEdgeCases:
    """Test YourModel edge cases and boundary conditions."""

    def test_minimum_valid_values(self):
        """Test minimum valid values for all fields."""
        model = YourModel(name="a", value=0)
        assert model.name == "a"
        assert model.value == 0

    def test_maximum_valid_values(self):
        """Test maximum valid values for all fields."""
        long_name = "x" * 255
        model = YourModel(name=long_name, value=999999999)
        assert len(model.name) == 255

    @pytest.mark.parametrize("name,expected", [
        ("  spaces  ", "spaces"),
        ("\ttabs\t", "tabs"),
        ("\nnewlines\n", "newlines"),
        ("  mixed \t\n ", "mixed"),
    ])
    def test_whitespace_handling(self, name: str, expected: str):
        """Test various whitespace handling scenarios."""
        model = YourModel(name=name, value=10)
        assert model.name == expected
```

### Step 5: Create Factory for Complex Scenarios

Add a factory class for creating test instances:

```python
# tests/data_models/test_factories.py
# Add to existing file

class YourModelFactory:
    """Factory for creating YourModel test instances."""

    @staticmethod
    def create(**overrides):
        """Create YourModel with sensible defaults."""
        defaults = {
            "name": "Test Model",
            "value": 100,
            "optional_field": None,
        }
        defaults.update(overrides)
        return YourModel(**defaults)

    @staticmethod
    def create_minimal():
        """Create minimal valid YourModel."""
        return YourModelFactory.create(name="Min", value=0)

    @staticmethod
    def create_maximal():
        """Create YourModel with all fields populated."""
        return YourModelFactory.create(
            name="Maximal Model",
            value=999999,
            optional_field="All fields populated"
        )

    @staticmethod
    def create_from_pattern(pattern: str, **overrides):
        """Create YourModel based on common patterns."""
        patterns = {
            "default": lambda: YourModelFactory.create(**overrides),
            "minimal": lambda: YourModelFactory.create_minimal(**overrides),
            "maximal": lambda: YourModelFactory.create_maximal(**overrides),
            "edge_case": lambda: YourModelFactory.create(
                name="x" * 255, value=0, **overrides
            ),
        }

        if pattern not in patterns:
            raise ValueError(f"Unknown pattern: {pattern}")

        return patterns[pattern]()
```

## Strategy Development Guidelines

### 1. Start with Basic Field Strategies

Begin by creating strategies for individual fields:

```python
def valid_field_name():
    """Generate valid field values."""
    return st.text(min_size=1, max_size=100).filter(valid_length_filter)
```

### 2. Build Invalid Data Strategies

Create strategies that generate invalid data for testing validation:

```python
def invalid_field_data():
    """Generate invalid field values."""
    return st.one_of(
        st.just(""),  # Empty
        st.just("   "),  # Whitespace only
        st.text(min_size=101),  # Too long
    )
```

### 3. Compose Model Strategies

Combine field strategies to create complete models:

```python
def valid_model(**overrides):
    """Generate valid model instances."""
    def build_model(field1, field2):
        data = {"field1": field1, "field2": field2}
        data.update(overrides)
        return Model(**data)

    return st.builds(
        build_model,
        field1=valid_field1(),
        field2=valid_field2()
    )
```

### 4. Create Specialized Strategies

Add strategies for specific test scenarios:

```python
def model_with_edge_case():
    """Generate model with edge case values."""
    return valid_model(field1="edge_case_value")

def model_by_type(model_type: str):
    """Generate model based on type."""
    type_strategies = {
        "minimal": minimal_model(),
        "maximal": maximal_model(),
        "typical": typical_model(),
    }
    return type_strategies[model_type]
```

### 5. Document Strategy Intent

Always document what each strategy generates and why:

```python
def complex_scenario_model():
    """Generate model representing a complex real-world scenario.

    This represents the case where a user has:
    - Maximum length name
    - Minimum valid value
    - All optional fields populated

    Used for stress testing and edge case validation.
    """
    return valid_model(
        name="x" * 255,
        value=0,
        optional_field="Complex scenario"
    )
```

## Testing Categories

Organize tests into these standard categories:

### 1. Validation Tests
- Field validation and constraints
- Input sanitization
- Business rule validation
- Error message verification

### 2. Behavior Tests
- Model methods and properties
- Immutability checks
- String representations
- Computed properties

### 3. Property-Based Tests
- Model invariants
- Field relationships
- Generation consistency
- Round-trip serialization

### 4. Edge Case Tests
- Boundary values
- Unicode and special characters
- Performance with large data
- Real-world patterns

## Best Practices

### 1. Use Type Hints

Always specify return types for strategies:

```python
def valid_model() -> st.SearchStrategy[YourModel]:
    """Generate valid YourModel instances."""
    # Implementation
```

### 2. Leverage Base Utilities

Use common utilities from `base.py`:

```python
from .base import non_empty_text, trimmed_text, hex_string

def valid_identifier():
    """Generate valid identifier using base utilities."""
    return trimmed_text(min_size=1, max_size=50)
```

### 3. Create Composable Strategies

Design strategies that can be combined:

```python
def base_model(**overrides):
    """Base strategy that can be customized."""
    # Implementation

def specialized_model():
    """Specialized model building on base."""
    return base_model(special_field="special_value")
```

### 4. Test Strategy Quality

Verify your strategies generate appropriate data:

```python
def test_strategy_generates_valid_models():
    """Test that strategy always generates valid models."""
    # Generate 100 examples
    examples = [valid_model().example() for _ in range(100)]

    # Verify all are valid
    for model in examples:
        assert isinstance(model, YourModel)
        # Add specific assertions
```

### 5. Handle Optional Fields

Properly handle optional fields in strategies:

```python
def model_with_optional():
    """Generate model with optional field handling."""
    return st.builds(
        YourModel,
        required_field=valid_field(),
        optional_field=st.one_of(
            st.none(),  # 50% None
            valid_optional_field()  # 50% populated
        )
    )
```

## Examples

### Complete Strategy Module Example

```python
# tests/data_models/strategies/your_domain.py
"""Hypothesis strategies for YourDomain models."""

from datetime import datetime
from hypothesis import strategies as st

from auto_release_note_generation.data_models import YourModel, RelatedModel
from .base import non_empty_text, valid_length_filter
from .utils import valid_git_sha

# Field strategies
def valid_identifier():
    """Generate valid identifiers."""
    return st.text(
        min_size=3,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_")
    ).filter(lambda x: x[0].isalpha())  # Must start with letter

def valid_timestamp():
    """Generate valid timestamps."""
    return st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 12, 31)
    )

# Model strategies
def valid_your_model(**overrides):
    """Generate valid YourModel instances."""
    def build_model(identifier, timestamp, related_sha):
        data = {
            "identifier": identifier,
            "timestamp": timestamp,
            "related_sha": related_sha,
        }
        data.update(overrides)
        return YourModel(**data)

    return st.builds(
        build_model,
        identifier=valid_identifier(),
        timestamp=valid_timestamp(),
        related_sha=valid_git_sha()
    )

# Scenario strategies
def your_model_with_related():
    """Generate YourModel with related model."""
    def build_with_related(model, related):
        model.set_related(related)
        return model

    return st.builds(
        build_with_related,
        model=valid_your_model(),
        related=valid_related_model()
    )

# Pattern strategies
def your_model_patterns():
    """Generate YourModel based on common patterns."""
    return st.one_of(
        valid_your_model(identifier="system-generated"),
        valid_your_model(identifier="user-created"),
        valid_your_model(identifier="imported-data"),
    )
```

### Using Strategies in Tests

```python
# tests/data_models/test_your_model.py
from hypothesis import given, assume
from .strategies import valid_your_model, your_model_patterns

class TestYourModel:
    @given(valid_your_model())
    def test_model_creation(self, model):
        """Test model creation with generated data."""
        assert model.identifier
        assert model.timestamp
        assert model.related_sha

    @given(your_model_patterns())
    def test_pattern_handling(self, model):
        """Test handling of common patterns."""
        # Pattern-specific assertions
        if model.identifier.startswith("system-"):
            assert model.is_system_generated()
        elif model.identifier.startswith("user-"):
            assert model.is_user_created()

    @given(valid_your_model(), valid_your_model())
    def test_model_comparison(self, model1, model2):
        """Test model comparison with different instances."""
        assume(model1.identifier != model2.identifier)
        assert model1 != model2
        assert model1.identifier != model2.identifier
```

## Summary

The modular strategy system provides:

1. **Clear organization** - Strategies grouped by domain
2. **Type safety** - Strategies return typed model instances
3. **Reusability** - Common patterns extracted to base utilities
4. **Composability** - Simple strategies combine for complex scenarios
5. **Comprehensive testing** - From basic validation to complex edge cases

When adding new data models:
1. Create the model with proper validation
2. Build domain-specific strategies
3. Export strategies in `__init__.py`
4. Write comprehensive tests using the strategies
5. Add factory methods for complex scenarios

This approach ensures consistent, maintainable, and thorough testing across all data models.
