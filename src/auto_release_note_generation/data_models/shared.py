from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .utils import GitSHA, GPGSignature


# Validation constants to avoid magic numbers
class ValidationLimits:
    """Constants for field validation limits."""

    # GitActor field limits
    NAME_MIN_LENGTH = 1
    NAME_MAX_LENGTH = 255
    EMAIL_MIN_LENGTH = 1
    EMAIL_MAX_LENGTH = 320  # RFC 5321 maximum email length

    # ChangeMetadata field limits
    BRANCH_NAME_MIN_LENGTH = 1

    # FileModification field limits
    PATH_MAX_LENGTH = 4096  # Common filesystem path limit


class GitActor(BaseModel):
    """Represents Git author/committer information with validation and immutability."""

    model_config = ConfigDict(
        frozen=True,  # Makes the model immutable after creation
        str_strip_whitespace=True,  # Automatically strips whitespace
    )

    name: str = Field(
        ...,
        min_length=ValidationLimits.NAME_MIN_LENGTH,
        max_length=ValidationLimits.NAME_MAX_LENGTH,
        description="Full name",
    )
    email: str = Field(
        ...,
        min_length=ValidationLimits.EMAIL_MIN_LENGTH,
        max_length=ValidationLimits.EMAIL_MAX_LENGTH,
        description="Email address",
    )
    timestamp: datetime = Field(..., description="Timestamp of the Git action")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower()

    def __str__(self) -> str:
        """Returns the actor in standard Git format with timestamp."""
        unix_timestamp = int(self.timestamp.timestamp())
        tz_offset = self.timestamp.strftime("%z") or "+0000"
        return f"{self.name} <{self.email}> {unix_timestamp} {tz_offset}"

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"GitActor(name='{self.name}', email='{self.email}', "
            f"timestamp={self.timestamp.isoformat()})"
        )


class GitMetadata(BaseModel):
    """Represents core immutable Git object metadata with validation."""

    model_config = ConfigDict(
        frozen=True,  # Makes the model immutable after creation
        str_strip_whitespace=True,  # Automatically strips whitespace
    )

    sha: GitSHA = Field(..., description="Git object SHA hash (4-64 characters)")
    author: GitActor = Field(..., description="Primary author of the commit")
    committer: GitActor = Field(..., description="Who committed/merged the change")
    parents: list[GitSHA] = Field(
        default_factory=list, description="List of parent commit SHAs"
    )
    gpg_signature: GPGSignature = Field(
        default=None, description="GPG signature for verification"
    )

    def is_merge_commit(self) -> bool:
        """Check if this commit is a merge commit (has multiple parents)."""
        return len(self.parents) > 1

    def is_root_commit(self) -> bool:
        """Check if this is a root commit (no parents)."""
        return len(self.parents) == 0

    def __str__(self) -> str:
        """Returns the metadata in a compact format."""
        parent_count = len(self.parents)
        if parent_count == 0:
            parent_info = "root"
        elif parent_count == 1:
            parent_info = f"parent: {self.parents[0][:8]}"
        else:
            parent_info = f"{parent_count} parents"

        gpg_info = " [signed]" if self.gpg_signature else ""
        return f"{self.sha[:8]} ({parent_info}){gpg_info}"

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"GitMetadata(sha='{self.sha}', author={self.author!r}, "
            f"committer={self.committer!r}, parents={self.parents}, "
            f"gpg_signature={'signed' if self.gpg_signature else 'None'})"
        )


