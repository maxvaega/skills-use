# Implementation Plan: skillkit v0.1 MVP - Core Functionality & LangChain Integration

**Branch**: `001-mvp-langchain-core` | **Date**: November 4, 2025 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-mvp-langchain-core/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

The v0.1 MVP delivers a Python library that implements Anthropic's Agent Skills functionality with a vertical slice approach. Core features include: (1) skill discovery from `.claude/skills/` directory, (2) YAML frontmatter parsing with validation, (3) progressive disclosure pattern (metadata-first loading), (4) skill invocation with $ARGUMENTS substitution and base directory injection, (5) LangChain StructuredTool integration (sync only), (6) 70% test coverage, and (7) PyPI publishing with minimal documentation.

**Technical Approach**: Framework-agnostic core with zero dependencies (stdlib + PyYAML only), optional LangChain integration via `pip install skillkit[langchain]`, frozen dataclasses with slots for memory efficiency, lazy content loading via `@cached_property`, string.Template for secure $ARGUMENTS substitution, comprehensive exception hierarchy with graceful degradation during discovery and strict validation during invocation.

## Technical Context

**Language/Version**: Python 3.9+ (minimum), Python 3.10+ recommended for optimal memory efficiency (slots + cached_property)
**Primary Dependencies**:
- Core: PyYAML 6.0+ (YAML parsing), Python stdlib (pathlib, dataclasses, functools, typing, re, logging)
- LangChain integration (optional): langchain-core 0.1.0+, pydantic 2.0+
- Development: pytest 7.0+, pytest-cov 4.0+, ruff 0.1.0+, mypy 1.0+

**Storage**: Filesystem-based (`.claude/skills/` directory with SKILL.md files)
**Testing**: pytest with 70% coverage target (v0.1), parametrized tests for edge cases, fixtures in conftest.py
**Target Platform**: Cross-platform (Linux, macOS, Windows) - regex patterns handle both Unix (\n) and Windows (\r\n) line endings
**Project Type**: Python library (single package structure)
**Performance Goals**:
- Discovery: <500ms for 10 skills (metadata only, ~5-10ms per skill for YAML parsing)
- Invocation: <10-25ms overhead (file I/O ~10-20ms + string processing ~1-5ms)
- Memory: ~2-2.5MB for 100 skills with 10% usage (80% reduction vs eager loading)

**Constraints**:
- Zero framework dependencies in core modules (framework-agnostic design)
- Sync-only for v0.1 (async deferred to v0.2)
- 1MB size limit on skill arguments (prevents resource exhaustion)
- UTF-8 encoding enforced throughout (security requirement)

**Scale/Scope**:
- Target: 10-20 skills for v0.1 users (acceptable without optimization)
- Design supports: 100+ skills via progressive disclosure pattern
- Test coverage: 70% for v0.1 (unit + integration), 90% target for v1.0

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Status**: Constitution file is a template placeholder (not yet customized for this project). Applying general Python library best practices as implicit constitution:

### Implicit Principles Applied

1. **Library-First Design** ✅
   - Core functionality (`skillkit.core`) has zero framework dependencies
   - Framework integrations cleanly separated (`skillkit.integrations`)
   - Independently testable and documented
   - Clear purpose: Enable LLM agents to discover and use packaged expertise

2. **Progressive Disclosure** ✅
   - Metadata-first loading pattern (lazy content loading via `@cached_property`)
   - 80% memory reduction vs eager loading
   - Enables browsing 100+ skills without loading full content

3. **Test-First Approach** ✅
   - 70% coverage target with pytest
   - Unit tests for discovery, parsing, invocation
   - Integration test for LangChain end-to-end workflow
   - Parametrized tests for 15+ edge cases

4. **Error Handling** ✅
   - Comprehensive exception hierarchy (11 exception types)
   - Graceful degradation during discovery (log errors, continue)
   - Strict validation during invocation (raise specific exceptions)
   - NullHandler configuration per Python library standards

