# Test API Contract: Pytest Test Suite

**Feature**: 001-pytest-test-scripts
**Date**: November 5, 2025
**Status**: Complete

## Overview

This document defines the public API for the pytest test suite, including shared fixtures, helper functions, pytest markers, and testing utilities available to all test files.

---

## Public Fixtures (conftest.py)

### temp_skills_dir

**Scope**: function (default)
**Type**: `Path`
**Description**: Creates a temporary directory for storing test skills. Automatically cleaned up after each test.

**Signature**:
```python
@pytest.fixture
def temp_skills_dir(tmp_path: Path) -> Path:
    """
    Create temporary skills directory for testing.

    Returns:
        Path to temporary skills directory (empty on creation)

    Example:
        def test_discovery(temp_skills_dir):
            # temp_skills_dir is now available as an empty directory
            assert temp_skills_dir.exists()
            assert list(temp_skills_dir.iterdir()) == []
    """
```

**Usage**:
```python
def test_empty_directory(temp_skills_dir):
    manager = SkillManager(temp_skills_dir)
    discovered = manager.discover()
    assert len(discovered) == 0
```

---

### skill_factory

**Scope**: function
**Type**: `Callable[[str, str, str, Optional[List[str]], **Any], Path]`
**Description**: Factory function for creating test SKILL.md files programmatically.

**Signature**:
```python
@pytest.fixture
def skill_factory(temp_skills_dir: Path) -> Callable:
    """
    Factory for creating test SKILL.md files in temp_skills_dir.

    Args:
        name: Skill name (used for directory name and frontmatter)
        description: Skill description (frontmatter field)
        content: Skill content body (after YAML frontmatter)
        allowed_tools: Optional list of allowed tools
        **extra_frontmatter: Additional YAML fields

    Returns:
        Path to created skill directory

    Raises:
        ValueError: If skill with same name already exists

    Example:
        def test_arguments(skill_factory):
            skill_dir = skill_factory(
                "test-skill",
                "A test skill",
                "Hello $ARGUMENTS!"
            )
            assert (skill_dir / "SKILL.md").exists()
    """
```

**Usage Examples**:
```python
# Basic usage
def test_basic_skill(temp_skills_dir, skill_factory):
    skill_dir = skill_factory(
        "my-skill",
        "My test skill",
        "This is the content"
    )

    manager = SkillManager(temp_skills_dir)
    skill = manager.get_skill("my-skill")
    assert skill.description == "My test skill"

# With arguments placeholder
def test_arguments_skill(temp_skills_dir, skill_factory):
    skill_factory(
        "greeter",
        "Greets someone",
        "Hello $ARGUMENTS!"
    )

    manager = SkillManager(temp_skills_dir)
    skill = manager.get_skill("greeter")
    result = skill.invoke(arguments="World")
    assert result == "Hello World!"

# With allowed-tools
def test_restricted_skill(temp_skills_dir, skill_factory):
    skill_factory(
        "restricted",
        "Tool-restricted skill",
        "Use grep to search",
        allowed_tools=["Grep", "Read"]
    )

    manager = SkillManager(temp_skills_dir)
    skill = manager.get_skill("restricted")
    assert skill.metadata.allowed_tools == ["Grep", "Read"]

# With extra frontmatter
def test_custom_fields(temp_skills_dir, skill_factory):
    skill_factory(
        "custom",
        "Skill with custom fields",
        "Content here",
        author="Test User",
        version="1.0.0"
    )

    # Custom fields are in SKILL.md but not parsed by library
    # (validates library ignores unknown fields gracefully)
```

---

### sample_skills

**Scope**: function
**Type**: `List[Path]`
**Description**: Creates 5 diverse sample skills for discovery and parsing tests.

**Signature**:
```python
@pytest.fixture
def sample_skills(skill_factory: Callable) -> List[Path]:
    """
    Create 5 sample skills with different characteristics.

    Returns:
        List of skill directory Paths

    Skills created:
        1. skill-1: Basic skill with simple content
        2. skill-2: Skill with $ARGUMENTS placeholder
        3. skill-3: Skill with Unicode content (你好 🎉)
        4. skill-4: Skill with long content (repeated 100x)
        5. skill-5: Skill with special HTML chars (<>&"')

    Example:
        def test_discovery(temp_skills_dir, sample_skills):
            manager = SkillManager(temp_skills_dir)
            discovered = manager.discover()
            assert len(discovered) == 5
    """
```

**Usage**:
```python
def test_discovery_count(temp_skills_dir, sample_skills):
    manager = SkillManager(temp_skills_dir)
    discovered = manager.discover()
    assert len(discovered) == 5

def test_all_skills_have_metadata(sample_skills):
    for skill_dir in sample_skills:
        skill_file = skill_dir / "SKILL.md"
        assert skill_file.exists()
```

