# Data Model: Skills-use v0.1 MVP

**Feature**: Core Functionality & LangChain Integration
**Date**: November 3, 2025
**Status**: Complete

## Overview

This document defines all data structures, entities, and their relationships for the skills-use library v0.1. The model follows the progressive disclosure pattern: lightweight metadata loaded during discovery, full content loaded on invocation.

---

## Core Entities

### 1. SkillMetadata

**Purpose**: Lightweight skill information loaded during discovery phase. Contains only YAML frontmatter data without markdown content.

**Location**: `src/skills_use/core/models.py`

**Definition**:
```python
@dataclass
class SkillMetadata:
    """
    Lightweight metadata for a skill.
    Loaded during discovery without reading full content.
    """
    name: str
    description: str
    skill_path: Path
    allowed_tools: Optional[List[str]] = None

    def __post_init__(self):
        """Validate required fields."""
        if not self.name:
            raise ValueError("Skill name is required")
        if not self.description:
            raise ValueError("Skill description is required")
        if not isinstance(self.skill_path, Path):
            self.skill_path = Path(self.skill_path)
```

**Fields**:

| Field | Type | Required | Description | Validation |
|-------|------|----------|-------------|------------|
| `name` | `str` | ✅ Yes | Unique skill identifier (e.g., "code-reviewer") | Non-empty string |
| `description` | `str` | ✅ Yes | Brief description of skill purpose (used by LLM for selection) | Non-empty string |
| `skill_path` | `Path` | ✅ Yes | Absolute path to SKILL.md file | Must be valid Path object |
| `allowed_tools` | `Optional[List[str]]` | ❌ No | List of tools skill can use (e.g., ["read", "grep"]) | None or list of strings |

**Usage**:
```python
metadata = SkillMetadata(
    name="code-reviewer",
    description="Reviews Python code for common mistakes",
    skill_path=Path("/Users/.../.claude/skills/code-reviewer/SKILL.md"),
    allowed_tools=["read", "grep"]
)
```

**State Transitions**: Immutable once created (read-only dataclass)

---

### 2. Skill

**Purpose**: Full skill object with loaded content. Created on-demand during invocation phase.

**Location**: `src/skills_use/core/models.py`

**Definition**:
```python
@dataclass
class Skill:
    """
    Full skill object with content loaded.
    Created on-demand during invocation.
    """
    metadata: SkillMetadata
    content: str
    base_directory: Path

    def invoke(self, arguments: str = "") -> str:
        """
        Process skill content with arguments.

        Args:
            arguments: User-provided arguments to substitute into skill

        Returns:
            Processed skill content ready for LLM consumption
        """
        from skills_use.core.invocation import process_skill_content
        return process_skill_content(self, arguments)
```

**Fields**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `metadata` | `SkillMetadata` | ✅ Yes | Associated skill metadata (name, description, etc.) |
| `content` | `str` | ✅ Yes | Full markdown content from SKILL.md (after frontmatter) |
| `base_directory` | `Path` | ✅ Yes | Parent directory of SKILL.md (for file references) |

**Usage**:
```python
skill = Skill(
    metadata=metadata,
    content="You are a code reviewer. Review: $ARGUMENTS",
    base_directory=Path("/Users/.../.claude/skills/code-reviewer")
)

result = skill.invoke("def foo(): return x/0")
```

**State Transitions**: Immutable once created; invocation creates new processed string

---

### 3. SkillDiscovery

**Purpose**: Discovers SKILL.md files from filesystem.

**Location**: `src/skills_use/core/discovery.py`

**Definition**:
```python
class SkillDiscovery:
    """
    Discovers SKILL.md files from .claude/skills/ directory.
    v0.1: Single hardcoded path, flat structure only.
    """
    DEFAULT_SKILLS_DIR = Path.home() / ".claude" / "skills"

    def __init__(self, skills_directory: Optional[Path] = None):
        self.skills_directory = skills_directory or self.DEFAULT_SKILLS_DIR

    def discover_skills(self) -> List[Path]:
        """
        Discover all SKILL.md files in skills directory.
        Returns: List of Path objects pointing to SKILL.md files
        """
        ...
```

**State**:

| Attribute | Type | Description |
|-----------|------|-------------|
| `skills_directory` | `Path` | Directory to scan for skills (default: `~/.claude/skills/`) |

**Operations**:
- `discover_skills() -> List[Path]`: Scan directory and return SKILL.md paths
- `_find_skill_file(directory: Path) -> Optional[Path]`: Case-insensitive SKILL.md lookup

