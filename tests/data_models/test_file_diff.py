"""Tests for FileModification and Diff data models."""

import pytest
from hypothesis import given
from pydantic import ValidationError

from auto_release_note_generation.data_models.shared import (
    Diff,
    FileModification,
    ValidationLimits,
)

from .strategies import (
    added_file,
    deleted_file,
    empty_diff,
    multi_file_diff,
    renamed_file,
    single_file_diff,
    unicode_file_path,
    valid_diff,
    valid_file_modification,
    valid_file_path,
    valid_line_counts,
)
from .test_factories import DiffFactory, FileModificationFactory


class TestFileModificationValidation:
    """Test FileModification validation logic."""

    def test_valid_creation_added_file(self):
        """Test creation of a valid added file modification."""
        mod = FileModification(
            path_before=None,
            path_after="src/new_file.py",
            modification_type="A",
            insertions=10,
            deletions=0,
        )
        assert mod.path_before is None
        assert mod.path_after == "src/new_file.py"
        assert mod.modification_type == "A"
        assert mod.insertions == 10
        assert mod.deletions == 0

    def test_valid_creation_deleted_file(self):
        """Test creation of a valid deleted file modification."""
        mod = FileModification(
            path_before="src/old_file.py",
            path_after=None,
            modification_type="D",
            insertions=0,
            deletions=15,
        )
        assert mod.path_before == "src/old_file.py"
        assert mod.path_after is None
        assert mod.modification_type == "D"
        assert mod.insertions == 0
        assert mod.deletions == 15

    def test_valid_creation_modified_file(self):
        """Test creation of a valid modified file modification."""
        mod = FileModification(
            path_before="src/file.py",
            path_after="src/file.py",
            modification_type="M",
            insertions=5,
            deletions=3,
        )
        assert mod.path_before == "src/file.py"
        assert mod.path_after == "src/file.py"
        assert mod.modification_type == "M"
        assert mod.insertions == 5
        assert mod.deletions == 3

    def test_valid_creation_renamed_file(self):
        """Test creation of a valid renamed file modification."""
        mod = FileModification(
            path_before="src/old_name.py",
            path_after="src/new_name.py",
            modification_type="R",
            insertions=2,
            deletions=1,
        )
        assert mod.path_before == "src/old_name.py"
        assert mod.path_after == "src/new_name.py"
        assert mod.modification_type == "R"
        assert mod.insertions == 2
        assert mod.deletions == 1

    def test_valid_creation_copied_file(self):
        """Test creation of a valid copied file modification."""
        mod = FileModification(
            path_before="src/original.py",
            path_after="src/copy.py",
            modification_type="C",
            insertions=0,
            deletions=0,
        )
        assert mod.path_before == "src/original.py"
        assert mod.path_after == "src/copy.py"
        assert mod.modification_type == "C"

    def test_negative_line_counts_rejected(self):
        """Test that negative line counts are rejected."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            FileModification(
                path_after="file.py",
                modification_type="A",
                insertions=-1,
                deletions=0,
            )

        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            FileModification(
                path_after="file.py",
                modification_type="A",
                insertions=0,
                deletions=-1,
            )

    def test_invalid_modification_type_rejected(self):
        """Test that invalid modification types are rejected."""
        with pytest.raises(ValidationError):
            FileModification(
                path_after="file.py",
                modification_type="Z",  # type: ignore[arg-type]  # Invalid type
                insertions=1,
                deletions=0,
            )

    def test_path_normalization(self):
        """Test that paths are normalized correctly."""
        mod = FileModification(
            path_before="  src\\file.py  ",
            path_after="  src/other.py  ",
            modification_type="R",
            insertions=0,
            deletions=0,
        )
        assert mod.path_before == "src/file.py"
        assert mod.path_after == "src/other.py"

    def test_path_too_long_rejected(self):
        """Test that overly long paths are rejected."""
        long_path = "a/" * (ValidationLimits.PATH_MAX_LENGTH // 2 + 1)
        with pytest.raises(ValidationError, match="Path too long"):
            FileModification(
                path_after=long_path,
                modification_type="A",
                insertions=1,
                deletions=0,
            )

    def test_null_bytes_in_path_rejected(self):
        """Test that null bytes in paths are rejected."""
        with pytest.raises(ValidationError, match="cannot contain null bytes"):
            FileModification(
                path_after="src/file\x00.py",
                modification_type="A",
                insertions=1,
                deletions=0,
            )

    @given(valid_file_path())
    def test_valid_file_paths_property_based(self, file_path):
        """Test that valid file paths are accepted using property-based testing."""
        mod = FileModificationFactory.create_modified_file(
            path_before=file_path,
            path_after=file_path,
        )
        assert mod.path_before == file_path
        assert mod.path_after == file_path

    @given(valid_file_modification())
    def test_all_modification_types_property_based(self, mod):
        """Test all modification types with property-based generation."""
        assert mod.modification_type in ["A", "C", "D", "M", "R", "T", "U", "X", "B"]

        # Validate type-specific constraints
        if mod.modification_type == "A":
            assert mod.path_before is None
            assert mod.path_after is not None
        elif mod.modification_type == "D":
            assert mod.path_before is not None
            assert mod.path_after is None
        elif mod.modification_type in ["R", "C"]:
            assert mod.path_before is not None
            assert mod.path_after is not None
            assert mod.path_before != mod.path_after

    @given(valid_line_counts(), valid_line_counts())
    def test_line_counts_property_based(self, insertions, deletions):
        """Test that valid line counts are accepted."""
        mod = FileModificationFactory.create_modified_file(
            insertions=insertions,
            deletions=deletions,
        )
        assert mod.insertions == insertions
        assert mod.deletions == deletions


class TestFileModificationBusinessLogic:
    """Test FileModification business logic validation."""

    def test_added_file_cannot_have_path_before(self):
        """Test that added files cannot have path_before."""
        with pytest.raises(ValidationError, match="cannot have path_before"):
            FileModification(
                path_before="some/path.py",
                path_after="new/file.py",
                modification_type="A",
                insertions=10,
                deletions=0,
            )

    def test_deleted_file_cannot_have_path_after(self):
        """Test that deleted files cannot have path_after."""
        with pytest.raises(ValidationError, match="cannot have path_after"):
            FileModification(
                path_before="old/file.py",
                path_after="some/path.py",
                modification_type="D",
                insertions=0,
                deletions=10,
            )

    def test_added_file_must_have_path_after(self):
        """Test that added files must have path_after."""
        with pytest.raises(ValidationError, match="must have path_after"):
            FileModification(
                path_before=None,
                path_after=None,
                modification_type="A",
                insertions=10,
                deletions=0,
            )

    def test_deleted_file_must_have_path_before(self):
        """Test that deleted files must have path_before."""
        with pytest.raises(ValidationError, match="must have path_before"):
            FileModification(
                path_before=None,
                path_after=None,
                modification_type="D",
                insertions=0,
                deletions=10,
            )

    def test_renamed_file_must_have_both_paths(self):
        """Test that renamed files must have both paths."""
        with pytest.raises(ValidationError, match="must have both"):
            FileModification(
                path_before=None,
                path_after="new.py",
                modification_type="R",
                insertions=0,
                deletions=0,
            )

        with pytest.raises(ValidationError, match="must have both"):
            FileModification(
                path_before="old.py",
                path_after=None,
                modification_type="R",
                insertions=0,
                deletions=0,
            )

    def test_copied_file_must_have_both_paths(self):
        """Test that copied files must have both paths."""
        with pytest.raises(ValidationError, match="must have both"):
            FileModification(
                path_before=None,
                path_after="copy.py",
                modification_type="C",
                insertions=0,
                deletions=0,
            )

    def test_renamed_file_must_have_different_paths(self):
        """Test that renamed files must have different paths."""
        with pytest.raises(ValidationError, match="must have different"):
            FileModification(
                path_before="same.py",
                path_after="same.py",
                modification_type="R",
                insertions=0,
                deletions=0,
            )

    def test_copied_file_must_have_different_paths(self):
        """Test that copied files must have different paths."""
        with pytest.raises(ValidationError, match="must have different"):
            FileModification(
                path_before="same.py",
                path_after="same.py",
                modification_type="C",
                insertions=0,
                deletions=0,
            )

    def test_modified_file_must_have_both_paths(self):
        """Test that modified files must have both paths."""
        with pytest.raises(ValidationError, match="must have both"):
            FileModification(
                path_before=None,
                path_after="file.py",
                modification_type="M",
                insertions=1,
                deletions=0,
            )

    def test_unmerged_file_must_have_path_after(self):
        """Test that unmerged files must have path_after."""
        with pytest.raises(ValidationError, match="must have path_after"):
            FileModification(
                path_before="old.py",
                path_after=None,
                modification_type="U",
                insertions=0,
                deletions=0,
            )


class TestFileModificationPropertyTests:
    """Property-based tests for FileModification using specific strategies."""

    @given(added_file())
    def test_added_file_properties(self, mod):
        """Test properties of added files."""
        assert mod.modification_type == "A"
        assert mod.path_before is None
        assert mod.path_after is not None
        assert mod.deletions == 0

    @given(deleted_file())
    def test_deleted_file_properties(self, mod):
        """Test properties of deleted files."""
        assert mod.modification_type == "D"
        assert mod.path_before is not None
        assert mod.path_after is None
        assert mod.insertions == 0

    @given(renamed_file())
    def test_renamed_file_properties(self, mod):
        """Test properties of renamed files."""
        assert mod.modification_type == "R"
        assert mod.path_before is not None
        assert mod.path_after is not None
        assert mod.path_before != mod.path_after
        assert mod.is_rename_or_copy()

    @given(unicode_file_path())
    def test_unicode_paths(self, path):
        """Test that unicode paths are handled correctly."""
        mod = FileModificationFactory.create_modified_file(
            path_before=path,
            path_after=path,
        )
        assert mod.path_before == path
        assert mod.path_after == path


class TestFileModificationBehavior:
    """Test FileModification behavior and methods."""

    def test_immutability(self):
        """Test that FileModification instances are immutable."""
        mod = FileModification(
            path_after="file.py",
            modification_type="A",
            insertions=10,
            deletions=0,
        )
        with pytest.raises(ValidationError):
            mod.insertions = 5

    @pytest.mark.parametrize(
        "scenario_index",
        range(5),  # Test first 5 realistic scenarios
    )
    def test_realistic_scenarios(self, scenario_index):
        """Test FileModification creation with realistic scenarios."""
        mod = FileModificationFactory.create_from_scenario(scenario_index)
        assert mod.modification_type in ["A", "C", "D", "M", "R", "T", "U", "X", "B"]
        assert mod.insertions >= 0
        assert mod.deletions >= 0
        # Verify path logic based on modification type
        if mod.modification_type == "A":
            assert mod.path_before is None
            assert mod.path_after is not None
        elif mod.modification_type == "D":
            assert mod.path_before is not None
            assert mod.path_after is None
        elif mod.modification_type in ["M", "R", "T", "U", "X", "B"]:
            assert mod.path_before is not None
            assert mod.path_after is not None

    def test_get_effective_path_prefers_path_after(self):
        """Test that get_effective_path prefers path_after."""
        mod = FileModification(
            path_before="old.py",
            path_after="new.py",
            modification_type="R",
            insertions=0,
            deletions=0,
        )
        assert mod.get_effective_path() == "new.py"

    def test_get_effective_path_fallback_to_path_before(self):
        """Test that get_effective_path falls back to path_before."""
        mod = FileModification(
            path_before="old.py",
            path_after=None,
            modification_type="D",
            insertions=0,
            deletions=10,
        )
        assert mod.get_effective_path() == "old.py"

    def test_get_effective_path_raises_when_no_paths(self):
        """Test that get_effective_path raises when no paths available."""

        # This scenario is impossible through normal validation, so we test the method
        # logic by creating a mock object that simulates the condition
        class MockFileModification:
            def __init__(self) -> None:
                self.path_before: str | None = None
                self.path_after: str | None = None

            def get_effective_path(self) -> str:
                """Implement the same logic as FileModification.get_effective_path."""
                if self.path_after:
                    return self.path_after
                if self.path_before:
                    return self.path_before
                raise ValueError("FileModification must have at least one path")

        mock_mod = MockFileModification()
        with pytest.raises(ValueError, match="must have at least one path"):
            mock_mod.get_effective_path()

    def test_get_all_paths_single_path(self):
        """Test get_all_paths with single path."""
        mod = FileModification(
            path_after="file.py",
            modification_type="A",
            insertions=10,
            deletions=0,
        )
        assert mod.get_all_paths() == ["file.py"]

    def test_get_all_paths_different_paths(self):
        """Test get_all_paths with different paths."""
        mod = FileModification(
            path_before="old.py",
            path_after="new.py",
            modification_type="R",
            insertions=0,
            deletions=0,
        )
        assert mod.get_all_paths() == ["old.py", "new.py"]

    def test_get_all_paths_same_paths(self):
        """Test get_all_paths with same paths (modification)."""
        mod = FileModification(
            path_before="file.py",
            path_after="file.py",
            modification_type="M",
            insertions=5,
            deletions=2,
        )
        assert mod.get_all_paths() == ["file.py"]

    def test_is_rename_or_copy(self):
        """Test is_rename_or_copy method."""
        rename_mod = FileModification(
            path_before="old.py",
            path_after="new.py",
            modification_type="R",
            insertions=0,
            deletions=0,
        )
        assert rename_mod.is_rename_or_copy()

        copy_mod = FileModification(
            path_before="src.py",
            path_after="copy.py",
            modification_type="C",
            insertions=0,
            deletions=0,
        )
        assert copy_mod.is_rename_or_copy()

        add_mod = FileModification(
            path_after="new.py",
            modification_type="A",
            insertions=10,
            deletions=0,
        )
        assert not add_mod.is_rename_or_copy()

    def test_string_representation(self):
        """Test string representations."""
        # Added file
        add_mod = FileModification(
            path_after="new.py",
            modification_type="A",
            insertions=10,
            deletions=0,
        )
        assert str(add_mod) == "A new.py (+10)"

        # Deleted file
        del_mod = FileModification(
            path_before="old.py",
            modification_type="D",
            insertions=0,
            deletions=5,
        )
        assert str(del_mod) == "D old.py (-5)"

        # Renamed file
        rename_mod = FileModification(
            path_before="old.py",
            path_after="new.py",
            modification_type="R",
            insertions=2,
            deletions=1,
        )
        assert str(rename_mod) == "R old.py → new.py (+2/-1)"

        # Modified file
        mod_mod = FileModification(
            path_before="file.py",
            path_after="file.py",
            modification_type="M",
            insertions=3,
            deletions=2,
        )
        assert str(mod_mod) == "M file.py (+3/-2)"

    def test_repr_format(self):
        """Test repr format."""
        mod = FileModification(
            path_before="old.py",
            path_after="new.py",
            modification_type="R",
            insertions=1,
            deletions=0,
            patch="some patch",
        )
        repr_str = repr(mod)
        assert "FileModification" in repr_str
        assert "modification_type='R'" in repr_str
        assert "path_before='old.py'" in repr_str
        assert "path_after='new.py'" in repr_str
        assert "insertions=1" in repr_str
        assert "deletions=0" in repr_str
        assert "patch=<patch>" in repr_str


class TestDiffValidation:
    """Test Diff validation logic."""

    def test_valid_creation(self):
        """Test creation of a valid diff."""
        mod = FileModification(
            path_after="file.py",
            modification_type="A",
            insertions=10,
            deletions=0,
        )
        diff = Diff(
            modifications=[mod],
            files_changed_count=1,
            insertions_count=10,
            deletions_count=0,
            affected_paths=[(None, "file.py")],
        )
        assert len(diff.modifications) == 1
        assert diff.files_changed_count == 1
        assert diff.insertions_count == 10
        assert diff.deletions_count == 0
        assert diff.affected_paths == [(None, "file.py")]

    def test_empty_diff_creation(self):
        """Test creation of an empty diff."""
        diff = Diff(
            modifications=[],
            files_changed_count=0,
            insertions_count=0,
            deletions_count=0,
            affected_paths=[],
        )
        assert len(diff.modifications) == 0
        assert diff.files_changed_count == 0
        assert diff.insertions_count == 0
        assert diff.deletions_count == 0
        assert diff.affected_paths == []

    def test_negative_counts_rejected(self):
        """Test that negative counts are rejected."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            Diff(
                files_changed_count=-1,
                insertions_count=0,
                deletions_count=0,
            )

        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            Diff(
                files_changed_count=0,
                insertions_count=-1,
                deletions_count=0,
            )

        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            Diff(
                files_changed_count=0,
                insertions_count=0,
                deletions_count=-1,
            )

    def test_invalid_affected_paths_format_rejected(self):
        """Test that invalid affected_paths format is rejected."""
        with pytest.raises(ValidationError, match="Input should be a valid tuple"):
            Diff(
                files_changed_count=0,
                insertions_count=0,
                deletions_count=0,
                affected_paths=["not_a_tuple"],  # type: ignore[list-item]
            )

    def test_invalid_affected_paths_tuple_format_rejected(self):
        """Test that invalid tuple format in affected_paths is rejected."""
        from auto_release_note_generation.data_models.shared import Diff

        # Test with non-tuple elements
        with pytest.raises(
            ValueError, match="Each affected_paths entry must be a tuple"
        ):
            # Bypass Pydantic's initial validation to hit our custom validator
            Diff.validate_affected_paths([("valid", "tuple"), "not_a_tuple"])  # type: ignore[list-item]

        # Test with wrong tuple length
        with pytest.raises(
            ValueError, match="Each affected_paths entry must be a tuple"
        ):
            Diff.validate_affected_paths([("valid", "tuple"), ("only_one",)])  # type: ignore[list-item]

    def test_both_paths_none_rejected(self):
        """Test that tuples with both paths as None are rejected."""
        with pytest.raises(ValidationError, match="must be non-None"):
            Diff(
                files_changed_count=0,
                insertions_count=0,
                deletions_count=0,
                affected_paths=[(None, None)],
            )


