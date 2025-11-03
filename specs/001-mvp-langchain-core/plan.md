# Implementation Plan: Skills-use v0.1 MVP - Core Functionality & LangChain Integration

**Branch**: `001-mvp-langchain-core` | **Date**: November 3, 2025 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-mvp-langchain-core/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This MVP implements the core skills-use library functionality: discovering skills from `.claude/skills/` directory, parsing SKILL.md files with YAML frontmatter, managing skill metadata with progressive disclosure pattern (load metadata first, defer content loading until invocation), and integrating with LangChain framework via StructuredTool objects. The library enables LLM agents to autonomously discover and utilize packaged expertise (skills) with minimal context window consumption.

## Technical Context

**Language/Version**: Python 3.9+ (minimum supported version)
**Primary Dependencies**: PyYAML (YAML frontmatter parsing), LangChain-core (StructuredTool integration), Pydantic 2.0+ (schema validation)
**Storage**: Filesystem-based (`.claude/skills/` directory with SKILL.md files)
**Testing**: pytest, pytest-cov (70% coverage target for v0.1)
**Target Platform**: Cross-platform (Linux, macOS, Windows) - Python package distributed via PyPI
**Project Type**: Single Python library package
**Performance Goals**:
  - Discovery: <500ms for 10 skills metadata loading
  - Invocation: <10ms overhead (excluding file I/O and LLM time)
**Constraints**:
  - Synchronous operations only (async deferred to v0.2)
  - Single skills directory (~/.claude/skills/) - custom paths deferred to v0.3
  - Flat directory structure only (nested directories deferred to v0.3)
**Scale/Scope**:
  - Target: 10-100 skills in typical deployment
  - Progressive disclosure ensures scalability
  - Minimal memory footprint (~1-5KB per skill metadata)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: ✅ PASS (Constitution not yet defined - using default Python library best practices)

Since the project constitution file is still a template, applying standard Python library development principles:

1. ✅ **Library-First Design**: Core functionality is framework-agnostic (core/ modules), framework integrations separate (integrations/)
2. ✅ **Clear API Contract**: Public API exposed via `__init__.py`, internal modules not exposed
3. ✅ **Test-First Approach**: 70% coverage minimum, all critical paths tested before v0.1 release
4. ✅ **Progressive Disclosure**: Metadata loaded upfront, content on-demand (architectural principle)
5. ✅ **Minimal Dependencies**: Core depends only on stdlib + PyYAML; framework deps are optional extras

