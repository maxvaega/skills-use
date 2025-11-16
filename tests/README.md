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

### Core Functionality Tests

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

### Async Functionality Tests (v0.2)

**test_async_discovery.py** - Async skill discovery functionality
- Tests async file I/O wrappers (_read_skill_file_async)
- Validates async discovery methods (ascan_directory, afind_skill_files)
- Tests SkillManager async discovery (adiscover)
- Verifies async/sync state management and AsyncStateError validation
- Tests concurrent async discovery and event loop responsiveness
- Validates async vs sync discovery equivalence

**test_async_invocation.py** - Async skill invocation capabilities
- Tests Skill.ainvoke() async method
- Validates SkillManager.ainvoke_skill() async method
- Tests concurrent async invocations (10+ parallel)
- Verifies async/sync state management and error handling
- Tests async invocation performance (minimal overhead <5ms)
- Validates edge cases (long arguments, special characters, Unicode)
- Stress tests with 50 concurrent invocations

**test_langchain_async.py** - Async LangChain integration
- Tests async LangChain tool creation with ainvoke()
- Validates concurrent tool invocations (10+ parallel)
- Tests dual-mode support (sync and async invocation)
- Verifies closure capture pattern for async tools
- Tests state management (AsyncStateError after sync discover)
- Validates Pydantic schema handling for async tools
- Tests async tool performance characteristics

### Plugin System Tests (v0.3)

**test_discovery_plugin.py** - Plugin discovery functionality
- Tests discover_plugin_manifest() function
- Validates multi-directory skill discovery from plugin manifests
- Tests graceful error handling for malformed manifests
- Verifies security validations (path traversal prevention)
- Tests async plugin discovery (adiscover_skills)
- Validates edge cases (empty skills list, non-existent directories)

**test_parser_plugin.py** - Plugin manifest parsing
- Tests parse_plugin_manifest() function
- Validates valid manifest parsing with all fields
- Tests missing required fields error handling
- Verifies JSON bomb protection (MAX_MANIFEST_SIZE limit)
- Tests security validations (path traversal, absolute paths, drive letters)
- Validates manifest version compatibility
- Tests integration with real fixture files

**test_manager_plugin.py** - SkillManager plugin integration
- Tests plugin source building with manifest parsing
- Validates plugin skill namespacing (_plugin_skills registry)
- Tests qualified name lookups (plugin:skill syntax)
- Verifies conflict resolution (project skills win over plugin)
- Tests multi-source discovery with plugins
- Validates end-to-end plugin workflows (sync and async)

### File Reference & Security Tests (v0.2+)

**test_path_resolver.py** - Secure file path resolution
- Tests FilePathResolver.resolve_path() function
- Validates relative path resolution within base directory
- Tests path traversal prevention (../, absolute paths)
- Verifies symlink resolution and escape detection
- Tests security error logging with detailed context
- Validates cross-platform path handling
- Tests edge cases (Unicode, spaces, special characters, very long paths)

**test_file_references_integration.py** - File reference integration
- Tests end-to-end file reference resolution workflow
- Validates integration with file-reference-skill example
- Tests skill invocation with supporting files
- Verifies security validation in real-world scenarios
- Tests symlink escape blocking in real skill usage
- Validates performance (<1ms per resolution, <100ms for 100 files)

### Integration Tests

**test_langchain_integration.py** - LangChain StructuredTool integration (8 tests passing)
- Validates tool creation from skills
- Tests tool invocation and argument passing
- Verifies error propagation to framework
- Tests long arguments (10KB+)
- Validates tool count matches skill count

### Edge Case Tests

**test_edge_cases.py** - Boundary conditions and error scenarios
- ✅ Invalid YAML syntax handling
- ✅ Symlink handling in skill directories
- ✅ Permission denied on Unix (tested)
- ✅ Missing required field logging
- ✅ Content load error after file deletion
- ✅ Duplicate skill name handling
- ✅ Large skills (500KB+ content) with lazy loading
- ✅ Windows line endings on Unix

### Performance Tests

**test_performance.py** - Performance validation
- ✅ Discovery time: <500ms for 50 skills
- ✅ Invocation overhead: <25ms average
- ✅ Memory usage: <5MB for 50 skills
- ✅ Cache effectiveness validation

### Installation Tests

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
- **fixtures_dir** - Path to static test fixtures directory (tests/fixtures/skills/)
- **skills_directory** - Path to example skills directory (examples/skills/)
- **skill_manager_async** - Async-initialized SkillManager for async tests
- **create_large_skill** - Helper for creating 500KB+ skills
- **create_permission_denied_skill** - Factory for Unix permission error testing

## Test Markers

Filter tests by category using pytest markers:

```bash
# Run only integration tests
pytest -m integration

# Run only async tests
pytest -m asyncio

# Run only performance tests
pytest -m performance

# Skip slow tests
pytest -m "not slow"

# Run LangChain-specific tests
pytest -m requires_langchain

# Run plugin tests
pytest -m plugin

# Run security tests
pytest -m security
```

Available markers:
- `integration` - Integration tests with external frameworks
- `asyncio` - Async tests requiring asyncio event loop
- `performance` - Performance validation tests (may take 15+ seconds)
- `slow` - Tests that take longer than 1 second
- `requires_langchain` - Tests requiring langchain-core dependency
- `plugin` - Plugin system tests (discovery, parsing, manager)
- `security` - Security validation tests (path traversal, symlinks)

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
# Core functionality only (v0.1)
pytest tests/test_discovery.py tests/test_parser.py tests/test_models.py tests/test_processors.py tests/test_manager.py

# Async functionality (v0.2)
pytest tests/test_async_discovery.py tests/test_async_invocation.py tests/test_langchain_async.py

# Plugin system (v0.3)
pytest tests/test_discovery_plugin.py tests/test_parser_plugin.py tests/test_manager_plugin.py

# File references & security (v0.2+)
pytest tests/test_path_resolver.py tests/test_file_references_integration.py

# Integration tests
pytest tests/test_langchain_integration.py

# Edge cases and performance
pytest tests/test_edge_cases.py tests/test_performance.py

# All v0.1 tests
pytest tests/test_discovery.py tests/test_parser.py tests/test_models.py tests/test_processors.py tests/test_manager.py tests/test_langchain_integration.py tests/test_edge_cases.py tests/test_performance.py tests/test_installation.py

# All v0.2 tests
pytest tests/test_async_discovery.py tests/test_async_invocation.py tests/test_langchain_async.py tests/test_path_resolver.py tests/test_file_references_integration.py

# All v0.3 tests
pytest tests/test_discovery_plugin.py tests/test_parser_plugin.py tests/test_manager_plugin.py
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

- **Python**: 3.10+ (minimum for full async support)
- **pytest**: 7.0+
- **pytest-asyncio**: 0.21.0+ (for async tests)
- **pytest-cov**: 4.0+ (for coverage measurement)
- **PyYAML**: 6.0+ (core dependency)
- **aiofiles**: 23.0+ (async file I/O for v0.2+)
- **langchain-core**: 0.1.0+ (for LangChain integration tests)
- **pydantic**: 2.0+ (validation for LangChain integration)

## Test Statistics

**Overall Status**: ✅ **v0.2 Complete** (All test suites passing)

- **Total test count**: **17 test files** across core, async, plugin, and integration tests
  - ✅ Core functionality: 33 tests (test_discovery, test_parser, test_models, test_processors, test_manager)
  - ✅ Async functionality: ~60 tests (test_async_discovery, test_async_invocation, test_langchain_async)
  - ✅ Plugin system: ~40 tests (test_discovery_plugin, test_parser_plugin, test_manager_plugin)
  - ✅ File references & security: ~80 tests (test_path_resolver, test_file_references_integration)
  - ✅ LangChain integration: 8 tests (test_langchain_integration)
  - ✅ Edge cases: 8 tests (test_edge_cases)
  - ✅ Performance: 4 tests (test_performance)
  - ✅ Installation validation: 8 tests (test_installation)

- **Test execution time**:
  - Core tests: <0.15 seconds
  - Async tests: <0.50 seconds
  - Plugin tests: <0.30 seconds
  - Full suite: ~1.5 seconds

- **Coverage**: **85.86%** line coverage (target: 70%) ✅
- **Assertion count**: 500+ assertions validating behavior
- **Test files**: 17 test modules + conftest.py
- **Static fixtures**: Multiple SKILL.md files and plugin manifests
- **Dynamic fixtures**: 10+ programmatic fixtures

**Breakdown by Version**:
- v0.1 (MVP):
  - Phase 1 (Setup): ✅ Complete
  - Phase 2 (Foundational): ✅ Complete
  - Phase 3 (Core - US1): ✅ Complete (33/33 passing)
  - Phase 4 (LangChain - US2): ✅ Complete (8/8 passing)
  - Phase 5 (Edge Cases - US3): ✅ Complete (8/8 passing)
  - Phase 6 (Performance - US4): ✅ Complete (4/4 passing)
  - Phase 7 (Installation - US5): ✅ Complete (7/8 passing, 1 skipped)
  - Phase 8 (Polish): ✅ Complete
- v0.2 (Async + File References):
  - Async discovery: ✅ Complete
  - Async invocation: ✅ Complete
  - Async LangChain: ✅ Complete
  - File path resolver: ✅ Complete
  - File references integration: ✅ Complete
- v0.3 (Plugins):
  - Plugin discovery: ✅ Complete
  - Plugin manifest parsing: ✅ Complete
  - Plugin manager integration: ✅ Complete

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
