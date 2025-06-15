"""Tests for ChangeMetadata data model."""

import pytest
from hypothesis import HealthCheck, given, settings
from pydantic import ValidationError

from auto_release_note_generation.data_models.shared import ChangeMetadata

from .conftest import SharedTestConfig
from .test_data import ChangeTestData
from .test_factories import ChangeMetadataFactory
from .test_strategies import HypothesisStrategies


class TestChangeMetadataValidation:
    """Test ChangeMetadata field validation and constraints."""

    @given(
        HypothesisStrategies.valid_change_types,
        HypothesisStrategies.valid_branch_names,
        HypothesisStrategies.valid_merge_bases,
        HypothesisStrategies.valid_pull_request_ids,
    )
    def test_comprehensive_valid_creation(
        self, change_type, target_branch, merge_base, pr_id
    ):
        """Test comprehensive valid creation with all field combinations."""
        # Generate appropriate source branches based on change type
        source_branches: list[str]
        if change_type == "direct":
            source_branches = []
        elif change_type == "initial":
            source_branches = []  # Initial commits have no source branches
        elif change_type == "octopus":
            source_branches = ["branch-1", "branch-2"]
        else:  # merge, squash, rebase, cherry-pick, revert, amend
            source_branches = ["feature-branch"]

        metadata = ChangeMetadata(
            change_type=change_type,
            source_branches=source_branches,
            target_branch=target_branch,
            merge_base=merge_base,
            pull_request_id=pr_id,
        )

        assert metadata.change_type == change_type
        assert metadata.source_branches == source_branches
        assert metadata.target_branch == target_branch.strip()
        assert metadata.merge_base == merge_base
        assert metadata.pull_request_id == (
            pr_id.strip() if pr_id and pr_id.strip() else None
        )

    def test_valid_creation(self):
        """Test that valid inputs create ChangeMetadata successfully."""
        # Test direct change with single source branch
        direct_metadata = ChangeMetadata(
            change_type="direct",
            source_branches=["feature/test"],
            target_branch="main",
        )
        assert direct_metadata.change_type == "direct"
        assert direct_metadata.source_branches == ["feature/test"]

        # Test merge change with single source branch
        merge_metadata = ChangeMetadata(
            change_type="merge",
            source_branches=["feature/test"],
            target_branch="main",
            merge_base="abc123",
        )
        assert merge_metadata.change_type == "merge"

        # Test octopus change with multiple source branches
        octopus_metadata = ChangeMetadata(
            change_type="octopus",
            source_branches=["feature/a", "feature/b"],
            target_branch="main",
            merge_base="abc123",
        )
        assert octopus_metadata.change_type == "octopus"
        assert len(octopus_metadata.source_branches) == 2

    @given(HypothesisStrategies.invalid_change_types)
    def test_invalid_change_type_rejection(self, invalid_type):
        """Test that invalid change types raise ValidationError."""
        with pytest.raises(ValidationError):
            ChangeMetadataFactory.create(change_type=invalid_type)

    @given(HypothesisStrategies.invalid_branch_names)
    @settings(suppress_health_check=[HealthCheck.filter_too_much])
    def test_invalid_target_branch_rejection(self, invalid_branch):
        """Test that invalid target branches raise ValidationError."""
        with pytest.raises(ValidationError):
            ChangeMetadataFactory.create(target_branch=invalid_branch)

    @given(HypothesisStrategies.empty_source_branch_lists)
    def test_empty_source_branches_allowed(self, empty_list):
        """Test that empty source branch lists are allowed."""
        metadata = ChangeMetadataFactory.create(source_branches=empty_list)
        assert metadata.source_branches == []

    @pytest.mark.parametrize(
        ("source_branches", "target_branch", "change_type"),
        ChangeTestData.INVALID_COMBINATIONS,
    )
    def test_invalid_business_logic_combinations(
        self, source_branches, target_branch, change_type
    ):
        """Test that logically invalid combinations are rejected."""
        with pytest.raises((ValidationError, ValueError)):
            ChangeMetadata(
                change_type=change_type,
                source_branches=source_branches,
                target_branch=target_branch,
            )

    def test_whitespace_stripping(self):
        """Test that whitespace is stripped from branch names."""
        metadata = ChangeMetadata(
            change_type="direct",
            source_branches=["  feature/test  "],
            target_branch="  main  ",
        )

        assert metadata.source_branches == ["feature/test"]
        assert metadata.target_branch == "main"


