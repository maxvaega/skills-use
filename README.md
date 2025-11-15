<div align="center">
<h1 align="center" style="font-size:4em">skillkit</h1>
</div>
<p align="center" style="max-width:80%; margin-bottom:40px">Enables Anthropic's Agent Skills functionality to any python agent, unleashing LLM-powered agents to <b>autonomously discover and utilize packaged expertise</b> in a token-efficient way.
skillkit is compatible with existings skills (SKILL.md), so you can browse and use any skill available on the web</p>

<p align="center">
<a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.10%2B-blue" /></a>
<a href="https://opensource.org/licenses/MIT">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" /></a>
<a href="https://pypi.org/project/skillkit/">
    <img src="https://img.shields.io/pypi/v/skillkit" /></a>
<a href="ttps://github.com/maxvaega/skillkit/releases">
    <img src="https://img.shields.io/github/v/release/maxvaega/skillkit" /></a>
<a href="https://github.com/maxvaega/skillkit/releases">
    <img src="https://img.shields.io/github/v/release/maxvaega/skillkit" /></a>
<a href="https://github.com/maxvaega/skillkit/stargazers">
    <img src="https://img.shields.io/github/stars/maxvaega/skillkit" /></a>
</p>

---

## Features

- **Framework-free**: can be used without any framework, or with other frameworks (currently only compatible with LangChain - more coming in the future!)
- **Async support**: Non-blocking skill discovery and invocation for high-performance applications
- **Multi-source skill discovery**: From project, Anthropic config, plugins, and custom directories with priority-based conflict resolution
- **Plugin ecosystem**: Full support for Anthropic's MCPB plugin manifests with namespaced skill access
- **Nested directory structures**: Discover skills in any directory hierarchy up to 5 levels deep
- **Secure file resolution**: Path traversal prevention for accessing skill supporting files
- **YAML frontmatter parsing** with comprehensive validation
- **Progressive disclosure pattern** (metadata-first loading, 80% memory reduction)
- **Security features**: Input validation, size limits, suspicious pattern detection, path security
- **Model-agnostic design**: Works with any LLM

---

## Why Skills Matter?

### What Skills Are

**Agent Skills** are modular capability packages that work like "onboarding guides" for AI. Each skill is a folder containing a **SKILL.md** file (with YAML metadata + Markdown instructions) plus optional supporting files like scripts, templates, and documentation. The Agent autonomously discovers and loads skills based on task relevance using a progressive disclosure model—first reading just the name/description metadata, then the full SKILL.md if needed, and finally any referenced files only when required.

### Why Skills Matter

**-  Transform AI from assistant to operational team member** — Skills let you encode your organization's procedural knowledge, workflows, and domain expertise into reusable capabilities that Claude can invoke autonomously. Instead of repeatedly prompting Claude with the same context, you create persistent "muscle memory" that integrates AI into real business processes, making it a specialized professional rather than a generic chatbot.

**-  Achieve scalable efficiency through progressive disclosure** — Unlike traditional prompting where everything loads into context, skills use a three-tier discovery system (metadata → full instructions → supplementary files) that **keeps Claude's context window lean**. This architecture allows unlimited expertise to be available without token bloat, dramatically **reducing running costs** while supporting dozens of skills simultaneously.

**-  Combine AI reasoning with deterministic code execution** — Skills can bundle Python scripts and executables alongside natural language instructions, letting Claude use traditional programming for tasks where LLMs are wasteful or unreliable (like sorting lists, filling PDF forms, or data transformations). This hybrid approach delivers the reliability of code with the flexibility of AI reasoning, ensuring consistent, auditable results for mission-critical operations. ⚠️ **Warning** Code execution feature is not currently active and will be released in future versions of skillkit

### Where can i find ready-to-use skills?