5. **Security & Safety** ✅
   - `yaml.safe_load()` prevents code execution
   - `string.Template` prevents attribute access vulnerabilities
   - 1MB size limit on arguments
   - Suspicious pattern detection (9 patterns including XSS, YAML injection)

6. **Simplicity & YAGNI** ✅
   - Sync-only for v0.1 (async deferred to v0.2)
   - Single skill directory (multiple paths deferred to v0.3)
   - Flat directory structure (nested deferred to v0.3)
   - 70% coverage sufficient for MVP (90% deferred to v1.0)

**Conclusion**: No constitution violations. Design aligns with Python library best practices (2024-2025 standards). Proceed to Phase 0.

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
skillkit/
├── src/
│   └── skillkit/
│       ├── __init__.py           # Public API exports + NullHandler configuration
│       ├── core/
│       │   ├── __init__.py       # Core module exports
│       │   ├── discovery.py      # SkillDiscovery: filesystem scanning
│       │   ├── parser.py         # SkillParser: YAML frontmatter parsing
│       │   ├── models.py         # SkillMetadata, Skill dataclasses
│       │   ├── manager.py        # SkillManager: orchestration layer
│       │   ├── processors.py     # ContentProcessor strategy pattern
│       │   └── exceptions.py     # Custom exceptions hierarchy
│       ├── integrations/
│       │   ├── __init__.py       # Integration module exports
│       │   └── langchain.py      # LangChain StructuredTool adapter
│       └── py.typed              # PEP 561 marker for type hints
├── tests/
│   ├── conftest.py               # Shared fixtures (fixtures_dir, skills_dir)
│   ├── test_discovery.py         # SkillDiscovery tests (happy path, empty dir)
│   ├── test_parser.py            # SkillParser tests (valid, missing fields, malformed YAML)
│   ├── test_models.py            # Dataclass tests (validation, immutability)
│   ├── test_processors.py        # ContentProcessor tests (parametrized edge cases)
│   ├── test_manager.py           # SkillManager tests (discover, list, get, load, invoke)
│   ├── test_langchain.py         # LangChain integration tests (end-to-end)
│   └── fixtures/
│       └── skills/               # Test SKILL.md files
│           ├── valid-skill/SKILL.md
│           ├── missing-name-skill/SKILL.md
│           ├── invalid-yaml-skill/SKILL.md
│           └── arguments-test-skill/SKILL.md
├── examples/
│   ├── basic_usage.py            # Standalone usage example
│   └── langchain_agent.py        # LangChain integration example
├── .docs/                        # Project documentation (PRD, TECH_SPECS, etc.)
├── pyproject.toml                # Package configuration (PEP 621)
├── README.md                     # Installation, quick start, examples
├── LICENSE                       # MIT license
└── .gitignore                    # Python-standard ignores
```

**Structure Decision**: Single Python library package structure (Option 1). Rationale:
- Framework-agnostic core in `src/skillkit/core/` (zero dependencies)
- Optional integrations in `src/skillkit/integrations/` (framework-specific)
- Tests mirror source structure for clarity
- Examples demonstrate standalone + framework usage
- PEP 621 `pyproject.toml` for modern Python packaging

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**Status**: No constitution violations detected. All design decisions align with simplicity principles:
- Zero unnecessary abstractions (direct filesystem operations, no ORM/repository pattern)
- Standard library prioritized (string.Template, dataclasses, pathlib)
- Strategy pattern justified by extensibility requirements (processors can be composed)
- Exception hierarchy justified by Python library standards (specific error handling)

No complexity justification required.

---

## Phase 0: Research (COMPLETE)

**Status**: ✅ All research documented in [research.md](./research.md)

The research phase identified and resolved 8 critical architectural decisions:

1. **Progressive Disclosure Pattern**: Two-tier dataclass architecture (SkillMetadata + Skill) with lazy content loading via `@cached_property`, achieving 80% memory reduction
2. **Framework-Agnostic Core**: Zero dependencies in `core/`, optional framework integrations in `integrations/`
3. **$ARGUMENTS Substitution**: `string.Template` with `$$ARGUMENTS` escaping, input validation, suspicious pattern detection
4. **Error Handling Strategy**: Graceful degradation during discovery, strict exceptions during invocation, 11-exception hierarchy
5. **YAML Frontmatter Parsing**: `yaml.safe_load()` with cross-platform line ending support, detailed error messages, typo detection
6. **LangChain Integration**: StructuredTool with closure capture pattern, sync-only v0.1, dual sync/async in v0.2
7. **Testing Strategy**: 70% coverage with parametrized tests, fixtures in conftest.py, pytest-cov measurement
8. **Synchronous-Only Implementation**: Async deferred to v0.2 (file I/O overhead negligible vs LLM latency)

**Key Technical Decisions**:
- Python 3.10+ recommended (full slots support), 3.9 supported (partial slots)
- Memory optimization: `frozen=True, slots=True` dataclasses (~60% reduction per instance)
- Security: `string.Template` prevents code execution, 1MB size limit, 9 suspicious patterns detected
- Cross-platform: Regex pattern `[\\r\\n]+` handles Unix/Windows line endings
- Performance: <500ms discovery for 10 skills, <10-25ms invocation overhead

All NEEDS CLARIFICATION items resolved. Ready for Phase 1 design artifacts.

---

## Phase 1: Design & Contracts

**Objective**: Generate data model, API contracts, and quickstart guide based on research findings.

### Phase 1 Deliverables

1. **data-model.md**: Entity definitions, relationships, validation rules, state transitions
2. **contracts/public-api.md**: Complete public API specifications with type signatures
3. **quickstart.md**: Developer onboarding guide with installation and usage examples

### Key Entities (from research.md)

**SkillMetadata** (Tier 1 - Lightweight)
```python
@dataclass(frozen=True, slots=True)
class SkillMetadata:
    name: str
    description: str
    skill_path: Path
    allowed_tools: tuple[str, ...] = field(default_factory=tuple)
