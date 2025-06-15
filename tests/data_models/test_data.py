"""Test data collections organized by domain."""


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
