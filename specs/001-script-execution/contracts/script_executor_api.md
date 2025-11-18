# Script Executor API Contract

**Module**: `skillkit.core.scripts.ScriptExecutor`
**Version**: v0.3.0
**Purpose**: Execute scripts with security controls, timeout enforcement, and comprehensive error handling

---

## Class Interface

### ScriptExecutor

```python
class ScriptExecutor:
    """Execute scripts with security controls and error handling."""

    def __init__(
        self,
        timeout: int = 30,
        max_output_size: int = 10 * 1024 * 1024,  # 10MB
        use_cache: bool = True
    ) -> None:
        """
        Initialize ScriptExecutor.

        Args:
            timeout: Default timeout in seconds (1-600)
            max_output_size: Maximum output size per stream in bytes
            use_cache: Whether to cache interpreter paths (LRU cache)

        Raises:
            ValueError: If timeout < 1 or timeout > 600
        """

    def execute(
        self,
        script_path: Path,
        arguments: Dict[str, Any],
        skill_base_dir: Path,
        skill_metadata: SkillMetadata,
        timeout: Optional[int] = None
    ) -> ScriptExecutionResult:
        """
        Execute a script with full security validation.

        Process:
        1. Validate script path (within skill directory, no traversal)
        2. Check script permissions (reject setuid/setgid)
        3. Resolve interpreter (extension mapping + shebang fallback)
        4. Serialize arguments to JSON
        5. Execute with timeout and environment injection
        6. Capture output with size limits
        7. Detect signals and format errors
        8. Log execution for auditing

        Args:
            script_path: Absolute path to script file
            arguments: Arguments to pass as JSON via stdin
            skill_base_dir: Base directory of the skill (for path validation)
            skill_metadata: Skill metadata (for environment variables)
            timeout: Execution timeout in seconds (overrides default)

        Returns:
            ScriptExecutionResult with execution details

        Raises:
            PathSecurityError: If script path escapes skill directory
            ScriptPermissionError: If script has dangerous permissions
            InterpreterNotFoundError: If interpreter not available in PATH
            ArgumentSerializationError: If arguments cannot be JSON-serialized
            ArgumentSizeError: If JSON payload exceeds 10MB
            FileNotFoundError: If script file doesn't exist
            OSError: If script cannot be executed (permission denied, etc.)

        Example:
            >>> executor = ScriptExecutor(timeout=60)
            >>> result = executor.execute(
            ...     script_path=Path("/skills/pdf/scripts/extract.py"),
            ...     arguments={"file": "doc.pdf"},
            ...     skill_base_dir=Path("/skills/pdf"),
            ...     skill_metadata=metadata
            ... )
            >>> if result.success:
            ...     print(result.stdout)
        """
```

---

## Method Contract Details

### execute() Pre-Conditions

```python
# Path validation
assert script_path.is_absolute()
assert script_path.exists()
assert script_path.is_file()
# script_path must resolve to within skill_base_dir

# Arguments validation
assert isinstance(arguments, dict)
assert json.dumps(arguments)  # Must be JSON-serializable
assert len(json.dumps(arguments)) <= 10 * 1024 * 1024  # Max 10MB

# Timeout validation
assert timeout is None or (1 <= timeout <= 600)
```

### execute() Post-Conditions

```python
result = executor.execute(...)

# Always returns ScriptExecutionResult (never None)
assert isinstance(result, ScriptExecutionResult)

# Exit code is always set
assert isinstance(result.exit_code, int)

# Stdout/stderr are always strings (never None)
assert isinstance(result.stdout, str)
assert isinstance(result.stderr, str)

# Execution time is always positive
assert result.execution_time_ms > 0

# Signal info is consistent
if result.signal is not None:
    assert result.exit_code < 0
    assert result.signal_number == -result.exit_code

# Timeout is properly detected
if result.timeout:
    assert result.exit_code == 124
    assert 'Timeout' in result.stderr
```

### execute() Error Handling