---

### 4. SkillParser

**Purpose**: Parses SKILL.md files and extracts YAML frontmatter + markdown content.

**Location**: `src/skills_use/core/parser.py`

**Definition**:
```python
class SkillParser:
    """
    Parses SKILL.md files with YAML frontmatter.
    v0.1: Minimal parsing - name, description, allowed-tools only.
    """
    FRONTMATTER_DELIMITER = "---"

    def parse_skill_file(self, skill_path: Path) -> SkillMetadata:
        """Parse SKILL.md and extract metadata."""
        ...

    def load_full_content(self, skill_path: Path) -> str:
        """Load full skill content (without frontmatter)."""
        ...
```

**State**: Stateless (no instance variables)

**Operations**:
- `parse_skill_file(path) -> SkillMetadata`: Extract frontmatter → SkillMetadata
- `load_full_content(path) -> str`: Extract markdown content only
- `_extract_frontmatter(content) -> Tuple[Dict, str]`: Split frontmatter/content

---

### 5. SkillManager

**Purpose**: Central orchestration layer managing skill discovery, loading, and invocation.

**Location**: `src/skills_use/core/manager.py`

**Definition**:
```python
class SkillManager:
    """
    Central coordinator for skill discovery, loading, and invocation.
    v0.1: Simple dict-based storage, no caching optimization.
    """
    def __init__(self, skills_directory: Optional[Path] = None):
        self.discovery = SkillDiscovery(skills_directory)
        self.parser = SkillParser()
        self._skills: Dict[str, SkillMetadata] = {}
        self._initialized = False

    def discover(self) -> None: ...
    def list_skills(self) -> List[SkillMetadata]: ...
    def get_skill(self, name: str) -> SkillMetadata: ...
    def load_skill(self, name: str) -> Skill: ...
    def invoke_skill(self, name: str, arguments: str = "") -> str: ...
```

**State**:

| Attribute | Type | Description | Lifecycle |
|-----------|------|-------------|-----------|
| `discovery` | `SkillDiscovery` | Filesystem scanner | Created in `__init__` |
| `parser` | `SkillParser` | YAML/markdown parser | Created in `__init__` |
| `_skills` | `Dict[str, SkillMetadata]` | Skill registry (name → metadata) | Populated in `discover()` |
| `_initialized` | `bool` | Whether discovery has run | False → True on first `discover()` |

**Operations**:
- `discover()`: Scan filesystem, populate `_skills` registry
- `list_skills() -> List[SkillMetadata]`: Return all discovered skills
- `get_skill(name) -> SkillMetadata`: Lookup skill by name (raises SkillNotFoundError)
- `load_skill(name) -> Skill`: Load full skill with content
- `invoke_skill(name, arguments) -> str`: Load + process + return content

**State Transitions**:
```
[Created] --discover()--> [Initialized]
                           |
                           |--list_skills()--> return _skills.values()
                           |--get_skill()----> return _skills[name]
                           |--load_skill()---> [Load content] --> return Skill
                           |--invoke_skill()-> [Load + process] --> return str
```

---

## Relationships

```
SkillManager
    ├── has-a: SkillDiscovery (filesystem scanner)
    ├── has-a: SkillParser (file parser)
    └── has-many: SkillMetadata (skill registry)

Skill
    ├── has-a: SkillMetadata (associated metadata)
    └── references: base_directory (for file operations)

SkillMetadata
    └── references: skill_path (Path to SKILL.md)
```

---

## Exception Hierarchy

**Location**: `src/skills_use/exceptions.py`

```python
SkillsUseError (Base)
├── SkillParsingError      # Malformed SKILL.md
├── SkillNotFoundError     # Skill doesn't exist
└── SkillInvocationError   # Runtime failure (future)
```

**Usage**:
```python
try:
    manager.invoke_skill("nonexistent-skill")
except SkillNotFoundError as e:
    print(f"Skill not found: {e}")
except SkillsUseError as e:
    print(f"General error: {e}")
```

---

## LangChain Integration Models

**Location**: `src/skills_use/integrations/langchain.py`

### SkillInput (Pydantic Model)

**Purpose**: Input schema for LangChain StructuredTool validation.

**Definition**:
```python
class SkillInput(BaseModel):
    """Input schema for LangChain skill tools."""
    arguments: str = Field(
        default="",
        description="Arguments to pass to the skill"
    )
```

**Fields**:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `arguments` | `str` | `""` | User-provided arguments for skill invocation |

