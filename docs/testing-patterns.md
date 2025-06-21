# Testing Patterns Guide

This guide explains the core testing principles and patterns for adding new modules and tests to the auto-release-note-generation project. Follow these patterns to ensure consistency, maintainability, and scalability as the codebase grows.

## Table of Contents

- [Core Principles](#core-principles)
- [Testing Architecture](#testing-architecture)
- [Essential Components](#essential-components)
- [Testing Categories](#testing-categories)
- [Best Practices](#best-practices)
- [Adding New Tests](#adding-new-tests)
- [Examples](#examples)

## Core Principles

When adding new tests or modules, follow these fundamental principles:

### 1. **Domain Separation**
- **One file per data model** - Each domain gets its own test file
- **Clear boundaries** - GitActor tests stay in `test_git_actor.py`, not mixed elsewhere
- **Focused responsibility** - Each test file has a single, clear purpose

### 2. **Pattern-Based Testing**
- **Property-based testing** with Hypothesis for comprehensive edge case coverage
- **Factory patterns** for consistent test data creation
- **Parametrized testing** for efficient test case variation
- **Fixture-based setup** for reusable test instances

### 3. **Shared Infrastructure**
- **Centralized configuration** for shared constants and utilities
- **Reusable strategies** for data generation
- **Common test data** organized by domain
- **Standardized assertions** for consistent error checking

## Testing Architecture

Organize your tests using this modular structure:

```
tests/data_models/
├── conftest.py                 # Shared configuration and fixtures
├── test_data.py               # Test data collections by domain
├── test_strategies.py         # Hypothesis strategies
├── test_factories.py          # Factory classes for test instances
├── test_{model_name}.py       # One file per data model
└── test_utils.py              # Utility function tests
```

### When to Create New Files

**Create a new test file when:**
- Adding a new data model (e.g., `Repository` → `test_repository.py`)
- Testing a new utility module (e.g., `validation.py` → `test_validation.py`)
- A domain grows beyond a single file's scope

**Use existing files when:**
- Adding tests for existing models
- Extending factory methods
- Adding new test data or strategies

## Essential Components

Understanding these four core components will help you add tests consistently:

### 1. SharedTestConfig - Central Configuration

Define constants that multiple tests need:

```python
class SharedTestConfig:
    """Configuration constants for all shared data model tests."""

    # Core defaults - used across all models
    DEFAULT_TIMESTAMP = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    DEFAULT_NAME = "John Doe"
    DEFAULT_EMAIL = "john.doe@example.com"

    # Model-specific defaults
    DEFAULT_CHANGE_TYPE = "direct"
    DEFAULT_TARGET_BRANCH = "main"

    # Validation collections
    VALID_CHANGE_TYPES = ["direct", "merge", "squash", "octopus", ...]
    INVALID_CHANGE_TYPES = ["invalid", "", None, "push", "pull"]
```

**When to add here:** Constants used by multiple test files or shared validation data.

### 2. HypothesisStrategies - Data Generation

Create reusable strategies for property-based testing:

```python
class HypothesisStrategies:
    """Centralized hypothesis strategies for data model testing."""

    # Basic data types
    valid_names = st.text(min_size=1, max_size=255)
    valid_emails = st.one_of(st.emails().map(str), git_realistic_emails)

    # Domain-specific strategies
    valid_git_shas = st.text(
        min_size=4, max_size=64,
        alphabet="0123456789abcdef"
    )

    valid_change_types = st.sampled_from([
        "direct", "merge", "squash", "octopus", "rebase"
    ])
```

**When to add here:** Reusable data generators that can be composed for different test scenarios.

### 3. TestData Collections - Static Test Data

Organize real-world test cases by domain:

```python
class GitTestData:
    """Test data specific to Git-related models."""

    REALISTIC_EMAILS = [
        "plainaddress",          # No @ symbol (common in Git)
        "build-system",          # System identifiers
        "user@internal",         # Internal domains
    ]

    CORPORATE_PATTERNS = [
        ("Build System", "build@ci"),
        ("Jenkins", "jenkins"),
        ("GitHub", "noreply@github.com"),
    ]
```

**When to add here:** Curated collections of real-world patterns and edge cases.

### 4. Factory Classes - Instance Creation

Build consistent test instances with pattern support:

```python
class ModelFactory:
    """Factory for creating Model test instances."""

    @staticmethod
    def create(**overrides):
        """Create Model with optional field overrides."""
        defaults = {
            "field1": SharedTestConfig.DEFAULT_VALUE,
            "field2": "sensible_default",
        }
        defaults.update(overrides)
        return Model(**defaults)

    @staticmethod
    def create_from_pattern(pattern_name: str, **overrides):
        """Create Model based on real-world patterns."""
        patterns = {
            "pattern1": lambda **k: ModelFactory.create(field1="specific_value", **k),
            "pattern2": lambda **k: ModelFactory.create(field2="other_value", **k),
        }
        return patterns[pattern_name](**overrides)
```

**When to add here:** When you need consistent instance creation or want to support workflow patterns.
## Testing Categories

Organize your test classes into these four standardized categories for any data model:

### 1. TestModelValidation
**Purpose:** Test field validation, constraints, and input sanitization

```python
class TestYourModelValidation:
    """Test YourModel field validation and constraints."""

    def test_valid_creation(self):
        """Test that valid inputs create instances successfully."""

    def test_invalid_field_rejection(self):
        """Test that invalid fields raise ValidationError."""

    def test_business_logic_validation(self):
        """Test that field combinations follow business rules."""
```

### 2. TestModelBehavior  
**Purpose:** Test core functionality, methods, and expected behaviors

```python
class TestYourModelBehavior:
    """Test YourModel behavior and constraints."""

    def test_immutability(self):
        """Test that model is immutable after creation."""

    def test_string_representation_format(self):
        """Test __str__ returns expected format."""

    def test_method_behavior(self):
        """Test custom methods work correctly."""
```

### 3. TestModelEdgeCases
**Purpose:** Test boundary conditions, edge cases, and unusual scenarios

```python
class TestYourModelEdgeCases:
    """Test YourModel edge cases and boundary conditions."""

    def test_minimum_length_fields(self):
        """Test minimum valid field lengths."""

    def test_special_characters(self):
        """Test special characters and unicode support."""

    def test_real_world_patterns(self):
        """Test patterns found in production data."""
```

### 4. TestModelFactory
**Purpose:** Test factory functionality and test data generation

```python
class TestYourModelFactory:
    """Test YourModelFactory functionality."""

    def test_default_creation(self):
        """Test factory creates valid default instances."""

    def test_pattern_based_creation(self):
        """Test pattern-based factory usage."""

    def test_factory_with_hypothesis(self):
        """Test factory works with hypothesis-generated data."""
```

## Best Practices

Follow these guidelines when adding new tests:

### 1. Use Property-Based Testing for Validation

Test with generated data to catch edge cases:

```python
@given(HypothesisStrategies.valid_names, HypothesisStrategies.valid_emails)
def test_model_creation_invariants(self, name, email):
    """Property-based test for model creation."""
    instance = ModelFactory.create(name=name, email=email)

    # Test invariants that should always hold
    assert len(instance.name.strip()) > 0
    assert instance.name == name.strip()  # Whitespace normalization
    assert instance.email == email.lower()  # Email normalization
```

### 2. Use Parametrized Testing for Multiple Cases

Test multiple similar scenarios efficiently:

```python
@pytest.mark.parametrize("input_value,expected_result", [
    ("valid_input", "expected_output"),
    ("edge_case", "edge_result"),
    ("special_chars", "special_result"),
])
def test_field_processing(self, input_value, expected_result):
    """Test that different inputs produce expected results."""
    instance = ModelFactory.create(field=input_value)
    assert instance.processed_field == expected_result
```

### 3. Use Descriptive Test Names

Name tests to explain what they verify:

```python
# ✅ Good - explains the behavior being tested
def test_email_field_converts_uppercase_to_lowercase_for_consistency(self):

# ❌ Avoid - generic and unclear
def test_email_validation(self):
```

### 4. Test Both Positive and Negative Cases

Always test both success and failure scenarios:

```python
def test_valid_input_accepted(self):
    """Test that valid input creates instance successfully."""
    instance = ModelFactory.create(field="valid_value")
    assert instance.field == "valid_value"

def test_invalid_input_rejected(self):
    """Test that invalid input raises appropriate error."""
    with pytest.raises(ValidationError, match="Expected error message"):
        ModelFactory.create(field="invalid_value")
```

### 5. Organize Tests by Single Responsibility

Each test class should have one clear purpose:

```python
# ✅ Good - clear separation
class TestModelValidation:
    """Test field validation only."""

class TestModelBehavior:  
    """Test methods and business logic only."""

# ❌ Avoid - mixed responsibilities
class TestModel:
    """Tests everything - hard to navigate."""
```

## Adding New Tests

Follow this step-by-step process to add tests for new models or functionality:

### Step 1: Determine Test Location

**For new data models:**
- Create `test_{model_name}.py` (e.g., `test_repository.py`)
- Use existing domain files for related functionality

**For existing models:**
- Add to appropriate existing test file
- Extend factory methods in `test_factories.py`

### Step 2: Add Shared Configuration

Update `conftest.py` with constants your tests will need:

```python
class SharedTestConfig:
    # ...existing config...

    # Your new model defaults
    DEFAULT_NEW_FIELD = "sensible_default"
    VALID_NEW_OPTIONS = ["option1", "option2", "option3"]
    INVALID_NEW_OPTIONS = ["invalid", "", None]
```

### Step 3: Create Hypothesis Strategies

Add data generation strategies to `test_strategies.py`:

```python
class HypothesisStrategies:
    # ...existing strategies...

    # Your new field strategies
    valid_new_fields = st.text(min_size=1, max_size=100)
    valid_new_options = st.sampled_from(["option1", "option2", "option3"])
```

### Step 4: Add Test Data Collections

Create domain-specific test data in `test_data.py`:

```python
class YourDomainTestData:
    """Test data specific to your domain."""

    COMMON_PATTERNS = [
        "pattern1",
        "pattern2",
        "pattern3",
    ]

    EDGE_CASES = [
        "edge_case_1",
        "edge_case_2",
    ]
```

### Step 5: Create Factory Class

Add factory to `test_factories.py`:

```python
class YourModelFactory:
    """Factory for creating YourModel test instances."""

    @staticmethod
    def create(**overrides):
        """Create YourModel with optional field overrides."""
        defaults = {
            "field1": SharedTestConfig.DEFAULT_VALUE,
            "field2": "another_default",
        }
        defaults.update(overrides)
        return YourModel(**defaults)

    @staticmethod
    def create_from_pattern(pattern_name: str, **overrides):
        """Create YourModel based on real-world patterns."""
        patterns = {
            "pattern1": lambda **k: YourModelFactory.create(field1="specific", **k),
            "pattern2": lambda **k: YourModelFactory.create(field2="other", **k),
        }
        return patterns[pattern_name](**overrides)
```

### Step 6: Create Test File

Create your test file with the four standard test classes:

```python
"""Tests for YourModel data model."""

import pytest
from pydantic import ValidationError

from your_module.models import YourModel
from .conftest import SharedTestConfig
from .test_strategies import HypothesisStrategies
from .test_data import YourDomainTestData
from .test_factories import YourModelFactory


class TestYourModelValidation:
    """Test YourModel field validation and constraints."""

    def test_valid_creation(self):
        """Test that valid inputs create YourModel successfully."""
        # ...test implementation


class TestYourModelBehavior:
    """Test YourModel behavior and constraints."""

    def test_string_representation(self):
        """Test __str__ returns expected format."""
        # ...test implementation


class TestYourModelEdgeCases:
    """Test YourModel edge cases and boundary conditions."""

    def test_boundary_values(self):
        """Test minimum and maximum valid values."""
        # ...test implementation


class TestYourModelFactory:
    """Test YourModelFactory functionality."""

    def test_default_creation(self):
        """Test factory creates valid default instances."""
        # ...test implementation
```

### Step 7: Add Fixtures (if needed)

Add fixtures to `conftest.py` for shared test data:

```python
@pytest.fixture
def default_your_model():
    """Default YourModel instance for testing."""
    from .test_factories import YourModelFactory
    return YourModelFactory.create()
```

### Step 8: Run and Validate Tests

```bash
# Run only your new tests
uv run pytest tests/data_models/test_your_model.py -v

# Run all tests to ensure no regressions  
uv run pytest tests/data_models/ -v

# Check coverage
uv run pytest tests/data_models/ --cov=src --cov-report=html
```

### Quick Reference Checklist

When adding tests, ensure you have:

- [ ] **Four test classes**: Validation, Behavior, EdgeCases, Factory
- [ ] **Property-based tests**: Using Hypothesis strategies
- [ ] **Parametrized tests**: For multiple similar cases
- [ ] **Error testing**: Both positive and negative cases
- [ ] **Factory methods**: For consistent instance creation
- [ ] **Descriptive test names**: Explaining what is being tested
- [ ] **Shared constants**: In SharedTestConfig for reusable values

## Examples

### Complete Test Class Structure

```python
class TestModelValidation:
    """Test Model field validation and constraints."""

    @given(HypothesisStrategies.valid_fields)
    def test_valid_creation(self, field_value):
        """Test that valid inputs create Model successfully."""
        instance = ModelFactory.create(field=field_value)
        assert instance.field == field_value

    @pytest.mark.parametrize("invalid_input,expected_error", [
        ("", "Field cannot be empty"),
        (None, "Field is required"),
        ("x" * 300, "Field too long"),
    ])
    def test_invalid_field_rejection(self, invalid_input, expected_error):
        """Test that invalid fields raise ValidationError."""
        with pytest.raises(ValidationError, match=expected_error):
            ModelFactory.create(field=invalid_input)
```

### Factory with Pattern Support

```python
class ModelFactory:
    """Factory for creating Model test instances."""

    @staticmethod
    def create(**overrides):
        """Create Model with intelligent defaults."""
        defaults = {
            "field1": SharedTestConfig.DEFAULT_VALUE,
            "field2": "default_value",
        }
        defaults.update(overrides)
        return Model(**defaults)

    @staticmethod
    def create_from_pattern(pattern_name: str, **overrides):
        """Create Model based on real-world patterns."""
        patterns = {
            "common": lambda **k: ModelFactory.create(field1="common_value", **k),
            "edge_case": lambda **k: ModelFactory.create(field1="edge_value", **k),
        }

        if pattern_name not in patterns:
            raise ValueError(f"Unknown pattern: {pattern_name}")

        return patterns[pattern_name](**overrides)
```

### Property-Based Testing

```python
@given(HypothesisStrategies.valid_names, HypothesisStrategies.valid_emails)
def test_model_invariants(self, name, email):
    """Test invariants that should always hold."""
    instance = ModelFactory.create(name=name, email=email)

    # These should always be true regardless of input
    assert len(instance.name.strip()) > 0
    assert instance.name == name.strip()
    assert instance.email == email.lower()
```

---

## Summary

This guide provides the essential patterns for adding new tests to the project:

1. **Follow the four-class structure** for each domain (Validation, Behavior, EdgeCases, Factory)
2. **Use shared infrastructure** (SharedTestConfig, HypothesisStrategies, TestData, Factories)
3. **Apply best practices** (property-based testing, descriptive names, error testing)
4. **Follow the step-by-step process** for adding new models or extending existing ones

By following these patterns, you ensure that new tests integrate seamlessly with the existing test suite while maintaining consistency, quality, and maintainability as the codebase grows.
