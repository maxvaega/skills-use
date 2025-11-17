# FilePathResolver API Contract

**Version**: v0.2
**Module**: `skillkit.core.path_resolver`

This document specifies the public API for secure file path resolution within skill directories.

---

## Purpose

`FilePathResolver` provides secure resolution of relative file paths from a skill's base directory, preventing directory traversal attacks while allowing access to bundled supporting files (scripts, templates, docs).

---

## Class: FilePathResolver

### `resolve_path()`

**Signature**:
```python
@staticmethod
def resolve_path(base_directory: Path, relative_path: str) -> Path
```

**Parameters**:
- `base_directory`: Skill base directory (e.g., `./skills/my-skill/`)
- `relative_path`: User-provided relative path (e.g., `"scripts/helper.py"`)

**Returns**:
- `Path`: Validated absolute path to the file

**Behavior**:
1. Validates `relative_path` is not absolute
2. Joins `base_directory` with `relative_path`
3. Resolves path to canonical form (follows symlinks, removes `.` and `..`)
4. Validates resolved path is descendant of `base_directory` using `Path.is_relative_to()`
5. Returns validated absolute path

**Security Guarantees**:
- **Path Traversal Prevention**: All `..` sequences validated after resolution
- **Symlink Handling**: Follows symlinks, then validates target is within base
- **Absolute Path Rejection**: Refuses absolute paths (e.g., `/etc/passwd`)
- **Canonical Validation**: Uses `Path.resolve()` to normalize before checking

**Exceptions**:
- `PathSecurityError`: If validation fails (traversal attempt, absolute path, symlink escape)
  - Exception message includes: skill name (if context available), attempted path, base directory

**Examples**:

```python
from pathlib import Path
from skillkit.core.path_resolver import FilePathResolver
from skillkit.core.exceptions import PathSecurityError

# Valid: subdirectory access
base = Path("/skills/my-skill")
path = FilePathResolver.resolve_path(base, "scripts/helper.py")
print(path)  # /skills/my-skill/scripts/helper.py

# Valid: same directory
path = FilePathResolver.resolve_path(base, "README.md")
print(path)  # /skills/my-skill/README.md

# Valid: nested subdirectories
path = FilePathResolver.resolve_path(base, "templates/config/default.yaml")
print(path)  # /skills/my-skill/templates/config/default.yaml

# Invalid: directory traversal
try:
    FilePathResolver.resolve_path(base, "../../../etc/passwd")
except PathSecurityError as e:
    print(e)  # "Path traversal attempt detected: '../../../etc/passwd' escapes base directory '/skills/my-skill/'"

# Invalid: absolute path
try:
    FilePathResolver.resolve_path(base, "/etc/passwd")
except PathSecurityError as e:
    print(e)  # "Absolute paths not allowed: '/etc/passwd'"

# Invalid: symlink escaping base
# Assuming /skills/my-skill/evil-link -> /etc/passwd
try:
    FilePathResolver.resolve_path(base, "evil-link")
except PathSecurityError as e:
    print(e)  # "Path traversal via symlink: 'evil-link' resolves outside base directory"
```

---

## Exception: PathSecurityError

**Module**: `skillkit.core.exceptions`

**Base Class**: `SkillKitError`

**Purpose**: Raised when file path validation detects a security violation

**Attributes**:
- `message: str` - Descriptive error message
- `base_directory: Path | None` - Base directory context
- `attempted_path: str | None` - User-provided path that failed validation
- `resolved_path: Path | None` - Resolved path (before validation failure)

**Error Message Format**:
```
Path traversal attempt detected: '{attempted_path}' escapes base directory '{base_directory}'
```

**Logging**:
- All `PathSecurityError` exceptions are automatically logged at ERROR level with full context
- Logs include: timestamp, skill name (if available), attempted path, base directory, resolved path

**Example**:
```python
try:
    path = FilePathResolver.resolve_path(base, "../../../etc/passwd")
except PathSecurityError as e:
    print(f"Security violation: {e}")
    print(f"Base: {e.base_directory}")
    print(f"Attempted: {e.attempted_path}")
    # Logs automatically written to logger with ERROR level
```

---

## Attack Vectors Tested

The `resolve_path()` implementation is validated against these attack patterns:

1. **Simple parent traversal**: `../../../etc/passwd`
2. **Encoded traversal**: `%2e%2e%2f%2e%2e%2f` (URL-encoded `../../`)
3. **Mixed separators**: `..\..\..\etc\passwd` (Windows-style on Unix)
4. **Absolute paths**: `/etc/passwd`, `C:\Windows\System32`
5. **Symlink escape**: Symlink pointing outside base directory
6. **Circular symlinks**: Symlink loops (should not hang)
7. **Redundant separators**: `scripts//helper.py`, `./scripts/./helper.py`

