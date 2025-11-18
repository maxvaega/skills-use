# Data Model: Script Execution Feature

**Feature**: Script Execution Support for Skills
**Version**: v0.3.0
**Date**: 2025-01-17

---

## Overview

This document defines the data models (classes, dataclasses, types) required for the script execution feature. All models follow skillkit's existing patterns (dataclasses with slots, immutability where possible, type hints).

---

## Core Data Models

### 1. ScriptMetadata

**Purpose**: Represents detected script information during lazy script detection

**Location**: `src/skillkit/core/scripts.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass(frozen=True, slots=True)
class ScriptMetadata:
    """Metadata for a detected executable script.

    Created during lazy script detection (triggered on skill invocation).
    Stored in Skill object for the skill's lifetime in memory.
    """

    name: str
    """Script name (filename without extension).

    Example: 'extract' for 'extract.py'
    """

    path: Path
    """Relative path from skill base directory.

    Example: Path('scripts/extract.py') or Path('scripts/utils/parser.js')
    Must be relative, not absolute.
    """

    script_type: str
    """Script language/interpreter type.

    Values: 'python', 'shell', 'javascript', 'ruby', 'perl'
    Determined from file extension (.py → python, .sh → shell, etc.)
    """

    description: str
    """Script description extracted from first comment block.

    Extracted by parsing first comment block (#, //, """, etc.) up to 500 chars.
    Empty string if no comments found (per FR-009).
    """

    def get_fully_qualified_name(self, skill_name: str) -> str:
        """Get LangChain tool name for this script.

        Args:
            skill_name: Name of the parent skill

        Returns:
            Fully qualified tool name (e.g., 'pdf-extractor.extract')
        """
        return f"{skill_name}.{self.name}"
```

**Design Notes**:
- `frozen=True`: Immutable after creation (thread-safe, cacheable)
- `slots=True`: Memory optimization (60% reduction per instance)
- `path` is relative (not absolute) for portability across deployments

---

### 2. ScriptExecutionResult

**Purpose**: Represents the outcome of script execution with all captured data

**Location**: `src/skillkit/core/scripts.py`

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass(frozen=True, slots=True)
class ScriptExecutionResult:
    """Result of executing a script with security controls.

    Returned by ScriptExecutor.execute() and SkillManager.execute_skill_script().
    Contains all captured output, exit status, timing, and error information.
    """

    stdout: str
    """Captured standard output (decoded as UTF-8).

    Truncated at 10MB with '[... output truncated ...]' marker if exceeded.
    Empty string if script produced no output.
    """

    stderr: str
    """Captured standard error (decoded as UTF-8).

    Truncated at 10MB if exceeded.
    Contains 'Signal: <NAME>' if script was terminated by signal.
    Contains 'Timeout' if script exceeded timeout limit.
    """

    exit_code: int
    """Process exit code.

    0: Success
    1-255: Error (script-defined)
    -N: Killed by signal N (Unix only, e.g., -11 = SIGSEGV)
    124: Timeout (conventional timeout exit code)
    """

    execution_time_ms: float
    """Execution duration in milliseconds.

    Measured from subprocess start to completion (includes overhead).
    Accuracy: ~0.1ms (depends on system clock resolution).
    """

    script_path: Path
    """Absolute path to the executed script (resolved, validated).

    Guaranteed to be within skill base directory (security validated).
    """

    signal: Optional[str]
    """Signal name if script was terminated by signal (Unix only).

    Examples: 'SIGSEGV', 'SIGKILL', 'SIGTERM', 'SIGINT'
    None if script exited normally.
    """

    signal_number: Optional[int]
    """Signal number if terminated by signal (Unix only).

    Examples: 11 (SIGSEGV), 9 (SIGKILL), 15 (SIGTERM)
    None if exited normally.
    Corresponds to negative exit_code (signal_number = -exit_code).
    """

    stdout_truncated: bool
    """True if stdout was truncated due to 10MB size limit."""

    stderr_truncated: bool
    """True if stderr was truncated due to 10MB size limit."""

    @property
    def success(self) -> bool:
        """True if script exited successfully (exit_code == 0)."""
        return self.exit_code == 0

    @property
    def timeout(self) -> bool:
        """True if script was killed due to timeout."""
        return self.exit_code == 124 and 'Timeout' in self.stderr

    @property
    def signaled(self) -> bool:
        """True if script was terminated by signal."""
        return self.signal is not None
