# Contributing to skillkit

Thank you for your interest in contributing to skillkit! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Testing Guidelines](#testing-guidelines)
- [Code Style](#code-style)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)
- [Feature Requests](#feature-requests)

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please be respectful and constructive in all interactions.

**Expected Behavior:**
- Be respectful and considerate
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

**Unacceptable Behavior:**
- Harassment, discrimination, or offensive comments
- Trolling, insulting, or derogatory remarks
- Public or private harassment
- Publishing others' private information without permission

## Getting Started

### Prerequisites

- Python 3.10 or higher (3.10+ recommended for optimal performance)
- Git
- Basic understanding of Python development
- Familiarity with pytest for testing

### Finding Ways to Contribute

1. **Browse open issues**: Check the [issue tracker](https://github.com/maxvaega/skillkit/issues) for bugs and feature requests
2. **Documentation**: Help improve documentation, examples, or tutorials
3. **Bug fixes**: Fix bugs and submit pull requests
4. **New features**: Propose and implement new features (discuss first in an issue)
4. **Tests**: Add test coverage for existing functionality
5. **Examples**: Create new example skills or usage patterns

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/skillkit.git
cd skillkit
```

### 2. Install Development Dependencies

```bash
# Install package in editable mode with all extras
pip install -e ".[dev,langchain]"
```

This installs:
- Core dependencies (PyYAML)
- Development tools (pytest, pytest-cov, mypy, ruff)
- Optional integrations (langchain-core, pydantic)

### 3. Verify Setup

```bash
# Run tests to ensure everything works
pytest

# Run examples
python examples/basic_usage.py
python examples/langchain_agent.py
```

## Development Workflow

### 1. Make Your Changes on a feature branch

- Write clear, concise commit messages
- Follow the existing code style
- Add tests for new functionality
- Update documentation as needed

### 3. Run Quality Checks

Before committing, ensure all checks pass:

```bash
# Run tests with coverage
pytest --cov=src/skillkit --cov-report=html
pytest --cov=src/skillkit --cov-report=term-missing

# Type checking
mypy src/skillkit --strict

# Linting
ruff check src/skillkit

# Format code
ruff format src/skillkit
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "Brief description of changes"
```

**Commit Message Guidelines:**
- Use present tense ("Add feature" not "Added feature")
- Use imperative mood ("Fix bug" not "Fixes bug")
- First line should be 50 characters or less
- Reference issues and PRs when relevant

Examples:
```
Add async support for skill discovery

Fix YAML parsing error with special characters

Update README with installation instructions

Add tests for argument substitution edge cases
```

## Testing Guidelines

### Writing Tests

- All new functionality must include tests
- Tests should be in `tests/` directory, mirroring `src/` structure
- Use pytest fixtures from `tests/conftest.py`
- Aim for 70%+ code coverage

### Test Structure

```python
import pytest
from skillkit import SkillManager
from skillkit.core.exceptions import SkillNotFoundError

def test_feature_success_case(tmp_path):
    """Test successful execution of feature."""
    # Arrange
    manager = SkillManager(tmp_path)

    # Act
    result = manager.some_method()

    # Assert
    assert result is not None

def test_feature_error_case(tmp_path):
    """Test error handling."""
    manager = SkillManager(tmp_path)

    with pytest.raises(SkillNotFoundError):
        manager.invoke_skill("nonexistent")
```

### Test Markers

Use pytest markers for categorization:

```python
@pytest.mark.unit  # Unit tests
@pytest.mark.integration  # Integration tests
@pytest.mark.slow  # Slow-running tests
```

### Running Specific Tests

```bash
# Run specific test file
pytest tests/test_manager.py

# Run specific test
pytest tests/test_manager.py::test_discover_skills

# Run with markers
pytest -m unit
pytest -m "not slow"

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src/skillkit --cov-report=html
```

## Code Style

### Python Style Guidelines

- Follow PEP 8 conventions
- Use type hints for all function signatures
- Maximum line length: 88 characters (Black/Ruff default)
- Use descriptive variable and function names

### Type Hints

```python
from pathlib import Path
from typing import Optional, List

def load_skill(
    skill_path: Path,
    validate: bool = True
) -> Optional[dict[str, str]]:
    """Load a skill from disk.

    Args:
        skill_path: Path to skill directory
        validate: Whether to validate skill contents

    Returns:
        Skill metadata dictionary or None if loading fails
    """
    ...
```

### Documentation

- All public functions/classes must have docstrings
- Use Google-style docstrings
- Include examples for complex functionality

```python
def invoke_skill(self, skill_name: str, arguments: str = "") -> str:
    """Invoke a skill with arguments.

    Args:
        skill_name: Name of skill to invoke
        arguments: Arguments to pass to skill

    Returns:
        Processed skill content with arguments substituted

    Raises:
        SkillNotFoundError: If skill not found
        ContentLoadError: If skill content cannot be loaded

    Example:
        >>> manager = SkillManager()
        >>> manager.discover()
        >>> result = manager.invoke_skill("code-reviewer", "Review file.py")
    """
    ...
```

### Code Organization

- Keep functions focused and single-purpose
- Use dataclasses for data structures
- Prefer composition over inheritance
- Follow the existing module structure

## Submitting Changes

### 1. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 2. Create Pull Request

1. Go to the [skillkit repository](https://github.com/maxvaega/skillkit)
2. Click "New Pull Request"
3. Select your fork and branch
4. Fill out the PR template with:
   - Description of changes
   - Related issue number (if applicable)
   - Testing performed
   - Screenshots (if UI-related)

### 3. PR Review Process

- Maintainers will review your PR
- Address any requested changes
- Once approved, your PR will be merged
- Your contribution will be credited in release notes

### PR Checklist

Before submitting, ensure:

- [ ] All tests pass (`pytest`)
- [ ] Code coverage is maintained or improved
- [ ] Type checking passes (`mypy --strict`)
- [ ] Linting passes (`ruff check`)
- [ ] Code is formatted (`ruff format`)
- [ ] Documentation is updated
- [ ] Commit messages are clear and descriptive
- [ ] Changes are tested on Python 3.10+

## Reporting Issues

### Bug Reports

When reporting bugs, include:

1. **Description**: Clear description of the issue
2. **Steps to reproduce**: Minimal code example
3. **Expected behavior**: What should happen
4. **Actual behavior**: What actually happens
5. **Environment**:
   - Python version
   - skillkit version
   - Operating system
   - Relevant dependencies

**Example:**

```markdown
### Bug: Skill discovery fails with spaces in directory names

**Description:**
SkillManager.discover() raises FileNotFoundError when skill directories contain spaces.

**Steps to reproduce:**
```python
from pathlib import Path
from skillkit import SkillManager

# Create skill directory with space
skill_dir = Path("~/.claude/skills/my skill")
skill_dir.mkdir(parents=True)

manager = SkillManager()
manager.discover()  # Fails here
```

**Expected:** Should discover skills in directories with spaces
**Actual:** FileNotFoundError raised

**Environment:**
- Python 3.10.19
- skillkit 0.1.0
- macOS 14.0

## Feature Requests

When proposing features:

1. **Use case**: Describe the problem you're trying to solve
2. **Proposed solution**: How you envision the feature working
3. **Alternatives considered**: Other approaches you've thought about
4. **Additional context**: Examples, mockups, or references

**Example:**

### Feature: Async skill discovery

**Use case:**
In applications with hundreds of skills, synchronous discovery blocks the event loop.

**Proposed solution:**
Add `async def adiscover()` method to SkillManager:

```python
manager = SkillManager()
await manager.adiscover()
```

**Alternatives:**
- Background thread (doesn't work well with async frameworks)
- Lazy discovery (increases latency at invocation time)

**Additional context:**
Similar to langchain's async patterns in LangChain 0.1+
-----

## Development Tips

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Module-specific logging:

```python
logging.getLogger('skillkit.core.discovery').setLevel(logging.DEBUG)
```

### Performance Testing

Test with many skills:

```bash
# Create 100 test skills
python tests/generate_test_skills.py

# Measure discovery time
python -m timeit "from skillkit import SkillManager; m=SkillManager(); m.discover()"
```

### Memory Profiling

```python
from memory_profiler import profile

@profile
def test_memory():
    manager = SkillManager()
    manager.discover()
    # Access content for subset of skills
    for skill in manager.list_skills()[:10]:
        _ = manager.invoke_skill(skill.name)
```

## Questions?

- Open a [discussion](https://github.com/maxvaega/skillkit/discussions)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Acknowledgments

Thank you for contributing to skillkit! Your contributions help make AI agents more capable and easier to develop.
