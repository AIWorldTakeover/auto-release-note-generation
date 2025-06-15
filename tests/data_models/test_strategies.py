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
