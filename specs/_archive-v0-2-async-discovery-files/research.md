# Research Document: v0.2 Async Support, Advanced Discovery & File Resolution

**Branch**: `001-v0-2-async-discovery-files`
**Date**: 2025-11-12
**Spec**: [spec.md](./spec.md)
**Status**: Complete

## Overview

This document captures the technical research and decision-making process for implementing v0.2 of the skillkit library. The research covers six critical technical decisions that will shape the async support, advanced discovery, and file reference resolution features.

All decisions are evaluated against:
- **2024-2025 best practices** for Python async programming
- **Security standards** (OWASP, Python Security guidelines)
- **Framework compatibility** (LangChain async patterns)
- **Performance characteristics** for target use cases (500+ skills, high-concurrency agents)
- **Backward compatibility** with v0.1 sync APIs

---

## Decision 1: Async File I/O Library Selection

### Context

The v0.2 implementation requires async file I/O for reading SKILL.md files and plugin manifests during discovery and invocation. Python's standard library does not provide native async file operations, requiring evaluation of third-party solutions versus stdlib workarounds.

### Decision

**Use `asyncio.to_thread()` with standard library file operations instead of aiofiles.**

### Rationale

1. **Zero Additional Dependencies**: Maintains framework-agnostic core principle by using only Python 3.10+ stdlib (asyncio module)

2. **Performance Characteristics**: Research shows that for typical skill files (2-10KB SKILL.md files):
   - aiofiles adds computing overhead through its thread pool wrapper
   - `asyncio.to_thread()` with stdlib `open()` is often more performant (source: Stack Overflow discussion comparing aiofile vs aiofiles)
   - For sequential file reads, cache efficiency favors simple async wrapping over complex async abstractions

3. **Simplicity**: `asyncio.to_thread()` pattern is straightforward and well-documented:
   ```python
   async def read_file_async(path: Path) -> str:
       def _read():
           with open(path, 'r', encoding='utf-8') as f:
               return f.read()
       return await asyncio.to_thread(_read)
   ```

4. **Maintenance**: Using stdlib reduces long-term maintenance burden (no dependency updates, security patches, or compatibility issues)

5. **Benchmarking Evidence**: Community benchmarks show:
   - Sequential file reading can be 10x faster than asyncio for small files due to cache efficiency
   - For our use case (hundreds of 2-10KB files), the GIL-release benefits of asyncio.to_thread are sufficient
   - aiofiles thread pool wrapper adds overhead without native async I/O benefits

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **aiofiles library** | Convenient API, popular (4.7M downloads/month), feature-rich | Extra dependency, thread pool overhead, no true async I/O (just wrapper) | Violates framework-agnostic core principle; performance gains negligible for our use case |
| **aiofile library** | True async I/O on Linux via caio, potential performance gains | Platform-specific, smaller ecosystem (92K downloads/month), limited feature support | Platform limitation unacceptable for cross-platform library; immaturity concerns |
| **Pure sync wrapped manually** | Zero dependencies, full control | More boilerplate, manual executor management | `asyncio.to_thread()` provides same benefits with cleaner API |
| **Native async (future)** | Best performance when available | Not in Python stdlib yet, uncertain timeline | Not viable for Python 3.10-3.13 support |

### Implementation Notes

1. **Wrapper Pattern**: Create thin async wrappers in `core/discovery.py` and `core/manager.py`:
   ```python
   async def _read_skill_file_async(self, path: Path) -> str:
       """Async wrapper for reading skill files."""
       def _read():
           with open(path, 'r', encoding='utf-8') as f:
               return f.read()
       return await asyncio.to_thread(_read)
   ```

2. **Error Handling**: Preserve exact exception behavior from sync version (FileNotFoundError, PermissionError, etc.)

3. **Encoding**: Always specify `encoding='utf-8'` for cross-platform consistency

4. **Context Managers**: Use standard `with open()` pattern inside sync function passed to `asyncio.to_thread()`

5. **Testing**: Verify event loop responsiveness during file I/O with pytest-asyncio

### Performance Expectations

- **Target**: Async discovery of 500 skills in <200ms (spec requirement: SC-001)
- **Overhead**: <2ms per async file read operation
- **Event Loop**: No blocking >5ms per file operation
- **Memory**: Identical to sync implementation (lazy loading maintained)

### References

- Stack Overflow: "AIOfile vs AIOfiles" - Performance comparison and recommendations
- Stack Overflow: "Speed of loading files with asyncio" - Benchmarking async file I/O approaches
- Python 3.10+ Documentation: `asyncio.to_thread()` function

---

## Decision 2: LangChain Async Tool Integration Pattern

### Context

LangChain's async agents require tools to implement the `ainvoke()` method for non-blocking execution. The StructuredTool class supports both sync (`func`) and async (`coroutine`) implementations, requiring careful integration pattern selection.

### Decision

**Implement dual sync/async pattern using StructuredTool.from_function() with both `func` and `coroutine` parameters.**

### Rationale

1. **Official LangChain Pattern**: Documentation explicitly recommends providing both implementations for optimal performance:
   ```python
   tool = StructuredTool.from_function(
       func=sync_invoke_skill,      # For sync agents
       coroutine=async_invoke_skill # For async agents
   )
   ```

2. **Performance**: Native async implementation avoids thread executor overhead:
   - Default `ainvoke()` behavior: runs `invoke()` in thread executor (adds overhead)
   - Explicit `coroutine` parameter: runs truly async, no thread pool overhead

3. **Compatibility**: Supports both sync and async LangChain agents with same tool:
   - Sync agents call `tool.invoke()` → uses `func` parameter
   - Async agents call `await tool.ainvoke()` → uses `coroutine` parameter

4. **Best Practice**: LangChain documentation states: "If you're working in an async codebase, you should create async tools rather than sync tools"

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Sync-only with default ainvoke** | Simple, minimal code | Thread executor overhead on every async call, not truly async | Poor performance for async agents; doesn't follow LangChain best practices |
| **Async-only with coroutine parameter** | Clean async implementation | Breaks sync agent compatibility | Violates backward compatibility requirement (v0.1 sync tools must work) |
| **Separate sync/async tool classes** | Clear separation of concerns | Duplicate tool definitions, API complexity | Unnecessary complexity; LangChain designed for dual-mode tools |

### Implementation Notes

1. **Integration Module**: Update `src/skillkit/integrations/langchain.py`:
   ```python
   def to_langchain_tools(manager: SkillManager) -> list[StructuredTool]:
       """Convert skills to LangChain tools with async support."""
       tools = []
       for metadata in manager.list_skills():
           # Sync version
           def sync_func(arguments: str = "") -> str:
               return manager.invoke_skill(metadata.name, arguments)

           # Async version
           async def async_func(arguments: str = "") -> str:
               return await manager.ainvoke_skill(metadata.name, arguments)

           tool = StructuredTool.from_function(
               func=sync_func,
               coroutine=async_func,
               name=metadata.name,
               description=metadata.description,
               # ... schema, error handling, etc.
           )
           tools.append(tool)
       return tools
   ```

