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
