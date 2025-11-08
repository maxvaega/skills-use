# Data Model: Pytest Test Suite

**Feature**: 001-pytest-test-scripts
**Date**: November 5, 2025
**Status**: Complete

## Overview

This document defines the data entities, relationships, and validation rules for the pytest test suite. The test suite validates the skillkit library v0.1.0, so the primary entities are **test fixtures** (static SKILL.md files) and **test helpers** (programmatic data generation).

---

## Core Entities

### 1. TestFixture (Static SKILL.md Files)

Represents a pre-created SKILL.md file in `tests/fixtures/skills/` used for testing various scenarios.

**Attributes**:
- `name` (str): Fixture directory name (e.g., "valid-basic", "invalid-missing-name")
- `category` (FixtureCategory): Classification - VALID, INVALID, or EDGE_CASE
- `path` (Path): Absolute path to fixture directory (e.g., `tests/fixtures/skills/valid-basic/`)
- `skill_file_path` (Path): Path to SKILL.md file within fixture directory
- `description` (str): Human-readable description of what the fixture tests
- `expected_behavior` (ExpectedBehavior): What should happen when parsing/loading this fixture

**Validation Rules**:
- `name` must match directory name pattern: `(valid|invalid|edge)-*`
- `path` must exist and contain a `SKILL.md` file
- `skill_file_path` must be `path / "SKILL.md"`
- `category` must align with name prefix:
  - `valid-*` → FixtureCategory.VALID
  - `invalid-*` → FixtureCategory.INVALID
  - `edge-*` → FixtureCategory.EDGE_CASE

**Example**:
```python
TestFixture(
    name="valid-basic",
    category=FixtureCategory.VALID,
    path=Path("tests/fixtures/skills/valid-basic"),
    skill_file_path=Path("tests/fixtures/skills/valid-basic/SKILL.md"),
    description="Minimal valid skill with all required fields",
    expected_behavior=ExpectedBehavior(
        should_parse=True,
        should_discover=True,
        should_invoke=True,
        expected_exception=None
    )
)
```

---

### 2. FixtureCategory (Enum)

Classification of test fixtures by test purpose.

**Values**:
- `VALID`: Skills that should parse and load successfully
- `INVALID`: Skills with missing/malformed fields that should raise ValidationError
- `EDGE_CASE`: Skills testing boundary conditions (large files, special chars, symlinks)

---

### 3. ExpectedBehavior (Dataclass)

Defines the expected outcome when using a test fixture.

**Attributes**:
- `should_parse` (bool): Should SkillParser.parse() succeed?
- `should_discover` (bool): Should discovery include this skill?
- `should_invoke` (bool): Should skill.invoke() work?
- `expected_exception` (Optional[Type[Exception]]): Exception type to expect (e.g., ValidationError)
- `expected_error_message` (Optional[str]): Regex pattern for error message (used with pytest.raises(match=...))
- `expected_warnings` (List[str]): Warning messages to expect in logs

**Validation Rules**:
- If `should_parse=False`, `expected_exception` must not be None
- If `should_discover=False`, `expected_warnings` should contain reason
- If `should_invoke=False` but `should_parse=True`, indicates runtime error

**Example**:
```python
# Valid skill
ExpectedBehavior(
    should_parse=True,
    should_discover=True,
    should_invoke=True,
    expected_exception=None,
    expected_error_message=None,
    expected_warnings=[]
)

# Invalid skill (missing name)
ExpectedBehavior(
    should_parse=False,
    should_discover=False,
    should_invoke=False,
    expected_exception=ValidationError,
    expected_error_message="name is required",
    expected_warnings=["Skipping invalid skill"]
)
```

---

### 4. SkillFactory (Fixture Function)

Programmatic skill generator for dynamic test scenarios.

**Signature**:
```python
def skill_factory(
    name: str,
    description: str,
    content: str,
    allowed_tools: Optional[List[str]] = None,
    **extra_frontmatter: Any
) -> Path:
    """
    Create a SKILL.md file in temp directory.

    Args:
        name: Skill name (frontmatter field)
        description: Skill description (frontmatter field)
        content: Skill content body (after frontmatter)
        allowed_tools: Optional list of allowed tools
        **extra_frontmatter: Additional YAML fields to include

    Returns:
        Path to created skill directory

    Raises:
        ValueError: If skill directory already exists
    """
```