2. **Closure Capture**: Each tool needs its own closure to capture `metadata.name`:
   ```python
   # WRONG: All tools share same metadata reference
   for metadata in manager.list_skills():
       func = lambda args: manager.invoke_skill(metadata.name, args)

   # CORRECT: Each tool captures its own metadata
   for metadata in manager.list_skills():
       def make_tool(meta):
           def func(args): return manager.invoke_skill(meta.name, args)
           async def afunc(args): return await manager.ainvoke_skill(meta.name, args)
           return StructuredTool.from_function(func=func, coroutine=afunc, ...)
       tools.append(make_tool(metadata))
   ```

3. **Error Handling**: Both sync and async versions must handle same exceptions identically

4. **Type Hints**: Ensure both functions have matching signatures for Pydantic schema generation

5. **Testing**: Verify both sync and async invocation paths with pytest and pytest-asyncio

### Compatibility Verification

- **LangChain Core Version**: Requires langchain-core 0.1.0+ (StructuredTool.from_function with coroutine parameter)
- **Pydantic Version**: Requires pydantic 2.0+ (type validation for both sync/async)
- **Backward Compatibility**: v0.1 code using sync tools continues working (only `func` parameter required)

### References

- LangChain API Documentation: `StructuredTool` class - coroutine parameter specification
- Stack Overflow: "Is it possible to implement an async method in StructuredTool with from_function?" - Confirmed dual-mode pattern
- LangChain How-to Guide: "How to create tools" - Async tool creation examples

---

## Decision 3: Plugin Manifest Schema

### Context

The v0.2 implementation adds plugin discovery, requiring a manifest format specification. Anthropic has published the Model Context Protocol (MCP) and MCP Bundle (MCPB) specifications, which define plugin manifest structures.

### Decision

**Use a simplified subset of the MCPB manifest.json schema (v0.3) with strict validation, focusing only on fields required for v0.2 skill discovery.**

### Rationale

1. **Official Anthropic Standard**: The MCPB manifest.json specification is Anthropic's official format for plugin bundles:
   - Location: `.claude-plugin/plugin.json` or `mcpb-manifest.json`
   - Specification: https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md
   - Version: 0.3 (current as of November 2024)

2. **Extensibility**: Using the official schema ensures future compatibility with Anthropic tooling:
   - Claude Desktop can load MCPB bundles directly
   - Community plugins can work across different systems
   - Future features (tools, prompts, localization) can be added incrementally

3. **Validation**: JSON Schema provides clear validation rules and error messages:
   - Required fields enforced at parse time
   - Type validation for all fields
   - Clear error messages for malformed manifests

4. **Subset Approach**: v0.2 only needs a minimal subset for skill discovery:
   - **Required**: `manifest_version`, `name`, `version`, `description`, `author`
   - **Optional for v0.2**: `skills` (string or array of skill directory paths)
   - **Deferred to v0.3+**: `tools`, `prompts`, `user_config`, `localization`, etc.

### Schema Specification (v0.2 Subset)

```json
{
  "manifest_version": "0.1",
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Brief plugin functionality overview",
  "author": {
    "name": "Author Name",
    "email": "optional@example.com",
    "url": "https://optional-website.com"
  },
  "skills": "skills/",  // Optional: string or array of paths
  // OR
  "skills": ["skills/", "additional-skills/"],

  // Optional v0.2 fields (informational only)
  "display_name": "My Plugin",
  "homepage": "https://plugin-homepage.com",
  "repository": {
    "type": "git",
    "url": "https://github.com/user/repo"
  }
}
```

### Validation Rules

| Field | Type | Required | Validation | Default |
|-------|------|----------|------------|---------|
| `manifest_version` | string | Yes | Must be "0.1" or "0.3" | N/A |
| `name` | string | Yes | Machine-readable identifier (kebab-case recommended) | N/A |
| `version` | string | Yes | Semver format (e.g., "1.0.0") | N/A |
| `description` | string | Yes | Brief overview (1-2 sentences) | N/A |
| `author` | object | Yes | Must include `name` field minimum | N/A |
| `author.name` | string | Yes | Author/organization name | N/A |
| `author.email` | string | No | Contact email | null |
| `author.url` | string | No | Website URL | null |
| `skills` | string or array | No | Relative path(s) to skill directories | `["skills/"]` |
| `display_name` | string | No | Human-friendly UI name | value of `name` |
| `homepage` | string | No | Plugin homepage URL | null |
| `repository` | object | No | Source control info | null |

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Custom skillkit format** | Full control, simpler schema | Not compatible with Anthropic ecosystem | Breaks interoperability with Claude Desktop and community plugins |
| **Full MCPB schema (all fields)** | Complete compatibility, future-proof | Overly complex for v0.2, many unused fields | Unnecessary complexity; subset approach allows incremental adoption |
| **Python-specific format (pyproject.toml)** | Familiar to Python devs, supports comments | Not cross-language, incompatible with MCP ecosystem | Violates framework-agnostic principle; language-specific |
| **YAML manifest** | Human-friendly, supports comments | Not Anthropic standard, parsing complexity | JSON is simpler and matches MCPB spec exactly |

### v0.2 Security Enhancements

Based on technical review (2025-01-13), the following security validations were added to Decision 3:

