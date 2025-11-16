# Data Model: skillkit v0.1 MVP

**Feature**: Core Functionality & LangChain Integration
**Branch**: `001-mvp-langchain-core`
**Date**: November 4, 2025

## Overview

This document defines the core data model for the skillkit library, including entities, relationships, validation rules, and state transitions. The design follows a two-tier progressive disclosure pattern for memory efficiency.

---

## Core Entities

### 1. SkillMetadata (Tier 1 - Lightweight)

**Purpose**: Represents discovered skill information without loading full content. Enables browsing and selection of skills with minimal memory footprint.

**Definition**:
```python
from dataclasses import dataclass, field
from pathlib import Path

@dataclass(frozen=True, slots=True)
class SkillMetadata:
    """Lightweight skill metadata loaded during discovery phase.

    Memory: ~400-800 bytes per instance (Python 3.10+)
    Immutable: frozen=True prevents accidental mutation
    Optimized: slots=True reduces memory by 60%
    """

    name: str
    """Unique skill identifier (from YAML frontmatter)."""

    description: str
    """Human-readable description of skill purpose."""

    skill_path: Path
    """Absolute path to SKILL.md file."""

    allowed_tools: tuple[str, ...] = field(default_factory=tuple)
    """Tool names allowed for this skill (optional, not enforced in v0.1)."""

    def __post_init__(self):
        """Validate skill path exists on construction."""
        if not self.skill_path.exists():
            raise ValueError(f"Skill path does not exist: {self.skill_path}")
```

**Attributes**:
- `name` (str, required): Skill identifier from YAML `name` field
- `description` (str, required): Skill purpose from YAML `description` field
- `skill_path` (Path, required): Absolute path to SKILL.md file
- `allowed_tools` (tuple[str, ...], optional): Tool restrictions (default: empty tuple)

**Validation Rules**:
- ✅ `name` must be non-empty string after `.strip()`
- ✅ `description` must be non-empty string after `.strip()`
- ✅ `skill_path` must exist on filesystem (checked in `__post_init__`)
- ✅ `allowed_tools` must be tuple of strings (converted from list during parsing)
- ✅ Immutable after construction (`frozen=True`)

**Memory Characteristics**:
- Python 3.10+: ~400-800 bytes per instance (`slots=True`)
- Python 3.9: ~1-2KB per instance (no slots support)
- 100 instances: ~40-200KB total

---

### 2. Skill (Tier 2 - Full with Lazy Content)

**Purpose**: Represents a fully loaded skill with content. Content is loaded on-demand via `@cached_property` for efficiency.

**Definition**:
```python
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

@dataclass(frozen=True, slots=True)  # slots=True requires Python 3.10+
class Skill:
    """Full skill with lazy-loaded content.

    Memory: ~400-800 bytes wrapper + ~50-200KB content (when loaded)
    Content loading: On-demand via @cached_property
    Processing: Via CompositeProcessor (base directory + arguments)

    Note: For Python 3.9, remove slots=True from this class only.
          SkillMetadata retains slots for memory optimization.
    """

    metadata: SkillMetadata
    """Lightweight metadata from discovery phase."""

    base_directory: Path
    """Base directory context for skill execution."""

    _processor: 'CompositeProcessor' = field(init=False, repr=False)
    """Content processor chain (initialized in __post_init__)."""

    def __post_init__(self):
        """Initialize processor chain (avoids inline imports anti-pattern)."""
        from skillkit.core.processors import (
            CompositeProcessor,
            BaseDirectoryProcessor,
            ArgumentSubstitutionProcessor
        )

        # Use object.__setattr__ because dataclass is frozen
        object.__setattr__(
            self,
            '_processor',
            CompositeProcessor([
                BaseDirectoryProcessor(),
                ArgumentSubstitutionProcessor()
            ])
        )

    @cached_property
    def content(self) -> str:
        """Lazy load content only when accessed.

        Raises:
            ContentLoadError: If file cannot be read (deleted, permissions, encoding)
        """
        from skillkit.core.exceptions import ContentLoadError

        try:
            return self.metadata.skill_path.read_text(encoding="utf-8")
        except FileNotFoundError as e:
            raise ContentLoadError(
                f"Skill file not found: {self.metadata.skill_path}. "
                f"File may have been deleted after discovery."
            ) from e
        except PermissionError as e:
            raise ContentLoadError(
                f"Permission denied reading skill: {self.metadata.skill_path}"
            ) from e
        except UnicodeDecodeError as e:
            raise ContentLoadError(
                f"Skill file contains invalid UTF-8: {self.metadata.skill_path}"
            ) from e

    def invoke(self, arguments: str = "") -> str:
        """Process skill content with arguments.

        Args:
            arguments: User-provided arguments for skill invocation

        Returns:
            Processed skill content with base directory + argument substitution

        Raises:
            ContentLoadError: If content cannot be loaded
            ArgumentProcessingError: If argument processing fails
            SizeLimitExceededError: If arguments exceed 1MB
        """
        context = {
            "arguments": arguments,
            "base_directory": str(self.base_directory),
            "skill_name": self.metadata.name
        }
        return self._processor.process(self.content, context)
```

