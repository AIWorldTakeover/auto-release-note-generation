"""Tests for data model utility functions."""

import pytest

from auto_release_note_generation.data_models.utils import (
    validate_and_normalize_sha,
    validate_gpg_signature,
)

# =============================================================================
# SHA VALIDATION TESTS
# =============================================================================


class TestValidateAndNormalizeSha:
    """Test the validate_and_normalize_sha function directly."""

    def test_valid_sha_normalization(self):
        """Test that valid SHAs are normalized correctly."""
        # Test lowercase normalization
        assert validate_and_normalize_sha("ABCD1234") == "abcd1234"
        assert validate_and_normalize_sha("ABC123def456") == "abc123def456"

        # Test whitespace stripping
        assert validate_and_normalize_sha("  abc123  ") == "abc123"
        assert validate_and_normalize_sha("\tabc123\n") == "abc123"

        # Test already normalized SHAs
        assert validate_and_normalize_sha("abcd1234") == "abcd1234"

    def test_valid_sha_lengths(self):
        """Test valid SHA lengths (4-64 characters)."""
        # Minimum length (4 characters)
        assert validate_and_normalize_sha("abc1") == "abc1"
        assert validate_and_normalize_sha("1234") == "1234"

        # Typical short SHA (8 characters)
        assert validate_and_normalize_sha("abcd1234") == "abcd1234"

        # Typical full SHA (40 characters)
        full_sha = "abc123def456789abcdef123456789abcdef1234"
        assert validate_and_normalize_sha(full_sha) == full_sha

        # Maximum length (64 characters)
        long_sha = "a" * 64
        assert validate_and_normalize_sha(long_sha) == long_sha

    def test_valid_hex_characters(self):
        """Test that valid hexadecimal characters are accepted."""
        # All lowercase hex digits
        assert validate_and_normalize_sha("0123456789abcdef") == "0123456789abcdef"

        # Mixed case hex digits
        assert validate_and_normalize_sha("0123456789ABCDEF") == "0123456789abcdef"

        # Edge cases
        assert validate_and_normalize_sha("0000") == "0000"
        assert validate_and_normalize_sha("ffff") == "ffff"

    def test_non_string_input_rejection(self):
        """Test that non-string inputs are rejected."""
        with pytest.raises(ValueError, match="SHA must be a string"):
            validate_and_normalize_sha(123)  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="SHA must be a string"):
            validate_and_normalize_sha(None)  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="SHA must be a string"):
            validate_and_normalize_sha([])  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="SHA must be a string"):
            validate_and_normalize_sha({})  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="SHA must be a string"):
            validate_and_normalize_sha(True)  # type: ignore[arg-type]

        with pytest.raises(ValueError, match="SHA must be a string"):
            validate_and_normalize_sha(42.5)  # type: ignore[arg-type]

    def test_invalid_length_rejection(self):
        """Test that invalid lengths are rejected."""
        # Too short (less than 4 characters)
        with pytest.raises(ValueError, match="SHA must be 4-64 characters long"):
            validate_and_normalize_sha("")

        with pytest.raises(ValueError, match="SHA must be 4-64 characters long"):
            validate_and_normalize_sha("a")

        with pytest.raises(ValueError, match="SHA must be 4-64 characters long"):
            validate_and_normalize_sha("ab")

        with pytest.raises(ValueError, match="SHA must be 4-64 characters long"):
            validate_and_normalize_sha("abc")

        # Too long (more than 64 characters)
        with pytest.raises(ValueError, match="SHA must be 4-64 characters long"):
            validate_and_normalize_sha("a" * 65)

        with pytest.raises(ValueError, match="SHA must be 4-64 characters long"):
            validate_and_normalize_sha("a" * 100)

    def test_invalid_characters_rejection(self):
        """Test that non-hexadecimal characters are rejected."""
        with pytest.raises(
            ValueError, match="SHA must contain only hexadecimal characters"
        ):
            validate_and_normalize_sha("abcg")  # 'g' is not hex

        with pytest.raises(
            ValueError, match="SHA must contain only hexadecimal characters"
        ):
            validate_and_normalize_sha("abc-123")  # '-' is not hex

        with pytest.raises(
            ValueError, match="SHA must contain only hexadecimal characters"
        ):
            validate_and_normalize_sha("abc 123")  # space is not hex

        with pytest.raises(
            ValueError, match="SHA must contain only hexadecimal characters"
        ):
            validate_and_normalize_sha("abcz123")  # 'z' is not hex

    def test_whitespace_only_rejection(self):
        """Test that whitespace-only strings are rejected."""
        with pytest.raises(ValueError, match="SHA must be 4-64 characters long"):
            validate_and_normalize_sha("   ")

        with pytest.raises(ValueError, match="SHA must be 4-64 characters long"):
            validate_and_normalize_sha("\t\n")


# =============================================================================
# GPG SIGNATURE VALIDATION TESTS
# =============================================================================


