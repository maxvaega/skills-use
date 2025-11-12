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

- **v0.1 (Week 4)**: Core functionality + LangChain integration (sync only)
- **v0.2 (Week 6)**: Async support + enhanced error handling
- **v0.3 (Week 10)**: Plugin integration + tool restrictions + full feature set
- **v1.0 (Week 12)**: Production polish + comprehensive documentation

### Current Focus (v0.1)

The MVP focuses on 7 critical paths:
1. Basic skill discovery from `.claude/skills/` directory
2. Minimal SKILL.md parsing (name, description, allowed-tools)
3. Lightweight metadata management
4. Basic skill invocation with $ARGUMENTS substitution
5. LangChain integration (sync only)
6. Minimal testing (70% coverage)
7. Minimal documentation + PyPI publishing

**What's deferred to v0.2+**: Async support, plugin integration, tool restriction enforcement, multiple search paths, comprehensive docs, CI/CD pipeline, 90% test coverage.

## Key Architectural Decisions

The v0.1 MVP is built on 8 critical architectural decisions (see `specs/001-mvp-langchain-core/research.md` for full rationale):

1. **Progressive Disclosure Pattern**: Two-tier architecture (SkillMetadata + Skill) with lazy content loading achieves 80% memory reduction
2. **Framework-Agnostic Core**: Zero dependencies in core modules; optional framework integrations via extras
3. **$ARGUMENTS Substitution**: `string.Template` for security + standard escaping (`$$ARGUMENTS`), 1MB size limit, suspicious pattern detection
4. **Error Handling**: Graceful degradation during discovery, strict exceptions during invocation, 11-exception hierarchy
5. **YAML Parsing**: `yaml.safe_load()` with cross-platform support, detailed error messages, typo detection
6. **LangChain Integration**: StructuredTool with closure capture pattern (sync-only v0.1, async in v0.2)
7. **Testing**: 70% coverage with pytest, parametrized tests, fixtures in conftest.py
8. **Sync-Only v0.1**: Async deferred to v0.2 (file I/O overhead negligible vs LLM latency)

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

**Current Phase**: ✅ v0.1 MVP COMPLETE - Ready for Distribution 🚀

**Completed**:
- ✅ Phase 0: Research (8 architectural decisions documented)
- ✅ Phase 1: Design (data-model.md, contracts/public-api.md, quickstart.md)
- ✅ Phase 2: Task Generation (120 tasks in tasks.md)
- ✅ Phase 3: Implementation Complete (All 9 phases executed successfully)
  - Core functionality (discovery, parsing, models, manager, processors)
  - LangChain integration with StructuredTool
  - 3 example skills and usage scripts
  - Comprehensive README.md
  - All code formatted and linting passing
- ✅ Phase 4: Testing completed (see tests/ folder)

**Next Steps**:
- Build package: `python -m build`
- Publish to PyPI: `twine upload dist/*`
- Gather user feedback for v0.2 planning

## Development Environment

This project uses Python Python 3.10+ .

**Virtual Environment Setup**:
```bash
python3.10 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

**Development Commands**:
- Run examples: `python examples/basic_usage.py`
- Run tests: `pytest` (when test suite is added)
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

### Core Dependencies (Zero Framework Dependencies)
- **PyYAML 6.0+**: YAML frontmatter parsing with `yaml.safe_load()` security
- **Python stdlib**: pathlib, dataclasses, functools, typing, re, logging, string.Template

### Optional Dependencies
- **langchain-core 0.1.0+**: StructuredTool integration (install: `pip install skillkit[langchain]`)
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

- **v0.1 MVP Implementation Complete **
- **Architectural Review**: All decisions validated against Python library best practices

## Active Technologies
- Python 3.10+ (minimum for full async support) + PyYAML 6.0+, aiofiles 23.0+ (new), langchain-core 0.1.0+, pydantic 2.0+ (001-v0-2-async-discovery-files)
- Filesystem-based (`.claude/skills/` directories, `.claude-plugin/plugin.json` manifests) (001-v0-2-async-discovery-files)

## Recent Changes
- 001-v0-2-async-discovery-files: Added Python 3.10+ (minimum for full async support) + PyYAML 6.0+, aiofiles 23.0+ (new), langchain-core 0.1.0+, pydantic 2.0+
