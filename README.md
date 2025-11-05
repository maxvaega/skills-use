# skills-use

Enables Anthropic's Agent Skills functionality to any python agent, unleashing LLM-powered agents to autonomously discover and utilize packaged expertise, regardless of their framework.
Skills-use is compatible with existings skills (SKILL.md), so you can browse and use any skill available on the web

## Features

- **Framework-free**: can be used without any framework, or with other frameworks (currently only compatible with LangChain - more coming in the future!)
- **Multi-source skill discovery** from local directories
- **YAML frontmatter parsing** with comprehensive validation
- **Progressive disclosure pattern** (metadata-first loading, 80% memory reduction)
- **Security features**: Input validation, size limits, suspicious pattern detection
- **Model-agnostic design**: Works with any LLM

## Why Skills Matter?

### What Skills Are

**Agent Skills** are modular capability packages that work like "onboarding guides" for AI. Each skill is a folder containing a **SKILL.md** file (with YAML metadata + Markdown instructions) plus optional supporting files like scripts, templates, and documentation. The Agent autonomously discovers and loads skills based on task relevance using a progressive disclosure model—first reading just the name/description metadata, then the full SKILL.md if needed, and finally any referenced files only when required.

---

### Why Skills Matter

**-  Transform AI from assistant to operational team member** — Skills let you encode your organization's procedural knowledge, workflows, and domain expertise into reusable capabilities that Claude can invoke autonomously. Instead of repeatedly prompting Claude with the same context, you create persistent "muscle memory" that integrates AI into real business processes, making it a specialized professional rather than a generic chatbot.

**-  Achieve scalable efficiency through progressive disclosure** — Unlike traditional prompting where everything loads into context, skills use a three-tier discovery system (metadata → full instructions → supplementary files) that **keeps Claude's context window lean**. This architecture allows unlimited expertise to be available without token bloat, dramatically **reducing running costs** while supporting dozens of skills simultaneously.

**-  Combine AI reasoning with deterministic code execution** — Skills can bundle Python scripts and executables alongside natural language instructions, letting Claude use traditional programming for tasks where LLMs are wasteful or unreliable (like sorting lists, filling PDF forms, or data transformations). This hybrid approach delivers the reliability of code with the flexibility of AI reasoning, ensuring consistent, auditable results for mission-critical operations. ⚠️ **Warning** Code execution feature is not currently active and will be released in future versions of skills-use

### Where can i find ready-to-use skills?

