# Data Model: v0.2 - Async Support, Advanced Discovery & File Resolution

**Feature**: v0.2 Async, Multi-Source Discovery, File Path Resolution
**Generated**: 2025-11-12

## Overview

This document defines the data models for v0.2, extending the v0.1 foundation with support for:
- Multiple skill sources with priority-based conflict resolution
- Plugin manifest parsing and namespace management
- Secure file path resolution within skill directories
- Async/sync state management

All v0.1 entities (SkillMetadata, Skill) are preserved unchanged for backward compatibility.

---

## Core Entities (v0.1 - Unchanged)

### SkillMetadata

**Purpose**: Lightweight metadata loaded during discovery phase

**Attributes**:
- `name: str` - Unique skill identifier within its source
- `description: str` - Human-readable skill purpose
- `skill_path: Path` - Absolute path to SKILL.md file
- `allowed_tools: tuple[str, ...]` - Tool restriction list (not enforced in v0.2)

**Validation Rules**:
- `name` must be non-empty string
- `skill_path` must exist at construction time
- `allowed_tools` defaults to empty tuple

**Memory**: ~400-800 bytes per instance (Python 3.10+)

### Skill

**Purpose**: Full skill with lazy-loaded content and processing

**Attributes**:
- `metadata: SkillMetadata` - Lightweight metadata reference
- `base_directory: Path` - Base directory context for skill execution
- `_processor: CompositeProcessor` - Content processing chain (internal)

**Relationships**:
- **Has-One** SkillMetadata (composition)
- **Uses** CompositeProcessor for content transformation

**State Transitions**: None (immutable after construction)

**Methods**:
- `content: str` - Lazy-loaded SKILL.md content (cached property)
- `invoke(arguments: str) -> str` - Process content with arguments

---

## New Entities (v0.2)

### SkillSource

**Purpose**: Represents a skill source location with priority and metadata

**Attributes**:
- `source_type: SourceType` - Enum: PROJECT | ANTHROPIC | PLUGIN | CUSTOM
- `directory: Path` - Absolute path to skill root directory
- `priority: int` - Priority for conflict resolution (higher = wins)
- `plugin_name: str | None` - Plugin namespace (only for PLUGIN type)
- `plugin_manifest: PluginManifest | None` - Parsed manifest (only for PLUGIN type)

**Validation Rules**:
- `directory` must exist and be a directory
- `priority` must be positive integer
- `plugin_name` required when `source_type == SourceType.PLUGIN`
- `plugin_manifest` required when `source_type == SourceType.PLUGIN`

**Default Priorities**:
- PROJECT: 100
- ANTHROPIC: 50
- PLUGIN: 10
- CUSTOM: 5

**Relationships**:
- **May-Have-One** PluginManifest (composition, only for plugins)

**Example**:
```python
# Project source
SkillSource(
    source_type=SourceType.PROJECT,
    directory=Path("./skills"),
    priority=100,
    plugin_name=None,
    plugin_manifest=None
)

# Plugin source
SkillSource(
    source_type=SourceType.PLUGIN,
    directory=Path("./plugins/my-plugin"),
    priority=10,
    plugin_name="my-plugin",
    plugin_manifest=PluginManifest(...)
)
```

### PluginManifest

**Purpose**: Parsed metadata from `.claude-plugin/plugin.json`

**Attributes**:
- `name: str` - Plugin identifier (must be valid Python identifier)
- `version: str` - Semantic version (e.g., "1.0.0")
- `description: str` - Plugin purpose
- `author: str | None` - Plugin author
- `skills: list[str]` - Additional skill directories relative to plugin root
- `manifest_path: Path` - Path to plugin.json file (for error reporting)

**Validation Rules**:
- `name` must match regex: `^[a-z0-9-]+$` (lowercase, alphanumeric, hyphens only)
- `version` must be valid semantic version (major.minor.patch)
- `description` required, non-empty
- `skills` defaults to `["skills/"]` if not specified
- Each path in `skills` must be relative (no `..` or absolute paths)

**JSON Schema** (from `.claude-plugin/plugin.json`):
```json
{
  "name": "my-plugin",          // REQUIRED
  "version": "1.0.0",           // REQUIRED
  "description": "...",         // REQUIRED
  "author": "John Doe",         // OPTIONAL
  "skills": ["skills/", "extra/"] // OPTIONAL (default: ["skills/"])
}
```

**Parsing**:
- Located at: `<plugin-root>/.claude-plugin/plugin.json`
- Parsed with: `json.load()` + pydantic validation
- Errors raise: `PluginManifestError` with clear message

**Example**:
```python
PluginManifest(
    name="data-tools",
    version="2.1.0",
    description="Data processing skills",
    author="Data Team",
    skills=["skills/", "experimental/"],
    manifest_path=Path("./plugins/data-tools/.claude-plugin/plugin.json")
)
```

