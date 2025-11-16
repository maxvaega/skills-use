# Feature Specification: Automated Pytest Test Suite for skillkit v0.1.0

**Feature Branch**: `001-pytest-test-scripts`
**Created**: November 5, 2025
**Status**: Draft
**Input**: User description: "pytest scripts for skillkit library (local packages before pytest upload)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Core Functionality Validation (Priority: P1)

As a library maintainer, I need automated pytest scripts that validate all core functionality (discovery, parsing, invocation) so that I can quickly verify the local library files works correctly before publishing to PyPI.

**Why this priority**: Core functionality is the foundation of the library. Without these tests passing, the library is unusable and cannot be published. This represents the minimum viable test suite.

**Independent Test**: Can be fully tested by running `pytest tests/test_core.py -v` with python 3.10 and delivers confidence that basic discovery, parsing, and invocation work correctly with various skill configurations.

**Acceptance Scenarios**:

1. **Given** a skill directory with 5-10 real skills, **When** running discovery tests, **Then** all skills are found and metadata is correctly parsed
2. **Given** skills with various SKILL.md configurations, **When** running parser tests, **Then** valid skills pass and invalid skills (missing fields, bad YAML) fail with helpful error messages
3. **Given** a loaded skill with arguments, **When** running invocation tests, **Then** $ARGUMENTS substitution works correctly and content is returned
4. **Given** an empty skill directory, **When** running discovery tests, **Then** system handles it gracefully with appropriate INFO logging
5. **Given** skills with Unicode content and emojis, **When** running parser tests, **Then** content is correctly parsed and handled

---

### User Story 2 - LangChain Integration Validation (Priority: P1)

As a library maintainer, I need automated pytest scripts that validate LangChain integration so that I can ensure the library correctly creates tools that agents can invoke.

**Why this priority**: LangChain integration is a core feature of v0.1.0 and advertised as a primary use case. Without these tests, we cannot guarantee the integration works.

**Independent Test**: Can be fully tested by running `pytest tests/test_langchain_integration.py -v` and delivers confidence that tools are created correctly and callable by LangChain agents.

**Acceptance Scenarios**:

1. **Given** a SkillManager with 3+ discovered skills, **When** running create_langchain_tools(), **Then** all skills are converted to LangChain StructuredTool objects
2. **Given** a LangChain tool created from a skill, **When** invoking the tool with test arguments, **Then** the skill executes correctly and returns expected output
3. **Given** a skill that raises an error, **When** invoking via LangChain tool, **Then** error is caught gracefully and propagated correctly
4. **Given** a skill with long arguments (10KB+), **When** invoking via LangChain, **Then** arguments are processed correctly without truncation

---

### User Story 3 - Edge Case and Error Handling Validation (Priority: P2)

As a library maintainer, I need automated pytest scripts that validate edge cases and error handling so that I can ensure the library behaves predictably in unusual or error conditions.

**Why this priority**: Edge case handling is critical for library reliability but not required for basic functionality. These tests catch bugs that would cause production issues.

**Independent Test**: Can be fully tested by running `pytest tests/test_edge_cases.py -v` and delivers confidence that the library handles malformed inputs, permission errors, and boundary conditions gracefully.

**Acceptance Scenarios**:

1. **Given** a skill file with missing required fields (name, description), **When** running discovery, **Then** error is logged and discovery continues for other skills
2. **Given** a skill file with invalid YAML syntax, **When** parsing, **Then** ValidationError is raised with helpful message
3. **Given** a skill file deleted after discovery, **When** attempting invocation, **Then** ContentLoadError is raised with clear message
4. **Given** duplicate skill names in different directories, **When** running discovery, **Then** first skill wins and WARNING is logged
5. **Given** a skill file with no read permissions, **When** running discovery, **Then** error is logged and discovery continues
6. **Given** a large skill file (500KB+), **When** loading content, **Then** lazy loading works correctly

---

### User Story 4 - Performance and Scale Validation (Priority: P3)

As a library maintainer, I need automated pytest scripts that validate performance characteristics so that I can ensure the library meets performance targets defined in the technical specifications.

**Why this priority**: Performance testing validates non-functional requirements but is not critical for basic functionality. These tests ensure the library scales appropriately.

**Independent Test**: Can be fully tested by running `pytest tests/test_performance.py -v` and delivers measurable performance metrics for discovery, invocation, and memory usage.

