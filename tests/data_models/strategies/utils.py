"""Strategies for GitSHA and GPGSignature types."""

from hypothesis import strategies as st

from .base import SHAValidationLimits, hex_string


# GitSHA Strategies
def valid_git_sha() -> st.SearchStrategy[str]:
    """Generate valid Git SHA strings (4-64 hex characters).

    Returns:
        Strategy generating valid SHA strings
    """
    return hex_string(
        min_length=SHAValidationLimits.MIN_LENGTH,
        max_length=SHAValidationLimits.MAX_LENGTH,
    )


def short_git_sha() -> st.SearchStrategy[str]:
    """Generate short Git SHA strings (4-12 characters).

    Returns:
        Strategy generating short SHA strings
    """
    return hex_string(
        min_length=SHAValidationLimits.MIN_LENGTH,
        max_length=12,
    )


def full_git_sha() -> st.SearchStrategy[str]:
    """Generate full Git SHA-1 strings (exactly 40 characters).

    Returns:
        Strategy generating 40-character SHA strings
    """
    return hex_string(min_length=40, max_length=40)


def extended_git_sha() -> st.SearchStrategy[str]:
    """Generate extended Git SHA-256 strings (exactly 64 characters).

    Returns:
        Strategy generating 64-character SHA strings
    """
    return hex_string(min_length=64, max_length=64)


def invalid_git_sha() -> st.SearchStrategy[str]:
    """Generate invalid Git SHA strings for testing validation.

    Returns:
        Strategy generating invalid SHA strings
    """
    return st.one_of(
        # Empty string
        st.just(""),
        # Whitespace only
        st.just("   "),
        # Too short (less than 4 chars)
        hex_string(min_length=1, max_length=3),
        # Too long (more than 64 chars)
        hex_string(min_length=65, max_length=100),
        # Invalid characters (not hex)
        st.text(
            min_size=4,
            max_size=64,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll"),
                blacklist_characters="abcdefABCDEF0123456789",
            ),
        ),
        # Mixed valid/invalid characters
        st.text(min_size=4, max_size=64).filter(
            lambda x: any(c not in "0123456789abcdefABCDEF" for c in x.strip())
        ),
    )


# GPGSignature Strategies
def valid_gpg_signature() -> st.SearchStrategy[str | None]:
    """Generate valid GPG signature strings.

    Returns:
        Strategy generating valid GPG signatures or None
    """
    # PGP signature block format
    pgp_signature = (
        st.text(min_size=1)
        .filter(lambda x: x.strip())
        .map(
            lambda x: (
                f"-----BEGIN PGP SIGNATURE-----\n{x.strip()}\n"
                "-----END PGP SIGNATURE-----"
            )
        )
    )

    # Git's gpgsig format
    gpgsig_signature = (
        st.text(min_size=1)
        .filter(lambda x: x.strip())
        .map(lambda x: f"gpgsig {x.strip()}")
    )

    return st.one_of(
        st.none(),  # No signature
        pgp_signature,
        gpgsig_signature,
    )


def invalid_gpg_signature() -> st.SearchStrategy[str]:
    """Generate invalid GPG signature strings for testing validation.

    Returns:
        Strategy generating invalid GPG signatures
    """
    return st.one_of(
        # Empty string
        st.just(""),
        # Whitespace only
        st.just("   "),
        st.just("\t\n"),
        # Invalid format (doesn't start with required prefixes)
        st.text(min_size=1, max_size=100).filter(
            lambda x: (
                x.strip()
                and not x.strip().startswith("-----BEGIN")
                and not x.strip().startswith("gpgsig ")
            )
        ),
        # Partial PGP format
        st.just("-----BEGIN PGP SIGNATURE-----"),
        st.just("-----END PGP SIGNATURE-----"),
        # Wrong prefix
        st.just("pgpsig test"),
        st.just("GPG: signature"),
    )