### QualifiedSkillName

**Purpose**: Skill identifier with optional plugin namespace

**Attributes**:
- `plugin: str | None` - Plugin name (if qualified)
- `skill: str` - Skill name

**Parsing Rules**:
- Format: `"plugin:skill"` (qualified) or `"skill"` (unqualified)
- Plugin part must match: `^[a-z0-9-]+$`
- Skill part must be non-empty

**Validation Rules**:
- Qualified names cannot have empty plugin or skill parts
- Colon (`:`) is reserved separator, cannot appear in skill names without plugin

**Examples**:
```python
# Unqualified (simple name)
QualifiedSkillName.parse("csv-parser")
# Result: QualifiedSkillName(plugin=None, skill="csv-parser")

# Qualified (plugin namespace)
QualifiedSkillName.parse("data-tools:csv-parser")
# Result: QualifiedSkillName(plugin="data-tools", skill="csv-parser")

# Invalid - multiple colons
QualifiedSkillName.parse("foo:bar:baz")
# Raises: ValueError("Invalid qualified name format")
```

**Use Cases**:
- Explicit plugin skill retrieval: `manager.get_skill("my-plugin:skill")`
- Conflict resolution: Force plugin version when project has same name
- Skill listing: Display full qualified names to users

### SkillPath

**Purpose**: Validated file path within a skill directory (security wrapper)

**Attributes**:
- `base_directory: Path` - Skill base directory (validated container)
- `relative_path: str` - User-provided relative path
- `resolved_path: Path` - Validated absolute path (computed)

**Validation Rules**:
- `relative_path` must not be absolute
- `relative_path` must not contain `..` that escapes `base_directory`
- `resolved_path` must be descendant of `base_directory` (checked via `is_relative_to()`)
- Symlinks are resolved before validation

**Security Properties**:
- **Path Traversal Prevention**: All `..` sequences validated after resolution
- **Symlink Handling**: Resolved to target, then validated target is within base
- **Canonical Paths**: Uses `Path.resolve()` to normalize before checking

**Exceptions**:
- Raises `PathSecurityError` if validation fails
- Error message includes attempted path and skill name for logging

**Example**:
```python
# Valid: subdirectory access
SkillPath.validate(
    base_directory=Path("/skills/my-skill"),
    relative_path="scripts/helper.py"
)
# Result: Path("/skills/my-skill/scripts/helper.py")

# Invalid: directory traversal attempt
SkillPath.validate(
    base_directory=Path("/skills/my-skill"),
    relative_path="../../../etc/passwd"
)
# Raises: PathSecurityError("Path traversal attempt detected...")
```

**Implementation Note**:
- This is a utility class, not stored as entity
- Used during `Skill.invoke()` to resolve file references

---

## Enumerations

### SourceType

**Purpose**: Skill source type classification