```python
try:
    result = executor.execute(...)
except PathSecurityError as e:
    # Script path escapes skill directory
    # e.g., "Script path escapes skill directory: ../../etc/passwd"
    pass

except ScriptPermissionError as e:
    # Script has setuid/setgid permissions
    # e.g., "Script has setuid bit: scripts/dangerous.py"
    pass

except InterpreterNotFoundError as e:
    # Required interpreter not in PATH
    # e.g., "Interpreter 'node' not found in PATH for script.js"
    pass

except ArgumentSerializationError as e:
    # Arguments cannot be JSON-serialized
    # e.g., "Cannot serialize arguments: circular reference"
    pass

except ArgumentSizeError as e:
    # JSON payload too large
    # e.g., "Arguments too large: 15728640 bytes (max 10MB)"
    pass

except FileNotFoundError as e:
    # Script file doesn't exist
    pass

except OSError as e:
    # Other OS-level errors (permissions, etc.)
    pass
```

---

## Environment Variables Injected

```python
env = {
    'SKILL_NAME': skill_metadata.name,
    'SKILL_BASE_DIR': str(skill_base_dir),
    'SKILL_VERSION': skill_metadata.version,
    'SKILLKIT_VERSION': '0.3.0',  # From skillkit.__version__
}
```

**Contract**: These 4 variables are ALWAYS injected into every script execution.

---

## Subprocess Configuration

```python
subprocess.run(
    [interpreter, str(script_path)],  # List form (secure)
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    input=json_data,                  # JSON via stdin
    timeout=timeout,
    cwd=skill_base_dir,               # Working directory = skill base
    shell=False,                      # CRITICAL: Never True
    text=True,                        # Decode as UTF-8
    check=False                       # Handle errors manually
)
```

**Security Guarantees**:
- ✅ `shell=False` prevents command injection
- ✅ List-form command prevents shell interpolation
- ✅ Working directory is skill base (scripts can use relative paths)
- ✅ JSON via stdin (secure, not visible in process listings)

---

## Logging Contract

Every execution is logged with:

```python
# INFO level (on success)
logger.info(
    f"Script executed: {script_path.name} | "
    f"exit_code=0 | "
    f"time={execution_time_ms:.2f}ms"
)

# ERROR level (on failure)
logger.error(
    f"Script failed: {script_path.name} | "
    f"exit_code={exit_code} | "
    f"time={execution_time_ms:.2f}ms | "
    f"error={stderr[:256]}"  # Truncated to 256 chars
)

# WARNING level (on timeout)
logger.warning(
    f"Script timeout: {script_path.name} exceeded {timeout}s"
)

# WARNING level (on output truncation)
logger.warning(
    f"Stdout truncated for {script_path.name}: "
    f"{len(stdout)} bytes -> {max_output_size} bytes"
)
```

**Audit Requirements**:
- Timestamp: Automatic from logger
- Script path: Relative to skill base (no sensitive paths)
- Arguments: Truncated to 256 chars in logs (no full argument logging for security)
- Exit code: Always logged
- Execution time: Always logged

---

## Performance Guarantees

**Overhead** (excluding actual script runtime):
- Path validation: <1ms
- Permission checks: <1ms
- Interpreter resolution: <5ms (first call) or <0.01ms (cached)
- JSON serialization: <10ms for typical payloads (<1MB)
- Process spawning: ~10-30ms (OS-dependent)
- Output capture: <10ms for typical outputs (<1MB)
- **Total overhead**: <50ms for 95% of executions (per SC-001)

**Scalability**:
- Concurrent executions: Supported (independent subprocesses)
- Memory per execution: ~10-20MB baseline + script memory usage
- Max concurrent: Limited by OS process limits (typically 1000+)

---

## Thread Safety

**ScriptExecutor is thread-safe**:
- No shared mutable state
- Each execution uses independent subprocess
- Interpreter cache is thread-safe (LRU cache with locks)

