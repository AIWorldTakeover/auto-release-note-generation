from datetime import datetime, timezone
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from auto_release_note_generation.data_models.shared import GitActor, GitMetadata

# =============================================================================
# TEST CONFIGURATION & SHARED UTILITIES
# =============================================================================


class SharedTestConfig:
    """Configuration constants for all shared data model tests."""

    DEFAULT_TIMESTAMP = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    DEFAULT_NAME = "John Doe"
    DEFAULT_EMAIL = "john.doe@example.com"

    # GitMetadata specific defaults
    DEFAULT_SHA = "abc123def456789abcdef123456789abcdef1234"
    DEFAULT_SHORT_SHA = "abc12345"
    DEFAULT_PARENT_SHA = "abc123def456789abcdef123456789abcdef1235"
    DEFAULT_GPG_SIGNATURE = None
    DEFAULT_VALID_GPG_SIGNATURE = (
        "-----BEGIN PGP SIGNATURE-----\nVersion: GnuPG v2\n\n"
        "iQIcBAABCAAGBQJhXYZ1AAoJEH8JWXvNOxq+ABC123def456789abcdef123456789\n"
        "=AbC1\n-----END PGP SIGNATURE-----"
    )

    # Test patterns
    MIN_SHA_LENGTH = 4
    MAX_SHA_LENGTH = 64
    TYPICAL_SHORT_SHA_LENGTH = 8
    TYPICAL_FULL_SHA_LENGTH = 40


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

    # GitSHA strategies
    valid_git_shas = st.text(
        min_size=4, max_size=64, alphabet="0123456789abcdef"
    ).filter(lambda x: len(x.strip()) >= 4)

    short_git_shas = st.text(min_size=4, max_size=12, alphabet="0123456789abcdef")

    full_git_shas = st.text(min_size=40, max_size=40, alphabet="0123456789abcdef")

    invalid_git_shas = st.one_of(
        st.just(""),  # Empty string
        st.text(min_size=1, max_size=3),  # Too short
        st.text(min_size=65, max_size=100),  # Too long
        st.text(
            min_size=4,
            max_size=64,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll"),
                blacklist_characters="abcdef0123456789",
            ),
        ),  # Invalid characters
    )

    # Parent SHA list strategies
    empty_parent_list: st.SearchStrategy[list[str]] = st.just([])

    single_parent_list: st.SearchStrategy[list[str]] = st.lists(
        st.text(min_size=4, max_size=40, alphabet="0123456789abcdef"),
        min_size=1,
        max_size=1,
    )

    merge_parent_list: st.SearchStrategy[list[str]] = st.lists(
        st.text(min_size=4, max_size=40, alphabet="0123456789abcdef"),
        min_size=2,
        max_size=8,
    )

    parent_sha_lists = st.one_of(
        empty_parent_list, single_parent_list, merge_parent_list
    )

    # GPG signature strategies
    valid_gpg_signatures = st.one_of(
        st.none(),
        st.text(min_size=1).map(
            lambda x: f"-----BEGIN PGP SIGNATURE-----\n{x}\n-----END PGP SIGNATURE-----"
        ),
        st.text(min_size=1).map(lambda x: f"gpgsig {x}"),
    )

    invalid_gpg_signatures = st.one_of(
        st.just(""),  # Empty string
        st.just("   "),  # Whitespace only
        st.text(min_size=1, max_size=100).filter(
            lambda x: x.strip() and not x.strip().startswith(("-----BEGIN", "gpgsig "))
        ),  # Invalid format
    )

    gpg_signatures = st.one_of(valid_gpg_signatures, invalid_gpg_signatures)


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

    # SHA patterns from real Git repositories
    REALISTIC_SHA_PATTERNS = [
        "a1b2c3d4",  # 8-char short SHA
        "1234567890abcdef",  # 16-char SHA
        "abc123def456789abcdef123456789abcdef1234",  # Full 40-char SHA
        "fedcba9876543210fedcba9876543210fedcba98",  # Different pattern
        "0000000000000000000000000000000000000000",  # All zeros (edge case)
        "ffffffffffffffffffffffffffffffffffffffff",  # All f's (edge case)
    ]

    # Parent combinations for different commit types
    ROOT_COMMIT_PATTERNS: list[list[str]] = [
        [],  # No parents
    ]

    REGULAR_COMMIT_PATTERNS = [
        ["abc123def456789abcdef123456789abcdef1234"],  # Single parent
    ]

    MERGE_COMMIT_PATTERNS = [
        # Simple merge (2 parents)
        [
            "abc123def456789abcdef123456789abcdef1234",
            "def456abc789def123abc456def789abc123de",
        ],
        # Complex merge (3+ parents - octopus merge)
        ["abc123def456", "def456abc789", "123456789abc"],
        ["abcdef", "123456", "fedcba", "654321", "abcabc"],
    ]

    # GPG signature test patterns
    GPG_SIGNATURE_PATTERNS = [
        None,  # Unsigned
        "mock_signature_1",  # Basic signature
        (
            "-----BEGIN PGP SIGNATURE-----\nmock\n-----END PGP SIGNATURE-----"
        ),  # Realistic format
    ]

    # Author/Committer relationship patterns
    AUTHOR_COMMITTER_PATTERNS = [
        # Same person
        ("John Doe", "john@example.com", "John Doe", "john@example.com"),
        # Different people (common in open source)
        ("Jane Author", "jane@author.com", "Bob Committer", "bob@maintainer.com"),
        # Corporate patterns
        ("Developer", "dev@company.com", "Build System", "build@ci.company.com"),
    ]