**Implementation** (in conftest.py):
```python
@pytest.fixture
def skill_factory(temp_skills_dir):
    """Factory for creating test SKILL.md files."""
    created_skills = []

    def _create_skill(name: str, description: str, content: str,
                      allowed_tools: Optional[List[str]] = None,
                      **extra_frontmatter: Any) -> Path:
        skill_dir = temp_skills_dir / name
        if skill_dir.exists():
            raise ValueError(f"Skill {name} already exists in temp directory")

        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"

        # Build frontmatter
        frontmatter = f"""---
name: {name}
description: {description}
"""
        if allowed_tools:
            frontmatter += f"allowed-tools: {allowed_tools}\n"

        for key, value in extra_frontmatter.items():
            frontmatter += f"{key}: {value}\n"

        frontmatter += "---\n\n"

        # Write file
        skill_file.write_text(frontmatter + content, encoding="utf-8")
        created_skills.append(skill_dir)

        return skill_dir

    yield _create_skill

    # Cleanup: temp_skills_dir fixture handles deletion
```

**Usage Examples**:
```python
def test_discovery(temp_skills_dir, skill_factory):
    # Create 5 skills programmatically
    skill_factory("skill-1", "First skill", "Content 1")
    skill_factory("skill-2", "Second skill", "Content 2")
    skill_factory("skill-3", "Third skill", "Content 3")
    skill_factory("skill-4", "Fourth skill", "Content 4")
    skill_factory("skill-5", "Fifth skill", "Content 5")

    manager = SkillManager(temp_skills_dir)
    discovered = manager.discover()

    assert len(discovered) == 5

def test_arguments_substitution(temp_skills_dir, skill_factory):
    skill_dir = skill_factory(
        "test-args",
        "Test arguments",
        "Hello $ARGUMENTS!"
    )

    manager = SkillManager(temp_skills_dir)
    skill = manager.get_skill("test-args")
    result = skill.invoke(arguments="World")

    assert result == "Hello World!"
```

---

### 5. PerformanceMetric (Dataclass)

Captures performance measurement data from performance tests.

**Attributes**:
- `metric_name` (str): Name of metric (e.g., "discovery_time", "invocation_overhead")
- `value` (float): Measured value
- `unit` (str): Unit of measurement (e.g., "seconds", "milliseconds", "megabytes")
- `threshold` (float): Maximum allowed value
- `passes` (bool): Does value meet threshold? (value <= threshold)
- `context` (Dict[str, Any]): Additional context (e.g., skill_count, iterations)

**Validation Rules**:
- `value` must be >= 0
- `threshold` must be > 0
- `passes` must equal `value <= threshold`

**Example**:
```python
PerformanceMetric(
    metric_name="discovery_time",
    value=0.423,
    unit="seconds",
    threshold=0.5,
    passes=True,
    context={"skill_count": 50, "platform": "darwin"}
)
```

---

### 6. CoverageReport (Dataclass)

Represents code coverage measurement results.

**Attributes**:
- `module_name` (str): Module being tested (e.g., "src/skillkit/core/discovery.py")
- `line_coverage` (float): Percentage of lines covered (0-100)
- `branch_coverage` (float): Percentage of branches covered (0-100)
- `missing_lines` (List[int]): Line numbers not covered by tests
- `passes_threshold` (bool): Does line_coverage >= 70%?

**Validation Rules**:
- `line_coverage` must be 0-100
- `branch_coverage` must be 0-100
- `passes_threshold` = `line_coverage >= 70.0`

**Example**:
```python
CoverageReport(
    module_name="src/skillkit/core/discovery.py",
    line_coverage=82.5,
    branch_coverage=75.3,
    missing_lines=[145, 167, 203],
    passes_threshold=True
)
```

---

## Entity Relationships

### Fixture → ExpectedBehavior (1:1)
Each TestFixture has exactly one ExpectedBehavior defining what should happen when using that fixture.

```text
TestFixture "valid-basic"
    └── ExpectedBehavior(should_parse=True, should_discover=True, ...)

TestFixture "invalid-missing-name"
    └── ExpectedBehavior(should_parse=False, expected_exception=ValidationError, ...)
```

### SkillFactory → Skill Files (1:N)
One SkillFactory fixture can create multiple SKILL.md files in a test.

```text
skill_factory(temp_skills_dir)
    ├── Creates skill-1/SKILL.md
    ├── Creates skill-2/SKILL.md
    └── Creates skill-N/SKILL.md
```

### Test Function → PerformanceMetric (1:N)
One performance test can capture multiple metrics.

```text
test_discovery_performance()
    ├── PerformanceMetric(metric_name="discovery_time", ...)
    └── PerformanceMetric(metric_name="memory_usage", ...)
```

### Test Suite → CoverageReport (1:N)
Overall test suite execution produces one CoverageReport per module.

```text
pytest run
    ├── CoverageReport(module_name="discovery.py", line_coverage=82.5%)
    ├── CoverageReport(module_name="parser.py", line_coverage=88.1%)
    └── CoverageReport(module_name="manager.py", line_coverage=76.3%)
```

---

## Data Flow Diagrams

### Test Execution Flow