class TestDiffPropertyTests:
    """Property-based tests for Diff using specific strategies."""

    @given(empty_diff())
    def test_empty_diff_properties(self, diff):
        """Test properties of empty diffs."""
        assert diff.is_empty()
        assert diff.files_changed_count == 0
        assert diff.insertions_count == 0
        assert diff.deletions_count == 0
        assert len(diff.modifications) == 0
        assert diff.get_total_changes() == 0

    @given(single_file_diff())
    def test_single_file_diff_properties(self, diff):
        """Test properties of single file diffs."""
        assert not diff.is_empty()
        assert diff.files_changed_count == 1
        assert len(diff.modifications) == 1
        assert diff.insertions_count == diff.modifications[0].insertions
        assert diff.deletions_count == diff.modifications[0].deletions

    @given(multi_file_diff())
    def test_multi_file_diff_properties(self, diff):
        """Test properties of multi-file diffs."""
        assert not diff.is_empty()
        assert diff.files_changed_count >= 2
        assert len(diff.modifications) >= 2
        assert diff.insertions_count == sum(m.insertions for m in diff.modifications)
        assert diff.deletions_count == sum(m.deletions for m in diff.modifications)

    @given(valid_diff())
    def test_diff_consistency(self, diff):
        """Test consistency between diff fields."""
        assert diff.files_changed_count == len(diff.modifications)
        assert diff.insertions_count == sum(m.insertions for m in diff.modifications)
        assert diff.deletions_count == sum(m.deletions for m in diff.modifications)
        assert len(diff.affected_paths) == len(diff.modifications)