class ChangeMetadata(BaseModel):
    """Represents metadata specific to logical changes with validation."""

    model_config = ConfigDict(
        frozen=True,  # Makes the model immutable after creation
        str_strip_whitespace=True,  # Automatically strips whitespace
    )

    change_type: Literal[
        "direct",
        "merge",
        "squash",
        "octopus",
        "rebase",
        "cherry-pick",
        "revert",
        "initial",
        "amend",
    ] = Field(..., description="Type of change")
    source_branches: list[str] = Field(
        default_factory=list,
        description="Source branch names (empty for direct, multiple for octopus)",
    )
    target_branch: str = Field(
        ...,
        min_length=ValidationLimits.BRANCH_NAME_MIN_LENGTH,
        description="Target branch name",
    )
    merge_base: GitSHA | None = Field(default=None, description="Merge base commit SHA")
    pull_request_id: str | None = Field(
        default=None, description="PR identifier if extractable from commit message"
    )

    @field_validator("source_branches")
    @classmethod
    def validate_source_branches(cls, v: list[str]) -> list[str]:
        """Validate that all source branches are non-empty strings."""
        for branch in v:
            if not branch or not branch.strip():
                raise ValueError("Source branch names must be non-empty strings")
        return [branch.strip() for branch in v]

    @field_validator("target_branch")
    @classmethod
    def validate_target_branch(cls, v: str) -> str:
        """Validate target branch is non-empty and properly formatted."""
        if not v or not v.strip():
            raise ValueError("Target branch must be a non-empty string")

        stripped = v.strip()
        # Check for invalid characters and patterns
        if any(c in stripped for c in [" ", "\t", "\n", "\r"]):
            raise ValueError("Target branch cannot contain whitespace characters")
        if stripped.startswith("/") or stripped.endswith("/") or "//" in stripped:
            raise ValueError("Target branch has invalid path format")

        return stripped

    @field_validator("pull_request_id")
    @classmethod
    def validate_pull_request_id(cls, v: str | None) -> str | None:
        """Validate pull request ID and convert empty strings to None."""
        if v is None:
            return None
        if not v.strip():
            return None
        return v.strip()

    @model_validator(mode="after")
    def validate_business_logic(self) -> "ChangeMetadata":
        """Validate business logic constraints between fields.

        Ensures that the combination of change_type and source_branches follows
        Git workflow patterns and logical constraints.

        Examples:
            Valid combinations:
            - direct: [], ["main"] (direct commits to branch)
            - merge: ["feature/auth"] (feature branch merge)
            - squash: ["feature/small-fix"] (squashed feature merge)
            - octopus: ["feat/a", "feat/b", "feat/c"] (multi-branch merge)
            - rebase: ["feature/branch"] (rebased commits)
            - cherry-pick: ["hotfix/patch"] (cherry-picked commit)
            - revert: ["bad-commit"] (reverted commit)
            - initial: [] (repository initialization)
            - amend: ["original-branch"] (amended commit)

            Invalid combinations:
            - direct: ["feat/a", "feat/b"] (direct can't have multiple sources)
            - merge: [] (merge requires a source branch)
            - octopus: ["single-branch"] (octopus needs multiple branches)
            - initial: ["main"] (initial commits can't have sources)

        Raises:
            ValueError: When field combination violates Git workflow logic.
        """
        # Direct-style changes should have exactly one or zero source branches
        if (
            self.change_type
            in [
                "direct",
                "rebase",
                "cherry-pick",
                "revert",
                "amend",
            ]
            and len(self.source_branches) > 1
        ):
            raise ValueError(
                f"{self.change_type} changes cannot have multiple source branches"
            )

        # Initial commits should have no source branches
        if self.change_type == "initial" and len(self.source_branches) > 0:
            raise ValueError("Initial commits cannot have source branches")

        # Merge/squash changes should have exactly one source branch
        if self.change_type in ["merge", "squash"] and len(self.source_branches) == 0:
            raise ValueError(
                f"{self.change_type} changes require at least one source branch"
            )

        # Octopus merges should have multiple source branches
        if self.change_type == "octopus" and len(self.source_branches) < 2:
            raise ValueError("Octopus merges require at least two source branches")

        return self

    def is_octopus_change(self) -> bool:
        """Check if this is an octopus merge (multiple source branches)."""
        return self.change_type == "octopus" and len(self.source_branches) >= 2

    def __str__(self) -> str:
        """Returns the metadata in a compact format."""
        source_info = ""
        if self.source_branches:
            if len(self.source_branches) == 1:
                source_info = f" from {self.source_branches[0]}"
            else:
                source_info = f" from {len(self.source_branches)} branches"

        pr_info = f" (PR: {self.pull_request_id})" if self.pull_request_id else ""
        return f"{self.change_type}{source_info} → {self.target_branch}{pr_info}"

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"ChangeMetadata(change_type='{self.change_type}', "
            f"source_branches={self.source_branches}, "
            f"target_branch='{self.target_branch}', "
            f"merge_base={self.merge_base!r}, "
            f"pull_request_id={self.pull_request_id!r})"
        )