**No violations or exceptions required for v0.1 MVP.**

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
skills-use/
├── src/
│   └── skills_use/
│       ├── __init__.py              # Public API exports (SkillManager, models, exceptions)
│       ├── core/
│       │   ├── __init__.py
│       │   ├── discovery.py         # SkillDiscovery class - filesystem scanning
│       │   ├── parser.py            # SkillParser class - YAML + markdown parsing
│       │   ├── models.py            # SkillMetadata, Skill dataclasses
│       │   ├── manager.py           # SkillManager - orchestration layer
│       │   └── invocation.py        # process_skill_content() - $ARGUMENTS substitution
│       ├── integrations/
│       │   ├── __init__.py
│       │   └── langchain.py         # create_langchain_tools() - LangChain adapter
│       └── exceptions.py            # SkillsUseError, SkillParsingError, etc.
├── tests/
│   ├── __init__.py
│   ├── test_discovery.py            # SkillDiscovery tests
│   ├── test_parser.py               # SkillParser tests
│   ├── test_invocation.py           # Invocation logic tests
│   ├── test_manager.py              # SkillManager integration tests
│   ├── test_langchain.py            # LangChain integration tests
│   └── fixtures/
│       └── skills/                  # Test SKILL.md samples
│           ├── valid-skill/
│           ├── missing-name-skill/
│           └── invalid-yaml-skill/
├── pyproject.toml                   # Package metadata, dependencies, build config
├── README.md                        # Installation, quick start, examples
├── LICENSE                          # MIT license
└── .gitignore
```

**Structure Decision**: Single Python library package (Option 1). This is a pure library with no CLI, web frontend, or mobile components. The `src/` layout follows modern Python packaging standards (PEP 420), enabling `pip install skills-use` to work correctly. Core logic is isolated from framework integrations to maintain independence and testability.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No violations tracked.** All design decisions align with Python library best practices and v0.1 MVP scope constraints.

---

## Phase 0: Research & Outline

**Status**: ✅ Complete

**Deliverable**: [research.md](./research.md)

### Key Decisions Documented

1. **Progressive Disclosure Pattern**: Metadata-first loading, content on-demand (Research Decision 1)
2. **Framework-Agnostic Core**: Zero framework dependencies in core modules (Research Decision 2)
3. **$ARGUMENTS Substitution**: Replace all occurrences or append if missing (Research Decision 3)
4. **Error Handling Strategy**: Graceful during discovery, strict during invocation (Research Decision 4)
5. **YAML Parsing**: Regex + yaml.safe_load() for security (Research Decision 5)
6. **LangChain Integration**: StructuredTool with single string parameter (Research Decision 6)
7. **Testing Strategy**: 70% coverage target with unit + integration tests (Research Decision 7)
8. **Sync-Only v0.1**: Async deferred to v0.2 for faster delivery (Research Decision 8)

### Technologies Selected

- **Core**: Python 3.9+, PyYAML 6.0+, pathlib (stdlib)
- **Integration**: LangChain-core 0.1+, Pydantic 2.0+
- **Testing**: pytest 7.0+, pytest-cov 4.0+
- **Linting/Formatting**: black, ruff, mypy

### Open Questions Resolved

All 7 open points from PRD resolved:
- OP-1 ($ARGUMENTS): Replace all or append
- OP-2 (Multiple paths): Deferred to v0.3
- OP-3 (Tool restrictions): Deferred to v0.2
- OP-4 (Async): v0.1 sync-only
- OP-5 (Performance): <500ms acceptable
- OP-6 (Frameworks): LangChain only for v0.1
- OP-7 (Error handling): Basic exceptions sufficient

---

## Phase 1: Design & Contracts

**Status**: ✅ Complete

**Deliverables**:
- [data-model.md](./data-model.md) - Entity models and relationships
- [contracts/public-api.md](./contracts/public-api.md) - API contract specification
- [quickstart.md](./quickstart.md) - Developer onboarding guide
- Updated agent context (CLAUDE.md)

### Core Entities Defined

1. **SkillMetadata**: Lightweight metadata (name, description, path, allowed_tools)
2. **Skill**: Full skill object (metadata + content + base_directory)
3. **SkillDiscovery**: Filesystem scanner
4. **SkillParser**: YAML frontmatter + markdown parser
5. **SkillManager**: Orchestration layer
6. **SkillInput**: Pydantic schema for LangChain tools

### API Surface

**Public Classes**:
- `SkillManager` - Main entry point
- `SkillMetadata` - Metadata model
- `Skill` - Full skill model
- Exceptions: `SkillsUseError`, `SkillParsingError`, `SkillNotFoundError`, `SkillInvocationError`

**Public Functions**:
- `create_langchain_tools()` - Bulk tool creation
- `create_langchain_tool_from_skill()` - Single tool creation

### Implementation Phases

**Week 1: Core Foundation** (24 hours)
- models.py, exceptions.py (3 hours)
- discovery.py + tests (4 hours)
- parser.py + tests (6 hours)
- manager.py + tests (4 hours)
- invocation.py + tests (6 hours)
- __init__.py (1 hour)

**Week 2: LangChain Integration** (12 hours)
- integrations/langchain.py + tests (8 hours)
- Integration testing (4 hours)

**Week 3: Testing & Examples** (10 hours)
- Comprehensive testing to 70% coverage (6 hours)
- Example skills (4 hours)

**Week 4: Documentation & Publishing** (14 hours)
- README.md (6 hours)
- PyPI preparation (4 hours)
- Publishing + announcement (4 hours)

### Constitution Check (Post-Design)

✅ **Re-evaluated**: All gates still pass
- Library-first design maintained
- Clear API contract defined
- Test-first approach documented
- Progressive disclosure preserved
- Minimal dependencies confirmed

No new violations introduced during design phase.

---

## Next Steps

### For Implementation (/speckit.implement)

**Prerequisites**: All Phase 0 and Phase 1 artifacts complete ✅

**Ready to proceed with**:
1. Project structure creation (`src/skills_use/`, `tests/`)
2. Core module implementation following TECH_SPECS.md
3. Test-driven development with 70% coverage target
4. LangChain integration and end-to-end testing

### For Task Generation (/speckit.tasks)

**Command**: `/speckit.tasks` will generate detailed task breakdown based on this plan

**Expected Output**: `tasks.md` with dependency-ordered implementation tasks

---

**Plan Status**: ✅ Complete (Phase 0 + Phase 1)
**Implementation Ready**: Yes
**Next Command**: `/speckit.tasks` to generate implementation tasks
