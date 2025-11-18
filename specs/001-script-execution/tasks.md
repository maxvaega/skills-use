---

description: "Task list for Script Execution Support feature"
---

# Tasks: Script Execution Support

**Input**: Design documents from `/specs/001-script-execution/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/, quickstart.md, research.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**Tests**: Not explicitly requested in spec.md - test tasks are marked as optional enhancements

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Single project structure: `src/skillkit/`, `tests/` at repository root
- All paths relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for v0.3.0 script execution feature

- [ ] T001 Create feature branch 001-script-execution from main
- [ ] T002 [P] Create src/skillkit/core/scripts.py module with INTERPRETER_MAP constant
- [ ] T003 [P] Create tests/test_script_detector.py test file structure
- [ ] T004 [P] Create tests/test_script_executor.py test file structure
- [ ] T005 [P] Create tests/fixtures/skills/script-skill/ test fixture directory with SKILL.md
- [ ] T006 [P] Create examples/script_execution.py example file skeleton
- [ ] T007 [P] Create examples/skills/pdf-extractor/ example skill directory with SKILL.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T008 Add script-specific exceptions to src/skillkit/core/exceptions.py: InterpreterNotFoundError, ScriptNotFoundError, ScriptPermissionError, ArgumentSerializationError, ArgumentSizeError
- [ ] T009 [P] Implement ScriptMetadata dataclass in src/skillkit/core/scripts.py with fields: name, path, script_type, description, and get_fully_qualified_name method
- [ ] T010 [P] Implement ScriptExecutionResult dataclass in src/skillkit/core/scripts.py with fields: stdout, stderr, exit_code, execution_time_ms, script_path, signal, signal_number, stdout_truncated, stderr_truncated, and properties: success, timeout, signaled
- [ ] T011 [P] Implement INTERPRETER_MAP constant dict in src/skillkit/core/scripts.py mapping extensions (.py, .sh, .js, .rb, .pl, .bat, .cmd, .ps1) to interpreters
- [ ] T012 [P] Add type aliases to src/skillkit/core/scripts.py: ScriptArguments, ScriptEnvironment, ScriptList
- [ ] T013 Extend Skill dataclass in src/skillkit/core/models.py with _scripts field (Optional[List[ScriptMetadata]]) and scripts property (lazy-loaded)
- [ ] T014 Update src/skillkit/__init__.py to export new script classes: ScriptMetadata, ScriptExecutionResult, and script exceptions

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Execute Skill Scripts for Deterministic Processing (Priority: P1) 🎯 MVP

**Goal**: Enable skills to execute scripts with arguments passed via JSON stdin, capture stdout/stderr, return results to agent

**Independent Test**: Create a simple skill with a Python script, invoke it with test data, verify output is captured and returned correctly

### Implementation for User Story 1

- [ ] T015 [P] [US1] Implement ScriptDescriptionExtractor class in src/skillkit/core/scripts.py with extract() method supporting Python docstrings, shell comments, JSDoc, Ruby/Perl comment blocks
- [ ] T016 [P] [US1] Implement ScriptDetector class in src/skillkit/core/scripts.py with __init__(max_depth, max_lines_for_description) and detect_scripts() method
- [ ] T017 [US1] Implement _scan_directories() method in ScriptDetector to scan scripts/ directory and skill root
- [ ] T018 [US1] Implement _is_executable_script() method in ScriptDetector to filter files by extension and exclude hidden/cache files
- [ ] T019 [US1] Implement _extract_metadata() method in ScriptDetector to create ScriptMetadata from detected files
- [ ] T020 [US1] Implement _get_script_type() helper function in src/skillkit/core/scripts.py to map extensions to script types
- [ ] T021 [P] [US1] Implement ScriptExecutor class __init__ in src/skillkit/core/scripts.py with timeout, max_output_size, use_cache parameters
- [ ] T022 [US1] Implement _validate_script_path() method in ScriptExecutor using os.path.realpath and os.path.commonpath for path traversal prevention
- [ ] T023 [US1] Implement _check_permissions() method in ScriptExecutor to reject setuid/setgid scripts
- [ ] T024 [US1] Implement _resolve_interpreter() method in ScriptExecutor with extension mapping and shebang fallback
- [ ] T025 [US1] Implement _serialize_arguments() method in ScriptExecutor with JSON serialization and size limit validation
- [ ] T026 [US1] Implement _build_environment() method in ScriptExecutor to inject SKILL_NAME, SKILL_BASE_DIR, SKILL_VERSION, SKILLKIT_VERSION
- [ ] T027 [US1] Implement _execute_subprocess() method in ScriptExecutor to run subprocess.run() with shell=False, capture output, handle signals
- [ ] T028 [US1] Implement _handle_output_truncation() method in ScriptExecutor to truncate stdout/stderr at 10MB limit
- [ ] T029 [US1] Implement _detect_signal() method in ScriptExecutor to parse negative exit codes as signals
- [ ] T030 [US1] Implement execute() orchestration method in ScriptExecutor coordinating all validation, execution, and error handling steps
- [ ] T031 [US1] Add audit logging to ScriptExecutor.execute() for INFO (success), ERROR (failure), WARNING (timeout/truncation) levels
- [ ] T032 [US1] Extend SkillManager in src/skillkit/core/manager.py with default_script_timeout parameter in __init__
- [ ] T033 [US1] Implement execute_skill_script() method in SkillManager to look up skill, find script, call ScriptExecutor, handle errors

**Checkpoint**: At this point, User Story 1 should be fully functional - scripts can be detected, executed, and results returned

---

## Phase 4: User Story 2 - Safe Script Execution with Security Boundaries (Priority: P1)

**Goal**: Implement security controls to prevent malicious scripts from accessing files outside skill directory or escalating privileges

**Independent Test**: Attempt path traversal attacks (../../etc/passwd), verify they're blocked with PathSecurityError, confirm all executions are logged

### Implementation for User Story 2

- [ ] T034 [US2] Enhance _validate_script_path() in ScriptExecutor to validate symlinks don't point outside skill directory using os.path.realpath
- [ ] T035 [US2] Enhance _check_permissions() in ScriptExecutor to check both setuid (stat.S_ISUID) and setgid (stat.S_ISGID) bits
- [ ] T036 [US2] Add security violation logging to _validate_script_path() with ERROR level when path traversal detected
- [ ] T037 [US2] Add security violation logging to _check_permissions() with ERROR level when dangerous permissions detected
- [ ] T038 [US2] Implement audit log entry in execute() with timestamp, skill name, script path, arguments (truncated to 256 chars), exit code, execution time

**Checkpoint**: Security boundaries enforced - path traversal blocked, dangerous permissions rejected, all executions audited

---

## Phase 5: User Story 3 - Timeout Management for Long-Running Scripts (Priority: P1)

**Goal**: Enforce execution timeouts to prevent infinite loops or hung processes from blocking the agent

**Independent Test**: Create script with infinite loop, set 5-second timeout, verify process killed after 5 seconds with timeout error

### Implementation for User Story 3

- [ ] T039 [US3] Implement timeout handling in _execute_subprocess() to catch subprocess.TimeoutExpired exception
- [ ] T040 [US3] Set exit_code to 124 and stderr to "Timeout" when subprocess.TimeoutExpired is caught
- [ ] T041 [US3] Add WARNING level log entry when timeout occurs with timeout duration and script details
- [ ] T042 [US3] Implement execution time measurement in execute() using time.perf_counter() before/after subprocess call
- [ ] T043 [US3] Add timeout property to ScriptExecutionResult to check if exit_code==124 and "Timeout" in stderr
- [ ] T044 [US3] Support custom timeout in SkillManager.execute_skill_script() that overrides default_script_timeout

**Checkpoint**: Timeout enforcement working - long-running scripts killed after timeout, execution time measured and logged

---

## Phase 6: User Story 4 - Tool Restriction Enforcement for Scripts (Priority: P2)

**Goal**: Enforce tool restrictions by checking if "Bash" is in skill's allowed-tools list before executing scripts

**Independent Test**: Create two skills - one with allowed-tools: Bash (allowed) and one with allowed-tools: Read, Write (blocked) - verify script execution succeeds for first and raises ToolRestrictionError for second

### Implementation for User Story 4

- [ ] T045 [US4] Implement _check_tool_restrictions() method in ScriptExecutor to validate "Bash" is in skill_metadata.allowed_tools
- [ ] T046 [US4] Raise ToolRestrictionError in _check_tool_restrictions() if Bash not allowed (with skill name and allowed tools list in error message)
- [ ] T047 [US4] Call _check_tool_restrictions() in execute() before script execution (after path/permission validation)
- [ ] T048 [US4] Handle None/empty allowed_tools (no restrictions) by allowing all script executions
- [ ] T049 [US4] Add test fixture tests/fixtures/skills/restricted-skill/ with SKILL.md declaring allowed-tools without Bash

**Checkpoint**: Tool restrictions enforced - scripts only execute if Bash in allowed-tools or no restrictions defined

---

## Phase 7: User Story 5 - Environment Context for Scripts (Priority: P2)

**Goal**: Inject skill metadata (name, base directory, version) into script environment for context-aware logging and file resolution

**Independent Test**: Create script that prints environment variables (SKILL_NAME, SKILL_BASE_DIR, SKILL_VERSION, SKILLKIT_VERSION), verify all values correctly injected

### Implementation for User Story 5

- [ ] T050 [US5] Ensure _build_environment() in ScriptExecutor injects SKILL_NAME from skill_metadata.name
- [ ] T051 [US5] Ensure _build_environment() in ScriptExecutor injects SKILL_BASE_DIR as absolute path string
- [ ] T052 [US5] Ensure _build_environment() in ScriptExecutor injects SKILL_VERSION from skill_metadata.version
- [ ] T053 [US5] Ensure _build_environment() in ScriptExecutor injects SKILLKIT_VERSION from skillkit.__version__
- [ ] T054 [US5] Merge injected environment with os.environ (preserve system PATH, HOME, etc.)
- [ ] T055 [US5] Update examples/script_execution.py to demonstrate environment variable usage in scripts

**Checkpoint**: Environment context available - all scripts receive skill metadata via environment variables

---

## Phase 8: User Story 6 - Automatic Script Detection (Priority: P3)

**Goal**: Automatically discover scripts in skill directories without manual registration

**Independent Test**: Create skill with multiple scripts in different locations (scripts/, scripts/utils/, root), trigger detection via Skill.scripts property, verify all executable scripts found with correct metadata

### Implementation for User Story 6

- [ ] T056 [US6] Implement recursive scanning in _scan_directories() up to max_depth levels (default 5)
- [ ] T057 [US6] Exclude __pycache__, node_modules, .venv, venv directories in _is_executable_script()
- [ ] T058 [US6] Skip hidden files (starting with '.') in _is_executable_script()
- [ ] T059 [US6] Skip symlinks in _is_executable_script() to avoid confusion and duplicate detection
- [ ] T060 [US6] Ensure detection completes in <10ms for 50 scripts by benchmarking detect_scripts() performance
- [ ] T061 [US6] Add INFO level logging in detect_scripts() with script count summary: "Detected {count} scripts in skill '{skill_name}'"
- [ ] T062 [US6] Handle graceful degradation if individual script parsing fails (log warning, skip script, continue detection)

**Checkpoint**: Automatic detection working - all executable scripts found recursively, excluding hidden/cache files

---

## Phase 9: LangChain Integration (Cross-Story)

**Goal**: Expose detected scripts as separate StructuredTools in LangChain integration with proper naming and error handling

**Dependencies**: Requires US1 (script execution), US6 (detection)

- [ ] T063 [P] Define ScriptToolResult TypedDict in src/skillkit/integrations/langchain.py with type, tool_use_id, content, is_error fields
- [ ] T064 Implement create_script_tools() function in src/skillkit/integrations/langchain.py to iterate skill.scripts and create StructuredTool per script
- [ ] T065 Implement script tool wrapper function that calls SkillManager.execute_skill_script(), returns stdout on success, raises ToolException on failure
- [ ] T066 Set tool name to "{skill_name}.{script_name}" format (e.g., "pdf-extractor.extract")
- [ ] T067 Set tool description from script.description (extracted from first comment block) or empty string if no description
- [ ] T068 Define free-form JSON input schema for script tools (single field accepting any JSON structure)
- [ ] T069 Update to_langchain_tools() in LangChainSkillAdapter to call create_script_tools() and append to tools list
- [ ] T070 Preserve prompt-based tool alongside script tools if skill has prompt (skills can expose 1+N tools)
- [ ] T071 Update examples/langchain_agent.py to demonstrate script tool usage with LangChain agents

**Checkpoint**: LangChain integration complete - each script exposed as separate tool, both sync and async supported

---

## Phase 10: Testing & Validation (Optional Enhancement)

**Purpose**: Comprehensive test coverage for all user stories (tests not explicitly requested in spec)

**Note**: These tasks are optional enhancements to improve code quality and reliability

- [ ] T072 [P] Write unit tests in tests/test_script_detector.py for detecting Python, Shell, JavaScript, Ruby, Perl scripts
- [ ] T073 [P] Write unit tests in tests/test_script_detector.py for skipping non-script files (.json, .md), hidden files, __pycache__
- [ ] T074 [P] Write unit tests in tests/test_script_detector.py for nested directories up to max_depth
- [ ] T075 [P] Write unit tests in tests/test_script_detector.py for description extraction from docstrings, comments, JSDoc
- [ ] T076 [P] Write unit tests in tests/test_script_detector.py for empty description when no comments exist
- [ ] T077 [P] Write unit tests in tests/test_script_executor.py for successful execution (exit code 0)
- [ ] T078 [P] Write unit tests in tests/test_script_executor.py for failed execution (exit code 1)
- [ ] T079 [P] Write unit tests in tests/test_script_executor.py for timeout handling (exit code 124)
- [ ] T080 [P] Write unit tests in tests/test_script_executor.py for signal termination (SIGSEGV, SIGKILL)
- [ ] T081 [P] Write unit tests in tests/test_script_executor.py for path traversal prevention (../../etc/passwd)
- [ ] T082 [P] Write unit tests in tests/test_script_executor.py for symlink validation
- [ ] T083 [P] Write unit tests in tests/test_script_executor.py for permission checks (setuid/setgid)
- [ ] T084 [P] Write unit tests in tests/test_script_executor.py for output truncation at 10MB
- [ ] T085 [P] Write unit tests in tests/test_script_executor.py for environment variable injection
- [ ] T086 [P] Write integration tests in tests/test_manager.py for SkillManager.execute_skill_script()
- [ ] T087 [P] Write integration tests in tests/test_langchain.py for script tool creation and invocation
- [ ] T088 [P] Create test fixtures in tests/fixtures/skills/script-skill/scripts/ with Python, Shell, JavaScript test scripts
- [ ] T089 [P] Create test script that triggers timeout (infinite loop) in tests/fixtures/skills/script-skill/scripts/
- [ ] T090 [P] Create test script that reads JSON from stdin and writes to stdout in tests/fixtures/skills/script-skill/scripts/
- [ ] T091 Run pytest with coverage to verify 70%+ test coverage for script modules

**Checkpoint**: Test suite complete - 70%+ coverage, all user stories validated with unit and integration tests

---

## Phase 11: Documentation & Examples

**Purpose**: User-facing documentation and real-world examples

- [ ] T092 [P] Implement working Python script in examples/skills/pdf-extractor/scripts/extract.py that demonstrates JSON stdin reading
- [ ] T093 [P] Implement working Shell script in examples/skills/pdf-extractor/scripts/convert.sh for format conversion example
- [ ] T094 [P] Write comprehensive example in examples/script_execution.py demonstrating: basic execution, error handling, timeout, environment variables
- [ ] T095 [P] Update README.md with Script Execution (v0.3+) section showing basic usage and LangChain integration
- [ ] T096 [P] Update CLAUDE.md with v0.3 status (In Progress → Released) and script execution feature summary
- [ ] T097 [P] Update .docs/TECH_SPECS.md (if exists) with script execution architecture and design decisions
- [ ] T098 [P] Add docstrings to all public methods in ScriptDetector, ScriptExecutor, and updated Skill/SkillManager classes
- [ ] T099 Update quickstart.md validation: verify all examples run successfully, check performance targets met

**Checkpoint**: Documentation complete - users can understand and use script execution feature via examples and docs

---

## Phase 12: Polish & Release Preparation

**Purpose**: Final refinements before v0.3.0 release

- [ ] T100 [P] Run ruff check src/skillkit to verify linting passes
- [ ] T101 [P] Run ruff format src/skillkit to ensure consistent formatting
- [ ] T102 [P] Run mypy src/skillkit --strict to verify type checking passes
- [ ] T103 Review all error messages for clarity and consistency
- [ ] T104 Verify backward compatibility: all v0.1/v0.2 APIs work unchanged
- [ ] T105 Run performance benchmarks: script detection <10ms for 50 scripts, execution overhead <50ms
- [ ] T106 Security review: verify shell=False everywhere, path validation comprehensive, no shell interpolation
- [ ] T107 Update version to 0.3.0 in pyproject.toml and src/skillkit/__init__.py
- [ ] T108 Update CHANGELOG in README.md and CLAUDE.md with v0.3.0 features
- [ ] T109 Create PR from 001-script-execution branch to main with comprehensive description

**Checkpoint**: v0.3.0 ready for release - all tests pass, documentation complete, security validated

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phases 3-8)**: All depend on Foundational phase completion
  - User Story 1 (Phase 3): Core execution - BLOCKS all other user stories
  - User Story 2 (Phase 4): Depends on US1 (extends security)
  - User Story 3 (Phase 5): Depends on US1 (extends timeout handling)
  - User Story 4 (Phase 6): Depends on US1 (extends tool restrictions)
  - User Story 5 (Phase 7): Depends on US1 (extends environment injection)
  - User Story 6 (Phase 8): Depends on US1 (detection complements execution)
- **LangChain Integration (Phase 9)**: Depends on US1 + US6
- **Testing (Phase 10)**: Can proceed in parallel with implementation (optional)
- **Documentation (Phase 11)**: Depends on all user stories being complete
- **Polish (Phase 12)**: Depends on all previous phases

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories - CORE FUNCTIONALITY
- **User Story 2 (P1)**: Can start after US1 complete - Extends security validation
- **User Story 3 (P1)**: Can start after US1 complete - Extends timeout handling
- **User Story 4 (P2)**: Can start after US1 complete - Adds tool restriction checks
- **User Story 5 (P2)**: Can start after US1 complete - Adds environment context
- **User Story 6 (P3)**: Can start after US1 complete - Adds automatic detection

### Critical Path

The minimum implementation for a working MVP:

1. Phase 1: Setup (T001-T007)
2. Phase 2: Foundational (T008-T014)
3. Phase 3: User Story 1 (T015-T033) ← CORE MVP
4. Phase 9: LangChain Integration (T063-T071)
5. Phase 11: Basic documentation (T092-T095)

This delivers the core value: scripts can be executed, results returned to agents via LangChain.

### Parallel Opportunities

- **Setup phase**: All tasks T002-T007 marked [P] can run in parallel
- **Foundational phase**: Tasks T009-T012, T014 marked [P] can run in parallel (T008, T013 are sequential)
- **Within User Story 1**: Tasks T015-T016, T021 marked [P] can run in parallel (different components)
- **Testing phase**: All test writing tasks T072-T090 marked [P] can run in parallel
- **Documentation phase**: All doc tasks T092-T099 marked [P] can run in parallel
- **Polish phase**: Tasks T100-T102 marked [P] can run in parallel

---

## Parallel Example: User Story 1 Core Components

```bash
# Launch foundational data models together:
Task: T009 - Implement ScriptMetadata dataclass
Task: T010 - Implement ScriptExecutionResult dataclass
Task: T011 - Implement INTERPRETER_MAP constant
Task: T012 - Add type aliases