```

**Skill** (Tier 2 - Full with lazy content)
```python
@dataclass(frozen=True, slots=True)  # slots=True requires Python 3.10+
class Skill:
    metadata: SkillMetadata
    base_directory: Path
    _processor: CompositeProcessor = field(init=False, repr=False)

    @cached_property
    def content(self) -> str:
        """Lazy load content only when accessed."""
```

**SkillManager** (Orchestration)
- Methods: `discover()`, `list_skills()`, `get_skill(name)`, `load_skill(name)`, `invoke_skill(name, args)`
- Discovery: Graceful degradation (log errors, continue)
- Invocation: Strict validation (raise specific exceptions)

**ContentProcessor** (Strategy Pattern)
- Base: Abstract processor interface
- BaseDirectoryProcessor: Injects base directory context
- ArgumentSubstitutionProcessor: Handles $ARGUMENTS with `string.Template`
- CompositeProcessor: Chains processors in order

**Exception Hierarchy** (11 exceptions)
```
SkillsUseError (base)
├── SkillParsingError
│   ├── InvalidYAMLError
│   ├── MissingRequiredFieldError
│   └── InvalidFrontmatterError
├── SkillNotFoundError
├── SkillInvocationError
│   ├── ArgumentProcessingError
│   └── ContentLoadError
└── SkillSecurityError
    ├── SuspiciousInputError
    └── SizeLimitExceededError