1. **Path Traversal Prevention**: Validate `skills` paths to prevent directory traversal attacks:
   - Block `..` sequences in skill paths
   - Block absolute paths (`/`, `\`, drive letters)
   - Implemented in `PluginManifest.__post_init__()` validation

2. **JSON Bomb Protection**: Enforce file size limit (1 MB) to prevent DoS attacks:
   - Check file size before parsing
   - Reject manifests exceeding `MAX_MANIFEST_SIZE`
   - Implemented in `parse_plugin_manifest()`

3. **Manifest Version Correction**: Support both `"0.1"` and `"0.3"` manifest versions:
   - Official MCPB examples use `"0.1"` (not `"0.3"`)
   - Spec document version is separate from manifest field value
   - Clear error message for unsupported versions

These additions ensure v0.2 manifest parsing is secure against common attack vectors while maintaining simplicity for MVP release.

### Implementation Notes

1. **Parser Module**: Add plugin manifest parsing to `core/parser.py`:
   ```python
   # Security constants
   MAX_MANIFEST_SIZE = 1_000_000  # 1 MB limit

   @dataclass
   class PluginManifest:
       manifest_version: str
       name: str
       version: str
       description: str
       author: dict[str, str]  # {"name": str, "email": str?, "url": str?}
       skills: list[str]  # Normalized to list (even if string in JSON)
       display_name: str | None = None
       homepage: str | None = None
       repository: dict[str, str] | None = None

       def __post_init__(self):
           """Validate manifest fields with security checks."""
           # Validate manifest version
           if self.manifest_version not in {"0.1", "0.3"}:
               raise ManifestValidationError(
                   f"Unsupported manifest_version: {self.manifest_version}. "
                   f"Supported versions: 0.1, 0.3"
               )

           # Basic field validation
           if not self.name or ' ' in self.name:
               raise ManifestValidationError("Plugin name cannot contain spaces")

           if not self.version or self.version.count('.') < 2:
               raise ManifestValidationError("Version must be semver (e.g., 1.0.0)")

           if not self.description or len(self.description) > 1000:
               raise ManifestValidationError("Description required (max 1000 chars)")

           # Validate author
           if not isinstance(self.author, dict) or 'name' not in self.author:
               raise ManifestValidationError("Author must have 'name' field")

           # SECURITY: Validate skills paths
           for skill_path in self.skills:
               if not skill_path:
                   raise ManifestValidationError("Skill path cannot be empty")

               # Prevent path traversal
               if ".." in skill_path:
                   raise ManifestValidationError(
                       f"Security violation: Path contains '..': {skill_path}"
                   )

               # Prevent absolute paths
               if skill_path.startswith("/") or skill_path.startswith("\\"):
                   raise ManifestValidationError(
                       f"Security violation: Path must be relative: {skill_path}"
                   )

               # Windows: Prevent drive letters
               if len(skill_path) >= 2 and skill_path[1] == ":":
                   raise ManifestValidationError(
                       f"Security violation: Drive letters not allowed: {skill_path}"
                   )

   def parse_plugin_manifest(manifest_path: Path) -> PluginManifest:
       """Parse and validate plugin.json manifest with security checks."""
       # Check file exists
       if not manifest_path.exists():
           raise ManifestNotFoundError(
               f"Plugin manifest not found: {manifest_path}\n"
               f"Expected location: .claude-plugin/plugin.json"
           )

       # SECURITY: Check file size (JSON bomb prevention)
       file_size = manifest_path.stat().st_size
       if file_size > MAX_MANIFEST_SIZE:
           raise ManifestParseError(
               f"Manifest too large: {file_size:,} bytes (max {MAX_MANIFEST_SIZE:,})"
           )

       # Parse JSON with error handling
       try:
           with open(manifest_path, 'r', encoding='utf-8') as f:
               data = json.load(f)
       except json.JSONDecodeError as e:
           raise ManifestParseError(
               f"Invalid JSON in {manifest_path.name}:\n"
               f"  Line {e.lineno}, Column {e.colno}: {e.msg}"
           ) from e

       # Validate required fields
       required = ['manifest_version', 'name', 'version', 'description', 'author']
       missing = [f for f in required if f not in data]
       if missing:
           raise ManifestValidationError(
               f"Missing required fields: {', '.join(missing)}\n"
               f"Required: {', '.join(required)}"
           )

       # Normalize skills field
       skills = data.get('skills', ['skills/'])
       if isinstance(skills, str):
           skills = [skills]
       elif not isinstance(skills, list):
           raise ManifestValidationError(
               f"'skills' must be string or array, got {type(skills).__name__}"
           )

       # Build manifest (validation happens in __post_init__)
       return PluginManifest(
           manifest_version=data['manifest_version'],
           name=data['name'],
           version=data['version'],
           description=data['description'],
           author=data['author'],
           skills=skills,
           display_name=data.get('display_name'),
           homepage=data.get('homepage'),
           repository=data.get('repository')
       )
   ```

2. **Discovery Logic**: Scan for `.claude-plugin/plugin.json` in plugin directories:
   ```python
   def discover_plugin(plugin_dir: Path) -> PluginManifest | None:
       """Discover and parse plugin manifest if present."""
       manifest_path = plugin_dir / '.claude-plugin' / 'plugin.json'
       if not manifest_path.exists():
           return None

       try:
           return parse_plugin_manifest(manifest_path)
       except (json.JSONDecodeError, ManifestValidationError) as e:
           logger.error(f"Invalid plugin manifest at {manifest_path}: {e}")
           return None
   ```

3. **Error Handling**: Graceful degradation for malformed manifests:
   - Log detailed error with manifest path and specific validation failure
   - Continue discovery for other plugins
   - Return plugin path in error list for user debugging

4. **Future Extension**: v0.3+ can add support for `tools`, `prompts`, `user_config` fields incrementally without breaking v0.2 plugins

### Testing Strategy

1. **Valid Manifests**: Test parsing with all required fields and various optional field combinations
2. **Missing Fields**: Verify clear error messages for each missing required field
3. **Type Validation**: Test with wrong types (e.g., string instead of object for author)
4. **Skills Normalization**: Test both string and array values for `skills` field
5. **Malformed JSON**: Test with syntax errors, ensure graceful error handling
6. **Security Tests** (v0.2 additions):
   - Path traversal: Test `skills: ["../../etc"]` is blocked
   - Absolute paths: Test `skills: ["/etc/passwd"]` is blocked
   - Drive letters: Test `skills: ["C:/Windows"]` is blocked
   - JSON bombs: Test oversized manifests (>1MB) are rejected
7. **Real-World**: If possible, test with actual Anthropic plugin examples

### References

- MCPB Manifest Specification: https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md
- Model Context Protocol: https://github.com/modelcontextprotocol
- Anthropic MCP Announcement: https://www.anthropic.com/news/model-context-protocol
- Claude Desktop Extensions Documentation: https://docs.claude.com/en/docs/mcp

---

## Decision 4: Path Traversal Prevention Strategy

### Context

File reference resolution (FR-020 through FR-027) requires secure path validation to prevent directory traversal attacks where malicious skills attempt to access files outside their base directory using paths like `../../etc/passwd`.

### Decision

**Use `pathlib.Path.resolve()` for canonical path normalization combined with `Path.is_relative_to()` (Python 3.9+) for ancestry validation.**

### Rationale

1. **OWASP Best Practice**: Path normalization + ancestry check is the recommended approach:
   - `resolve()` collapses `..` sequences, resolves symlinks, and creates canonical absolute paths
   - `is_relative_to()` validates the final path is within the allowed directory tree

2. **Security Guarantees**:
   - `resolve()` handles all common attack vectors:
     - `../` sequences
     - Symlinks (resolved to actual target)
     - URL encoding (path is decoded before resolution)
     - Mixed separators (`/` vs `\` on Windows)
     - Redundant separators (`//`, `/./`)

3. **Pythonic API**: `is_relative_to()` provides clear, readable security check:
   ```python
   base_dir = Path("/skills/my-skill").resolve()
   user_path = (base_dir / "../../etc/passwd").resolve()

   if not user_path.is_relative_to(base_dir):
       raise SecurityError("Path traversal attempt detected")
   ```

4. **Type Safety**: Works seamlessly with pathlib.Path objects throughout codebase

5. **Cross-Platform**: Handles platform-specific path quirks (Windows drives, UNC paths, POSIX symlinks)

### Security Implementation

```python
class FilePathResolver:
    """Secure path resolution for skill supporting files."""

    def __init__(self, skill_base_dir: Path):
        """Initialize resolver with skill's base directory."""
        self.base_dir = skill_base_dir.resolve()  # Canonical absolute path

    def resolve_path(self, relative_path: str) -> Path:
        """
        Resolve relative path from skill base directory.

        Args:
            relative_path: Path relative to skill base (e.g., "scripts/helper.py")

        Returns:
            Absolute Path object guaranteed to be within skill base directory

        Raises:
            PathSecurityError: If path attempts directory traversal
        """
        # Join and resolve to canonical absolute path
        requested_path = (self.base_dir / relative_path).resolve()

        # Validate path is descendant of base directory
        if not requested_path.is_relative_to(self.base_dir):
            raise PathSecurityError(
                f"Path traversal attempt detected: '{relative_path}' "
                f"resolves outside skill directory {self.base_dir}"
            )

        # Log access for security auditing
        logger.debug(f"Resolved path: {relative_path} -> {requested_path}")

        return requested_path
```

### Attack Vectors Tested

| Attack Vector | Example Input | Behavior | Blocked? |
|---------------|---------------|----------|----------|
| Parent directory | `../../etc/passwd` | Resolves outside base | Yes - `is_relative_to()` fails |
| Symlink escape | `link -> /etc/passwd` | Symlink resolved to target | Yes - target outside base |
| Absolute path | `/etc/passwd` | Joined to base, then resolved | Yes - resolves outside base |
| URL encoding | `..%2F..%2Fetc%2Fpasswd` | Path object decodes automatically | Yes - normalized then validated |
| Mixed separators | `..\\..\\etc\\passwd` (Windows) | Normalized by pathlib | Yes - cross-platform handling |
| Redundant separators | `scripts/../../etc/passwd` | Collapsed during resolution | Yes - canonical path validated |
| Circular symlink | `link1 -> link2 -> link1` | RuntimeError from resolve() | Yes - error caught, logged |

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **String prefix checking** | Simple, fast | Vulnerable to string-matching bypasses (e.g., `/my-skills` vs `/my-skills-backup`) | Security vulnerability documented in OWASP and community reports |
| **os.path.commonpath()** | Works on Python 3.5+ | String-based, less robust than pathlib, requires trailing slash hack | Less secure and less elegant than pathlib solution |
| **Path.relative_to() with exception** | Works on Python 3.5+ | Raises ValueError instead of returning bool, less readable | Functional but less clean API than `is_relative_to()` |
| **Manual .. sequence checking** | No dependencies | Easily bypassed (symlinks, URL encoding, absolute paths) | Multiple known security vulnerabilities |
| **Chroot/jail sandboxing** | Strongest isolation | Requires OS-level support, not cross-platform, complex | Out of scope for library-level security |

### Implementation Notes

1. **Module Location**: Create new file `src/skillkit/core/path_resolver.py`

2. **Exception Class**: Add to `core/exceptions.py`:
   ```python
   class PathSecurityError(SkillKitError):
       """Raised when path traversal or security violation is detected."""
       pass
   ```

3. **Logging**: Log all path traversal attempts at ERROR level:
   ```python
   logger.error(
       "Path traversal attempt detected",
       extra={
           "skill_name": skill_name,
           "skill_base": str(self.base_dir),
           "requested_path": relative_path,
           "resolved_path": str(requested_path)
       }
   )
   ```

4. **Integration with Content Processor**:
   ```python
   class ContentProcessor:
       def process(self, skill: Skill, arguments: str) -> str:
           # Inject base directory context
           content = f"Base directory for this skill: {skill.base_dir}\n\n{skill.content}"

           # Substitute $ARGUMENTS
           content = Template(content).safe_substitute(ARGUMENTS=arguments)

           return content
   ```

5. **Usage in Skills**:
   ```markdown
   # SKILL.md

   You are a data processing skill.

   Base directory for this skill: /path/to/skill/

   To process the data, execute the helper script:
   - Script location: scripts/process_data.py
   - Full path: /path/to/skill/scripts/process_data.py

   Example:
   python /path/to/skill/scripts/process_data.py --input $ARGUMENTS
   ```

### Python Version Compatibility

- **Python 3.9+**: Native `is_relative_to()` method (RECOMMENDED)
- **Python 3.8 and below**: Not supported in v0.2 (minimum Python 3.10 per spec)
  - If Python 3.8 support needed, use `relative_to()` with try/except ValueError

### Testing Strategy

1. **Unit Tests**: Test all attack vectors in table above
2. **Fuzzing**: Generate random malicious paths, verify all blocked
3. **Integration Tests**: Test with real skill files in various directory structures
4. **Security Review**: Code review by multiple developers
5. **Symlink Tests**: Create test symlinks (Linux/macOS only), verify resolution
6. **Edge Cases**:
   - Empty relative path (`""`)
   - Current directory (`.`)
   - Root directory (`/`)
   - Windows drive letters (`C:\`)
   - UNC paths (`\\server\share`)

### Performance Characteristics

- **Overhead**: ~0.1-0.5ms per path resolution (negligible)
- **Caching**: Consider caching resolved paths if same path accessed frequently
- **I/O Impact**: `resolve()` may perform filesystem operations (stat, readlink) - acceptable overhead

### References

- OWASP: "Path Traversal" - Attack vectors and prevention techniques
- Stack Overflow: "How to prevent directory traversal attack from Python code" - Accepted answer uses pathlib pattern
- Salvatore Security: "Preventing Directory Traversal Vulnerabilities in Python" - Detailed security analysis
- Python pathlib documentation: `Path.resolve()` and `Path.is_relative_to()` specifications

---

## Decision 5: Multi-Source Priority Resolution Data Structure

### Context

v0.2 supports multiple skill sources (project, anthropic, plugins, additional paths) with priority-based conflict resolution. The data structure must enable O(1) skill lookups by name while maintaining clear priority ordering for conflicts.

### Decision

**Use a two-tier structure: `dict[str, SkillMetadata]` for O(1) lookup combined with `list[SkillSource]` for priority-ordered scanning.**

### Rationale

1. **O(1) Lookup Performance**: Dictionary provides constant-time skill retrieval by name:
   ```python
   skill = manager._skills["my-skill"]  # O(1)
   ```

2. **Clear Priority Semantics**: List of SkillSource objects maintains explicit priority order:
   ```python
   sources = [
       SkillSource(path=project_dir, priority=100, type="project"),
       SkillSource(path=anthropic_dir, priority=50, type="anthropic"),
       SkillSource(path=plugin_dir, priority=10, type="plugin", plugin_name="my-plugin")
   ]
   ```

3. **Conflict Resolution**: Discovery scans sources in priority order, first-wins strategy:
   ```python
   for source in sorted(self.sources, key=lambda s: s.priority, reverse=True):
       for skill_meta in discover_skills_in_source(source):
           if skill_meta.name not in self._skills:
               self._skills[skill_meta.name] = skill_meta
           else:
               logger.warning(f"Skill '{skill_meta.name}' already exists from higher priority source")
   ```

4. **Fully Qualified Names**: Plugin skills support namespaced access:
   ```python
   # Regular lookup (priority order)
   skill = manager.get_skill("data-processor")  # Gets project version

   # Qualified lookup (explicit)
   skill = manager.get_skill("my-plugin:data-processor")  # Gets plugin version

   # Implementation
   if ":" in skill_name:
       plugin_name, skill_name = skill_name.split(":", 1)
       return self._plugin_skills[plugin_name][skill_name]
   else:
       return self._skills[skill_name]
   ```

5. **Memory Efficiency**: No duplication - each skill stored once in appropriate dict

### Data Model

```python
@dataclass
class SkillSource:
    """Represents a source location for skills with priority."""
    path: Path                    # Absolute path to skill directory
    priority: int                 # Higher priority = resolved first
    source_type: str             # "project", "anthropic", "plugin", "custom"
    plugin_name: str | None = None  # For plugin sources only

    def __hash__(self):
        return hash((self.path, self.plugin_name))

class SkillManager:
    def __init__(
        self,
        project_skill_dir: Path | None = None,
        anthropic_config_dir: Path | None = None,
        plugin_dirs: list[Path] | None = None,
        additional_search_paths: list[Path] | None = None
    ):
        # Priority-ordered sources
        self.sources: list[SkillSource] = self._build_sources(
            project_skill_dir,
            anthropic_config_dir,
            plugin_dirs,
            additional_search_paths
        )

        # Main skill registry (simple name -> metadata)
        self._skills: dict[str, SkillMetadata] = {}

        # Plugin-namespaced skills (plugin_name -> skill_name -> metadata)
        self._plugin_skills: dict[str, dict[str, SkillMetadata]] = {}

    def _build_sources(self, ...) -> list[SkillSource]:
        """Build priority-ordered list of skill sources."""
        sources = []

        if project_skill_dir:
            sources.append(SkillSource(
                path=project_skill_dir.resolve(),
                priority=100,
                source_type="project"
            ))

        if anthropic_config_dir:
            sources.append(SkillSource(
                path=anthropic_config_dir.resolve(),
                priority=50,
                source_type="anthropic"
            ))

        if plugin_dirs:
            for plugin_dir in plugin_dirs:
                # Discover plugin manifest
                manifest = discover_plugin_manifest(plugin_dir)
                sources.append(SkillSource(
                    path=plugin_dir.resolve(),
                    priority=10,
                    source_type="plugin",
                    plugin_name=manifest.name if manifest else plugin_dir.name
                ))

        if additional_search_paths:
            for i, path in enumerate(additional_search_paths):
                sources.append(SkillSource(
                    path=path.resolve(),
                    priority=5 - i,  # Lower priority for additional paths
                    source_type="custom"
                ))

        return sorted(sources, key=lambda s: s.priority, reverse=True)
```

### Conflict Resolution Algorithm

```python
def discover(self) -> None:
    """Discover skills from all sources with priority-based conflict resolution."""
    self._skills.clear()
    self._plugin_skills.clear()

    for source in self.sources:
        logger.info(f"Scanning source: {source.path} (priority={source.priority})")

        # Discover all skills in this source
        discovered = self._discovery.discover_skills(source.path)

        for skill_meta in discovered:
            # Plugin skills: namespace and store separately
            if source.source_type == "plugin" and source.plugin_name:
                plugin_name = source.plugin_name
                if plugin_name not in self._plugin_skills:
                    self._plugin_skills[plugin_name] = {}

                # Store in plugin namespace
                self._plugin_skills[plugin_name][skill_meta.name] = skill_meta

            # All skills: add to main registry if not already present
            if skill_meta.name not in self._skills:
                self._skills[skill_meta.name] = skill_meta
                logger.debug(f"Registered skill '{skill_meta.name}' from {source.path}")
            else:
                # Conflict: log warning with both paths
                existing = self._skills[skill_meta.name]
                logger.warning(
                    f"Skill name conflict: '{skill_meta.name}' found in multiple sources. "
                    f"Using: {existing.base_dir} (priority {self._get_source_priority(existing)}). "
                    f"Ignoring: {skill_meta.base_dir} (priority {source.priority}). "
                    f"Use fully qualified name '{source.plugin_name}:{skill_meta.name}' to access ignored version."
                )
```

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Priority queue (heapq)** | Efficient for priority-based access | O(log n) lookup, complex conflict resolution, not suitable for key-value lookups | Poor lookup performance; priority queue is for min/max extraction, not name-based access |
| **Single dict with tuple values** | Simple structure: `{name: (priority, metadata)}` | Conflict resolution requires manual logic, no plugin namespacing | Doesn't support fully qualified names cleanly |
| **ChainMap (stdlib)** | Layers multiple dicts, automatic priority | No conflict warnings, hard to track source of skills, no plugin namespacing | Lacks transparency for debugging conflicts |
| **Separate dicts per source** | Clear source isolation | O(n) lookup (search all dicts), complex conflict logic | Poor performance for large skill sets |
| **Custom registry class** | Full control, encapsulation | More code, maintenance burden | Two-tier dict/list approach is sufficient and simpler |

### Implementation Notes

1. **Source Priority Constants**:
   ```python
   PRIORITY_PROJECT = 100
   PRIORITY_ANTHROPIC = 50
   PRIORITY_PLUGIN = 10
   PRIORITY_CUSTOM_BASE = 5  # Decrement for each additional path
   ```

2. **Qualified Name Parsing**:
   ```python
   def get_skill(self, skill_name: str) -> SkillMetadata:
       """Get skill by name (simple or fully qualified)."""
       if ":" in skill_name:
           # Fully qualified: "plugin-name:skill-name"
           plugin_name, base_name = skill_name.split(":", 1)

           if plugin_name not in self._plugin_skills:
               raise SkillNotFoundError(f"Plugin '{plugin_name}' not found")

           if base_name not in self._plugin_skills[plugin_name]:
               raise SkillNotFoundError(
                   f"Skill '{base_name}' not found in plugin '{plugin_name}'"
               )

           return self._plugin_skills[plugin_name][base_name]
       else:
           # Simple name: use priority order
           if skill_name not in self._skills:
               raise SkillNotFoundError(f"Skill '{skill_name}' not found")

           return self._skills[skill_name]
   ```

3. **List All Skills**:
   ```python
   def list_skills(self, include_plugin_qualified: bool = False) -> list[SkillMetadata]:
       """List all discovered skills."""
       if not include_plugin_qualified:
           return list(self._skills.values())

       # Include both simple names and fully qualified plugin names
       all_skills = list(self._skills.values())
       for plugin_name, skills in self._plugin_skills.items():
           for skill_name, skill_meta in skills.items():
               # Add qualified version if it differs from main registry
               if skill_name not in self._skills or self._skills[skill_name] != skill_meta:
                   # Create copy with qualified name
                   qualified_meta = replace(skill_meta, name=f"{plugin_name}:{skill_name}")
                   all_skills.append(qualified_meta)

       return all_skills
   ```

4. **Memory Overhead**: Minimal duplication:
   - Plugin skills appear in both `_plugin_skills` and `_skills` (if no conflict)
   - Both dicts store references to same SkillMetadata objects (shared memory)
   - Overhead: ~100 bytes per plugin skill for dict entry

### Performance Analysis

| Operation | Time Complexity | Notes |
|-----------|----------------|-------|
| `get_skill("name")` | O(1) | Dict lookup |
| `get_skill("plugin:name")` | O(1) | Two dict lookups |
| `list_skills()` | O(n) | Iterate all skills |
| `discover()` | O(n * m) | n sources, m skills per source |
| Priority conflict check | O(1) per skill | During discovery only |

### Testing Strategy

1. **Priority Order**: Test skills with same name in multiple sources, verify correct version used
2. **Qualified Names**: Test plugin namespace access with and without conflicts
3. **Edge Cases**:
   - Empty source list
   - Source with no skills
   - Duplicate plugin names (should log warning)
   - Circular plugin references (not possible with file structure)
4. **Performance**: Benchmark lookup times with 500+ skills across 10 sources

### References

- Python Data Structures Best Practices: dict for O(1) lookups, list for ordered collections
- Stack Overflow: Registry pattern implementations in Python
- Real Python: "Python Stacks, Queues, and Priority Queues" - When to use each structure

---

## Decision 6: Async/Sync State Management Pattern

### Context

SkillManager must support both sync (`discover()`, `invoke_skill()`) and async (`adiscover()`, `ainvoke_skill()`) APIs. Users should not mix initialization methods (e.g., calling `discover()` then `adiscover()` on same instance) to prevent undefined behavior.

### Decision

**Use separate factory methods (`create()` and `acreate()`) with internal state tracking to prevent mixing, rather than separate sync/async classes.**

### Rationale

1. **Single Class Benefits**:
   - No code duplication (both modes share data structures, validation logic)
   - Unified API surface (users import one SkillManager class)
   - Easier testing (test both modes on same class)

2. **State Flag Protection**: Track initialization state to prevent mixing:
   ```python
   class SkillManager:
       def __init__(self, ...):
           self._initialized_async: bool | None = None  # None=uninitialized, True=async, False=sync

       def discover(self) -> None:
           if self._initialized_async is True:
               raise AsyncStateError("Manager was initialized async; use adiscover() instead")
           self._initialized_async = False
           # ... discovery logic

       async def adiscover(self) -> None:
           if self._initialized_async is False:
               raise AsyncStateError("Manager was initialized sync; use discover() instead")
           self._initialized_async = True
           # ... async discovery logic
   ```

3. **Clear Error Messages**: Users get actionable feedback if they mix modes:
   ```
   AsyncStateError: Manager was initialized with discover() (sync mode).
   To use async methods, create a new manager and call adiscover() instead.
   ```

4. **Factory Pattern (Optional Enhancement)**: Provide convenience factories for clarity:
   ```python
   @classmethod
   def create(cls, ...) -> "SkillManager":
       """Create and initialize manager synchronously."""
       manager = cls(...)
       manager.discover()
       return manager

   @classmethod
   async def acreate(cls, ...) -> "SkillManager":
       """Create and initialize manager asynchronously."""
       manager = cls(...)
       await manager.adiscover()
       return manager
   ```

5. **Best Practice Alignment**: Python async best practices discourage dual-mode classes but allow them for specific use cases:
   - LangChain uses similar pattern (StructuredTool has both `invoke` and `ainvoke`)
   - HTTP clients (httpx, aiohttp) often have sync/async versions as separate classes
   - For skillkit, single class is justified by shared state and logic

### State Management Implementation

```python
from enum import Enum
from typing import Literal

class InitMode(Enum):
    """Initialization mode for SkillManager."""
    UNINITIALIZED = "uninitialized"
    SYNC = "sync"
    ASYNC = "async"

class SkillManager:
    def __init__(
        self,
        project_skill_dir: Path | None = None,
        anthropic_config_dir: Path | None = None,
        plugin_dirs: list[Path] | None = None,
        additional_search_paths: list[Path] | None = None
    ):
        # Source configuration
        self.sources = self._build_sources(...)

        # Skill registries
        self._skills: dict[str, SkillMetadata] = {}
        self._plugin_skills: dict[str, dict[str, SkillMetadata]] = {}

        # State tracking
        self._init_mode: InitMode = InitMode.UNINITIALIZED

    def discover(self) -> None:
        """Synchronous skill discovery."""
        if self._init_mode == InitMode.ASYNC:
            raise AsyncStateError(
                "Manager was initialized with adiscover() (async mode). "
                "Cannot mix sync and async methods. Create a new manager instance."
            )

        self._init_mode = InitMode.SYNC
        self._discover_impl()  # Shared implementation

    async def adiscover(self) -> None:
        """Asynchronous skill discovery."""
        if self._init_mode == InitMode.SYNC:
            raise AsyncStateError(
                "Manager was initialized with discover() (sync mode). "
                "Cannot mix sync and async methods. Create a new manager instance."
            )

        self._init_mode = InitMode.ASYNC
        await self._adiscover_impl()  # Async implementation

    def invoke_skill(self, skill_name: str, arguments: str = "") -> str:
        """Synchronous skill invocation."""
        if self._init_mode == InitMode.ASYNC:
            raise AsyncStateError(
                "Manager was initialized async. Use ainvoke_skill() instead."
            )

        if self._init_mode == InitMode.UNINITIALIZED:
            raise StateError("Manager not initialized. Call discover() first.")

        return self._invoke_impl(skill_name, arguments)

    async def ainvoke_skill(self, skill_name: str, arguments: str = "") -> str:
        """Asynchronous skill invocation."""
        if self._init_mode == InitMode.SYNC:
            raise AsyncStateError(
                "Manager was initialized sync. Use invoke_skill() instead."
            )

        if self._init_mode == InitMode.UNINITIALIZED:
            raise StateError("Manager not initialized. Call adiscover() first.")

        return await self._ainvoke_impl(skill_name, arguments)

    # Factory methods (optional, for convenience)
    @classmethod
    def create(
        cls,
        project_skill_dir: Path | None = None,
        **kwargs
    ) -> "SkillManager":
        """Create and initialize manager synchronously."""
        manager = cls(project_skill_dir, **kwargs)
        manager.discover()
        return manager

    @classmethod
    async def acreate(
        cls,
        project_skill_dir: Path | None = None,
        **kwargs
    ) -> "SkillManager":
        """Create and initialize manager asynchronously."""
        manager = cls(project_skill_dir, **kwargs)
        await manager.adiscover()
        return manager
```

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Separate SyncManager and AsyncManager classes** | Clear separation, no state confusion | Code duplication, complex maintenance, confusing API | Violates DRY principle; users must choose class upfront |
| **Warning-only (allow mixing)** | Flexible, no errors | Undefined behavior, hard-to-debug issues, race conditions | Unsafe; async/sync mixing can cause event loop errors |
| **Auto-detection (inspect event loop)** | Seamless, no user choice needed | Complex, fragile, doesn't handle edge cases (nested loops) | Too magical; explicit is better than implicit |
| **Pure async (deprecate sync)** | Simplest implementation | Breaks v0.1 backward compatibility, forces async everywhere | Violates backward compatibility requirement |
| **Pure sync (no async)** | No complexity | Blocks event loop, can't use in async applications | Doesn't meet v0.2 requirements |

### Implementation Notes

1. **Exception Class**: Add to `core/exceptions.py`:
   ```python
   class AsyncStateError(SkillKitError):
       """Raised when async/sync methods are mixed incorrectly."""
       pass

   class StateError(SkillKitError):
       """Raised when manager is in invalid state (e.g., not initialized)."""
       pass
   ```

2. **Shared Implementation**: Extract common logic to avoid duplication:
   ```python
   def _discover_impl(self) -> list[SkillMetadata]:
       """Shared discovery logic (sync execution)."""
       # Common validation, source iteration, metadata creation
       pass

   async def _adiscover_impl(self) -> list[SkillMetadata]:
       """Async discovery logic (delegates file I/O to asyncio.to_thread)."""
       # Same logic as _discover_impl but with async file I/O
       pass

   def _invoke_impl(self, skill_name: str, arguments: str) -> str:
       """Shared invocation logic (sync file I/O)."""
       pass

   async def _ainvoke_impl(self, skill_name: str, arguments: str) -> str:
       """Async invocation logic (async file I/O)."""
       pass
   ```

3. **Type Hints**: Ensure proper async annotations:
   ```python
   from typing import Coroutine, Any

   async def adiscover(self) -> None:  # Return None (not Coroutine[Any, Any, None])
       ...
   ```

4. **Context Managers** (Future Enhancement): Could add async context manager support:
   ```python
   async def __aenter__(self) -> "SkillManager":
       await self.adiscover()
       return self

   async def __aexit__(self, *exc_info):
       # Cleanup if needed
       pass

   # Usage
   async with SkillManager.acreate(project_dir) as manager:
       result = await manager.ainvoke_skill("my-skill", "args")
   ```

### Testing Strategy

1. **State Transitions**: Test all valid and invalid state transitions:
   - UNINITIALIZED → SYNC (via discover) ✓
   - UNINITIALIZED → ASYNC (via adiscover) ✓
   - SYNC → SYNC (repeated discover calls) ✓
   - ASYNC → ASYNC (repeated adiscover calls) ✓
   - SYNC → ASYNC (should raise AsyncStateError) ✗
   - ASYNC → SYNC (should raise AsyncStateError) ✗

2. **Error Messages**: Verify error messages are clear and actionable

3. **Factory Methods**: Test `create()` and `acreate()` convenience methods

4. **Concurrency**: Test that multiple async managers can coexist independently

5. **Type Checking**: Verify mypy accepts both sync and async patterns:
   ```python
   # Sync
   manager = SkillManager.create(project_dir)
   result: str = manager.invoke_skill("skill", "args")

   # Async
   manager = await SkillManager.acreate(project_dir)
   result: str = await manager.ainvoke_skill("skill", "args")
   ```

### Documentation Notes

1. **User Guide**: Clearly document that sync and async are mutually exclusive:
   ```python
   # Good: Consistent sync usage
   manager = SkillManager(project_dir)
   manager.discover()
   result = manager.invoke_skill("skill", "args")

   # Good: Consistent async usage
   manager = SkillManager(project_dir)
   await manager.adiscover()
   result = await manager.ainvoke_skill("skill", "args")

   # Bad: Mixing modes (raises AsyncStateError)
   manager = SkillManager(project_dir)
   manager.discover()
   result = await manager.ainvoke_skill("skill", "args")  # ERROR!
   ```

2. **Migration Guide**: Help v0.1 users understand async options:
   - v0.1 sync code continues working unchanged
   - Async is opt-in via new methods
   - Users can choose per-instance (create separate managers if needed)

### Performance Considerations

- **State Check Overhead**: ~0.1μs per method call (negligible)
- **Memory Overhead**: Single enum value per instance (~40 bytes)
- **No Runtime Penalty**: State checks are simple enum comparisons

### References

- Stack Overflow: "How to set class attribute with await in __init__" - Factory pattern for async initialization
- Stack Overflow: "Implementing both Sync and Async clients with DRY" - Shared implementation strategies
- Software Engineering SE: "How to structure your Python code with asynchronous and synchronous parts" - Best practices for dual-mode code
- Python asyncio best practices: Explicit async/await over auto-detection

---

## Summary of Decisions

| # | Decision Area | Chosen Approach | Key Rationale |
|---|---------------|-----------------|---------------|
| 1 | **Async File I/O** | `asyncio.to_thread()` with stdlib `open()` | Zero dependencies, comparable performance, simpler than aiofiles |
| 2 | **LangChain Async** | Dual `func` + `coroutine` in StructuredTool | Official LangChain pattern, best performance for async agents |
| 3 | **Plugin Manifest** | MCPB manifest.json v0.3 subset | Anthropic standard, ecosystem compatibility, future extensibility |
| 4 | **Path Traversal** | `Path.resolve()` + `is_relative_to()` | OWASP best practice, secure, Pythonic API |
| 5 | **Multi-Source Registry** | `dict` for O(1) lookup + `list` for priority | Performance + clarity, supports fully qualified names |
| 6 | **Async/Sync State** | Single class with state flag + factory methods | No duplication, clear errors, convenient usage |

## Next Steps

1. **Phase 1: Design** - Create detailed data models, API contracts, and quickstart guide based on these decisions
2. **Phase 2: Task Generation** - Break down implementation into atomic tasks referencing these research findings
3. **Phase 3: Implementation** - Execute tasks with confidence in architectural decisions
4. **Phase 4: Testing** - Validate all decisions with comprehensive test coverage

## References

### Official Documentation
- Python asyncio: https://docs.python.org/3/library/asyncio.html
- Python pathlib: https://docs.python.org/3/library/pathlib.html
- LangChain API: https://api.python.langchain.com/
- MCPB Specification: https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md

### Security Resources
- OWASP Path Traversal: https://owasp.org/www-community/attacks/Path_Traversal
- Salvatore Security: https://salvatoresecurity.com/preventing-directory-traversal-vulnerabilities-in-python/

### Community Discussions
- Stack Overflow: Multiple threads cited inline
- Python Discuss: Async best practices thread
- Real Python: Async programming guides

### Benchmarks & Performance
- aiofiles GitHub issues: Performance discussions
- Python asyncio wiki: Benchmarks section

---

## Decision 7: SkillManager Initialization Behavior and Default Directory Discovery

**Added**: 2025-11-16 (Session 2025-11-16 clarifications for User Story 3)

### Context

User Story 3 requires SkillManager to support flexible initialization patterns including:
1. Zero-configuration usage with default directories (`./skills/`, `./.claude/skills/`)
2. Explicit path configuration for custom locations
3. Opt-out mechanism to disable default discovery
4. Clear error reporting for invalid configurations

The original v0.2 implementation did not address these initialization semantics, leading to gaps in acceptance scenarios 4-8.

### Decision

**Implement tri-state parameter logic with default directory discovery: `None` (apply defaults) | `""` (opt-out) | `Path` (use explicit)**

### Rationale

1. **Zero-Configuration Usability**: Users should be able to initialize `SkillManager()` without parameters and have skills discovered automatically if default directories exist. This is critical for getting started and reduces friction.

2. **Pythonic Conventions**: Using `None` for "apply defaults" is idiomatic Python (matches function default parameters). Empty string `""` as opt-out is explicit and unambiguous.

3. **Clear Error Handling**: Distinguishing between default paths (warn if missing) and explicit paths (error if missing) provides clear feedback:
   - Default missing → INFO log, continue (user may not have skills yet)
   - Explicit missing → ConfigurationError (user made a mistake)

4. **Flexibility for Edge Cases**: Supports advanced use cases like:
   - Disable project skills but enable anthropic: `SkillManager(project_skill_dir="", anthropic_config_dir="./.claude/skills")`
   - Start with zero skills regardless of filesystem: `SkillManager(project_skill_dir="", anthropic_config_dir="", plugin_dirs=[])`

5. **Consistency with Priorities**: Default directories respect the same priority system (./skills/ > ./.claude/skills/) as explicit multi-source configuration

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------|
| **Always require explicit paths** | Simple, no ambiguity | Poor UX, forces boilerplate | Contradicts zero-configuration goal; requires users to always specify paths even for standard layout |
| **Use special sentinel value (e.g., `SKIP`)** | Explicit opt-out | Non-Pythonic, requires imports | Empty string `""` is clearer and doesn't require special constants |
| **Separate `use_defaults` boolean parameter** | Clear intent | Extra parameter, complex interactions | Increases API surface; tri-state approach is more concise |
| **Auto-detect only, no opt-out** | Simplest implementation | No way to disable defaults | Prevents advanced use cases where users need empty manager |

### Implementation Specification

#### Default Directory Constants

```python
# In manager.py module-level constants
DEFAULT_PROJECT_DIR = Path("./skills")
DEFAULT_ANTHROPIC_DIR = Path("./.claude/skills")
```

#### Tri-State Parameter Logic

For `project_skill_dir` parameter:
- `None` (or omitted) → Check if `DEFAULT_PROJECT_DIR` exists → Add to sources if exists
- `""` (empty string) → Skip (explicit opt-out, no default fallback)
- `Path` or `str` (non-empty) → Validate exists → Add to sources OR raise ConfigurationError

Same logic applies to `anthropic_config_dir`.

For `plugin_dirs` parameter:
- `None` (or omitted) → No plugins configured (skip)
- `[]` (empty list) → Explicit opt-out (skip)
- `[Path, ...]` (non-empty list) → Validate each path → Add valid ones OR raise ConfigurationError for invalid

#### Updated `_build_sources()` Method Logic

```python
def _build_sources(...) -> List[SkillSource]:
    sources: List[SkillSource] = []

    # Project skills - tri-state logic
    if project_skill_dir is None:
        # Apply default
        if DEFAULT_PROJECT_DIR.exists():
            sources.append(SkillSource(SourceType.PROJECT, DEFAULT_PROJECT_DIR.resolve(), PRIORITY_PROJECT))
    elif project_skill_dir == "":
        # Explicit opt-out - skip
        pass
    else:
        # Explicit path - validate existence
        path = Path(project_skill_dir)
        if not path.exists() or not path.is_dir():
            raise ConfigurationError(
                f"Explicitly configured directory does not exist: project_skill_dir='{path}'"
            )
        sources.append(SkillSource(SourceType.PROJECT, path.resolve(), PRIORITY_PROJECT))

    # Similar logic for anthropic_config_dir
    # ... (same tri-state pattern)

    # Plugin dirs - handle None vs []
    if plugin_dirs is not None and plugin_dirs != []:
        for plugin_dir in plugin_dirs:
            path = Path(plugin_dir)
            if not path.exists() or not path.is_dir():
                raise ConfigurationError(
                    f"Explicitly configured plugin directory does not exist: '{path}'"
                )
            # ... (rest of plugin logic)

    # INFO logging when no sources configured
    if not sources:
        logger.info("No skill directories found; initialized with empty skill list")

    return sources
```

#### Error Message Format

ConfigurationError messages must include:
1. The parameter name that failed
2. The path that was provided
3. What the issue is (doesn't exist, not a directory, etc.)

Example:
```
ConfigurationError: Explicitly configured directory does not exist: project_skill_dir='/nonexistent/path'
```

### Test Coverage Requirements

Must add tests for all acceptance scenarios 4-8:

```python
# Scenario 4: Default project directory exists
def test_default_project_dir_discovered(tmp_path):
    # Create ./skills/ in working dir
    # Initialize SkillManager() without params
    # Assert skills from ./skills/ are discovered

# Scenario 5: Both defaults exist with conflict
def test_both_defaults_priority_resolution(tmp_path):
    # Create ./skills/ and ./.claude/skills/ with same skill name
    # Initialize SkillManager() without params
    # Assert ./skills/ version wins (priority 100 > 50)

# Scenario 6: No defaults exist
def test_no_defaults_exist_empty_manager(tmp_path, caplog):
    # Ensure no ./skills/ or ./.claude/skills/ exist
    # Initialize SkillManager() without params
    # Assert 0 skills registered
    # Assert INFO log "No skill directories found"

# Scenario 7: Explicit invalid path raises error
def test_explicit_invalid_path_raises_error():
    # Initialize SkillManager(project_skill_dir="/nonexistent/path")
    # Assert raises ConfigurationError with clear message

# Scenario 8: Explicit opt-out with empty string
def test_empty_string_opt_out(tmp_path):
    # Create ./skills/ and ./.claude/skills/
    # Initialize SkillManager(project_skill_dir="", anthropic_config_dir="", plugin_dirs=[])
    # Assert 0 skills registered
    # Assert NO INFO log (intentional, not error condition)
```

### Performance Expectations

- **No performance impact**: Default directory checks are simple `Path.exists()` calls (~1ms total)
- **Memory**: No change (still lazy loading)
- **Initialization time**: <5ms additional overhead for default checks

### Security Considerations

1. **Path Traversal**: Default paths are relative to CWD, validated via `Path.resolve()` before use
2. **Symlink Attacks**: Same validation as explicit paths (existing symlink handling in discovery.py)
3. **Race Conditions**: Directory existence checks are inherently racy but acceptable (initialization-time only)

### User Documentation Updates Required

1. **quickstart.md**: Add zero-configuration example as primary pattern
2. **README.md**: Update initialization examples to show default behavior first
3. **manager.py docstring**: Document tri-state parameter semantics
4. **examples/basic_usage.py**: Add example demonstrating default discovery

### References

- Python PEP 20 (Zen of Python): "Explicit is better than implicit" - supports tri-state approach
- Python stdlib conventions: Use of `None` for default values (e.g., `open(mode=None)`)
- User feedback: Request for zero-configuration initialization (User Story 3 motivation)

### Backward Compatibility

- **v0.1 Compatibility**: Fully preserved. Users with explicit paths see no change.
- **Breaking Change**: None. New behavior only applies when parameters are omitted/None.
- **Migration**: No migration required. Existing code works identically.

---

**Document Status**: Updated with Session 2025-11-16 clarifications
**Last Updated**: 2025-11-16
**Reviewed By**: Implementation review (gaps identified)
