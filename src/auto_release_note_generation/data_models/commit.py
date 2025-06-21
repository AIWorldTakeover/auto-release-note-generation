from pydantic import BaseModel, ConfigDict, Field, field_validator

from .shared import Diff, GitMetadata


class Commit(BaseModel):
    """Represents a comprehensive Git commit with metadata, changes, and AI summary.

    A Commit combines Git metadata, file modifications, and optional AI-generated
    summaries to provide a complete representation of a single commit in the
    release note generation pipeline.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,  # Automatically strips whitespace
        # Note: Not using frozen=True to allow ai_summary to be added post-construction
    )

    metadata: GitMetadata = Field(
        ..., description="Core Git metadata (SHA, author, etc.)"
    )
    summary: str = Field(
        ...,
        min_length=1,
        description="Short description (first line of commit message)",
    )
    message: str = Field(..., min_length=1, description="Full commit message")
    branches: list[str] = Field(
        default_factory=list, description="Associated branch names"
    )
    tags: list[str] = Field(default_factory=list, description="Associated tag names")
    diff: Diff = Field(..., description="Detailed file modifications")
    ai_summary: str | None = Field(
        default=None, description="AI-generated summary (added post-construction)"
    )

    @field_validator("summary", "message")
    @classmethod
    def validate_text_fields(cls, v: str) -> str:
        """Validate summary and message are non-empty after stripping.

        TODO: Add comprehensive validation:
        - Maximum length limits
        - Character encoding validation
        - Format-specific validation (e.g., conventional commits)
        """
        if not v.strip():
            msg = "Summary and message cannot be empty or whitespace-only"
            raise ValueError(msg)
        return v.strip()

    @field_validator("branches", "tags")
    @classmethod
    def validate_name_lists(cls, v: list[str]) -> list[str]:
        """Validate branch and tag name lists.

        TODO: Add comprehensive Git name validation:
        - Git ref name rules (no spaces, special characters, etc.)
        - Length limits
        - Reserved name checks
        """
        # Basic validation - ensure no empty strings
        validated = []
        for name in v:
            if not isinstance(name, str):
                raise ValueError("Branch and tag names must be strings")
            stripped = name.strip()
            if not stripped:
                msg = "Branch and tag names cannot be empty or whitespace-only"
                raise ValueError(msg)
            validated.append(stripped)
        return validated

    @field_validator("ai_summary")
    @classmethod
    def validate_ai_summary(cls, v: str | None) -> str | None:
        """Validate AI summary format.

        TODO: Add structured AI summary validation:
        - Confidence score validation
        - Required fields checking
        - Content quality checks
        """
        if v is None:
            return None
        if not v.strip():
            return None
        return v.strip()

    def has_ai_summary(self) -> bool:
        """Check if this commit has an AI-generated summary."""
        return self.ai_summary is not None and len(self.ai_summary.strip()) > 0

    def get_short_sha(self, length: int = 8) -> str:
        """Get abbreviated SHA for display purposes."""
        return self.metadata.sha[:length]

    def is_merge_commit(self) -> bool:
        """Check if this is a merge commit (delegates to metadata)."""
        return self.metadata.is_merge_commit()

    def is_root_commit(self) -> bool:
        """Check if this is a root commit (delegates to metadata)."""
        return self.metadata.is_root_commit()

    def get_total_changes(self) -> int:
        """Get total number of line changes (delegates to diff)."""
        return self.diff.get_total_changes()

    def get_affected_paths(self) -> list[str]:
        """Get all unique paths affected by this commit (delegates to diff)."""
        return self.diff.get_all_affected_paths()

    def __str__(self) -> str:
        """Returns the commit in a compact format suitable for logs."""
        short_sha = self.get_short_sha()
        if len(self.summary) > 50:
            summary_preview = self.summary[:50] + "..."
        else:
            summary_preview = self.summary

        # Include basic change info
        files_changed = self.diff.files_changed_count
        files_word = "file" if files_changed == 1 else "files"

        ai_indicator = " [AI]" if self.has_ai_summary() else ""

        return (
            f"{short_sha} {summary_preview} "
            f"({files_changed} {files_word}){ai_indicator}"
        )

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return (
            f"Commit(sha='{self.get_short_sha()}', "
            f"author='{self.metadata.author.name}', "
            f"summary='{self.summary[:30]}...', "
            f"branches={len(self.branches)}, "
            f"tags={len(self.tags)}, "
            f"files_changed={self.diff.files_changed_count}, "
            f"ai_summary={'Yes' if self.has_ai_summary() else 'No'})"
        )
