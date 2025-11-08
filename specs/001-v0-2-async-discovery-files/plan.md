# Implementation Plan: v0.2 - Async Support, Advanced Discovery & File Resolution

**Branch**: `001-v0-2-async-discovery-files` | **Date**: 2025-11-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-v0-2-async-discovery-files/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature completes the v0.2 milestone by adding three major enhancements to skillkit:

1. **Async Support (IR-2.4)**: Non-blocking async methods for skill discovery and invocation, enabling integration with async frameworks (FastAPI, async LangChain agents) via `adiscover()`, `ainvoke_skill()`, and LangChain `ainvoke` support
2. **Advanced Discovery (FR-1)**: Multi-source skill discovery from project, Anthropic, and plugin directories with priority-based conflict resolution, plugin manifest parsing, nested directory structures, and fully qualified naming
3. **File Reference Resolution (FR-5)**: Secure relative path resolution for skill supporting files (scripts, templates, docs) with path traversal prevention

The implementation maintains 100% backward compatibility with v0.1's sync API while adding async capabilities as a parallel code path. Memory efficiency is preserved through lazy loading, and security is enhanced through path validation.

## Technical Context

**Language/Version**: Python 3.10+ (minimum 3.10, recommended 3.11+ for optimal memory efficiency)
**Primary Dependencies**:
- Core: PyYAML 6.0+ (YAML parsing), aiofiles 23.0+ (async file I/O - NEW for v0.2)
- Optional: langchain-core 0.1.0+, pydantic 2.0+ (LangChain integration)
- Dev: pytest 7.0+, pytest-asyncio 0.21+ (NEW for v0.2), pytest-cov 4.0+, ruff 0.1.0+, mypy 1.0+

**Storage**: Filesystem-based (.claude/skills/, project skills/, plugin directories with .claude-plugin/plugin.json manifests)
**Testing**: pytest with pytest-asyncio for async test coverage, mypy strict mode for type safety, 70% coverage target
**Target Platform**: Cross-platform (Linux, macOS, Windows) Python library for distribution via PyPI
**Project Type**: Single Python library with framework-agnostic core and optional integrations
**Performance Goals**:
- Async discovery: <200ms for 500 skills (50% faster than sync)
- Async invocation: <2ms overhead vs sync
- Event loop: Never block >5ms during async operations
- Memory: <2.5MB for 100 skills (maintain v0.1 efficiency)

**Constraints**:
- 100% backward compatibility with v0.1 sync API
- Zero new dependencies in core (aiofiles is core, not integration)
- Path traversal validation must be bulletproof (security-critical)
- Async and sync APIs must produce identical results (except timing)

**Scale/Scope**:
- Support 500+ skills across multiple sources
- Handle up to 5 levels of nested directory structures
- Concurrent async invocations: 10+ parallel without errors
- Plugin ecosystem: Multiple plugins with namespace isolation

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: No project constitution file found at `.specify/memory/constitution.md`. The file contains only a template.

**Proceeding with general software engineering best practices**:

1. ✅ **Backward Compatibility**: v0.1 sync API remains unchanged and functional
2. ✅ **Test Coverage**: Maintaining 70% coverage requirement, adding pytest-asyncio for async paths
3. ✅ **Type Safety**: All new async methods will have full type hints compatible with mypy strict mode
4. ✅ **Security First**: Path traversal validation is security-critical and will be thoroughly tested
5. ✅ **Framework Agnostic**: Core async support uses stdlib asyncio + aiofiles, no framework dependencies
6. ✅ **Documentation**: All new APIs will be documented with examples in quickstart.md
7. ✅ **Progressive Enhancement**: Async is additive; users can continue using sync API

**No violations detected**. Proceeding to Phase 0 research.

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
├── __init__.py                 # Public API exports
├── py.typed                    # Type hints marker
├── core/                       # Framework-agnostic core (v0.1 + v0.2 additions)
│   ├── __init__.py             # Core exports
│   ├── models.py               # SkillMetadata, Skill dataclasses (NEW: SkillSource, PluginManifest)
│   ├── discovery.py            # SkillDiscovery (NEW: async, multi-source, plugin support)
│   ├── parser.py               # SkillParser (NEW: plugin manifest parsing)
│   ├── manager.py              # SkillManager (NEW: async methods, multi-source, path resolution)
│   ├── processors.py           # ContentProcessor (NEW: base directory injection)
│   ├── exceptions.py           # Exception hierarchy (NEW: SecurityError for path traversal)
│   └── path_utils.py           # NEW: Path validation and resolution utilities
└── integrations/               # Framework adapters
    ├── __init__.py             # Integration exports
    └── langchain.py            # LangChain StructuredTool (NEW: async ainvoke support)

tests/                          # Test suite (mirrors src/)
├── conftest.py                 # Shared fixtures (NEW: async fixtures)
├── test_discovery.py           # Discovery tests (NEW: async, multi-source, plugin tests)
├── test_parser.py              # Parser tests (NEW: plugin manifest tests)
├── test_models.py              # Dataclass tests (NEW: SkillSource, PluginManifest tests)
├── test_processors.py          # Processor tests (NEW: base directory injection tests)
├── test_manager.py             # Manager tests (NEW: async, multi-source, path resolution tests)
├── test_path_utils.py          # NEW: Path validation tests (security-critical)
├── test_langchain.py           # LangChain integration (NEW: async ainvoke tests)
└── fixtures/
    └── skills/                 # Test SKILL.md files
        ├── valid-skill/
        ├── nested/             # NEW: Nested structure tests
        │   └── group/
        │       └── skill/
        └── plugins/            # NEW: Plugin test fixtures
            └── test-plugin/
                └── .claude-plugin/
                    └── plugin.json

examples/                       # Usage examples
├── basic_usage.py              # Standalone usage (NEW: async examples)
├── langchain_agent.py          # LangChain integration (NEW: async agent example)
└── skills/                     # Example skills
```

**Structure Decision**: Single Python library structure (Option 1) with framework-agnostic core and optional integrations. This matches the existing v0.1 implementation and will be extended with:
- New `path_utils.py` module for secure path resolution
- Extended `models.py` with SkillSource and PluginManifest dataclasses
- Async methods added to existing modules (discovery, manager, langchain integration)
- New test fixtures for plugins and nested structures

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations detected. This section is not applicable.