class TestChangeMetadataBehavior:
    """Test ChangeMetadata behavior and constraints."""

    def test_immutability(self, default_change_metadata):
        """Test that ChangeMetadata is immutable after creation."""
        with pytest.raises(ValidationError):
            default_change_metadata.change_type = "merge"

        with pytest.raises(ValidationError):
            default_change_metadata.source_branches = ["new/branch"]

        with pytest.raises(ValidationError):
            default_change_metadata.target_branch = "develop"

    def test_string_representation_format(self):
        """Test __str__ returns compact format."""
        # Direct change
        direct = ChangeMetadataFactory.create_direct_change(
            source_branch="feature/auth"
        )
        assert str(direct) == "direct from feature/auth → main"

        # Merge change
        merge = ChangeMetadataFactory.create_merge_change()
        assert str(merge) == "merge from feature/new-feature → main"

        # Multiple branches
        octopus = ChangeMetadataFactory.create_octopus_change(branch_count=3)
        assert str(octopus) == "octopus from 3 branches → develop"

    def test_string_representation_without_source_branches(self):
        """Test __str__ handles empty source branches."""
        metadata = ChangeMetadata(
            change_type="direct",
            source_branches=[],
            target_branch="main",
        )
        assert str(metadata) == "direct → main"

    @given(
        HypothesisStrategies.valid_change_types,
        HypothesisStrategies.valid_branch_names,
    )
    def test_repr_format(self, change_type, target_branch):
        """Test __repr__ returns detailed representation."""
        # Generate appropriate source branches based on change type
        if change_type == "direct":
            source_branches = ["single-branch"]
        elif change_type == "initial":
            source_branches = []  # Initial commits have no source branches
        elif change_type == "octopus":
            source_branches = ["branch-1", "branch-2"]
        else:  # merge, squash, rebase, cherry-pick, revert, amend
            source_branches = ["feature-branch"]

        metadata = ChangeMetadata(
            change_type=change_type,
            source_branches=source_branches,
            target_branch=target_branch,
        )
        repr_str = repr(metadata)

        assert repr_str.startswith("ChangeMetadata(")
        assert f"change_type='{change_type}'" in repr_str
        assert f"source_branches={source_branches}" in repr_str
        assert f"target_branch='{target_branch.strip()}'" in repr_str

    def test_string_methods_consistency(self, change_metadata_collection):
        """Test that str and repr work consistently across instances."""
        for metadata in change_metadata_collection:
            str_result = str(metadata)
            repr_result = repr(metadata)

            assert isinstance(str_result, str)
            assert len(str_result) > 0
            assert isinstance(repr_result, str)
            assert len(repr_result) > 0


