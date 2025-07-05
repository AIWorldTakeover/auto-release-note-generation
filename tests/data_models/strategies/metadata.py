"""Strategies for GitMetadata and ChangeMetadata models."""

from hypothesis import strategies as st

from auto_release_note_generation.data_models.shared import ChangeMetadata, GitMetadata

from .actors import valid_git_actor
from .base import SAFE_CHARACTERS, ValidationLimits
from .utils import valid_git_sha, valid_gpg_signature


# GitMetadata Strategies
def valid_git_metadata() -> st.SearchStrategy[GitMetadata]:
    """Generate valid GitMetadata instances.

    Returns:
        Strategy generating valid GitMetadata instances
    """
    return st.builds(
        GitMetadata,
        sha=valid_git_sha(),
        author=valid_git_actor(),
        committer=valid_git_actor(),
        parents=st.lists(valid_git_sha(), min_size=0, max_size=8),
        gpg_signature=valid_gpg_signature(),
    )


def root_commit_metadata() -> st.SearchStrategy[GitMetadata]:
    """Generate GitMetadata for root commits (no parents).

    Returns:
        Strategy generating root commit metadata
    """
    return st.builds(
        GitMetadata,
        sha=valid_git_sha(),
        author=valid_git_actor(),
        committer=valid_git_actor(),
        parents=st.just([]),  # No parents
        gpg_signature=valid_gpg_signature(),
    )


def merge_commit_metadata() -> st.SearchStrategy[GitMetadata]:
    """Generate GitMetadata for merge commits (multiple parents).

    Returns:
        Strategy generating merge commit metadata
    """
    return st.builds(
        GitMetadata,
        sha=valid_git_sha(),
        author=valid_git_actor(),
        committer=valid_git_actor(),
        parents=st.lists(valid_git_sha(), min_size=2, max_size=8),  # 2+ parents
        gpg_signature=valid_gpg_signature(),
    )


def signed_commit_metadata() -> st.SearchStrategy[GitMetadata]:
    """Generate GitMetadata for signed commits.

    Returns:
        Strategy generating signed commit metadata
    """
    return st.builds(
        GitMetadata,
        sha=valid_git_sha(),
        author=valid_git_actor(),
        committer=valid_git_actor(),
        parents=st.lists(valid_git_sha(), min_size=0, max_size=2),
        gpg_signature=valid_gpg_signature().filter(lambda x: x is not None),
    )


# ChangeMetadata Strategies
def valid_branch_name() -> st.SearchStrategy[str]:
    """Generate valid Git branch names.

    Returns:
        Strategy generating valid branch names
    """
    return st.text(
        min_size=ValidationLimits.BRANCH_NAME_MIN_LENGTH,
        max_size=100,
        alphabet=SAFE_CHARACTERS["branch_safe"],
    ).filter(
        lambda x: (
            len(x.strip()) > 0
            and not x.startswith("/")
            and not x.endswith("/")
            and "//" not in x
            and not any(c in x for c in [" ", "\t", "\n", "\r"])
        )
    )


def valid_pr_id() -> st.SearchStrategy[str | None]:
    """Generate valid pull request IDs.

    Returns:
        Strategy generating valid PR IDs or None
    """
    pr_formats = st.one_of(
        # GitHub style
        st.integers(min_value=1, max_value=99999).map(lambda x: f"#{x}"),
        # GitLab style
        st.integers(min_value=1, max_value=99999).map(lambda x: f"!{x}"),
        # Jira style
        st.tuples(
            st.sampled_from(["PROJ", "ISSUE", "FEAT", "BUG"]),
            st.integers(min_value=1, max_value=9999),
        ).map(lambda x: f"{x[0]}-{x[1]}"),
        # Generic ID
        st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"),
                whitelist_characters="-_",
            ),
        ).filter(lambda x: len(x.strip()) > 0),
    )

    return st.one_of(st.none(), pr_formats)


# Change type specific strategies
def direct_change() -> st.SearchStrategy[ChangeMetadata]:
    """Generate ChangeMetadata for direct commits.

    Returns:
        Strategy generating direct change metadata
    """
    return st.builds(
        ChangeMetadata,
        change_type=st.just("direct"),
        source_branches=st.one_of(
            st.just([]),  # No source
            st.lists(valid_branch_name(), min_size=1, max_size=1),  # Single source
        ),
        target_branch=valid_branch_name(),
        merge_base=st.one_of(st.none(), valid_git_sha()),
        pull_request_id=valid_pr_id(),
    )


def merge_change() -> st.SearchStrategy[ChangeMetadata]:
    """Generate ChangeMetadata for merge commits.

    Returns:
        Strategy generating merge change metadata
    """
    return st.builds(
        ChangeMetadata,
        change_type=st.just("merge"),
        source_branches=st.lists(valid_branch_name(), min_size=1, max_size=1),
        target_branch=valid_branch_name(),
        merge_base=st.one_of(st.none(), valid_git_sha()),
        pull_request_id=valid_pr_id(),
    )


def squash_change() -> st.SearchStrategy[ChangeMetadata]:
    """Generate ChangeMetadata for squash merges.

    Returns:
        Strategy generating squash change metadata
    """
    return st.builds(
        ChangeMetadata,
        change_type=st.just("squash"),
        source_branches=st.lists(valid_branch_name(), min_size=1, max_size=1),
        target_branch=valid_branch_name(),
        merge_base=st.one_of(st.none(), valid_git_sha()),
        pull_request_id=valid_pr_id(),
    )


