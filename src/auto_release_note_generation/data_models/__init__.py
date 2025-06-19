"""Data models for Git repository analysis and release note generation.

This package contains Pydantic models for representing Git data structures
across three main levels: Commit → LogicalChange → Release.
"""

# Core data models
from .commit import Commit
from .shared import (
    ChangeMetadata,
    Diff,
    FileModification,
    GitActor,
    GitMetadata,
)

# Utility types and functions
from .utils import GitSHA, GPGSignature

__all__ = [
    "ChangeMetadata",
    "Commit",
    "Diff",
    "FileModification",
    "GPGSignature",
    "GitActor",
    "GitMetadata",
    "GitSHA",
]
