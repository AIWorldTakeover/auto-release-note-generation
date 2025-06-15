"""Shared test configuration, fixtures, and utilities for data model tests."""

from datetime import datetime, timezone

import pytest

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

    # ChangeMetadata specific defaults
    DEFAULT_CHANGE_TYPE = "direct"
    DEFAULT_SOURCE_BRANCH = "feature/user-auth"
    DEFAULT_TARGET_BRANCH = "main"
    DEFAULT_MERGE_BASE = "abc123def456789abcdef123456789abcdef1230"
    DEFAULT_PULL_REQUEST_ID = "42"

    # ChangeMetadata constants
    VALID_CHANGE_TYPES = [
        "direct",
        "merge",
        "squash",
        "octopus",
        "rebase",
        "cherry-pick",
        "revert",
        "initial",
        "amend",
    ]
    INVALID_CHANGE_TYPES = ["invalid", "", None, "push", "pull", "fetch"]

    TYPICAL_BRANCH_NAMES = [
        "main",
        "master",
        "develop",
        "feature/auth",
        "bugfix/fix-login",
        "hotfix/security-patch",
        "release/v1.2.0",
    ]

    INVALID_BRANCH_NAMES = [
        "",
        "  ",
        "feature with spaces",
        "feature\nwith\nnewlines",
        "feature\twith\ttabs",
        "feature/",
        "/feature",
        "//double-slash",
    ]

    REALISTIC_PR_IDS = ["1", "42", "123", "9999", "PR-001", "pull-request-456"]

    # Test patterns
    MIN_SHA_LENGTH = 4
    MAX_SHA_LENGTH = 64
    TYPICAL_SHORT_SHA_LENGTH = 8
    TYPICAL_FULL_SHA_LENGTH = 40


# =============================================================================
# SHARED TEST UTILITIES - Reusable across all data models
# =============================================================================


class TestHelpers:
    """Helper functions for common test patterns."""

    @staticmethod
    def assert_validation_error_contains(
        error: Exception, expected_messages: list[str]
    ) -> None:
        """Assert that a validation error contains expected messages."""
        error_str = str(error)
        for message in expected_messages:
            assert message in error_str, f"Expected '{message}' in error: {error_str}"

    @staticmethod
    def create_realistic_git_timestamp() -> datetime:
        """Create a realistic Git timestamp with timezone."""
        return datetime(2023, 6, 15, 14, 30, 0, tzinfo=timezone.utc)


# =============================================================================
# FIXTURES - Shared across test classes
# =============================================================================


@pytest.fixture
def default_git_actor():
    """Create a default GitActor instance for testing."""
    from .test_factories import GitActorFactory

    return GitActorFactory.create()


@pytest.fixture
def git_actors_collection():
    """Create a collection of GitActor instances for testing."""
    from .test_factories import GitActorFactory

    return [
        GitActorFactory.create(),
        GitActorFactory.create_with_realistic_email(),
        GitActorFactory.create_corporate_pattern(),
    ]


@pytest.fixture
def default_git_metadata():
    """Create a default GitMetadata instance for testing."""
    from .test_factories import GitMetadataFactory

    return GitMetadataFactory.create()


@pytest.fixture
def git_metadata_collection():
    """Create a collection of GitMetadata instances for testing."""
    from .test_factories import GitMetadataFactory

    return [
        GitMetadataFactory.create(),
        GitMetadataFactory.create_root_commit(),
        GitMetadataFactory.create_regular_commit(),
        GitMetadataFactory.create_merge_commit(),
    ]


@pytest.fixture
def root_commit_metadata():
    """Create GitMetadata for a root commit (no parents)."""
    from .test_factories import GitMetadataFactory

    return GitMetadataFactory.create_root_commit()


@pytest.fixture
def merge_commit_metadata():
    """Create GitMetadata for a merge commit."""
    from .test_factories import GitMetadataFactory

    return GitMetadataFactory.create_merge_commit()


@pytest.fixture
def signed_commit_metadata():
    """Create GitMetadata with GPG signature."""
    from .test_factories import GitMetadataFactory

    return GitMetadataFactory.create_signed_commit()


@pytest.fixture
def commit_type_examples():
    """Create examples of different commit types."""
    from .test_factories import GitMetadataFactory

    return {
        "root": GitMetadataFactory.create_root_commit(),
        "regular": GitMetadataFactory.create_regular_commit(),
        "merge": GitMetadataFactory.create_merge_commit(),
        "octopus": GitMetadataFactory.create_octopus_merge(),
        "signed": GitMetadataFactory.create_signed_commit(),
    }


@pytest.fixture
def default_change_metadata():
    """Create a default ChangeMetadata instance for testing."""
    from .test_factories import ChangeMetadataFactory

    return ChangeMetadataFactory.create()


@pytest.fixture
def change_metadata_collection():
    """Create a collection of ChangeMetadata instances for testing."""
    from .test_factories import ChangeMetadataFactory

    return [
        ChangeMetadataFactory.create(),
        ChangeMetadataFactory.create_direct_change(),
        ChangeMetadataFactory.create_merge_change(),
        ChangeMetadataFactory.create_octopus_change(),
    ]


@pytest.fixture
def direct_change_metadata():
    """Create ChangeMetadata for a direct change."""
    from .test_factories import ChangeMetadataFactory

    return ChangeMetadataFactory.create_direct_change()


@pytest.fixture
def merge_change_metadata():
    """Create ChangeMetadata for a merge change."""
    from .test_factories import ChangeMetadataFactory

    return ChangeMetadataFactory.create_merge_change()


@pytest.fixture
def octopus_change_metadata():
    """Create ChangeMetadata for an octopus merge."""
    from .test_factories import ChangeMetadataFactory

    return ChangeMetadataFactory.create_octopus_change()


@pytest.fixture
def change_type_examples():
    """Create examples of different change types."""
    from .test_factories import ChangeMetadataFactory

    return {
        "direct": ChangeMetadataFactory.create_direct_change(),
        "merge": ChangeMetadataFactory.create_merge_change(),
        "squash": ChangeMetadataFactory.create_squash_change(),
        "octopus": ChangeMetadataFactory.create_octopus_change(),
        "rebase": ChangeMetadataFactory.create_rebase_change(),
        "cherry_pick": ChangeMetadataFactory.create_cherry_pick_change(),
        "revert": ChangeMetadataFactory.create_revert_change(),
        "initial": ChangeMetadataFactory.create_initial_change(),
        "amend": ChangeMetadataFactory.create_amend_change(),
    }