```

**Design Notes**:
- Immutable and frozen for safety
- Includes both raw data (exit_code, stdout) and derived properties (success, timeout, signaled)
- signal/signal_number are Optional (Unix-only, None on Windows)

---

### 3. ScriptToolResult (LangChain)

**Purpose**: Formatted return value from LangChain script-based StructuredTools

**Location**: `src/skillkit/integrations/langchain.py`

**Note**: This is not a formal dataclass, but a typed dict return format

```python
from typing import TypedDict, Union, Optional

class ScriptToolResult(TypedDict):
    """Return format for LangChain script tools.

    Follows LangChain tool result protocol:
    - On success (exit_code==0): content = stdout, is_error = False
    - On failure (exit_code!=0): raise ToolException with stderr message

    This TypedDict documents the expected structure, but tools
    typically return just the content string or raise exceptions.
    """

    type: str  # Always "tool_result"
    tool_use_id: str  # Unique identifier for this invocation
    content: Union[str, list, None]  # stdout on success, None on error
    is_error: bool  # False on success, True on error
```

**LangChain Tool Behavior**:
```python
def execute_script_tool(arguments: dict) -> str:
    """
    LangChain StructuredTool function for script execution.

    Args:
        arguments: Free-form JSON dict passed from agent

    Returns:
        stdout string if exit_code == 0

    Raises:
        ToolException: If exit_code != 0, with stderr as message
    """
    result = executor.execute(script_path, arguments, ...)

    if result.exit_code == 0:
        return result.stdout  # Success: return content
    else:
        raise ToolException(result.stderr)  # Failure: raise exception
```

---

## Supporting Models

### 4. InterpreterMapping

**Purpose**: Configuration for mapping file extensions to interpreters

**Location**: `src/skillkit/core/scripts.py`

```python
from typing import Dict

# Extension-to-interpreter mapping (immutable dict)
INTERPRETER_MAP: Dict[str, str] = {
    '.py': 'python3',      # Python 3.x
    '.sh': 'bash',         # Bash shell
    '.js': 'node',         # Node.js
    '.rb': 'ruby',         # Ruby interpreter
    '.pl': 'perl',         # Perl interpreter
    '.bat': 'cmd',         # Windows batch (Windows only)
    '.cmd': 'cmd',         # Windows command (Windows only)
    '.ps1': 'powershell',  # PowerShell (cross-platform)
}
```

**Design Notes**:
- Constant dict (UPPER_CASE naming)
- Keys are lowercase file extensions (including dot)
- Values are interpreter command names (not full paths)

---

### 5. Environment Variables (for Script Execution)

**Purpose**: Environment variables injected into script execution context

**Location**: Passed as dict to subprocess, not a formal data model

```python
env_vars = {
    'SKILL_NAME': skill.metadata.name,        # e.g., 'pdf-extractor'
    'SKILL_BASE_DIR': str(skill.base_dir),    # e.g., '/path/to/skills/pdf-extractor'
    'SKILL_VERSION': skill.metadata.version,  # e.g., '1.0.0'
    'SKILLKIT_VERSION': __version__,          # e.g., '0.3.0'
}
```

**Contract**: These 4 variables are guaranteed to be available in all script executions.

---

## Integration with Existing Models

### Skill Model Extension

**File**: `src/skillkit/core/models.py` (existing)

```python
@dataclass(slots=True)
class Skill:
    """Skill with content and metadata (existing class).

    Extended in v0.3.0 to support script detection and caching.
    """

    # ... existing fields (metadata, content, etc.)

    _scripts: Optional[List[ScriptMetadata]] = field(default=None, init=False, repr=False)
    """Cached detected scripts (lazy-loaded, private).

    Populated on first access to scripts property.
    None until scripts are detected (lazy initialization).
    """

    @property
    def scripts(self) -> List[ScriptMetadata]:
        """Get detected scripts (lazy-loaded).

        Detection runs once on first access, results cached for skill lifetime.

        Returns:
            List of ScriptMetadata (may be empty if no scripts found)
        """
        if self._scripts is None:
            from skillkit.core.scripts import ScriptDetector
            detector = ScriptDetector()
            self._scripts = detector.detect_scripts(self.base_dir)
        return self._scripts