class TestDiffBehavior:
    """Test Diff behavior and methods."""

    def test_immutability(self):
        """Test that Diff instances are immutable."""
        mod = FileModification(
            path_after="file.py",
            modification_type="A",
            insertions=10,
            deletions=0,
        )
        diff = Diff(
            modifications=[mod],
            files_changed_count=1,
            insertions_count=10,
            deletions_count=0,
        )
        with pytest.raises(ValidationError):
            diff.files_changed_count = 2

    def test_is_empty(self):
        """Test is_empty method."""
        empty_diff = Diff(
            modifications=[],
            files_changed_count=0,
            insertions_count=0,
            deletions_count=0,
            affected_paths=[],
        )
        assert empty_diff.is_empty()

        mod = FileModification(
            path_after="file.py",
            modification_type="A",
            insertions=5,
            deletions=0,
        )
        non_empty_diff = Diff(
            modifications=[mod],
            files_changed_count=1,
            insertions_count=5,
            deletions_count=0,
        )
        assert not non_empty_diff.is_empty()

    def test_get_total_changes(self):
        """Test get_total_changes method."""
        mod = FileModification(
            path_after="file.py",
            modification_type="A",
            insertions=10,
            deletions=5,
        )
        diff = Diff(
            modifications=[mod],
            files_changed_count=1,
            insertions_count=10,
            deletions_count=5,
        )
        assert diff.get_total_changes() == 15

    def test_get_modification_types(self):
        """Test get_modification_types method."""
        mods = [
            FileModification(
                path_after="added.py",
                modification_type="A",
                insertions=10,
                deletions=0,
            ),
            FileModification(
                path_before="deleted.py",
                modification_type="D",
                insertions=0,
                deletions=5,
            ),
            FileModification(
                path_before="old.py",
                path_after="new.py",
                modification_type="R",
                insertions=2,
                deletions=1,
            ),
        ]
        diff = Diff(
            modifications=mods,
            files_changed_count=3,
            insertions_count=12,
            deletions_count=6,
        )
        assert diff.get_modification_types() == {"A", "D", "R"}

    def test_get_renamed_files(self):
        """Test get_renamed_files method."""
        mods = [
            FileModification(
                path_after="added.py",
                modification_type="A",
                insertions=10,
                deletions=0,
            ),
            FileModification(
                path_before="old.py",
                path_after="new.py",
                modification_type="R",
                insertions=2,
                deletions=1,
            ),
        ]
        diff = Diff(
            modifications=mods,
            files_changed_count=2,
            insertions_count=12,
            deletions_count=1,
        )
        renamed = diff.get_renamed_files()
        assert len(renamed) == 1
        assert renamed[0].modification_type == "R"

    def test_get_copied_files(self):
        """Test get_copied_files method."""
        mods = [
            FileModification(
                path_before="src.py",
                path_after="copy.py",
                modification_type="C",
                insertions=0,
                deletions=0,
            ),
            FileModification(
                path_after="added.py",
                modification_type="A",
                insertions=10,
                deletions=0,
            ),
        ]
        diff = Diff(
            modifications=mods,
            files_changed_count=2,
            insertions_count=10,
            deletions_count=0,
        )
        copied = diff.get_copied_files()
        assert len(copied) == 1
        assert copied[0].modification_type == "C"

    def test_get_all_affected_paths(self):
        """Test get_all_affected_paths method."""
        mod1 = FileModification(
            path_after="added.py",
            modification_type="A",
            insertions=5,
            deletions=0,
        )
        mod2 = FileModification(
            path_before="deleted.py",
            modification_type="D",
            insertions=0,
            deletions=3,
        )
        mod3 = FileModification(
            path_before="old.py",
            path_after="new.py",
            modification_type="R",
            insertions=1,
            deletions=1,
        )
        diff = Diff(
            modifications=[mod1, mod2, mod3],
            files_changed_count=3,
            insertions_count=6,
            deletions_count=4,
            affected_paths=[
                (None, "added.py"),
                ("deleted.py", None),
                ("old.py", "new.py"),
            ],
        )
        paths = diff.get_all_affected_paths()
        assert set(paths) == {"added.py", "deleted.py", "old.py", "new.py"}
        assert paths == sorted(paths)  # Should be sorted

    def test_string_representation(self):
        """Test string representations."""
        # Empty diff
        empty_diff = Diff(
            files_changed_count=0,
            insertions_count=0,
            deletions_count=0,
        )
        assert str(empty_diff) == "Empty diff"

        # Single file
        mod = FileModification(
            path_after="file.py",
            modification_type="A",
            insertions=10,
            deletions=5,
        )
        single_diff = Diff(
            modifications=[mod],
            files_changed_count=1,
            insertions_count=10,
            deletions_count=5,
        )
        assert str(single_diff) == "1 file changed, 10 insertions(+), 5 deletions(-)"

        # Multiple files
        mod2 = FileModification(
            path_after="file2.py",
            modification_type="A",
            insertions=15,
            deletions=0,
        )
        multi_diff = Diff(
            modifications=[mod, mod2],
            files_changed_count=2,
            insertions_count=25,
            deletions_count=5,
        )
        assert str(multi_diff) == "2 files changed, 25 insertions(+), 5 deletions(-)"

    def test_repr_format(self):
        """Test repr format."""
        mod = FileModification(
            path_after="file.py",
            modification_type="A",
            insertions=10,
            deletions=0,
        )
        diff = Diff(
            modifications=[mod],
            files_changed_count=1,
            insertions_count=10,
            deletions_count=0,
            affected_paths=[(None, "file.py")],
        )
        repr_str = repr(diff)
        assert "Diff(" in repr_str
        assert "files_changed=1" in repr_str
        assert "insertions=10" in repr_str
        assert "deletions=0" in repr_str
        assert "modifications_count=1" in repr_str
        assert "affected_paths_count=1" in repr_str