def octopus_change() -> st.SearchStrategy[ChangeMetadata]:
    """Generate ChangeMetadata for octopus merges.

    Returns:
        Strategy generating octopus change metadata
    """
    return st.builds(
        ChangeMetadata,
        change_type=st.just("octopus"),
        source_branches=st.lists(valid_branch_name(), min_size=2, max_size=8),
        target_branch=valid_branch_name(),
        merge_base=st.one_of(st.none(), valid_git_sha()),
        pull_request_id=valid_pr_id(),
    )


def rebase_change() -> st.SearchStrategy[ChangeMetadata]:
    """Generate ChangeMetadata for rebased commits.

    Returns:
        Strategy generating rebase change metadata
    """
    return st.builds(
        ChangeMetadata,
        change_type=st.just("rebase"),
        source_branches=st.one_of(
            st.just([]),
            st.lists(valid_branch_name(), min_size=1, max_size=1),
        ),
        target_branch=valid_branch_name(),
        merge_base=st.one_of(st.none(), valid_git_sha()),
        pull_request_id=valid_pr_id(),
    )


def cherry_pick_change() -> st.SearchStrategy[ChangeMetadata]:
    """Generate ChangeMetadata for cherry-picked commits.

    Returns:
        Strategy generating cherry-pick change metadata
    """
    return st.builds(
        ChangeMetadata,
        change_type=st.just("cherry-pick"),
        source_branches=st.one_of(
            st.just([]),
            st.lists(valid_branch_name(), min_size=1, max_size=1),
        ),
        target_branch=valid_branch_name(),
        merge_base=st.one_of(st.none(), valid_git_sha()),
        pull_request_id=valid_pr_id(),
    )


def revert_change() -> st.SearchStrategy[ChangeMetadata]:
    """Generate ChangeMetadata for reverted commits.

    Returns:
        Strategy generating revert change metadata
    """
    return st.builds(
        ChangeMetadata,
        change_type=st.just("revert"),
        source_branches=st.one_of(
            st.just([]),
            st.lists(valid_branch_name(), min_size=1, max_size=1),
        ),
        target_branch=valid_branch_name(),
        merge_base=st.one_of(st.none(), valid_git_sha()),
        pull_request_id=valid_pr_id(),
    )


def initial_change() -> st.SearchStrategy[ChangeMetadata]:
    """Generate ChangeMetadata for initial commits.

    Returns:
        Strategy generating initial change metadata
    """
    return st.builds(
        ChangeMetadata,
        change_type=st.just("initial"),
        source_branches=st.just([]),  # No source branches
        target_branch=valid_branch_name(),
        merge_base=st.none(),  # No merge base
        pull_request_id=st.none(),  # Usually no PR
    )


def amend_change() -> st.SearchStrategy[ChangeMetadata]:
    """Generate ChangeMetadata for amended commits.

    Returns:
        Strategy generating amend change metadata
    """
    return st.builds(
        ChangeMetadata,
        change_type=st.just("amend"),
        source_branches=st.one_of(
            st.just([]),
            st.lists(valid_branch_name(), min_size=1, max_size=1),
        ),
        target_branch=valid_branch_name(),
        merge_base=st.one_of(st.none(), valid_git_sha()),
        pull_request_id=valid_pr_id(),
    )


def valid_change_metadata() -> st.SearchStrategy[ChangeMetadata]:
    """Generate valid ChangeMetadata instances.

    Returns:
        Strategy generating valid ChangeMetadata instances
    """
    return st.one_of(
        direct_change(),
        merge_change(),
        squash_change(),
        octopus_change(),
        rebase_change(),
        cherry_pick_change(),
        revert_change(),
        initial_change(),
        amend_change(),
    )


def invalid_change_metadata() -> st.SearchStrategy[dict[str, str | list[str] | None]]:
    """Generate invalid ChangeMetadata data for validation testing.

    Returns:
        Strategy generating dictionaries with invalid change metadata
    """
    # Invalid branch names
    invalid_branch = st.one_of(
        st.just(""),  # Empty
        st.just("   "),  # Whitespace only
        st.just("/branch"),  # Starts with /
        st.just("branch/"),  # Ends with /
        st.just("branch//name"),  # Contains //
        st.just("branch name"),  # Contains space
        st.just("branch\tname"),  # Contains tab
    )

    # Invalid combinations
    return st.one_of(
        # Direct with multiple sources
        st.builds(
            dict,
            change_type=st.just("direct"),
            source_branches=st.lists(valid_branch_name(), min_size=2, max_size=5),
            target_branch=valid_branch_name(),
        ),
        # Merge with no sources
        st.builds(
            dict,
            change_type=st.just("merge"),
            source_branches=st.just([]),
            target_branch=valid_branch_name(),
        ),
        # Octopus with single source
        st.builds(
            dict,
            change_type=st.just("octopus"),
            source_branches=st.lists(valid_branch_name(), min_size=1, max_size=1),
            target_branch=valid_branch_name(),
        ),
        # Initial with sources
        st.builds(
            dict,
            change_type=st.just("initial"),
            source_branches=st.lists(valid_branch_name(), min_size=1, max_size=3),
            target_branch=valid_branch_name(),
        ),
        # Invalid target branch
        st.builds(
            dict,
            change_type=st.sampled_from(["direct", "merge", "squash"]),
            source_branches=st.lists(valid_branch_name(), min_size=0, max_size=2),
            target_branch=invalid_branch,
        ),
    )
