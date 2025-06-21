"""Tests for GitActor data model."""

from datetime import datetime, timezone

import pytest
from hypothesis import given
from pydantic import ValidationError

from auto_release_note_generation.data_models.shared import GitActor

from .conftest import SharedTestConfig
from .test_data import GitTestData
from .test_factories import GitActorFactory
from .test_strategies import HypothesisStrategies


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
        with pytest.raises(ValidationError):
            GitActorFactory.create(name=invalid_name)

    @given(HypothesisStrategies.invalid_emails)
    def test_invalid_email_rejection(self, invalid_email):
        """Test that invalid emails raise ValidationError."""
        with pytest.raises(ValidationError):
            GitActorFactory.create(email=invalid_email)

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
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            default_git_actor.name = "New Name"

        with pytest.raises(ValidationError):
            default_git_actor.email = "new@example.com"

        with pytest.raises(ValidationError):
            default_git_actor.timestamp = datetime.now()

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

    @given(HypothesisStrategies.valid_timestamps)
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