class TestDiffBusinessLogic:
    """Test Diff business logic validation."""

    def test_consistency_files_changed_with_modifications(self):
        """Test consistency between files_changed_count and modifications."""
        with pytest.raises(ValidationError, match="Must have modifications"):
            Diff(
                modifications=[],
                files_changed_count=1,  # Inconsistent with empty modifications
                insertions_count=0,
                deletions_count=0,
            )

    def test_consistency_line_counts_with_modifications(self):
        """Test consistency between line counts and modifications."""
        with pytest.raises(ValidationError, match="Must have modifications"):
            Diff(
                modifications=[],
                files_changed_count=0,
                insertions_count=5,  # Inconsistent with empty modifications
                deletions_count=0,
            )

        with pytest.raises(ValidationError, match="Must have modifications"):
            Diff(
                modifications=[],
                files_changed_count=0,
                insertions_count=0,
                deletions_count=3,  # Inconsistent with empty modifications
            )

    def test_valid_empty_diff_consistency(self):
        """Test that valid empty diff passes consistency checks."""
        diff = Diff(
            modifications=[],
            files_changed_count=0,
            insertions_count=0,
            deletions_count=0,
        )
        assert diff.is_empty()

    def test_valid_non_empty_diff_consistency(self):
        """Test that valid non-empty diff passes consistency checks."""
        mod = FileModification(
            path_after="file.py",
            modification_type="A",
            insertions=10,
            deletions=0,
        )
        diff = Diff(
            modifications=[mod],
            files_changed_count=1,
            insertions_count=10,
            deletions_count=0,
        )
        assert not diff.is_empty()
        assert diff.get_total_changes() == 10


