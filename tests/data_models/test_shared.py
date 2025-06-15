from datetime import datetime, timezone
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from auto_release_note_generation.data_models.shared import (
    ChangeMetadata,
    GitActor,
    GitMetadata,
)

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
    invalid_names = st.one_of(
        st.just(""),
        st.text(min_size=256).filter(lambda x: len(x.strip()) > 255),
        st.just("   "),
    )

    invalid_emails = st.one_of(
        st.just(""),  # Empty string
        st.text(min_size=321).filter(
            lambda x: len(x.strip()) > 320
        ),  # Too long after stripping
        st.just("   "),  # Whitespace only
    )

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
        st.text(min_size=1)
        .filter(lambda x: x.strip())
        .map(
            lambda x: (
                f"-----BEGIN PGP SIGNATURE-----\n{x.strip()}\n"
                "-----END PGP SIGNATURE-----"
            )
        ),
        st.text(min_size=1)
        .filter(lambda x: x.strip())
        .map(lambda x: f"gpgsig {x.strip()}"),
    )

    invalid_gpg_signatures = st.one_of(
        st.just(""),  # Empty string
        st.just("   "),  # Whitespace only
        st.text(min_size=1, max_size=100).filter(
            lambda x: x.strip() and not x.strip().startswith(("-----BEGIN", "gpgsig "))
        ),  # Invalid format
    )

    gpg_signatures = st.one_of(valid_gpg_signatures, invalid_gpg_signatures)

    # ChangeMetadata strategies
    valid_change_types = st.sampled_from(
        [
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
    )

    invalid_change_types = st.one_of(
        st.just(""),  # Empty string
        st.just("invalid"),  # Invalid type
        st.just("push"),  # Not in allowed types
        st.just("pull"),  # Not in allowed types
        st.just("fetch"),  # Not in allowed types
        st.text(min_size=1, max_size=20).filter(
            lambda x: x.strip()
            not in [
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
        ),  # Any other string not in valid types
    )

    valid_branch_names = st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_/."
        ),
    ).filter(
        lambda x: (
            len(x.strip()) > 0
            and not x.startswith("/")
            and not x.endswith("/")
            and "//" not in x
            and not any(c in x for c in [" ", "\t", "\n", "\r"])
        )
    )

    invalid_branch_names = st.one_of(
        st.just(""),  # Empty string
        st.just("  "),  # Whitespace only
        st.text(min_size=1, max_size=50).filter(
            lambda x: (
                " " in x.strip()
                or "\t" in x.strip()
                or "\n" in x.strip()
                or x.strip().startswith("/")
                or x.strip().endswith("/")
                or "//" in x.strip()
                or not x.strip()  # Empty after stripping
            )
        ),  # Invalid characters or patterns that persist after stripping
    )

    # Enhanced source branch list strategies
    empty_source_branches: st.SearchStrategy[list[str]] = st.just([])

    single_source_branch = st.lists(valid_branch_names, min_size=1, max_size=1)

    multiple_source_branches = st.lists(valid_branch_names, min_size=2, max_size=8)

    source_branch_lists = st.one_of(single_source_branch, multiple_source_branches)

    # Reuse empty_source_branches strategy for consistency
    empty_source_branch_lists = empty_source_branches

    # Enhanced PR ID strategies
    valid_pull_request_ids = st.one_of(
        st.none(),
        st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"
            ),
        ).filter(lambda x: len(x.strip()) > 0),
    )

    # Merge base strategies (reuse GitSHA strategies)
    valid_merge_bases = st.one_of(st.none(), valid_git_shas)


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