All attack vectors **must be blocked** and raise `PathSecurityError`.

---

## Integration with Skill Processing

### Processor Integration

File path resolution is integrated into the `BaseDirectoryProcessor`:

**v0.2 Enhanced BaseDirectoryProcessor**:
```python
class BaseDirectoryProcessor:
    def process(self, content: str, context: dict[str, Any]) -> str:
        base_directory = Path(context["base_directory"])

        # Inject base directory context
        header = f"Base directory for this skill: {base_directory}\n\n"

        # Add file path resolution helper message
        helper = (
            "To access supporting files within this skill directory, "
            "use relative paths (e.g., 'scripts/helper.py', 'templates/config.yaml'). "
            "Path traversal attempts (e.g., '../../../') will be blocked.\n\n"
        )

        return header + helper + content
```

### User Workflow

1. **Skill author** bundles supporting files:
   ```
   skills/my-skill/
   ├── SKILL.md
   ├── scripts/
   │   └── helper.py
   └── templates/
       └── config.yaml
   ```

2. **Skill content** references files:
   ```markdown
   # My Skill

   This skill uses a helper script located at `scripts/helper.py`.
   You can customize behavior using the config template at `templates/config.yaml`.

   Please invoke the helper script with: python $BASE_DIR/scripts/helper.py
   ```

3. **LLM/User** receives processed content:
   ```
   Base directory for this skill: /path/to/skills/my-skill

   To access supporting files within this skill directory, use relative paths...

   # My Skill

   This skill uses a helper script located at `scripts/helper.py`.
   ...
   ```

4. **LLM/User** accesses files via resolver:
   ```python
   from skillkit.core.path_resolver import FilePathResolver

   base = Path("/path/to/skills/my-skill")
   script_path = FilePathResolver.resolve_path(base, "scripts/helper.py")

   # Execute or read the file
   subprocess.run(["python", str(script_path)])
   ```

---

## Performance Characteristics

### Resolution Time
- **Typical case**: <1ms per path (fast pathlib operations)
- **Symlink resolution**: +1-3ms (depends on filesystem)
- **Validation**: <0.1ms (simple path comparison)

### Memory
- **Static method**: Zero instance overhead
- **Path objects**: ~200 bytes per Path instance (temporary)

### Caching
- No caching implemented (resolution is fast enough)
- Callers may cache resolved paths if needed

---

## Testing Requirements

### Unit Tests

**Test Coverage**:
- Valid paths: same directory, subdirectories, nested subdirectories
- Invalid paths: all 7 attack vectors listed above
- Edge cases: empty path, `.` (current dir), `..` (parent dir)
- Symlinks: valid symlinks within base, symlinks escaping, circular symlinks

**Test Fixtures**:
```
tests/fixtures/skills/path-test-skill/
├── SKILL.md
├── scripts/
│   └── helper.py
├── templates/
│   └── config.yaml
├── valid-symlink -> scripts/helper.py (points within base)
├── evil-symlink -> /etc/passwd (points outside base)
└── circular-symlink -> circular-symlink (points to itself)
```

### Security Tests

**Fuzzing**:
- Generate 1000+ malicious path variations
- Verify all are blocked with `PathSecurityError`
- No false positives (valid paths incorrectly blocked)

**Manual Review**:
- OWASP Path Traversal checklist
- Security audit by second developer

---

## Platform Compatibility

### Cross-Platform Behavior

| Platform | Path Separator | Symlinks Supported | Notes |
|----------|----------------|-------------------|-------|
| Linux    | `/`            | ✅ Yes             | Full support |
| macOS    | `/`            | ✅ Yes             | Full support |
| Windows  | `\` or `/`     | ⚠️ Limited         | Junction points supported, symlinks require admin |

**Windows Notes**:
- `Path.resolve()` handles both `/` and `\` separators
- Symlink detection works for junction points
- Regular symlinks require admin privileges (may not work)
- Testing focuses on non-symlink attack vectors on Windows

### Encoding

- **Path encoding**: UTF-8 (Python default)
- **Case sensitivity**: Platform-dependent (preserved as-is)
  - Linux/macOS: Case-sensitive
  - Windows: Case-insensitive (but case-preserving)

---

## Deprecation & Future Changes

### v0.2 Stable API
- `FilePathResolver.resolve_path()` is **stable** and will not change signature in v0.x

### Future Enhancements (v0.3+)
- Glob pattern support: `resolve_glob(base, "scripts/*.py")` → list of paths
- Validation modes: strict (default) vs permissive (allow symlinks outside base with warning)
- Audit logging: Optional detailed logging of all path resolutions for compliance