# =============================================================================
# FACTORY FUNCTIONS - One per data model class
# =============================================================================


class GitActorFactory:
    """Factory for creating GitActor test instances."""

    @staticmethod
    def create(**overrides: Any) -> GitActor:
        """Create GitActor with optional field overrides."""
        defaults: dict[str, Any] = {
            "name": SharedTestConfig.DEFAULT_NAME,
            "email": SharedTestConfig.DEFAULT_EMAIL,
            "timestamp": SharedTestConfig.DEFAULT_TIMESTAMP,
        }
        defaults.update(overrides)
        return GitActor(**defaults)

    @staticmethod
    def create_with_realistic_email(email_index: int = 0) -> GitActor:
        """Create GitActor with Git-realistic email."""
        email = GitTestData.REALISTIC_EMAILS[
            email_index % len(GitTestData.REALISTIC_EMAILS)
        ]
        return GitActorFactory.create(email=email)

    @staticmethod
    def create_corporate_pattern(pattern_index: int = 0) -> GitActor:
        """Create GitActor with corporate Git pattern."""
        name, email = GitTestData.CORPORATE_PATTERNS[
            pattern_index % len(GitTestData.CORPORATE_PATTERNS)
        ]
        return GitActorFactory.create(name=name, email=email)


class GitMetadataFactory:
    """Factory for creating GitMetadata test instances."""

    @staticmethod
    def create(**overrides: Any) -> GitMetadata:
        """Create GitMetadata with optional field overrides."""
        defaults: dict[str, Any] = {
            "sha": SharedTestConfig.DEFAULT_SHA,
            "author": GitActorFactory.create(),
            "committer": GitActorFactory.create(),
            "parents": [],
            "gpg_signature": SharedTestConfig.DEFAULT_GPG_SIGNATURE,
        }
        defaults.update(overrides)
        return GitMetadata(**defaults)

    @staticmethod
    def create_root_commit(**overrides: Any) -> GitMetadata:
        """Create GitMetadata for a root commit (no parents)."""
        defaults: dict[str, Any] = {"parents": []}
        defaults.update(overrides)
        return GitMetadataFactory.create(**defaults)

    @staticmethod
    def create_regular_commit(
        parent_sha: str | None = None, **overrides: Any
    ) -> GitMetadata:
        """Create GitMetadata for a regular commit (single parent)."""
        parent = parent_sha or SharedTestConfig.DEFAULT_PARENT_SHA
        defaults: dict[str, Any] = {"parents": [parent]}
        defaults.update(overrides)
        return GitMetadataFactory.create(**defaults)

    @staticmethod
    def create_merge_commit(parent_count: int = 2, **overrides: Any) -> GitMetadata:
        """Create GitMetadata for a merge commit with specified parent count."""
        parents = [f"{i:040x}" for i in range(parent_count)]  # Generate valid hex SHAs
        defaults: dict[str, Any] = {"parents": parents}
        defaults.update(overrides)
        return GitMetadataFactory.create(**defaults)

    @staticmethod
    def create_octopus_merge(parent_count: int = 5, **overrides: Any) -> GitMetadata:
        """Create GitMetadata for an octopus merge (3+ parents)."""
        if parent_count < 3:
            raise ValueError("Octopus merge requires at least 3 parents")
        return GitMetadataFactory.create_merge_commit(parent_count, **overrides)

    @staticmethod
    def create_signed_commit(
        signature: str | None = None, **overrides: Any
    ) -> GitMetadata:
        """Create GitMetadata with GPG signature."""
        if signature is None:
            signature = SharedTestConfig.DEFAULT_VALID_GPG_SIGNATURE
        defaults: dict[str, Any] = {"gpg_signature": signature}
        defaults.update(overrides)
        return GitMetadataFactory.create(**defaults)

    @staticmethod
    def create_with_different_author_committer(**overrides: Any) -> GitMetadata:
        """Create GitMetadata where author != committer."""
        author = GitActorFactory.create(
            name="Original Author", email="author@example.com"
        )
        committer = GitActorFactory.create(
            name="Code Maintainer",
            email="maintainer@example.com",
            timestamp=SharedTestConfig.DEFAULT_TIMESTAMP,
        )
        defaults: dict[str, Any] = {"author": author, "committer": committer}
        defaults.update(overrides)
        return GitMetadataFactory.create(**defaults)

    @staticmethod
    def create_from_pattern(pattern_name: str, **overrides: Any) -> GitMetadata:
        """Create GitMetadata from predefined patterns."""
        patterns: dict[str, Any] = {
            "root": GitMetadataFactory.create_root_commit,
            "regular": GitMetadataFactory.create_regular_commit,
            "merge": GitMetadataFactory.create_merge_commit,
            "octopus": GitMetadataFactory.create_octopus_merge,
            "signed": GitMetadataFactory.create_signed_commit,
        }

        if pattern_name not in patterns:
            raise ValueError(f"Unknown pattern: {pattern_name}")

        return patterns[pattern_name](**overrides)