```

### API Surface (contracts/public-api.md)

**Core API** (skillkit.core)
- `SkillManager(skills_dir: Path | None = None)` - Main entry point
- `SkillMetadata` - Dataclass (name, description, skill_path, allowed_tools)
- `Skill` - Dataclass (metadata, base_directory, content property)
- All exceptions from hierarchy

**LangChain Integration** (skillkit.integrations.langchain)
- `create_langchain_tools(manager: SkillManager) -> List[StructuredTool]`
- `SkillInput` - Pydantic model for tool input schema

### Quickstart Requirements (quickstart.md)

1. **Installation**: `pip install skillkit` and `pip install skillkit[langchain]`
2. **Creating Skills**: SKILL.md format with YAML frontmatter examples
3. **Standalone Usage**: Basic SkillManager usage without frameworks
4. **LangChain Integration**: End-to-end agent example
5. **Common Patterns**: $ARGUMENTS substitution, error handling, logging configuration
6. **Troubleshooting**: Common issues and solutions

---

## Phase 2: Task Generation (DEFERRED)

**Status**: Not created by `/speckit.plan` command. Use `/speckit.tasks` to generate detailed implementation tasks.

The tasks.md file will break down implementation into dependency-ordered, actionable tasks across:
- Core modules (discovery, parser, models, manager, processors, exceptions)
- LangChain integration
- Test suite (unit + integration)
- Documentation (README, examples)
- Packaging (pyproject.toml, distribution)

Expected task count: ~25-35 tasks over 4-week timeline.

---

## Implementation Timeline

**Week 1**: Core foundation
- Create project structure
- Implement models.py + exceptions.py
- Implement discovery.py + parser.py with tests
- Achieve: Skill discovery and metadata parsing working

**Week 2**: Invocation and processing
- Implement processors.py (ContentProcessor hierarchy)
- Implement manager.py orchestration layer
- Add comprehensive tests (parametrized edge cases)
- Achieve: End-to-end skill invocation working

**Week 3**: LangChain integration
- Implement integrations/langchain.py
- Create LangChain integration tests
- Write examples (basic_usage.py, langchain_agent.py)
- Achieve: LangChain agents can use skills

**Week 4**: Documentation and distribution
- Write README.md with installation and examples
- Configure pyproject.toml
- Verify 70% test coverage
- Publish to PyPI
- Achieve: Library publicly available and documented

---

## Success Metrics

**Functional Validation**:
- ✅ All 50 functional requirements from spec.md satisfied
- ✅ 6 user stories with acceptance scenarios pass
- ✅ Edge cases handled gracefully with clear error messages

**Performance Validation**:
- ✅ Discovery: <500ms for 10 skills (metadata only)
- ✅ Invocation: <10-25ms overhead (file I/O + processing)
- ✅ Memory: ~2-2.5MB for 100 skills with 10% usage

**Quality Validation**:
- ✅ 70% test coverage measured with pytest-cov
- ✅ All tests passing with pytest
- ✅ Type checking passes with mypy in strict mode
- ✅ Linting passes with ruff

**Distribution Validation**:
- ✅ Package installable via `pip install skillkit`
- ✅ README example runs without modification
- ✅ LangChain integration example demonstrates end-to-end workflow
- ✅ Published to PyPI with MIT license

---

## Risk Mitigation

**Risk 1: LangChain API Changes**
- Mitigation: Pin langchain-core version, use stable StructuredTool interface
- Impact: Low (StructuredTool is stable since v0.1)

**Risk 2: Cross-Platform Line Ending Issues**
- Mitigation: Regex pattern `[\\r\\n]+` tested on Unix + Windows
- Impact: Low (pattern handles both \n and \r\n)

**Risk 3: Memory Usage on Python 3.9**
- Mitigation: Document Python 3.10+ recommendation, 3.9 fallback acceptable
- Impact: Low (25% memory overhead on 3.9 still 80% reduction vs eager loading)

**Risk 4: Scope Creep**
- Mitigation: Strict adherence to vertical slice plan, defer all non-critical features
- Impact: Medium (requires discipline to reject feature additions)

**Risk 5: Test Coverage Target**
- Mitigation: Focus on critical paths (discovery, parsing, invocation), defer edge case tests
- Impact: Low (70% coverage acceptable for MVP)

---

## Post-Implementation

After `/speckit.implement` completes:

1. **Manual verification**: Run examples/langchain_agent.py with real LLM
2. **Coverage report**: `pytest --cov=skillkit --cov-report=html`
3. **Type checking**: `mypy src/skillkit --strict`
4. **Linting**: `ruff check src/skillkit`
5. **Build package**: `python -m build`
6. **Test installation**: `pip install dist/skillkit-0.1.0-*.whl`
7. **Publish to PyPI**: `python -m twine upload dist/*`

**Iteration to v0.2**: Gather user feedback, implement async support, enhance error handling
