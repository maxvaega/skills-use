# SkillManager API Contract

**Version**: v0.2
**Module**: `skillkit.core.manager`

This document specifies the public API for `SkillManager` in v0.2, including new async methods and multi-source discovery.

---

## Constructor

### `SkillManager.__init__()`

**Signature**:
```python
def __init__(
    self,
    project_skill_dir: Path | str | None = None,
    anthropic_config_dir: Path | str | None = None,
    plugin_dirs: list[Path | str] | None = None,
    additional_search_paths: list[Path | str] | None = None,
) -> None
```

**Parameters**:
- `project_skill_dir` (optional): Path to project skills directory. Default: `./skills/`
- `anthropic_config_dir` (optional): Path to Anthropic config directory. Default: `./.claude/skills/`
- `plugin_dirs` (optional): List of plugin root directories to scan for `.claude-plugin/plugin.json`. Default: `[]`
- `additional_search_paths` (optional): Additional skill directories with custom priority. Default: `[]`

**Behavior**:
- Constructs SkillSource objects for each configured directory
- Assigns priorities: project (100) > anthropic (50) > plugins (10) > additional (5)
- Does NOT perform discovery (call `discover()` or `adiscover()` explicitly)

**Exceptions**:
- `ValueError`: If a configured directory does not exist

**Examples**:
```python
# Minimal - project only
manager = SkillManager()

# Multi-source
manager = SkillManager(
    project_skill_dir="./my-skills",
    anthropic_config_dir="./.claude/skills",
    plugin_dirs=["./plugins/data-tools", "./plugins/web-tools"],
)

# Custom paths
manager = SkillManager(
    additional_search_paths=["./shared-skills", "./team-skills"]
)
```

---

## Discovery Methods

### `discover()` (Sync)

**Signature**:
```python
def discover(self) -> dict[str, SkillMetadata]
```

**Returns**:
- `dict[str, SkillMetadata]`: Mapping of skill names to metadata
  - Keys: Simple names (highest priority version) + qualified names (`plugin:skill`)
  - Values: SkillMetadata objects

**Behavior**:
1. Scans all configured SkillSource directories
2. For plugin sources: Parses `.claude-plugin/plugin.json` manifests
3. Loads SKILL.md files from all skill directories
4. Resolves name conflicts using priority order (project > anthropic > plugins > additional)
5. Stores both simple names (highest priority) and qualified names (`plugin:skill`)
6. Sets init mode to `InitMode.SYNC`

**Side Effects**:
- Populates internal skill registry
- Logs warnings for name conflicts, malformed manifests, invalid SKILL.md files

**Exceptions**:
- `AsyncStateError`: If `adiscover()` was already called
- `DiscoveryError`: If no skills found in any source (may be relaxed to warning)

**Performance**:
- ~5-10ms per skill (YAML parsing dominates)
- Example: 500 skills in ~2.5-5 seconds

**Examples**:
```python
manager = SkillManager(plugin_dirs=["./plugins"])
skills = manager.discover()

print(f"Discovered {len(skills)} skills")
# Simple name access (highest priority)
metadata = skills["csv-parser"]
# Qualified name access (specific plugin)
metadata = skills["data-tools:csv-parser"]
```

### `adiscover()` (Async)

**Signature**:
```python
async def adiscover(self) -> dict[str, SkillMetadata]
```

**Returns**:
- `dict[str, SkillMetadata]`: Same as `discover()`

**Behavior**:
- Same as `discover()`, but uses async file I/O via `asyncio.to_thread()`
- Allows concurrent scanning of multiple sources via `asyncio.gather()`
- Sets init mode to `InitMode.ASYNC`

**Performance**:
- Target: <200ms for 500 skills (50% faster than sync due to concurrent I/O)

**Exceptions**:
- Same as `discover()`
- `AsyncStateError`: If `discover()` was already called

**Examples**:
```python
import asyncio

async def main():
    manager = SkillManager(plugin_dirs=["./plugins"])
    skills = await manager.adiscover()
    print(f"Discovered {len(skills)} skills asynchronously")

asyncio.run(main())
```

---

## Skill Retrieval Methods

### `get_skill()`

**Signature**:
```python
def get_skill(self, name: str) -> Skill
```

**Parameters**:
- `name`: Skill name (simple or qualified: `"skill"` or `"plugin:skill"`)

**Returns**:
- `Skill`: Full skill object with lazy-loaded content

**Behavior**:
1. Parses name as `QualifiedSkillName`
2. Looks up in skill registry
3. Creates `Skill` object with metadata + base directory
4. Caches created Skill objects for reuse

**Exceptions**:
- `SkillNotFoundError`: If name not in registry
- `StateError`: If `discover()` or `adiscover()` not called yet

**Examples**:
```python
# Simple name (highest priority version)
skill = manager.get_skill("csv-parser")

# Qualified name (specific plugin version)
skill = manager.get_skill("data-tools:csv-parser")

# Access skill metadata
print(skill.metadata.description)

# Invoke skill
result = skill.invoke("process data.csv")
```

### `list_skills()`

**Signature**:
```python
def list_skills(self, include_qualified: bool = True) -> list[str]
```

**Parameters**:
- `include_qualified` (optional): Include fully qualified names. Default: `True`

**Returns**:
- `list[str]`: Sorted list of skill names

**Behavior**:
- Returns simple names + qualified names (if `include_qualified=True`)
- Sorted alphabetically

**Examples**:
```python
# All names (simple + qualified)
names = manager.list_skills()
# ["csv-parser", "data-tools:csv-parser", "data-tools:json-parser", ...]

# Simple names only
names = manager.list_skills(include_qualified=False)
# ["csv-parser", "json-parser", ...]
```

