# Quickstart: Running Tests for skillkit

**Feature**: 001-pytest-test-scripts
**Date**: November 5, 2025
**Audience**: Developers working on skillkit library

## Overview

This guide provides a 5-minute introduction to running and writing tests for the skillkit library. The test suite uses pytest and achieves 70%+ code coverage across all modules.

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/maxvaega/skillkit.git
cd skillkit
```

### 2. Set Up Virtual Environment

**Using Python 3.10** (recommended):
```bash
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

**Or using default Python 3** (aliased to 3.10):
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Development Dependencies

```bash
pip install -e ".[dev]"
```

This installs:
- Core library (skillkit)
- Test dependencies (pytest, pytest-cov)
- LangChain integration (for integration tests)

**Verify installation**:
```bash
pytest --version  # Should show pytest 7.0+
python -c "import skillkit; print(skillkit.__version__)"  # Should show 0.1.0
```

---

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest

# Expected output:
# ============================= test session starts =============================
# collected 50+ items
#
# tests/test_discovery.py ........                                        [ 16%]
# tests/test_parser.py ..........                                         [ 36%]
# tests/test_models.py .......                                            [ 50%]
# tests/test_processors.py ........                                       [ 66%]
# tests/test_manager.py ......                                            [ 78%]
# tests/test_langchain_integration.py ....                                [ 86%]
# tests/test_edge_cases.py ........                                       [ 98%]
# tests/test_performance.py ....                                          [100%]
#
# ========================== 50 passed in 15.23s ================================
```

### Run with Verbose Output

```bash
pytest -v

# Shows individual test names:
# tests/test_discovery.py::test_discover_empty_directory PASSED
# tests/test_discovery.py::test_discover_multiple_skills PASSED
# tests/test_parser.py::test_parse_valid_skill PASSED
# ...
```

### Run Specific Test File

```bash
pytest tests/test_discovery.py
pytest tests/test_langchain_integration.py -v
```

### Run Specific Test Function

```bash
pytest tests/test_discovery.py::test_discover_multiple_skills -v
pytest tests/test_parser.py::test_parse_invalid_yaml -v
```

### Run Tests Matching Pattern

```bash
# Run all discovery-related tests
pytest -k "discovery"

# Run all tests with "invalid" in name
pytest -k "invalid"

# Run all argument-related tests
pytest -k "argument"
```

---

## Running with Coverage

### Basic Coverage Report

```bash
pytest --cov=src/skillkit

# Output includes coverage summary:
# ----------- coverage: platform darwin, python 3.10.19 -----------
# Name                                    Stmts   Miss  Cover
# -----------------------------------------------------------
# src/skillkit/__init__.py                  8      0   100%
# src/skillkit/core/discovery.py          145     25    83%
# src/skillkit/core/parser.py             167     18    89%
# src/skillkit/core/models.py              89      8    91%
# src/skillkit/core/manager.py            132     30    77%
# src/skillkit/core/processors.py         103     19    82%
# src/skillkit/core/exceptions.py          22      5    77%
# src/skillkit/integrations/langchain.py   68     18    74%
# -----------------------------------------------------------
# TOTAL                                     734    123    83%
```

### Detailed HTML Coverage Report

```bash
pytest --cov=src/skillkit --cov-report=html

# Opens htmlcov/index.html in browser
open htmlcov/index.html  # macOS
# xdg-open htmlcov/index.html  # Linux
# start htmlcov/index.html  # Windows
```

The HTML report shows:
- Line-by-line coverage highlighting
- Which branches were taken/not taken
- Missing lines highlighted in red

### Show Missing Lines

```bash
pytest --cov=src/skillkit --cov-report=term-missing

# Output shows missing line numbers:
# src/skillkit/core/discovery.py    145     25    83%   67-72, 145, 167, 203
# src/skillkit/core/parser.py       167     18    89%   98, 134-137, 201
```

### Enforce Coverage Threshold

```bash
# Fail build if coverage drops below 70%
pytest --cov=src/skillkit --cov-fail-under=70

# Exit code 0 if >=70%, exit code 1 if <70%
```

---

## Running Specific Test Categories

### Integration Tests Only

```bash
pytest -m integration -v

# Runs only LangChain integration tests
```

### Performance Tests Only

```bash
pytest -m performance -v

# Runs tests measuring discovery time, invocation overhead, memory usage
```

### Skip Slow Tests

```bash
pytest -m "not slow"

# Skips tests that take >5 seconds (useful for fast feedback)
```

### Skip Tests Requiring LangChain

```bash
pytest -m "not requires_langchain"

# Useful if langchain-core is not installed
```

---

## Debugging Failed Tests

### Stop on First Failure

```bash
pytest -x

# Exits immediately when first test fails
```

### Drop into Debugger on Failure

```bash
pytest --pdb

# Automatically opens Python debugger (pdb) when test fails
```

### Show Local Variables in Traceback

```bash
pytest --showlocals

