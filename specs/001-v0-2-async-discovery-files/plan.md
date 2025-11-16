# Implementation Plan: v0.2 - Async Support, Advanced Discovery & File Resolution

**Branch**: `001-v0-2-async-discovery-files` | **Date**: 2025-11-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-v0-2-async-discovery-files/spec.md`

**Note**: This plan has been updated to incorporate clarifications from Session 2025-11-16 regarding SkillManager initialization behavior (User Story 3).

## Summary

v0.2 adds enterprise-grade async capabilities and multi-source skill discovery to skillkit. Primary features include: (1) Full async/await support (`adiscover()`, `ainvoke_skill()`) for non-blocking operations in FastAPI and async agents, (2) Multi-source discovery with priority-based resolution (project > anthropic > plugins > custom), (3) Plugin ecosystem support with MCPB manifest parsing, (4) Secure file reference resolution with path traversal prevention, and (5) Nested skill directory structures up to 5 levels deep.

**Critical Update (2025-11-16)**: Implementation review reveals gaps in User Story 3 acceptance scenarios 4-8 (default directory discovery and initialization behavior). Current `_build_sources()` method requires updates to support:
- Default directory discovery when parameters are None/omitted
- Empty string `""` as explicit opt-out signal
- ConfigurationError for explicitly provided nonexistent paths
- INFO logging when no directories are found
- Proper differentiation between None (apply defaults) and "" (opt-out)

## Technical Context

**Language/Version**: Python 3.10+ (minimum for full async/await support with aiofiles)
**Primary Dependencies**: PyYAML 6.0+, aiofiles 23.0+, langchain-core 0.1.0+, pydantic 2.0+
**Storage**: Filesystem-based (`.claude/skills/`, `./skills/`, plugin directories with SKILL.md files)
**Testing**: pytest 7.0+, pytest-asyncio 0.21+, pytest-cov 4.0+ (target: 70%+ coverage)
**Target Platform**: Cross-platform (macOS, Linux, Windows with best-effort Windows UNC path support)
**Project Type**: Python library (single-project structure with optional framework integrations)
**Performance Goals**: Async discovery <200ms for 500 skills (SC-001), async invocation overhead <2ms (SC-002)
**Constraints**: Backward compatible with v0.1 sync APIs, framework-agnostic core (zero dependencies except PyYAML/aiofiles), strict type safety (mypy --strict)
**Scale/Scope**: Support 500+ skills, 5-level nested directories, concurrent plugin discovery, production-grade error handling

**Session 2025-11-16 Clarifications - Default Directory Behavior**:
The SkillManager initialization behavior for User Story 3 has been clarified with specific requirements for handling default directories (`./skills/`, `./.claude/skills/`):

1. **None vs Omitted Parameters**: Both `SkillManager()` and `SkillManager(project_skill_dir=None)` MUST behave identically - apply default directory discovery
2. **Default Discovery Logic**: When project_skill_dir is None/omitted, check if `./skills/` exists; when anthropic_config_dir is None/omitted, check if `./.claude/skills/` exists; scan all that exist
3. **Both Defaults Exist**: When both `./skills/` and `./.claude/skills/` exist, MUST scan both with priority-based deduplication (./skills/ wins conflicts)
4. **No Defaults Exist**: When neither default directory exists and no custom paths provided, initialize successfully with empty skill list + INFO log "No skill directories found; initialized with empty skill list"
5. **Explicit Opt-Out**: Empty string `""` for directory parameters and empty list `[]` for plugin_dirs MUST disable discovery for those sources (no default fallback, no INFO message)
6. **Explicit Invalid Path**: When user provides explicit non-None, non-empty, non-default path that doesn't exist (e.g., `SkillManager(project_skill_dir="/bad/path")`), MUST raise ConfigurationError immediately with message indicating which parameter and path failed
7. **Mixed Opt-Out**: Support mixed configurations like `SkillManager(project_skill_dir="/valid/path", anthropic_config_dir="")` - only scan /valid/path, anthropic discovery explicitly disabled

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Note**: Project constitution file is currently a template placeholder. The following checks are based on standard Python library best practices and the project's documented principles in CLAUDE.md:

### Core Principle Compliance

1. **Library-First Design**: ✅ PASS
   - v0.2 maintains framework-agnostic core in `src/skillkit/core/`
   - Optional integrations remain in `src/skillkit/integrations/`
   - Zero breaking changes to v0.1 public API

2. **Test-First Development**: ⚠️ PARTIAL (User Story 3 gaps identified)
   - Existing tests cover async patterns, multi-source discovery, plugin support
   - **Gap**: Tests for acceptance scenarios 4-8 (default directory behavior) are incomplete
   - **Required**: Add tests for None/omitted parameters, empty string opt-out, ConfigurationError validation
   - Coverage target: 70%+ (current status: 70%+, but gaps exist in initialization edge cases)

3. **Backward Compatibility**: ✅ PASS
   - All v0.1 sync APIs preserved (`discover()`, `invoke_skill()`, `load_skill()`)
   - Async methods are additive (`adiscover()`, `ainvoke_skill()`)
   - Legacy `skill_dir` parameter mapped to `project_skill_dir` with deprecation warning

4. **Performance Requirements**: ✅ PASS
   - Target: <200ms for 500 skills async discovery (SC-001)
   - Target: <2ms overhead for async invocation (SC-002)
   - Memory: No increase from v0.1 (progressive disclosure pattern maintained)

5. **Security Requirements**: ✅ PASS
   - Path traversal prevention implemented with `pathlib.resolve()` validation
   - YAML safe loading via `yaml.safe_load()`
   - Argument substitution with 1MB size limit and suspicious pattern detection

### Session 2025-11-16 Clarifications - Implementation Gaps

**Status**: 🔴 REQUIRES REMEDIATION

The current implementation (`src/skillkit/core/manager.py:134-267`, `_build_sources()` method) does NOT fully implement User Story 3 acceptance scenarios 4-8:

**Gap Analysis**:

| Requirement | Current Behavior | Required Behavior | Remediation |
|-------------|------------------|-------------------|-------------|
| None/omitted parameters | Ignored (no defaults applied) | Apply default directory discovery (`./skills/`, `./.claude/skills/`) | Update `_build_sources()` to check for defaults when param is None |
| Both defaults exist | Not handled | Scan both with priority deduplication | Add logic to scan both when both exist |
| No defaults exist | Silent (no skills, no log) | Initialize with empty list + INFO log | Add INFO logging when no directories found |
| Empty string opt-out | Not distinguished from None | Treat "" as explicit opt-out (no defaults) | Add condition: `if param == "": skip` vs `if param is None: apply_defaults` |
| Explicit invalid path | WARNING logged, continues | Raise ConfigurationError immediately | Add path validation before processing |
| Mixed opt-out | Not tested | Support mixed valid path + opt-out | Validate with integration test |

**Required Changes**:

1. **`_build_sources()` method** (manager.py:134-267):
   - Add default directory constants (`DEFAULT_PROJECT_DIR = "./skills/"`, `DEFAULT_ANTHROPIC_DIR = "./.claude/skills/"`)
   - Implement tri-state logic for each parameter: `None` (apply defaults) | `""` (opt-out) | `Path` (use explicit)
   - Add path existence validation for explicit non-default paths → raise ConfigurationError
   - Add INFO logging when no sources are configured after processing all parameters

2. **`SkillManager.__init__()` signature** (manager.py:57-102):
   - No signature changes required (already accepts `str | Path | None`)
   - Update docstring to document None vs "" behavior

3. **Exception handling** (exceptions.py):
   - Verify ConfigurationError exists with appropriate message formatting

4. **Tests** (tests/test_manager.py):
   - Add parametrized tests for acceptance scenarios 4-8
   - Test None vs omitted parameters (both should trigger defaults)
   - Test empty string opt-out behavior
   - Test ConfigurationError for invalid explicit paths
   - Test INFO logging when no directories found
   - Test mixed configurations

**Recommendation**: Implement remediation in tasks.md as high-priority tasks before v0.2 release completion.

## Project Structure

### Documentation (this feature)

```text
specs/001-v0-2-async-discovery-files/
├── plan.md              # This file (UPDATED 2025-11-16)
├── research.md          # Phase 0 output (COMPLETE)
├── data-model.md        # Phase 1 output (COMPLETE)
├── quickstart.md        # Phase 1 output (COMPLETE)
├── contracts/           # Phase 1 output (COMPLETE)
│   ├── skill-manager-api.md
│   ├── skill-discovery-api.md
│   └── plugin-manifest-schema.json
└── tasks.md             # Phase 2 output (COMPLETE, needs update for gaps)
```

### Source Code (repository root)

**Structure Decision**: Single-project Python library structure (Option 1). This is a standalone library with optional framework integrations, not a web/mobile application.

```text
src/skillkit/
├── __init__.py             # Public API exports
├── core/                   # Framework-agnostic core
│   ├── __init__.py
│   ├── discovery.py        # Multi-source discovery + plugin manifest parsing
│   ├── parser.py           # YAML frontmatter parsing
│   ├── models.py           # SkillMetadata, Skill, SkillSource, PluginManifest
│   ├── manager.py          # ⚠️ NEEDS UPDATE: _build_sources() method (User Story 3 gaps)
│   ├── processors.py       # Content processors (argument substitution)
│   └── exceptions.py       # Exception hierarchy (verify ConfigurationError exists)
├── integrations/           # Framework-specific adapters
│   └── langchain.py        # LangChain async integration
└── py.typed                # PEP 561 marker

