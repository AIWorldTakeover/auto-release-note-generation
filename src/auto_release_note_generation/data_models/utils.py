"""Utility functions for data model validation."""

import re
from typing import Annotated

from pydantic import BeforeValidator


def validate_and_normalize_sha(value: str) -> str:
    """Validate SHA is hexadecimal and normalize to lowercase."""
    if not isinstance(value, str):
        raise ValueError("SHA must be a string")

    value = value.strip().lower()

    if not (4 <= len(value) <= 64):
        raise ValueError(f"SHA must be 4-64 characters long, got {len(value)}")

    if not re.match(r"^[0-9a-f]+$", value):
        raise ValueError("SHA must contain only hexadecimal characters")

    return value


def validate_gpg_signature(value: str | None) -> str | None:
    """Validate GPG signature format if provided."""
    if value is None or not value.strip():
        return None

    stripped = value.strip()
    if not stripped.startswith(("-----BEGIN", "gpgsig ")):
        raise ValueError("GPG signature must start with '-----BEGIN' or 'gpgsig '")

    return stripped


# Type aliases using Annotated for reusability
GitSHA = Annotated[str, BeforeValidator(validate_and_normalize_sha)]
GPGSignature = Annotated[str | None, BeforeValidator(validate_gpg_signature)]
