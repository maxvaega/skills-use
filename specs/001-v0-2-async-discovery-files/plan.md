# Implementation Plan: v0.2 - Async Support, Advanced Discovery & File Resolution

**Branch**: `001-v0-2-async-discovery-files` | **Date**: 2025-11-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-v0-2-async-discovery-files/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature completes the v0.2 release by implementing three major capabilities:

1. **Async Support**: Non-blocking skill discovery and invocation via `adiscover()` and `ainvoke_skill()` methods, with async file I/O and full LangChain `ainvoke` integration
2. **Advanced Discovery**: Multiple skill sources (project/anthropic/plugins), plugin manifest parsing, nested directory structures, and fully qualified skill names for conflict resolution
3. **File Reference Resolution**: Secure relative path resolution for skill supporting files with directory traversal prevention

The implementation maintains backward compatibility with v0.1 sync APIs while adding async as an optional enhancement. Priority order for skill conflicts is: project > anthropic > plugins > additional paths.

## Technical Context

<!--
  ACTION REQUIRED: Replace the content in this section with the technical details
  for the project. The structure here is presented in advisory capacity to guide
  the iteration process.
-->

**Language/Version**: Python 3.10+ (minimum for full async support)
**Primary Dependencies**: PyYAML 6.0+, aiofiles 23.0+ (new), langchain-core 0.1.0+, pydantic 2.0+
**Storage**: Filesystem-based (`.claude/skills/` directories, `.claude-plugin/plugin.json` manifests)
**Testing**: pytest 7.0+, pytest-asyncio 0.21+ (new), pytest-cov 4.0+
**Target Platform**: Cross-platform (Linux, macOS, Windows) with asyncio event loop support
**Project Type**: Single Python library with framework-agnostic core
**Performance Goals**: Async discovery <200ms for 500 skills, async invocation overhead <2ms
**Constraints**: Backward compatible with v0.1, zero new dependencies in core (aiofiles optional)
**Scale/Scope**: Support 500+ skills across 10+ sources with nested structures up to 5 levels deep

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Framework-Agnostic Core Principle

**Status**: ✅ PASS

- Async support implemented in `src/skillkit/core/` using only stdlib asyncio and aiofiles
- No framework-specific dependencies introduced to core modules
- LangChain async integration isolated in `src/skillkit/integrations/langchain.py`

### Progressive Disclosure Pattern

**Status**: ✅ PASS

- Maintains v0.1 lazy loading architecture (SkillMetadata + Skill two-tier pattern)
- Async discovery loads only metadata; full content loaded on-demand via `ainvoke_skill()`
- No changes to memory efficiency characteristics

### Backward Compatibility

**Status**: ✅ PASS

- All v0.1 sync APIs (`discover()`, `invoke_skill()`) remain unchanged
- Async methods are purely additive (`adiscover()`, `ainvoke_skill()`)
- Existing code using sync methods continues working without modifications

### Security-First Design

**Status**: ✅ PASS

- Path traversal prevention is mandatory for file reference resolution
- Uses `pathlib.Path.resolve()` for canonical path validation
- All resolved paths validated to stay within skill base directory
- SecurityError raised on any traversal attempts

### Testing Requirements

**Status**: ✅ PASS

- Maintains 70% coverage minimum from v0.1
- Adds pytest-asyncio for async code path coverage
- Parametrized tests for sync/async equivalence validation
- Security fuzzing tests for path traversal edge cases

### Complexity Justification

**Status**: ✅ PASS (with justification)

- **Async complexity**: Justified by target use case (500+ skills, high-concurrency agents)
- **Multi-source discovery**: Required for Anthropic plugin ecosystem support
- **Path validation**: Security-critical feature, cannot be simplified