class FileModification(BaseModel):
    """Represents modifications to a single file with validation."""

    model_config = ConfigDict(
        frozen=True,
        str_strip_whitespace=True,
    )

    path_before: str | None = Field(
        default=None, description="File path before modification (None if added)"
    )
    path_after: str | None = Field(
        default=None, description="File path after modification (None if deleted)"
    )
    modification_type: Literal[
        "A",  # Addition of a file
        "C",  # Copy of a file into a new one
        "D",  # Deletion of a file
        "M",  # Modification of the contents or mode of a file
        "R",  # Renaming of a file
        "T",  # Change in the type of the file (regular file, symlink, submodule)
        "U",  # File is unmerged (must complete merge before commit)
        "X",  # Unknown change type (likely a bug)
        "B",  # Have had their pairing broken
    ] = Field(..., description="Git modification type")
    insertions: int = Field(
        ...,
        ge=0,
        description="Lines added to this file",
    )
    deletions: int = Field(
        ...,
        ge=0,
        description="Lines removed from this file",
    )
    patch: str | None = Field(
        default=None,
        description="Unified diff patch text for this file",
        # TODO: Add patch format validation once we have more clarity
    )

    @field_validator("path_before", "path_after")
    @classmethod
    def validate_file_paths(cls, v: str | None) -> str | None:
        """Validate file paths when provided."""
        if v is None:
            return None

        # Normalize path separators and strip whitespace
        normalized = v.strip().replace("\\", "/")

        if not normalized:
            return None

        # Basic git path validation
        if len(normalized) > ValidationLimits.PATH_MAX_LENGTH:
            raise ValueError(
                f"Path too long: maximum {ValidationLimits.PATH_MAX_LENGTH} characters"
            )

        # Git doesn't allow null bytes in paths
        if "\x00" in normalized:
            raise ValueError("Path cannot contain null bytes")

        return normalized

    @model_validator(mode="after")
    def validate_business_logic(self) -> "FileModification":
        """Validate business logic constraints between fields."""
        # Added files should have no path_before
        if self.modification_type == "A" and self.path_before is not None:
            raise ValueError("Added files (type 'A') cannot have path_before")

        # Deleted files should have no path_after
        if self.modification_type == "D" and self.path_after is not None:
            raise ValueError("Deleted files (type 'D') cannot have path_after")

        # Added files must have path_after
        if self.modification_type == "A" and self.path_after is None:
            raise ValueError("Added files (type 'A') must have path_after")

        # Deleted files must have path_before
        if self.modification_type == "D" and self.path_before is None:
            raise ValueError("Deleted files (type 'D') must have path_before")

        # Renamed/copied files should have both paths and be different
        if self.modification_type in ["R", "C"]:
            if self.path_before is None or self.path_after is None:
                raise ValueError(
                    f"{self.modification_type} files must have both "
                    "path_before and path_after"
                )
            if self.path_before == self.path_after:
                raise ValueError(
                    f"{self.modification_type} files must have different "
                    "path_before and path_after"
                )

        # Modified files should have both paths
        if self.modification_type == "M" and (
            self.path_before is None or self.path_after is None
        ):
            raise ValueError(
                "Modified files (type 'M') must have both path_before and path_after"
            )

        # Unmerged files should have path_after
        if self.modification_type == "U" and self.path_after is None:
            raise ValueError("Unmerged files (type 'U') must have path_after")

        return self

    def get_effective_path(self) -> str:
        """Get the effective file path for this modification."""
        if self.path_after is not None:
            return self.path_after
        if self.path_before is not None:
            return self.path_before
        raise ValueError("FileModification must have at least one path")

    def get_all_paths(self) -> list[str]:
        """Get all paths associated with this modification."""
        paths = []
        if self.path_before is not None:
            paths.append(self.path_before)
        if self.path_after is not None and self.path_after != self.path_before:
            paths.append(self.path_after)
        return paths

    def is_rename_or_copy(self) -> bool:
        """Check if this modification is a rename or copy operation."""
        return self.modification_type in ["R", "C"]

    def __str__(self) -> str:
        """Returns the modification in a compact format."""
        if self.modification_type == "A":
            return f"A {self.path_after} (+{self.insertions})"
        if self.modification_type == "D":
            return f"D {self.path_before} (-{self.deletions})"
        if self.modification_type in ["R", "C"]:
            return (
                f"{self.modification_type} {self.path_before} → "
                f"{self.path_after} (+{self.insertions}/-{self.deletions})"
            )
        path = self.get_effective_path()
        return f"{self.modification_type} {path} (+{self.insertions}/-{self.deletions})"

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"FileModification(modification_type='{self.modification_type}', "
            f"path_before={self.path_before!r}, "
            f"path_after={self.path_after!r}, "
            f"insertions={self.insertions}, deletions={self.deletions}, "
            f"patch={'<patch>' if self.patch else 'None'})"
        )


