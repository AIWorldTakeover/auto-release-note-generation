from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .utils import GitSHA, GPGSignature


class GitActor(BaseModel):
    """Represents Git author/committer information with validation and immutability."""

    model_config = ConfigDict(
        frozen=True,  # Makes the model immutable after creation
        str_strip_whitespace=True,  # Automatically strips whitespace
    )

    name: str = Field(..., min_length=1, max_length=255, description="Full name")
    email: str = Field(..., min_length=1, max_length=320, description="Email address")
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