# Displays values of local variables in failure traceback
```

### Increase Verbosity

```bash
pytest -vv

# More detailed output, including full diffs for assertion failures
```

### Run Failed Tests First

```bash
# First run (some tests fail)
pytest

# Re-run only failed tests
pytest --lf  # --last-failed

# Re-run failed tests first, then others
pytest --ff  # --failed-first
```

---

## Parallel Test Execution (Optional)

For faster test execution, install `pytest-xdist`:

```bash
pip install pytest-xdist
```

Then run tests in parallel:

```bash
# Auto-detect CPU count and run on all cores
pytest -n auto

# Run on 4 workers
pytest -n 4

# Expected speedup: ~3-4x on 4-core machine
```

**Note**: Performance tests may be less accurate when run in parallel.

---

## Writing Your First Test

### 1. Create Test File

Create `tests/test_example.py`:

```python
"""Example test demonstrating skillkit testing patterns."""

import pytest
from skillkit import SkillManager


def test_basic_discovery(temp_skills_dir, skill_factory):
    """Test basic skill discovery with two skills."""
    # Arrange: Create test skills
    skill_factory("skill-1", "First skill", "Content 1")
    skill_factory("skill-2", "Second skill", "Content 2")

    # Act: Discover skills
    manager = SkillManager(temp_skills_dir)
    discovered = manager.discover()

    # Assert: Verify results
    assert len(discovered) == 2
    assert "skill-1" in discovered
    assert "skill-2" in discovered
    assert discovered["skill-1"].description == "First skill"


def test_argument_substitution(temp_skills_dir, skill_factory):
    """Test that $ARGUMENTS placeholder is substituted correctly."""
    # Arrange: Create skill with placeholder
    skill_factory("greeter", "Greets someone", "Hello $ARGUMENTS!")

    # Act: Invoke skill with arguments
    manager = SkillManager(temp_skills_dir)
    skill = manager.get_skill("greeter")
    result = skill.invoke(arguments="World")

    # Assert: Check substitution
    assert result == "Hello World!"


@pytest.mark.parametrize("content,arguments,expected", [
    ("Hello $ARGUMENTS!", "World", "Hello World!"),
    ("$ARGUMENTS is great", "Python", "Python is great"),
    ("No placeholder", "test", "No placeholder"),
])
def test_multiple_substitution_scenarios(temp_skills_dir, skill_factory,
                                        content, arguments, expected):
    """Test argument substitution with multiple scenarios."""
    skill_factory("test", "Test skill", content)
    manager = SkillManager(temp_skills_dir)
    result = manager.get_skill("test").invoke(arguments=arguments)
    assert result == expected
```

### 2. Run Your Test

```bash
pytest tests/test_example.py -v
```

Expected output:
```
tests/test_example.py::test_basic_discovery PASSED                     [ 25%]
tests/test_example.py::test_argument_substitution PASSED               [ 50%]
tests/test_example.py::test_multiple_substitution_scenarios[Hello $ARGUMENTS!-World-Hello World!] PASSED [ 62%]
tests/test_example.py::test_multiple_substitution_scenarios[$ARGUMENTS is great-Python-Python is great] PASSED [ 75%]
tests/test_example.py::test_multiple_substitution_scenarios[No placeholder-test-No placeholder] PASSED [100%]

========================== 5 passed in 0.23s ==================================
```

---

## Common Test Fixtures

### temp_skills_dir

Provides a temporary directory for creating test skills. Automatically cleaned up after each test.

```python
def test_with_temp_dir(temp_skills_dir):
    assert temp_skills_dir.exists()
    assert list(temp_skills_dir.iterdir()) == []  # Empty on creation
```

### skill_factory

Factory function for creating SKILL.md files programmatically.

```python
def test_with_factory(temp_skills_dir, skill_factory):
    skill_dir = skill_factory(
        "my-skill",
        "My test skill",
        "This is the content",
        allowed_tools=["Grep", "Read"]
    )
    assert (skill_dir / "SKILL.md").exists()
```

### sample_skills

Creates 5 diverse sample skills for discovery tests.

```python
def test_with_samples(temp_skills_dir, sample_skills):
    manager = SkillManager(temp_skills_dir)
    discovered = manager.discover()
    assert len(discovered) == 5
```

### fixtures_dir

Path to static test fixtures in `tests/fixtures/skills/`.

```python
def test_with_static_fixture(fixtures_dir):
    skill_path = fixtures_dir / "valid-basic" / "SKILL.md"
    assert skill_path.exists()
```

---

## Test Organization

### Test File Structure

```text
tests/
├── conftest.py                  # Shared fixtures
├── test_discovery.py            # Discovery tests
├── test_parser.py               # Parser tests
├── test_models.py               # Dataclass tests
├── test_processors.py           # Content processing tests
├── test_manager.py              # SkillManager tests
├── test_langchain_integration.py # LangChain integration
├── test_edge_cases.py           # Edge case handling
├── test_performance.py          # Performance tests
└── fixtures/                    # Static test data
    └── skills/
        ├── valid-basic/
        ├── invalid-missing-name/
        └── ...
