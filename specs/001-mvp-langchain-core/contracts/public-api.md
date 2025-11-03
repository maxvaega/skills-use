# Public API Contract: Skills-use v0.1 MVP

**Version**: 0.1.0
**Date**: November 3, 2025
**Package**: `skills-use`

## Overview

This document defines the public API contract for the skills-use library v0.1. All classes, functions, and methods documented here are guaranteed stable within the 0.1.x version series.

---

## Module: `skills_use` (Top-Level)

**Import**: `from skills_use import ...`

### Exported Classes

```python
from skills_use import (
    SkillManager,      # Main entry point
    SkillMetadata,     # Skill metadata model
    Skill,             # Full skill model
    SkillsUseError,    # Base exception
    SkillParsingError, # Parsing errors
    SkillNotFoundError,# Lookup errors
    SkillInvocationError, # Invocation errors
)
```

---

## Class: `SkillManager`

**Purpose**: Central coordinator for skill discovery, loading, and invocation.

**Module**: `skills_use.SkillManager`

### Constructor

```python
def __init__(self, skills_directory: Optional[Path] = None) -> None
```

**Parameters**:
- `skills_directory` (Optional[Path]): Custom skills directory path. Defaults to `~/.claude/skills/`

**Example**:
```python
from skills_use import SkillManager

# Use default directory
manager = SkillManager()

# Use custom directory
from pathlib import Path
manager = SkillManager(skills_directory=Path("./my-skills"))
```

---

### Method: `discover()`

```python
def discover(self) -> None
```

**Purpose**: Discover and load all skill metadata from the skills directory.

**Parameters**: None

**Returns**: None

**Side Effects**: Populates internal skill registry

**Raises**: None (errors logged, continues processing)

**Example**:
```python
manager = SkillManager()
manager.discover()  # Scans ~/.claude/skills/
```

**Notes**:
- Must be called before `list_skills()`, `get_skill()`, etc.
- Gracefully handles parsing errors (logs and continues)
- Automatically called on first `list_skills()` or `get_skill()` if not explicitly invoked

---

### Method: `list_skills()`

```python
def list_skills(self) -> List[SkillMetadata]
```

**Purpose**: List all discovered skills.

**Parameters**: None

**Returns**: `List[SkillMetadata]` - All discovered skill metadata objects

**Raises**: None

**Example**:
```python
skills = manager.list_skills()
for skill in skills:
    print(f"{skill.name}: {skill.description}")

# Output:
# code-reviewer: Reviews Python code for common mistakes
# markdown-formatter: Formats markdown documents
```

**Notes**:
- Auto-calls `discover()` if not already initialized
- Returns empty list if no skills found

---

### Method: `get_skill()`

```python
def get_skill(self, name: str) -> SkillMetadata
```

**Purpose**: Get skill metadata by name.

**Parameters**:
- `name` (str): Skill name (from YAML frontmatter)

**Returns**: `SkillMetadata` - Skill metadata object

**Raises**:
- `SkillNotFoundError`: If skill with given name doesn't exist

**Example**:
```python
metadata = manager.get_skill("code-reviewer")
print(metadata.description)
# Output: Reviews Python code for common mistakes
```

**Notes**:
- Auto-calls `discover()` if not already initialized
- Name lookup is exact match (case-sensitive)

---

### Method: `load_skill()`

```python
def load_skill(self, name: str) -> Skill
```

**Purpose**: Load full skill with content.

**Parameters**:
- `name` (str): Skill name

**Returns**: `Skill` - Full skill object with loaded content

**Raises**:
- `SkillNotFoundError`: If skill doesn't exist
- `SkillParsingError`: If content cannot be loaded

**Example**:
```python
skill = manager.load_skill("code-reviewer")
print(skill.content)
# Output: Full markdown content from SKILL.md
```

**Notes**:
- Content loaded on-demand (not cached in v0.1)
- Use `invoke_skill()` instead for processed content

---

### Method: `invoke_skill()`

```python
def invoke_skill(self, name: str, arguments: str = "") -> str
```

**Purpose**: Load and invoke skill with arguments.

**Parameters**:
- `name` (str): Skill name
- `arguments` (str): User arguments to pass to skill. Default: `""`

**Returns**: `str` - Processed skill content ready for LLM consumption

**Raises**:
- `SkillNotFoundError`: If skill doesn't exist
- `SkillParsingError`: If content cannot be loaded