**Usage**:
```python
tool = StructuredTool(
    name="code-reviewer",
    description="Reviews Python code",
    func=skill_func,
    args_schema=SkillInput  # Pydantic validation
)
```

---

## Invocation Processing

**Location**: `src/skills_use/core/invocation.py`

**Function**: `process_skill_content(skill: Skill, arguments: str = "") -> str`

**Algorithm**:
```
1. Inject base directory: "Base directory for this skill: {path}\n\n"
2. If "$ARGUMENTS" in content:
   - Replace all occurrences with arguments
3. Else if arguments provided:
   - Append "\n\nARGUMENTS: {arguments}"
4. Return processed content
```

**Transformations**:

| Input Content | Arguments | Output Content |
|---------------|-----------|----------------|
| `Review: $ARGUMENTS` | `"code"` | `Base directory: /path\n\nReview: code` |
| `$ARGUMENTS\n$ARGUMENTS` | `"test"` | `Base directory: /path\n\ntest\ntest` |
| `Review code` | `"foo"` | `Base directory: /path\n\nReview code\n\nARGUMENTS: foo` |

---

## SKILL.md File Format

**Location**: User's filesystem (`~/.claude/skills/skill-name/SKILL.md`)

**Structure**:
```markdown
---
name: skill-name
description: Brief description
allowed-tools: ["tool1", "tool2"]  # Optional
---

Markdown content with $ARGUMENTS placeholder.
```

**Validation Rules**:

| Field | Requirement | Error if Missing |
|-------|-------------|------------------|
| `---` delimiters | Required | SkillParsingError: "No valid YAML frontmatter found" |
| `name` | Required, non-empty string | SkillParsingError: "Missing required field 'name'" |
| `description` | Required, non-empty string | SkillParsingError: "Missing required field 'description'" |
| `allowed-tools` | Optional, list of strings | Warning logged if invalid type |

---

## Data Flow

### Discovery Phase
```
Filesystem
    ↓
SkillDiscovery.discover_skills()
    ↓ (List[Path])
SkillParser.parse_skill_file()
    ↓ (SkillMetadata)
SkillManager._skills[name] = metadata
```

### Invocation Phase
```
User calls manager.invoke_skill(name, arguments)
    ↓
SkillManager.get_skill(name) → SkillMetadata
    ↓
SkillParser.load_full_content(path) → str
    ↓
Create Skill(metadata, content, base_directory)
    ↓
process_skill_content(skill, arguments) → str
    ↓
Return processed content to user
```

### LangChain Integration
```
create_langchain_tools(manager)
    ↓
manager.list_skills() → List[SkillMetadata]
    ↓
For each metadata:
    Create StructuredTool(name, description, func, args_schema)
    ↓
Return List[StructuredTool]
```

---

## Validation Rules Summary

### SkillMetadata Validation
- ✅ `name`: Non-empty string
- ✅ `description`: Non-empty string
- ✅ `skill_path`: Valid Path object
- ⚠️ `allowed_tools`: None or list of strings (warning if invalid)

### SKILL.md Validation
- ✅ Frontmatter delimiters (`---`) present
- ✅ Valid YAML between delimiters
- ✅ Required fields: `name`, `description`
- ✅ UTF-8 encoding

### Invocation Validation
- ✅ Skill must exist in registry (raises SkillNotFoundError)
- ✅ Content must be loadable (raises SkillParsingError)
- ✅ Arguments can be any string (including empty)

---

## Performance Characteristics

| Entity | Memory Footprint | Load Time |
|--------|------------------|-----------|
| SkillMetadata | ~1-5KB | ~5-10ms (YAML parsing) |
| Skill (full content) | ~50-200KB | ~10-20ms (file I/O) |
| SkillManager (10 skills) | ~10-50KB | ~100ms (discovery phase) |

---

## Future Extensions (v0.2+)

### Planned Additions
- **SkillCache**: TTL-based content caching (v0.3)
- **SkillValidator**: Tool restriction enforcement (v0.2)
- **AsyncSkillManager**: Async methods (`adiscover`, `ainvoke_skill`) (v0.2)
- **SkillMetrics**: Invocation tracking, performance monitoring (v0.3)

### Not In Scope for v0.1
- ❌ Skill versioning
- ❌ Skill dependencies
- ❌ Skill marketplace integration
- ❌ Multiple search paths
- ❌ Plugin discovery

---

**Document Version**: 1.0
**Last Updated**: November 3, 2025
**Status**: Complete
