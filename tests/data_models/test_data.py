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


class FileTestData:
    """Test data specific to FileModification and Diff models."""

    # Realistic file paths from real-world projects
    REALISTIC_FILE_PATHS = [
        # Standard programming files
        "src/main.py",
        "lib/utils.js",
        "include/header.h",
        "tests/test_file.py",
        "docs/README.md",
        "config/settings.json",
        # Deep nested paths
        "src/auto_release_note_generation/data_models/shared.py",
        "tests/data_models/test_file_diff.py",
        "frontend/src/components/UserProfile/UserProfile.tsx",
        "backend/api/v1/endpoints/users.py",
        # Common web development patterns
        "public/index.html",
        "static/css/main.css",
        "assets/images/logo.png",
        "node_modules/package/dist/index.js",
        # Configuration and build files
        ".github/workflows/ci.yml",
        "docker/Dockerfile",
        "scripts/deploy.sh",
        "Makefile",
        ".gitignore",
        "pyproject.toml",
        "package.json",
        "requirements.txt",
        # Documentation patterns
        "docs/api/endpoints.md",
        "README.rst",
        "CHANGELOG.md",
        "LICENSE",
        "CONTRIBUTING.md",
    ]

    # Unicode and international file paths
    UNICODE_FILE_PATHS = [
        "docs/中文文档.md",
        "src/модуль.py",
        "tests/тест.js",
        "assets/日本語.png",
        "config/설정.json",
        "data/données.csv",
        "scripts/εργαλεία.sh",
        "templates/шаблон.html",
    ]

    # Edge case file paths
    EDGE_CASE_PATHS = [
        # Very short paths
        "a",
        "x.py",
        "1.js",
        # Paths with special characters (valid in Git)
        "file-with-dashes.py",
        "file_with_underscores.js",
        "file.with.dots.md",
        "folder/sub-folder/file-name.ext",
        # Mixed case and numbers
        "CamelCaseFile.Java",
        "UPPER_CASE.SQL",
        "file123.txt",
        "test_file_v2.py",
        # Common prefixes/suffixes
        "test_something.py",
        "something_test.js",
        "TestSomething.java",
        "SomethingTest.cpp",
        "__init__.py",
        "main.go",
        "index.html",
        "style.css",
        # Long but realistic paths
        "very/deep/nested/directory/structure/with/many/levels/final_file.py",
        "src/components/ui/forms/input/types/NumberInput/NumberInput.tsx",
    ]

    # File modification scenarios with realistic patterns
    MODIFICATION_TYPE_SCENARIOS = [
        # Added files - common patterns
        ("A", None, "src/new_feature.py", 50, 0),
        ("A", None, "tests/test_new_feature.py", 25, 0),
        ("A", None, "docs/new_feature.md", 15, 0),
        ("A", None, ".github/workflows/new-ci.yml", 30, 0),
        # Deleted files - common patterns
        ("D", "src/deprecated.py", None, 0, 45),
        ("D", "tests/test_deprecated.py", None, 0, 20),
        ("D", "old_config.json", None, 0, 10),
        ("D", "legacy/old_module.js", None, 0, 150),
        # Modified files - typical changes
        ("M", "src/main.py", "src/main.py", 15, 8),
        ("M", "README.md", "README.md", 5, 2),
        ("M", "package.json", "package.json", 3, 1),
        ("M", "pyproject.toml", "pyproject.toml", 2, 0),
        # Renamed files - common patterns
        ("R", "old_name.py", "new_name.py", 2, 1),
        ("R", "src/module.js", "src/better_module.js", 0, 0),
        ("R", "docs/old_doc.md", "docs/updated_doc.md", 5, 3),
        ("R", "config/dev.json", "config/development.json", 0, 0),
        # Copied files - duplication patterns
        ("C", "src/template.py", "src/new_module.py", 10, 0),
        ("C", "config/base.json", "config/production.json", 5, 0),
        ("C", "tests/base_test.py", "tests/specific_test.py", 20, 5),
        # Type changes - file mode/type changes
        ("T", "scripts/deploy", "scripts/deploy.sh", 1, 0),
        ("T", "config", "config.json", 0, 0),
        # Unmerged files - conflict scenarios
        ("U", "src/conflicted.py", "src/conflicted.py", 10, 5),
        ("U", "config/settings.json", "config/settings.json", 2, 2),
    ]

    # Large diff patterns for performance testing
    LARGE_DIFF_PATTERNS = [
        # Mass file addition (new feature/module)
        {
            "description": "New Python module with tests",
            "modifications": [
                ("A", None, f"src/new_module/file_{i}.py", 20, 0) for i in range(10)
            ]
            + [
                ("A", None, f"tests/new_module/test_file_{i}.py", 15, 0)
                for i in range(10)
            ],
        },
        # Mass file deletion (cleanup/refactor)
        {
            "description": "Legacy code cleanup",
            "modifications": [
                ("D", f"legacy/old_file_{i}.js", None, 0, 30) for i in range(20)
            ],
        },
        # Large refactor (many file modifications)
        {
            "description": "API refactor",
            "modifications": [
                ("M", f"src/api/endpoint_{i}.py", f"src/api/endpoint_{i}.py", 10, 8)
                for i in range(15)
            ]
            + [
                (
                    "M",
                    f"tests/api/test_endpoint_{i}.py",
                    f"tests/api/test_endpoint_{i}.py",
                    5,
                    3,
                )
                for i in range(15)
            ],
        },
        # Mixed operation large diff
        {
            "description": "Major version update",
            "modifications": [
                ("A", None, f"src/v2/new_feature_{i}.py", 25, 0) for i in range(5)
            ]
            + [("D", f"src/v1/old_feature_{i}.py", None, 0, 40) for i in range(8)]
            + [
                ("M", f"src/core/module_{i}.py", f"src/core/module_{i}.py", 15, 12)
                for i in range(12)
            ]
            + [
                ("R", f"src/util_{i}.py", f"src/utils/util_{i}.py", 2, 1)
                for i in range(6)
            ],
        },
    ]

    # Complex rename/move scenarios
    COMPLEX_RENAME_SCENARIOS = [
        # Simple renames
        ("old_file.py", "new_file.py"),
        ("utils.js", "utilities.js"),
        # Directory moves
        ("src/old_module.py", "lib/old_module.py"),
        ("frontend/component.tsx", "src/components/component.tsx"),
        # Extension changes
        ("script", "script.sh"),
        ("README", "README.md"),
        ("config", "config.json"),
        # Complex reorganization
        ("old/path/file.py", "new/structure/file.py"),
        ("legacy/module/submodule.js", "src/refactored/submodule.js"),
        ("tests/old/test_file.py", "tests/unit/test_file.py"),
        # Camel case to snake case
        ("CamelCaseFile.py", "camel_case_file.py"),
        ("SomeComponent.tsx", "some_component.tsx"),
        # Version updates in filenames
        ("api_v1.py", "api_v2.py"),
        ("config_old.json", "config_new.json"),
    ]

    # Patch content examples (simplified to avoid syntax issues)
    REALISTIC_PATCH_EXAMPLES = [
        "@@ -0,0 +1,3 @@\n+def new_function():\n+    pass",
        "@@ -1,3 +1,3 @@\n def function():\n-    old_code\n+    new_code",
        "@@ -10,5 +10,6 @@\n def method():\n-    old_var = 1\n+    new_var = 2",
    ]

    # Binary file patterns (no patch content)
    BINARY_FILE_PATTERNS = [
        ("A", None, "assets/logo.png", 0, 0, None),
        ("A", None, "fonts/font.woff2", 0, 0, None),
        ("D", "old_image.jpg", None, 0, 0, None),
        ("M", "data/file.db", "data/file.db", 0, 0, None),
        ("R", "old_binary", "new_binary.exe", 0, 0, None),
    ]
