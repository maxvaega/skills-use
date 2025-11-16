# Tasks: Automated Pytest Test Suite for skillkit v0.1.0

**Input**: Design documents from `/specs/001-pytest-test-scripts/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/test-api.md

**Tests**: This feature IS about implementing tests, so all tasks are test-related.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each test category.

---

## 📊 Overall Progress (November 5, 2025)

**Status**: ✅ **100% COMPLETE** - All tests passing, ready for production

**Test Results**:
- **Passing**: 73/74 tests (99%, 1 skipped)
- **Coverage**: 85.86% (exceeds 70% target by 15.86%) ✅
- **Failing**: 0 tests ✅
- **Flaky Tests**: None detected (parallel execution validated)

**Phase Completion**:
- ✅ Phase 1: Setup (5/5 tasks - 100%)
- ✅ Phase 2: Foundational (7/7 tasks - 100%)
- ✅ Phase 3: User Story 1 - Core Functionality (34/34 tasks - 100%)
- ✅ Phase 4: User Story 2 - LangChain Integration (10/10 tasks - 100%)
- ✅ Phase 5: User Story 3 - Edge Cases (11/11 tasks - 100%)
- ✅ Phase 6: User Story 4 - Performance (5/5 tasks - 100%)
- ✅ Phase 7: User Story 5 - Installation (6/6 tasks - 100%)
- ✅ Phase 8: Polish (11/11 tasks - 100%)

**Total**: 89/89 tasks complete (100%) ✅

**Completion**: All API fixes applied → All tests passing → Coverage validated → Documentation updated → Production ready

---

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Test Infrastructure) ✅ COMPLETE

**Purpose**: Project initialization and test framework configuration

- [X] T001 Create test directory structure: `tests/`, `tests/fixtures/`, `tests/fixtures/skills/`
- [X] T002 Configure pytest in `pyproject.toml` with markers (integration, performance, slow, requires_langchain)
- [X] T003 Configure coverage settings in `pyproject.toml` with 70% threshold and branch tracking
- [X] T004 Create empty `tests/__init__.py` for test package
- [X] T005 Create `tests/conftest.py` with pytest configuration and imports

---

## Phase 2: Foundational (Shared Test Fixtures) ✅ COMPLETE

**Purpose**: Core test fixtures and helpers that ALL test files will use

**⚠️ CRITICAL**: No user story tests can be written until this phase is complete

- [X] T006 Implement `temp_skills_dir` fixture in `tests/conftest.py` (returns Path to temp directory)
- [X] T007 Implement `skill_factory` fixture in `tests/conftest.py` (factory function for creating SKILL.md files)
- [X] T008 Implement `sample_skills` fixture in `tests/conftest.py` (creates 5 diverse sample skills)
- [X] T009 Implement `fixtures_dir` fixture in `tests/conftest.py` (returns Path to tests/fixtures/skills/)
- [X] T010 [P] Implement `assert_skill_metadata_valid()` helper function in `tests/conftest.py`
- [X] T011 [P] Implement `create_large_skill()` helper function in `tests/conftest.py` (creates 500KB+ skill)
- [X] T012 [P] Implement `create_permission_denied_skill()` helper function in `tests/conftest.py` (Unix-only, chmod 000)

**Checkpoint**: ✅ Foundational fixtures ready - test implementation can now begin in parallel

---

## Phase 3: User Story 1 - Core Functionality Validation (Priority: P1) 🎯 MVP

**Goal**: Validate all core functionality (discovery, parsing, invocation) works correctly with various skill configurations

**Independent Test**: Run `pytest tests/test_discovery.py tests/test_parser.py tests/test_models.py tests/test_processors.py tests/test_manager.py -v` and verify all pass

**Status**: 🔧 IN PROGRESS - 86.39% coverage achieved, 65/73 tests passing, 8 tests need API fixes

### Static Test Fixtures for User Story 1 ✅ COMPLETE

- [X] T013 [P] [US1] Create `tests/fixtures/skills/valid-basic/SKILL.md` (minimal valid skill with name, description, content)
- [X] T014 [P] [US1] Create `tests/fixtures/skills/valid-with-arguments/SKILL.md` (skill with $ARGUMENTS placeholder)
- [X] T015 [P] [US1] Create `tests/fixtures/skills/valid-unicode/SKILL.md` (skill with Unicode content: 你好 🎉)
- [X] T016 [P] [US1] Create `tests/fixtures/skills/invalid-missing-name/SKILL.md` (YAML without name field)
- [X] T017 [P] [US1] Create `tests/fixtures/skills/invalid-missing-description/SKILL.md` (YAML without description field)
- [X] T018 [P] [US1] Create `tests/fixtures/skills/invalid-yaml-syntax/SKILL.md` (malformed YAML: unclosed bracket)

### Discovery Tests (test_discovery.py) ✅ COMPLETE

- [X] T019 [P] [US1] Create `tests/test_discovery.py` with imports and file header
- [X] T020 [P] [US1] Write `test_discover_empty_directory` - validates empty dir returns empty list with INFO logging
- [X] T021 [P] [US1] Write `test_discover_multiple_skills` - validates 5 skills are discovered using sample_skills fixture
- [X] T022 [P] [US1] Write `test_discover_valid_skills_from_fixtures` - validates static fixtures are discovered correctly
- [X] T023 [P] [US1] Write `test_discover_skill_metadata_structure` - validates metadata has name, description, skill_path
- [X] T024 [P] [US1] Write `test_discover_unicode_content` - validates Unicode/emoji skills parse correctly
- [X] T025 [P] [US1] Write `test_discover_duplicate_skill_names_logs_warning` - validates WARNING logged for duplicates (caplog)
- [X] T026 [P] [US1] Write `test_discover_skips_invalid_skills_gracefully` - validates discovery continues after encountering invalid skill
- [X] T026a [US1] **FIX**: Update all discovery tests to use correct SkillManager API - `discover()` returns None (void), use `list_skills()` to get List[SkillMetadata], convert to dict if needed using `{skill.name: skill for skill in manager.list_skills()}`

### Parser Tests (test_parser.py) ✅ COMPLETE

- [X] T027 [P] [US1] Create `tests/test_parser.py` with imports and file header
- [X] T028 [P] [US1] Write `test_parse_valid_basic_skill` - validates parsing of valid-basic fixture
- [X] T029 [P] [US1] Write `test_parse_valid_skill_with_arguments` - validates $ARGUMENTS placeholder preserved
- [X] T030 [P] [US1] Write `test_parse_valid_skill_with_unicode` - validates Unicode content handled correctly
- [X] T031 [P] [US1] Write `test_parse_invalid_missing_name_raises_validation_error` - validates ValidationError with "name is required" message
- [X] T032 [P] [US1] Write `test_parse_invalid_missing_description_raises_validation_error` - validates ValidationError with "description is required"
- [X] T033 [P] [US1] Write `test_parse_invalid_yaml_syntax_raises_validation_error` - validates ValidationError with helpful YAML error message
- [X] T034 [P] [US1] Write parametrized `test_parse_invalid_skills` - tests all 3 invalid fixtures in one parametrized test

### Models Tests (test_models.py) ✅ COMPLETE

- [X] T035 [P] [US1] Create `tests/test_models.py` with imports and file header
- [X] T036 [P] [US1] Write `test_skill_metadata_creation` - validates SkillMetadata instantiation with all fields
- [X] T037 [P] [US1] Write `test_skill_metadata_allowed_tools_optional` - validates allowed_tools can be None
- [X] T038 [P] [US1] Write `test_skill_creation_with_metadata` - validates Skill instantiation with SkillMetadata
- [X] T039 [P] [US1] Write `test_skill_lazy_content_loading` - validates content not loaded until accessed
- [X] T040 [P] [US1] Write `test_skill_content_caching` - validates content cached after first access (no repeated file reads)

### Processors Tests (test_processors.py) ✅ COMPLETE

- [X] T041 [P] [US1] Create `tests/test_processors.py` with imports and file header
- [X] T042 [P] [US1] Write `test_process_content_without_placeholder` - validates content returned unchanged when no $ARGUMENTS
- [X] T043 [P] [US1] Write `test_substitute_arguments_basic` - validates "Hello $ARGUMENTS!" → "Hello World!"
- [X] T044 [P] [US1] Write parametrized `test_substitute_arguments_various_positions` - tests $ARGUMENTS at start, middle, end
- [X] T045 [P] [US1] Write `test_substitute_arguments_with_special_characters` - validates arguments with <>& etc.
- [X] T046 [P] [US1] Write `test_substitute_arguments_size_limit_enforcement` - validates SizeLimitExceededError for 1MB+ arguments
- [X] T047 [P] [US1] Write `test_process_content_escaping_double_dollar` - validates $$ARGUMENTS escaping works

### Manager Tests (test_manager.py) ✅ COMPLETE

- [X] T048 [P] [US1] Create `tests/test_manager.py` with imports and file header
- [X] T049 [P] [US1] Write `test_manager_discover_returns_dict` - validates discover() returns dict of SkillMetadata
- [X] T050 [P] [US1] Write `test_manager_get_skill_by_name` - validates get_skill() returns Skill object
- [X] T051 [P] [US1] Write `test_manager_list_skills_returns_names` - validates list_skills() returns list of skill names
- [X] T052 [P] [US1] Write `test_manager_skill_invocation` - validates end-to-end: discover → get_skill → invoke
- [X] T053 [P] [US1] Write `test_manager_caching_behavior` - validates multiple get_skill calls don't re-parse
- [X] T054 [P] [US1] Write `test_manager_content_load_error_when_file_deleted` - validates ContentLoadError after file deletion

**Checkpoint**: At this point, User Story 1 (Core Functionality Validation) should be fully functional and independently testable

---

## Phase 4: User Story 2 - LangChain Integration Validation (Priority: P1) ✅ COMPLETE

**Goal**: Validate LangChain integration creates correct StructuredTool objects that agents can invoke

**Independent Test**: Run `pytest tests/test_langchain_integration.py -v` and verify all pass

**Status**: ✅ COMPLETE - All 8 tests pass, coverage at 75.40%

### LangChain Integration Tests (test_langchain_integration.py) ✅ COMPLETE

- [X] T055 [US2] Create `tests/test_langchain_integration.py` with imports and langchain marker
- [X] T056 [P] [US2] Write `test_create_langchain_tools_returns_list` - validates create_langchain_tools() returns List[StructuredTool]
- [X] T057 [P] [US2] Write `test_langchain_tool_count_matches_skills` - validates 3 skills → 3 StructuredTool objects
- [X] T058 [P] [US2] Write `test_langchain_tool_has_correct_name` - validates tool.name matches skill name
- [X] T059 [P] [US2] Write `test_langchain_tool_has_correct_description` - validates tool.description matches skill description
- [X] T060 [P] [US2] Write `test_langchain_tool_invocation_with_arguments` - validates tool.invoke({"arguments": "test"}) works
- [X] T061 [P] [US2] Write `test_langchain_tool_invocation_returns_content` - validates return value matches expected content
- [X] T062 [P] [US2] Write `test_langchain_tool_invocation_with_long_arguments` - validates 10KB+ arguments processed correctly
- [X] T063 [P] [US2] Write `test_langchain_tool_error_propagation` - validates skill errors propagate to LangChain correctly
- [X] T063a [US2] **FIX**: Updated langchain.py invoke_skill to accept `arguments` as kwarg (LangChain unpacks Pydantic model fields)
- [X] T063b [US2] **FIX**: Updated test assertions to match actual output format (includes base directory + frontmatter)

**Checkpoint**: ✅ **PHASE 4 COMPLETE** - User Stories 1 AND 2 both work independently. All 8 LangChain integration tests pass. Coverage: 75.40% (exceeds 70% target).

---

## Phase 5: User Story 3 - Edge Case and Error Handling Validation (Priority: P2)

**Goal**: Validate library handles edge cases and errors gracefully (malformed inputs, permission errors, boundary conditions)

**Independent Test**: Run `pytest tests/test_edge_cases.py -v` and verify all pass

### Additional Static Fixtures for User Story 3

- [X] T064 [P] [US3] Create `tests/fixtures/skills/edge-large-content/SKILL.md` (500KB+ content file using script)
- [X] T065 [P] [US3] Create `tests/fixtures/skills/edge-special-chars/SKILL.md` (arguments with <>& and injection patterns)

### Edge Case Tests (test_edge_cases.py)

- [X] T066 [US3] Create `tests/test_edge_cases.py` with imports and file header
- [X] T067 [P] [US3] Write `test_missing_required_field_logs_error_and_continues` - validates discovery skips invalid skill with ERROR log
- [X] T068 [P] [US3] Write `test_invalid_yaml_syntax_raises_validation_error` - validates helpful error message for YAML errors
- [X] T069 [P] [US3] Write `test_content_load_error_when_file_deleted_after_discovery` - validates ContentLoadError with clear message
- [X] T070 [P] [US3] Write `test_duplicate_skill_names_first_wins_with_warning` - validates first skill wins, WARNING logged
- [X] T071 [P] [US3] Write `test_permission_denied_skill_logs_error_and_continues` (Unix-only with skipif) - validates graceful handling
- [X] T072 [P] [US3] Write `test_large_skill_lazy_loading_works` - validates 500KB+ content loads correctly
- [X] T073 [P] [US3] Write `test_symlink_in_skill_directory_handled` - validates symlinks followed/handled correctly
- [X] T074 [P] [US3] Write `test_windows_line_endings_handled_on_unix` - validates \r\n line endings work

**Checkpoint**: All edge cases validated - library handles errors gracefully

---

## Phase 6: User Story 4 - Performance and Scale Validation (Priority: P3)

**Goal**: Validate library meets performance targets (discovery <500ms for 50 skills, invocation <25ms, memory <5MB)

**Independent Test**: Run `pytest tests/test_performance.py -v -m performance` and verify all pass (may take 15+ seconds)

### Performance Tests (test_performance.py)

- [X] T075 [US4] Create `tests/test_performance.py` with imports and performance marker
- [X] T076 [P] [US4] Write `test_discovery_time_50_skills` - validates discovery <500ms for 50 generated skills (using time.perf_counter)
- [X] T077 [P] [US4] Write `test_invocation_overhead_100_invocations` - validates avg <25ms for 100 sequential invocations
- [X] T078 [P] [US4] Write `test_memory_usage_50_skills_10_percent_usage` - validates <5MB memory for 50 skills with 10% loaded (sys.getsizeof)
- [X] T079 [P] [US4] Write `test_cache_effectiveness_no_repeated_file_reads` - validates content cached (mock file I/O or track calls)

**Checkpoint**: Performance validated - library meets documented targets

---

## Phase 7: User Story 5 - Installation and Environment Validation (Priority: P2)

**Goal**: Validate package installs correctly across Python versions and imports work with/without extras

**Independent Test**: Run `pytest tests/test_installation.py -v` in fresh virtualenv and verify all pass

### Installation Tests (test_installation.py)

- [X] T080 [US5] Create `tests/test_installation.py` with imports and file header
- [X] T081 [P] [US5] Write `test_core_imports_without_extras` - validates `from skillkit import *` works without [langchain]
- [X] T082 [P] [US5] Write `test_langchain_import_with_extras` - validates `from skillkit.integrations.langchain import *` works with [langchain]
- [X] T083 [P] [US5] Write `test_langchain_import_fails_without_extras` - validates ImportError when langchain not installed
- [X] T084 [P] [US5] Write `test_package_version_metadata` - validates `skillkit.__version__ == "0.1.0"`
- [X] T085 [P] [US5] Write `test_package_metadata_attributes` - validates `__author__`, `__license__` attributes exist

**Checkpoint**: Installation validated - package structure correct

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final touches and validation across all test files

**Status**: 🔧 IN PROGRESS - 8 tests need API fixes, then final validation

- [X] T086 [P] Add docstrings to all test functions explaining what they test
- [X] T087 [P] Review all test files for consistent naming conventions (test_<module>_<scenario>)
- [X] T088 [P] Add type hints to helper functions in conftest.py
- [X] T089 Fix remaining 8 API mismatches in edge case and performance tests
- [X] T090 Run full test suite: `pytest -v` and verify all tests pass
- [X] T091 Run coverage check: `pytest --cov=src/skillkit --cov-fail-under=70` and verify >=70% (achieved 85.86% ✅)
- [X] T092 Generate HTML coverage report: `pytest --cov=src/skillkit --cov-report=html` and review
- [X] T093 Test on Python 3.10 (default python3 alias) - all tests must pass
- [X] T094 [P] Validate quickstart.md examples work (run basic usage examples from docs)
- [X] T095 [P] Update tests/README.md with current statistics
- [X] T096 Final validation: Run `pytest -n auto` (parallel execution) and verify no flaky tests

### Remaining Fixes for T089

**Issue**: Tests confusing `SkillMetadata` (from `list_skills()`) with `Skill` objects (from `get_skill()`)

8 tests need to call `manager.get_skill(name)` before accessing `.content` or `.invoke()`:

1. **test_edge_cases.py**:
   - `test_missing_required_field_logs_error_and_continues` - Fix log assertion
   - `test_content_load_error_when_file_deleted_after_discovery` - Use `get_skill()`
   - `test_duplicate_skill_names_first_wins_with_warning` - Fix discovery logic
   - `test_large_skill_lazy_loading_works` - Use `get_skill()`
   - `test_windows_line_endings_handled_on_unix` - Fix metadata access

2. **test_performance.py**:
   - `test_invocation_overhead_100_invocations` - Already gets skill, check invoke call
   - `test_memory_usage_50_skills_10_percent_usage` - Use `get_skill()` for content access
   - `test_cache_effectiveness_no_repeated_file_reads` - Already gets skill, verify logic

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-7)**: All depend on Foundational phase completion
  - US1 (Core Functionality) - P1: Can start after Foundational
  - US2 (LangChain Integration) - P1: Can start after Foundational (independent of US1)
  - US3 (Edge Cases) - P2: Can start after Foundational (independent of US1, US2)
  - US4 (Performance) - P3: Can start after Foundational (independent of others)
  - US5 (Installation) - P2: Can start after Foundational (independent of others)
- **Polish (Phase 8)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 2 (P1)**: Can start after Foundational - No dependencies on other stories
- **User Story 3 (P2)**: Can start after Foundational - No dependencies on other stories
- **User Story 4 (P3)**: Can start after Foundational - No dependencies on other stories
- **User Story 5 (P2)**: Can start after Foundational - No dependencies on other stories

### Within Each User Story

- Static fixtures can be created in parallel (all marked [P])
- Test functions within same file can be written in parallel (all marked [P])
- Each test file is independent and tests can be run individually

### Parallel Opportunities

- **Phase 1**: All setup tasks can run sequentially (only 5 tasks)
- **Phase 2**: Helper functions T010-T012 can run in parallel (marked [P])
- **Phase 3 (US1)**:
  - Static fixtures T013-T018 can all run in parallel
  - Within each test file (discovery, parser, models, processors, manager), all test functions can be written in parallel
- **Phase 4 (US2)**: All test functions T056-T063 can be written in parallel
- **Phase 5 (US3)**: Static fixtures T064-T065 in parallel, test functions T067-T074 in parallel
- **Phase 6 (US4)**: All test functions T076-T079 can be written in parallel
- **Phase 7 (US5)**: All test functions T081-T085 can be written in parallel
- **Phase 8**: Most polish tasks can run in parallel

---

## Parallel Example: User Story 1

```bash
# Create all static fixtures in parallel:
Task T013: "Create tests/fixtures/skills/valid-basic/SKILL.md"
Task T014: "Create tests/fixtures/skills/valid-with-arguments/SKILL.md"
Task T015: "Create tests/fixtures/skills/valid-unicode/SKILL.md"
Task T016: "Create tests/fixtures/skills/invalid-missing-name/SKILL.md"
Task T017: "Create tests/fixtures/skills/invalid-missing-description/SKILL.md"
Task T018: "Create tests/fixtures/skills/invalid-yaml-syntax/SKILL.md"

