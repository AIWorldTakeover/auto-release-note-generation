"""Strategies for FileModification and Diff models."""

from hypothesis import strategies as st

from auto_release_note_generation.data_models.shared import Diff, FileModification

from .base import SAFE_CHARACTERS, ValidationLimits


def valid_file_path() -> st.SearchStrategy[str]:
    """Generate valid file paths.

    Returns:
        Strategy generating valid file paths
    """
    return st.text(
        min_size=1,
        max_size=100,  # Keep reasonable for testing
        alphabet=SAFE_CHARACTERS["path_safe"],
    ).filter(
        lambda x: (
            len(x.strip()) > 0
            and "\x00" not in x  # No null bytes
            and len(x.strip().replace("\\", "/")) <= ValidationLimits.PATH_MAX_LENGTH
        )
    )


def unicode_file_path() -> st.SearchStrategy[str]:
    """Generate file paths with unicode characters.

    Returns:
        Strategy generating unicode file paths
    """
    unicode_chars = st.characters(
        whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Pd"),
        whitelist_characters="/-_.αβγδεζηθικλμνξοπρστυφχψω中文日本語한글",
    )

    return st.text(
        min_size=1,
        max_size=50,
        alphabet=unicode_chars,
    ).filter(lambda x: len(x.strip()) > 0 and "\x00" not in x)


def valid_line_counts() -> st.SearchStrategy[int]:
    """Generate valid line count values.

    Returns:
        Strategy generating non-negative integers
    """
    return st.integers(min_value=0, max_value=10000)


def valid_patch_content() -> st.SearchStrategy[str | None]:
    """Generate valid patch content.

    Returns:
        Strategy generating unified diff patches or None
    """
    # Simple patch format
    simple_patch = st.builds(
        lambda added, removed: (
            f"@@ -1,{removed} +1,{added} @@\n"
            + "\n".join([f"-old_line_{i}" for i in range(min(removed, 5))])
            + ("\n" if removed > 0 else "")
            + "\n".join([f"+new_line_{i}" for i in range(min(added, 5))])
        ),
        st.integers(min_value=0, max_value=10),
        st.integers(min_value=0, max_value=10),
    )

    # Any non-empty text as patch
    text_patch = st.text(min_size=1, max_size=1000).filter(lambda x: x.strip())

    return st.one_of(
        st.none(),  # No patch
        simple_patch,
        text_patch,
    )


# FileModification type-specific strategies
def added_file() -> st.SearchStrategy[FileModification]:
    """Generate FileModification for added files (type A).

    Returns:
        Strategy generating added file modifications
    """
    return st.builds(
        FileModification,
        path_before=st.none(),  # No path before
        path_after=valid_file_path(),
        modification_type=st.just("A"),
        insertions=valid_line_counts(),
        deletions=st.just(0),  # No deletions for new files
        patch=valid_patch_content(),
    )


def deleted_file() -> st.SearchStrategy[FileModification]:
    """Generate FileModification for deleted files (type D).

    Returns:
        Strategy generating deleted file modifications
    """
    return st.builds(
        FileModification,
        path_before=valid_file_path(),
        path_after=st.none(),  # No path after
        modification_type=st.just("D"),
        insertions=st.just(0),  # No insertions for deleted files
        deletions=valid_line_counts(),
        patch=valid_patch_content(),
    )


def modified_file() -> st.SearchStrategy[FileModification]:
    """Generate FileModification for modified files (type M).

    Returns:
        Strategy generating modified file modifications
    """
    return valid_file_path().flatmap(
        lambda path: st.builds(
            FileModification,
            path_before=st.just(path),
            path_after=st.just(path),  # Same path
            modification_type=st.just("M"),
            insertions=valid_line_counts(),
            deletions=valid_line_counts(),
            patch=valid_patch_content(),
        )
    )


def renamed_file() -> st.SearchStrategy[FileModification]:
    """Generate FileModification for renamed files (type R).

    Returns:
        Strategy generating renamed file modifications
    """
    paths = st.tuples(valid_file_path(), valid_file_path()).filter(
        lambda p: p[0] != p[1]  # Different paths
    )

    return paths.flatmap(
        lambda p: st.builds(
            FileModification,
            path_before=st.just(p[0]),
            path_after=st.just(p[1]),
            modification_type=st.just("R"),
            insertions=valid_line_counts(),
            deletions=valid_line_counts(),
            patch=valid_patch_content(),
        )
    )


def copied_file() -> st.SearchStrategy[FileModification]:
    """Generate FileModification for copied files (type C).

    Returns:
        Strategy generating copied file modifications
    """
    paths = st.tuples(valid_file_path(), valid_file_path()).filter(
        lambda p: p[0] != p[1]  # Different paths
    )

    return paths.flatmap(
        lambda p: st.builds(
            FileModification,
            path_before=st.just(p[0]),
            path_after=st.just(p[1]),
            modification_type=st.just("C"),
            insertions=valid_line_counts(),
            deletions=st.just(0),  # Copies usually have no deletions
            patch=valid_patch_content(),
        )
    )