# =============================================================================
# SHARED TEST UTILITIES - Reusable across all data models
# =============================================================================


class TestHelpers:
    """Helper functions for common test patterns."""

    @staticmethod
    def assert_validation_error(
        factory_func: Any, field_name: str | None = None, **kwargs: Any
    ) -> ValidationError:
        """Assert ValidationError is raised with optional field checking."""
        with pytest.raises(ValidationError) as exc_info:
            factory_func(**kwargs)

        if field_name:
            error_fields = [error["loc"][0] for error in exc_info.value.errors()]
            assert field_name in error_fields

        return exc_info.value

    @staticmethod
    def assert_model_immutable(
        model_instance: Any, field_updates: dict[str, Any]
    ) -> None:
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


@pytest.fixture
def default_git_metadata():
    """Default GitMetadata instance for testing."""
    return GitMetadataFactory.create()


@pytest.fixture
def git_metadata_collection():
    """Collection of various GitMetadata instances for bulk testing."""
    return [
        GitMetadataFactory.create_root_commit(),
        GitMetadataFactory.create_regular_commit(),
        GitMetadataFactory.create_merge_commit(parent_count=2),
        GitMetadataFactory.create_octopus_merge(parent_count=4),
        GitMetadataFactory.create_signed_commit(),
        GitMetadataFactory.create_with_different_author_committer(),
    ]


@pytest.fixture
def root_commit_metadata():
    """GitMetadata instance representing a root commit."""
    return GitMetadataFactory.create_root_commit()


