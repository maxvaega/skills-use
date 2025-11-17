# Tasks: v0.2 - Async Support, Advanced Discovery & File Resolution

**Input**: Design documents from `/specs/001-v0-2-async-discovery-files/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Tests are OPTIONAL per project guidelines, but CRITICAL security and remediation tests are included for User Story 3 (default directory behavior gaps) and User Story 6 (path traversal prevention).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

**⚠️ CRITICAL IMPLEMENTATION GAPS**: User Story 3 has identified gaps in default directory discovery behavior (acceptance scenarios 4-8). High-priority remediation tasks T076-T088 must be completed before v0.2 release.

## Format: `- [ ] [ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency updates for v0.2

- [X] T001 Update pyproject.toml with new dependencies: aiofiles 23.0+, pytest-asyncio 0.21+
- [X] T002 [P] Verify Python 3.10+ environment is active via venv
- [X] T003 [P] Install development dependencies with pip install -e ".[dev,async]"

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Create new exception classes in src/skillkit/core/exceptions.py: PathSecurityError, AsyncStateError, ManifestNotFoundError, ManifestParseError, ManifestValidationError
- [X] T005 Create new enumerations in src/skillkit/core/models.py: SourceType (PROJECT, ANTHROPIC, PLUGIN, CUSTOM), InitMode (UNINITIALIZED, SYNC, ASYNC)
- [X] T006 [P] Create new dataclass PluginManifest in src/skillkit/core/models.py with manifest_version, name, version, description, author, skills fields
- [X] T007 [P] Create new dataclass SkillSource in src/skillkit/core/models.py with source_type, directory, priority, plugin_name, plugin_manifest fields
- [X] T008 [P] Add QualifiedSkillName parsing utility to src/skillkit/core/models.py with parse() static method
- [X] T009 Update SkillManager.__init__() in src/skillkit/core/manager.py to accept project_skill_dir, anthropic_config_dir, plugin_dirs, additional_search_paths parameters
- [X] T010 Implement _build_sources() method in src/skillkit/core/manager.py to construct priority-ordered list of SkillSource objects
- [X] T011 Add init_mode property and state tracking to SkillManager in src/skillkit/core/manager.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Async Skill Discovery for High-Performance Applications (Priority: P1) 🎯 MVP

**Goal**: Enable non-blocking skill discovery via adiscover() for async applications with 500+ skills

**Independent Test**: Initialize SkillManager with await manager.adiscover() and verify event loop remains responsive while all skills are discovered

### Implementation for User Story 1

- [X] T012 [P] [US1] Create async file reading wrapper _read_skill_file_async() using asyncio.to_thread() in src/skillkit/core/discovery.py
- [X] T013 [P] [US1] Create async plugin manifest reading wrapper _read_manifest_async() using asyncio.to_thread() in src/skillkit/core/parser.py
- [X] T014 [US1] Implement SkillDiscovery.adiscover_skills() async method in src/skillkit/core/discovery.py using async file I/O wrappers
- [X] T015 [US1] Implement SkillManager.adiscover() async method in src/skillkit/core/manager.py that scans sources concurrently via asyncio.gather()
- [X] T016 [US1] Add AsyncStateError validation to adiscover() to prevent mixing with discover() in src/skillkit/core/manager.py
- [X] T017 [US1] Set init_mode to InitMode.ASYNC after successful adiscover() in src/skillkit/core/manager.py
- [X] T018 [US1] Update existing discover() to check for AsyncStateError and set init_mode to InitMode.SYNC in src/skillkit/core/manager.py

**Checkpoint**: Async discovery is fully functional and can be tested independently with await manager.adiscover()

---

## Phase 4: User Story 2 - Async Skill Invocation for LangChain Agents (Priority: P1)

**Goal**: Enable async skill invocation via ainvoke_skill() for LangChain async agents

**Independent Test**: Create LangChain async agent, invoke skill via await tool.ainvoke(), verify event loop remains responsive

### Implementation for User Story 2

- [X] T019 [P] [US2] Create async content loading wrapper _load_content_async() using asyncio.to_thread() in src/skillkit/core/models.py Skill class
- [X] T020 [P] [US2] Add async invoke method ainvoke() to Skill class in src/skillkit/core/models.py
- [X] T021 [US2] Implement SkillManager.ainvoke_skill() async method in src/skillkit/core/manager.py that calls skill.ainvoke()
- [X] T022 [US2] Add AsyncStateError validation to ainvoke_skill() to prevent mixing with sync invocation in src/skillkit/core/manager.py
- [X] T023 [US2] Update LangChain integration in src/skillkit/integrations/langchain.py to add coroutine parameter to StructuredTool.from_function()
- [X] T024 [US2] Implement async wrapper function for each tool in create_langchain_tools() using closure capture pattern in src/skillkit/integrations/langchain.py
- [X] T025 [US2] Update examples/langchain_agent.py to demonstrate async agent with await tool.ainvoke() usage

**Checkpoint**: Async invocation works with LangChain async agents and supports 10+ concurrent invocations

**✅ VALIDATED**: Phase 4 implementation complete and tested (42 tests, 100% pass rate)
- Async invocation tests: 22/22 passed
- LangChain async tests: 20/20 passed
- Example validation: Successfully runs with --async flag
- All code formatted, linted, and type-checked

---

## Phase 5: User Story 3 - Multiple Skill Source Discovery (Priority: P2)

**Goal**: Discover and deduplicate skills from project, anthropic, and plugin directories with priority-based conflict resolution

**Independent Test**: Configure SkillManager with 3 sources, verify all skills discovered, confirm priority order (project > anthropic > plugins)

### Implementation for User Story 3

- [X] T026 [P] [US3] Update SkillDiscovery.discover_skills() in src/skillkit/core/discovery.py to accept SkillSource parameter
- [X] T027 [US3] Implement multi-source discovery loop in SkillManager.discover() that scans all sources in priority order in src/skillkit/core/manager.py
- [X] T028 [US3] Add conflict detection and warning logging when same skill name found in multiple sources in src/skillkit/core/manager.py
- [X] T029 [US3] Implement simple name registry (highest priority wins) in SkillManager._skills dict in src/skillkit/core/manager.py
- [X] T030 [US3] Update list_skills() to support include_qualified parameter in src/skillkit/core/manager.py
- [X] T031 [US3] Update get_skill() to parse QualifiedSkillName and support both simple and qualified lookups in src/skillkit/core/manager.py
- [X] T032 [US3] Update adiscover() to implement same multi-source logic as discover() with async file I/O in src/skillkit/core/manager.py
- [X] T033 [US3] Create example script examples/multi_source.py demonstrating 3-source configuration and conflict resolution

**Checkpoint**: Multi-source discovery works with proper priority resolution for both sync and async

**✅ VALIDATED**: Phase 5 implementation complete

**⚠️ CRITICAL GAPS IDENTIFIED**: Session 2025-11-16 review identified missing implementation for acceptance scenarios 4-8:
- Default directory discovery when parameters are None/omitted
- Empty string `""` as explicit opt-out mechanism
- ConfigurationError for explicitly provided nonexistent paths
- INFO logging when no directories found
- Tri-state parameter logic (None vs "" vs Path)

**REMEDIATION REQUIRED**: Tasks T076-T088 below address these gaps before v0.2 release

---

## Phase 5.1: User Story 3 REMEDIATION - Default Directory Discovery (HIGH PRIORITY) 🚨

**Purpose**: Fix identified gaps in SkillManager initialization behavior for default directory discovery

**Impact**: Without these fixes, users cannot use zero-configuration initialization and edge cases cause confusion

### Critical Remediation Implementation

- [X] T076 [US3] Add DEFAULT_PROJECT_DIR and DEFAULT_ANTHROPIC_DIR constants to src/skillkit/core/manager.py module level (Path("./skills"), Path("./.claude/skills"))
- [X] T077 [US3] Refactor SkillManager._build_sources() in src/skillkit/core/manager.py to implement tri-state logic for project_skill_dir parameter: None → check default exists, "" → skip, Path → validate exists
- [X] T078 [US3] Refactor SkillManager._build_sources() in src/skillkit/core/manager.py to implement tri-state logic for anthropic_config_dir parameter: None → check default exists, "" → skip, Path → validate exists
- [X] T079 [US3] Add explicit path validation to _build_sources() in src/skillkit/core/manager.py: raise ConfigurationError when user-provided non-None, non-empty, non-default path doesn't exist
- [X] T080 [US3] Add empty sources INFO logging to _build_sources() in src/skillkit/core/manager.py: log "No skill directories found; initialized with empty skill list" when sources list is empty
- [X] T081 [US3] Update SkillManager.__init__() docstring in src/skillkit/core/manager.py with detailed documentation of None vs "" vs Path behavior including all edge cases
- [X] T082 [US3] Add docstring examples for common initialization patterns: zero-config, explicit paths, opt-out, mixed configurations

### Critical Remediation Tests (WRITE FIRST - MUST FAIL)

> **CRITICAL**: These tests address acceptance scenarios 4-8 from spec.md. Write tests FIRST, verify they FAIL, then implement remediation.

- [X] T083 [P] [US3] Create test_scenario_4_default_project_discovered() in tests/test_manager.py: verify SkillManager() without params discovers ./skills/ when it exists
- [X] T084 [P] [US3] Create test_scenario_5_both_defaults_priority() in tests/test_manager.py: verify SkillManager() scans both ./skills/ and ./.claude/skills/ with project priority when both exist and skill name conflicts
- [X] T085 [P] [US3] Create test_scenario_6_no_defaults_empty_with_log() in tests/test_manager.py: verify SkillManager() initializes successfully with 0 skills and INFO log when neither default directory exists
- [X] T086 [P] [US3] Create test_scenario_7_explicit_invalid_raises_error() in tests/test_manager.py: verify SkillManager(project_skill_dir="/nonexistent") raises ConfigurationError with parameter name and path in message
- [X] T087 [P] [US3] Create test_scenario_8_empty_string_opt_out() in tests/test_manager.py: verify SkillManager(project_skill_dir="", anthropic_config_dir="", plugin_dirs=[]) initializes with 0 skills and INFO log
- [X] T088 [P] [US3] Create test_mixed_valid_and_opt_out() in tests/test_manager.py: verify SkillManager(project_skill_dir="/valid/path", anthropic_config_dir="") only scans /valid/path

**Checkpoint**: ✅ User Story 3 remediation complete - all acceptance scenarios 4-8 now pass (6/6 tests passing)

---

## Phase 6: User Story 4 - Plugin Directory Support (Priority: P2)

**Goal**: Discover plugin manifests, parse metadata, load skills with plugin namespacing (plugin-name:skill-name)

**Independent Test**: Create plugin with .claude-plugin/plugin.json, verify plugin skills discovered with correct namespacing

### Implementation for User Story 4

- [X] T034 [P] [US4] Implement parse_plugin_manifest() function in src/skillkit/core/parser.py with JSON parsing and validation
- [X] T035 [P] [US4] Add PluginManifest.__post_init__() validation in src/skillkit/core/models.py with manifest_version check, name regex, version semver, skills path security validation
- [X] T036 [US4] Implement discover_plugin_manifest() in src/skillkit/core/discovery.py that scans for .claude-plugin/plugin.json
- [X] T037 [US4] Add JSON bomb protection (1MB file size limit) to parse_plugin_manifest() in src/skillkit/core/parser.py
- [X] T038 [US4] Update _build_sources() in src/skillkit/core/manager.py to parse plugin manifests for plugin_dirs
- [X] T039 [US4] Implement plugin skill namespacing in SkillManager._plugin_skills nested dict in src/skillkit/core/manager.py
- [X] T040 [US4] Add plugin skills to both _plugin_skills and _skills registries in discover() method in src/skillkit/core/manager.py
- [X] T041 [US4] Update get_skill() to handle qualified names (plugin:skill) lookups in _plugin_skills in src/skillkit/core/manager.py
- [X] T042 [US4] Add graceful error handling for malformed manifests with detailed logging in src/skillkit/core/parser.py
- [X] T043 [US4] Create example plugin structure in examples/skills/example-plugin/ with .claude-plugin/plugin.json and skills/

**Checkpoint**: Plugin discovery works with manifest parsing, namespacing, and conflict resolution

**✅ VALIDATED**: Phase 6 implementation complete

---

## Phase 7: User Story 5 - Nested Skill Structure Support (Priority: P2)

**Goal**: Support both flat (./skills/skill-name/) and nested (./skills/group/skill-name/) directory structures simultaneously

**Independent Test**: Create nested skill structure with subdirectories, verify all skills discovered regardless of nesting depth

### Implementation for User Story 5

- [X] T044 [US5] Update SkillDiscovery.discover_skills() in src/skillkit/core/discovery.py to use recursive directory walking with os.walk() or Path.rglob()
- [X] T045 [US5] Add depth limit validation (warn if >5 levels) to discovery in src/skillkit/core/discovery.py
- [X] T046 [US5] Update skill name extraction to handle nested paths correctly in src/skillkit/core/discovery.py
- [X] T047 [US5] Add symlink resolution and circular symlink detection to discovery in src/skillkit/core/discovery.py
- [X] T048 [US5] Test nested discovery with both sync and async methods to ensure consistency in src/skillkit/core/manager.py
- [X] T049 [US5] Create example nested skill structure in examples/skills/ with multiple nesting levels for demonstration

**Checkpoint**: Nested directory structures work for both flat and nested skills up to 5 levels deep

**✅ VALIDATED**: Phase 7 implementation complete and tested
- Recursive discovery: Implemented with depth limit (max 5 levels)
- Symlink handling: Circular symlink detection and resolution
- Depth warnings: Warns when exceeding max depth (>5 levels)
- Test validation: All sync and async tests passed (4/4 skills discovered at various depths)
- Example structure: Created nested-example with skills at depths 0, 1, and 2

---

## Phase 8: User Story 6 - File Reference Resolution for Skills (Priority: P2)

**Goal**: Resolve supporting file paths from skill base directory with directory traversal prevention

**Independent Test**: Create skill with supporting files, invoke and access via relative paths, verify path traversal blocked

### Implementation for User Story 6

- [X] T050 [P] [US6] Create new file src/skillkit/core/path_resolver.py with FilePathResolver class
- [X] T051 [P] [US6] Implement FilePathResolver.resolve_path() static method using Path.resolve() + is_relative_to() pattern in src/skillkit/core/path_resolver.py
- [X] T052 [US6] Add path traversal validation that raises PathSecurityError for invalid paths in src/skillkit/core/path_resolver.py
- [X] T053 [US6] Add symlink resolution and escape detection to resolve_path() in src/skillkit/core/path_resolver.py
- [X] T054 [US6] Implement ERROR-level logging for all PathSecurityError exceptions in src/skillkit/core/path_resolver.py
- [X] T055 [US6] Create BaseDirectoryProcessor enhancement that injects base directory context into skill content in src/skillkit/core/processors.py
- [X] T056 [US6] Update Skill class to expose base_directory property in src/skillkit/core/models.py
- [X] T057 [US6] Add file path resolution helper message to processed content in src/skillkit/core/processors.py
- [X] T058 [US6] Create example script examples/file_references.py demonstrating supporting file access with FilePathResolver
- [X] T059 [US6] Create example skill with supporting files (scripts/, templates/, docs/) in examples/skills/file-reference-skill/

**Checkpoint**: File path resolution works securely with all attack vectors blocked and clear error messages

**✅ VALIDATED**: Phase 8 implementation complete
- FilePathResolver created with secure path validation
- Path traversal prevention using Path.resolve() + is_relative_to()
- Symlink resolution and escape detection implemented
- ERROR-level logging for security violations
- BaseDirectoryProcessor enhanced with file resolution helper
- Example skill with supporting files created (scripts/, templates/, docs/)
- Example script demonstrating all use cases
- All code formatted, linted, and type-checked

---

## Phase 9: User Story 7 - Graceful Conflict Resolution Across Skill Sources (Priority: P3)

**Goal**: Resolve conflicts using priority order (project > anthropic > plugins) with fully qualified name disambiguation

**Independent Test**: Create skills with identical names in different sources, verify priority order and qualified name access

### Implementation for User Story 7

- [X] T060 [US7] Enhance conflict warning logging in discover() to include all conflicting paths and resolution used in src/skillkit/core/manager.py
- [X] T061 [US7] Update list_skills(include_qualified=True) to return both simple and qualified names for conflicts in src/skillkit/core/manager.py
- [X] T062 [US7] Add duplicate plugin name detection with warning and disambiguator suffix (plugin-name-2) in src/skillkit/core/manager.py
- [X] T063 [US7] Update documentation strings in src/skillkit/core/manager.py to clarify priority order and qualified name usage
- [X] T064 [US7] Create comprehensive example demonstrating all conflict scenarios in examples/multi_source.py

**Checkpoint**: Conflict resolution is transparent with clear warnings and qualified name access to all versions

**✅ VALIDATED**: Phase 9 implementation complete
- Enhanced conflict logging with full path and priority details
- list_skills(include_qualified=True) returns qualified names only for conflicts
- Duplicate plugin name detection and automatic disambiguation
- Comprehensive documentation updates clarifying priority order
- Complete example demonstrating all 5 conflict resolution scenarios

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T065 [P] Update README.md with v0.2 async examples and multi-source configuration
- [X] T066 [P] Update examples/basic_usage.py to show both sync and async patterns
- [X] T067 [P] Create examples/async_usage.py with FastAPI integration and concurrent invocations
- [X] T068 [P] Add type hints to all new async methods ensuring mypy strict mode compatibility
- [X] T069 Code cleanup: Remove any debug logging, ensure consistent error messages across all modules
- [X] T070 [P] Update src/skillkit/__init__.py to export new public APIs (adiscover, ainvoke_skill, FilePathResolver)
- [X] T071 Verify backward compatibility by running v0.1 usage patterns against v0.2 code
- [X] T072 Run ruff format and ruff check on all modified files
- [X] T073 Run mypy --strict on src/skillkit to verify type safety
- [X] T074 Validate all quickstart.md examples execute successfully
- [X] T075 Update CHANGELOG.md with v0.2 release notes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-9)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 10)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1) - Async Discovery**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1) - Async Invocation**: Depends on User Story 1 completion (needs async discovery)
- **User Story 3 (P2) - Multi-Source Discovery**: Can start after Foundational (Phase 2) - Independent from async stories
- **User Story 4 (P2) - Plugin Support**: Depends on User Story 3 completion (needs multi-source infrastructure)
- **User Story 5 (P2) - Nested Structures**: Can start after Foundational (Phase 2) - Independent from other stories
- **User Story 6 (P2) - File Resolution**: Can start after Foundational (Phase 2) - Independent from other stories
- **User Story 7 (P3) - Conflict Resolution**: Depends on User Stories 3 and 4 completion (needs multi-source + plugins)