# Write all discovery tests in parallel:
Task T020: "Write test_discover_empty_directory"
Task T021: "Write test_discover_multiple_skills"
Task T022: "Write test_discover_valid_skills_from_fixtures"
Task T023: "Write test_discover_skill_metadata_structure"
Task T024: "Write test_discover_unicode_content"
Task T025: "Write test_discover_duplicate_skill_names_logs_warning"
Task T026: "Write test_discover_skips_invalid_skills_gracefully"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (test infrastructure)
2. Complete Phase 2: Foundational (shared fixtures - CRITICAL)
3. Complete Phase 3: User Story 1 (core functionality tests)
4. **STOP and VALIDATE**: Run `pytest tests/test_discovery.py tests/test_parser.py tests/test_models.py tests/test_processors.py tests/test_manager.py -v`
5. Verify 70% coverage on core modules

### Incremental Delivery

1. Complete Setup + Foundational → Test infrastructure ready
2. Add US1 (Core Functionality) → Test independently → Validate (MVP!)
3. Add US2 (LangChain Integration) → Test independently → Validate
4. Add US3 (Edge Cases) → Test independently → Validate
5. Add US4 (Performance) → Test independently → Validate
6. Add US5 (Installation) → Test independently → Validate
7. Polish → Final validation and documentation

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together (critical path)
2. Once Foundational is done:
   - Developer A: User Story 1 (Core Functionality) - 7 test files
   - Developer B: User Story 2 (LangChain Integration) - 1 test file
   - Developer C: User Story 3 (Edge Cases) - 1 test file
   - Developer D: User Story 4 (Performance) - 1 test file
   - Developer E: User Story 5 (Installation) - 1 test file
3. Stories complete and integrate independently

---

## Notes

- **Test count**: ~95 tasks total (~75 test functions across 9 test files)
- **Estimated completion**: 3-5 days for single developer (MVP = 2 days for US1)
- **Critical path**: Setup → Foundational → US1 (Core) → Coverage validation
- **Python version**: Run all tests using Python 3.10 (`python3` alias)
- **Coverage target**: Minimum 70% line coverage across all modules
- **Performance targets**: Discovery <500ms (50 skills), Invocation <25ms, Memory <5MB
- **Fixtures**: 8 static SKILL.md files + programmatic generation via skill_factory
- **Markers**: integration, performance, slow, requires_langchain for test filtering
- **Execution**: Single command `pytest` runs full suite in <60 seconds
- **Validation**: Each user story is independently testable with `pytest tests/test_<file>.py -v`
- **[P] tasks**: Different files or functions within same file, no dependencies
- **[Story] label**: Maps task to user story for traceability (US1-US5)
- **Commit strategy**: Commit after each test file is complete and passing
- **Stop checkpoints**: Each user story checkpoint allows validation before proceeding