```

**Design Notes**:
- Lazy loading pattern (scripts detected only when first accessed)
- Private `_scripts` field with public `scripts` property
- Detection happens during skill invocation, not during discovery

---

### SkillManager Extension

**File**: `src/skillkit/core/manager.py` (existing)

```python
class SkillManager:
    """Manage skill lifecycle (existing class).

    Extended in v0.3.0 to support script execution.
    """

    # ... existing methods (discover, invoke_skill, etc.)

    def execute_skill_script(
        self,
        skill_name: str,
        script_name: str,
        arguments: dict,
        timeout: Optional[int] = None
    ) -> ScriptExecutionResult:
        """Execute a specific script from a skill.

        Args:
            skill_name: Name of the skill (e.g., 'pdf-extractor')
            script_name: Name of the script without extension (e.g., 'extract')
            arguments: Arguments to pass as JSON via stdin
            timeout: Execution timeout in seconds (default: self.default_script_timeout)

        Returns:
            ScriptExecutionResult with execution details

        Raises:
            SkillNotFoundError: If skill doesn't exist
            ScriptNotFoundError: If script not found in skill
            InterpreterNotFoundError: If required interpreter not available
            PathSecurityError: If script path validation fails
            ToolRestrictionError: If 'Bash' not in allowed-tools
        """
        pass  # Implementation in Phase 2
```

---

## Exception Models

**File**: `src/skillkit/core/exceptions.py` (existing, extend with new exceptions)

```python
class InterpreterNotFoundError(SkillKitError):
    """Raised when required interpreter is not available in PATH.

    Example:
        InterpreterNotFoundError("Interpreter 'node' not found in PATH for script.js")
    """
    pass

class ScriptNotFoundError(SkillKitError):
    """Raised when requested script doesn't exist in skill.

    Example:
        ScriptNotFoundError("Script 'extract' not found in skill 'pdf-extractor'")
    """
    pass

class ScriptPermissionError(SkillKitError):
    """Raised when script has dangerous permissions (setuid/setgid).

    Example:
        ScriptPermissionError("Script has setuid bit: scripts/dangerous.py")
    """
    pass

class ArgumentSerializationError(SkillKitError):
    """Raised when arguments cannot be serialized to JSON.

    Example:
        ArgumentSerializationError("Cannot serialize arguments: circular reference detected")
    """
    pass

class ArgumentSizeError(SkillKitError):
    """Raised when JSON-serialized arguments exceed 10MB size limit.

    Example:
        ArgumentSizeError("Arguments too large: 15728640 bytes (max 10MB)")
    """
    pass
```

---

## Type Aliases

**File**: `src/skillkit/core/scripts.py`

```python
from typing import Dict, Any, List
from pathlib import Path

# Type aliases for clarity
ScriptArguments = Dict[str, Any]
"""Arguments passed to scripts as JSON (free-form dict)."""

ScriptEnvironment = Dict[str, str]
"""Environment variables for script execution (str keys and values)."""

ScriptList = List[ScriptMetadata]
"""List of detected scripts for a skill."""
```

---

## Validation Rules

### ScriptMetadata Validation

```python
def validate_script_metadata(meta: ScriptMetadata, skill_base_dir: Path) -> None:
    """Validate ScriptMetadata consistency.

    Raises:
        ValueError: If validation fails
    """
    # Path must be relative
    if meta.path.is_absolute():
        raise ValueError(f"Script path must be relative: {meta.path}")

    # Script type must be supported
    valid_types = {'python', 'shell', 'javascript', 'ruby', 'perl'}
    if meta.script_type not in valid_types:
        raise ValueError(f"Invalid script type: {meta.script_type}")

    # Name must match filename stem
    expected_name = meta.path.stem
    if meta.name != expected_name:
        raise ValueError(
            f"Name mismatch: name='{meta.name}', path stem='{expected_name}'"
        )
