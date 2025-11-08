# Tasks: skillkit v0.1 MVP - Core Functionality & LangChain Integration

**Input**: Design documents from `/specs/001-mvp-langchain-core/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/public-api.md

**Tests**: Included per Testing Strategy (Decision 7) - 70% coverage target with pytest

**Organization**: Tasks grouped by user story to enable independent implementation and testing

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US6)
- Include exact file paths in descriptions

## Path Conventions

Single Python library structure (per plan.md):
- `src/skillkit/` - Source code
- `tests/` - Test suite
- `examples/` - Example scripts
- `.docs/` - Documentation

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project structure per plan.md (src/skillkit/{core,integrations}/, tests/, examples/)
- [ ] T002 [P] Initialize pyproject.toml with Python 3.9+ dependencies (PyYAML 6.0+)
- [ ] T003 [P] Configure ruff for linting and formatting in pyproject.toml
- [ ] T004 [P] Configure mypy for strict type checking in pyproject.toml
- [ ] T005 [P] Add py.typed marker file in src/skillkit/py.typed for PEP 561
- [ ] T006 [P] Create .gitignore for Python project
- [ ] T007 [P] Create LICENSE file (MIT license)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T008 [P] Implement exception hierarchy in src/skillkit/core/exceptions.py (11 exception types per research.md)
- [ ] T009 [P] Implement SkillMetadata dataclass in src/skillkit/core/models.py (frozen=True, slots=True)
- [ ] T010 [P] Implement Skill dataclass in src/skillkit/core/models.py (with @cached_property, Python 3.10+ slots)
- [ ] T011 [P] Configure NullHandler logging in src/skillkit/__init__.py (Python library standard)
- [ ] T012 [P] Create test fixtures directory structure tests/fixtures/skills/
- [ ] T013 [P] Create conftest.py with fixtures_dir and skills_dir fixtures in tests/conftest.py
- [ ] T014 [P] Create valid skill fixture in tests/fixtures/skills/valid-skill/SKILL.md
- [ ] T015 [P] Create missing-name skill fixture in tests/fixtures/skills/missing-name-skill/SKILL.md
- [ ] T016 [P] Create invalid-yaml skill fixture in tests/fixtures/skills/invalid-yaml-skill/SKILL.md
- [ ] T017 [P] Create arguments-test skill fixture in tests/fixtures/skills/arguments-test-skill/SKILL.md

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Basic Skill Discovery and Usage (Priority: P1) 🎯 MVP

**Goal**: Enable discovery of skills from `.claude/skills/` directory and access their metadata

**Independent Test**: Place SKILL.md file in `.claude/skills/skill-name/`, run discovery, verify skill found with correct metadata

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T018 [P] [US1] Test discovery of 3 skills in tests/test_discovery.py (FR-001, FR-002)
- [ ] T019 [P] [US1] Test discovery with empty directory in tests/test_discovery.py (FR-005)
- [ ] T020 [P] [US1] Test discovery with missing directory in tests/test_discovery.py (FR-004)
- [ ] T021 [P] [US1] Test skill metadata structure in tests/test_models.py
- [ ] T022 [P] [US1] Test immutability of SkillMetadata in tests/test_models.py

### Implementation for User Story 1

- [ ] T023 [US1] Implement SkillDiscovery class in src/skillkit/core/discovery.py (scan filesystem)
- [ ] T024 [US1] Implement discovery.scan_directory() method with flat structure support (FR-003)
- [ ] T025 [US1] Implement discovery.find_skill_files() with case-insensitive SKILL.md matching (FR-002)
- [ ] T026 [US1] Add graceful error handling for missing/empty directories in discovery (FR-004, FR-005)
- [ ] T027 [US1] Add logging (INFO) for discovery results in SkillDiscovery

**Checkpoint**: At this point, User Story 1 should be fully functional - skills can be discovered and metadata accessed

---

## Phase 4: User Story 2 - Skill Metadata Access Without Loading Full Content (Priority: P1)

**Goal**: Progressive disclosure pattern - load only metadata initially, defer content loading until invocation

**Independent Test**: Load 10 skills and verify only metadata in memory, not full markdown content

### Tests for User Story 2

- [ ] T028 [P] [US2] Test list_skills() returns metadata only in tests/test_manager.py (FR-017)
- [ ] T029 [P] [US2] Test get_skill() returns metadata without content in tests/test_manager.py (FR-018)
- [ ] T030 [P] [US2] Test get_skill() raises KeyError for missing skill in tests/test_manager.py (FR-019)
- [ ] T031 [P] [US2] Test discovery completes in <500ms for 10 skills in tests/test_manager.py (FR-020)

### Implementation for User Story 2

- [ ] T032 [US2] Implement SkillManager.__init__() in src/skillkit/core/manager.py
- [ ] T033 [US2] Implement SkillManager.discover() with graceful degradation in src/skillkit/core/manager.py
- [ ] T034 [US2] Implement SkillManager.list_skills() returning List[SkillMetadata] in src/skillkit/core/manager.py
- [ ] T035 [US2] Implement SkillManager.get_skill() with SkillNotFoundError in src/skillkit/core/manager.py
- [ ] T036 [US2] Add duplicate skill handling (first wins, log WARNING) in SkillManager.discover()
- [ ] T037 [US2] Add logging for discovery completion and empty directory in SkillManager

**Checkpoint**: Metadata management working - can browse skills efficiently without loading full content

---

## Phase 5: User Story 5 - SKILL.md Parsing and Validation (Priority: P2)

**Goal**: Parse YAML frontmatter, extract required fields, validate skill format

**Independent Test**: Provide valid and invalid SKILL.md files, verify parsing succeeds/fails with clear error messages

**Note**: Moved before User Story 3 because parsing is a prerequisite for invocation

### Tests for User Story 5

- [ ] T038 [P] [US5] Test parse valid SKILL.md in tests/test_parser.py (FR-007 through FR-011)
- [ ] T039 [P] [US5] Test parse minimal skill (only required fields) in tests/test_parser.py
- [ ] T040 [P] [US5] Test Windows line endings (CRLF) in tests/test_parser.py
- [ ] T041 [P] [US5] Test UTF-8 BOM auto-strip in tests/test_parser.py
- [ ] T042 [P] [US5] Test empty name raises MissingRequiredFieldError in tests/test_parser.py (FR-012)
- [ ] T043 [P] [US5] Test whitespace-only description raises error in tests/test_parser.py (FR-013)
- [ ] T044 [P] [US5] Test missing required fields with clear errors in tests/test_parser.py (FR-012, FR-013)
- [ ] T045 [P] [US5] Test invalid YAML syntax with line/column details in tests/test_parser.py (FR-014)
- [ ] T046 [P] [US5] Test malformed allowed-tools (non-list) in tests/test_parser.py
- [ ] T047 [P] [US5] Test malformed allowed-tools (mixed types) in tests/test_parser.py
- [ ] T048 [P] [US5] Test typo detection (allowed_tools → allowed-tools) in tests/test_parser.py
- [ ] T049 [P] [US5] Test unknown field forward compatibility in tests/test_parser.py
- [ ] T050 [P] [US5] Test multiple delimiters in content in tests/test_parser.py
- [ ] T051 [P] [US5] Test missing frontmatter delimiters in tests/test_parser.py
- [ ] T052 [P] [US5] Test non-dict frontmatter in tests/test_parser.py

### Implementation for User Story 5

- [ ] T053 [US5] Implement SkillParser class in src/skillkit/core/parser.py
- [ ] T054 [US5] Add cross-platform regex pattern ([\r\n]+) for frontmatter extraction in SkillParser
- [ ] T055 [US5] Implement yaml.safe_load() with detailed error extraction in SkillParser
- [ ] T056 [US5] Implement required field validation (name, description non-empty) in SkillParser
- [ ] T057 [US5] Implement optional field handling (allowed-tools) with graceful degradation in SkillParser
- [ ] T058 [US5] Implement typo detection for field names (TYPO_MAP) in SkillParser
- [ ] T059 [US5] Add UTF-8-sig encoding for BOM handling in SkillParser
- [ ] T060 [US5] Add comprehensive error messages with file paths and field names in SkillParser
- [ ] T061 [US5] Integrate SkillParser into SkillManager.discover() method

**Checkpoint**: SKILL.md parsing working with comprehensive validation and helpful error messages

---

## Phase 6: User Story 3 - Skill Invocation with Argument Substitution (Priority: P1)

**Goal**: Invoke skills with arguments, process content with base directory injection and $ARGUMENTS substitution

**Independent Test**: Invoke skill with arguments, verify content has base directory and arguments substituted correctly

### Tests for User Story 3

- [ ] T062 [P] [US3] Test single $ARGUMENTS placeholder replaced in tests/test_processors.py
- [ ] T063 [P] [US3] Test multiple $ARGUMENTS placeholders replaced in tests/test_processors.py
- [ ] T064 [P] [US3] Test empty arguments replaces with empty string in tests/test_processors.py
- [ ] T065 [P] [US3] Test no placeholder appends arguments in tests/test_processors.py
- [ ] T066 [P] [US3] Test no placeholder and no arguments (unchanged) in tests/test_processors.py
- [ ] T067 [P] [US3] Test $$ARGUMENTS escaping in tests/test_processors.py
- [ ] T068 [P] [US3] Test mixed escaped and normal $ARGUMENTS in tests/test_processors.py
- [ ] T069 [P] [US3] Test Unicode arguments in tests/test_processors.py
- [ ] T070 [P] [US3] Test multiline arguments in tests/test_processors.py
- [ ] T071 [P] [US3] Test size limit exceeded (1MB) in tests/test_processors.py
- [ ] T072 [P] [US3] Test suspicious patterns logged in tests/test_processors.py
- [ ] T073 [P] [US3] Test typo detection (lowercase, titlecase) in tests/test_processors.py
- [ ] T074 [P] [US3] Test base directory injection in tests/test_processors.py (FR-022)
- [ ] T075 [P] [US3] Test Skill.invoke() end-to-end in tests/test_models.py (FR-021 through FR-028)
- [ ] T076 [P] [US3] Test SkillManager.invoke_skill() in tests/test_manager.py

### Implementation for User Story 3

- [ ] T077 [P] [US3] Implement ContentProcessor abstract base class in src/skillkit/core/processors.py
- [ ] T078 [P] [US3] Implement BaseDirectoryProcessor in src/skillkit/core/processors.py (FR-022)
- [ ] T079 [US3] Implement ArgumentSubstitutionProcessor with string.Template in src/skillkit/core/processors.py
- [ ] T080 [US3] Add input validation (1MB limit) to ArgumentSubstitutionProcessor
- [ ] T081 [US3] Add suspicious pattern detection (9 patterns) to ArgumentSubstitutionProcessor
- [ ] T082 [US3] Add typo detection (5 common patterns) to ArgumentSubstitutionProcessor
- [ ] T083 [US3] Implement _get_identifiers() with Python 3.11+ fallback in ArgumentSubstitutionProcessor
- [ ] T084 [P] [US3] Implement CompositeProcessor for chaining in src/skillkit/core/processors.py
- [ ] T085 [US3] Implement Skill.invoke() method using CompositeProcessor
- [ ] T086 [US3] Implement Skill.content @cached_property with error handling (ContentLoadError)
- [ ] T087 [US3] Implement SkillManager.load_skill() method
- [ ] T088 [US3] Implement SkillManager.invoke_skill() convenience method

**Checkpoint**: Skill invocation working end-to-end with secure argument substitution and base directory context

---

## Phase 7: User Story 4 - LangChain Agent Integration (Priority: P1)

**Goal**: Convert discovered skills into LangChain StructuredTool objects for agent usage

**Independent Test**: Create LangChain tools from skills, pass to agent, verify agent can invoke skills successfully

### Tests for User Story 4

- [ ] T089 [P] [US4] Test create_langchain_tools() creates correct number of tools in tests/test_langchain.py (FR-030)
- [ ] T090 [P] [US4] Test StructuredTool invocation with arguments in tests/test_langchain.py (FR-032)
- [ ] T091 [P] [US4] Test tool returns processed content in tests/test_langchain.py (FR-035)
- [ ] T092 [P] [US4] Test tool invocation overhead <10ms in tests/test_langchain.py (FR-036)
- [ ] T093 [P] [US4] Test end-to-end LangChain agent integration in tests/test_langchain.py (FR-037)
- [ ] T094 [P] [US4] Test closure capture pattern (each tool invokes correct skill) in tests/test_langchain.py

### Implementation for User Story 4

- [ ] T095 [US4] Create src/skillkit/integrations/__init__.py with exports
- [ ] T096 [US4] Implement import guards for langchain dependencies in src/skillkit/integrations/langchain.py
- [ ] T097 [US4] Implement SkillInput Pydantic model in src/skillkit/integrations/langchain.py
- [ ] T098 [US4] Implement create_langchain_tools() with closure capture in src/skillkit/integrations/langchain.py
- [ ] T099 [US4] Add error handling (3-layer approach) to tool functions in create_langchain_tools()
- [ ] T100 [US4] Add transparency docstring about async wrapping in create_langchain_tools()
- [ ] T101 [US4] Update src/skillkit/__init__.py to export core public API

**Checkpoint**: LangChain integration complete - agents can discover and use skills as tools

---

## Phase 8: User Story 6 - Example Skills for Testing (Priority: P2)

**Goal**: Provide working example skills that demonstrate common use cases

**Independent Test**: Run example agent code with provided skills, verify successful task completion

### Implementation for User Story 6

- [ ] T102 [P] [US6] Create code-reviewer skill in examples/skills/code-reviewer/SKILL.md
- [ ] T103 [P] [US6] Create markdown-formatter skill in examples/skills/markdown-formatter/SKILL.md
- [ ] T104 [P] [US6] Create git-helper skill in examples/skills/git-helper/SKILL.md
- [ ] T105 [P] [US6] Create basic_usage.py example in examples/basic_usage.py
- [ ] T106 [P] [US6] Create langchain_agent.py example in examples/langchain_agent.py
- [ ] T107 [US6] Test examples run without modification (verify FR-049)

**Checkpoint**: Example skills and code available for new users to learn from

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T108 [P] Create README.md with installation, quick start, and examples (FR-046, FR-050)
- [ ] T109 [P] Add SKILL.md format documentation to README.md
- [ ] T110 [P] Verify all public APIs exported in src/skillkit/__init__.py
- [ ] T111 [P] Verify all exceptions exported in src/skillkit/core/exceptions.py
- [ ] T112 Run pytest --cov=skillkit --cov-report=html to verify 70%+ coverage (FR-043)
- [ ] T113 Run mypy src/skillkit --strict for type checking
- [ ] T114 Run ruff check src/skillkit for linting
- [ ] T115 Validate quickstart.md examples work without modification (FR-049)
- [ ] T116 Create pyproject.toml [project.optional-dependencies] for langchain (FR-045)
- [ ] T117 Add python-frontmatter to dev dependencies for future consideration
- [ ] T118 Final code cleanup and docstring verification
- [ ] T119 Build package with python -m build
- [ ] T120 Test installation in clean virtualenv (pip install dist/*.whl)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories**:
  - US1 (Phase 3): Depends on Foundational - can start immediately after Phase 2
  - US2 (Phase 4): Depends on US1 completion (needs SkillDiscovery)
  - US5 (Phase 5): Can start in parallel with US2 (independent)
  - US3 (Phase 6): Depends on US5 completion (needs SkillParser)
  - US4 (Phase 7): Depends on US3 completion (needs SkillManager.invoke_skill)
  - US6 (Phase 8): Depends on US4 completion (needs full functionality)
- **Polish (Phase 9)**: Depends on all user stories being complete

### Critical Path (MVP)

```
Setup → Foundational → US1 → US2 → US5 → US3 → US4 → Polish
```

### User Story Dependencies

- **US1 (Discovery)**: Independent after Foundational
- **US2 (Metadata)**: Requires US1 (SkillDiscovery)
- **US5 (Parsing)**: Independent after Foundational (can parallel with US2)
- **US3 (Invocation)**: Requires US5 (SkillParser)
- **US4 (LangChain)**: Requires US3 (full invocation pipeline)
- **US6 (Examples)**: Requires US4 (complete functionality)

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models before processors
- Processors before managers
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 2 (Foundational)**:
- All tasks marked [P] can run in parallel (T008-T017)

**Phase 3 (US1)**:
- All test tasks can run in parallel (T018-T022)

**Phase 4 (US2)**:
- All test tasks can run in parallel (T028-T031)

**Phase 5 (US5)**:
- All test tasks can run in parallel (T038-T052)

**Phase 6 (US3)**:
- Test tasks T062-T076 can run in parallel
- Processor implementations T077, T078, T084 can run in parallel (different classes)

**Phase 7 (US4)**:
- All test tasks can run in parallel (T089-T094)

**Phase 8 (US6)**:
- All skill creation tasks can run in parallel (T102-T104)
- Both example scripts can run in parallel (T105-T106)

**Phase 9 (Polish)**:
- Tasks T108-T111 can run in parallel (different files)

**User Story Parallelization** (if team capacity allows):
- US2 and US5 can run in parallel after US1 completes
- All test-writing phases can be done ahead of implementation

---

## Parallel Example: User Story 3 (Invocation)

```bash
# Launch all test tasks together:
Task T062: "Test single $ARGUMENTS placeholder replaced in tests/test_processors.py"
Task T063: "Test multiple $ARGUMENTS placeholders replaced in tests/test_processors.py"
Task T064: "Test empty arguments replaces with empty string in tests/test_processors.py"
...
Task T076: "Test SkillManager.invoke_skill() in tests/test_manager.py"

