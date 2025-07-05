"""Strategies for Commit model."""

from hypothesis import strategies as st

from auto_release_note_generation.data_models.commit import Commit

from .base import non_empty_text
from .files import valid_diff
from .metadata import merge_commit_metadata, root_commit_metadata, valid_git_metadata


def valid_commit_summary() -> st.SearchStrategy[str]:
    """Generate valid commit summaries (first line of message).

    Returns:
        Strategy generating valid commit summaries
    """
    return non_empty_text(min_size=1, max_size=100)


def valid_commit_message() -> st.SearchStrategy[str]:
    """Generate valid full commit messages.

    Returns:
        Strategy generating valid commit messages
    """
    # Single line messages
    single_line = valid_commit_summary()

    # Multi-line messages
    multi_line = st.builds(
        lambda summary, body: f"{summary}\n\n{body}",
        valid_commit_summary(),
        non_empty_text(min_size=1, max_size=500),
    )

    return st.one_of(single_line, multi_line)


def conventional_commit_message() -> st.SearchStrategy[str]:
    """Generate conventional commit format messages.

    Returns:
        Strategy generating conventional commit messages
    """
    types = st.sampled_from(
        [
            "feat",
            "fix",
            "docs",
            "style",
            "refactor",
            "perf",
            "test",
            "build",
            "ci",
            "chore",
            "revert",
        ]
    )

    scopes = st.one_of(
        st.none(),  # No scope
        st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(
                whitelist_categories=["Ll"],
                whitelist_characters="-",
            ),
        ),
    )

    breaking = st.booleans()

    description = non_empty_text(min_size=1, max_size=50)

    body = st.one_of(
        st.just(""),  # No body
        non_empty_text(min_size=1, max_size=200),
    )

    footer = st.one_of(
        st.just(""),  # No footer
        st.builds(
            lambda ref, desc: f"Closes #{ref}: {desc}",
            st.integers(min_value=1, max_value=9999),
            non_empty_text(min_size=1, max_size=50),
        ),
    )

    return st.builds(
        lambda type_, scope, breaking, desc, body, footer: (
            f"{type_}"
            + (f"({scope})" if scope else "")
            + ("!" if breaking else "")
            + f": {desc}"
            + (f"\n\n{body}" if body else "")
            + (f"\n\n{footer}" if footer else "")
        ),
        types,
        scopes,
        breaking,
        description,
        body,
        footer,
    )


def valid_branch_names() -> st.SearchStrategy[list[str]]:
    """Generate lists of valid branch names.

    Returns:
        Strategy generating lists of branch names
    """
    branch_name = st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="-_/.",
        ),
    ).filter(
        lambda x: (
            len(x.strip()) > 0
            and not x.startswith("/")
            and not x.endswith("/")
            and "//" not in x
        )
    )

    return st.lists(branch_name, min_size=0, max_size=5)


def valid_tag_names() -> st.SearchStrategy[list[str]]:
    """Generate lists of valid tag names.

    Returns:
        Strategy generating lists of tag names
    """
    # Semantic version tags
    semver = st.builds(
        lambda major, minor, patch: f"v{major}.{minor}.{patch}",
        st.integers(min_value=0, max_value=99),
        st.integers(min_value=0, max_value=99),
        st.integers(min_value=0, max_value=999),
    )

    # Release tags
    release = st.builds(
        lambda name, version: f"{name}-{version}",
        st.sampled_from(["release", "rel", "prod", "stable"]),
        st.text(
            min_size=1,
            max_size=20,
            alphabet=st.characters(
                whitelist_categories=("Ll", "Nd"),
                whitelist_characters=".-",
            ),
        ),
    )

    # Any valid tag
    any_tag = st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd"),
            whitelist_characters="-_./",
        ),
    ).filter(lambda x: len(x.strip()) > 0)

    tag_name = st.one_of(semver, release, any_tag)

    return st.lists(tag_name, min_size=0, max_size=3)


def valid_commit() -> st.SearchStrategy[Commit]:
    """Generate valid Commit instances.

    Returns:
        Strategy generating valid Commit instances
    """
    return st.builds(
        Commit,
        metadata=valid_git_metadata(),
        summary=valid_commit_summary(),
        message=valid_commit_message(),
        branches=valid_branch_names(),
        tags=valid_tag_names(),
        diff=valid_diff(),
        ai_summary=st.one_of(st.none(), non_empty_text(min_size=10, max_size=200)),
    )


def merge_commit() -> st.SearchStrategy[Commit]:
    """Generate merge Commit instances.

    Returns:
        Strategy generating merge commits
    """
    # Merge commit messages often have specific patterns
    merge_summary = st.one_of(
        st.builds(
            lambda branch: f"Merge branch '{branch}'",
            st.text(
                min_size=1,
                max_size=30,
                alphabet=st.characters(
                    whitelist_categories=("Lu", "Ll", "Nd"),
                    whitelist_characters="-_/",
                ),
            ),
        ),
        st.builds(
            lambda pr: f"Merge pull request #{pr}",
            st.integers(min_value=1, max_value=9999),
        ),
        valid_commit_summary(),  # Or any summary
    )

    return st.builds(
        Commit,
        metadata=merge_commit_metadata(),  # 2+ parents
        summary=merge_summary,
        message=valid_commit_message(),
        branches=valid_branch_names(),
        tags=valid_tag_names(),
        diff=valid_diff(),
        ai_summary=st.one_of(st.none(), non_empty_text(min_size=10, max_size=200)),
    )


def root_commit() -> st.SearchStrategy[Commit]:
    """Generate root Commit instances (initial commits).

    Returns:
        Strategy generating root commits
    """
    # Root commits often have specific messages
    root_summary = st.one_of(
        st.just("Initial commit"),
        st.just("Initialize repository"),
        st.just("Initial import"),
        st.just("Project initialization"),
        valid_commit_summary(),  # Or any summary
    )

    return st.builds(
        Commit,
        metadata=root_commit_metadata(),  # No parents
        summary=root_summary,
        message=valid_commit_message(),
        branches=valid_branch_names(),
        tags=valid_tag_names(),
        diff=valid_diff(),
        ai_summary=st.none(),  # Usually no AI summary for initial commits
    )


def commit_with_ai_summary() -> st.SearchStrategy[Commit]:
    """Generate Commit instances with AI summaries.

    Returns:
        Strategy generating commits with AI summaries
    """
    ai_summaries = st.one_of(
        # Structured summary
        st.builds(
            lambda type_, desc, impact: (
                f"Type: {type_}\nDescription: {desc}\nImpact: {impact}"
            ),
            st.sampled_from(["Feature", "Bug Fix", "Refactor", "Documentation"]),
            non_empty_text(min_size=10, max_size=100),
            st.sampled_from(["Low", "Medium", "High", "Critical"]),
        ),
        # Natural language summary
        non_empty_text(min_size=20, max_size=300),
        # Bullet points
        st.lists(
            non_empty_text(min_size=10, max_size=50),
            min_size=2,
            max_size=5,
        ).map(lambda items: "\n".join(f"• {item}" for item in items)),
    )

    return st.builds(
        Commit,
        metadata=valid_git_metadata(),
        summary=valid_commit_summary(),
        message=valid_commit_message(),
        branches=valid_branch_names(),
        tags=valid_tag_names(),
        diff=valid_diff(),
        ai_summary=ai_summaries,
    )