---

## Skill Invocation Methods

### `invoke_skill()` (Sync)

**Signature**:
```python
def invoke_skill(self, name: str, arguments: str = "") -> str
```

**Parameters**:
- `name`: Skill name (simple or qualified)
- `arguments` (optional): User arguments for `$ARGUMENTS` substitution. Default: `""`

**Returns**:
- `str`: Processed skill content with base directory + argument substitution

**Behavior**:
1. Retrieves skill via `get_skill(name)`
2. Calls `skill.invoke(arguments)`
3. Returns processed content

**Exceptions**:
- `SkillNotFoundError`: If skill not found
- `ContentLoadError`: If SKILL.md cannot be read
- `ArgumentProcessingError`: If argument substitution fails
- `SizeLimitExceededError`: If arguments exceed 1MB

**Performance**:
- First invocation: ~10-25ms (includes content loading)
- Subsequent: ~1-5ms (content cached)

**Examples**:
```python
# Invoke with arguments
result = manager.invoke_skill("csv-parser", "data.csv")

# Invoke without arguments
result = manager.invoke_skill("help-docs")
```

### `ainvoke_skill()` (Async)

**Signature**:
```python
async def ainvoke_skill(self, name: str, arguments: str = "") -> str
```

**Parameters**:
- Same as `invoke_skill()`

**Returns**:
- Same as `invoke_skill()`

**Behavior**:
- Async version using `asyncio.to_thread()` for file I/O
- Otherwise identical to `invoke_skill()`

**Performance**:
- Adds <2ms overhead compared to sync
- Benefits: Non-blocking for high-concurrency scenarios

**Exceptions**:
- Same as `invoke_skill()`

**Examples**:
```python
async def process_skills():
    # Sequential
    result1 = await manager.ainvoke_skill("csv-parser", "data.csv")
    result2 = await manager.ainvoke_skill("json-parser", "data.json")

    # Concurrent (10+ parallel invocations)
    results = await asyncio.gather(
        manager.ainvoke_skill("skill-1", "arg1"),
        manager.ainvoke_skill("skill-2", "arg2"),
        manager.ainvoke_skill("skill-3", "arg3"),
    )
```

---

## Properties

### `init_mode`

**Signature**:
```python
@property
def init_mode(self) -> InitMode
```

**Returns**:
- `InitMode`: Current initialization state (UNINITIALIZED | SYNC | ASYNC)

**Usage**:
```python
manager = SkillManager()
print(manager.init_mode)  # InitMode.UNINITIALIZED

manager.discover()
print(manager.init_mode)  # InitMode.SYNC

# Attempting adiscover() now raises AsyncStateError
```

---

## Error Handling

### Exception Hierarchy

```
SkillKitError (base)
├── DiscoveryError
│   ├── PluginManifestError (malformed plugin.json)
│   └── SkillParseError (invalid SKILL.md)
├── SkillNotFoundError (skill name not in registry)
├── ContentLoadError (file I/O errors)
├── ProcessingError
│   ├── ArgumentProcessingError ($ARGUMENTS substitution)
│   └── SizeLimitExceededError (arguments > 1MB)
├── PathSecurityError (path traversal attempt)
├── AsyncStateError (mixing sync/async init)
└── StateError (method called before discovery)
```

### Error Messages

All exceptions include:
- Clear description of what failed
- Context (skill name, file path, plugin name)
- Actionable remediation when applicable

**Examples**:
```python
# SkillNotFoundError
"Skill 'csv-parser' not found. Available skills: ['json-parser', 'xml-parser']. Did you mean 'json-parser'?"

# PluginManifestError
"Failed to parse plugin manifest at ./plugins/foo/.claude-plugin/plugin.json: Missing required field 'name'"

# PathSecurityError
"Path traversal attempt detected in skill 'my-skill': '../../../etc/passwd' escapes base directory './skills/my-skill/'"

# AsyncStateError
"Cannot call adiscover() after discover(). SkillManager is already initialized in SYNC mode."
```

---

## Backward Compatibility

### v0.1 APIs (Unchanged)

These methods remain fully compatible:
- `SkillManager.__init__(skill_dir: Path | str)` - Now accepts as `project_skill_dir`
- `discover() -> dict[str, SkillMetadata]` - Signature unchanged
- `get_skill(name: str) -> Skill` - Signature unchanged
- `invoke_skill(name, arguments) -> str` - Signature unchanged
- `list_skills() -> list[str]` - Signature unchanged (new `include_qualified` parameter is optional)

### Migration Notes

**v0.1 code works unchanged**:
```python
# v0.1 usage (still works)
manager = SkillManager("./skills")
manager.discover()
result = manager.invoke_skill("my-skill", "args")
```

**v0.2 enhancements are opt-in**:
```python
# v0.2 multi-source (backward compatible)
manager = SkillManager(
    project_skill_dir="./skills",  # was skill_dir in v0.1
    plugin_dirs=["./plugins"]       # new in v0.2
)
await manager.adiscover()  # new in v0.2
```

---

## Thread Safety

### Sync Methods
- **Thread-safe after discovery**: Multiple threads can call `get_skill()`, `invoke_skill()`, `list_skills()` concurrently
- **NOT thread-safe during discovery**: Do not call `discover()` from multiple threads

### Async Methods
- **Asyncio-safe**: All async methods use proper async primitives
- **Concurrency safe**: Multiple coroutines can call `ainvoke_skill()` concurrently

### Caveats
- Skill content caching uses `@cached_property` (not thread-safe on first access)
- Recommendation: Perform discovery once at application startup
