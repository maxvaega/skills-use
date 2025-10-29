# Skills-use

**skills-use** is a Python library that implements Anthropic's Agent Skills functionality, enabling LLM-powered agents to autonomously discover and utilize packaged expertise. The library provides:

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

## Documentation

All project documentation is located in the `.docs/` directory:

### `.docs/MVP_VERTICAL_SLICE_PLAN.md`
The **implementation roadmap** for the project. Contains:
- Vertical slice philosophy and rationale
- 4-week MVP plan with week-by-week breakdown
- Critical path requirements (CP-1 through CP-7)
- Post-launch iteration roadmap (v0.2, v0.3, v1.0)
- Success metrics and validation criteria
- Risk mitigation strategies
- Comparison between original horizontal approach vs vertical slice

### `.docs/PRD_SKILLS-USE_LIBRARY.md`
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

## Development Environment

This project uses Python.

## Project Structure

The repository is currently in early development. Expected structure (from TECH_SPECS.md):

```
skills-use/
├── .docs/                    # Project documentation
├── src/
│   └── skills_use/
│       ├── core/             # Core discovery, parsing, management
│       ├── integrations/     # Framework adapters (LangChain, etc.)
│       └── exceptions.py     # Custom exceptions
├── tests/                    # Test suite
├── examples/                 # Example skills and usage
└── pyproject.toml           # Package configuration
```
