# skillkit

**skillkit** is a Python library that implements Anthropic's Agent Skills functionality, enabling LLM-powered agents to autonomously discover and utilize packaged expertise. The library provides:

- Multi-source skill discovery from personal directories, project directories, and plugins
- SKILL.md parsing with YAML frontmatter validation
- Progressive disclosure pattern (metadata loading → on-demand content)
- Framework integrations (LangChain, LlamaIndex, CrewAI, Haystack, Google ADK)
- Security features (tool restrictions, path traversal prevention)
- Model-agnostic design supporting Claude, GPT, Gemini, and open-source LLMs

## Development Approach

This project follows a **Vertical Slice MVP strategy** to deliver working functionality quickly:

- **v0.1 (Released)**: Core functionality + LangChain integration (sync only)
- **v0.2 (Released)**: Async support + multi-source discovery + plugin integration
- **v0.3 (Planned)**: Script execution + tool restriction enforcement + additional framework integrations
- **v1.0 (Planned)**: Production polish + comprehensive documentation + 90% test coverage

### Current Focus (v0.2)

The v0.2 release adds enterprise-grade features:
1. **Async support**: `adiscover()` and `ainvoke_skill()` methods for concurrent operations
2. **Multi-source discovery**: Project dirs, Anthropic config, plugins, custom paths with priority resolution
3. **Plugin ecosystem**: Full MCPB manifest support with namespaced skill access (`plugin:skill-name`)
4. **Nested structures**: Discover skills up to 5 levels deep in directory hierarchies
5. **Secure file resolution**: Path traversal prevention and reference validation
6. **LangChain async**: Full async/await support in LangChain integration
7. **Backward compatibility**: All v0.1 APIs remain unchanged

**What's deferred to v0.3+**: Script execution, tool restriction enforcement, additional framework integrations (LlamaIndex, CrewAI, Haystack), advanced argument schemas, CI/CD pipeline, 90% test coverage.

## Key Architectural Decisions

### Core Architecture (v0.1)
The foundation is built on 8 critical decisions (see `specs/001-mvp-langchain-core/research.md` for rationale):

1. **Progressive Disclosure Pattern**: Two-tier architecture (SkillMetadata + Skill) with lazy content loading achieves 80% memory reduction
2. **Framework-Agnostic Core**: Zero dependencies in core modules; optional framework integrations via extras
3. **$ARGUMENTS Substitution**: `string.Template` for security + standard escaping (`$$ARGUMENTS`), 1MB size limit, suspicious pattern detection
4. **Error Handling**: Graceful degradation during discovery, strict exceptions during invocation, 11-exception hierarchy
5. **YAML Parsing**: `yaml.safe_load()` with cross-platform support, detailed error messages, typo detection
6. **LangChain Integration**: StructuredTool with closure capture pattern
7. **Testing**: 70% coverage with pytest, parametrized tests, fixtures in conftest.py
8. **Performance-First Design**: Optimized for LLM-bound workflows

### v0.2 Enhancements
Additional architectural patterns added in v0.2:

1. **Async-First I/O**: Full async/await support with `aiofiles` for non-blocking file operations, enabling concurrent skill discovery and invocation
2. **Multi-Source Resolution**: Priority-based discovery (project:100, config:50, plugins:10, custom:5) with fully qualified names (`plugin:skill-name`)
3. **Plugin Architecture**: MCPB manifest parsing with namespace isolation and conflict resolution
4. **Secure Path Resolution**: Traversal prevention, symlink validation, and file reference security
5. **Backward Compatibility**: All v0.1 sync APIs preserved; async methods are additive (`discover()` + `adiscover()`)

**Security Validated**: All decisions reviewed against 2024-2025 Python library best practices (scores 8-9.5/10).

## Documentation

Main project documentation is located in the `.docs/` directory:

### `.docs/MVP_VERTICAL_SLICE_PLAN.md`
The **implementation roadmap** for the project. Contains:
- Vertical slice philosophy and rationale
- 4-week MVP plan with week-by-week breakdown
- Critical path requirements (CP-1 through CP-7)
- Post-launch iteration roadmap (v0.2, v0.3, v1.0)
- Success metrics and validation criteria
- Risk mitigation strategies
- Comparison between original horizontal approach vs vertical slice