class Diff(BaseModel):
    """Collection of file modifications with aggregated metrics."""

    model_config = ConfigDict(
        frozen=True,
    )

    modifications: list[FileModification] = Field(
        default_factory=list, description="Per-file modification details"
    )
    # TODO: Implement cross-validation between modifications and counts
    files_changed_count: int = Field(..., ge=0, description="Count of affected files")
    insertions_count: int = Field(..., ge=0, description="Total lines added")
    deletions_count: int = Field(..., ge=0, description="Total lines removed")
    affected_paths: list[tuple[str | None, str | None]] = Field(
        default_factory=list,
        description="List of (path_before, path_after) tuples",
    )

    @field_validator("affected_paths")
    @classmethod
    def validate_affected_paths(
        cls, v: list[tuple[str | None, str | None]]
    ) -> list[tuple[str | None, str | None]]:
        """Validate affected paths format."""
        for path_tuple in v:
            if not isinstance(path_tuple, tuple) or len(path_tuple) != 2:
                raise ValueError(
                    "Each affected_paths entry must be a tuple of "
                    "(path_before, path_after)"
                )
            path_before, path_after = path_tuple
            if path_before is None and path_after is None:
                raise ValueError("At least one path in each tuple must be non-None")
        return v

    @model_validator(mode="after")
    def validate_aggregated_metrics(self) -> "Diff":
        """Validate that aggregated metrics are consistent."""
        # Check that we have some modifications if counts > 0
        if self.files_changed_count > 0 and not self.modifications:
            raise ValueError("Must have modifications if files_changed_count > 0")

        if (
            self.insertions_count > 0 or self.deletions_count > 0
        ) and not self.modifications:
            raise ValueError(
                "Must have modifications if insertions_count or deletions_count > 0"
            )

        return self

    def is_empty(self) -> bool:
        """Check if this diff represents no changes."""
        return (
            self.files_changed_count == 0
            and self.insertions_count == 0
            and self.deletions_count == 0
            and len(self.modifications) == 0
        )

    def get_total_changes(self) -> int:
        """Get total number of line changes (insertions + deletions)."""
        return self.insertions_count + self.deletions_count

    def get_modification_types(self) -> set[str]:
        """Get unique modification types present in this diff."""
        return {mod.modification_type for mod in self.modifications}

    def get_renamed_files(self) -> list[FileModification]:
        """Get all file modifications that are renames."""
        return [mod for mod in self.modifications if mod.modification_type == "R"]

    def get_copied_files(self) -> list[FileModification]:
        """Get all file modifications that are copies."""
        return [mod for mod in self.modifications if mod.modification_type == "C"]

    def get_all_affected_paths(self) -> list[str]:
        """Get a flattened list of all unique paths affected by this diff."""
        all_paths = set()
        for path_before, path_after in self.affected_paths:
            if path_before is not None:
                all_paths.add(path_before)
            if path_after is not None:
                all_paths.add(path_after)
        return sorted(all_paths)

    def __str__(self) -> str:
        """Returns the diff in a compact format."""
        if self.is_empty():
            return "Empty diff"

        files_word = "file" if self.files_changed_count == 1 else "files"
        changes_parts = []

        if self.insertions_count > 0:
            changes_parts.append(f"{self.insertions_count} insertions(+)")
        if self.deletions_count > 0:
            changes_parts.append(f"{self.deletions_count} deletions(-)")

        changes_str = ", ".join(changes_parts) if changes_parts else "no line changes"

        return f"{self.files_changed_count} {files_word} changed, {changes_str}"

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"Diff(files_changed={self.files_changed_count}, "
            f"insertions={self.insertions_count}, "
            f"deletions={self.deletions_count}, "
            f"modifications_count={len(self.modifications)}, "
            f"affected_paths_count={len(self.affected_paths)})"
        )