```

### Test Naming Conventions

- Test files: `test_*.py`
- Test functions: `test_*`
- Descriptive names: `test_discover_multiple_skills` (not `test_discovery`)

### Test Structure (Arrange-Act-Assert)

```python
def test_example():
    # Arrange: Set up test data and preconditions
    skill_factory("test", "Test", "Content")
    manager = SkillManager(temp_skills_dir)

    # Act: Perform the action being tested
    result = manager.get_skill("test")

    # Assert: Check expected outcomes
    assert result.name == "test"
```

---

## Continuous Integration (Future)

When CI/CD is set up, tests will run automatically on:
- Every push to feature branches
- Every pull request
- Before merging to main branch

**Expected CI workflow**:
```yaml
# .github/workflows/test.yml (future)
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11", "3.12"]

    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install dependencies
        run: pip install -e ".[dev]"
      - name: Run tests with coverage
        run: pytest --cov=src/skillkit --cov-fail-under=70
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Troubleshooting

### Issue: Tests fail with "ModuleNotFoundError: No module named 'skillkit'"

**Solution**: Install package in editable mode:
```bash
pip install -e ".[dev]"
```

### Issue: Coverage report shows 0% coverage

**Solution**: Ensure you're using `--cov=src/skillkit` (not just `--cov`):
```bash
pytest --cov=src/skillkit
```

### Issue: LangChain integration tests fail with ImportError

**Solution**: Install langchain extras:
```bash
pip install -e ".[langchain,dev]"
```

### Issue: Performance tests fail with "Discovery took 0.523s, expected <0.5s"

**Solution**: Performance tests are sensitive to system load. Retry or increase threshold in test file.

### Issue: Permission error tests fail on Windows

**Solution**: `create_permission_denied_skill()` only works on Unix. Skip these tests on Windows:
```python
@pytest.mark.skipif(sys.platform == "win32", reason="Unix-only test")
def test_permission_error():
    ...
```

---

## Next Steps

### For Developers

1. **Read**: [test-api.md](./contracts/test-api.md) for complete fixture and helper documentation
2. **Explore**: Browse existing test files in `tests/` for examples
3. **Write**: Add tests for new features following existing patterns
4. **Run**: Use `pytest --cov` regularly to maintain >70% coverage

### For Contributors

1. **Before submitting PR**: Ensure all tests pass (`pytest`)
2. **Add tests**: New features require corresponding tests
3. **Maintain coverage**: Don't let coverage drop below 70%
4. **Document**: Add docstrings to new test functions

### For Library Users

Tests serve as **executable documentation** showing how to use the library:
- `test_discovery.py`: Shows how to discover skills
- `test_manager.py`: Shows how to use SkillManager
- `test_langchain_integration.py`: Shows LangChain integration patterns

---

## Quick Reference

### Most Common Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/skillkit --cov-report=html

# Run specific test file
pytest tests/test_discovery.py -v

# Run specific test
pytest tests/test_discovery.py::test_discover_multiple_skills -v

# Debug failed test
pytest --pdb -x

# Skip slow tests
pytest -m "not slow"

# Run in parallel
pytest -n auto
```

### Most Common Fixtures

```python
def test_example(temp_skills_dir, skill_factory, sample_skills, fixtures_dir):
    # temp_skills_dir: Temporary directory for test skills
    # skill_factory: Function to create SKILL.md files
    # sample_skills: 5 pre-created sample skills
    # fixtures_dir: Path to static fixtures
    pass
```

### Most Common Assertions

```python
# Basic assertions
assert len(discovered) == 5
assert "skill-1" in discovered
assert skill.name == "expected-name"

# Exception assertions
with pytest.raises(ValidationError, match="name is required"):
    parser.parse(invalid_skill_path)

# Performance assertions
assert elapsed < 0.5, f"Took {elapsed:.3f}s, expected <0.5s"

# Log assertions
with caplog.at_level(logging.WARNING):
    manager.discover()
assert "duplicate" in caplog.text.lower()
```

---

## Summary

You now know how to:
- ✅ Install test dependencies (`pip install -e ".[dev]"`)
- ✅ Run all tests (`pytest`)
- ✅ Run with coverage (`pytest --cov=src/skillkit`)
- ✅ Run specific tests (`pytest tests/test_discovery.py::test_name`)
- ✅ Debug failures (`pytest --pdb -x`)
- ✅ Write basic tests using fixtures (`temp_skills_dir`, `skill_factory`)
- ✅ Use parametrized tests (`@pytest.mark.parametrize`)

For detailed documentation, see:
- **[test-api.md](./contracts/test-api.md)**: Complete fixture and helper API
- **[data-model.md](./data-model.md)**: Test data entities and relationships
- **[research.md](./research.md)**: Architectural decisions and rationale

**Happy testing!** 🧪