class ChangeTestData:
    """Test data specific to ChangeMetadata and change-related models."""

    # Real-world change type patterns
    # (change_type, source_branches, target, merge_base, pr_id)
    CHANGE_TYPE_PATTERNS = [
        # Direct commits (no merge)
        ("direct", [], "main", None, None),
        ("direct", [], "develop", None, "456"),
        ("direct", ["main"], "main", None, None),  # Self-targeting direct
        # Simple merges
        ("merge", ["feature/auth"], "main", "abc123def456", "123"),
        ("merge", ["bugfix/login"], "develop", "def456abc789", None),
        ("merge", ["hotfix/security"], "main", "123456abcdef", "urgent-001"),
        # Squash merges
        ("squash", ["feature/refactor"], "main", "123456abcdef", "789"),
        ("squash", ["hotfix/security"], "master", None, "001"),
        ("squash", ["feature/small-change"], "develop", "abcdef123456", "PR-042"),
        # Octopus merges (multiple source branches)
        ("octopus", ["feature/a", "feature/b"], "main", "abcdef123456", "111"),
        ("octopus", ["dev", "staging", "hotfix"], "main", "456789fedcba", None),
        (
            "octopus",
            ["f1", "f2", "f3", "f4"],
            "develop",
            "fedcba987654",
            "complex-merge",
        ),
        # Rebase commits (replayed commits)
        ("rebase", ["feature/branch"], "main", "abc123def456", None),
        ("rebase", [], "develop", None, None),  # Direct rebase
        # Cherry-pick commits (selective commit application)
        ("cherry-pick", ["hotfix/patch"], "main", "def456abc789", None),
        ("cherry-pick", [], "develop", None, "cherry-pick-123"),
        # Revert commits (undoing changes)
        ("revert", ["bad-commit"], "main", "123456abcdef", "revert-456"),
        ("revert", [], "develop", None, None),
        # Initial commits (repository start)
        ("initial", [], "main", None, None),
        ("initial", [], "master", None, None),
        # Amended commits (git commit --amend)
        ("amend", [], "feature/fix", None, None),
        ("amend", ["original-branch"], "main", "abc123def456", "amended-pr"),
    ]

    # Realistic branch name patterns
    COMMON_BRANCHES = ["main", "master", "develop", "staging", "production"]

    FEATURE_BRANCHES = [
        "feature/user-authentication",
        "feature/payment-integration",
        "feature/api-v2",
        "feat/mobile-app",
        "features/dashboard-redesign",
    ]

    BUGFIX_BRANCHES = [
        "bugfix/login-issue",
        "bugfix/memory-leak",
        "fix/security-vulnerability",
        "hotfix/critical-bug",
        "bug/ui-rendering",
    ]

    RELEASE_BRANCHES = [
        "release/v1.0.0",
        "release/v2.1.3",
        "rel/sprint-42",
        "releases/q4-2023",
    ]

    # Corporate patterns
    CORPORATE_BRANCH_PATTERNS = [
        "users/john.doe/experimental-feature",
        "teams/backend/database-migration",
        "releases/sprint-42",
        "environments/staging-deployment",
        "projects/mobile-app/feature-auth",
        "departments/security/audit-fixes",
    ]

    # Edge case patterns
    EDGE_CASE_BRANCH_NAMES = [
        "a",  # Minimum length
        "feature-with-dashes",
        "feature_with_underscores",
        "feature.with.dots",
        "123-numeric-start",
        "CamelCaseBranch",
        "UPPERCASE-BRANCH",
        "mixed-Case_Branch.name",
        "very-long-branch-name-that-tests-maximum-length-handling",
        "release/v1.0.0-rc.1",  # Release candidate with dots and dashes
        "feature/ABC-123-implement-oauth",  # Ticket numbers
        "hotfix/CVE-2024-1234",  # Security vulnerability references
        "users/jane.doe/experimental",  # User-namespaced branches
        "teams/backend/database-migration",  # Team-namespaced branches
        "environments/staging-eu-west",  # Environment branches
        "dependencies/upgrade-node-18",  # Dependency update branches
        "refactor/extract-common-utils",  # Refactoring branches
        "chore/update-github-actions",  # Maintenance branches
        "docs/api-documentation-v2",  # Documentation branches
        "test/integration-test-suite",  # Testing branches
        "build/docker-optimization",  # Build system branches
        "ci/add-security-scanning",  # CI/CD branches
        "perf/optimize-database-queries",  # Performance branches
        "feat/PROJ-456-user-management",  # Feature with project prefix
    ]

    # Unicode and international branch names
    UNICODE_BRANCH_NAMES = [
        "feature/测试",  # Chinese
        "bugfix/тест",  # Russian
        "release/한국어",  # Korean
        "hotfix/العربية",  # Arabic
        "feature/日本語",  # Japanese
    ]

    # Real-world change patterns
    DIRECT_CHANGE_PATTERNS = [
        # Single-branch direct commits
        (["main"], "main"),
        (["develop"], "develop"),
        (["hotfix/critical"], "main"),
    ]

    MERGE_CHANGE_PATTERNS = [
        # Feature merges
        (["feature/auth"], "develop"),
        (["feature/payment", "feature/ui"], "main"),
        (["bugfix/security"], "main"),
    ]

    SQUASH_CHANGE_PATTERNS = [
        # Squash merges common in GitHub workflow
        (["feature/small-fix"], "main"),
        (["fix/typo"], "develop"),
    ]

    OCTOPUS_CHANGE_PATTERNS = [
        # Multi-branch octopus merges
        (["feature/a", "feature/b", "feature/c"], "develop"),
        (["hotfix/p1", "hotfix/p2", "bugfix/minor"], "main"),
    ]

    # Invalid combinations for testing validation
    INVALID_COMBINATIONS = [
        # Empty source branches should fail for merge/squash
        ([], "develop", "merge"),
        ([], "main", "squash"),
        # Single source branch with octopus should fail
        (["feature/single"], "main", "octopus"),
        # Multiple source branches with direct-style changes should fail
        (["feature/a", "feature/b"], "main", "direct"),
        (["feature/a", "feature/b"], "main", "rebase"),
        (["feature/a", "feature/b"], "main", "cherry-pick"),
        (["feature/a", "feature/b"], "main", "revert"),
        (["feature/a", "feature/b"], "main", "amend"),
        # Initial commits with source branches should fail
        (["feature/branch"], "main", "initial"),
        (["main"], "main", "initial"),
    ]

    # Pull request ID patterns
    GITHUB_PR_PATTERNS = ["1", "42", "123", "9999"]
    GITLAB_MR_PATTERNS = ["!1", "!42", "!123"]
    CUSTOM_PR_PATTERNS = ["PR-001", "MR-042", "pull-request-123"]

    # Comprehensive PR ID patterns from various systems
    REALISTIC_PR_IDS = [
        "1",
        "42",
        "123",
        "9999",
        "1234567890",  # Numeric
        "pr-123",
        "PR-456",
        "pull-789",  # Prefixed
        "abc123",
        "gh-456",
        "gl-789",  # Mixed
        "JIRA-123",
        "TICKET-456",
        "ISSUE-789",  # Issue tracker
        "feature-request-001",
        "hotfix-urgent",  # Descriptive
    ]

    # Merge base patterns (SHA where branches diverged)
    MERGE_BASE_PATTERNS = [
        "abc123def456789abcdef123456789abcdef1230",
        "def456abc789def123abc456def789abc123ab",
        "123456789abcdef123456789abcdef123456789",
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


class ChangeMetadataFactory:
    """Factory for creating ChangeMetadata test instances."""

    @staticmethod
    def create(**overrides: Any) -> ChangeMetadata:
        """Create ChangeMetadata with optional field overrides."""
        defaults: dict[str, Any] = {
            "change_type": SharedTestConfig.DEFAULT_CHANGE_TYPE,
            "source_branches": [SharedTestConfig.DEFAULT_SOURCE_BRANCH],
            "target_branch": SharedTestConfig.DEFAULT_TARGET_BRANCH,
            "merge_base": SharedTestConfig.DEFAULT_MERGE_BASE,
            "pull_request_id": SharedTestConfig.DEFAULT_PULL_REQUEST_ID,
        }
        defaults.update(overrides)

        # Adjust source branches based on change type to ensure valid combinations
        change_type = defaults.get("change_type", SharedTestConfig.DEFAULT_CHANGE_TYPE)
        if change_type == "octopus" and len(defaults.get("source_branches", [])) < 2:
            defaults["source_branches"] = ["feature/branch-1", "feature/branch-2"]
        elif change_type == "initial":
            defaults["source_branches"] = []  # Initial commits have no source branches
        elif change_type == "direct" and len(defaults.get("source_branches", [])) > 1:
            defaults["source_branches"] = [defaults["source_branches"][0]]

        return ChangeMetadata(**defaults)

    @staticmethod
    def create_direct_change(
        source_branch: str | None = None, **overrides: Any
    ) -> ChangeMetadata:
        """Create ChangeMetadata for a direct change (single source branch)."""
        branch = source_branch or SharedTestConfig.DEFAULT_SOURCE_BRANCH
        defaults: dict[str, Any] = {
            "change_type": "direct",
            "source_branches": [branch],
            "target_branch": SharedTestConfig.DEFAULT_TARGET_BRANCH,
            "merge_base": None,  # Direct changes don't have merge base
            "pull_request_id": None,  # Direct changes typically don't have PR IDs
        }
        defaults.update(overrides)
        return ChangeMetadata(**defaults)

    @staticmethod
    def create_merge_change(
        source_branch: str | None = None, **overrides: Any
    ) -> ChangeMetadata:
        """Create ChangeMetadata for a merge change (feature branch merge)."""
        branch = source_branch or "feature/new-feature"
        defaults: dict[str, Any] = {
            "change_type": "merge",
            "source_branches": [branch],
            "target_branch": "main",
            "merge_base": SharedTestConfig.DEFAULT_MERGE_BASE,
            "pull_request_id": None,  # Let tests specify PR ID explicitly
        }
        defaults.update(overrides)
        return ChangeMetadataFactory.create(**defaults)

    @staticmethod
    def create_squash_change(
        source_branch: str | None = None, **overrides: Any
    ) -> ChangeMetadata:
        """Create ChangeMetadata for a squash merge (GitHub-style)."""
        branch = source_branch or "feature/small-fix"
        defaults: dict[str, Any] = {
            "change_type": "squash",
            "source_branches": [branch],
            "target_branch": "main",
            "merge_base": SharedTestConfig.DEFAULT_MERGE_BASE,
        }
        defaults.update(overrides)
        return ChangeMetadataFactory.create(**defaults)

    @staticmethod
    def create_octopus_change(
        branch_count: int = 3, **overrides: Any
    ) -> ChangeMetadata:
        """Create ChangeMetadata for an octopus merge (multiple source branches)."""
        if branch_count < 2:
            raise ValueError("Octopus merge requires at least 2 source branches")

        branches = [f"feature/branch-{i}" for i in range(branch_count)]
        defaults: dict[str, Any] = {
            "change_type": "octopus",
            "source_branches": branches,
            "target_branch": "develop",
            "merge_base": SharedTestConfig.DEFAULT_MERGE_BASE,
            "pull_request_id": None,  # Don't include default PR ID
        }
        defaults.update(overrides)
        return ChangeMetadata(**defaults)

    @staticmethod
    def create_github_pr_change(
        pr_id: str | None = None, **overrides: Any
    ) -> ChangeMetadata:
        """Create ChangeMetadata with GitHub PR pattern."""
        pr = pr_id or "42"
        defaults: dict[str, Any] = {
            "change_type": "squash",
            "source_branches": ["feature/github-integration"],
            "target_branch": "main",
            "pull_request_id": pr,
        }
        defaults.update(overrides)
        return ChangeMetadataFactory.create(**defaults)

    @staticmethod
    def create_hotfix_change(**overrides: Any) -> ChangeMetadata:
        """Create ChangeMetadata for a hotfix (direct to main)."""
        defaults: dict[str, Any] = {
            "change_type": "merge",
            "source_branches": ["hotfix/critical-security-fix"],
            "target_branch": "main",
            "merge_base": SharedTestConfig.DEFAULT_MERGE_BASE,
            "pull_request_id": "HOTFIX-001",
        }
        defaults.update(overrides)
        return ChangeMetadataFactory.create(**defaults)

    @staticmethod
    def create_release_change(**overrides: Any) -> ChangeMetadata:
        """Create ChangeMetadata for a release branch merge."""
        defaults: dict[str, Any] = {
            "change_type": "merge",
            "source_branches": ["release/v1.2.0"],
            "target_branch": "main",
            "merge_base": SharedTestConfig.DEFAULT_MERGE_BASE,
        }
        defaults.update(overrides)
        return ChangeMetadataFactory.create(**defaults)

    @staticmethod
    def create_rebase_change(
        source_branch: str | None = None, **overrides: Any
    ) -> ChangeMetadata:
        """Create ChangeMetadata for a rebase operation."""
        branch = source_branch or "feature/rebased-branch"
        defaults: dict[str, Any] = {
            "change_type": "rebase",
            "source_branches": [branch] if branch else [],
            "target_branch": "main",
            "merge_base": SharedTestConfig.DEFAULT_MERGE_BASE,
            "pull_request_id": None,  # Rebases typically don't have PR IDs
        }
        defaults.update(overrides)
        return ChangeMetadataFactory.create(**defaults)

    @staticmethod
    def create_cherry_pick_change(
        source_branch: str | None = None, **overrides: Any
    ) -> ChangeMetadata:
        """Create ChangeMetadata for a cherry-pick operation."""
        branch = source_branch or "hotfix/cherry-picked"
        defaults: dict[str, Any] = {
            "change_type": "cherry-pick",
            "source_branches": [branch] if branch else [],
            "target_branch": "main",
            "merge_base": SharedTestConfig.DEFAULT_MERGE_BASE,
            "pull_request_id": None,
        }
        defaults.update(overrides)
        return ChangeMetadataFactory.create(**defaults)

    @staticmethod
    def create_revert_change(
        source_branch: str | None = None, **overrides: Any
    ) -> ChangeMetadata:
        """Create ChangeMetadata for a revert operation."""
        branch = source_branch or "bad-commit"
        defaults: dict[str, Any] = {
            "change_type": "revert",
            "source_branches": [branch] if branch else [],
            "target_branch": "main",
            "merge_base": SharedTestConfig.DEFAULT_MERGE_BASE,
            "pull_request_id": None,
        }
        defaults.update(overrides)
        return ChangeMetadataFactory.create(**defaults)

    @staticmethod
    def create_initial_change(**overrides: Any) -> ChangeMetadata:
        """Create ChangeMetadata for an initial commit."""
        defaults: dict[str, Any] = {
            "change_type": "initial",
            "source_branches": [],  # Initial commits have no source branches
            "target_branch": "main",
            "merge_base": None,  # No merge base for initial commits
            "pull_request_id": None,
        }
        defaults.update(overrides)
        return ChangeMetadata(**defaults)

    @staticmethod
    def create_amend_change(
        source_branch: str | None = None, **overrides: Any
    ) -> ChangeMetadata:
        """Create ChangeMetadata for an amended commit."""
        branch = source_branch or "feature/amended"
        defaults: dict[str, Any] = {
            "change_type": "amend",
            "source_branches": [branch] if branch else [],
            "target_branch": "feature/amended",  # Often amending on same branch
            "merge_base": None,
            "pull_request_id": None,
        }
        defaults.update(overrides)
        return ChangeMetadataFactory.create(**defaults)

    @staticmethod
    def create_with_pr(pr_id: str | None = None, **overrides: Any) -> ChangeMetadata:
        """Create ChangeMetadata with pull request information."""
        pr = pr_id or SharedTestConfig.DEFAULT_PULL_REQUEST_ID
        defaults: dict[str, Any] = {"pull_request_id": pr}
        defaults.update(overrides)
        return ChangeMetadataFactory.create(**defaults)

    @staticmethod
    def create_corporate_pattern(
        pattern_index: int = 0, **overrides: Any
    ) -> ChangeMetadata:
        """Create ChangeMetadata with corporate naming patterns."""
        target = ChangeTestData.CORPORATE_BRANCH_PATTERNS[
            pattern_index % len(ChangeTestData.CORPORATE_BRANCH_PATTERNS)
        ]
        defaults: dict[str, Any] = {"target_branch": target}
        defaults.update(overrides)
        return ChangeMetadataFactory.create(**defaults)

    @staticmethod
    def create_from_pattern(pattern_name: str, **overrides: Any) -> ChangeMetadata:
        """Create ChangeMetadata from predefined patterns."""
        patterns: dict[str, Any] = {
            "direct": ChangeMetadataFactory.create_direct_change,
            "merge": ChangeMetadataFactory.create_merge_change,
            "squash": ChangeMetadataFactory.create_squash_change,
            "octopus": ChangeMetadataFactory.create_octopus_change,
            "rebase": ChangeMetadataFactory.create_rebase_change,
            "cherry-pick": ChangeMetadataFactory.create_cherry_pick_change,
            "revert": ChangeMetadataFactory.create_revert_change,
            "initial": ChangeMetadataFactory.create_initial_change,
            "amend": ChangeMetadataFactory.create_amend_change,
            "github-pr": ChangeMetadataFactory.create_github_pr_change,
            "hotfix": ChangeMetadataFactory.create_hotfix_change,
            "release": ChangeMetadataFactory.create_release_change,
            "with_pr": ChangeMetadataFactory.create_with_pr,
            "corporate": ChangeMetadataFactory.create_corporate_pattern,
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


@pytest.fixture
def default_change_metadata():
    """Default ChangeMetadata instance for testing."""
    return ChangeMetadataFactory.create()


@pytest.fixture
def change_metadata_collection():
    """Collection of various ChangeMetadata instances for bulk testing."""
    return [
        ChangeMetadataFactory.create_direct_change(),
        ChangeMetadataFactory.create_merge_change(),
        ChangeMetadataFactory.create_squash_change(),
        ChangeMetadataFactory.create_octopus_change(branch_count=3),
        ChangeMetadataFactory.create_rebase_change(),
        ChangeMetadataFactory.create_cherry_pick_change(),
        ChangeMetadataFactory.create_revert_change(),
        ChangeMetadataFactory.create_initial_change(),
        ChangeMetadataFactory.create_amend_change(),
        ChangeMetadataFactory.create_github_pr_change(),
        ChangeMetadataFactory.create_hotfix_change(),
        ChangeMetadataFactory.create_release_change(),
    ]


@pytest.fixture
def direct_change_metadata():
    """ChangeMetadata instance representing a direct change."""
    return ChangeMetadataFactory.create_direct_change()


@pytest.fixture
def merge_change_metadata():
    """ChangeMetadata instance representing a merge change."""
    return ChangeMetadataFactory.create_merge_change()


@pytest.fixture
def octopus_change_metadata():
    """ChangeMetadata instance representing an octopus merge."""
    return ChangeMetadataFactory.create_octopus_change()


@pytest.fixture
def change_type_examples():
    """Dictionary of change types with their metadata instances."""
    return {
        "direct": ChangeMetadataFactory.create_direct_change(),
        "merge": ChangeMetadataFactory.create_merge_change(),
        "squash": ChangeMetadataFactory.create_squash_change(),
        "octopus": ChangeMetadataFactory.create_octopus_change(),
        "rebase": ChangeMetadataFactory.create_rebase_change(),
        "cherry-pick": ChangeMetadataFactory.create_cherry_pick_change(),
        "revert": ChangeMetadataFactory.create_revert_change(),
        "initial": ChangeMetadataFactory.create_initial_change(),
        "amend": ChangeMetadataFactory.create_amend_change(),
        "github-pr": ChangeMetadataFactory.create_github_pr_change(),
        "hotfix": ChangeMetadataFactory.create_hotfix_change(),
        "release": ChangeMetadataFactory.create_release_change(),
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
# CHANGEMETADATA TEST CLASSES - Organized by test category
# =============================================================================


class TestChangeMetadataValidation:
    """Test ChangeMetadata field validation and constraints."""

    @given(
        HypothesisStrategies.valid_change_types,
        HypothesisStrategies.valid_branch_names,
        HypothesisStrategies.valid_merge_bases,
        HypothesisStrategies.valid_pull_request_ids,
    )
    def test_comprehensive_valid_creation(
        self, change_type, target_branch, merge_base, pr_id
    ):
        """Test comprehensive valid creation with all field combinations."""
        # Generate appropriate source branches based on change type
        source_branches: list[str]
        if change_type == "direct":
            source_branches = []
        elif change_type == "initial":
            source_branches = []  # Initial commits have no source branches
        elif change_type == "octopus":
            source_branches = ["branch-1", "branch-2"]
        else:  # merge, squash, rebase, cherry-pick, revert, amend
            source_branches = ["feature-branch"]

        metadata = ChangeMetadata(
            change_type=change_type,
            source_branches=source_branches,
            target_branch=target_branch,
            merge_base=merge_base,
            pull_request_id=pr_id,
        )

        assert metadata.change_type == change_type
        assert metadata.source_branches == source_branches
        assert metadata.target_branch == target_branch.strip()
        assert metadata.merge_base == merge_base
        assert metadata.pull_request_id == (
            pr_id.strip() if pr_id and pr_id.strip() else None
        )

    def test_valid_creation(self):
        """Test that valid inputs create ChangeMetadata successfully."""
        # Test direct change with single source branch
        direct_metadata = ChangeMetadata(
            change_type="direct",
            source_branches=["feature/test"],
            target_branch="main",
        )
        assert direct_metadata.change_type == "direct"
        assert direct_metadata.source_branches == ["feature/test"]

        # Test merge change with single source branch
        merge_metadata = ChangeMetadata(
            change_type="merge",
            source_branches=["feature/test"],
            target_branch="main",
            merge_base="abc123",
        )
        assert merge_metadata.change_type == "merge"

        # Test octopus change with multiple source branches
        octopus_metadata = ChangeMetadata(
            change_type="octopus",
            source_branches=["feature/a", "feature/b"],
            target_branch="main",
            merge_base="abc123",
        )
        assert octopus_metadata.change_type == "octopus"
        assert len(octopus_metadata.source_branches) == 2

    @given(HypothesisStrategies.invalid_change_types)
    def test_invalid_change_type_rejection(self, invalid_type):
        """Test that invalid change types raise ValidationError."""
        TestHelpers.assert_validation_error(
            ChangeMetadataFactory.create,
            field_name="change_type",
            change_type=invalid_type,
        )

    @given(HypothesisStrategies.invalid_branch_names)
    @settings(suppress_health_check=[HealthCheck.filter_too_much])
    def test_invalid_target_branch_rejection(self, invalid_branch):
        """Test that invalid target branches raise ValidationError."""
        TestHelpers.assert_validation_error(
            ChangeMetadataFactory.create,
            field_name="target_branch",
            target_branch=invalid_branch,
        )

    @given(HypothesisStrategies.empty_source_branch_lists)
    def test_empty_source_branches_allowed(self, empty_list):
        """Test that empty source branch lists are allowed."""
        metadata = ChangeMetadataFactory.create(source_branches=empty_list)
        assert metadata.source_branches == []

    @pytest.mark.parametrize(
        ("source_branches", "target_branch", "change_type"),
        ChangeTestData.INVALID_COMBINATIONS,
    )
    def test_invalid_business_logic_combinations(
        self, source_branches, target_branch, change_type
    ):
        """Test that logically invalid combinations are rejected."""
        with pytest.raises((ValidationError, ValueError)):
            ChangeMetadata(
                change_type=change_type,
                source_branches=source_branches,
                target_branch=target_branch,
            )

    def test_whitespace_stripping(self):
        """Test that whitespace is stripped from branch names."""
        metadata = ChangeMetadata(
            change_type="direct",
            source_branches=["  feature/test  "],
            target_branch="  main  ",
        )

        assert metadata.source_branches == ["feature/test"]
        assert metadata.target_branch == "main"


class TestChangeMetadataBehavior:
    """Test ChangeMetadata behavior and constraints."""

    def test_immutability(self, default_change_metadata):
        """Test that ChangeMetadata is immutable after creation."""
        field_updates = {
            "change_type": "merge",
            "source_branches": ["new/branch"],
            "target_branch": "develop",
            "merge_base": "new_sha_123",
            "pull_request_id": "999",
        }

        TestHelpers.assert_model_immutable(default_change_metadata, field_updates)

    def test_string_representation_format(self):
        """Test __str__ returns compact format."""
        # Direct change
        direct = ChangeMetadataFactory.create_direct_change(
            source_branch="feature/auth"
        )
        assert str(direct) == "direct from feature/auth → main"

        # Merge change
        merge = ChangeMetadataFactory.create_merge_change()
        assert str(merge) == "merge from feature/new-feature → main"

        # Multiple branches
        octopus = ChangeMetadataFactory.create_octopus_change(branch_count=3)
        assert str(octopus) == "octopus from 3 branches → develop"

        # With PR ID
        pr_change = ChangeMetadataFactory.create_github_pr_change(pr_id="42")
        assert (
            str(pr_change) == "squash from feature/github-integration → main (PR: 42)"
        )

    def test_string_representation_without_source_branches(self):
        """Test __str__ handles empty source branches."""
        metadata = ChangeMetadata(
            change_type="direct",
            source_branches=[],
            target_branch="main",
        )
        assert str(metadata) == "direct → main"

    @given(
        HypothesisStrategies.valid_change_types,
        HypothesisStrategies.valid_branch_names,
    )
    def test_repr_format(self, change_type, target_branch):
        """Test __repr__ returns detailed representation."""
        # Generate appropriate source branches based on change type
        if change_type == "direct":
            source_branches = ["single-branch"]
        elif change_type == "initial":
            source_branches = []  # Initial commits have no source branches
        elif change_type == "octopus":
            source_branches = ["branch-1", "branch-2"]
        else:  # merge, squash, rebase, cherry-pick, revert, amend
            source_branches = ["feature-branch"]

        metadata = ChangeMetadata(
            change_type=change_type,
            source_branches=source_branches,
            target_branch=target_branch,
        )
        repr_str = repr(metadata)

        assert repr_str.startswith("ChangeMetadata(")
        assert f"change_type='{change_type}'" in repr_str
        assert f"source_branches={source_branches}" in repr_str
        assert f"target_branch='{target_branch.strip()}'" in repr_str

    def test_string_methods_consistency(self, change_metadata_collection):
        """Test that str and repr work consistently across instances."""
        for metadata in change_metadata_collection:
            str_result = str(metadata)
            repr_result = repr(metadata)

            assert isinstance(str_result, str)
            assert len(str_result) > 0
            assert isinstance(repr_result, str)
            assert len(repr_result) > 0


class TestChangeMetadataEdgeCases:
    """Test ChangeMetadata edge cases and boundary conditions."""

    def test_minimum_length_fields(self):
        """Test minimum valid field lengths."""
        metadata = ChangeMetadata(
            change_type="direct",
            source_branches=["a"],
            target_branch="b",
        )

        assert metadata.source_branches == ["a"]
        assert metadata.target_branch == "b"

    def test_maximum_length_fields(self):
        """Test maximum valid field lengths."""
        long_branch = "a" * 100
        metadata = ChangeMetadata(
            change_type="merge",
            source_branches=[long_branch],
            target_branch=long_branch,
        )

        assert metadata.source_branches == [long_branch]
        assert metadata.target_branch == long_branch

    @pytest.mark.parametrize(
        ("source_branches", "target_branch"), ChangeTestData.DIRECT_CHANGE_PATTERNS
    )
    def test_direct_change_patterns(self, source_branches, target_branch):
        """Test direct change patterns from real-world scenarios."""
        metadata = ChangeMetadata(
            change_type="direct",
            source_branches=source_branches,
            target_branch=target_branch,
        )
        assert metadata.change_type == "direct"
        assert len(metadata.source_branches) <= 1

    @pytest.mark.parametrize(
        ("source_branches", "target_branch"), ChangeTestData.MERGE_CHANGE_PATTERNS
    )
    def test_merge_change_patterns(self, source_branches, target_branch):
        """Test merge change patterns from real-world scenarios."""
        metadata = ChangeMetadata(
            change_type="merge",
            source_branches=source_branches,
            target_branch=target_branch,
        )
        assert metadata.change_type == "merge"

    @pytest.mark.parametrize(
        ("source_branches", "target_branch"), ChangeTestData.OCTOPUS_CHANGE_PATTERNS
    )
    def test_octopus_change_patterns(self, source_branches, target_branch):
        """Test octopus merge patterns."""
        metadata = ChangeMetadata(
            change_type="octopus",
            source_branches=source_branches,
            target_branch=target_branch,
        )
        assert metadata.change_type == "octopus"
        assert len(metadata.source_branches) >= 2

    @pytest.mark.parametrize("pr_id", ChangeTestData.GITHUB_PR_PATTERNS)
    def test_github_pr_id_patterns(self, pr_id):
        """Test GitHub PR ID patterns."""
        metadata = ChangeMetadataFactory.create_github_pr_change(pr_id=pr_id)
        assert metadata.pull_request_id == pr_id

    @pytest.mark.parametrize("merge_base", ChangeTestData.MERGE_BASE_PATTERNS)
    def test_merge_base_patterns(self, merge_base):
        """Test merge base SHA patterns."""
        metadata = ChangeMetadataFactory.create_merge_change(merge_base=merge_base)
        assert metadata.merge_base == merge_base

    def test_branch_name_special_characters(self):
        """Test branch names with special characters."""
        special_branches = [
            "feature/user-auth",
            "bugfix/fix-login-issue",
            "release/v1.2.0",
            "hotfix/security.patch",
        ]

        for branch in special_branches:
            metadata = ChangeMetadata(
                change_type="merge",
                source_branches=[branch],
                target_branch="main",
            )
            assert metadata.source_branches == [branch]

    def test_none_optional_fields(self):
        """Test that optional fields can be None."""
        metadata = ChangeMetadata(
            change_type="direct",
            source_branches=["main"],
            target_branch="main",
            merge_base=None,
            pull_request_id=None,
        )

        assert metadata.merge_base is None
        assert metadata.pull_request_id is None

    def test_unicode_branch_names(self):
        """Test branch names with Unicode characters."""
        for branch_name in ChangeTestData.UNICODE_BRANCH_NAMES:
            metadata = ChangeMetadata(
                change_type="merge",
                source_branches=[branch_name],
                target_branch="main",
            )
            assert metadata.source_branches == [branch_name]

    def test_realistic_pr_id_formats(self):
        """Test realistic PR ID formats from various systems."""
        for pr_id in ChangeTestData.REALISTIC_PR_IDS:
            metadata = ChangeMetadataFactory.create_with_pr(pr_id=pr_id)
            assert metadata.pull_request_id == pr_id

    def test_empty_pr_id_normalization(self):
        """Test that empty PR ID becomes None."""
        metadata = ChangeMetadata(
            change_type="direct",
            source_branches=[],
            target_branch="main",
            pull_request_id="",
        )
        assert metadata.pull_request_id is None

        metadata2 = ChangeMetadata(
            change_type="direct",
            source_branches=[],
            target_branch="main",
            pull_request_id="   ",
        )
        assert metadata2.pull_request_id is None

    def test_many_source_branches(self):
        """Test large octopus merges."""
        many_branches = [f"feature/branch-{i}" for i in range(10)]
        metadata = ChangeMetadata(
            change_type="octopus",
            source_branches=many_branches,
            target_branch="main",
        )
        assert len(metadata.source_branches) == 10
        assert metadata.is_octopus_change()

    def test_change_type_patterns_from_test_data(self):
        """Test change type patterns from ChangeTestData."""
        for pattern in ChangeTestData.CHANGE_TYPE_PATTERNS:
            change_type, source_branches, target, merge_base, pr_id = pattern
            metadata = ChangeMetadata(
                change_type=change_type,  # type: ignore[arg-type]
                source_branches=source_branches,
                target_branch=target,
                merge_base=merge_base,
                pull_request_id=pr_id,
            )
            assert metadata.change_type == change_type
            assert metadata.source_branches == source_branches
            assert metadata.target_branch == target


class TestChangeMetadataFactory:
    """Test ChangeMetadataFactory functionality."""

    def test_default_creation(self, default_change_metadata):
        """Test factory creates valid default ChangeMetadata."""
        factory_metadata = ChangeMetadataFactory.create()

        assert factory_metadata.change_type == default_change_metadata.change_type
        assert (
            factory_metadata.source_branches == default_change_metadata.source_branches
        )
        assert factory_metadata.target_branch == default_change_metadata.target_branch

    def test_override_functionality(self):
        """Test factory accepts override values."""
        custom_type = "merge"
        metadata = ChangeMetadataFactory.create(change_type=custom_type)

        assert metadata.change_type == custom_type
        assert metadata.target_branch == SharedTestConfig.DEFAULT_TARGET_BRANCH

    def test_specialized_factory_methods(self):
        """Test specialized factory methods work correctly."""
        # Direct change
        direct = ChangeMetadataFactory.create_direct_change()
        assert direct.change_type == "direct"
        assert len(direct.source_branches) <= 1

        # Merge change
        merge = ChangeMetadataFactory.create_merge_change()
        assert merge.change_type == "merge"
        assert merge.target_branch == "main"

        # Squash change
        squash = ChangeMetadataFactory.create_squash_change()
        assert squash.change_type == "squash"

        # Octopus change
        octopus = ChangeMetadataFactory.create_octopus_change(branch_count=4)
        assert octopus.change_type == "octopus"
        assert len(octopus.source_branches) == 4

        # GitHub PR change
        github_pr = ChangeMetadataFactory.create_github_pr_change()
        assert github_pr.change_type == "squash"
        assert github_pr.pull_request_id is not None

        # Hotfix change
        hotfix = ChangeMetadataFactory.create_hotfix_change()
        assert hotfix.change_type == "merge"
        assert "hotfix" in hotfix.source_branches[0]

        # Release change
        release = ChangeMetadataFactory.create_release_change()
        assert release.change_type == "merge"
        assert "release" in release.source_branches[0]

        # Rebase change
        rebase = ChangeMetadataFactory.create_rebase_change()
        assert rebase.change_type == "rebase"
        assert len(rebase.source_branches) <= 1

        # Cherry-pick change
        cherry_pick = ChangeMetadataFactory.create_cherry_pick_change()
        assert cherry_pick.change_type == "cherry-pick"
        assert len(cherry_pick.source_branches) <= 1

        # Revert change
        revert = ChangeMetadataFactory.create_revert_change()
        assert revert.change_type == "revert"
        assert len(revert.source_branches) <= 1

        # Initial change
        initial = ChangeMetadataFactory.create_initial_change()
        assert initial.change_type == "initial"
        assert len(initial.source_branches) == 0

        # Amend change
        amend = ChangeMetadataFactory.create_amend_change()
        assert amend.change_type == "amend"
        assert len(amend.source_branches) <= 1

    def test_pattern_based_creation(self):
        """Test pattern-based factory usage."""
        patterns = [
            "direct",
            "merge",
            "squash",
            "octopus",
            "rebase",
            "cherry-pick",
            "revert",
            "initial",
            "amend",
            "github-pr",
            "hotfix",
            "release",
        ]

        for pattern in patterns:
            metadata = ChangeMetadataFactory.create_from_pattern(pattern)
            assert isinstance(metadata, ChangeMetadata)

        # Test invalid pattern
        with pytest.raises(ValueError, match="Unknown pattern"):
            ChangeMetadataFactory.create_from_pattern("invalid_pattern")

    @given(HypothesisStrategies.valid_change_types)
    def test_factory_with_hypothesis(self, change_type):
        """Test factory works with hypothesis-generated data."""
        metadata = ChangeMetadataFactory.create(change_type=change_type)
        assert metadata.change_type == change_type

    def test_factory_creates_valid_instances(self, change_metadata_collection):
        """Test that all factory methods create valid instances."""
        for metadata in change_metadata_collection:
            assert isinstance(metadata, ChangeMetadata)
            assert isinstance(metadata.change_type, str)
            assert isinstance(metadata.source_branches, list)
            assert isinstance(metadata.target_branch, str)

            # Test string methods work
            str_result = str(metadata)
            repr_result = repr(metadata)
            assert isinstance(str_result, str)
            assert isinstance(repr_result, str)

    def test_octopus_factory_validation(self):
        """Test octopus factory validates branch count."""
        with pytest.raises(ValueError, match="at least 2 source branches"):
            ChangeMetadataFactory.create_octopus_change(branch_count=1)

        # Valid octopus merge
        octopus = ChangeMetadataFactory.create_octopus_change(branch_count=3)
        assert len(octopus.source_branches) == 3


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