class TestValidateGpgSignature:
    """Test the validate_gpg_signature function directly."""

    def test_none_input(self):
        """Test that None input returns None."""
        assert validate_gpg_signature(None) is None

    def test_empty_string_input(self):
        """Test that empty string returns None."""
        assert validate_gpg_signature("") is None

    def test_whitespace_only_input(self):
        """Test that whitespace-only strings return None."""
        assert validate_gpg_signature("   ") is None
        assert validate_gpg_signature("\t\n") is None
        assert validate_gpg_signature("  \t  \n  ") is None

    def test_valid_gpg_signatures(self):
        """Test that valid GPG signatures are accepted and stripped."""
        # Valid gpgsig format
        assert validate_gpg_signature("gpgsig test") == "gpgsig test"
        assert (
            validate_gpg_signature("gpgsig some_signature_data")
            == "gpgsig some_signature_data"
        )

        # Valid PGP signature format
        pgp_sig = "-----BEGIN PGP SIGNATURE-----"
        assert validate_gpg_signature(pgp_sig) == pgp_sig

        full_pgp_sig = (
            "-----BEGIN PGP SIGNATURE-----\n"
            "Version: GnuPG v2\n\n"
            "iQIcBAABCAAGBQJhXYZ1AAoJEH8JWXvNOxq+ABC123def456789abcdef123456789\n"
            "=AbC1\n"
            "-----END PGP SIGNATURE-----"
        )
        assert validate_gpg_signature(full_pgp_sig) == full_pgp_sig

    def test_whitespace_stripping(self):
        """Test that leading/trailing whitespace is stripped."""
        # Test gpgsig format with whitespace
        assert validate_gpg_signature("  gpgsig test  ") == "gpgsig test"
        assert validate_gpg_signature("\tgpgsig test\n") == "gpgsig test"

        # Test PGP format with whitespace
        pgp_sig = "  -----BEGIN PGP SIGNATURE-----  "
        assert validate_gpg_signature(pgp_sig) == "-----BEGIN PGP SIGNATURE-----"

    def test_invalid_signature_formats(self):
        """Test that invalid signature formats are rejected."""
        # Doesn't start with expected prefixes
        with pytest.raises(ValueError, match="GPG signature must start with"):
            validate_gpg_signature("invalid signature")

        with pytest.raises(ValueError, match="GPG signature must start with"):
            validate_gpg_signature("sig gpgsig test")

        with pytest.raises(ValueError, match="GPG signature must start with"):
            validate_gpg_signature("BEGIN PGP SIGNATURE")

        with pytest.raises(ValueError, match="GPG signature must start with"):
            validate_gpg_signature("random text")

    def test_edge_case_signatures(self):
        """Test edge cases for GPG signatures."""
        # Minimal valid signatures
        assert validate_gpg_signature("gpgsig x") == "gpgsig x"
        assert validate_gpg_signature("-----BEGIN") == "-----BEGIN"

        # Case sensitivity matters
        with pytest.raises(ValueError, match="GPG signature must start with"):
            validate_gpg_signature("GPGSIG test")

        with pytest.raises(ValueError, match="GPG signature must start with"):
            validate_gpg_signature("-----begin PGP SIGNATURE-----")


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestUtilityFunctionIntegration:
    """Test how utility functions work together and with the type system."""

    def test_gitsha_type_alias_behavior(self):
        """Test that GitSHA type alias uses validate_and_normalize_sha correctly."""
        # This test ensures the type alias is properly configured
        # We test this indirectly through the models that use GitSHA
        from datetime import datetime

        from auto_release_note_generation.data_models.shared import (
            GitActor,
            GitMetadata,
        )

        # Create a simple GitMetadata to test SHA validation
        author = GitActor(
            name="Test", email="test@example.com", timestamp=datetime.now()
        )

        # Test that SHA normalization works through the type alias
        metadata = GitMetadata(
            sha="ABC123",  # Should be normalized to lowercase
            author=author,
            committer=author,
        )
        assert metadata.sha == "abc123"

    def test_gpg_signature_type_alias_behavior(self):
        """Test that GPGSignature type alias uses validate_gpg_signature correctly."""
        from datetime import datetime

        from auto_release_note_generation.data_models.shared import (
            GitActor,
            GitMetadata,
        )

        author = GitActor(
            name="Test", email="test@example.com", timestamp=datetime.now()
        )

        # Test that empty GPG signature becomes None
        metadata = GitMetadata(
            sha="abc123",
            author=author,
            committer=author,
            gpg_signature="",  # Should become None
        )
        assert metadata.gpg_signature is None

        # Test that valid GPG signature is preserved
        metadata_signed = GitMetadata(
            sha="def456",
            author=author,
            committer=author,
            gpg_signature="gpgsig test_signature",
        )
        assert metadata_signed.gpg_signature == "gpgsig test_signature"