class TestChangeMetadataEdgeCases:
    """Test ChangeMetadata edge cases and boundary conditions."""

    def test_minimum_length_fields(self):
        """Test minimum valid field lengths."""
        metadata = ChangeMetadata(
            change_type="direct",
            source_branches=["a"],
            target_branch="b",
        )

        assert metadata.source_branches == ["a"]
        assert metadata.target_branch == "b"

    def test_maximum_length_fields(self):
        """Test maximum valid field lengths."""
        long_branch = "a" * 100
        metadata = ChangeMetadata(
            change_type="merge",
            source_branches=[long_branch],
            target_branch=long_branch,
        )

        assert metadata.source_branches == [long_branch]
        assert metadata.target_branch == long_branch

    @pytest.mark.parametrize(
        ("source_branches", "target_branch"), ChangeTestData.DIRECT_CHANGE_PATTERNS
    )
    def test_direct_change_patterns(self, source_branches, target_branch):
        """Test direct change patterns from real-world scenarios."""
        metadata = ChangeMetadata(
            change_type="direct",
            source_branches=source_branches,
            target_branch=target_branch,
        )
        assert metadata.change_type == "direct"
        assert len(metadata.source_branches) <= 1

    @pytest.mark.parametrize(
        ("source_branches", "target_branch"), ChangeTestData.MERGE_CHANGE_PATTERNS
    )
    def test_merge_change_patterns(self, source_branches, target_branch):
        """Test merge change patterns from real-world scenarios."""
        metadata = ChangeMetadata(
            change_type="merge",
            source_branches=source_branches,
            target_branch=target_branch,
        )
        assert metadata.change_type == "merge"

    @pytest.mark.parametrize(
        ("source_branches", "target_branch"), ChangeTestData.OCTOPUS_CHANGE_PATTERNS
    )
    def test_octopus_change_patterns(self, source_branches, target_branch):
        """Test octopus merge patterns."""
        metadata = ChangeMetadata(
            change_type="octopus",
            source_branches=source_branches,
            target_branch=target_branch,
        )
        assert metadata.change_type == "octopus"
        assert len(metadata.source_branches) >= 2

    @pytest.mark.parametrize("pr_id", ChangeTestData.GITHUB_PR_PATTERNS)
    def test_github_pr_id_patterns(self, pr_id):
        """Test GitHub PR ID patterns."""
        metadata = ChangeMetadataFactory.create(
            change_type="squash",
            source_branches=["feature/github-integration"],
            target_branch="main",
            pull_request_id=pr_id,
        )
        assert metadata.pull_request_id == pr_id

    @pytest.mark.parametrize("merge_base", ChangeTestData.MERGE_BASE_PATTERNS)
    def test_merge_base_patterns(self, merge_base):
        """Test merge base SHA patterns."""
        metadata = ChangeMetadataFactory.create_merge_change(merge_base=merge_base)
        assert metadata.merge_base == merge_base

    def test_branch_name_special_characters(self):
        """Test branch names with special characters."""
        special_branches = [
            "feature/user-auth",
            "bugfix/fix-login-issue",
            "release/v1.2.0",
            "hotfix/security.patch",
        ]

        for branch in special_branches:
            metadata = ChangeMetadata(
                change_type="merge",
                source_branches=[branch],
                target_branch="main",
            )
            assert metadata.source_branches == [branch]

    def test_none_optional_fields(self):
        """Test that optional fields can be None."""
        metadata = ChangeMetadata(
            change_type="direct",
            source_branches=["main"],
            target_branch="main",
            merge_base=None,
            pull_request_id=None,
        )

        assert metadata.merge_base is None
        assert metadata.pull_request_id is None

    def test_unicode_branch_names(self):
        """Test branch names with Unicode characters."""
        for branch_name in ChangeTestData.UNICODE_BRANCH_NAMES:
            metadata = ChangeMetadata(
                change_type="merge",
                source_branches=[branch_name],
                target_branch="main",
            )
            assert metadata.source_branches == [branch_name]

    def test_realistic_pr_id_formats(self):
        """Test realistic PR ID formats from various systems."""
        for pr_id in ChangeTestData.REALISTIC_PR_IDS:
            metadata = ChangeMetadataFactory.create(
                change_type="merge",
                source_branches=["feature/test"],
                target_branch="main",
                pull_request_id=pr_id,
            )
            assert metadata.pull_request_id == pr_id

    def test_empty_pr_id_normalization(self):
        """Test that empty PR ID becomes None."""
        metadata = ChangeMetadata(
            change_type="direct",
            source_branches=[],
            target_branch="main",
            pull_request_id="",
        )
        assert metadata.pull_request_id is None

        metadata2 = ChangeMetadata(
            change_type="direct",
            source_branches=[],
            target_branch="main",
            pull_request_id="   ",
        )
        assert metadata2.pull_request_id is None

    def test_many_source_branches(self):
        """Test large octopus merges."""
        many_branches = [f"feature/branch-{i}" for i in range(10)]
        metadata = ChangeMetadata(
            change_type="octopus",
            source_branches=many_branches,
            target_branch="main",
        )
        assert len(metadata.source_branches) == 10

    def test_change_type_patterns_from_test_data(self):
        """Test change type patterns from ChangeTestData."""
        for pattern in ChangeTestData.CHANGE_TYPE_PATTERNS:
            change_type, source_branches, target, merge_base, pr_id = pattern
            metadata = ChangeMetadata(
                change_type=change_type,  # type: ignore[arg-type]
                source_branches=source_branches,
                target_branch=target,
                merge_base=merge_base,
                pull_request_id=pr_id,
            )
            assert metadata.change_type == change_type
            assert metadata.source_branches == source_branches
            assert metadata.target_branch == target