**Gates Result**: All checks PASS. Proceed to Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/skillkit/
├── core/                          # Framework-agnostic core (v0.1 + v0.2 extensions)
│   ├── discovery.py               # SkillDiscovery: sync + async filesystem scanning
│   ├── parser.py                  # SkillParser: YAML parsing + plugin manifest parsing
│   ├── models.py                  # SkillMetadata, Skill, PluginManifest, SkillSource
│   ├── manager.py                 # SkillManager: sync/async orchestration + multi-source
│   ├── processors.py              # ContentProcessor: $ARGUMENTS + file path injection
│   ├── path_resolver.py           # NEW: FilePathResolver for secure relative path resolution
│   └── exceptions.py              # Exception hierarchy (add AsyncStateError, PathSecurityError)
├── integrations/
│   └── langchain.py               # LangChain StructuredTool: add ainvoke support
└── py.typed

tests/
├── test_discovery.py              # Discovery: async tests + multi-source tests
├── test_parser.py                 # Parser: plugin manifest parsing tests
├── test_models.py                 # Models: new dataclasses (PluginManifest, SkillSource)
├── test_processors.py             # Processors: file path injection tests
├── test_path_resolver.py          # NEW: Path resolution + security validation tests
├── test_manager.py                # Manager: async methods + multi-source orchestration
├── test_langchain.py              # LangChain: ainvoke integration tests
└── fixtures/
    └── skills/                    # Test SKILL.md files
        ├── valid-skill/
        ├── nested-skill/           # NEW: nested directory structure
        ├── plugin-skill/           # NEW: plugin with manifest
        └── path-traversal-skill/   # NEW: malicious path test cases

examples/
├── async_usage.py                 # NEW: Async discovery and invocation example
├── multi_source.py                # NEW: Multiple skill sources example
└── file_references.py             # NEW: Supporting files example
```

**Structure Decision**: Single Python library structure maintained from v0.1. New files added for async support (`path_resolver.py`), new test fixtures for v0.2 scenarios, and new examples demonstrating async and multi-source features.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**Status**: No violations. All complexity is justified by requirements.

---

## Post-Design Constitution Check

*Re-evaluated after Phase 1 design completion*

### Framework-Agnostic Core Principle

**Status**: ✅ PASS (Confirmed)

- Design maintains separation: `asyncio.to_thread()` in core (stdlib only)
- `aiofiles` NOT used in core (deferred to optional dependency)
- Plugin manifest parsing uses `json` module (stdlib)
- All new entities (`SkillSource`, `PluginManifest`, `QualifiedSkillName`, `SkillPath`) are pure dataclasses

### Progressive Disclosure Pattern

**Status**: ✅ PASS (Confirmed)

- No changes to v0.1 lazy loading architecture
- Async methods use same two-tier pattern (metadata → full skill)
- `FilePathResolver` is stateless utility (zero memory overhead)
- Plugin manifests loaded once per plugin (minimal overhead: ~400 bytes each)

### Backward Compatibility

**Status**: ✅ PASS (Confirmed)

- All v0.1 method signatures unchanged
- New parameters are optional with sensible defaults
- v0.1 constructor argument `skill_dir` mapped to `project_skill_dir`
- Async methods have distinct names (`adiscover`, `ainvoke_skill`) to avoid confusion

### Security-First Design

**Status**: ✅ PASS (Confirmed)

- `FilePathResolver.resolve_path()` implements OWASP path traversal prevention
- Uses `Path.resolve()` + `is_relative_to()` pattern (Python 3.9+ safe)
- All 7 attack vectors tested and documented
- `PathSecurityError` raised on any validation failure with detailed context

### Testing Requirements

**Status**: ✅ PASS (Confirmed)

- Test plan maintains 70% coverage target
- Added `pytest-asyncio` for async code paths
- Security fuzzing tests for path traversal (100+ malicious patterns)
- Integration tests for multi-source discovery and plugin manifests

### API Design Quality

**Status**: ✅ PASS (New Check)

- All public methods have type hints (mypy strict mode compatible)
- Error messages include context (skill name, path, source)
- Async methods follow Python async best practices (not blocking, proper error propagation)
- API contracts documented with examples, exceptions, and performance characteristics

**Final Gates Result**: All checks PASS. Design approved for implementation (Phase 2).
