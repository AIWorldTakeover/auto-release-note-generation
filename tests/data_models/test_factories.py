"""Factory classes for creating test data instances."""

from collections.abc import Callable
from typing import Any

from auto_release_note_generation.data_models.shared import (
    ChangeMetadata,
    Diff,
    FileModification,
    GitActor,
    GitMetadata,
)

from .conftest import SharedTestConfig
from .test_data import FileTestData, GitTestData


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
            "merge_base": None,  # Initial commits have no merge base
            "pull_request_id": None,  # Initial commits have no PR
        }
        defaults.update(overrides)
        return ChangeMetadata(**defaults)

    @staticmethod
    def create_amend_change(**overrides: Any) -> ChangeMetadata:
        """Create ChangeMetadata for an amended commit."""
        defaults: dict[str, Any] = {
            "change_type": "amend",
            "source_branches": [],
            "target_branch": "feature/fix",
            "merge_base": None,
            "pull_request_id": None,
        }
        defaults.update(overrides)
        return ChangeMetadata(**defaults)

    @staticmethod
    def create_from_pattern(pattern_name: str, **overrides: Any) -> ChangeMetadata:
        """Create ChangeMetadata based on a pattern name."""
        pattern_mapping: dict[str, Callable[..., ChangeMetadata]] = {
            "direct": ChangeMetadataFactory.create_direct_change,
            "merge": ChangeMetadataFactory.create_merge_change,
            "squash": ChangeMetadataFactory.create_squash_change,
            "octopus": lambda **kwargs: ChangeMetadataFactory.create_octopus_change(
                branch_count=kwargs.pop("branch_count", 3), **kwargs
            ),
            "rebase": ChangeMetadataFactory.create_rebase_change,
            "cherry-pick": ChangeMetadataFactory.create_cherry_pick_change,
            "revert": ChangeMetadataFactory.create_revert_change,
            "initial": ChangeMetadataFactory.create_initial_change,
            "amend": ChangeMetadataFactory.create_amend_change,
            "github-pr": lambda **kwargs: ChangeMetadataFactory.create_squash_change(
                pull_request_id="123", **kwargs
            ),
            "hotfix": lambda **kwargs: ChangeMetadataFactory.create_direct_change(
                source_branch="hotfix/security-patch", **kwargs
            ),
            "release": lambda **kwargs: ChangeMetadataFactory.create_merge_change(
                source_branch="release/v1.0.0", **kwargs
            ),
        }

        if pattern_name not in pattern_mapping:
            raise ValueError(f"Unknown pattern: {pattern_name}")

        factory_func = pattern_mapping[pattern_name]
        return factory_func(**overrides)


class FileModificationFactory:
    """Factory for creating FileModification test instances."""

    @staticmethod
    def create(**overrides: Any) -> "FileModification":
        """Create FileModification with optional field overrides."""
        from auto_release_note_generation.data_models.shared import FileModification

        defaults: dict[str, Any] = {
            "path_after": "src/file.py",
            "modification_type": "M",
            "insertions": 5,
            "deletions": 3,
            "path_before": "src/file.py",
        }
        defaults.update(overrides)
        return FileModification(**defaults)

    @staticmethod
    def create_added_file(**overrides: Any) -> "FileModification":
        """Create FileModification for an added file."""
        from auto_release_note_generation.data_models.shared import FileModification

        defaults: dict[str, Any] = {
            "path_before": None,
            "path_after": "src/new_file.py",
            "modification_type": "A",
            "insertions": 10,
            "deletions": 0,
        }
        defaults.update(overrides)
        return FileModification(**defaults)

    @staticmethod
    def create_deleted_file(**overrides: Any) -> "FileModification":
        """Create FileModification for a deleted file."""
        from auto_release_note_generation.data_models.shared import FileModification

        defaults: dict[str, Any] = {
            "path_before": "src/old_file.py",
            "path_after": None,
            "modification_type": "D",
            "insertions": 0,
            "deletions": 15,
        }
        defaults.update(overrides)
        return FileModification(**defaults)

    @staticmethod
    def create_modified_file(**overrides: Any) -> "FileModification":
        """Create FileModification for a modified file."""
        from auto_release_note_generation.data_models.shared import FileModification

        defaults: dict[str, Any] = {
            "path_before": "src/file.py",
            "path_after": "src/file.py",
            "modification_type": "M",
            "insertions": 8,
            "deletions": 5,
        }
        defaults.update(overrides)
        return FileModification(**defaults)

    @staticmethod
    def create_renamed_file(**overrides: Any) -> "FileModification":
        """Create FileModification for a renamed file."""
        from auto_release_note_generation.data_models.shared import FileModification

        defaults: dict[str, Any] = {
            "path_before": "src/old_name.py",
            "path_after": "src/new_name.py",
            "modification_type": "R",
            "insertions": 2,
            "deletions": 1,
        }
        defaults.update(overrides)
        return FileModification(**defaults)

    @staticmethod
    def create_copied_file(**overrides: Any) -> "FileModification":
        """Create FileModification for a copied file."""
        from auto_release_note_generation.data_models.shared import FileModification

        defaults: dict[str, Any] = {
            "path_before": "src/template.py",
            "path_after": "src/copy.py",
            "modification_type": "C",
            "insertions": 5,
            "deletions": 0,
        }
        defaults.update(overrides)
        return FileModification(**defaults)

    @staticmethod
    def create_with_realistic_path(
        path_index: int = 0, **overrides: Any
    ) -> "FileModification":
        """Create FileModification with realistic file path."""
        path = FileTestData.REALISTIC_FILE_PATHS[
            path_index % len(FileTestData.REALISTIC_FILE_PATHS)
        ]
        return FileModificationFactory.create_modified_file(
            path_before=path, path_after=path, **overrides
        )

    @staticmethod
    def create_from_scenario(
        scenario_index: int = 0, **overrides: Any
    ) -> "FileModification":
        """Create FileModification from realistic scenario."""
        scenario = FileTestData.MODIFICATION_TYPE_SCENARIOS[
            scenario_index % len(FileTestData.MODIFICATION_TYPE_SCENARIOS)
        ]
        mod_type, path_before, path_after, insertions, deletions = scenario

        defaults: dict[str, Any] = {
            "modification_type": mod_type,
            "path_before": path_before,
            "path_after": path_after,
            "insertions": insertions,
            "deletions": deletions,
        }
        defaults.update(overrides)
        return FileModificationFactory.create(**defaults)

    @staticmethod
    def create_with_unicode_path(**overrides: Any) -> "FileModification":
        """Create FileModification with Unicode file path."""
        path = FileTestData.UNICODE_FILE_PATHS[0]
        return FileModificationFactory.create_modified_file(
            path_before=path, path_after=path, **overrides
        )