@pytest.fixture
def merge_commit_metadata():
    """GitMetadata instance representing a merge commit."""
    return GitMetadataFactory.create_merge_commit()


@pytest.fixture
def signed_commit_metadata():
    """GitMetadata instance with GPG signature."""
    return GitMetadataFactory.create_signed_commit()


@pytest.fixture
def commit_type_examples():
    """Dictionary of commit types with their metadata instances."""
    return {
        "root": GitMetadataFactory.create_root_commit(),
        "regular": GitMetadataFactory.create_regular_commit(),
        "merge": GitMetadataFactory.create_merge_commit(),
        "octopus": GitMetadataFactory.create_octopus_merge(),
        "signed": GitMetadataFactory.create_signed_commit(),
    }


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
# GITMETADATA TEST CLASSES - Organized by test category
# =============================================================================


class TestGitMetadataValidation:
    """Test GitMetadata field validation and constraints."""

    @given(
        HypothesisStrategies.valid_git_shas,
        HypothesisStrategies.parent_sha_lists,
        HypothesisStrategies.valid_gpg_signatures,
    )
    def test_valid_creation(self, sha, parents, gpg_signature):
        """Test that valid inputs create GitMetadata successfully."""
        author = GitActorFactory.create()
        committer = GitActorFactory.create()

        metadata = GitMetadata(
            sha=sha,
            author=author,
            committer=committer,
            parents=parents,
            gpg_signature=gpg_signature,
        )

        assert metadata.sha == sha
        assert metadata.author == author
        assert metadata.committer == committer
        assert metadata.parents == parents
        assert metadata.gpg_signature == gpg_signature

    @given(HypothesisStrategies.invalid_git_shas)
    def test_invalid_sha_rejection(self, invalid_sha):
        """Test that invalid SHAs raise ValidationError."""
        # Skip cases that are actually valid hex but uppercase
        if invalid_sha and all(c in "0123456789ABCDEFabcdef" for c in invalid_sha):
            return  # Skip valid hex strings

        TestHelpers.assert_validation_error(
            GitMetadataFactory.create, field_name="sha", sha=invalid_sha
        )

    def test_required_fields_validation(self):
        """Test that required fields raise ValidationError when missing."""
        with pytest.raises(ValidationError):
            GitMetadata()  # type: ignore[call-arg] # Missing all required fields

        with pytest.raises(ValidationError):
            GitMetadata(sha="abc123")  # type: ignore[call-arg] # Missing author, committer

    def test_author_committer_validation(self):
        """Test that author and committer must be valid GitActor instances."""
        TestHelpers.assert_validation_error(
            GitMetadataFactory.create, field_name="author", author="invalid_author"
        )

        TestHelpers.assert_validation_error(
            GitMetadataFactory.create, field_name="committer", committer=123
        )

    def test_parents_list_validation(self):
        """Test that parent SHA list validation works correctly."""
        # Valid parent lists should work
        valid_parents = ["abc123", "def456"]
        metadata = GitMetadataFactory.create(parents=valid_parents)
        assert metadata.parents == valid_parents

        # Invalid parent SHAs should be rejected
        with pytest.raises(ValidationError):
            GitMetadataFactory.create(parents=["invalid-sha-with-dashes"])

    @given(HypothesisStrategies.invalid_gpg_signatures)
    def test_gpg_signature_validation(self, invalid_signature):
        """Test that invalid GPG signatures are rejected."""
        if invalid_signature == "" or invalid_signature == "   ":
            # Empty string and whitespace should become None
            metadata = GitMetadataFactory.create(gpg_signature=invalid_signature)
            assert metadata.gpg_signature is None
        else:
            TestHelpers.assert_validation_error(
                GitMetadataFactory.create,
                field_name="gpg_signature",
                gpg_signature=invalid_signature,
            )


