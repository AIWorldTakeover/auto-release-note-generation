"""Tests for GitMetadata data model."""

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from auto_release_note_generation.data_models.shared import GitMetadata

from .test_data import GitTestData
from .test_factories import GitActorFactory, GitMetadataFactory
from .test_strategies import HypothesisStrategies


class TestGitMetadataValidation:
    """Test GitMetadata field validation and constraints."""

    @given(
        HypothesisStrategies.valid_git_shas,
        HypothesisStrategies.parent_sha_lists,
        HypothesisStrategies.valid_gpg_signatures,
    )
    def test_valid_creation(self, sha, parents, gpg_signature):
        """Test that valid inputs create GitMetadata successfully."""
        author = GitActorFactory.create()
        committer = GitActorFactory.create()

        metadata = GitMetadata(
            sha=sha,
            author=author,
            committer=committer,
            parents=parents,
            gpg_signature=gpg_signature,
        )

        assert metadata.sha == sha
        assert metadata.author == author
        assert metadata.committer == committer
        assert metadata.parents == parents
        assert metadata.gpg_signature == gpg_signature

    @given(HypothesisStrategies.invalid_git_shas)
    def test_invalid_sha_rejection(self, invalid_sha):
        """Test that invalid SHAs raise ValidationError."""
        # Skip cases that are actually valid hex but uppercase
        if invalid_sha and all(c in "0123456789ABCDEFabcdef" for c in invalid_sha):
            return  # Skip valid hex strings

        with pytest.raises(ValidationError):
            GitMetadataFactory.create(sha=invalid_sha)

    def test_required_fields_validation(self):
        """Test that required fields raise ValidationError when missing."""
        with pytest.raises(ValidationError):
            GitMetadata()  # type: ignore[call-arg] # Missing all required fields

        with pytest.raises(ValidationError):
            GitMetadata(sha="abc123")  # type: ignore[call-arg] # Missing author, committer

    def test_author_committer_validation(self):
        """Test that author and committer must be valid GitActor instances."""
        with pytest.raises(ValidationError):
            GitMetadataFactory.create(author="invalid_author")

        with pytest.raises(ValidationError):
            GitMetadataFactory.create(committer=123)

    def test_parents_list_validation(self):
        """Test that parent SHA list validation works correctly."""
        # Valid parent lists should work
        valid_parents = ["abc123", "def456"]
        metadata = GitMetadataFactory.create(parents=valid_parents)
        assert metadata.parents == valid_parents

        # Invalid parent SHAs should be rejected
        with pytest.raises(ValidationError):
            GitMetadataFactory.create(parents=["invalid-sha-with-dashes"])

    @given(HypothesisStrategies.invalid_gpg_signatures)
    def test_gpg_signature_validation(self, invalid_signature):
        """Test that invalid GPG signatures are rejected."""
        if invalid_signature == "" or invalid_signature == "   ":
            # Empty string and whitespace should become None
            metadata = GitMetadataFactory.create(gpg_signature=invalid_signature)
            assert metadata.gpg_signature is None
        else:
            with pytest.raises(ValidationError):
                GitMetadataFactory.create(gpg_signature=invalid_signature)


class TestGitMetadataBehavior:
    """Test GitMetadata behavior and constraints."""

    def test_immutability(self, default_git_metadata):
        """Test that GitMetadata is immutable after creation."""
        with pytest.raises(ValidationError):
            default_git_metadata.sha = "new_sha_123"

        with pytest.raises(ValidationError):
            default_git_metadata.author = GitActorFactory.create(name="New Author")

        with pytest.raises(ValidationError):
            default_git_metadata.committer = GitActorFactory.create(
                name="New Committer"
            )

    @pytest.mark.parametrize(
        ("parent_count", "expected_merge", "expected_root"),
        [
            (0, False, True),  # Root commit
            (1, False, False),  # Regular commit
            (2, True, False),  # Merge commit
            (3, True, False),  # Octopus merge
        ],
    )
    def test_commit_type_detection(self, parent_count, expected_merge, expected_root):
        """Test is_merge_commit and is_root_commit methods."""
        parents = [f"{i:040x}" for i in range(parent_count)]
        metadata = GitMetadataFactory.create(parents=parents)

        assert metadata.is_merge_commit() == expected_merge
        assert metadata.is_root_commit() == expected_root

    def test_string_representation_format(self):
        """Test __str__ returns compact format."""
        # Root commit
        root_commit = GitMetadataFactory.create_root_commit(sha="abc12345def67890")
        assert str(root_commit) == "abc12345 (root)"

        # Single parent
        single_parent = GitMetadataFactory.create_regular_commit(
            sha="def12345abc67890", parent_sha="abc123def456"
        )
        assert str(single_parent) == "def12345 (parent: abc123de)"

        # Merge commit
        merge_commit = GitMetadataFactory.create_merge_commit(
            sha="abc12345def67890", parent_count=3
        )
        assert str(merge_commit) == "abc12345 (3 parents)"

    def test_string_representation_with_gpg(self):
        """Test __str__ includes GPG signature indicator."""
        signed_commit = GitMetadataFactory.create_signed_commit(sha="abc12345def67890")
        result = str(signed_commit)
        assert "[signed]" in result
        assert "abc12345" in result

    def test_repr_format(self, default_git_metadata):
        """Test __repr__ returns detailed representation."""
        repr_str = repr(default_git_metadata)

        assert repr_str.startswith("GitMetadata(")
        assert f"sha='{default_git_metadata.sha}'" in repr_str
        assert "author=" in repr_str
        assert "committer=" in repr_str
        assert "parents=" in repr_str
        assert "gpg_signature=" in repr_str