def valid_file_modification() -> st.SearchStrategy[FileModification]:
    """Generate valid FileModification instances.

    Returns:
        Strategy generating valid FileModification instances
    """
    return st.one_of(
        added_file(),
        deleted_file(),
        modified_file(),
        renamed_file(),
        copied_file(),
        # Other types (T, U, X, B) with similar logic
        st.builds(
            FileModification,
            path_before=st.one_of(st.none(), valid_file_path()),
            path_after=valid_file_path(),
            modification_type=st.sampled_from(["T", "U", "X", "B"]),
            insertions=valid_line_counts(),
            deletions=valid_line_counts(),
            patch=valid_patch_content(),
        ),
    )


def invalid_file_modification_data() -> st.SearchStrategy[dict[str, str | int | None]]:
    """Generate invalid FileModification data for validation testing.

    Returns:
        Strategy generating dictionaries with invalid file modification data
    """
    invalid_paths = st.one_of(
        st.just(""),  # Empty
        st.just("  "),  # Whitespace only
        st.text(min_size=4097, max_size=5000),  # Too long
        st.text(min_size=1, max_size=20).filter(
            lambda x: "\x00" in x  # Contains null bytes
        ),
    )

    return st.one_of(
        # Added file with path_before
        st.builds(
            dict,
            path_before=valid_file_path(),
            path_after=valid_file_path(),
            modification_type=st.just("A"),
            insertions=valid_line_counts(),
            deletions=st.just(0),
        ),
        # Deleted file with path_after
        st.builds(
            dict,
            path_before=valid_file_path(),
            path_after=valid_file_path(),
            modification_type=st.just("D"),
            insertions=st.just(0),
            deletions=valid_line_counts(),
        ),
        # Renamed with same paths
        valid_file_path().flatmap(
            lambda path: st.builds(
                dict,
                path_before=st.just(path),
                path_after=st.just(path),
                modification_type=st.just("R"),
                insertions=valid_line_counts(),
                deletions=valid_line_counts(),
            )
        ),
        # Invalid paths
        st.builds(
            dict,
            path_before=st.one_of(st.none(), invalid_paths),
            path_after=invalid_paths,
            modification_type=st.sampled_from(["A", "M", "D", "R", "C"]),
            insertions=valid_line_counts(),
            deletions=valid_line_counts(),
        ),
        # Negative line counts
        st.builds(
            dict,
            path_before=st.one_of(st.none(), valid_file_path()),
            path_after=st.one_of(st.none(), valid_file_path()),
            modification_type=st.sampled_from(["A", "M", "D"]),
            insertions=st.integers(max_value=-1),
            deletions=st.integers(max_value=-1),
        ),
    )


# Diff strategies
def empty_diff() -> st.SearchStrategy[Diff]:
    """Generate empty Diff instances.

    Returns:
        Strategy generating empty diffs
    """
    return st.builds(
        Diff,
        modifications=st.just([]),
        files_changed_count=st.just(0),
        insertions_count=st.just(0),
        deletions_count=st.just(0),
        affected_paths=st.just([]),
    )


def single_file_diff() -> st.SearchStrategy[Diff]:
    """Generate Diff with single file modification.

    Returns:
        Strategy generating single-file diffs
    """
    return valid_file_modification().flatmap(
        lambda mod: st.builds(
            Diff,
            modifications=st.just([mod]),
            files_changed_count=st.just(1),
            insertions_count=st.just(mod.insertions),
            deletions_count=st.just(mod.deletions),
            affected_paths=st.just([(mod.path_before, mod.path_after)]),
        )
    )


def multi_file_diff() -> st.SearchStrategy[Diff]:
    """Generate Diff with multiple file modifications.

    Returns:
        Strategy generating multi-file diffs
    """
    modifications = st.lists(valid_file_modification(), min_size=2, max_size=10)

    return modifications.flatmap(
        lambda mods: st.builds(
            Diff,
            modifications=st.just(mods),
            files_changed_count=st.just(len(mods)),
            insertions_count=st.just(sum(m.insertions for m in mods)),
            deletions_count=st.just(sum(m.deletions for m in mods)),
            affected_paths=st.just([(m.path_before, m.path_after) for m in mods]),
        )
    )


def large_diff() -> st.SearchStrategy[Diff]:
    """Generate large Diff instances for stress testing.

    Returns:
        Strategy generating large diffs
    """
    modifications = st.lists(valid_file_modification(), min_size=50, max_size=100)

    return modifications.flatmap(
        lambda mods: st.builds(
            Diff,
            modifications=st.just(mods),
            files_changed_count=st.just(len(mods)),
            insertions_count=st.just(sum(m.insertions for m in mods)),
            deletions_count=st.just(sum(m.deletions for m in mods)),
            affected_paths=st.just([(m.path_before, m.path_after) for m in mods]),
        )
    )


def valid_diff() -> st.SearchStrategy[Diff]:
    """Generate valid Diff instances.

    Returns:
        Strategy generating valid Diff instances
    """
    return st.one_of(
        empty_diff(),
        single_file_diff(),
        multi_file_diff(),
    )