**Acceptance Scenarios**:

1. **Given** 50 skills in a directory, **When** running discovery, **Then** completion time is under 500ms (target: ~5-10ms per skill)
2. **Given** 50 discovered skills, **When** measuring memory footprint, **Then** total memory usage is under 5MB (target: ~2-5MB for 50 skills)
3. **Given** a skill loaded for invocation, **When** invoking 100 times sequentially, **Then** average invocation overhead is under 25ms
4. **Given** multiple concurrent invocations of the same skill, **When** measuring cache effectiveness, **Then** no repeated file reads occur after first load

---

### User Story 5 - Installation and Environment Validation (Priority: P2)

As a library maintainer, I need automated pytest scripts that validate installation and import behavior so that I can ensure the package installs correctly across different Python versions and environments.

**Why this priority**: Installation testing is critical for user experience but can be tested semi-manually during pre-publication checks. Automated tests reduce publication risk.

**Independent Test**: Can be fully tested by running `pytest tests/test_installation.py -v` in a fresh virtualenv and delivers confidence that package structure, imports, and dependencies are correct.

**Acceptance Scenarios**:

1. **Given** a fresh virtualenv with Python 3.9, **When** installing from wheel, **Then** all imports work correctly
2. **Given** installation without `[langchain]` extras, **When** importing core modules, **Then** no dependency errors occur
3. **Given** installation with `[langchain]` extras, **When** importing langchain integration, **Then** all dependencies are satisfied
4. **Given** the installed package, **When** checking version and metadata, **Then** correct version (0.1.0) and metadata are returned

---

### Edge Cases

- What happens when a skill directory contains symbolic links to other skills?
- How does the system handle Windows line endings (`\r\n`) in SKILL.md files on Unix systems?
- What happens when skills have identical names but different casing (e.g., `code-reviewer` vs `Code-Reviewer`)?
- How does the system handle extremely long skill names (>255 characters)?
- What happens when $ARGUMENTS contains special characters that could cause injection attacks?
- How does the system handle skills with circular references in their content?
- What happens when the `.claude/skills/` directory is a symlink?
- How does the system handle concurrent discovery operations on the same directory?

## Requirements *(mandatory)*

### Functional Requirements

#### Core Testing Infrastructure (P1)

- **FR-001**: Test suite MUST use pytest framework with fixtures defined in `conftest.py`
- **FR-002**: Tests MUST achieve minimum 70% code coverage as defined in v0.1.0 specifications
- **FR-003**: Test suite MUST be runnable with single command `pytest` from project root
- **FR-004**: Tests MUST use parametrized testing for multiple input scenarios (valid/invalid skills, various Python versions)
- **FR-005**: Test fixtures MUST include realistic SKILL.md files covering all edge cases (missing fields, invalid YAML, Unicode content)

#### Discovery and Parsing Tests (P1)

- **FR-006**: Tests MUST validate discovery of 5-10 real skills from filesystem
- **FR-007**: Tests MUST validate parsing of valid SKILL.md files with all required fields (name, description, content)
- **FR-008**: Tests MUST validate error handling for malformed SKILL.md files (missing name, missing description, invalid YAML)
- **FR-009**: Tests MUST validate handling of empty skill directories with appropriate logging
- **FR-010**: Tests MUST validate Unicode content parsing including emoji and non-ASCII characters
- **FR-011**: Tests MUST validate duplicate skill name detection with WARNING logging

#### Invocation and Processing Tests (P1)

- **FR-012**: Tests MUST validate $ARGUMENTS substitution with various argument types (strings, numbers, special characters)
- **FR-013**: Tests MUST validate skill invocation returns correct content
- **FR-014**: Tests MUST validate multiple invocations of same skill use caching (no repeated file reads)
- **FR-015**: Tests MUST validate ContentLoadError when skill file is deleted after discovery
- **FR-016**: Tests MUST validate argument size limit enforcement (1MB threshold with SizeLimitExceededError)

#### LangChain Integration Tests (P1)

- **FR-017**: Tests MUST validate create_langchain_tools() creates StructuredTool objects for all discovered skills
- **FR-018**: Tests MUST validate LangChain tools are callable with correct argument schema
- **FR-019**: Tests MUST validate error propagation from skills to LangChain tools
- **FR-020**: Tests MUST validate tool invocation with long arguments (10KB+)