class TestFileModificationEdgeCases:
    """Test edge cases for FileModification."""

    def test_all_modification_types(self):
        """Test all supported modification types."""
        types_and_configs = [
            ("A", {"path_after": "file.py"}),
            ("C", {"path_before": "src.py", "path_after": "copy.py"}),
            ("D", {"path_before": "file.py"}),
            ("M", {"path_before": "file.py", "path_after": "file.py"}),
            ("R", {"path_before": "old.py", "path_after": "new.py"}),
            ("T", {"path_before": "file", "path_after": "file"}),
            ("U", {"path_before": "conflict.py", "path_after": "conflict.py"}),
            ("X", {"path_before": "weird.py", "path_after": "weird.py"}),
            ("B", {"path_before": "broken.py", "path_after": "broken.py"}),
        ]

        for mod_type, paths in types_and_configs:
            mod = FileModification(
                modification_type=mod_type,  # type: ignore[arg-type]
                insertions=1,
                deletions=0,
                **paths,
            )
            assert mod.modification_type == mod_type

    def test_patch_field_optional(self):
        """Test that patch field is optional."""
        mod_without_patch = FileModification(
            path_after="file.py",
            modification_type="A",
            insertions=10,
            deletions=0,
        )
        assert mod_without_patch.patch is None

        mod_with_patch = FileModification(
            path_after="file.py",
            modification_type="A",
            insertions=10,
            deletions=0,
            patch="@@ -0,0 +1,3 @@\n+line1\n+line2\n+line3",
        )
        assert mod_with_patch.patch is not None

    def test_empty_path_normalization(self):
        """Test that empty/whitespace paths are normalized to None."""
        # Test the validator directly since business logic prevents invalid combinations
        assert FileModification.validate_file_paths("   ") is None
        assert FileModification.validate_file_paths("") is None