**Example**:
```python
result = manager.invoke_skill(
    "code-reviewer",
    "Review this function:\ndef foo(x): return x/0"
)

print(result)
# Output:
# Base directory for this skill: /Users/.../code-reviewer
#
# [Skill content with $ARGUMENTS replaced]
```

**Notes**:
- Combines `load_skill()` + argument processing
- `$ARGUMENTS` placeholder replaced with provided arguments
- If no placeholder, arguments appended as "ARGUMENTS: {args}"
- Base directory always injected at beginning

---

## Class: `SkillMetadata`

**Purpose**: Lightweight skill metadata (loaded during discovery).

**Module**: `skills_use.SkillMetadata`

### Constructor

```python
@dataclass
class SkillMetadata:
    name: str
    description: str
    skill_path: Path
    allowed_tools: Optional[List[str]] = None
```

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | Yes | Skill identifier |
| `description` | `str` | Yes | Brief description |
| `skill_path` | `Path` | Yes | Path to SKILL.md file |
| `allowed_tools` | `Optional[List[str]]` | No | Allowed tools list (parsed but not enforced in v0.1) |

**Example**:
```python
metadata = SkillMetadata(
    name="code-reviewer",
    description="Reviews Python code",
    skill_path=Path("/Users/.../code-reviewer/SKILL.md"),
    allowed_tools=["read", "grep"]
)
```

---

## Class: `Skill`

**Purpose**: Full skill object with loaded content.

**Module**: `skills_use.Skill`

### Constructor

```python
@dataclass
class Skill:
    metadata: SkillMetadata
    content: str
    base_directory: Path
```

**Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `metadata` | `SkillMetadata` | Associated metadata |
| `content` | `str` | Full markdown content (after frontmatter) |
| `base_directory` | `Path` | Skill directory path |

---

### Method: `invoke()`

```python
def invoke(self, arguments: str = "") -> str
```

**Purpose**: Process skill content with arguments.

**Parameters**:
- `arguments` (str): User arguments. Default: `""`

**Returns**: `str` - Processed content

**Example**:
```python
skill = manager.load_skill("code-reviewer")
result = skill.invoke("def foo(): pass")
print(result)
```

**Notes**:
- Equivalent to calling `process_skill_content(skill, arguments)`
- Handles $ARGUMENTS substitution and base directory injection

---

## Module: `skills_use.integrations.langchain`

**Purpose**: LangChain framework integration.

**Import**: `from skills_use.integrations.langchain import ...`

### Function: `create_langchain_tools()`

```python
def create_langchain_tools(
    manager: Optional[SkillManager] = None,
    skills_directory: Optional[Path] = None
) -> List[StructuredTool]
```

**Purpose**: Create LangChain StructuredTool instances from discovered skills.

**Parameters**:
- `manager` (Optional[SkillManager]): Existing SkillManager. If None, creates new one.
- `skills_directory` (Optional[Path]): Skills directory (used if manager is None)

**Returns**: `List[StructuredTool]` - LangChain tool objects

**Raises**: None (errors logged and returned as error strings)

**Example**:
```python
from skills_use.integrations.langchain import create_langchain_tools
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent, AgentExecutor

# Create tools from skills
tools = create_langchain_tools()

# Use with LangChain agent
llm = ChatOpenAI(model="gpt-4")
agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)

result = agent_executor.invoke({
    "input": "Review my Python code for bugs"
})
```

**Notes**:
- Automatically discovers skills if manager not provided
- One tool per skill
- Tool name = skill name, tool description = skill description
- Tool input: single `arguments` string parameter
- Errors caught and returned as strings (agent-friendly)

---

### Function: `create_langchain_tool_from_skill()`

```python
def create_langchain_tool_from_skill(
    skill_name: str,
    manager: SkillManager
) -> StructuredTool
```

**Purpose**: Create a single LangChain tool from a specific skill.

**Parameters**:
- `skill_name` (str): Name of the skill
- `manager` (SkillManager): SkillManager instance

**Returns**: `StructuredTool` - LangChain tool object

**Raises**:
- `SkillNotFoundError`: If skill doesn't exist

**Example**:
```python
from skills_use import SkillManager
from skills_use.integrations.langchain import create_langchain_tool_from_skill

manager = SkillManager()
manager.discover()

tool = create_langchain_tool_from_skill("code-reviewer", manager)
```

---

## Exception Classes

### `SkillsUseError`

**Module**: `skills_use.SkillsUseError`