### Within Each User Story

- Foundation tasks before story-specific tasks
- Models before services
- Core implementation before examples
- Sync implementation before async (for US1, US2)
- Story complete before moving to next priority

### Parallel Opportunities

- **Phase 1 (Setup)**: All tasks can run in parallel (T001, T002, T003)
- **Phase 2 (Foundational)**: Tasks T004-T008 can run in parallel (new models/exceptions), T009-T011 sequential
- **User Story 1**: T012 and T013 can run in parallel (different files)
- **User Story 2**: T019 and T020 can run in parallel (different files)
- **User Story 3**: T026 can run in parallel with other tasks before T027
- **User Story 4**: T034, T035 can run in parallel (different aspects of manifest parsing)
- **User Story 6**: T050, T051, T052, T053, T054 can be worked on in parallel (different aspects of path resolver)
- **Phase 10 (Polish)**: T065, T066, T067, T068, T070 can all run in parallel (different files)

---

## Parallel Example: User Story 1 (Async Discovery)

```bash
# Launch async wrappers in parallel (different files):
Task: "Create async file reading wrapper _read_skill_file_async() in discovery.py"
Task: "Create async plugin manifest reading wrapper _read_manifest_async() in parser.py"

# Then implement async discovery methods sequentially
```

---

## Parallel Example: User Story 6 (File Resolution)