### `.docs/PRD_skillkit_LIBRARY.md`
The **comprehensive Product Requirements Document**. Contains:
- Complete functional requirements (FR-1 through FR-9)
- Technical specifications (TS-1 through TS-6)
- Integration requirements for all frameworks (IR-1 through IR-6)
- Distribution and deployment requirements (DR-1 through DR-12)
- Error handling specifications (EH-1 through EH-3)
- Testing requirements (TR-1 through TR-5)
- Open points requiring resolution (OP-1 through OP-7)
- Example skills and plugin structures

### `.docs/TECH_SPECS.md`
The **technical architecture specification** for v0.1. Contains:
- Detailed module structure and file organization
- Core data models (SkillMetadata, Skill classes)
- API signatures for all public methods
- Exception hierarchy and error handling
- Dependencies and version requirements
- Code examples and usage patterns
- Key design decisions and rationale
- Testing strategy and performance considerations

### `.docs/SKILL format specification`
- Full specification for skills and SKILL.md

### `.specify/` folder
This project was developed using speckit method. all development phases have been documented thoroughly inside `.specify/` folder

## Project Status

**Current Phase**: ✅ v0.2.0 RELEASED

**v0.1 Completed**:
- ✅ Core functionality (discovery, parsing, models, manager, processors)
- ✅ LangChain integration with StructuredTool (sync)
- ✅ Progressive disclosure pattern with lazy loading
- ✅ YAML frontmatter parsing and validation
- ✅ Argument substitution with security features
- ✅ 70%+ test coverage with comprehensive test suite
- ✅ Published to PyPI

**v0.2 Completed**:
- ✅ Full async/await support (`adiscover()`, `ainvoke_skill()`)
- ✅ Multi-source skill discovery (project, Anthropic config, plugins, custom paths)
- ✅ Plugin ecosystem with MCPB manifest support
- ✅ Priority-based conflict resolution
- ✅ Fully qualified skill names (`plugin:skill-name`)
- ✅ Nested directory structures (up to 5 levels)
- ✅ Secure file path resolution with traversal prevention
- ✅ LangChain async integration
- ✅ Updated examples (async_usage.py, multi_source.py, file_references.py)
- ✅ Backward compatible with v0.1

**Next Steps**:
- Plan v0.3: Script execution, tool restrictions, framework integrations
- Gather community feedback and feature requests
- Improve documentation with more real-world examples

## Development Environment

This project uses Python Python 3.10+ .