class TestDiffEdgeCases:
    """Test edge cases for Diff."""

    def test_complex_affected_paths(self):
        """Test complex affected paths scenarios."""
        mod1 = FileModification(
            path_after="added.py",
            modification_type="A",
            insertions=5,
            deletions=0,
        )
        mod2 = FileModification(
            path_before="deleted.py",
            modification_type="D",
            insertions=0,
            deletions=5,
        )
        mod3 = FileModification(
            path_before="old.py",
            path_after="new.py",
            modification_type="R",
            insertions=5,
            deletions=5,
        )
        mod4 = FileModification(
            path_before="file.py",
            path_after="file.py",
            modification_type="M",
            insertions=5,
            deletions=0,
        )
        diff = Diff(
            modifications=[mod1, mod2, mod3, mod4],
            files_changed_count=4,
            insertions_count=20,
            deletions_count=10,
            affected_paths=[
                (None, "added.py"),
                ("deleted.py", None),
                ("old.py", "new.py"),
                ("file.py", "file.py"),
            ],
        )
        paths = diff.get_all_affected_paths()
        expected = ["added.py", "deleted.py", "file.py", "new.py", "old.py"]
        assert paths == expected

    def test_large_diff_stats(self):
        """Test diff with large statistics."""
        mod = FileModification(
            path_after="large_file.py",
            modification_type="A",
            insertions=50000,
            deletions=25000,
        )
        diff = Diff(
            modifications=[mod],
            files_changed_count=1,
            insertions_count=50000,
            deletions_count=25000,
        )
        assert diff.get_total_changes() == 75000
        expected_str = "1 file changed, 50000 insertions(+), 25000 deletions(-)"
        assert str(diff) == expected_str