```

### ScriptExecutionResult Validation

```python
def validate_execution_result(result: ScriptExecutionResult) -> None:
    """Validate ScriptExecutionResult consistency.

    Raises:
        ValueError: If validation fails
    """
    # Signal info should be consistent with exit code
    if result.signal is not None:
        if result.exit_code >= 0:
            raise ValueError(
                f"Signal present but exit_code is positive: {result.exit_code}"
            )
        if result.signal_number != -result.exit_code:
            raise ValueError(
                f"Signal number mismatch: signal_number={result.signal_number}, "
                f"exit_code={result.exit_code}"
            )

    # Timeout should have exit code 124
    if result.timeout and result.exit_code != 124:
        raise ValueError(f"Timeout but exit_code != 124: {result.exit_code}")
```

---

## Relationships Between Models

```
Skill (extended)
  └─> scripts: List[ScriptMetadata] (lazy-loaded)
        └─> Each ScriptMetadata describes one script file

SkillManager.execute_skill_script()
  ├─> Takes: skill_name + script_name + arguments
  ├─> Looks up: ScriptMetadata from Skill.scripts
  ├─> Executes: via ScriptExecutor
  └─> Returns: ScriptExecutionResult

LangChainSkillAdapter.create_script_tools()
  ├─> Reads: Skill.scripts (List[ScriptMetadata])
  ├─> Creates: One StructuredTool per ScriptMetadata
  └─> Tool invocation returns: ScriptToolResult (stdout or exception)
```

---

## Memory Footprint Analysis

**Per-Skill Overhead** (for script support):

| Component | Size | Count | Total |
|-----------|------|-------|-------|
| ScriptMetadata | ~200 bytes | 5 scripts | 1 KB |
| Cached `_scripts` list | ~100 bytes | 1 | 100 bytes |
| **Total per skill** | | | **~1.1 KB** |

**For 100 skills with 5 scripts each**:
- Total overhead: ~110 KB
- Negligible compared to skill content (typically 10-50 KB per skill)

**Design Trade-off**: Lazy loading amortizes detection cost but adds minimal memory overhead for caching.

---

## Schema Evolution (Future Versions)

**v0.3.1+ Potential Extensions**:

```python
@dataclass(frozen=True, slots=True)
class ScriptMetadata:
    # ... existing fields ...

    # Potential additions:
    input_schema: Optional[dict] = None
    """JSON Schema for script input validation (extracted from docstring)."""

    output_schema: Optional[dict] = None
    """JSON Schema for script output format (extracted from docstring)."""

    dependencies: List[str] = field(default_factory=list)
    """Required packages (e.g., ['pdf-lib', 'sharp'] for Node.js)."""

    min_interpreter_version: Optional[str] = None
    """Minimum interpreter version required (e.g., '3.10' for Python)."""
```

**v0.4.0+ Potential Extensions**:
- Script execution caching (memoization)
- Binary executable support (compiled scripts)
- Container-based sandboxing integration

---

## Summary

**Core Models**:
1. `ScriptMetadata` - Detected script information
2. `ScriptExecutionResult` - Script execution outcome
3. `ScriptToolResult` - LangChain tool return format (TypedDict)

**Supporting Models**:
4. `INTERPRETER_MAP` - Extension-to-interpreter mapping (constant)
5. Environment variables dict - Injected into script context

**Extensions**:
6. `Skill.scripts` property - Lazy-loaded script list
7. `SkillManager.execute_skill_script()` - Script execution API

**Exceptions**:
8. 5 new exception types for script-specific errors

All models follow skillkit's design principles:
- Immutable where possible (`frozen=True`)
- Memory-efficient (`slots=True`)
- Fully type-hinted
- Clear documentation
- Validation rules enforced

**Next Steps**: Generate contracts/ for API interfaces and message formats.