The web is full of great skills! here are some repositories you can check out:
- [Anthropic Skills Library](https://github.com/anthropics/skills)
- [Claude-Plugins.dev Library](https://claude-plugins.dev/skills)
- [travisvn/awesome-claude-skills repo](https://github.com/travisvn/awesome-claude-skills)
- [maxvaega/awesome-skills repo](https://github.com/maxvaega/awesome-skills)

---

## Installation

### Core library

```bash
pip install skillkit
```

### With async support

```bash
pip install skillkit[async]
```

### With LangChain integration

```bash
pip install skillkit[langchain]
```

### All extras (async + LangChain + dev tools)

```bash
pip install skillkit[all]
```

### Development dependencies

```bash
pip install skillkit[dev]
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
allowed-tools: Read, Grep
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

#### Sync usage (v0.1 compatible)

```python
from skillkit import SkillManager

# Create manager (defaults to ./.claude/skills/)
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

#### Async usage (v0.2+)

```python
import asyncio
from skillkit import SkillManager

async def main():
    # Create manager with multiple sources
    manager = SkillManager(
        project_skill_dir="./skills",              # Priority: 100
        anthropic_config_dir="./.claude/skills",  # Priority: 50
        plugin_dirs=["./plugins/my-plugin"]       # Priority: 10
    )

    # Async discovery (non-blocking)
    await manager.adiscover()

    # List available skills
    for skill in manager.list_skills():
        print(f"{skill.name}: {skill.description}")

    # Async invocation (non-blocking)
    result = await manager.ainvoke_skill("code-reviewer", "Review function calculate_total()")
    print(result)

asyncio.run(main())
```

### 3. Use with LangChain

```python
from skillkit import SkillManager
from skillkit.integrations.langchain import create_langchain_tools
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain.messages import HumanMessage

# Discover skills
manager = SkillManager()
manager.discover()

# Convert to LangChain tools
tools = create_langchain_tools(manager)

# Create agent
llm = ChatOpenAI(model="gpt-4")
prompt = "You are a helpful assistant. use the available skills tools to answer the user queries."
agent = create_agent(
    llm, 
    tools, 
    system_prompt=prompt
    )

# Use agent
query="What are Common Architectural Scenarios in python?"
messages = [HumanMessage(content=query)]
result = agent.invoke({"messages": messages})
```

## Advanced Features (v0.2+)

### Multi-Source Discovery with Priority Resolution

```python
from skillkit import SkillManager

# Configure multiple skill sources
manager = SkillManager(
    project_skill_dir="./skills",              # Priority: 100 (highest)
    anthropic_config_dir="./.claude/skills",  # Priority: 50
    plugin_dirs=[                              # Priority: 10 each
        "./plugins/data-tools",
        "./plugins/web-tools"
    ],
    additional_search_paths=["./shared"]      # Priority: 5
)

manager.discover()

# Simple name gets highest priority version
skill = manager.get_skill("csv-parser")  # Gets project version if exists

# Qualified name accesses specific plugin version
skill = manager.get_skill("data-tools:csv-parser")  # Explicit plugin version
```

### Plugin Integration

Create a plugin with `.claude-plugin/plugin.json`:

```json
{
  "manifest_version": "0.1",
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "My custom skill collection",
  "author": {
    "name": "Your Name"
  },
  "skills": ["skills/"]
}
```

### Secure File References

Access supporting files securely from skills:

```python
from skillkit.core.path_resolver import FilePathResolver

# Get skill
skill = manager.load_skill("data-processor")

# Resolve supporting files (path traversal prevented)
helper_path = FilePathResolver.resolve_path(
    skill.base_directory,
    "scripts/helper.py"
)

# Use the file
with open(helper_path, 'r') as f:
    script = f.read()
```

### Async LangChain Integration

```python
import asyncio
from skillkit import SkillManager
from skillkit.integrations.langchain import create_langchain_tools
from langchain.agents import AgentExecutor
from langchain_anthropic import ChatAnthropic

async def run_agent():
    manager = SkillManager()
    await manager.adiscover()

    tools = create_langchain_tools(manager)
    llm = ChatAnthropic(model="claude-3-5-sonnet-20241022")

    # Tools support both sync (invoke) and async (ainvoke)
    result = await tools[0].ainvoke({"arguments": "test"})

asyncio.run(run_agent())
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
allowed-tools: Bash, Read
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

# v0.1 style (still works)
manager = SkillManager(Path("/custom/skills"))

# v0.2 style (recommended)
manager = SkillManager(project_skill_dir=Path("/custom/skills"))
```

### Concurrent async invocations

```python
import asyncio

async def process_multiple_files():
    manager = SkillManager()
    await manager.adiscover()

    # Process 10+ files concurrently
    results = await asyncio.gather(
        manager.ainvoke_skill("csv-parser", "data1.csv"),
        manager.ainvoke_skill("csv-parser", "data2.csv"),
        manager.ainvoke_skill("json-parser", "data.json"),
        # ... more concurrent invocations
    )
    return results

asyncio.run(process_multiple_files())
```

### Error handling

```python
from skillkit import SkillNotFoundError, ContentLoadError

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
logging.getLogger('skillkit.core.discovery').setLevel(logging.DEBUG)
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

- **Python**: 3.10+
- **Core dependencies**: PyYAML 6.0+
- **Optional**: langchain-core 0.1.0+, pydantic 2.0+ (for LangChain integration)

## Development

### Setup

```bash
git clone https://github.com/maxvaega/skillkit.git
cd skillkit
python3.10 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Run tests

The project includes a comprehensive pytest-based test suite with 70%+ coverage validating core functionality, integrations, and edge cases.
For detailed testing instructions, test organization, markers, and debugging tips, see **[tests/README.md](tests/README.md)**.

```bash
pytest
pytest --cov=src/skillkit --cov-report=html
```

### Type checking

```bash
mypy src/skillkit --strict
```

### Linting

```bash
ruff check src/skillkit
ruff format src/skillkit
```

## Examples

See `examples/` directory:
- `basic_usage.py` - Standalone usage (sync and async patterns)
- `async_usage.py` - Async usage with FastAPI integration
- `langchain_agent.py` - LangChain agent integration (sync and async)
- `multi_source.py` - Multi-source discovery and conflict resolution
- `file_references.py` - Secure file path resolution
- `skills/` - Example skills and plugins

Run examples:
```bash
# Basic sync usage
python examples/basic_usage.py

# Async usage with FastAPI
python examples/async_usage.py

# LangChain integration
python examples/langchain_agent.py

# Multi-source discovery
python examples/multi_source.py

# File path resolution
python examples/file_references.py
```

## Roadmap

### v0.1 (Released)
- ✅ Core skill discovery and metadata management
- ✅ YAML frontmatter parsing with validation
- ✅ Progressive disclosure pattern (lazy loading)
- ✅ Skill invocation with argument substitution
- ✅ LangChain integration (sync only)
- ✅ 70% test coverage

### v0.2 (Current) ✨
- ✅ Async support (`adiscover()`, `ainvoke_skill()`)
- ✅ Multi-source discovery (project, Anthropic config, plugins, custom paths)
- ✅ Plugin integration with MCPB manifest support
- ✅ Nested directory structures (up to 5 levels deep)
- ✅ Fully qualified skill names for conflict resolution
- ✅ Secure file path resolution with traversal prevention
- ✅ LangChain async integration (`ainvoke`)
- ✅ Backward compatible with v0.1

### v0.3 (Planned)
- Script Execution (script detection, execution with variables, stdout/stderr capture, sandboxing)
- Tool restriction enforcement (allowed-tools validation)
- Additional framework integrations (LlamaIndex, CrewAI, Haystack)

### v0.4 (Planned)
- Advanced arguments schemas
- Skill versioning and compatibility checks
- Enhanced error handling and recovery
- Performance optimizations

### v1.0 (Planned)
- Comprehensive documentation
- 90% test coverage
- Production-ready stability
- Full plugin ecosystem support

## License

MIT License - see LICENSE file for details.

## Contributing

We welcome contributions from the community! Whether you're fixing bugs, adding features, improving documentation, or creating new example skills, your help is appreciated.

### Quick Start for Contributors

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and add tests
4. Ensure all tests pass (`pytest`)
5. Ensure code quality checks pass (`ruff check`, `mypy --strict`)
6. Submit a pull request

### Detailed Guidelines

For comprehensive contribution guidelines, including:
- Development environment setup
- Code style and testing requirements
- PR submission process
- Bug reporting and feature requests

Please see **[CONTRIBUTING.md](CONTRIBUTING.md)** for detailed information.

## Support

- **Issues**: https://github.com/maxvaega/skillkit/issues
- **Documentation**: https://github.com/maxvaega/skillkit#readme

## Acknowledgments

- Inspired by Anthropic's Agent Skills functionality
- Built with Python, PyYAML, LangChain, and Pydantic
