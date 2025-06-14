from datetime import datetime, timezone

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from auto_release_note_generation.data_models.shared import GitActor

# =============================================================================
# TEST CONFIGURATION & SHARED UTILITIES
# =============================================================================


class SharedTestConfig:
    """Configuration constants for all shared data model tests."""

    DEFAULT_TIMESTAMP = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    DEFAULT_NAME = "John Doe"
    DEFAULT_EMAIL = "john.doe@example.com"


# =============================================================================
# HYPOTHESIS STRATEGIES - Reusable across all data models
# =============================================================================


class HypothesisStrategies:
    """Centralized hypothesis strategies for data model testing."""

    # Text-based strategies
    valid_names = st.text(
        min_size=1,
        max_size=255,
        alphabet=st.characters(blacklist_categories=("Cc", "Cs")),
    ).filter(lambda x: len(x.strip()) > 0)  # Ensure name isn't empty after stripping

    valid_emails = st.text(
        min_size=1,
        max_size=320,
        alphabet=st.characters(
            blacklist_categories=("Cc", "Cs"), blacklist_characters="\n\r\t"
        ),
    ).filter(lambda x: len(x.strip()) > 0)  # Ensure email isn't empty after stripping

    git_realistic_emails = st.one_of(
        st.emails().map(str),
        st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="@.-_+"
            ),
        ),
    )

    # Time-based strategies
    valid_timestamps = st.datetimes(
        min_value=datetime(1970, 1, 1),
        max_value=datetime(2100, 12, 31),
        timezones=st.one_of(st.none(), st.timezones()),
    )

    # Invalid data strategies
    invalid_names = st.one_of(st.just(""), st.text(min_size=256), st.just("   "))

    invalid_emails = st.one_of(st.just(""), st.text(min_size=321), st.just("   "))


# =============================================================================
# TEST DATA COLLECTIONS - Organized by domain
# =============================================================================


class GitTestData:
    """Test data specific to Git-related models."""

    REALISTIC_EMAILS = [
        "plainaddress",
        "user@",
        "@domain.com",
        "build-system",
        "noreply",
        "user@internal",
        "automated-system-123",
    ]

    SPECIAL_NAMES = [
        "John O'Connor",
        "Mary-Jane Smith",
        "Jean-Luc Picard",
        "李小明",
        "Müller, Hans",
    ]

    CORPORATE_PATTERNS = [
        ("Build System", "build@ci"),
        ("Jenkins", "jenkins"),
        ("GitHub", "noreply@github.com"),
        ("Automated Deploy", "deploy-bot"),
        ("Code Review Bot", "review-bot@internal"),
    ]


# =============================================================================
# FACTORY FUNCTIONS - One per data model class
# =============================================================================


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

    @staticmethod
    def create_corporate_pattern(pattern_index=0):
        """Create GitActor with corporate Git pattern."""
        name, email = GitTestData.CORPORATE_PATTERNS[
            pattern_index % len(GitTestData.CORPORATE_PATTERNS)
        ]
        return GitActorFactory.create(name=name, email=email)


# =============================================================================
# SHARED TEST UTILITIES - Reusable across all data models
# =============================================================================


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


# =============================================================================
# FIXTURES - Shared across test classes
# =============================================================================


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
        GitActorFactory.create(name="José García", email="josé@example.com"),
    ]


# =============================================================================
# GITACTOR TEST CLASSES - Organized by test category
# =============================================================================


class TestGitActorValidation:
    """Test GitActor field validation and constraints."""

    @given(
        HypothesisStrategies.valid_names,
        HypothesisStrategies.git_realistic_emails,
        HypothesisStrategies.valid_timestamps,
    )
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
            GitActorFactory.create, field_name="name", name=invalid_name
        )

    @given(HypothesisStrategies.invalid_emails)
    def test_invalid_email_rejection(self, invalid_email):
        """Test that invalid emails raise ValidationError."""
        TestHelpers.assert_validation_error(
            GitActorFactory.create, field_name="email", email=invalid_email
        )

    @pytest.mark.parametrize("email", GitTestData.REALISTIC_EMAILS)
    def test_git_realistic_emails_accepted(self, email):
        """Test that Git-realistic malformed emails are accepted."""
        actor = GitActorFactory.create(email=email)

        assert actor.email == email.lower()
        # Verify string representation works
        str_result = str(actor)
        assert email.lower() in str_result

    def test_email_normalization(self):
        """Test that email is normalized to lowercase."""
        actor = GitActorFactory.create(email="JOHN.DOE@EXAMPLE.COM")
        assert actor.email == "john.doe@example.com"

    def test_whitespace_stripping(self):
        """Test that whitespace is stripped from name and email."""
        actor = GitActor(
            name="  John Doe  ",
            email="  john.doe@example.com  ",
            timestamp=datetime.now(),
        )

        assert actor.name == "John Doe"
        assert actor.email == "john.doe@example.com"


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

    def test_string_representation_without_timezone(self):
        """Test __str__ handles naive datetime."""
        naive_time = datetime(2023, 1, 1, 12, 0, 0)
        actor = GitActorFactory.create(timestamp=naive_time)

        result = str(actor)
        assert "John Doe <john.doe@example.com>" in result
        assert "+0000" in result

    @given(
        HypothesisStrategies.valid_names,
        HypothesisStrategies.valid_emails,
        HypothesisStrategies.valid_timestamps,
    )
    def test_repr_format(self, name, email, timestamp):
        """Test __repr__ returns detailed representation."""
        actor = GitActor(name=name, email=email, timestamp=timestamp)
        repr_str = repr(actor)

        assert repr_str.startswith("GitActor(")
        assert f"name='{name.strip()}'" in repr_str
        assert f"email='{email.strip().lower()}'" in repr_str
        assert f"timestamp={timestamp.isoformat()}" in repr_str

    def test_string_methods_consistency(self, git_actors_collection):
        """Test that str and repr work consistently across instances."""
        for actor in git_actors_collection:
            str_result = str(actor)
            repr_result = repr(actor)

            assert isinstance(str_result, str)
            assert len(str_result) > 0
            assert isinstance(repr_result, str)
            assert len(repr_result) > 0