class TestGitMetadataEdgeCases:
    """Test GitMetadata edge cases and boundary conditions."""

    def test_minimum_sha_length(self):
        """Test minimum valid SHA length (4 characters)."""
        metadata = GitMetadataFactory.create(sha="a1b2")
        assert metadata.sha == "a1b2"

    def test_maximum_sha_length(self):
        """Test maximum valid SHA length (64 characters)."""
        long_sha = "a" * 64
        metadata = GitMetadataFactory.create(sha=long_sha)
        assert metadata.sha == long_sha

    @pytest.mark.parametrize("sha", GitTestData.REALISTIC_SHA_PATTERNS)
    def test_realistic_sha_patterns(self, sha):
        """Test SHA patterns from real Git repositories."""
        metadata = GitMetadataFactory.create(sha=sha)
        assert metadata.sha == sha

    @pytest.mark.parametrize("parents", GitTestData.MERGE_COMMIT_PATTERNS)
    def test_complex_merge_patterns(self, parents):
        """Test complex merge scenarios including octopus merges."""
        metadata = GitMetadataFactory.create(parents=parents)
        if len(parents) == 0:
            assert metadata.is_root_commit()
        elif len(parents) == 1:
            assert not metadata.is_merge_commit()
            assert not metadata.is_root_commit()
        else:
            assert metadata.is_merge_commit()
        assert len(metadata.parents) == len(parents)

    def test_empty_parent_list_default(self):
        """Test that parents defaults to empty list."""
        metadata = GitMetadata(
            sha="abc123",
            author=GitActorFactory.create(),
            committer=GitActorFactory.create(),
        )
        assert metadata.parents == []
        assert metadata.is_root_commit()

    def test_same_author_committer(self):
        """Test behavior when author and committer are the same person."""
        actor = GitActorFactory.create()
        metadata = GitMetadataFactory.create(author=actor, committer=actor)

        assert metadata.author == metadata.committer
        # Note: Pydantic creates separate instances even when passed the same object

    def test_large_parent_list(self):
        """Test handling of commits with many parents (octopus merge)."""
        many_parents = [f"{i:040x}" for i in range(8)]
        metadata = GitMetadataFactory.create(parents=many_parents)

        assert metadata.is_merge_commit()
        assert len(metadata.parents) == 8
        assert "8 parents" in str(metadata)

    @given(st.integers(min_value=0, max_value=10))
    def test_parent_count_behavior(self, parent_count):
        """Test behavior with various parent counts."""
        parents = [f"{i:040x}" for i in range(parent_count)]
        metadata = GitMetadataFactory.create(parents=parents)

        if parent_count == 0:
            assert metadata.is_root_commit()
            assert not metadata.is_merge_commit()
        elif parent_count == 1:
            assert not metadata.is_root_commit()
            assert not metadata.is_merge_commit()
        else:
            assert not metadata.is_root_commit()
            assert metadata.is_merge_commit()


class TestGitMetadataFactory:
    """Test GitMetadataFactory functionality."""

    def test_default_creation(self, default_git_metadata):
        """Test factory creates valid default GitMetadata."""
        factory_metadata = GitMetadataFactory.create()

        assert factory_metadata.sha == default_git_metadata.sha
        assert isinstance(factory_metadata.author, type(default_git_metadata.author))
        assert isinstance(
            factory_metadata.committer, type(default_git_metadata.committer)
        )

    def test_override_functionality(self):
        """Test factory accepts override values."""
        custom_sha = "abcdef123456789abcdef123456789abcdef1234"
        metadata = GitMetadataFactory.create(sha=custom_sha)

        assert metadata.sha == custom_sha

    def test_specialized_factory_methods(self):
        """Test specialized factory methods."""
        # Root commit
        root = GitMetadataFactory.create_root_commit()
        assert root.is_root_commit()
        assert len(root.parents) == 0

        # Regular commit
        regular = GitMetadataFactory.create_regular_commit()
        assert not regular.is_root_commit()
        assert not regular.is_merge_commit()
        assert len(regular.parents) == 1

        # Merge commit
        merge = GitMetadataFactory.create_merge_commit()
        assert merge.is_merge_commit()
        assert len(merge.parents) == 2

        # Signed commit
        signed = GitMetadataFactory.create_signed_commit()
        assert signed.gpg_signature is not None

    def test_pattern_based_creation(self):
        """Test pattern-based factory creation."""
        patterns = ["root", "regular", "merge", "octopus", "signed"]

        for pattern in patterns:
            metadata = GitMetadataFactory.create_from_pattern(pattern)
            assert isinstance(metadata, GitMetadata)

    @given(HypothesisStrategies.valid_git_shas)
    def test_factory_with_hypothesis(self, sha):
        """Test factory works with hypothesis-generated data."""
        metadata = GitMetadataFactory.create(sha=sha)
        assert metadata.sha == sha

    def test_factory_creates_valid_instances(self, git_metadata_collection):
        """Test that all factory instances are valid."""
        for metadata in git_metadata_collection:
            assert isinstance(metadata, GitMetadata)
            assert len(metadata.sha) >= 4
            assert metadata.author is not None
            assert metadata.committer is not None