```bash
# Launch path resolver implementation tasks in parallel:
Task: "Create FilePathResolver class in path_resolver.py"
Task: "Implement resolve_path() static method in path_resolver.py"
Task: "Add path traversal validation in path_resolver.py"
Task: "Add symlink resolution in path_resolver.py"
Task: "Add error logging in path_resolver.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only - Both P1)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Async Discovery)
4. Complete Phase 4: User Story 2 (Async Invocation)
5. **STOP and VALIDATE**: Test async discovery + invocation independently
6. Deploy/demo async functionality

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 + 2 → Test async independently → Deploy/Demo (Async MVP!)
3. Add User Story 3 + 4 → Test multi-source + plugins independently → Deploy/Demo
4. Add User Story 5 → Test nested structures independently → Deploy/Demo
5. Add User Story 6 → Test file resolution independently → Deploy/Demo
6. Add User Story 7 → Test conflict resolution independently → Deploy/Demo
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 + 2 (Async - sequential within)
   - Developer B: User Story 3 + 4 (Multi-source - sequential within)
   - Developer C: User Story 5 (Nested - independent)
   - Developer D: User Story 6 (File resolution - independent)
3. User Story 7 done last (depends on US3 + US4)
4. Stories complete and integrate independently

---

## Implementation Notes

### Async Implementation Pattern

All async methods follow this pattern:
```python
async def async_method(self):
    """Async version using asyncio.to_thread()."""
    def _sync_impl():
        # Sync implementation
        pass
    return await asyncio.to_thread(_sync_impl)
