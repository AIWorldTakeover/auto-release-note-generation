"""Utility functions for data model validation."""

import re
from typing import Annotated

from pydantic import BeforeValidator


# Validation constants to avoid magic numbers
class SHAValidationLimits:
    """Constants for SHA validation limits."""

    MIN_LENGTH = 4   # Minimum Git SHA length (short form)
    MAX_LENGTH = 64  # Maximum Git SHA length (extended)


def validate_and_normalize_sha(value: str) -> str:
    """Validate SHA is hexadecimal and normalize to lowercase.

    Accepts Git SHA hashes of 4-64 characters, which covers short SHAs,
    standard 40-character SHAs, and extended SHA-256 64-character hashes.

    Examples:
        >>> validate_and_normalize_sha("ABC123")
        'abc123'
        >>> validate_and_normalize_sha("  abc123def456  ")
        'abc123def456'
        >>> validate_and_normalize_sha("1234567890abcdef1234567890abcdef12345678")
        '1234567890abcdef1234567890abcdef12345678'

    Args:
        value: SHA string to validate and normalize

    Returns:
        Normalized lowercase SHA string

    Raises:
        ValueError: If SHA is invalid format, length, or contains non-hex characters
    """
    if not isinstance(value, str):
        raise ValueError("SHA must be a string")

    value = value.strip().lower()

    if not (
        SHAValidationLimits.MIN_LENGTH <= len(value) <= SHAValidationLimits.MAX_LENGTH
    ):
        raise ValueError(
            f"SHA must be {SHAValidationLimits.MIN_LENGTH}-"
            f"{SHAValidationLimits.MAX_LENGTH} characters long, got {len(value)}"
        )

    if not re.match(r"^[0-9a-f]+$", value):
        raise ValueError("SHA must contain only hexadecimal characters")

    return value


def validate_gpg_signature(value: str | None) -> str | None:
    """Validate GPG signature format if provided.

    Accepts Git's gpgsig format or standard PGP signature blocks.
    Empty/whitespace-only values are converted to None.

    Examples:
        >>> validate_gpg_signature(None)
        None
        >>> validate_gpg_signature("")
        None
        >>> validate_gpg_signature("gpgsig test_signature_data")
        'gpgsig test_signature_data'
        >>> validate_gpg_signature("-----BEGIN PGP SIGNATURE-----")
        '-----BEGIN PGP SIGNATURE-----'

    Args:
        value: GPG signature string or None

    Returns:
        Validated signature string or None if empty

    Raises:
        ValueError: If signature format is invalid
    """
    if value is None or not value.strip():
        return None

    stripped = value.strip()
    if not stripped.startswith(("-----BEGIN", "gpgsig ")):
        raise ValueError("GPG signature must start with '-----BEGIN' or 'gpgsig '")

    return stripped


# Type aliases using Annotated for reusability
GitSHA = Annotated[str, BeforeValidator(validate_and_normalize_sha)]
GPGSignature = Annotated[str | None, BeforeValidator(validate_gpg_signature)]