The web is full of great skills! here are some repositories you can check out:
- [Anthropic Skills Library](https://github.com/anthropics/skills)
- [Claude-Plugins.dev Library](https://claude-plugins.dev/skills)
- [travisvn/awesome-claude-skills repo](https://github.com/travisvn/awesome-claude-skills)
- [maxvaega/awesome-skills repo](https://github.com/maxvaega/awesome-skills)

## Installation

### Core library

```bash
pip install skills-use
```

### With LangChain integration

```bash
pip install skills-use[langchain]
```

### Development dependencies

```bash
pip install skills-use[dev]
```

## Quick Start

### 1. Create a skill

Create a directory structure:
```
.claude/skills/code-reviewer/SKILL.md
```

SKILL.md format:
```markdown
---
name: code-reviewer
description: Review code for best practices and potential issues
allowed-tools:
  - read
  - grep
---

# Code Reviewer Skill

You are a code reviewer. Analyze the provided code for:
- Best practices violations
- Potential bugs
- Security vulnerabilities

## Instructions

$ARGUMENTS
```

### 2. Use standalone (without frameworks)

```python
from skills_use import SkillManager

# Create manager (defaults to ~/.claude/skills/)
manager = SkillManager()

# Discover skills
manager.discover()

# List available skills
for skill in manager.list_skills():
    print(f"{skill.name}: {skill.description}")

# Invoke a skill
result = manager.invoke_skill("code-reviewer", "Review function calculate_total()")
print(result)
```

### 3. Use with LangChain

```python
from skills_use import SkillManager
from skills_use.integrations.langchain import create_langchain_tools
from langchain.agents import create_react_agent, AgentExecutor
from langchain_openai import ChatOpenAI

# Discover skills
manager = SkillManager()
manager.discover()

# Convert to LangChain tools
tools = create_langchain_tools(manager)

# Create agent
llm = ChatOpenAI(model="gpt-4")
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)

# Use agent
result = agent_executor.invoke({"input": "Review my code for security issues"})
```

## SKILL.md Format

### Required Fields

- `name` (string): Unique skill identifier
- `description` (string): Human-readable skill description

### Optional Fields

- `allowed-tools` (list): Tool names allowed for this skill (not enforced in v0.1)

### Example

```yaml
---
name: git-helper
description: Generate git commit messages and workflow guidance
allowed-tools:
  - bash
  - read
---

# Git Helper Skill

Content with $ARGUMENTS placeholder...
```

### Argument Substitution

- `$ARGUMENTS` → replaced with user-provided arguments
- `$$ARGUMENTS` → literal `$ARGUMENTS` (escaped)
- No placeholder + arguments → arguments appended to end
- No placeholder + no arguments → content unchanged

## Common Usage Patterns

### Custom skills directory

```python
from pathlib import Path
manager = SkillManager(Path("/custom/skills"))
```

### Error handling

```python
from skills_use import SkillNotFoundError, ContentLoadError

try:
    result = manager.invoke_skill("my-skill", args)
except SkillNotFoundError:
    print("Skill not found")
except ContentLoadError:
    print("Skill file was deleted or is unreadable")
```

### Accessing metadata

```python
metadata = manager.get_skill("code-reviewer")
print(f"Path: {metadata.skill_path}")
print(f"Tools: {metadata.allowed_tools}")
```

### Multiple arguments

```python
# Arguments are passed as a single string
result = manager.invoke_skill("code-reviewer", "Review file.py for security issues")
```

### No placeholder behavior

If SKILL.md has no `$ARGUMENTS` placeholder:
- With arguments: appended to end of content
- Without arguments: content returned unchanged

## Debugging Tips

### Enable logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Module-specific logging

```python
logging.getLogger('skills_use.core.discovery').setLevel(logging.DEBUG)
```

### Common issues

**Skill not found after discovery:**
- Check skill directory path
- Verify SKILL.md file exists (case-insensitive)
- Check logs for parsing errors

**YAML parsing errors:**
- Validate YAML syntax (use yamllint)
- Check for proper `---` delimiters
- Ensure required fields present

**Arguments not substituted:**
- Check for `$ARGUMENTS` placeholder (case-sensitive)
- Check for typos: `$arguments`, `$ARGUMENT`, `$ ARGUMENTS`
- See logs for typo detection warnings

**Memory usage concerns:**
- Content is loaded lazily (only when `.content` accessed or `invoke()` called)
- Python 3.10+ recommended for optimal memory efficiency (60% reduction via slots)

## Performance Tips

1. **Discover once**: Call `discover()` once at startup, reuse manager
2. **Reuse manager**: Don't create new SkillManager for each invocation
3. **Keep skills focused**: Large skills (>200KB) may slow down invocation
4. **Use Python 3.10+**: Better memory efficiency with dataclass slots

## Requirements

- **Python**: 3.9+ (3.10+ recommended)
- **Core dependencies**: PyYAML 6.0+
- **Optional**: langchain-core 0.1.0+, pydantic 2.0+ (for LangChain integration)

## Development

### Setup

```bash
git clone https://github.com/maxvaega/skills-use.git
cd skills-use
python3.10 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### Run tests

```bash
pytest
pytest --cov=skills_use --cov-report=html
```

### Type checking

```bash
mypy src/skills_use --strict
```

### Linting

```bash
ruff check src/skills_use
ruff format src/skills_use
```

## Examples

See `examples/` directory:
- `basic_usage.py` - Standalone usage without frameworks
- `langchain_agent.py` - LangChain agent integration
- `skills/` - Example skills (code-reviewer, markdown-formatter, git-helper)

Run examples:
```bash
python examples/basic_usage.py
python examples/langchain_agent.py  # Requires langchain extras
```

## Roadmap

### v0.1 (Current)
- ✅ Core skill discovery and metadata management
- ✅ YAML frontmatter parsing with validation
- ✅ Progressive disclosure pattern (lazy loading)
- ✅ Skill invocation with argument substitution
- ✅ LangChain integration (sync only)
- ✅ 70% test coverage

### v0.2 (Planned)
- Async support (`adiscover()`, `ainvoke_skill()`)
- Enhanced error handling and recovery
- Performance optimizations

### v0.3 (Planned)
- Multiple search paths for skills
- Plugin integration for dynamic skill loading
- Tool restriction enforcement

### v1.0 (Planned)
- Nested directory support
- Skill versioning and compatibility checks
- Comprehensive documentation
- 90% test coverage

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass (`pytest`)
5. Submit a pull request

## Support

- **Issues**: https://github.com/maxvaega/skills-use/issues
- **Documentation**: https://github.com/maxvaega/skills-use#readme

## Acknowledgments

- Inspired by Anthropic's Agent Skills functionality
- Built with Python, PyYAML, LangChain, and Pydantic