#### Edge Case Tests (P2)

- **FR-021**: Tests MUST validate permission error handling (skill files with no read permissions)
- **FR-022**: Tests MUST validate symlink handling in skill directories
- **FR-023**: Tests MUST validate Windows line ending handling (`\r\n`) on Unix systems
- **FR-024**: Tests MUST validate large skill file lazy loading (500KB+ content)
- **FR-025**: Tests MUST validate security patterns detection for suspicious arguments (command injection patterns)

#### Performance Tests (P3)

- **FR-026**: Tests MUST measure discovery time for 50 skills and validate under 500ms
- **FR-027**: Tests MUST measure memory usage for 50 skills and validate under 5MB
- **FR-028**: Tests MUST measure invocation overhead and validate under 25ms average for 100 invocations
- **FR-029**: Tests MUST validate cache effectiveness by monitoring file I/O operations

#### Installation Tests (P2)

- **FR-030**: Tests MUST validate clean virtualenv installation from built wheel
- **FR-031**: Tests MUST validate import success for all public API exports
- **FR-032**: Tests MUST validate dependency resolution with and without `[langchain]` extras
- **FR-033**: Tests MUST validate correct package version and metadata

### Key Entities

- **Test Fixture**: Represents a SKILL.md file configuration used for testing (valid, invalid YAML, missing fields, Unicode content, etc.)
- **Test Skill Directory**: Temporary directory structure containing test SKILL.md files for discovery testing
- **Performance Metric**: Measurement data collected during performance tests (discovery time, memory usage, invocation overhead)
- **Coverage Report**: Test coverage data showing which code paths are exercised by tests

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Test suite achieves minimum 70% code coverage across all modules (discovery, parser, models, manager, processors)
- **SC-002**: All core functionality tests (FR-006 through FR-016) pass consistently on Python 3.9 and 3.10
- **SC-003**: All LangChain integration tests (FR-017 through FR-020) pass with actual LangChain agent invocations
- **SC-004**: Performance tests validate discovery time under 500ms for 50 skills
- **SC-005**: Performance tests validate memory usage under 5MB for 50 skills
- **SC-006**: Performance tests validate invocation overhead under 25ms average
- **SC-007**: Test suite completes full run in under 60 seconds on standard developer hardware
- **SC-008**: All edge case tests (FR-021 through FR-025) pass and demonstrate graceful error handling
- **SC-009**: Installation tests pass in fresh virtualenvs on Python 3.9, 3.10, 3.11, and 3.12
- **SC-010**: Zero test flakiness - all tests pass consistently across multiple runs

## Out of Scope

The following are explicitly **NOT** included in this feature:

- Cross-platform testing on Windows or Linux (manual testing only for v0.1.0)
- Async testing (deferred to v0.2 when async support is added)
- Integration tests with other frameworks (LlamaIndex, CrewAI, Haystack - deferred to v0.3)
- Load testing or stress testing beyond 50 skills
- Automated CI/CD pipeline setup (manual pytest execution for v0.1.0)
- Test coverage above 70% (stretch goal for v1.0)
- Security penetration testing (basic validation only)

## Assumptions

1. **Test Environment**: Tests will run on developer machines with multiple versions of Python installed. Run all tests using python 3.10 (python3 alias)
2. **File System**: Tests assume POSIX-compliant filesystem with standard permissions model
3. **Dependencies**: All dependencies specified in `pyproject.toml` are correctly installed
4. **Test Data**: Fixture SKILL.md files will be manually created and maintained in `tests/fixtures/skills/`
5. **Performance Baseline**: Performance tests assume modern hardware (SSD, 8GB+ RAM, multi-core CPU)
6. **Coverage Tool**: pytest-cov plugin will be used for coverage measurement
7. **Isolation**: Tests will use temporary directories and will not modify actual `.claude/skills/` directory

## Open Questions

None - All requirements are clear and testable based on existing technical specifications and testing plan.

## Notes

- This specification is derived from `tests.local.md`, which provides comprehensive pre-publication testing checklist
- Test suite should align with v0.1.0 MVP scope (sync-only, LangChain integration, core functionality)
- Priority levels ensure core functionality tests (P1) are implemented first, followed by quality tests (P2) and performance tests (P3)
- Each user story is independently testable and can be developed/validated separately
- Success criteria are measurable and aligned with technical specifications in `.docs/TECH_SPECS.md`