```text
┌─────────────────┐
│  pytest starts  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Load conftest.py       │
│  - Register fixtures    │
│  - Define helpers       │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Discover test files    │
│  - test_discovery.py    │
│  - test_parser.py       │
│  - ... (9 test files)   │
└────────┬────────────────┘
         │
         ▼
┌─────────────────────────┐
│  For each test function │
└────────┬────────────────┘
         │
         ├─► Inject fixtures (temp_skills_dir, skill_factory, etc.)
         │
         ├─► Setup test data
         │   - Load static fixtures from tests/fixtures/skills/
         │   - OR generate dynamic data via skill_factory
         │
         ├─► Execute test logic
         │   - Call library functions (discover, parse, invoke)
         │   - Capture results
         │
         ├─► Assert expected outcomes
         │   - Use native assert statements
         │   - Check exception types/messages
         │   - Validate performance metrics
         │
         └─► Cleanup (handled by fixtures)
                 │
                 ▼
         ┌─────────────────┐
         │  Next test      │
         └─────────────────┘
```

### Fixture Data Flow

```text
┌──────────────────────────┐
│  Static Fixtures         │
│  tests/fixtures/skills/  │
│  - valid-basic/          │
│  - invalid-missing-name/ │
│  - edge-large-content/   │
└──────────┬───────────────┘
           │
           │ (read at test time)
           │
           ▼
   ┌───────────────────┐
   │  Test Function    │
   │  (e.g., test_*)   │
   └───────┬───────────┘
           │
           │ (assert expectations)
           │
           ▼
   ┌────────────────────────┐
   │  Expected Behavior     │
   │  - should_parse=False  │
   │  - expected_exception  │
   └────────────────────────┘


┌──────────────────────────┐
│  Dynamic Generation      │
│  skill_factory fixture   │
└──────────┬───────────────┘
           │
           │ (create at test time)
           │
           ▼
   ┌─────────────────────┐
   │  temp_skills_dir/   │
   │  - skill-1/         │
   │  - skill-2/         │
   │  - ... skill-N/     │
   └─────────┬───────────┘
             │
             │ (cleanup after test)
             │
             ▼
   ┌─────────────────────┐
   │  Temporary cleanup  │
   │  (tmp_path handles) │
   └─────────────────────┘
```

### Coverage Measurement Flow

```text
┌─────────────────────┐
│  pytest --cov       │
└──────────┬──────────┘
           │
           ▼
┌──────────────────────────┐
│  pytest-cov plugin       │
│  - Instruments source    │
│  - Tracks line execution │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Run all tests           │
│  - Execute library code  │
│  - Track which lines run │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Generate reports        │
│  - Terminal summary      │
│  - HTML detailed report  │
│  - JSON data export      │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  Check threshold         │
│  - Is coverage >= 70%?   │
│  - Fail build if not     │
└──────────────────────────┘
```

---

## Validation Rules Summary

### TestFixture Validation
1. `name` must match directory name
2. `path` must exist and be a directory
3. `skill_file_path` must exist and be a file named "SKILL.md"
4. `category` must align with name prefix (valid/invalid/edge)
5. `expected_behavior` must be consistent with category

### ExpectedBehavior Validation
1. If `should_parse=False`, must specify `expected_exception`
2. If `expected_exception` is set, must provide `expected_error_message` pattern
3. If `should_invoke=True`, `should_parse` must also be True
4. `expected_warnings` must be non-empty if `should_discover=False` but file is valid YAML

### PerformanceMetric Validation
1. `value` >= 0
2. `threshold` > 0
3. `passes` must equal `value <= threshold`
4. `unit` must be one of: "seconds", "milliseconds", "megabytes", "count"

### CoverageReport Validation
1. `line_coverage` in range [0, 100]
2. `branch_coverage` in range [0, 100]
3. `passes_threshold` = (`line_coverage` >= 70.0)
4. `missing_lines` must be sorted and contain valid line numbers

---

## State Transitions

### Test Execution Lifecycle

```text
┌──────────────┐
│   PENDING    │ ← Test queued by pytest
└──────┬───────┘
       │
       │ pytest runs test
       ▼
┌──────────────┐
│   RUNNING    │ ← Fixtures injected, test logic executing
└──────┬───────┘
       │
       ├─► Assertions pass
       │   ├─► PASSED ✅
       │   └─► Mark as PASSED in report
       │
       ├─► Assertion fails
       │   ├─► FAILED ❌
       │   └─► Show diff + traceback
       │
       ├─► Exception raised (not expected)
       │   ├─► ERROR 💥
       │   └─► Show exception traceback
       │
       └─► pytest.skip() called
           ├─► SKIPPED ⏭️
           └─► Show skip reason
```

### Fixture Lifecycle

