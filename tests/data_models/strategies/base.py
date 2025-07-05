"""Base strategies and common helpers for hypothesis testing."""

from collections.abc import Callable

from hypothesis import strategies as st

from auto_release_note_generation.data_models.shared import ValidationLimits
from auto_release_note_generation.data_models.utils import SHAValidationLimits

# Re-export validation limits for convenience
__all__ = [
    "SAFE_CHARACTERS",
    "UNICODE_CATEGORIES",
    "SHAValidationLimits",
    "ValidationLimits",
    "hex_string",
    "non_empty_text",
    "text_with_length",
    "trimmed_text",
    "valid_length_filter",
]

# Character categories for text generation
UNICODE_CATEGORIES = {
    "letters": ("Lu", "Ll", "Lt", "Lm", "Lo"),
    "numbers": ("Nd", "Nl", "No"),
    "punctuation": ("Pc", "Pd", "Ps", "Pe", "Pi", "Pf", "Po"),
    "symbols": ("Sm", "Sc", "Sk", "So"),
    "separators": ("Zs", "Zl", "Zp"),
}

# Safe character sets for various contexts
SAFE_CHARACTERS = {
    "alphanumeric": st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
    "hex": st.sampled_from("0123456789abcdefABCDEF"),
    "path_safe": st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_./"
    ),
    "branch_safe": st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_/."
    ),
    "email_safe": st.characters(
        whitelist_categories=("Lu", "Ll", "Nd"),
        whitelist_characters="@.-_+",
    ),
}


def non_empty_text(
    min_size: int = 1,
    max_size: int | None = None,
    alphabet: st.SearchStrategy[str] | None = None,
) -> st.SearchStrategy[str]:
    """Generate non-empty text that remains non-empty after stripping.

    Args:
        min_size: Minimum length of generated text
        max_size: Maximum length of generated text
        alphabet: Character strategy to use

    Returns:
        Strategy that generates non-empty strings
    """
    if alphabet is None:
        alphabet = st.characters(blacklist_categories=("Cc", "Cs"))

    return st.text(
        min_size=min_size,
        max_size=max_size,
        alphabet=alphabet,
    ).filter(lambda x: len(x.strip()) > 0)


def trimmed_text(
    strategy: st.SearchStrategy[str],
) -> st.SearchStrategy[str]:
    """Apply trimming to a text strategy.

    Args:
        strategy: Text strategy to trim

    Returns:
        Strategy that generates trimmed strings
    """
    return strategy.map(lambda x: x.strip())


def text_with_length(
    min_length: int,
    max_length: int,
    alphabet: st.SearchStrategy[str] | None = None,
) -> st.SearchStrategy[str]:
    """Generate text with specific length constraints after trimming.

    Args:
        min_length: Minimum length after trimming
        max_length: Maximum length after trimming
        alphabet: Character strategy to use

    Returns:
        Strategy that generates strings within length bounds
    """
    if alphabet is None:
        alphabet = st.characters(blacklist_categories=("Cc", "Cs"))

    # Generate slightly larger to account for trimming
    return st.text(
        min_size=min_length,
        max_size=max_length + 10,  # Buffer for whitespace
        alphabet=alphabet,
    ).filter(lambda x: min_length <= len(x.strip()) <= max_length)


def valid_length_filter(
    min_length: int,
    max_length: int,
) -> Callable[[str], bool]:
    """Create a filter function for validating string length after stripping.

    Args:
        min_length: Minimum allowed length
        max_length: Maximum allowed length

    Returns:
        Filter function for hypothesis strategies
    """

    def filter_fn(value: str) -> bool:
        stripped = value.strip()
        return min_length <= len(stripped) <= max_length

    return filter_fn


def hex_string(
    min_length: int,
    max_length: int,
    uppercase: bool = False,
) -> st.SearchStrategy[str]:
    """Generate hexadecimal strings.

    Args:
        min_length: Minimum length
        max_length: Maximum length
        uppercase: Whether to use uppercase letters

    Returns:
        Strategy generating hex strings
    """
    alphabet = "0123456789ABCDEF" if uppercase else "0123456789abcdef"
    return st.text(
        min_size=min_length,
        max_size=max_length,
        alphabet=alphabet,
    )