**Base class** for all skills-use exceptions.

**Usage**:
```python
from skills_use import SkillsUseError

try:
    manager.invoke_skill("my-skill")
except SkillsUseError as e:
    print(f"Error: {e}")
```

---

### `SkillParsingError`

**Module**: `skills_use.SkillParsingError`

**Inherits**: `SkillsUseError`

**Raised when**: SKILL.md file cannot be parsed (missing fields, malformed YAML, invalid frontmatter)

**Example**:
```python
from skills_use import SkillParsingError

try:
    manager.discover()
except SkillParsingError as e:
    print(f"Parsing error: {e}")
```

---

### `SkillNotFoundError`

**Module**: `skills_use.SkillNotFoundError`

**Inherits**: `SkillsUseError`

**Raised when**: Requested skill doesn't exist in registry

**Example**:
```python
from skills_use import SkillNotFoundError

try:
    skill = manager.get_skill("nonexistent-skill")
except SkillNotFoundError as e:
    print(f"Skill not found: {e}")
```

---

### `SkillInvocationError`

**Module**: `skills_use.SkillInvocationError`

**Inherits**: `SkillsUseError`

**Raised when**: Skill invocation fails at runtime

**Note**: Reserved for future use (v0.2+). Not raised in v0.1.

---

## Version Compatibility

**Semantic Versioning**: This library follows [SemVer 2.0.0](https://semver.org/)

**v0.1.x Guarantees**:
- ✅ Public API signatures will not change
- ✅ Exception types will not change
- ✅ Behavior documented here is stable
- ⚠️ Internal implementation may change (do not import from `core/` directly)

**Breaking Changes** (require v0.2.0+):
- Changing method signatures
- Removing public classes/methods
- Changing exception hierarchy

**Non-Breaking Changes** (allowed in v0.1.x):
- Adding new methods
- Adding optional parameters with defaults
- Performance improvements
- Bug fixes

---

## Installation

```bash
# Core only
pip install skills-use

# With LangChain integration
pip install skills-use[langchain]

# Development dependencies
pip install skills-use[dev]

# Everything
pip install skills-use[all]
```

---

## Minimal Working Example

```python
from skills_use import SkillManager

# Initialize and discover skills
manager = SkillManager()
manager.discover()

# List available skills
skills = manager.list_skills()
print(f"Found {len(skills)} skills")

# Invoke a skill
result = manager.invoke_skill(
    "code-reviewer",
    "Review this code:\ndef foo(): return 1/0"
)
print(result)
```

---

## LangChain Integration Example

```python
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from skills_use.integrations.langchain import create_langchain_tools

# Create skills as LangChain tools
tools = create_langchain_tools()

# Setup agent
llm = ChatOpenAI(model="gpt-4", temperature=0)
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. Use skills when appropriate."),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Use agent
result = agent_executor.invoke({
    "input": "Review my Python code for common mistakes"
})
print(result)
```

---

## Thread Safety

**v0.1 Thread Safety**:
- ❌ `SkillManager` is **NOT thread-safe**
- ❌ Do not share `SkillManager` instances across threads
- ✅ Create separate `SkillManager` instance per thread

**Future**: Thread-safe operations planned for v0.3

---

## Performance Characteristics

| Operation | Expected Time | Notes |
|-----------|---------------|-------|
| `discover()` | <500ms for 10 skills | Dominated by filesystem I/O |
| `list_skills()` | <1ms | Returns cached metadata |
| `get_skill()` | <1ms | Dict lookup |
| `load_skill()` | ~10-20ms | File I/O + parsing |
| `invoke_skill()` | ~10-25ms | File I/O + string processing |

**Memory**: ~1-5KB per skill metadata, ~50-200KB per loaded skill

---

## Limitations (v0.1)

**Known Limitations**:
- ❌ Async support: Not available (use sync methods only)
- ❌ Custom skills directory: Supported via constructor, but no multi-path search
- ❌ Nested directories: Not supported (flat structure only)
- ❌ Tool restriction enforcement: `allowed-tools` parsed but not enforced
- ❌ Content caching: Content reloaded on each invocation
- ❌ Thread safety: Not thread-safe

**Planned for v0.2+**: See [MVP_VERTICAL_SLICE_PLAN.md](.docs/MVP_VERTICAL_SLICE_PLAN.md)

---

**Document Version**: 1.0
**API Version**: 0.1.0
**Last Updated**: November 3, 2025
**Status**: Stable