**Values**:
- `PROJECT = "project"` - Project-specific skills (./skills/)
- `ANTHROPIC = "anthropic"` - Anthropic config skills (./.claude/skills/)
- `PLUGIN = "plugin"` - Plugin skills (./plugins/*/skills/)
- `CUSTOM = "custom"` - Additional user paths

**Usage**:
```python
from enum import Enum

class SourceType(str, Enum):
    PROJECT = "project"
    ANTHROPIC = "anthropic"
    PLUGIN = "plugin"
    CUSTOM = "custom"
```

### InitMode

**Purpose**: Tracks SkillManager initialization state

**Values**:
- `UNINITIALIZED = "uninitialized"` - No discovery run yet
- `SYNC = "sync"` - Initialized via `discover()`
- `ASYNC = "async"` - Initialized via `adiscover()`

**Usage**:
- Prevents mixing sync and async initialization
- Raises `AsyncStateError` when attempting to mix

**State Transitions**:
```
UNINITIALIZED → SYNC (via discover())
UNINITIALIZED → ASYNC (via adiscover())
SYNC → SYNC (no-op, already initialized)
ASYNC → ASYNC (no-op, already initialized)
SYNC ↛ ASYNC (ERROR: AsyncStateError)
ASYNC ↛ SYNC (ERROR: AsyncStateError)
```

---

## Relationships

### SkillManager → SkillSource (1:N)
- **Cardinality**: One manager, many sources
- **Storage**: `list[SkillSource]` sorted by priority (descending)
- **Lifecycle**: Sources configured at manager construction, immutable thereafter

### SkillSource → SkillMetadata (1:N)
- **Cardinality**: One source, many skills discovered
- **Mapping**: Skills tracked in manager's `dict[str, SkillMetadata]` with source reference
- **Lifecycle**: Metadata loaded during discovery, cached until manager destroyed

### PluginManifest → SkillMetadata (1:N)
- **Cardinality**: One plugin, many skills (from manifest.skills directories)
- **Namespace**: All skills prefixed with plugin name: `{plugin.name}:{skill.name}`
- **Lifecycle**: Plugin skills loaded during plugin source discovery

### Skill → SkillPath (1:N)
- **Cardinality**: One skill, many supporting files
- **Usage**: During `invoke()`, relative paths in content are resolved via SkillPath
- **Lifecycle**: Validated on-demand when skill accesses supporting files

---

## Data Flow

### Discovery Flow (Multi-Source)

1. **SkillManager** receives `list[SkillSource]` (sorted by priority)
2. **SkillDiscovery** scans each source in order:
   - For PLUGIN sources: Parse `.claude-plugin/plugin.json` → PluginManifest
   - Scan `manifest.skills` directories for SKILL.md files
3. **SkillParser** extracts metadata from each SKILL.md
4. **SkillManager** stores in `dict[str, SkillMetadata]`:
   - Key: Simple name (unqualified) for highest priority version
   - Key: Qualified name (`plugin:skill`) for plugin versions
5. Conflicts logged as warnings with paths

### Invocation Flow (File Path Resolution)

1. **User** calls `manager.invoke_skill("my-skill", "args")`
2. **SkillManager** retrieves `Skill` object from cache/creates new
3. **Skill.invoke()** processes content:
   - Loads content (lazy, cached)
   - **BaseDirectoryProcessor** injects: `Base directory: {base_directory}`
   - **ArgumentSubstitutionProcessor** replaces `$ARGUMENTS`
4. **LLM** reads processed content, references supporting files (e.g., "scripts/helper.py")
5. **User/LLM** accesses file via `SkillPath.validate(base_directory, "scripts/helper.py")`
6. **SkillPath** validates and returns absolute path or raises `PathSecurityError`

---

## Memory Characteristics (Updated for v0.2)

### Per-Skill Overhead

| Entity | Size | Count (500 skills) | Total Memory |
|--------|------|-------------------|--------------|
| SkillMetadata | ~600 bytes | 500 | ~300 KB |
| SkillSource | ~200 bytes | 10 sources | ~2 KB |
| PluginManifest | ~400 bytes | 5 plugins | ~2 KB |
| Skill (cached) | ~800 bytes + 100 KB content | 50 active | ~5 MB |
| **Total** | - | - | **~5.3 MB** |

**Optimization Notes**:
- SkillMetadata uses `slots=True` (60% memory reduction)
- Skill content lazy-loaded (only 10% typically loaded)
- SkillSource/PluginManifest loaded once, shared across all skills from that source

### Async Memory Overhead

**No additional memory overhead** compared to sync:
- Async methods use same dataclasses
- `asyncio.to_thread()` creates thread-local copies (negligible for file reads)
- No coroutine state stored between invocations

---

## Validation Summary

### Construction-Time Validation

- **SkillMetadata**: `skill_path.exists()` check
- **SkillSource**: `directory.exists()` + type-specific constraints
- **PluginManifest**: JSON schema validation + name regex + version format
- **QualifiedSkillName**: Format validation (`plugin:skill` or `skill`)

### Runtime Validation

- **Skill.content**: UTF-8 encoding, file still exists, permissions
- **SkillPath**: Path traversal prevention, symlink resolution, descendant check
- **SkillManager.get_skill()**: Name exists, not ambiguous (if unqualified)

### Error Handling

All validation errors raise domain-specific exceptions:
- `SkillNotFoundError` - Skill name not found in registry
- `PluginManifestError` - Manifest parsing or validation failed
- `PathSecurityError` - Path traversal attempt detected
- `AsyncStateError` - Mixing sync/async initialization
- `ContentLoadError` - File I/O errors during content loading

---

## Testing Considerations

### Unit Test Coverage

- **SkillSource**: Priority ordering, type validation, plugin-specific constraints
- **PluginManifest**: Valid manifests, malformed JSON, missing required fields, invalid version
- **QualifiedSkillName**: Parsing variants (qualified/unqualified), invalid formats
- **SkillPath**: 7 attack vectors (see research.md), symlink handling, case sensitivity

### Integration Test Scenarios

- **Multi-source discovery**: 3 sources (project/anthropic/plugin), verify priority resolution
- **Name conflicts**: Same skill in 2 sources, verify highest priority wins, qualified access works
- **Nested plugin skills**: Plugin with `skills=["a/", "b/"]`, verify all discovered
- **Path resolution**: Skill invocation with supporting files, verify paths resolved correctly

### Security Test Requirements

- **Path traversal fuzzing**: Test 100+ malicious path patterns
- **Symlink attacks**: Circular symlinks, symlinks escaping base, symlinks to sensitive files
- **Plugin manifest injection**: Malicious JSON, oversized manifests, invalid encodings
- **Async race conditions**: Concurrent discovery, concurrent invocation, state corruption attempts