**Virtual Environment Setup**:
```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**Development Commands**:
- Run examples:
  - `python examples/basic_usage.py` (sync and async patterns)
  - `python examples/async_usage.py` (FastAPI integration)
  - `python examples/langchain_agent.py` (sync and async LangChain)
  - `python examples/multi_source.py` (multi-source discovery)
  - `python examples/file_references.py` (secure file resolution)
- Run tests: `pytest` (70%+ coverage)
- Run specific test markers: `pytest -m async` or `pytest -m integration`
- Lint code: `ruff check src/skillkit`
- Format code: `ruff format src/skillkit`
- Type check: `mypy src/skillkit --strict`

## Project Structure

### Repository Current Structure (Implemented)

```
skillkit/
├── src/
│   └── skillkit/
│       ├── __init__.py             # Public API exports + NullHandler
│       ├── core/                   # Framework-agnostic core
│       │   ├── __init__.py         # Core module exports
│       │   ├── discovery.py        # SkillDiscovery: filesystem scanning
│       │   ├── parser.py           # SkillParser: YAML parsing
│       │   ├── models.py           # SkillMetadata, Skill dataclasses
│       │   ├── manager.py          # SkillManager: orchestration
│       │   ├── processors.py       # ContentProcessor strategies
│       │   └── exceptions.py       # Exception hierarchy
│       ├── integrations/           # Framework-specific adapters
│       │   ├── __init__.py         # Integration exports
│       │   └── langchain.py        # LangChain StructuredTool adapter
│       └── py.typed                # PEP 561 type hints marker
├── tests/                          # Test suite (mirrors src/)
│   ├── conftest.py                 # Shared fixtures
│   ├── test_discovery.py           # Discovery tests
│   ├── test_parser.py              # Parser tests
│   ├── test_models.py              # Dataclass tests
│   ├── test_processors.py          # Processor tests
│   ├── test_manager.py             # Manager tests
│   ├── test_langchain.py           # LangChain integration tests
│   └── fixtures/
│       └── skills/                 # Test SKILL.md files
│           ├── valid-skill/
│           ├── missing-name-skill/
│           ├── invalid-yaml-skill/
│           └── arguments-test-skill/
├── examples/                       # Usage examples
│   ├── basic_usage.py              # Standalone usage
│   └── langchain_agent.py          # LangChain integration
│   └── skills/                     # Examples skills folders
├── pyproject.toml                  # Package configuration (PEP 621)
├── README.md                       # Installation + quick start
├── LICENSE                         # MIT license
└── .gitignore                      # Python-standard ignores
```

**Key Design Decisions**:
- **Framework-agnostic core**: `src/skillkit/core/` has zero dependencies (stdlib + PyYAML only)
- **Optional integrations**: `src/skillkit/integrations/` requires framework-specific extras
- **Test structure**: Mirrors source for clarity (`test_*.py` for each module)
- **Modern packaging**: PEP 621 `pyproject.toml` with optional dependencies (`[langchain]`, `[dev]`)

### Python Version
- **Minimum**: Python 3.10 (supported with minor memory trade-offs)
- **Recommended**: Python 3.10+ (optimal memory efficiency via slots + cached_property)
- **Memory impact**: Python 3.10+ provides 60% memory reduction per instance via `slots=True` compared to Python 3.9
- **Important**: always run python commands inside venv for correct python library management

### Core Dependencies
- **PyYAML 6.0+**: YAML frontmatter parsing with `yaml.safe_load()` security
- **aiofiles 23.0+**: Async file I/O for non-blocking operations (v0.2+)
- **Python stdlib**: pathlib, dataclasses, functools, typing, re, logging, string.Template, asyncio

### Optional Dependencies
- **langchain-core 0.1.0+**: StructuredTool integration with async support (install: `pip install skillkit[langchain]`)
- **pydantic 2.0+**: Input schema validation (explicit dependency despite being transitive from langchain-core)

### Development Dependencies
- **pytest 7.0+**: Test framework with 70% coverage target
- **pytest-cov 4.0+**: Coverage measurement
- **ruff 0.1.0+**: Fast linting and formatting (replaces black + flake8)
- **mypy 1.0+**: Type checking in strict mode

### Storage & Distribution
- **Storage**: Filesystem-based (`.claude/skills/` directory with SKILL.md files)
- **Packaging**: PEP 621 `pyproject.toml` with hatchling or setuptools 61.0+
- **Distribution**: PyPI (`pip install skillkit`)

### Performance Characteristics
- **Discovery**: ~5-10ms per skill (YAML parsing dominates)
- **Invocation**: ~10-25ms overhead (file I/O ~10-20ms + processing ~1-5ms)
- **Memory**: ~2-2.5MB for 100 skills with 10% usage (80% reduction vs eager loading)

## Changelog

### v0.2.0 (Released)
- **Async Support**: Full async/await implementation with `adiscover()` and `ainvoke_skill()`
- **Multi-Source Discovery**: Project dirs, Anthropic config, plugins, custom paths with priority resolution
- **Plugin Ecosystem**: MCPB manifest support with namespaced skill access
- **Nested Directories**: Discover skills up to 5 levels deep
- **Secure Path Resolution**: Traversal prevention and reference validation
- **LangChain Async**: Full async integration for LangChain agents
- **New Examples**: async_usage.py, multi_source.py, file_references.py
- **Backward Compatible**: All v0.1 APIs preserved

### v0.1.0 (Released)
- **Core Functionality**: Skill discovery, parsing, and invocation
- **Progressive Disclosure**: Lazy loading with 80% memory reduction
- **LangChain Integration**: StructuredTool adapter (sync only)
- **Security Features**: YAML safe loading, argument substitution validation
- **Testing**: 70%+ coverage with pytest
- **Documentation**: Comprehensive README and examples
- **PyPI Distribution**: Published as `pip install skillkit`

## Active Technologies
- **Python**: 3.10+ (minimum for full async support)
- **Core**: PyYAML 6.0+, aiofiles 23.0+
- **Integrations**: langchain-core 0.1.0+, pydantic 2.0+
- **Storage**: Filesystem-based (`.claude/skills/` directories, `.claude-plugin/plugin.json` manifests)
- **Testing**: pytest 7.0+, pytest-cov 4.0+, pytest-asyncio 0.21+
- **Quality**: ruff 0.1.0+, mypy 1.0+

## v0.2 Implementation Notes

**Branch**: `001-v0-2-async-discovery-files` (merged to main)

**Key Changes**:
1. Added `aiofiles` dependency for async file I/O
2. Implemented async methods across all core modules (discovery, parser, manager)
3. Enhanced SkillDiscovery with multi-source support and priority resolution
4. Added plugin manifest parsing and namespace management
5. Implemented secure file path resolution with traversal prevention
6. Extended LangChain integration with async support
7. Added comprehensive async tests with pytest-asyncio
8. Updated all examples to demonstrate new capabilities

**Performance Impact**:
- Async discovery: ~40-60% faster for 100+ skills (concurrent file I/O)
- Memory: No change from v0.1 (still ~2-2.5MB for 100 skills)
- Backward compatibility: Zero breaking changes

## Quick Reference for AI Agents

### Key Files and Locations
- **Main source**: `src/skillkit/core/` (discovery.py, parser.py, models.py, manager.py, processors.py)
- **Integrations**: `src/skillkit/integrations/langchain.py`
- **Tests**: `tests/` (mirrors src/ structure)
- **Examples**: `examples/` (basic_usage.py, async_usage.py, langchain_agent.py, multi_source.py, file_references.py)
- **Config**: `pyproject.toml` (package metadata, dependencies, build config)
- **Documentation**: `README.md` (user-facing), `CLAUDE.md` (agent context), `.docs/` (specs)

### Common Development Tasks
1. **Add new feature**: Update relevant module in `src/skillkit/core/`, add tests in `tests/`, update examples if needed
2. **Add framework integration**: Create new file in `src/skillkit/integrations/`, add optional dependency in `pyproject.toml`
3. **Update tests**: Run `pytest -v` to verify, `pytest -m async` for async tests, `pytest --cov` for coverage
4. **Add example**: Create new file in `examples/`, ensure it's referenced in README.md
5. **Release new version**: Update version in `pyproject.toml`, update CHANGELOG in README.md and CLAUDE.md, run `python -m build`

### Testing Strategy
- **Unit tests**: Each module has corresponding test file (test_discovery.py, test_parser.py, etc.)
- **Integration tests**: test_langchain.py, test_manager.py (marked with `@pytest.mark.integration`)
- **Async tests**: Marked with `@pytest.mark.asyncio` (requires pytest-asyncio)
- **Fixtures**: Defined in `tests/conftest.py` and `tests/fixtures/skills/`
- **Coverage target**: 70%+ (current: 70%+)

### Code Quality Standards
- **Formatting**: Use `ruff format src/skillkit` (no config needed, uses defaults)
- **Linting**: Use `ruff check src/skillkit` (rules in pyproject.toml)
- **Type checking**: Use `mypy src/skillkit --strict` (strictest mode)
- **Docstrings**: Google-style docstrings for all public APIs
- **Comments**: Explain "why", not "what" (code should be self-documenting)

### API Design Principles
1. **Backward compatibility**: Never break existing APIs, only add new ones
2. **Async additive**: Async methods complement sync (e.g., `discover()` + `adiscover()`)
3. **Graceful degradation**: Discovery failures log warnings, invocation failures raise exceptions
4. **Progressive disclosure**: Metadata loads first, content loads on-demand
5. **Security first**: Always validate paths, sanitize inputs, use safe YAML loading