class DiffFactory:
    """Factory for creating Diff test instances."""

    @staticmethod
    def create(**overrides: Any) -> "Diff":
        """Create Diff with optional field overrides."""
        from auto_release_note_generation.data_models.shared import Diff

        mod = FileModificationFactory.create_modified_file()
        defaults: dict[str, Any] = {
            "modifications": [mod],
            "files_changed_count": 1,
            "insertions_count": mod.insertions,
            "deletions_count": mod.deletions,
            "affected_paths": [(mod.path_before, mod.path_after)],
        }
        defaults.update(overrides)
        return Diff(**defaults)

    @staticmethod
    def create_empty(**overrides: Any) -> "Diff":
        """Create empty Diff."""
        from auto_release_note_generation.data_models.shared import Diff

        defaults: dict[str, Any] = {
            "modifications": [],
            "files_changed_count": 0,
            "insertions_count": 0,
            "deletions_count": 0,
            "affected_paths": [],
        }
        defaults.update(overrides)
        return Diff(**defaults)

    @staticmethod
    def create_single_file(**overrides: Any) -> "Diff":
        """Create Diff with single file modification."""
        from auto_release_note_generation.data_models.shared import Diff

        mod = FileModificationFactory.create_added_file()
        defaults: dict[str, Any] = {
            "modifications": [mod],
            "files_changed_count": 1,
            "insertions_count": mod.insertions,
            "deletions_count": mod.deletions,
            "affected_paths": [(mod.path_before, mod.path_after)],
        }
        defaults.update(overrides)
        return Diff(**defaults)

    @staticmethod
    def create_multi_file(file_count: int = 3, **overrides: Any) -> "Diff":
        """Create Diff with multiple file modifications."""
        from auto_release_note_generation.data_models.shared import Diff

        modifications = []
        total_insertions = 0
        total_deletions = 0
        affected_paths = []

        for i in range(file_count):
            mod = FileModificationFactory.create_modified_file(
                path_before=f"src/file_{i}.py",
                path_after=f"src/file_{i}.py",
                insertions=5 + i,
                deletions=2 + i,
            )
            modifications.append(mod)
            total_insertions += mod.insertions
            total_deletions += mod.deletions
            affected_paths.append((mod.path_before, mod.path_after))

        defaults: dict[str, Any] = {
            "modifications": modifications,
            "files_changed_count": file_count,
            "insertions_count": total_insertions,
            "deletions_count": total_deletions,
            "affected_paths": affected_paths,
        }
        defaults.update(overrides)
        return Diff(**defaults)

    @staticmethod
    def create_large_diff(file_count: int = 100, **overrides: Any) -> "Diff":
        """Create large Diff for performance testing."""
        from auto_release_note_generation.data_models.shared import Diff

        modifications = []
        affected_paths = []

        for i in range(file_count):
            mod = FileModificationFactory.create_added_file(
                path_after=f"src/generated_file_{i}.py",
                insertions=10,
                deletions=0,
            )
            modifications.append(mod)
            affected_paths.append((mod.path_before, mod.path_after))

        defaults: dict[str, Any] = {
            "modifications": modifications,
            "files_changed_count": file_count,
            "insertions_count": file_count * 10,
            "deletions_count": 0,
            "affected_paths": affected_paths,
        }
        defaults.update(overrides)
        return Diff(**defaults)

    @staticmethod
    def create_from_scenario_pattern(
        pattern_index: int = 0, **overrides: Any
    ) -> "Diff":
        """Create Diff from large diff pattern."""
        pattern = FileTestData.LARGE_DIFF_PATTERNS[
            pattern_index % len(FileTestData.LARGE_DIFF_PATTERNS)
        ]

        modifications = []
        total_insertions = 0
        total_deletions = 0
        affected_paths = []

        for mod_data in pattern["modifications"]:  # type: ignore[index]
            mod_type, path_before, path_after, insertions, deletions = mod_data
            mod = FileModification(
                modification_type=mod_type,
                path_before=path_before,
                path_after=path_after,
                insertions=insertions,
                deletions=deletions,
            )
            modifications.append(mod)
            total_insertions += insertions
            total_deletions += deletions
            affected_paths.append((path_before, path_after))

        defaults: dict[str, Any] = {
            "modifications": modifications,
            "files_changed_count": len(modifications),
            "insertions_count": total_insertions,
            "deletions_count": total_deletions,
            "affected_paths": affected_paths,
        }
        defaults.update(overrides)
        return Diff(**defaults)