```text
┌────────────────┐
│  NOT LOADED    │ ← Fixture defined in conftest.py
└────────┬───────┘
         │
         │ Test requests fixture
         ▼
┌────────────────┐
│  SETUP         │ ← Fixture function runs (before yield)
└────────┬───────┘
         │
         ▼
┌────────────────┐
│  ACTIVE        │ ← Test uses fixture value
└────────┬───────┘
         │
         │ Test completes (pass or fail)
         ▼
┌────────────────┐
│  TEARDOWN      │ ← Fixture cleanup runs (after yield)
└────────┬───────┘
         │
         ▼
┌────────────────┐
│  DISPOSED      │ ← Fixture no longer in memory
└────────────────┘

Scopes:
- function: SETUP/TEARDOWN per test
- class: SETUP once per test class, TEARDOWN after class
- module: SETUP once per test file, TEARDOWN after file
- session: SETUP once for entire test run, TEARDOWN at end
```

---

## Performance Characteristics

### Test Fixture Operations

| Operation | Latency | Notes |
|-----------|---------|-------|
| Load static fixture | <5ms | Read SKILL.md from disk |
| Generate skill via factory | <10ms | Create directory + write file |
| Cleanup temp directory | <50ms | Delete all generated files |
| Fixture setup (function scope) | <15ms | Create temp_skills_dir, register factory |

### Test Execution Performance

| Test Category | Count | Expected Duration | Notes |
|---------------|-------|-------------------|-------|
| Discovery tests | 8-10 | <5s | Fast filesystem operations |
| Parser tests | 10-12 | <3s | YAML parsing + validation |
| Model tests | 5-8 | <2s | Dataclass instantiation |
| Processor tests | 8-10 | <5s | String substitution + file I/O |
| Manager tests | 6-8 | <4s | Orchestration logic |
| LangChain tests | 4-6 | <8s | Integration with external framework |
| Edge case tests | 8-10 | <10s | Large files, permission errors |
| Performance tests | 4-6 | <15s | 50-skill generation + timing |
| Installation tests | 3-5 | <10s | Virtualenv operations (slow) |
| **Total** | **50-75** | **<60s** | **Full suite target** |

### Memory Usage

| Component | Memory | Notes |
|-----------|--------|-------|
| pytest process | ~50MB | Base pytest + plugins |
| Loaded fixtures | ~5MB | Static SKILL.md files in memory |
| Generated skills (50) | ~2MB | Temporary files |
| Test results | ~1MB | Pass/fail status, tracebacks |
| Coverage data | ~10MB | Line execution tracking |
| **Total** | **~70MB** | **Peak during performance tests** |

---

## Dependencies on Production Code

The test suite validates the following production entities (defined in src/skillkit/):

### SkillMetadata (models.py)
- Validated by: `test_models.py`, `test_discovery.py`
- Fields tested: name, description, skill_path, allowed_tools

### Skill (models.py)
- Validated by: `test_models.py`, `test_processors.py`
- Methods tested: invoke(), content property (lazy loading)

### SkillDiscovery (discovery.py)
- Validated by: `test_discovery.py`
- Methods tested: discover_skills(), handle_duplicates()

### SkillParser (parser.py)
- Validated by: `test_parser.py`
- Methods tested: parse(), validate_frontmatter()

### ContentProcessor (processors.py)
- Validated by: `test_processors.py`
- Methods tested: process(), substitute_arguments()

### SkillManager (manager.py)
- Validated by: `test_manager.py`
- Methods tested: discover(), get_skill(), list_skills()

### create_langchain_tools() (integrations/langchain.py)
- Validated by: `test_langchain_integration.py`
- Returns: List[StructuredTool]

### Exception Hierarchy (exceptions.py)
- Validated by: All test files
- Exceptions tested: SkillError, ValidationError, ContentLoadError, SizeLimitExceededError

---

## Python Version Compatibility

Tests must pass on Python 3.9, 3.10, 3.11, and 3.12.

**Known compatibility considerations**:
- **Python 3.9**: No `slots=True` in dataclasses (slightly higher memory usage, functionally identical)
- **Python 3.10+**: Optimal performance with slots + cached_property
- **Python 3.11+**: Faster pytest execution due to performance improvements
- **Python 3.12**: New exception handling may affect traceback assertions

**Testing strategy**:
- Primary development on Python 3.10 (default `python3` alias)
- Manual validation on 3.9, 3.11, 3.12 before release
- CI/CD (future) will test all versions automatically

---

## Next Steps

1. **contracts/test-api.md**: Document public test fixtures, helper functions, pytest markers
2. **quickstart.md**: Create "Running Tests" guide for developers
3. **tasks.md**: Generate implementation tasks for writing actual tests

---

**Data Model Complete**: All test entities, relationships, and validation rules defined. Ready for contracts and quickstart generation.