class TestGitMetadataBehavior:
    """Test GitMetadata behavior and constraints."""

    def test_immutability(self, default_git_metadata):
        """Test that GitMetadata is immutable after creation."""
        field_updates = {
            "sha": "new_sha_123",
            "author": GitActorFactory.create(name="New Author"),
            "committer": GitActorFactory.create(name="New Committer"),
            "parents": ["new_parent"],
            "gpg_signature": "new_signature",
        }

        TestHelpers.assert_model_immutable(default_git_metadata, field_updates)

    @pytest.mark.parametrize(
        ("parent_count", "expected_merge", "expected_root"),
        [
            (0, False, True),  # Root commit
            (1, False, False),  # Regular commit
            (2, True, False),  # Merge commit
            (3, True, False),  # Octopus merge
        ],
    )
    def test_commit_type_detection(self, parent_count, expected_merge, expected_root):
        """Test is_merge_commit and is_root_commit methods."""
        parents = [f"{i:040x}" for i in range(parent_count)]
        metadata = GitMetadataFactory.create(parents=parents)

        assert metadata.is_merge_commit() == expected_merge
        assert metadata.is_root_commit() == expected_root

    def test_string_representation_format(self):
        """Test __str__ returns compact format."""
        # Root commit
        root_commit = GitMetadataFactory.create_root_commit(sha="abc12345def67890")
        assert str(root_commit) == "abc12345 (root)"

        # Single parent
        single_parent = GitMetadataFactory.create_regular_commit(
            sha="def12345abc67890", parent_sha="abc123def456"
        )
        assert str(single_parent) == "def12345 (parent: abc123de)"

        # Merge commit
        merge_commit = GitMetadataFactory.create_merge_commit(
            sha="abc12345def67890", parent_count=3
        )
        assert str(merge_commit) == "abc12345 (3 parents)"

    def test_string_representation_with_gpg(self):
        """Test __str__ includes GPG signature indicator."""
        signed_commit = GitMetadataFactory.create_signed_commit(sha="abc12345def67890")
        result = str(signed_commit)
        assert "[signed]" in result
        assert "abc12345" in result

    def test_repr_format(self, default_git_metadata):
        """Test __repr__ returns detailed representation."""
        repr_str = repr(default_git_metadata)

        assert repr_str.startswith("GitMetadata(")
        assert f"sha='{default_git_metadata.sha}'" in repr_str
        assert "author=" in repr_str
        assert "committer=" in repr_str
        assert "parents=" in repr_str
        assert "gpg_signature=" in repr_str


class TestGitMetadataEdgeCases:
    """Test GitMetadata edge cases and boundary conditions."""

    def test_minimum_sha_length(self):
        """Test minimum valid SHA length (4 characters)."""
        metadata = GitMetadataFactory.create(sha="a1b2")
        assert metadata.sha == "a1b2"

    def test_maximum_sha_length(self):
        """Test maximum valid SHA length (64 characters)."""
        long_sha = "a" * 64
        metadata = GitMetadataFactory.create(sha=long_sha)
        assert metadata.sha == long_sha

    @pytest.mark.parametrize("sha", GitTestData.REALISTIC_SHA_PATTERNS)
    def test_realistic_sha_patterns(self, sha):
        """Test SHA patterns from real Git repositories."""
        metadata = GitMetadataFactory.create(sha=sha)
        assert metadata.sha == sha

    @pytest.mark.parametrize("parents", GitTestData.MERGE_COMMIT_PATTERNS)
    def test_complex_merge_patterns(self, parents):
        """Test complex merge scenarios including octopus merges."""
        metadata = GitMetadataFactory.create(parents=parents)
        if len(parents) == 0:
            assert metadata.is_root_commit()
        elif len(parents) == 1:
            assert not metadata.is_merge_commit()
            assert not metadata.is_root_commit()
        else:
            assert metadata.is_merge_commit()
        assert len(metadata.parents) == len(parents)

    def test_empty_parent_list_default(self):
        """Test that parents defaults to empty list."""
        metadata = GitMetadata(
            sha="abc123",
            author=GitActorFactory.create(),
            committer=GitActorFactory.create(),
        )
        assert metadata.parents == []
        assert metadata.is_root_commit()

    def test_same_author_committer(self):
        """Test behavior when author and committer are the same person."""
        actor = GitActorFactory.create()
        metadata = GitMetadataFactory.create(author=actor, committer=actor)

        assert metadata.author == metadata.committer
        # Note: Pydantic creates separate instances even when passed the same object

    def test_large_parent_list(self):
        """Test handling of commits with many parents (octopus merge)."""
        many_parents = [f"{i:040x}" for i in range(8)]
        metadata = GitMetadataFactory.create(parents=many_parents)

        assert metadata.is_merge_commit()
        assert len(metadata.parents) == 8
        assert "8 parents" in str(metadata)

    @given(st.integers(min_value=0, max_value=10))
    def test_parent_count_behavior(self, parent_count):
        """Test behavior with various parent counts."""
        parents = [f"{i:040x}" for i in range(parent_count)]
        metadata = GitMetadataFactory.create(parents=parents)

        if parent_count == 0:
            assert metadata.is_root_commit()
            assert not metadata.is_merge_commit()
        elif parent_count == 1:
            assert not metadata.is_root_commit()
            assert not metadata.is_merge_commit()
        else:
            assert not metadata.is_root_commit()
            assert metadata.is_merge_commit()