class TestFileModificationFactory:
    """Test FileModificationFactory functionality."""

    def test_default_creation(self):
        """Test factory creates valid default instances."""
        mod = FileModificationFactory.create()
        assert mod.modification_type == "M"
        assert mod.path_before == "src/file.py"
        assert mod.path_after == "src/file.py"
        assert mod.insertions == 5
        assert mod.deletions == 3

    def test_added_file_factory(self):
        """Test factory for added files."""
        mod = FileModificationFactory.create_added_file()
        assert mod.modification_type == "A"
        assert mod.path_before is None
        assert mod.path_after is not None
        assert mod.deletions == 0

    def test_deleted_file_factory(self):
        """Test factory for deleted files."""
        mod = FileModificationFactory.create_deleted_file()
        assert mod.modification_type == "D"
        assert mod.path_before is not None
        assert mod.path_after is None
        assert mod.insertions == 0

    def test_renamed_file_factory(self):
        """Test factory for renamed files."""
        mod = FileModificationFactory.create_renamed_file()
        assert mod.modification_type == "R"
        assert mod.path_before != mod.path_after
        assert mod.path_before is not None
        assert mod.path_after is not None

    def test_copied_file_factory(self):
        """Test factory for copied files."""
        mod = FileModificationFactory.create_copied_file()
        assert mod.modification_type == "C"
        assert mod.path_before != mod.path_after
        assert mod.path_before is not None
        assert mod.path_after is not None

    def test_overrides_work(self):
        """Test that factory overrides work correctly."""
        custom_path = "custom/path.py"
        mod = FileModificationFactory.create(path_after=custom_path)
        assert mod.path_after == custom_path

    def test_realistic_path_factory(self):
        """Test factory with realistic paths."""
        mod = FileModificationFactory.create_with_realistic_path()
        effective_path = mod.get_effective_path()
        # Should be one of our realistic paths
        from .test_data import FileTestData

        assert any(path in effective_path for path in FileTestData.REALISTIC_FILE_PATHS)

    def test_unicode_path_factory(self):
        """Test factory with Unicode paths."""
        mod = FileModificationFactory.create_with_unicode_path()
        effective_path = mod.get_effective_path()
        # Should contain non-ASCII characters
        assert any(ord(char) > 127 for char in effective_path)

    def test_scenario_factory(self):
        """Test factory with realistic scenarios."""
        mod = FileModificationFactory.create_from_scenario(0)
        # Should have realistic values from our test data
        assert mod.modification_type in ["A", "C", "D", "M", "R", "T", "U", "X", "B"]


