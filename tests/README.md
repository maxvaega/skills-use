# skills-use Test Suite

Comprehensive pytest-based test suite for the skills-use library, validating all core functionality, integrations, edge cases, and performance characteristics.

## Quick Start

### Run all tests
```bash
pytest
```

### Run with coverage report
```bash
pytest --cov=src/skills_use --cov-report=html
# View report: open htmlcov/index.html
```

### Run specific test file
```bash
pytest tests/test_parser.py -v
pytest tests/test_models.py -v
pytest tests/test_manager.py -v
```

## Test Organization

### Core Functionality Tests (Phase 3)

**test_discovery.py** - Skill discovery and filesystem scanning
- Validates discovery from multiple sources
- Tests graceful error handling for invalid skills
- Verifies duplicate name handling with warnings

**test_parser.py** - YAML frontmatter parsing
- Tests valid skill parsing (basic, with arguments, Unicode)
- Validates error messages for invalid YAML
- Checks required field validation (name, description)

**test_models.py** - Data model validation
- Tests SkillMetadata and Skill dataclass instantiation
- Validates lazy content loading pattern
- Verifies content caching behavior (@cached_property)

**test_processors.py** - Content processing strategies
- Tests $ARGUMENTS substitution at various positions
- Validates escaping ($$ARGUMENTS → $ARGUMENTS literal)
- Tests size limits (1MB argument size enforcement)
- Validates BaseDirectoryProcessor injection
- Tests CompositeProcessor chaining

**test_manager.py** - Orchestration layer
- Tests end-to-end workflows (discover → list → invoke)
- Validates skill not found error handling
- Tests graceful degradation with mixed valid/invalid skills
- Verifies discovery clears previous results on re-run

### Integration Tests (Phase 4)

**test_langchain_integration.py** - LangChain StructuredTool integration *(completed)*
- Validates tool creation from skills
- Tests tool invocation and argument passing
- Verifies error propagation to framework

### Edge Case Tests (Phase 5)

**test_edge_cases.py** - Boundary conditions and error scenarios *(planned)*
- Large skills (500KB+ content)
- Special characters and injection patterns
- Permission denied errors (Unix-only)
- Symlinks and Windows line endings

### Performance Tests (Phase 6)

**test_performance.py** - Performance validation *(planned)*
- Discovery time: <500ms for 50 skills
- Invocation overhead: <25ms average
- Memory usage: <5MB for 50 skills with 10% loaded

### Installation Tests (Phase 7)

**test_installation.py** - Package distribution validation *(planned)*
- Import validation with/without extras
- Version metadata validation
- Package structure verification

## Test Fixtures

### Static Fixtures (`tests/fixtures/skills/`)

Pre-created SKILL.md files for consistent testing:

- **valid-basic/** - Minimal valid skill
- **valid-with-arguments/** - Skill with $ARGUMENTS placeholder
- **valid-unicode/** - Skill with Unicode content (你好 🎉)
- **invalid-missing-name/** - Missing required 'name' field
- **invalid-missing-description/** - Missing required 'description' field
- **invalid-yaml-syntax/** - Malformed YAML frontmatter

### Dynamic Fixtures (`conftest.py`)

Programmatic fixtures for flexible testing:

- **temp_skills_dir** - Temporary directory for test isolation
- **skill_factory** - Factory function for creating SKILL.md files
- **sample_skills** - Pre-created set of 5 diverse sample skills
- **fixtures_dir** - Path to static test fixtures

## Test Markers

Filter tests by category using pytest markers:

```bash
# Run only integration tests
pytest -m integration

# Run only performance tests
pytest -m performance

# Skip slow tests
pytest -m "not slow"

# Run LangChain-specific tests
pytest -m requires_langchain
```

Available markers:
- `integration` - Integration tests with external frameworks
- `performance` - Performance validation tests (may take 15+ seconds)
- `slow` - Tests that take longer than 1 second
- `requires_langchain` - Tests requiring langchain-core dependency

## Coverage Requirements

**Minimum coverage**: 70% line coverage across all modules
**Current coverage**: 75%+ (as of Phase 3 completion)

```bash
# Check coverage with failure on <70%
pytest --cov=src/skills_use --cov-fail-under=70

# Generate detailed HTML report
pytest --cov=src/skills_use --cov-report=html
open htmlcov/index.html
```

## Common Test Commands

### Run specific test categories
```bash
# Core functionality only
pytest tests/test_discovery.py tests/test_parser.py tests/test_models.py tests/test_processors.py tests/test_manager.py

# Integration tests only
pytest tests/test_langchain_integration.py

# Edge cases and performance
pytest tests/test_edge_cases.py tests/test_performance.py
```

### Verbose output with detailed assertions
```bash
pytest -vv
```

### Show print statements
```bash
pytest -s
```

### Run tests in parallel (faster)
```bash
pytest -n auto
```

### Stop on first failure
```bash
pytest -x
```

### Run last failed tests only
```bash
pytest --lf
```

### Show test durations
```bash
pytest --durations=10
```

## Debugging Tests

### Enable debug logging
```bash
pytest --log-cli-level=DEBUG
```

### Drop into debugger on failure
```bash
pytest --pdb
```

### Run specific test by name
```bash
pytest tests/test_parser.py::test_parse_valid_basic_skill -v
```

### Run tests matching pattern
```bash
pytest -k "test_parse" -v
pytest -k "invalid" -v
```

## Test Development Guidelines

### Writing New Tests

1. **Follow naming convention**: `test_<module>_<scenario>`
2. **Add docstrings**: Explain what the test validates
3. **Use fixtures**: Leverage conftest.py fixtures for setup
4. **Parametrize when possible**: Reduce duplication with @pytest.mark.parametrize
5. **Test one thing**: Each test should validate one specific behavior
6. **Add markers**: Tag tests with appropriate markers (integration, slow, etc.)

### Example Test Structure

```python
def test_parse_valid_skill_with_unicode(fixtures_dir):
    """Validate Unicode/emoji content is handled correctly.

    Tests that the parser can handle SKILL.md files containing Unicode
    characters and emoji in both frontmatter and content.
    """
    parser = SkillParser()
    skill_path = fixtures_dir / "valid-unicode" / "SKILL.md"

    metadata = parser.parse_skill_file(skill_path)

    assert metadata.name is not None
    assert metadata.description is not None
```

## CI/CD Integration

Tests are designed to run in automated environments:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pytest --cov=src/skills_use --cov-fail-under=70 --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## Requirements

- **Python**: 3.10+ (3.9 compatible with minor memory trade-offs)
- **pytest**: 7.0+
- **pytest-cov**: 4.0+ (for coverage measurement)
- **PyYAML**: 6.0+ (core dependency)
- **langchain-core**: 0.1.0+ (for integration tests)

## Test Statistics

- **Total test count**: 39 tests (Phase 3 complete)
- **Test execution time**: <1 second for core tests
- **Coverage**: 75%+ line coverage
- **Assertion count**: 150+ assertions validating behavior

## Troubleshooting

### Tests failing with import errors
```bash
# Ensure package installed in development mode
pip install -e ".[dev]"
```

### Fixtures not found
```bash
# Verify conftest.py is present
ls tests/conftest.py

# Check fixtures directory structure
ls tests/fixtures/skills/
```

### Permission errors on Unix
```bash
# Some tests require Unix permissions (skip on Windows)
pytest -m "not unix_only"
```

### Coverage report not generating
```bash
# Install pytest-cov
pip install pytest-cov

# Verify source path is correct
pytest --cov=src/skills_use --cov-report=term
```

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure tests pass: `pytest`
3. Verify coverage: `pytest --cov=src/skills_use`
4. Run type checking: `mypy src/skills_use --strict`
5. Format code: `ruff format tests/`
6. Lint code: `ruff check tests/`

## Resources

- **Main documentation**: [README.md](../README.md)
- **Test specifications**: [specs/001-pytest-test-scripts/](../specs/001-pytest-test-scripts/)
- **pytest documentation**: https://docs.pytest.org/
- **Coverage.py documentation**: https://coverage.readthedocs.io/