**Attributes**:
- `metadata` (SkillMetadata, required): Lightweight metadata from discovery
- `base_directory` (Path, required): Base directory for skill context
- `_processor` (CompositeProcessor, internal): Content processing chain
- `content` (str, lazy property): Full SKILL.md markdown content

**Validation Rules**:
- ✅ Content loaded with UTF-8 encoding (security requirement)
- ✅ Content cached after first access (`@cached_property`)
- ✅ Processor chain initialized in `__post_init__` (not inline)
- ✅ Immutable after construction (`frozen=True`)

**Memory Characteristics**:
- Wrapper: ~400-800 bytes (Python 3.10+), ~1-2KB (Python 3.9)
- Content: ~50-200KB per skill (only when `content` property accessed)
- 100 skills with 10% usage: ~2-2.5MB total (80% reduction vs eager loading)

**State Lifecycle**:
1. **Discovered**: SkillMetadata created, no content loaded
2. **Loaded**: Skill instance created, content still not loaded
3. **Invoked**: `content` property accessed, file read and cached
4. **Processed**: `invoke()` called, content transformed with arguments

---

### 3. SkillManager (Orchestration Layer)

**Purpose**: Central registry managing skill discovery, access, and invocation. Single entry point for all skill operations.

**Definition**:
```python
from pathlib import Path
from typing import List, Dict

class SkillManager:
    """Central skill registry with discovery and invocation capabilities.

    Discovery: Graceful degradation (log errors, continue processing)
    Invocation: Strict validation (raise specific exceptions)
    Thread-safety: Not guaranteed in v0.1 (single-threaded usage assumed)
    """

    def __init__(self, skills_dir: Path | None = None):
        """Initialize skill manager.

        Args:
            skills_dir: Path to skills directory (default: ~/.claude/skills/)
        """
        from pathlib import Path

        if skills_dir is None:
            skills_dir = Path.home() / ".claude" / "skills"

        self.skills_dir = skills_dir
        self._skills: Dict[str, SkillMetadata] = {}
        self._parser = SkillParser()
        self._discovery = SkillDiscovery()

    def discover(self) -> None:
        """Discover skills from skills_dir (graceful degradation)."""
        # Implementation: See contracts/public-api.md
        pass

    def list_skills(self) -> List[SkillMetadata]:
        """Return all discovered skill metadata (lightweight)."""
        return list(self._skills.values())

    def get_skill(self, name: str) -> SkillMetadata:
        """Get skill metadata by name (strict validation).

        Raises:
            SkillNotFoundError: If skill name not in registry
        """
        # Implementation: See contracts/public-api.md
        pass

    def load_skill(self, name: str) -> Skill:
        """Load full skill instance (content loaded lazily)."""
        # Implementation: See contracts/public-api.md
        pass

    def invoke_skill(self, name: str, arguments: str = "") -> str:
        """Load and invoke skill in one call (convenience method)."""
        # Implementation: See contracts/public-api.md
        pass
```

**Attributes**:
- `skills_dir` (Path): Root directory for skill discovery
- `_skills` (Dict[str, SkillMetadata]): Internal skill registry (name → metadata)
- `_parser` (SkillParser): YAML frontmatter parser
- `_discovery` (SkillDiscovery): Filesystem scanner

**Validation Rules**:
- ✅ Discovery: Continue on individual skill errors (graceful degradation)
- ✅ Invocation: Raise exceptions on errors (strict validation)
- ✅ Duplicate names: First discovered skill wins, log WARNING
- ✅ Empty directory: Return empty list, log INFO