**Concurrent executions**:
```python
from concurrent.futures import ThreadPoolExecutor

executor = ScriptExecutor()

with ThreadPoolExecutor(max_workers=10) as pool:
    futures = [
        pool.submit(executor.execute, script, args, base, meta)
        for script, args in jobs
    ]
    results = [f.result() for f in futures]
```

---

## Example Usage

### Basic Execution

```python
from skillkit.core.scripts import ScriptExecutor
from pathlib import Path

executor = ScriptExecutor(timeout=30)

result = executor.execute(
    script_path=Path("/skills/pdf-extractor/scripts/extract.py"),
    arguments={
        "file_path": "documents/sample.pdf",
        "output_format": "text"
    },
    skill_base_dir=Path("/skills/pdf-extractor"),
    skill_metadata=skill.metadata
)

if result.success:
    print(f"Success: {result.stdout}")
else:
    print(f"Error (exit {result.exit_code}): {result.stderr}")
```

### Error Handling

```python
try:
    result = executor.execute(
        script_path=Path("/skills/data-processor/scripts/transform.py"),
        arguments={"data": large_dataset},
        skill_base_dir=Path("/skills/data-processor"),
        skill_metadata=skill.metadata,
        timeout=120  # Override default timeout
    )
except InterpreterNotFoundError:
    print("Please install Python 3.10+ to use this skill")
except ArgumentSizeError:
    print("Dataset too large, please use file-based input")
except PathSecurityError as e:
    print(f"Security violation: {e}")
```

### Signal Detection

```python
result = executor.execute(...)

if result.signaled:
    print(f"Script crashed with {result.signal} (signal {result.signal_number})")
    print(f"This may indicate a bug in the script")

if result.timeout:
    print(f"Script exceeded timeout, try increasing timeout value")
```

---

## Security Contract

**Guaranteed Security Validations** (in order):

1. **Path Traversal Prevention**:
   ```python
   real_path = Path(os.path.realpath(script_path))
   real_base = Path(os.path.realpath(skill_base_dir))
   assert os.path.commonpath([real_path, real_base]) == real_base
   ```

2. **Permission Validation**:
   ```python
   st = os.stat(script_path)
   assert not (st.st_mode & stat.S_ISUID)
   assert not (st.st_mode & stat.S_ISGID)
   ```

3. **Interpreter Validation**:
   ```python
   assert shutil.which(interpreter) is not None
   ```

4. **Argument Validation**:
   ```python
   json_data = json.dumps(arguments)
   assert len(json_data) <= 10 * 1024 * 1024
   ```

5. **Subprocess Security**:
   ```python
   assert shell == False
   assert isinstance(cmd, list)
   ```

**Attack Patterns Blocked**:
- ❌ `../../../../etc/passwd` (relative traversal)
- ❌ `/etc/passwd` (absolute path escape)
- ❌ Symlinks outside skill directory
- ❌ Scripts with setuid/setgid bits
- ❌ Shell interpolation attacks
- ❌ Command injection via `shell=True`
- ❌ DoS via massive outputs (10MB limit)
- ❌ DoS via infinite loops (timeout)

---

## Testing Contract

**Required Unit Tests**:
- ✅ Successful execution (exit code 0)
- ✅ Failed execution (exit code 1)
- ✅ Timeout handling (exit code 124)
- ✅ Signal termination (SIGSEGV, SIGKILL)
- ✅ Path traversal attack prevention
- ✅ Symlink validation
- ✅ Permission checks (setuid/setgid)
- ✅ Missing interpreter error
- ✅ JSON serialization errors
- ✅ Argument size limit enforcement
- ✅ Output truncation at 10MB
- ✅ Encoding errors (non-UTF-8 output)
- ✅ Environment variable injection
- ✅ Concurrent executions

**Test Coverage Target**: 90%+ for ScriptExecutor class

---

## Version History

| Version | Changes |
|---------|---------|
| v0.3.0  | Initial implementation |

---

## Related Contracts

- [Script Detector API](./script_detector_api.md)
- [Skill Manager Extensions](./skill_manager_extensions.md)
- [LangChain Integration](./langchain_integration.md)