class TestGitMetadataFactory:
    """Test GitMetadataFactory functionality."""

    def test_default_creation(self, default_git_metadata):
        """Test factory creates valid default GitMetadata."""
        factory_metadata = GitMetadataFactory.create()

        assert factory_metadata.sha == default_git_metadata.sha
        assert isinstance(factory_metadata.author, GitActor)
        assert isinstance(factory_metadata.committer, GitActor)
        assert factory_metadata.parents == []

    def test_override_functionality(self):
        """Test factory accepts override values."""
        custom_sha = "abc123456789"
        metadata = GitMetadataFactory.create(sha=custom_sha)

        assert metadata.sha == custom_sha
        assert metadata.author.name == SharedTestConfig.DEFAULT_NAME

    def test_specialized_factory_methods(self):
        """Test specialized factory methods work correctly."""
        # Root commit
        root = GitMetadataFactory.create_root_commit()
        assert root.is_root_commit()
        assert not root.is_merge_commit()

        # Regular commit
        regular = GitMetadataFactory.create_regular_commit()
        assert not regular.is_root_commit()
        assert not regular.is_merge_commit()
        assert len(regular.parents) == 1

        # Merge commit
        merge = GitMetadataFactory.create_merge_commit(parent_count=3)
        assert merge.is_merge_commit()
        assert not merge.is_root_commit()
        assert len(merge.parents) == 3

        # Octopus merge
        octopus = GitMetadataFactory.create_octopus_merge(parent_count=5)
        assert octopus.is_merge_commit()
        assert len(octopus.parents) == 5

        # Signed commit
        signed = GitMetadataFactory.create_signed_commit()
        assert signed.gpg_signature is not None

    def test_pattern_based_creation(self):
        """Test pattern-based factory usage."""
        patterns = ["root", "regular", "merge", "octopus", "signed"]

        for pattern in patterns:
            metadata = GitMetadataFactory.create_from_pattern(pattern)
            assert isinstance(metadata, GitMetadata)

        # Test invalid pattern
        with pytest.raises(ValueError, match="Unknown pattern"):
            GitMetadataFactory.create_from_pattern("invalid_pattern")

    @given(HypothesisStrategies.valid_git_shas)
    def test_factory_with_hypothesis(self, sha):
        """Test factory works with hypothesis-generated data."""
        metadata = GitMetadataFactory.create(sha=sha)
        assert metadata.sha == sha

    def test_factory_creates_valid_instances(self, git_metadata_collection):
        """Test that all factory methods create valid instances."""
        for metadata in git_metadata_collection:
            assert isinstance(metadata, GitMetadata)
            assert isinstance(metadata.sha, str)
            assert isinstance(metadata.author, GitActor)
            assert isinstance(metadata.committer, GitActor)
            assert isinstance(metadata.parents, list)

            # Test string methods work
            str_result = str(metadata)
            repr_result = repr(metadata)
            assert isinstance(str_result, str)
            assert isinstance(repr_result, str)


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