# Launch processor base classes in parallel:
Task T077: "Implement ContentProcessor abstract base class"
Task T078: "Implement BaseDirectoryProcessor"
Task T084: "Implement CompositeProcessor for chaining"
```

---

## Implementation Strategy

### MVP First (Phases 1-7 Only)

1. Complete Phase 1: Setup (7 tasks)
2. Complete Phase 2: Foundational (10 tasks) **CRITICAL BLOCKER**
3. Complete Phase 3: User Story 1 (10 tasks) - Discovery working
4. Complete Phase 4: User Story 2 (9 tasks) - Metadata management working
5. Complete Phase 5: User Story 5 (24 tasks) - Parsing working
6. Complete Phase 6: User Story 3 (27 tasks) - Invocation working
7. Complete Phase 7: User Story 4 (13 tasks) - LangChain integration working
8. **STOP and VALIDATE**: Run all tests, verify 70% coverage
9. Optional Phase 8: Examples (6 tasks)
10. Complete Phase 9: Polish (13 tasks)
11. Deploy to PyPI

**Total MVP Tasks**: 100 tasks (excluding examples)
**Total with Examples**: 106 tasks
**Estimated Timeline**: 4 weeks per plan.md

### Incremental Delivery Checkpoints

1. **After Phase 3**: Can discover skills and access metadata (basic functionality)
2. **After Phase 4**: Can browse skills efficiently without loading content (progressive disclosure working)
3. **After Phase 5**: Can parse and validate SKILL.md files (quality assurance working)
4. **After Phase 6**: Can invoke skills with arguments (core functionality complete)
5. **After Phase 7**: Can use skills with LangChain agents (integration complete - **MVP READY**)
6. **After Phase 8**: Have working examples for users (adoption ready)
7. **After Phase 9**: Ready for PyPI publication (production ready)

### Parallel Team Strategy

With multiple developers after Foundational phase completes:

- **Developer A**: Focus on US1 + US2 (Discovery & Metadata)
- **Developer B**: Focus on US5 (Parsing - can start in parallel with US2)
- **Developer C**: Focus on US3 (Invocation - starts after US5 complete)
- **Developer D**: Focus on US4 (LangChain - starts after US3 complete)
- **All**: Reconvene for examples and polish

---

## Notes

- [P] tasks = different files, no dependencies within phase
- [Story] label maps task to specific user story for traceability (US1-US6)
- Each user story should be independently completable and testable
- **Verify tests fail before implementing** (TDD approach per research.md)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Python 3.10+ recommended for full slots support (Python 3.9 supported with minor memory overhead)
- Use `string.Template` for $ARGUMENTS substitution (security requirement)
- Use `yaml.safe_load()` for parsing (security requirement)
- Configure NullHandler for logging (Python library standard)
- Aim for 70% test coverage (measured with pytest-cov)
- Follow strict mypy type checking
- Use ruff for linting and formatting
- Tests use tmp_path fixture for isolation
- Tests use @pytest.mark.parametrize for edge cases (15+ scenarios in US3)
- All exceptions chain with `raise ... from e` for debugging

---

**Document Version**: 1.0
**Generated**: November 4, 2025
**Feature**: skillkit v0.1 MVP - Core Functionality & LangChain Integration
**Branch**: `001-mvp-langchain-core`
**Total Tasks**: 120 (7 setup + 10 foundational + 103 implementation/tests/polish)
**Target Coverage**: 70%+
**Estimated Timeline**: 4 weeks