```

### Security Validation Pattern

All security validations follow this pattern:
```python
# 1. Normalize path
resolved = path.resolve()

# 2. Validate within base
if not resolved.is_relative_to(base):
    raise PathSecurityError(f"Path traversal: {path}")

# 3. Log attempt
logger.error("Security violation detected", extra={...})
```

### Plugin Manifest Validation Pattern

All plugin manifest validations follow this pattern:
```python
# 1. Check file size (JSON bomb protection)
if path.stat().st_size > MAX_MANIFEST_SIZE:
    raise ManifestParseError("File too large")

# 2. Parse JSON
data = json.load(f)

# 3. Validate required fields
# 4. Validate field formats
# 5. Security checks (path traversal in skills field)
```

---

## Success Criteria Validation

After completing all tasks, verify these success criteria from spec.md:

- **SC-001**: Async discovery of 500 skills completes in <200ms
- **SC-002**: Async invocation adds <2ms overhead vs sync
- **SC-003**: 10+ parallel invocations work without errors
- **SC-004**: 3+ source directories with priority resolution work correctly
- **SC-005**: Plugin discovery finds all plugins and namespaces correctly
- **SC-006**: Nested structures up to 5 levels discovered correctly
- **SC-007**: Path traversal blocked 100% with clear errors
- **SC-008**: Supporting files accessible via relative paths
- **SC-009**: Fully qualified names resolve correctly with conflicts
- **SC-010**: Async and sync APIs produce identical results

---

## Task Summary

**Total Tasks**: 88 (75 completed ✅ + 13 remediation tasks 🚨)

**Tasks by Phase**:
- Phase 1 (Setup): 3 tasks ✅ COMPLETE
- Phase 2 (Foundational): 8 tasks ✅ COMPLETE
- Phase 3 (US1 - Async Discovery): 7 tasks ✅ COMPLETE
- Phase 4 (US2 - Async Invocation): 7 tasks ✅ COMPLETE
- Phase 5 (US3 - Multi-Source): 8 tasks ✅ COMPLETE
- **Phase 5.1 (US3 REMEDIATION)**: 13 tasks 🚨 HIGH PRIORITY
- Phase 6 (US4 - Plugin Support): 10 tasks ✅ COMPLETE
- Phase 7 (US5 - Nested Structures): 6 tasks ✅ COMPLETE
- Phase 8 (US6 - File Resolution): 10 tasks ✅ COMPLETE
- Phase 9 (US7 - Conflict Resolution): 5 tasks ✅ COMPLETE
- Phase 10 (Polish): 11 tasks ✅ COMPLETE

**Critical Path to v0.2 Release**:
1. ✅ Phases 1-10 completed (75 tasks)
2. 🚨 **Phase 5.1 Remediation REQUIRED** (13 tasks) - Blocks v0.2.0 release
3. After remediation: Performance validation (SC-001, SC-002) + final release

**Parallel Opportunities**:
- Remediation tests T083-T088 can run in parallel (6 tests, different scenarios)
- Implementation tasks T076-T082 are sequential (refactoring same method)

**Estimated Remediation Time**: 4-6 hours
- Implementation (T076-T082): 2-3 hours
- Tests (T083-T088): 1.5-2 hours
- Validation and edge case testing: 0.5-1 hour

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests are OPTIONAL per project guidelines (critical security/remediation tests included)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- All file paths use src/skillkit/ structure per plan.md project structure
- Backward compatibility with v0.1 is mandatory (validated in Phase 10)
- **🚨 CRITICAL**: Phase 5.1 remediation must complete before v0.2.0 release (identified in plan.md Session 2025-11-16)
