# Testing Patterns Guide

This document outlines the standardized testing patterns used in the auto-release-note-generation project. These patterns ensure consistency, maintainability, and scalability across all test suites.

## Table of Contents

- [Overview](#overview)
- [File Structure](#file-structure)
- [Core Components](#core-components)
- [Testing Categories](#testing-categories)
- [Best Practices](#best-practices)
- [Examples](#examples)
- [Adding New Tests](#adding-new-tests)

## Overview

Our testing approach combines several powerful testing patterns:

- **Property-based testing** with Hypothesis for comprehensive edge case coverage
- **Factory pattern** for consistent test data creation
- **Parametrized testing** for efficient test case variation
- **Centralized strategies** for reusable test data generation
- **Modular organization** for easy maintenance and expansion

## File Structure

Each test file follows this standardized structure:

```python
# =============================================================================
# TEST CONFIGURATION & SHARED UTILITIES
# =============================================================================

class SharedTestConfig:
    """Configuration constants for all shared data model tests."""
    pass

# =============================================================================
# HYPOTHESIS STRATEGIES - Reusable across all data models
# =============================================================================

class HypothesisStrategies:
    """Centralized hypothesis strategies for data model testing."""
    pass

# =============================================================================
# TEST DATA COLLECTIONS - Organized by domain
# =============================================================================

class DomainTestData:
    """Test data specific to domain-related models."""
    pass

# =============================================================================
# FACTORY FUNCTIONS - One per data model class
# =============================================================================

class ModelFactory:
    """Factory for creating Model test instances."""
    pass

# =============================================================================
# SHARED TEST UTILITIES - Reusable across all data models
# =============================================================================

class TestHelpers:
    """Helper functions for common test patterns."""
    pass

# =============================================================================
# FIXTURES - Shared across test classes
# =============================================================================

@pytest.fixture
def model_fixture():
    pass

# =============================================================================
# MODEL TEST CLASSES - Organized by test category
# =============================================================================

class TestModelValidation:
    pass

class TestModelBehavior:
    pass

class TestModelEdgeCases:
    pass

class TestModelFactory:
    pass
```

## Core Components

### 1. SharedTestConfig

Centralized configuration for test constants:

```python
class SharedTestConfig:
    """Configuration constants for all shared data model tests."""
    
    DEFAULT_TIMESTAMP = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    DEFAULT_NAME = "John Doe"
    DEFAULT_EMAIL = "john.doe@example.com"
    
    # Add model-specific defaults
    DEFAULT_VERSION = "1.0.0"
    DEFAULT_URL = "https://example.com"
```

**Purpose**: Single source of truth for test data constants that need to remain consistent across tests.

### 2. HypothesisStrategies

Centralized Hypothesis strategies for property-based testing:

```python
class HypothesisStrategies:
    """Centralized hypothesis strategies for data model testing."""
    
    # Valid data strategies
    valid_names = st.text(
        min_size=1, 
        max_size=255, 
        alphabet=st.characters(blacklist_categories=("Cc", "Cs"))
    )
    
    # Invalid data strategies  
    invalid_names = st.one_of(
        st.just(""),
        st.text(min_size=256),
        st.just("   ")
    )
    
    # Domain-specific strategies
    git_emails = st.one_of(
        st.emails().map(str),
        st.text(min_size=1, max_size=50, alphabet=st.characters(...))
    )
```

**Purpose**: Reusable data generation strategies that can be composed for different test scenarios.

### 3. DomainTestData

Static test data collections organized by domain:

```python
class GitTestData:
    """Test data specific to Git-related models."""
    
    REALISTIC_EMAILS = [
        "plainaddress",
        "user@",
        "@domain.com",
        "build-system",
    ]
    
    CORPORATE_PATTERNS = [
        ("Build System", "build@ci"),
        ("Jenkins", "jenkins"),
    ]
```

**Purpose**: Curated collections of real-world test cases that represent common patterns.

### 4. Factory Classes

One factory per data model for consistent instance creation:

```python
class GitActorFactory:
    """Factory for creating GitActor test instances."""
    
    @staticmethod
    def create(**overrides):
        """Create GitActor with optional field overrides."""
        defaults = {
            "name": SharedTestConfig.DEFAULT_NAME,
            "email": SharedTestConfig.DEFAULT_EMAIL,
            "timestamp": SharedTestConfig.DEFAULT_TIMESTAMP,
        }
        defaults.update(overrides)
        return GitActor(**defaults)
    
    @staticmethod
    def create_with_realistic_email(email_index=0):
        """Create GitActor with Git-realistic email."""
        email = GitTestData.REALISTIC_EMAILS[
            email_index % len(GitTestData.REALISTIC_EMAILS)
        ]
        return GitActorFactory.create(email=email)
```

**Purpose**: Consistent, customizable instance creation with sensible defaults.

### 5. TestHelpers

Reusable assertion and utility functions:

```python
class TestHelpers:
    """Helper functions for common test patterns."""
    
    @staticmethod
    def assert_validation_error(factory_func, field_name=None, **kwargs):
        """Assert ValidationError is raised with optional field checking."""
        with pytest.raises(ValidationError) as exc_info:
            factory_func(**kwargs)
        
        if field_name:
            error_fields = [error["loc"][0] for error in exc_info.value.errors()]
            assert field_name in error_fields
        
        return exc_info.value
    
    @staticmethod
    def assert_model_immutable(model_instance, field_updates):
        """Assert that model fields cannot be modified (frozen behavior)."""
        for field_name, new_value in field_updates.items():
            with pytest.raises(ValidationError):
                setattr(model_instance, field_name, new_value)
```

**Purpose**: Common assertion patterns that reduce code duplication and improve test readability.

### 6. Fixtures

Shared test instances and collections:

```python
@pytest.fixture
def default_git_actor():
    """Default GitActor instance for testing."""
    return GitActorFactory.create()

@pytest.fixture
def git_actors_collection():
    """Collection of various GitActor instances for bulk testing."""
    return [
        GitActorFactory.create(),
        GitActorFactory.create_with_realistic_email(),
        GitActorFactory.create_corporate_pattern(),
    ]
```

**Purpose**: Reusable test data that can be shared across multiple test methods.

## Testing Categories

### 1. TestModelValidation

Tests field validation, constraints, and input sanitization:

```python
class TestGitActorValidation:
    """Test GitActor field validation and constraints."""

    @given(HypothesisStrategies.valid_names, 
           HypothesisStrategies.git_realistic_emails, 
           HypothesisStrategies.valid_timestamps)
    def test_valid_creation(self, name, email, timestamp):
        """Test that valid inputs create GitActor successfully."""
        actor = GitActor(name=name, email=email, timestamp=timestamp)
        
        assert actor.name == name.strip()
        assert actor.email == email.lower()
        assert actor.timestamp == timestamp

    @given(HypothesisStrategies.invalid_names)
    def test_invalid_name_rejection(self, invalid_name):
        """Test that invalid names raise ValidationError."""
        TestHelpers.assert_validation_error(
            GitActorFactory.create,
            field_name="name",
            name=invalid_name
        )
```

**Focus**: Input validation, field constraints, data transformation.

### 2. TestModelBehavior

Tests core functionality, methods, and expected behaviors:

```python
class TestGitActorBehavior:
    """Test GitActor behavior and constraints."""

    def test_immutability(self, default_git_actor):
        """Test that GitActor is immutable after creation."""
        field_updates = {
            "name": "New Name",
            "email": "new@example.com",
            "timestamp": datetime.now(),
        }
        
        TestHelpers.assert_model_immutable(default_git_actor, field_updates)

    def test_string_representation_format(self):
        """Test __str__ returns proper Git format."""
        fixed_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        actor = GitActorFactory.create(timestamp=fixed_time)
        
        expected = "John Doe <john.doe@example.com> 1672574400 +0000"
        assert str(actor) == expected
```

**Focus**: Method behavior, string representations, model configuration.

### 3. TestModelEdgeCases

Tests boundary conditions, edge cases, and unusual scenarios:

```python
class TestGitActorEdgeCases:
    """Test GitActor edge cases and boundary conditions."""

    def test_minimum_length_fields(self):
        """Test minimum valid field lengths."""
        actor = GitActor(name="A", email="a", timestamp=datetime.now())
        
        assert actor.name == "A"
        assert actor.email == "a"

    @pytest.mark.parametrize("name", GitTestData.SPECIAL_NAMES)
    def test_special_characters_in_name(self, name):
        """Test special characters commonly found in Git names."""
        actor = GitActorFactory.create(name=name)
        assert actor.name == name
```

**Focus**: Boundary values, special characters, unusual but valid inputs.

### 4. TestModelFactory

Tests factory functionality and test data generation:

```python
class TestGitActorFactory:
    """Test GitActorFactory functionality."""

    def test_default_creation(self, default_git_actor):
        """Test factory creates valid default GitActor."""
        factory_actor = GitActorFactory.create()
        
        assert factory_actor.name == default_git_actor.name
        assert factory_actor.email == default_git_actor.email

    @given(HypothesisStrategies.valid_names)
    def test_factory_with_hypothesis(self, name):
        """Test factory works with hypothesis-generated data."""
        actor = GitActorFactory.create(name=name)
        assert actor.name == name.strip()
```

**Focus**: Factory method correctness, integration with test data strategies.

## Best Practices

### 1. Property-Based Testing

Use Hypothesis for comprehensive testing:

```python
@given(HypothesisStrategies.valid_names, HypothesisStrategies.valid_emails)
def test_model_creation(self, name, email):
    """Property-based test for model creation."""
    model = ModelFactory.create(name=name, email=email)
    
    # Test invariants that should always hold
    assert len(model.name) > 0
    assert "@" in model.email or model.email in VALID_NON_EMAIL_FORMATS
```

### 2. Parametrized Testing

Use parametrization for multiple similar test cases:

```python
@pytest.mark.parametrize("invalid_input,expected_error", [
    ("", "String too short"),
    ("x" * 300, "String too long"),
    ("   ", "String is whitespace"),
])
def test_validation_errors(self, invalid_input, expected_error):
    """Test specific validation error messages."""
    with pytest.raises(ValidationError, match=expected_error):
        ModelFactory.create(field=invalid_input)
```

### 3. Meaningful Test Names

Use descriptive test names that explain what is being tested:

```python
# Good
def test_email_normalization_converts_uppercase_to_lowercase(self):
    
# Better  
def test_email_field_automatically_converts_uppercase_to_lowercase(self):

# Best
def test_email_validation_normalizes_uppercase_emails_to_lowercase_for_consistency(self):
```

### 4. Test Data Organization

Organize test data by domain and use case:

```python
class EmailTestData:
    """Email-specific test data patterns."""
    
    VALID_FORMATS = [
        "user@domain.com",
        "user.name@domain.com", 
        "user+tag@domain.com",
    ]
    
    GIT_REALISTIC = [
        "plainaddress",  # No @ symbol (common in Git)
        "build-system",  # System identifiers
    ]
    
    CORPORATE_PATTERNS = [
        "jenkins@ci-server",
        "deploy-bot@internal",
    ]
```

### 5. Error Testing

Test both positive and negative cases:

```python
def test_validation_accepts_valid_input(self):
    """Test that valid input is accepted."""
    model = ModelFactory.create(field="valid_value")
    assert model.field == "valid_value"

def test_validation_rejects_invalid_input(self):
    """Test that invalid input is rejected with proper error."""
    TestHelpers.assert_validation_error(
        ModelFactory.create,
        field_name="field",
        field="invalid_value"
    )
```

## Examples

### Complete Test Class Example

```python
class TestCommitMessageValidation:
    """Test CommitMessage field validation and constraints."""

    @given(HypothesisStrategies.valid_commit_messages)
    def test_valid_commit_message_creation(self, message):
        """Test that valid commit messages create instances successfully."""
        commit = CommitMessageFactory.create(message=message)
        
        assert commit.message == message.strip()
        assert len(commit.message) > 0

    @pytest.mark.parametrize("invalid_message", [
        "",  # Empty
        "   ",  # Whitespace only
        "x" * 1001,  # Too long
    ])
    def test_invalid_commit_message_rejection(self, invalid_message):
        """Test that invalid commit messages raise ValidationError."""
        TestHelpers.assert_validation_error(
            CommitMessageFactory.create,
            field_name="message",
            message=invalid_message
        )

    def test_commit_message_whitespace_normalization(self):
        """Test that leading/trailing whitespace is stripped."""
        commit = CommitMessageFactory.create(message="  Fix bug  ")
        assert commit.message == "Fix bug"
```

### Factory Pattern Example

```python
class CommitMessageFactory:
    """Factory for creating CommitMessage test instances."""
    
    @staticmethod
    def create(**overrides):
        """Create CommitMessage with optional field overrides."""
        defaults = {
            "message": SharedTestConfig.DEFAULT_COMMIT_MESSAGE,
            "author": GitActorFactory.create(),
            "timestamp": SharedTestConfig.DEFAULT_TIMESTAMP,
        }
        defaults.update(overrides)
        return CommitMessage(**defaults)
    
    @staticmethod
    def create_conventional_commit(commit_type="feat"):
        """Create CommitMessage following conventional commit format."""
        message = f"{commit_type}: add new feature"
        return CommitMessageFactory.create(message=message)
    
    @staticmethod
    def create_with_body_and_footer():
        """Create CommitMessage with extended format."""
        message = """feat: add user authentication

Implement OAuth2 authentication flow with Google and GitHub providers.
Includes user session management and token refresh.

Closes #123
Co-authored-by: Jane Doe <jane@example.com>"""
        return CommitMessageFactory.create(message=message)
```

## Adding New Tests

### Step 1: Extend Configuration

Add new constants to `SharedTestConfig`:

```python
class SharedTestConfig:
    # ...existing config...
    
    # New model defaults
    DEFAULT_REPOSITORY_URL = "https://github.com/user/repo.git"
    DEFAULT_BRANCH_NAME = "main"
    DEFAULT_TAG_NAME = "v1.0.0"
```

### Step 2: Add Hypothesis Strategies

Extend `HypothesisStrategies` with new data generators:

```python
class HypothesisStrategies:
    # ...existing strategies...
    
    # New strategies
    valid_urls = st.text(min_size=10).map(lambda x: f"https://{x}.com")
    valid_branch_names = st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), 
                              whitelist_characters="-_/")
    ).filter(lambda x: not x.startswith('/') and not x.endswith('/'))
```

### Step 3: Create Test Data Collections

Add domain-specific test data:

```python
class RepositoryTestData:
    """Test data specific to repository-related models."""
    
    COMMON_URLS = [
        "https://github.com/user/repo.git",
        "git@github.com:user/repo.git",
        "https://gitlab.com/user/repo.git",
    ]
    
    BRANCH_PATTERNS = [
        "main",
        "develop", 
        "feature/add-authentication",
        "bugfix/fix-login-issue",
        "release/v1.2.0",
    ]
```

### Step 4: Create Factory Class

Implement factory for the new model:

```python
class RepositoryFactory:
    """Factory for creating Repository test instances."""
    
    @staticmethod
    def create(**overrides):
        """Create Repository with optional field overrides."""
        defaults = {
            "url": SharedTestConfig.DEFAULT_REPOSITORY_URL,
            "branch": SharedTestConfig.DEFAULT_BRANCH_NAME,
            "name": "test-repo",
        }
        defaults.update(overrides)
        return Repository(**defaults)
    
    @staticmethod
    def create_github_repo():
        """Create Repository with GitHub-specific patterns."""
        return RepositoryFactory.create(
            url="https://github.com/owner/repo.git",
            name="repo"
        )
```

### Step 5: Implement Test Classes

Create the four standard test classes:

```python
class TestRepositoryValidation:
    """Test Repository field validation and constraints."""
    
    @given(HypothesisStrategies.valid_urls)
    def test_valid_url_acceptance(self, url):
        """Test that valid URLs are accepted."""
        repo = RepositoryFactory.create(url=url)
        assert repo.url == url

class TestRepositoryBehavior:
    """Test Repository behavior and constraints."""
    
    def test_url_parsing_extracts_name(self):
        """Test that repository name is extracted from URL."""
        repo = RepositoryFactory.create(url="https://github.com/user/my-repo.git")
        assert repo.name == "my-repo"

class TestRepositoryEdgeCases:
    """Test Repository edge cases and boundary conditions."""
    
    @pytest.mark.parametrize("url", RepositoryTestData.COMMON_URLS)
    def test_common_url_formats(self, url):
        """Test common repository URL formats."""
        repo = RepositoryFactory.create(url=url)
        assert repo.url == url

class TestRepositoryFactory:
    """Test RepositoryFactory functionality."""
    
    def test_github_repo_factory(self):
        """Test GitHub-specific repository factory."""
        repo = RepositoryFactory.create_github_repo()
        assert "github.com" in repo.url
```

### Step 6: Add Fixtures

Create fixtures for the new model:

```python
@pytest.fixture
def default_repository():
    """Default Repository instance for testing."""
    return RepositoryFactory.create()

@pytest.fixture
def repository_collection():
    """Collection of various Repository instances for bulk testing."""
    return [
        RepositoryFactory.create(),
        RepositoryFactory.create_github_repo(),
        RepositoryFactory.create(url="https://gitlab.com/user/repo.git"),
    ]
```

## Conclusion

This testing pattern provides:

- **Consistency** across all test files
- **Reusability** of test data and utilities
- **Scalability** for adding new models and tests
- **Maintainability** through clear organization
- **Comprehensive coverage** with property-based testing

Follow this guide when adding new tests to ensure consistency and quality across the entire test suite.