class TestChangeMetadataFactory:
    """Test ChangeMetadataFactory functionality."""

    def test_default_creation(self, default_change_metadata):
        """Test factory creates valid default ChangeMetadata."""
        factory_metadata = ChangeMetadataFactory.create()

        assert factory_metadata.change_type == default_change_metadata.change_type
        assert (
            factory_metadata.source_branches == default_change_metadata.source_branches
        )
        assert factory_metadata.target_branch == default_change_metadata.target_branch

    def test_override_functionality(self):
        """Test factory accepts override values."""
        custom_type = "merge"
        metadata = ChangeMetadataFactory.create(change_type=custom_type)

        assert metadata.change_type == custom_type
        assert metadata.target_branch == SharedTestConfig.DEFAULT_TARGET_BRANCH

    def test_specialized_factory_methods(self):
        """Test specialized factory methods work correctly."""
        # Direct change
        direct = ChangeMetadataFactory.create_direct_change()
        assert direct.change_type == "direct"
        assert len(direct.source_branches) <= 1

        # Merge change
        merge = ChangeMetadataFactory.create_merge_change()
        assert merge.change_type == "merge"
        assert merge.target_branch == "main"

        # Squash change
        squash = ChangeMetadataFactory.create_squash_change()
        assert squash.change_type == "squash"

        # Octopus change
        octopus = ChangeMetadataFactory.create_octopus_change(branch_count=4)
        assert octopus.change_type == "octopus"
        assert len(octopus.source_branches) == 4

        # Rebase change
        rebase = ChangeMetadataFactory.create_rebase_change()
        assert rebase.change_type == "rebase"
        assert len(rebase.source_branches) <= 1

        # Cherry-pick change
        cherry_pick = ChangeMetadataFactory.create_cherry_pick_change()
        assert cherry_pick.change_type == "cherry-pick"
        assert len(cherry_pick.source_branches) <= 1

        # Revert change
        revert = ChangeMetadataFactory.create_revert_change()
        assert revert.change_type == "revert"
        assert len(revert.source_branches) <= 1

        # Initial change
        initial = ChangeMetadataFactory.create_initial_change()
        assert initial.change_type == "initial"
        assert len(initial.source_branches) == 0

        # Amend change
        amend = ChangeMetadataFactory.create_amend_change()
        assert amend.change_type == "amend"
        assert len(amend.source_branches) <= 1

    @given(HypothesisStrategies.valid_change_types)
    def test_factory_with_hypothesis(self, change_type):
        """Test factory works with hypothesis-generated data."""
        metadata = ChangeMetadataFactory.create(change_type=change_type)
        assert metadata.change_type == change_type

    def test_factory_creates_valid_instances(self, change_metadata_collection):
        """Test that all factory methods create valid instances."""
        for metadata in change_metadata_collection:
            assert isinstance(metadata, ChangeMetadata)
            assert isinstance(metadata.change_type, str)
            assert isinstance(metadata.source_branches, list)
            assert isinstance(metadata.target_branch, str)

            # Test string methods work
            str_result = str(metadata)
            repr_result = repr(metadata)
            assert isinstance(str_result, str)
            assert isinstance(repr_result, str)

    def test_octopus_factory_validation(self):
        """Test octopus factory validates branch count."""
        with pytest.raises(ValueError, match="at least 2 source branches"):
            ChangeMetadataFactory.create_octopus_change(branch_count=1)

        # Valid octopus merge
        octopus = ChangeMetadataFactory.create_octopus_change(branch_count=3)
        assert len(octopus.source_branches) == 3

    def test_pattern_based_creation(self):
        """Test pattern-based factory usage."""
        patterns = [
            "direct",
            "merge",
            "squash",
            "octopus",
            "rebase",
            "cherry-pick",
            "revert",
            "initial",
            "amend",
            "github-pr",
            "hotfix",
            "release",
        ]

        for pattern in patterns:
            metadata = ChangeMetadataFactory.create_from_pattern(pattern)
            assert isinstance(metadata, ChangeMetadata)

        # Test invalid pattern
        with pytest.raises(ValueError, match="Unknown pattern"):
            ChangeMetadataFactory.create_from_pattern("invalid_pattern")
