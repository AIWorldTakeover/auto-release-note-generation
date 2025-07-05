# Hypothesis Strategies for Data Model Testing

This directory contains modular, model-aware Hypothesis strategies for testing the Pydantic data models.

## Structure

- **base.py** - Common helpers and base strategies
- **utils.py** - GitSHA and GPGSignature strategies  
- **actors.py** - GitActor strategies
- **metadata.py** - GitMetadata and ChangeMetadata strategies
- **files.py** - FileModification and Diff strategies
- **commits.py** - Commit strategies

## Usage Examples

### Basic Usage

```python
from hypothesis import given
from tests.data_models.strategies import valid_git_actor, valid_commit

@given(valid_git_actor())
def test_actor_properties(actor):
    assert actor.name.strip() == actor.name  # Already stripped
    assert actor.email.islower()  # Already lowercase

@given(valid_commit())
def test_commit_properties(commit):
    assert commit.summary.strip() == commit.summary
    assert len(commit.metadata.parents) >= 0
```

### Testing Validation

```python
from hypothesis import given
from pydantic import ValidationError
from tests.data_models.strategies import invalid_actor_data, invalid_git_sha

@given(invalid_actor_data())
def test_actor_validation(invalid_data):
    with pytest.raises(ValidationError):
        GitActor(**invalid_data)

@given(invalid_git_sha())
def test_sha_validation(invalid_sha):
    with pytest.raises(ValueError):
        validate_and_normalize_sha(invalid_sha)
```

### Composite Strategies

```python
from tests.data_models.strategies import merge_commit, root_commit

@given(merge_commit())
def test_merge_commit_properties(commit):
    assert commit.is_merge_commit()
    assert len(commit.metadata.parents) >= 2

@given(root_commit())
def test_root_commit_properties(commit):
    assert commit.is_root_commit()
    assert len(commit.metadata.parents) == 0
```

### Property-Based Testing

```python
from hypothesis import given
from tests.data_models.strategies import valid_change_metadata

@given(valid_change_metadata())
def test_change_metadata_invariants(metadata):
    # Business logic invariants
    if metadata.change_type == "octopus":
        assert len(metadata.source_branches) >= 2
    elif metadata.change_type == "initial":
        assert len(metadata.source_branches) == 0
    elif metadata.change_type in ["merge", "squash"]:
        assert len(metadata.source_branches) == 1
```

## Migration from Old Strategies

Replace imports:
```python
# Old
from .test_strategies import HypothesisStrategies

# New  
from .strategies import (
    valid_git_actor,
    valid_commit,
    # ... specific strategies you need
)
```

Update usage:
```python
# Old
@given(HypothesisStrategies.valid_names)
def test_name(name):
    ...

# New
@given(valid_git_actor_name())
def test_name(name):
    ...
```
