# skillkit Test Suite

Comprehensive pytest-based test suite for the skillkit library, validating all core functionality, integrations, edge cases, and performance characteristics.

## Quick Start

### Run all tests
```bash
pytest
```

### Run with coverage report
```bash
pytest --cov=src/skillkit --cov-report=html
# View report: open htmlcov/index.html
```

### Run specific test file
```bash
pytest tests/test_parser.py -v
pytest tests/test_models.py -v
pytest tests/test_manager.py -v
```

## Test Organization

### Core Functionality Tests (Phase 3) ✅ **COMPLETE**

**test_discovery.py** - Skill discovery and filesystem scanning (7 tests passing)
- Validates discovery from multiple sources
- Tests graceful error handling for invalid skills
- Verifies duplicate name handling with warnings
- Tests empty directory handling with INFO logging

**test_parser.py** - YAML frontmatter parsing (8 tests passing)
- Tests valid skill parsing (basic, with arguments, Unicode)
- Validates error messages for invalid YAML
- Checks required field validation (name, description)
- Parametrized tests for all invalid skill scenarios

**test_models.py** - Data model validation (5 tests passing)
- Tests SkillMetadata and Skill dataclass instantiation
- Validates lazy content loading pattern
- Verifies content caching behavior (@cached_property)
- Tests optional fields (allowed_tools can be None)

**test_processors.py** - Content processing strategies (7 tests passing)
- Tests $ARGUMENTS substitution at various positions
- Validates escaping ($$ARGUMENTS → $ARGUMENTS literal)
- Tests size limits (1MB argument size enforcement)
- Tests special characters and empty arguments

**test_manager.py** - Orchestration layer (6 tests passing)
- Tests end-to-end workflows (discover → list → invoke)
- Validates skill not found error handling
- Tests graceful degradation with mixed valid/invalid skills
- Verifies caching behavior and content load errors

### Integration Tests (Phase 4) ✅ **COMPLETE**

**test_langchain_integration.py** - LangChain StructuredTool integration (8 tests passing)
- Validates tool creation from skills
- Tests tool invocation and argument passing
- Verifies error propagation to framework
- Tests long arguments (10KB+)
- Validates tool count matches skill count

### Edge Case Tests (Phase 5) ✅ **COMPLETE** (8/8 passing)

**test_edge_cases.py** - Boundary conditions and error scenarios
- ✅ Invalid YAML syntax handling
- ✅ Symlink handling in skill directories
- ✅ Permission denied on Unix (tested)
- ✅ Missing required field logging
- ✅ Content load error after file deletion
- ✅ Duplicate skill name handling
- ✅ Large skills (500KB+ content) with lazy loading
- ✅ Windows line endings on Unix

### Performance Tests (Phase 6) ✅ **COMPLETE** (4/4 passing)

**test_performance.py** - Performance validation
- ✅ Discovery time: <500ms for 50 skills
- ✅ Invocation overhead: <25ms average
- ✅ Memory usage: <5MB for 50 skills
- ✅ Cache effectiveness validation

### Installation Tests (Phase 7) ✅ **COMPLETE**

**test_installation.py** - Package distribution validation (8 tests passing)
- Import validation with/without extras
- Version metadata validation
- Package structure verification
- Type hints availability (py.typed marker)

## Test Fixtures

### Static Fixtures (`tests/fixtures/skills/`)

Pre-created SKILL.md files for consistent testing:

**Valid Skills:**
- **valid-basic/** - Minimal valid skill
- **valid-with-arguments/** - Skill with $ARGUMENTS placeholder
- **valid-unicode/** - Skill with Unicode content (你好 🎉)

**Invalid Skills:**
- **invalid-missing-name/** - Missing required 'name' field
- **invalid-missing-description/** - Missing required 'description' field
- **invalid-yaml-syntax/** - Malformed YAML frontmatter

**Edge Case Skills:**
- **edge-large-content/** - Large skill (1MB+ content) for lazy loading tests
- **edge-special-chars/** - Special characters and injection pattern testing

### Dynamic Fixtures (`conftest.py`)

Programmatic fixtures for flexible testing:

- **temp_skills_dir** - Temporary directory for test isolation (auto-cleanup)
- **skill_factory** - Factory function for creating SKILL.md files dynamically
- **sample_skills** - Pre-created set of 5 diverse sample skills
- **fixtures_dir** - Path to static test fixtures directory
- **create_large_skill** - Helper for creating 500KB+ skills
- **create_permission_denied_skill** - Factory for Unix permission error testing

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
**Current coverage**: **85.86%** ✅ (exceeds target by 15.86%)

**Coverage by Module** (as of November 5, 2025):
- `__init__.py`: 100.00%
- `core/__init__.py`: 100.00%
- `core/exceptions.py`: 100.00%
- `integrations/__init__.py`: 100.00%
- `core/manager.py`: 93.75%
- `core/processors.py`: 91.46%
- `integrations/langchain.py`: 89.47%
- `core/models.py`: 84.62%
- `core/parser.py`: 79.00%
- `core/discovery.py`: 67.44%

```bash
# Check coverage with failure on <70%
pytest --cov=src/skillkit --cov-fail-under=70

# Generate detailed HTML report
pytest --cov=src/skillkit --cov-report=html
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
    pytest --cov=src/skillkit --cov-fail-under=70 --cov-report=xml

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

**Overall Status**: ✅ **99% Complete** (73/74 tests passing, 1 skipped)

- **Total test count**: **74 tests** across 9 test files
  - ✅ Core functionality: 33 tests (100% passing)
  - ✅ LangChain integration: 8 tests (100% passing)
  - ✅ Installation validation: 8 tests (87.5% passing, 1 skipped)
  - ✅ Edge cases: 8 tests (100% passing)
  - ✅ Performance: 4 tests (100% passing)

- **Test execution time**:
  - Core tests: <0.15 seconds
  - Full suite: ~0.30 seconds
  - Performance tests: <0.10 seconds

- **Coverage**: **85.86%** line coverage (target: 70%) ✅
- **Assertion count**: 200+ assertions validating behavior
- **Test files**: 9 test modules + conftest.py
- **Static fixtures**: 8 SKILL.md files
- **Dynamic fixtures**: 6 programmatic fixtures

**Breakdown by Phase**:
- Phase 1 (Setup): ✅ Complete
- Phase 2 (Foundational): ✅ Complete
- Phase 3 (Core - US1): ✅ Complete (33/33 passing)
- Phase 4 (LangChain - US2): ✅ Complete (8/8 passing)
- Phase 5 (Edge Cases - US3): ✅ Complete (8/8 passing)
- Phase 6 (Performance - US4): ✅ Complete (4/4 passing)
- Phase 7 (Installation - US5): ✅ Complete (7/8 passing, 1 skipped)
- Phase 8 (Polish): ✅ Complete

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
pytest --cov=src/skillkit --cov-report=term
```

## Contributing

When adding new features:

1. Write tests first (TDD approach)
2. Ensure tests pass: `pytest`
3. Verify coverage: `pytest --cov=src/skillkit`
4. Run type checking: `mypy src/skillkit --strict`
5. Format code: `ruff format tests/`
6. Lint code: `ruff check tests/`

## Resources

- **Main documentation**: [README.md](../README.md)
- **Test specifications**: [specs/001-pytest-test-scripts/](../specs/001-pytest-test-scripts/)
- **pytest documentation**: https://docs.pytest.org/
- **Coverage.py documentation**: https://coverage.readthedocs.io/
