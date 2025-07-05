"""Strategies for GitActor model."""

from datetime import datetime

from hypothesis import strategies as st

from auto_release_note_generation.data_models.shared import GitActor

from .base import SAFE_CHARACTERS, ValidationLimits, text_with_length


def valid_git_actor_name() -> st.SearchStrategy[str]:
    """Generate valid Git actor names.

    Returns:
        Strategy generating valid names (1-255 chars)
    """
    return text_with_length(
        min_length=ValidationLimits.NAME_MIN_LENGTH,
        max_length=ValidationLimits.NAME_MAX_LENGTH,
    )


def valid_git_actor_email() -> st.SearchStrategy[str]:
    """Generate valid Git actor emails.

    Git is very permissive with email formats, so we generate
    realistic patterns that Git would accept.

    Returns:
        Strategy generating valid email-like strings
    """
    # Standard email format
    standard_email = st.emails().map(str)

    # Git-style loose email format
    git_loose_email = st.text(
        min_size=ValidationLimits.EMAIL_MIN_LENGTH,
        max_size=50,  # Keep reasonable for testing
        alphabet=SAFE_CHARACTERS["email_safe"],
    ).filter(lambda x: len(x.strip()) > 0 and "@" in x)

    # Legacy/special formats Git accepts
    special_formats = st.sampled_from(
        [
            "user@localhost",
            "user@machine",
            "user@192.168.1.1",
            "user+tag@example.com",
            "first.last@example.com",
            "user@sub.domain.example.com",
        ]
    )

    return st.one_of(standard_email, git_loose_email, special_formats)


def realistic_git_actors() -> st.SearchStrategy[GitActor]:
    """Generate GitActor instances with realistic patterns.

    Returns:
        Strategy generating realistic GitActor instances
    """
    realistic_names = st.sampled_from(
        [
            "John Doe",
            "Jane Smith",
            "GitHub Actions",
            "Dependabot[bot]",
            "renovate[bot]",
            "José García",
            "李明",
            "Müller, Hans",
            "O'Brien, Patrick",
            "Jean-Pierre Dupont",
        ]
    )

    realistic_emails = st.sampled_from(
        [
            "john.doe@example.com",
            "jane@company.org",
            "actions@github.com",
            "49699333+dependabot[bot]@users.noreply.github.com",
            "bot@renovateapp.com",
            "user@localhost",
            "developer@192.168.1.1",
            "team+project@company.com",
        ]
    )

    return st.builds(
        GitActor,
        name=realistic_names,
        email=realistic_emails,
        timestamp=valid_git_timestamp(),
    )


def corporate_actor_patterns() -> st.SearchStrategy[GitActor]:
    """Generate GitActor instances with corporate patterns.

    Returns:
        Strategy generating corporate-style GitActor instances
    """
    corporate_patterns = [
        ("Jenkins CI", "jenkins@ci.company.com"),
        ("Build Bot", "buildbot@company.com"),
        ("Release Manager", "releases@company.org"),
        ("QA Team", "qa-team@company.com"),
        ("Security Scanner", "security-bot@company.com"),
        ("Merge Queue", "merge-queue@company.internal"),
    ]

    pattern = st.sampled_from(corporate_patterns)

    return pattern.flatmap(
        lambda p: st.builds(
            GitActor,
            name=st.just(p[0]),
            email=st.just(p[1]),
            timestamp=valid_git_timestamp(),
        )
    )


def valid_git_timestamp() -> st.SearchStrategy[datetime]:
    """Generate valid timestamps for Git operations.

    Returns:
        Strategy generating datetime objects with various timezones
    """
    return st.datetimes(
        min_value=datetime(1970, 1, 1),
        max_value=datetime(2100, 12, 31),
        timezones=st.one_of(
            st.none(),  # Naive datetime
            st.timezones(),  # Any timezone
        ),
    )


def valid_git_actor() -> st.SearchStrategy[GitActor]:
    """Generate valid GitActor instances.

    Returns:
        Strategy generating valid GitActor instances
    """
    return st.builds(
        GitActor,
        name=valid_git_actor_name(),
        email=valid_git_actor_email(),
        timestamp=valid_git_timestamp(),
    )


def invalid_actor_data() -> st.SearchStrategy[dict[str, str | datetime]]:
    """Generate invalid data for GitActor validation testing.

    Returns:
        Strategy generating dictionaries with invalid actor data
    """
    invalid_names = st.one_of(
        st.just(""),  # Empty
        st.just("   "),  # Whitespace only
        st.text(min_size=256),  # Too long
    )

    invalid_emails = st.one_of(
        st.just(""),  # Empty
        st.just("   "),  # Whitespace only
        st.text(min_size=321),  # Too long
    )

    # Generate various invalid combinations
    return st.one_of(
        # Invalid name
        st.builds(
            dict,
            name=invalid_names,
            email=valid_git_actor_email(),
            timestamp=valid_git_timestamp(),
        ),
        # Invalid email
        st.builds(
            dict,
            name=valid_git_actor_name(),
            email=invalid_emails,
            timestamp=valid_git_timestamp(),
        ),
        # Both invalid
        st.builds(
            dict,
            name=invalid_names,
            email=invalid_emails,
            timestamp=valid_git_timestamp(),
        ),
    )