# Then launch core classes together:
Task: T015 - Implement ScriptDescriptionExtractor class
Task: T016 - Implement ScriptDetector class
Task: T021 - Implement ScriptExecutor class __init__
```

---

## Implementation Strategy

### MVP First (Minimum Viable Product)

**Scope**: User Story 1 + LangChain Integration only

1. Complete Phase 1: Setup (T001-T007)
2. Complete Phase 2: Foundational (T008-T014)
3. Complete Phase 3: User Story 1 (T015-T033)
4. Complete Phase 9: LangChain Integration (T063-T071)
5. Add basic examples (T092-T095)
6. **STOP and VALIDATE**: Test script execution end-to-end with LangChain agent
7. Deploy/demo if ready

**Value Delivered**: Skills can execute scripts, pass arguments via JSON stdin, return results to agents. This is the core functionality that unblocks deterministic operations.

### Incremental Delivery (Recommended)

1. **Foundation** (Phases 1-2) → Data models and exceptions ready
2. **MVP** (Phase 3 + Phase 9) → Core execution + LangChain → Deploy/Demo
3. **Security Hardening** (Phase 4) → Path validation + security logging → Deploy/Demo
4. **Reliability** (Phase 5) → Timeout enforcement → Deploy/Demo
5. **Tool Restrictions** (Phase 6) → Enforcement → Deploy/Demo
6. **Environment Context** (Phase 7) → Metadata injection → Deploy/Demo
7. **Auto-Detection** (Phase 8) → Convenience feature → Deploy/Demo
8. **Polish** (Phases 10-12) → Tests + docs + release → v0.3.0 Release

Each increment adds value without breaking previous functionality.

### Parallel Team Strategy

With multiple developers after Foundation is complete:

- **Developer A**: User Story 1 core (Phase 3) - HIGHEST PRIORITY
- **Developer B**: Testing infrastructure (Phase 10) - Parallel with implementation
- **Developer C**: Examples and documentation (Phase 11) - Parallel with implementation

Once US1 complete:

- **Developer A**: Security (Phase 4) → Timeout (Phase 5)
- **Developer B**: Tool Restrictions (Phase 6) → Environment (Phase 7)
- **Developer C**: Auto-Detection (Phase 8) → LangChain Integration (Phase 9)

---

## Success Criteria Validation

After implementation, verify these measurable outcomes from spec.md:

- [ ] **SC-001**: Script execution overhead <50ms for 95% of executions (measure with benchmarks)
- [ ] **SC-002**: 100% of path traversal attacks blocked (test with ../../etc/passwd, symlinks, etc.)
- [ ] **SC-003**: Outputs up to 10MB captured completely; >10MB truncated with WARNING log
- [ ] **SC-004**: Timeout enforcement within ±100ms of configured value
- [ ] **SC-005**: 100% of executions logged with timestamp, skill, script, exit code, duration
- [ ] **SC-006**: 100% of unauthorized script executions blocked when Bash not in allowed-tools
- [ ] **SC-007**: Script detection <10ms for 95% of skills with ≤50 scripts
- [ ] **SC-008**: Scripts execute successfully on Linux, macOS, Windows (test cross-platform)
- [ ] **SC-009**: Zero crashes caused by script failures (all errors handled gracefully)
- [ ] **SC-010**: Custom timeouts configurable from 1-600 seconds

---

## Notes

- [P] tasks = different files/components, no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability (US1, US2, US3, etc.)
- Each user story should be independently completable and testable
- Tests are optional (not explicitly requested in spec) but recommended for quality
- Commit after each task or logical group of tasks
- Stop at any checkpoint to validate story independently
- Focus on MVP first (US1 + LangChain integration) before adding security/convenience features
- Security is critical: never use shell=True, always validate paths, enforce timeouts
- Backward compatibility: all v0.1/v0.2 APIs must continue working unchanged

---

## Estimated Timeline

Based on quickstart.md guidance:

- **Phase 1-2 (Setup + Foundational)**: 1-2 days
- **Phase 3 (User Story 1 - Core MVP)**: 2-3 days
- **Phase 4-8 (Security + Enhancements)**: 3-4 days
- **Phase 9 (LangChain Integration)**: 1 day
- **Phase 10 (Testing)**: 2-3 days (parallel with implementation)
- **Phase 11 (Documentation)**: 1-2 days
- **Phase 12 (Polish)**: 1 day

**Total**: 5-7 days for full v0.3.0 implementation (as estimated in quickstart.md)

**MVP only**: 3-4 days (Phases 1-3 + Phase 9 + basic docs)
