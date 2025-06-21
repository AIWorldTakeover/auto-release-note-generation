"""Hypothesis strategies for data model testing."""

from datetime import datetime

from hypothesis import strategies as st


class HypothesisStrategies:
    """Centralized hypothesis strategies for data model testing."""

    # Text-based strategies
    valid_names = st.text(
        min_size=1,
        max_size=255,
        alphabet=st.characters(blacklist_categories=("Cc", "Cs")),
    ).filter(lambda x: len(x.strip()) > 0)  # Ensure name isn't empty after stripping

    valid_emails = st.text(
        min_size=1,
        max_size=320,
        alphabet=st.characters(
            blacklist_categories=("Cc", "Cs"), blacklist_characters="\n\r\t"
        ),
    ).filter(lambda x: len(x.strip()) > 0)  # Ensure email isn't empty after stripping

    git_realistic_emails = st.one_of(
        st.emails().map(str),
        st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="@.-_+"
            ),
        ),
    )

    # Time-based strategies
    valid_timestamps = st.datetimes(
        min_value=datetime(1970, 1, 1),
        max_value=datetime(2100, 12, 31),
        timezones=st.one_of(st.none(), st.timezones()),
    )

    # Invalid data strategies
    invalid_names = st.one_of(
        st.just(""),
        st.text(min_size=256).filter(lambda x: len(x.strip()) > 255),
        st.just("   "),
    )

    invalid_emails = st.one_of(
        st.just(""),  # Empty string
        st.text(min_size=321).filter(
            lambda x: len(x.strip()) > 320
        ),  # Too long after stripping
        st.just("   "),  # Whitespace only
    )

    # GitSHA strategies
    valid_git_shas = st.text(
        min_size=4, max_size=64, alphabet="0123456789abcdef"
    ).filter(lambda x: len(x.strip()) >= 4)

    short_git_shas = st.text(min_size=4, max_size=12, alphabet="0123456789abcdef")

    full_git_shas = st.text(min_size=40, max_size=40, alphabet="0123456789abcdef")

    invalid_git_shas = st.one_of(
        st.just(""),  # Empty string
        st.text(min_size=1, max_size=3),  # Too short
        st.text(min_size=65, max_size=100),  # Too long
        st.text(
            min_size=4,
            max_size=64,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll"),
                blacklist_characters="abcdef0123456789",
            ),
        ),  # Invalid characters
    )

    # Parent SHA list strategies
    empty_parent_list: st.SearchStrategy[list[str]] = st.just([])

    single_parent_list: st.SearchStrategy[list[str]] = st.lists(
        st.text(min_size=4, max_size=40, alphabet="0123456789abcdef"),
        min_size=1,
        max_size=1,
    )

    merge_parent_list: st.SearchStrategy[list[str]] = st.lists(
        st.text(min_size=4, max_size=40, alphabet="0123456789abcdef"),
        min_size=2,
        max_size=8,
    )

    parent_sha_lists = st.one_of(
        empty_parent_list, single_parent_list, merge_parent_list
    )

    # GPG signature strategies
    valid_gpg_signatures = st.one_of(
        st.none(),
        st.text(min_size=1)
        .filter(lambda x: x.strip())
        .map(
            lambda x: (
                f"-----BEGIN PGP SIGNATURE-----\n{x.strip()}\n"
                "-----END PGP SIGNATURE-----"
            )
        ),
        st.text(min_size=1)
        .filter(lambda x: x.strip())
        .map(lambda x: f"gpgsig {x.strip()}"),
    )

    invalid_gpg_signatures = st.one_of(
        st.just(""),  # Empty string
        st.just("   "),  # Whitespace only
        st.text(min_size=1, max_size=100).filter(
            lambda x: x.strip() and not x.strip().startswith(("-----BEGIN", "gpgsig "))
        ),  # Invalid format
    )

    gpg_signatures = st.one_of(valid_gpg_signatures, invalid_gpg_signatures)

    # ChangeMetadata strategies
    valid_change_types = st.sampled_from(
        [
            "direct",
            "merge",
            "squash",
            "octopus",
            "rebase",
            "cherry-pick",
            "revert",
            "initial",
            "amend",
        ]
    )

    invalid_change_types = st.one_of(
        st.just(""),  # Empty string
        st.just("invalid"),  # Invalid type
        st.just("push"),  # Not in allowed types
        st.just("pull"),  # Not in allowed types
        st.just("fetch"),  # Not in allowed types
        st.text(min_size=1, max_size=20).filter(
            lambda x: x.strip()
            not in [
                "direct",
                "merge",
                "squash",
                "octopus",
                "rebase",
                "cherry-pick",
                "revert",
                "initial",
                "amend",
            ]
        ),  # Any other string not in valid types
    )

    valid_branch_names = st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_/."
        ),
    ).filter(
        lambda x: (
            len(x.strip()) > 0
            and not x.startswith("/")
            and not x.endswith("/")
            and "//" not in x
            and not any(c in x for c in [" ", "\t", "\n", "\r"])
        )
    )

    invalid_branch_names = st.one_of(
        st.just(""),  # Empty string
        st.just("  "),  # Whitespace only
        st.text(min_size=1, max_size=50).filter(
            lambda x: (
                " " in x.strip()
                or "\t" in x.strip()
                or "\n" in x.strip()
                or x.strip().startswith("/")
                or x.strip().endswith("/")
                or "//" in x.strip()
                or not x.strip()  # Empty after stripping
            )
        ),  # Invalid characters or patterns that persist after stripping
    )

    # Enhanced source branch list strategies
    empty_source_branches: st.SearchStrategy[list[str]] = st.just([])

    single_source_branch = st.lists(valid_branch_names, min_size=1, max_size=1)

    multiple_source_branches = st.lists(valid_branch_names, min_size=2, max_size=8)

    source_branch_lists = st.one_of(single_source_branch, multiple_source_branches)

    # Reuse empty_source_branches strategy for consistency
    empty_source_branch_lists = empty_source_branches

    # Enhanced PR ID strategies
    valid_pull_request_ids = st.one_of(
        st.none(),
        st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="-_"
            ),
        ).filter(lambda x: len(x.strip()) > 0),
    )

    # Merge base strategies (reuse GitSHA strategies)
    valid_merge_bases = st.one_of(st.none(), valid_git_shas)

    # FileModification strategies
    valid_file_paths = st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="/-_."
        ),
    ).filter(
        lambda x: (
            len(x.strip()) > 0
            and "\x00" not in x  # No null bytes
            and len(x.strip().replace("\\", "/")) <= 4096  # Under path limit
        )
    )

    # File path edge cases for testing validation
    invalid_file_paths = st.one_of(
        st.just(""),  # Empty string
        st.just("  "),  # Whitespace only
        st.text(min_size=4097, max_size=5000),  # Too long
        st.text(min_size=1, max_size=20).filter(
            lambda x: "\x00" in x  # Contains null bytes
        ),
    )

    # Unicode and special character paths for edge case testing
    unicode_file_paths = st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd", "Pc", "Pd"),
            whitelist_characters="/-_.αβγδεζηθικλμνξοπρστυφχψω中文日本語한글",
        ),
    ).filter(lambda x: len(x.strip()) > 0 and "\x00" not in x)

    # Modification type strategies
    valid_modification_types = st.sampled_from(
        [
            "A",  # Addition
            "C",  # Copy
            "D",  # Deletion
            "M",  # Modification
            "R",  # Rename
            "T",  # Type change
            "U",  # Unmerged
            "X",  # Unknown
            "B",  # Broken pairing
        ]
    )

    invalid_modification_types = st.one_of(
        st.just(""),  # Empty string
        st.just("Z"),  # Invalid type
        st.text(min_size=1, max_size=5).filter(
            lambda x: x.upper() not in ["A", "C", "D", "M", "R", "T", "U", "X", "B"]
        ),
    )

    # Line count strategies
    valid_line_counts = st.integers(min_value=0, max_value=10000)

    # Large line counts for stress testing
    large_line_counts = st.integers(min_value=10000, max_value=100000)

    invalid_line_counts = st.integers(max_value=-1)

    # Patch content strategies
    valid_patch_content = st.one_of(
        st.none(),
        st.text(min_size=1, max_size=1000).filter(lambda x: x.strip()),
        # Realistic patch format
        st.builds(
            lambda added, removed: (
                f"@@ -1,{removed} +1,{added} @@\n"
                + "\n".join([f"-old_line_{i}" for i in range(min(removed, 5))])
                + "\n"
                + "\n".join([f"+new_line_{i}" for i in range(min(added, 5))])
            ),
            st.integers(min_value=0, max_value=10),
            st.integers(min_value=0, max_value=10),
        ),
    )

    # Simple file modification dictionaries for testing
    valid_added_file_data = st.builds(
        lambda path_after, insertions, patch: {
            "path_before": None,
            "path_after": path_after,
            "modification_type": "A",
            "insertions": insertions,
            "deletions": 0,
            "patch": patch,
        },
        valid_file_paths,
        valid_line_counts,
        valid_patch_content,
    )

    valid_deleted_file_data = st.builds(
        lambda path_before, deletions, patch: {
            "path_before": path_before,
            "path_after": None,
            "modification_type": "D",
            "insertions": 0,
            "deletions": deletions,
            "patch": patch,
        },
        valid_file_paths,
        valid_line_counts,
        valid_patch_content,
    )

    valid_modified_file_data = st.builds(
        lambda path, insertions, deletions, patch: {
            "path_before": path,
            "path_after": path,
            "modification_type": "M",
            "insertions": insertions,
            "deletions": deletions,
            "patch": patch,
        },
        valid_file_paths,
        valid_line_counts,
        valid_line_counts,
        valid_patch_content,
    )

    # Combined strategy for any valid file modification
    valid_file_modification_data = st.one_of(
        valid_added_file_data,
        valid_deleted_file_data,
        valid_modified_file_data,
    )