---

### fixtures_dir

**Scope**: session
**Type**: `Path`
**Description**: Path to static test fixtures directory (`tests/fixtures/skills/`).

**Signature**:
```python
@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """
    Path to static test fixtures directory.

    Returns:
        Path to tests/fixtures/skills/

    Example:
        def test_static_fixture(fixtures_dir):
            valid_skill = fixtures_dir / "valid-basic" / "SKILL.md"
            assert valid_skill.exists()
    """
```

**Usage**:
```python
def test_valid_basic_fixture(fixtures_dir):
    skill_path = fixtures_dir / "valid-basic" / "SKILL.md"
    parser = SkillParser()
    metadata = parser.parse(skill_path)
    assert metadata.name == "valid-basic"

@pytest.mark.parametrize("fixture_name", [
    "valid-basic",
    "valid-with-arguments",
    "valid-unicode"
])
def test_valid_fixtures(fixtures_dir, fixture_name):
    skill_path = fixtures_dir / fixture_name / "SKILL.md"
    parser = SkillParser()
    metadata = parser.parse(skill_path)  # Should not raise
    assert metadata.name == fixture_name
```

---

### captured_logs

**Scope**: function
**Type**: `pytest.LogCaptureFixture`
**Description**: Built-in pytest fixture for capturing log messages.

**Usage**:
```python
import logging

def test_warning_logged(temp_skills_dir, skill_factory, caplog):
    # Create duplicate skills
    skill_factory("duplicate", "First", "Content 1")
    skill_factory("duplicate", "Second", "Content 2")

    with caplog.at_level(logging.WARNING):
        manager = SkillManager(temp_skills_dir)
        manager.discover()

    assert "duplicate skill name" in caplog.text.lower()
```

---

## Helper Functions (conftest.py)

### assert_skill_metadata_valid()

**Signature**:
```python
def assert_skill_metadata_valid(metadata: SkillMetadata) -> None:
    """
    Assert that SkillMetadata object has valid structure.

    Args:
        metadata: SkillMetadata instance to validate

    Raises:
        AssertionError: If any validation fails

    Checks:
        - name is non-empty string
        - description is non-empty string
        - skill_path exists and points to SKILL.md
        - allowed_tools is None or list of strings

    Example:
        def test_metadata(sample_skills):
            metadata = discover_metadata(sample_skills[0])
            assert_skill_metadata_valid(metadata)
    """
    assert metadata.name, "name must be non-empty"
    assert metadata.description, "description must be non-empty"
    assert metadata.skill_path.exists(), f"skill_path must exist: {metadata.skill_path}"
    assert metadata.skill_path.name == "SKILL.md", "skill_path must point to SKILL.md"
    if metadata.allowed_tools is not None:
        assert isinstance(metadata.allowed_tools, list), "allowed_tools must be list"
        assert all(isinstance(t, str) for t in metadata.allowed_tools), "allowed_tools items must be strings"
```

---

### create_large_skill()

**Signature**:
```python
def create_large_skill(temp_skills_dir: Path, size_kb: int = 500) -> Path:
    """
    Create a skill with large content for testing lazy loading.

    Args:
        temp_skills_dir: Directory to create skill in
        size_kb: Approximate size of content in kilobytes

    Returns:
        Path to created skill directory

    Example:
        def test_large_skill_lazy_loading(temp_skills_dir):
            skill_dir = create_large_skill(temp_skills_dir, size_kb=500)
            # Verify content is not loaded until accessed
            metadata = SkillParser().parse(skill_dir / "SKILL.md")
            assert not hasattr(metadata, '_content')  # Not loaded yet
    """
    skill_dir = temp_skills_dir / "large-skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"

    content = "Lorem ipsum dolor sit amet. " * (size_kb * 1024 // 30)  # Approx size_kb

    frontmatter = """---
name: large-skill
description: Large skill for testing lazy loading
---

"""
    skill_file.write_text(frontmatter + content, encoding="utf-8")
    return skill_dir
```

---

### create_permission_denied_skill()

**Signature**:
```python
def create_permission_denied_skill(temp_skills_dir: Path) -> Path:
    """
    Create a skill with no read permissions for testing error handling.

    Args:
        temp_skills_dir: Directory to create skill in

    Returns:
        Path to created skill directory

    Note:
        Only works on Unix systems. On Windows, this may not restrict access.

    Example:
        def test_permission_error(temp_skills_dir):
            skill_dir = create_permission_denied_skill(temp_skills_dir)
            parser = SkillParser()
            with pytest.raises(PermissionError):
                parser.parse(skill_dir / "SKILL.md")
    """
    skill_dir = temp_skills_dir / "no-permission"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"

    skill_file.write_text("""---
name: no-permission
description: Skill with no read permissions
---

Content
""", encoding="utf-8")

    skill_file.chmod(0o000)  # Remove all permissions
    return skill_dir
```

