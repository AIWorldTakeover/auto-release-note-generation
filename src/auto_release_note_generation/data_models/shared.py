from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