class TestDiffFactory:
    """Test DiffFactory functionality."""

    def test_default_creation(self):
        """Test factory creates valid default instances."""
        diff = DiffFactory.create()
        assert diff.files_changed_count == 1
        assert len(diff.modifications) == 1
        assert diff.insertions_count > 0 or diff.deletions_count > 0

    def test_empty_diff_factory(self):
        """Test factory for empty diffs."""
        diff = DiffFactory.create_empty()
        assert diff.is_empty()
        assert diff.files_changed_count == 0
        assert len(diff.modifications) == 0

    def test_single_file_factory(self):
        """Test factory for single file diffs."""
        diff = DiffFactory.create_single_file()
        assert diff.files_changed_count == 1
        assert len(diff.modifications) == 1
        assert not diff.is_empty()

    def test_multi_file_factory(self):
        """Test factory for multi-file diffs."""
        file_count = 5
        diff = DiffFactory.create_multi_file(file_count)
        assert diff.files_changed_count == file_count
        assert len(diff.modifications) == file_count
        assert len(diff.affected_paths) == file_count

    def test_large_diff_factory(self):
        """Test factory for large diffs."""
        file_count = 50
        diff = DiffFactory.create_large_diff(file_count)
        assert diff.files_changed_count == file_count
        assert len(diff.modifications) == file_count

    def test_scenario_pattern_factory(self):
        """Test factory with scenario patterns."""
        diff = DiffFactory.create_from_scenario_pattern(0)
        assert diff.files_changed_count > 0
        assert len(diff.modifications) == diff.files_changed_count

    def test_overrides_work(self):
        """Test that factory overrides work correctly."""
        custom_count = 2
        diff = DiffFactory.create_multi_file(
            custom_count, files_changed_count=custom_count
        )
        assert diff.files_changed_count == custom_count

    def test_consistency_invariants(self):
        """Test that factory maintains consistency invariants."""
        diff = DiffFactory.create_multi_file(3)

        # Check that aggregated counts match individual modifications
        total_insertions = sum(mod.insertions for mod in diff.modifications)
        total_deletions = sum(mod.deletions for mod in diff.modifications)

        assert diff.insertions_count == total_insertions
        assert diff.deletions_count == total_deletions
        assert diff.files_changed_count == len(diff.modifications)

    def test_string_representation_edge_cases(self):
        """Test string representation edge cases for different change combinations."""
        # Only insertions, no deletions
        mod_only_insertions = FileModification(
            path_after="file.py",
            modification_type="A",
            insertions=5,
            deletions=0,
        )
        diff_only_insertions = Diff(
            modifications=[mod_only_insertions],
            files_changed_count=1,
            insertions_count=5,
            deletions_count=0,
        )
        assert str(diff_only_insertions) == "1 file changed, 5 insertions(+)"

        # Only deletions, no insertions
        mod_only_deletions = FileModification(
            path_before="file.py",
            modification_type="D",
            insertions=0,
            deletions=3,
        )
        diff_only_deletions = Diff(
            modifications=[mod_only_deletions],
            files_changed_count=1,
            insertions_count=0,
            deletions_count=3,
        )
        assert str(diff_only_deletions) == "1 file changed, 3 deletions(-)"

        # No line changes (e.g., file mode changes)
        mod_no_changes = FileModification(
            path_before="file.py",
            path_after="file.py",
            modification_type="T",
            insertions=0,
            deletions=0,
        )
        diff_no_changes = Diff(
            modifications=[mod_no_changes],
            files_changed_count=1,
            insertions_count=0,
            deletions_count=0,
        )
        assert str(diff_no_changes) == "1 file changed, no line changes"

    def test_get_effective_path_error_handling(self):
        """Test get_effective_path method error handling."""
        # We can't create a FileModification with both paths None due to validation,
        # but we can test the method logic by temporarily modifying an object
        mod = FileModificationFactory.create_added_file()

        # Test the method logic by setting both paths to None after creation
        # This simulates the edge case that the method needs to handle
        original_path_after = mod.path_after
        original_path_before = mod.path_before

        # Temporarily override the paths using object.__setattr__ to bypass immutability
        object.__setattr__(mod, "path_after", None)
        object.__setattr__(mod, "path_before", None)

        with pytest.raises(
            ValueError, match="FileModification must have at least one path"
        ):
            mod.get_effective_path()

        # Restore original values for cleanup
        object.__setattr__(mod, "path_after", original_path_after)
        object.__setattr__(mod, "path_before", original_path_before)