---

### 4. ContentProcessor (Strategy Pattern)

**Purpose**: Provides pluggable content processing strategies. Enables composition of processing steps (base directory injection, argument substitution, future extensions).

**Definition**:
```python
from abc import ABC, abstractmethod

class ContentProcessor(ABC):
    """Abstract base for content processing strategies."""

    @abstractmethod
    def process(self, content: str, context: dict) -> str:
        """Process content with given context.

        Args:
            content: Raw skill content
            context: Processing context (arguments, base_directory, skill_name)

        Returns:
            Processed content

        Raises:
            Various processing-specific exceptions
        """
        pass

class BaseDirectoryProcessor(ContentProcessor):
    """Injects base directory context at beginning."""

    def process(self, content: str, context: dict) -> str:
        base_dir = context.get("base_directory", "")
        return f"Base directory for this skill: {base_dir}\n\n{content}"

class ArgumentSubstitutionProcessor(ContentProcessor):
    """Handles $ARGUMENTS placeholder using string.Template."""

    PLACEHOLDER_NAME = "ARGUMENTS"
    MAX_ARGUMENT_LENGTH = 1_000_000  # 1MB

    def process(self, content: str, context: dict) -> str:
        # Implementation: See research.md Decision 3
        pass

class CompositeProcessor(ContentProcessor):
    """Chains multiple processors in order."""

    def __init__(self, processors: list[ContentProcessor]):
        self.processors = processors

    def process(self, content: str, context: dict) -> str:
        result = content
        for processor in self.processors:
            result = processor.process(result, context)
        return result
```

**Design Benefits**:
- ✅ Single Responsibility: Each processor handles one concern
- ✅ Open/Closed Principle: Add new processors without modifying existing
- ✅ Testability: Each processor tested in isolation
- ✅ Extensibility: Chain processors in any order

---

## Entity Relationships

```
SkillManager (1) ──discovers──> (N) SkillMetadata
     │
     └──loads──> (N) Skill
                   │
                   ├──contains──> (1) SkillMetadata
                   └──processes_via──> (1) CompositeProcessor
                                           │
                                           └──chains──> (N) ContentProcessor
```

**Cardinality**:
- SkillManager : SkillMetadata = 1 : N (one manager, many skills)
- SkillManager : Skill = 1 : N (manager loads many skills on-demand)
- Skill : SkillMetadata = 1 : 1 (each skill has one metadata)
- CompositeProcessor : ContentProcessor = 1 : N (one composite, many strategies)

**Ownership**:
- SkillManager owns SkillMetadata instances (stored in `_skills` dict)
- Skill references SkillMetadata (composition, not ownership)
- Skill owns CompositeProcessor (created in `__post_init__`)

---

## State Transitions

### Skill Discovery Lifecycle

```
[Filesystem] → [Discovery] → [Parsing] → [Validation] → [Registry]
     │              │            │            │              │
     │              ├─error──────┴────log─────┘              │
     │              └─continue_with_next──────────────────────┘
     │
     └─empty_dir────────────────────────────────────────────>[]
```

**States**:
1. **Undiscovered**: Skill exists on filesystem, not yet scanned
2. **Discovered**: SkillMetadata created, stored in registry
3. **Error**: Parsing failed, logged and skipped (graceful degradation)

### Skill Invocation Lifecycle

```
[Get Metadata] → [Load Skill] → [Access Content] → [Process] → [Return]
       │              │                │              │
       └─not_found────┴─exception──────┴──exception───┘
```

**States**:
1. **Metadata Retrieved**: SkillManager.get_skill(name) succeeds
2. **Skill Loaded**: Skill instance created (content not yet loaded)
3. **Content Loaded**: `content` property accessed, file read and cached
4. **Processed**: `invoke()` called, content transformed with context
5. **Returned**: Processed string returned to caller

---

## Validation Rules Summary

### SkillMetadata Validation
- ✅ `name` non-empty after `.strip()`
- ✅ `description` non-empty after `.strip()`
- ✅ `skill_path` exists on filesystem
- ✅ `allowed_tools` is tuple of strings (empty tuple if missing)
- ✅ Immutable after construction