class TestGitActorEdgeCases:
    """Test GitActor edge cases and boundary conditions."""

    def test_minimum_length_fields(self):
        """Test minimum valid field lengths."""
        actor = GitActor(name="A", email="a", timestamp=datetime.now())

        assert actor.name == "A"
        assert actor.email == "a"

    def test_maximum_length_fields(self):
        """Test maximum valid field lengths."""
        long_name = "A" * 255
        long_email = "a" * 320

        actor = GitActor(name=long_name, email=long_email, timestamp=datetime.now())

        assert actor.name == long_name
        assert actor.email == long_email

    def test_unicode_support(self):
        """Test Unicode characters in name and email."""
        actor = GitActor(
            name="José García", email="josé@example.com", timestamp=datetime.now()
        )

        assert actor.name == "José García"
        assert actor.email == "josé@example.com"

    @pytest.mark.parametrize("name", GitTestData.SPECIAL_NAMES)
    def test_special_characters_in_name(self, name):
        """Test special characters commonly found in Git names."""
        actor = GitActorFactory.create(name=name)
        assert actor.name == name

    @given(st.datetimes())
    def test_various_timestamp_formats(self, timestamp):
        """Test GitActor handles various timestamp formats."""
        actor = GitActorFactory.create(timestamp=timestamp)

        assert actor.timestamp == timestamp
        assert isinstance(str(actor), str)

    @pytest.mark.parametrize(("name", "email"), GitTestData.CORPORATE_PATTERNS)
    def test_corporate_git_patterns(self, name, email):
        """Test patterns commonly found in corporate Git environments."""
        actor = GitActor(name=name, email=email, timestamp=datetime.now())

        assert actor.name == name
        assert actor.email == email.lower()
        str(actor)  # Should not raise exception


class TestGitActorFactory:
    """Test GitActorFactory functionality."""

    def test_default_creation(self, default_git_actor):
        """Test factory creates valid default GitActor."""
        factory_actor = GitActorFactory.create()

        assert factory_actor.name == default_git_actor.name
        assert factory_actor.email == default_git_actor.email
        assert isinstance(factory_actor.timestamp, datetime)

    def test_override_functionality(self):
        """Test factory accepts override values."""
        custom_name = "Jane Smith"
        actor = GitActorFactory.create(name=custom_name)

        assert actor.name == custom_name
        assert actor.email == SharedTestConfig.DEFAULT_EMAIL

    def test_realistic_email_factory(self):
        """Test factory method for realistic Git emails."""
        actor = GitActorFactory.create_with_realistic_email(0)

        assert actor.email in [email.lower() for email in GitTestData.REALISTIC_EMAILS]

    def test_corporate_pattern_factory(self):
        """Test factory method for corporate Git patterns."""
        actor = GitActorFactory.create_corporate_pattern(0)

        expected_name, expected_email = GitTestData.CORPORATE_PATTERNS[0]
        assert actor.name == expected_name
        assert actor.email == expected_email.lower()

    @given(HypothesisStrategies.valid_names)
    def test_factory_with_hypothesis(self, name):
        """Test factory works with hypothesis-generated data."""
        actor = GitActorFactory.create(name=name)
        assert actor.name == name.strip()


# =============================================================================
# FUTURE EXPANSION PLACEHOLDER
# =============================================================================

# When adding new classes to shared.py, follow this pattern:
#
# class TestNewDataModelValidation:
#     """Test NewDataModel field validation and constraints."""
#     pass
#
# class TestNewDataModelBehavior:
#     """Test NewDataModel behavior and constraints."""
#     pass
#
# class TestNewDataModelEdgeCases:
#     """Test NewDataModel edge cases and boundary conditions."""
#     pass
#
# class TestNewDataModelFactory:
#     """Test NewDataModelFactory functionality."""
#     pass