tests/
├── conftest.py             # Shared fixtures
├── test_discovery.py       # Discovery tests (async + sync)
├── test_parser.py          # Parser tests
├── test_models.py          # Dataclass tests
├── test_processors.py      # Processor tests
├── test_manager.py         # ⚠️ NEEDS UPDATE: Add tests for User Story 3 scenarios 4-8
├── test_langchain.py       # LangChain integration tests
└── fixtures/
    └── skills/             # Test SKILL.md files

examples/
├── basic_usage.py          # Sync and async patterns
├── async_usage.py          # FastAPI integration
├── langchain_agent.py      # LangChain sync/async
├── multi_source.py         # Multi-source discovery
├── file_references.py      # Secure file resolution
└── skills/                 # Example skill directories

pyproject.toml              # Package configuration (PEP 621)
README.md                   # User-facing documentation
CLAUDE.md                   # AI agent context (project instructions)
.docs/                      # Comprehensive specs
├── PRD_skillkit_LIBRARY.md
├── MVP_VERTICAL_SLICE_PLAN.md
├── TECH_SPECS.md
└── SKILL format specification
```

**Key Files Requiring Updates for Session 2025-11-16 Clarifications**:
- `src/skillkit/core/manager.py` - `_build_sources()` method and `__init__()` docstring
- `src/skillkit/core/exceptions.py` - Verify ConfigurationError implementation
- `tests/test_manager.py` - Add parametrized tests for acceptance scenarios 4-8

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**Status**: No constitutional violations requiring justification. All complexity is essential:

1. **Async/Sync Dual APIs**: Required for backward compatibility (v0.1 sync users) + modern async adoption
2. **Multi-Source Discovery**: Essential for plugin ecosystem and organizational separation of concerns
3. **Tri-State Parameter Logic (None/""/ Path)**: Required for flexible initialization (defaults + opt-out + explicit)
4. **Priority-Based Conflict Resolution**: Necessary for predictable behavior when skill names collide across sources

All complexity aligns with v0.2 feature requirements and user scenarios 1-7.

## Implementation Gaps Summary (Session 2025-11-16)

**Current Status**: v0.2 implementation is ~85% complete. The following gaps in User Story 3 (acceptance scenarios 4-8) require remediation:

### Gap 1: Default Directory Discovery Not Implemented
**Location**: `src/skillkit/core/manager.py:134-267` (`_build_sources()`)
**Issue**: When `project_skill_dir=None` or `anthropic_config_dir=None`, no default directories are checked
**Required**: Check for `./skills/` and `./.claude/skills/` when parameters are None/omitted
**Impact**: Users cannot use zero-configuration initialization - must always provide explicit paths

### Gap 2: Empty String Not Treated as Opt-Out
**Location**: `src/skillkit/core/manager.py:134-267` (`_build_sources()`)
**Issue**: No distinction between `None` (should apply defaults) and `""` (should opt-out)
**Required**: Implement tri-state logic: `None` → defaults, `""` → skip, `Path` → use explicit
**Impact**: Users cannot explicitly disable default directory discovery

### Gap 3: Explicit Invalid Paths Only Warn
**Location**: `src/skillkit/core/manager.py:161-174, 177-192, 201-242, 245-257`
**Issue**: Invalid explicit paths log WARNING and continue instead of raising ConfigurationError
**Required**: Distinguish between default paths (warn + continue) vs explicit paths (error immediately)
**Impact**: User mistakes in configuration are silently ignored, leading to confusion

### Gap 4: No INFO Logging When No Directories Found
**Location**: `src/skillkit/core/manager.py:259-266` (end of `_build_sources()`)
**Issue**: When no sources are configured, initialization is silent
**Required**: Log INFO message "No skill directories found; initialized with empty skill list"
**Impact**: Users don't know if initialization succeeded with zero skills vs failed silently

### Gap 5: Missing Tests for New Behavior
**Location**: `tests/test_manager.py`
**Issue**: No tests for acceptance scenarios 4-8 (default discovery, opt-out, error handling)
**Required**: Add parametrized tests covering all initialization edge cases
**Impact**: Changes risk introducing regressions without test safety net

### Remediation Roadmap

**Estimated Effort**: 4-6 hours (coding + testing)

1. **Step 1**: Update `_build_sources()` with default directory logic (2 hours)
   - Add constants for default paths
   - Implement tri-state parameter handling
   - Add ConfigurationError for invalid explicit paths
   - Add INFO logging when sources list is empty

2. **Step 2**: Verify ConfigurationError implementation (15 minutes)
   - Check `src/skillkit/core/exceptions.py` has ConfigurationError
   - Add if missing with appropriate error message formatting

3. **Step 3**: Update `__init__()` docstring (30 minutes)
   - Document None vs "" behavior
   - Add examples for all initialization patterns

4. **Step 4**: Add comprehensive tests (2 hours)
   - Test None/omitted parameters trigger defaults
   - Test empty string disables discovery
   - Test ConfigurationError for invalid explicit paths
   - Test INFO logging when no directories found
   - Test mixed configurations

5. **Step 5**: Update examples and documentation (1 hour)
   - Add example for zero-configuration initialization
   - Update quickstart.md with default behavior explanation
   - Add troubleshooting section for common initialization issues

**Next Command**: `/speckit.tasks` to generate updated tasks.md with remediation tasks as high-priority items