---

## Pytest Markers

Custom markers for organizing and filtering tests.

### @pytest.mark.integration

**Description**: Marks tests that test integration with external frameworks (LangChain).
**Usage**: Run only integration tests: `pytest -m integration`

```python
@pytest.mark.integration
def test_langchain_tool_creation():
    # Test LangChain integration
    pass
```

---

### @pytest.mark.performance

**Description**: Marks tests that measure performance characteristics.
**Usage**: Run only performance tests: `pytest -m performance`

```python
@pytest.mark.performance
def test_discovery_speed():
    # Test discovery performance
    pass
```

---

### @pytest.mark.slow

**Description**: Marks tests that take >5 seconds to run.
**Usage**: Skip slow tests: `pytest -m "not slow"`

```python
@pytest.mark.slow
def test_50_skill_discovery():
    # Generates 50 skills (takes ~10s)
    pass
```

---

### @pytest.mark.requires_langchain

**Description**: Marks tests that require langchain-core to be installed.
**Usage**: Skip if langchain not installed: `pytest -m "not requires_langchain"`

```python
@pytest.mark.requires_langchain
def test_create_langchain_tools():
    from skillkit.integrations.langchain import create_langchain_tools
    # Test function
    pass
```

---

### Marker Registration (pytest.ini)

```ini
[tool.pytest.ini_options]
markers = [
    "integration: Integration tests with external frameworks",
    "performance: Performance measurement tests",
    "slow: Tests that take >5 seconds",
    "requires_langchain: Tests requiring langchain-core",
]
```

---

## Common Test Patterns

### Pattern 1: Basic Discovery Test

```python
def test_discover_skills(temp_skills_dir, skill_factory):
    """Test basic skill discovery."""
    # Setup: Create test skills
    skill_factory("skill-1", "First skill", "Content 1")
    skill_factory("skill-2", "Second skill", "Content 2")

    # Execute: Discover skills
    manager = SkillManager(temp_skills_dir)
    discovered = manager.discover()

    # Assert: Verify results
    assert len(discovered) == 2
    assert "skill-1" in discovered
    assert "skill-2" in discovered
```

---

### Pattern 2: Parametrized Invalid Input Test

```python
@pytest.mark.parametrize("fixture_name,expected_error", [
    ("invalid-missing-name", "name is required"),
    ("invalid-missing-description", "description is required"),
    ("invalid-yaml-syntax", "YAML parsing failed"),
])
def test_invalid_skills(fixtures_dir, fixture_name, expected_error):
    """Test that invalid skills raise appropriate errors."""
    skill_path = fixtures_dir / fixture_name / "SKILL.md"
    parser = SkillParser()

    with pytest.raises(ValidationError, match=expected_error):
        parser.parse(skill_path)
```

---

### Pattern 3: Performance Measurement Test

```python
import time

@pytest.mark.performance
def test_discovery_performance(temp_skills_dir, skill_factory):
    """Test that discovery completes in <500ms for 50 skills."""
    # Setup: Generate 50 skills
    for i in range(50):
        skill_factory(f"skill-{i}", f"Description {i}", f"Content {i}")

    # Measure: Discovery time
    manager = SkillManager(temp_skills_dir)
    start = time.perf_counter()
    discovered = manager.discover()
    elapsed = time.perf_counter() - start

    # Assert: Performance target met
    assert len(discovered) == 50
    assert elapsed < 0.5, f"Discovery took {elapsed:.3f}s, expected <0.5s"
```

---

### Pattern 4: Exception Testing

```python
def test_content_load_error_when_file_deleted(temp_skills_dir, skill_factory):
    """Test ContentLoadError when skill file is deleted after discovery."""
    # Setup: Create and discover skill
    skill_dir = skill_factory("test-skill", "Test", "Content")
    manager = SkillManager(temp_skills_dir)
    skill = manager.get_skill("test-skill")

    # Manipulate: Delete file
    (skill_dir / "SKILL.md").unlink()

    # Assert: Exception raised on content access
    with pytest.raises(ContentLoadError, match="skill file not found"):
        _ = skill.content
```

---

### Pattern 5: Log Capture Test