### Skill Validation
- ✅ Content encoding UTF-8 with BOM auto-stripping (`utf-8-sig`)
- ✅ Content cached after first access
- ✅ Processor chain initialized correctly
- ✅ Immutable after construction

### Invocation Validation
- ✅ Skill name exists in registry (raise SkillNotFoundError)
- ✅ Arguments size ≤ 1MB (raise SizeLimitExceededError)
- ✅ Suspicious patterns logged (defense-in-depth, not blocked)
- ✅ Content file readable (raise ContentLoadError)

### YAML Frontmatter Validation
- ✅ Delimiters present (`---` at start and end)
- ✅ Valid YAML syntax (raise InvalidYAMLError with line/column)
- ✅ Required fields present (`name`, `description`)
- ✅ Optional fields well-formed (`allowed-tools` is list of strings)
- ✅ Unknown fields ignored with DEBUG log (forward compatibility)

---

## Data Flow

### Discovery Flow

```
1. SkillManager.discover()
   └─> SkillDiscovery.scan(skills_dir)
       └─> For each skill directory:
           ├─> SkillParser.parse_skill_file(SKILL.md)
           │   └─> Extract YAML frontmatter
           │   └─> Validate required fields
           │   └─> Create SkillMetadata
           └─> Store in SkillManager._skills dict
               (handle duplicates: log WARNING, keep first)
```

### Invocation Flow

```
2. SkillManager.invoke_skill(name, arguments)
   └─> SkillManager.load_skill(name)
       ├─> SkillManager.get_skill(name) → SkillMetadata
       └─> Create Skill(metadata, base_directory)
   └─> Skill.invoke(arguments)
       ├─> Access Skill.content (lazy load, cache)
       └─> CompositeProcessor.process(content, context)
           ├─> BaseDirectoryProcessor.process()
           └─> ArgumentSubstitutionProcessor.process()
   └─> Return processed string
```

### LangChain Integration Flow

```
3. create_langchain_tools(manager)
   └─> For each SkillMetadata in manager.list_skills():
       └─> Create StructuredTool
           ├─> name = metadata.name
           ├─> description = metadata.description
           ├─> args_schema = SkillInput (single string parameter)
           └─> func = lambda args: manager.invoke_skill(name, args)
               (with closure capture via default parameter)
```

---

## Performance Characteristics

### Memory Usage
- **Discovery**: ~40-200KB for 100 skills (metadata only)
- **Invocation**: +50-200KB per skill when content loaded
- **Total (10% usage)**: ~2-2.5MB for 100 skills (80% reduction vs eager)

### Latency
- **Discovery**: ~5-10ms per skill (YAML parsing dominates)
- **Invocation**: ~10-25ms overhead (10-20ms file I/O + 1-5ms processing)
- **LLM inference**: ~2000-5000ms (dominates total latency)

### Scalability
- **Target**: 10-20 skills for v0.1 users
- **Design supports**: 100+ skills via progressive disclosure
- **Bottleneck**: Filesystem I/O during discovery (parallelization deferred to v0.3)

---

## Python Version Compatibility

**Python 3.10+ (Recommended)**:
- Full `slots=True` support on both SkillMetadata and Skill
- Memory: ~2.0MB for 100 skills with 10% usage
- Performance: Optimal

**Python 3.9 (Supported)**:
- `slots=True` on SkillMetadata only (remove from Skill class)
- Memory: ~2.5MB for 100 skills with 10% usage (~25% increase)
- Performance: Acceptable (still 80% reduction vs eager loading)

**Rationale**: Minor memory trade-off acceptable to avoid attrs dependency (conflicts with zero-dependency core goal).

---

## Future Enhancements (Deferred)

**v0.2**:
- Async methods: `adiscover()`, `aload_skill()`, `ainvoke_skill()`
- Enhanced error handling: More granular exception types
- Caching: In-memory cache for frequently used skills

**v0.3**:
- Multiple search paths: Prioritized skill directories
- Plugin integration: Dynamic skill loading from plugins
- Tool restriction enforcement: Validate allowed-tools at runtime

**v1.0**:
- Nested directory support: Skills organized in subdirectories
- Skill versioning: Version constraints and compatibility checks
- Conflict resolution: Priority-based duplicate handling

---

**Document Version**: 1.0
**Date**: November 4, 2025
**Status**: Phase 1 Complete - Ready for contracts generation