```python
import logging

def test_duplicate_skill_warning(temp_skills_dir, skill_factory, caplog):
    """Test that duplicate skill names log a warning."""
    # Setup: Create duplicate skills in different directories
    (temp_skills_dir / "dir1").mkdir()
    (temp_skills_dir / "dir2").mkdir()

    skill_factory("duplicate", "First", "Content 1")
    skill_factory("duplicate", "Second", "Content 2")

    # Execute: Discover with logging
    with caplog.at_level(logging.WARNING):
        manager = SkillManager(temp_skills_dir)
        manager.discover()

    # Assert: Warning logged
    assert "duplicate" in caplog.text.lower()
    assert "WARNING" in [rec.levelname for rec in caplog.records]
```

---

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_discovery.py

# Run specific test function
pytest tests/test_discovery.py::test_discover_multiple_skills

# Run tests matching pattern
pytest -k "discovery"

# Run tests with markers
pytest -m integration
pytest -m "not slow"
pytest -m "performance and not slow"
```

---

### Coverage Commands

```bash
# Run with coverage
pytest --cov=src/skillkit

# Generate HTML coverage report
pytest --cov=src/skillkit --cov-report=html

# Fail if coverage below 70%
pytest --cov=src/skillkit --cov-fail-under=70

# Show missing lines
pytest --cov=src/skillkit --cov-report=term-missing
```

---

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (auto-detect CPU count)
pytest -n auto

# Run tests on 4 workers
pytest -n 4
```

---

### Debug Mode

```bash
# Stop on first failure
pytest -x

# Drop into debugger on failure
pytest --pdb

# Show local variables in tracebacks
pytest --showlocals

# Increase verbosity
pytest -vv
```

---

## Test Configuration (pyproject.toml)

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

addopts = [
    "-v",
    "--strict-markers",
    "--cov=src/skillkit",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-fail-under=70",
]

markers = [
    "integration: Integration tests with external frameworks",
    "performance: Performance measurement tests",
    "slow: Tests that take >5 seconds",
    "requires_langchain: Tests requiring langchain-core",
]

[tool.coverage.run]
branch = true
source = ["src/skillkit"]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__pycache__/*",
]

[tool.coverage.report]
precision = 2
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if TYPE_CHECKING:",
    "raise AssertionError",
    "raise NotImplementedError",
]
```

---

## Best Practices

### 1. Test Naming

```python
# GOOD: Descriptive test names
def test_discovery_finds_all_skills_in_directory()
def test_parser_raises_validation_error_for_missing_name()
def test_invoke_substitutes_arguments_correctly()

# BAD: Vague test names
def test_discovery()
def test_error()
def test_invoke()
```

---

### 2. Arrange-Act-Assert Pattern

```python
def test_skill_invocation():
    # Arrange: Set up test data
    skill_factory("test", "Test skill", "Hello $ARGUMENTS!")
    manager = SkillManager(temp_skills_dir)
    skill = manager.get_skill("test")

    # Act: Perform action
    result = skill.invoke(arguments="World")

    # Assert: Check outcome
    assert result == "Hello World!"
```

---

### 3. One Assertion per Test (when possible)

```python
# GOOD: Focused test
def test_discovery_count(sample_skills):
    manager = SkillManager(temp_skills_dir)
    discovered = manager.discover()
    assert len(discovered) == 5

def test_discovery_includes_all_skills(sample_skills):
    manager = SkillManager(temp_skills_dir)
    discovered = manager.discover()
    assert all(f"skill-{i}" in discovered for i in range(1, 6))

# ACCEPTABLE: Multiple related assertions
def test_skill_metadata_structure(sample_skills):
    metadata = discover_metadata(sample_skills[0])
    assert metadata.name == "skill-1"
    assert metadata.description == "First skill"
    assert metadata.skill_path.exists()
```

---

### 4. Parametrization for Multiple Scenarios

```python
# GOOD: Parametrized test
@pytest.mark.parametrize("content,arguments,expected", [
    ("Hello $ARGUMENTS!", "World", "Hello World!"),
    ("$ARGUMENTS is nice", "Python", "Python is nice"),
    ("No substitution", "test", "No substitution"),
])
def test_argument_substitution(skill_factory, content, arguments, expected):
    skill_factory("test", "Test", content)
    manager = SkillManager(temp_skills_dir)
    result = manager.get_skill("test").invoke(arguments=arguments)
    assert result == expected

# BAD: Repeated test logic
def test_substitution_1():
    # ... test "Hello $ARGUMENTS!"

def test_substitution_2():
    # ... test "$ARGUMENTS is nice"

def test_substitution_3():
    # ... test "No substitution"
```

---

## Next Steps

1. **quickstart.md**: Create "Running Tests" guide for developers
2. **tasks.md**: Generate implementation tasks for writing actual tests

---

**Test API Contract Complete**: All public fixtures, helpers, markers, and patterns documented. Ready for implementation.
