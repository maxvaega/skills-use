# Python Subprocess Security Research (2024-2025)

**Research Date**: 2025-11-18
**Purpose**: Identify security best practices for executing untrusted scripts in skillkit v0.3
**Sources**: OWASP, Python Security Documentation, Stack Overflow, Snyk, Security Researchers

---

## Executive Summary

This research document provides comprehensive guidance on securely executing untrusted Python scripts using the `subprocess` module. Key findings include:

- **CRITICAL**: Always use `shell=False` with list-based arguments to prevent command injection
- **RECOMMENDED**: Use `subprocess.run()` over `Popen()` for simpler use cases with built-in timeout support
- **ESSENTIAL**: Validate script paths using `os.path.realpath()` and `os.path.commonpath()` to prevent path traversal
- **IMPORTANT**: Implement output size limits and streaming to prevent memory exhaustion
- **WARNING**: Avoid `preexec_fn` due to thread safety issues (deprecated in modern Python)

---

## 1. Secure Subprocess Execution Patterns

### Decision: Use `subprocess.run()` with `shell=False` and list-based arguments

### Rationale

1. **Command Injection Prevention**: `shell=False` (the default) prevents shell interpretation of metacharacters, eliminating command chaining attacks
2. **Built-in Timeout**: `subprocess.run()` has native timeout support (added in Python 3.3+)
3. **Simpler API**: Higher-level abstraction handles common cases without manual process management
4. **Automatic Cleanup**: Waits for process completion and sets returncode automatically

### Code Example: Secure Execution

```python
import subprocess
import signal
from pathlib import Path

def execute_script_securely(script_path: Path, timeout: int = 30) -> dict:
    """
    Execute a Python script securely with timeout enforcement.

    Args:
        script_path: Validated path to the script
        timeout: Maximum execution time in seconds

    Returns:
        dict with keys: returncode, stdout, stderr, signal_name, timed_out

    Raises:
        subprocess.TimeoutExpired: If script exceeds timeout
    """
    try:
        # SECURE: List-based arguments, shell=False (default)
        result = subprocess.run(
            ["/usr/bin/python3", str(script_path)],  # Explicit interpreter
            capture_output=True,  # Capture stdout/stderr
            text=True,  # Decode as UTF-8 strings
            timeout=timeout,  # Enforce timeout
            check=False,  # Don't raise on non-zero exit
            shell=False  # CRITICAL: Prevent shell interpretation
        )

        # Detect signal-based termination
        signal_name = None
        if result.returncode < 0:
            signal_num = -result.returncode
            try:
                signal_name = signal.Signals(signal_num).name
            except ValueError:
                signal_name = f"UNKNOWN_SIGNAL_{signal_num}"

        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "signal_name": signal_name,
            "timed_out": False
        }

    except subprocess.TimeoutExpired as e:
        return {
            "returncode": None,
            "stdout": e.stdout.decode('utf-8', errors='replace') if e.stdout else "",
            "stderr": e.stderr.decode('utf-8', errors='replace') if e.stderr else "",
            "signal_name": None,
            "timed_out": True
        }
```

### Code Example: INSECURE Patterns to Avoid

```python
# INSECURE: shell=True with user input
script = user_input  # Could be: "script.py; rm -rf /"
subprocess.run(f"python {script}", shell=True)  # COMMAND INJECTION!

# INSECURE: String concatenation with user input
subprocess.run("python " + user_script, shell=True)  # COMMAND INJECTION!

# INSECURE: f-strings with shell=True
subprocess.run(f"python {user_script}", shell=True)  # COMMAND INJECTION!
```

### When to Use `Popen()` Instead

Use `Popen()` for advanced scenarios requiring:
- Real-time streaming of stdout/stderr during execution
- Bi-directional communication with the subprocess
- Custom signal handling before termination
- Non-blocking execution patterns

**Important**: `Popen()` has the same security requirements (list args, `shell=False`)

### Alternatives Considered

1. **`os.system()`**: REJECTED - Always uses shell, no output capture, deprecated
2. **`os.popen()`**: REJECTED - Uses shell by default, limited control
3. **`subprocess.call()`**: SUPERSEDED by `subprocess.run()` (legacy API)
4. **`subprocess.check_output()`**: VIABLE but raises on non-zero exit (less flexible)

### Security Score: 9.5/10

**Deductions**:
- -0.5: Requires careful path validation (covered in Section 2)

---

## 2. Path Traversal Prevention

### Decision: Use `os.path.realpath()` + `os.path.commonpath()` validation

### Rationale

1. **Symlink Resolution**: `os.path.realpath()` resolves symbolic links to actual file locations
2. **Canonical Paths**: Eliminates `..`, `.`, and double slashes
3. **Boundary Checking**: `os.path.commonpath()` verifies paths stay within allowed directories
4. **Cross-Platform**: Works on Linux, macOS, and Windows (unlike some Unix-specific checks)

### Code Example: Path Validation

```python
import os
from pathlib import Path
from typing import Optional

class PathTraversalError(Exception):
    """Raised when path traversal attack is detected."""
    pass

def validate_script_path(
    base_dir: Path,
    script_path: Path,
    follow_symlinks: bool = False
) -> Path:
    """
    Validate that script_path is within base_dir and safe to execute.

    Args:
        base_dir: Allowed base directory (must be absolute)
        script_path: Path to validate (can be relative or absolute)
        follow_symlinks: If True, resolve symlinks; if False, reject them

    Returns:
        Resolved absolute path to the script

    Raises:
        PathTraversalError: If path escapes base_dir or is a symlink (when disallowed)
        FileNotFoundError: If script doesn't exist
        PermissionError: If script has setuid/setgid bits
    """
    # Ensure base_dir is absolute
    base_dir = base_dir.resolve(strict=True)

    # Convert to absolute path (doesn't resolve symlinks yet)
    if not script_path.is_absolute():
        script_path = base_dir / script_path

    # Check for symlinks BEFORE resolving
    if not follow_symlinks and script_path.is_symlink():
        raise PathTraversalError(f"Symlinks not allowed: {script_path}")

    # Resolve to canonical path (follows symlinks if follow_symlinks=True)
    try:
        resolved_path = script_path.resolve(strict=True)  # strict=True raises if not exists
    except (OSError, RuntimeError) as e:
        # RuntimeError indicates symlink loop (Python 3.13+)
        raise PathTraversalError(f"Invalid path or symlink loop: {script_path}") from e

    # Verify path stays within base_dir
    try:
        common = Path(os.path.commonpath([str(base_dir), str(resolved_path)]))
    except ValueError:
        # Paths on different drives (Windows)
        raise PathTraversalError(f"Path on different drive: {script_path}")

    if common != base_dir:
        raise PathTraversalError(
            f"Path escapes base directory: {script_path} -> {resolved_path}"
        )

    # Additional check: resolved path must start with base_dir
    if not str(resolved_path).startswith(str(base_dir) + os.sep):
        raise PathTraversalError(f"Path outside base directory: {resolved_path}")

    # Verify file exists and is a regular file
    if not resolved_path.is_file():
        raise FileNotFoundError(f"Not a regular file: {resolved_path}")

    # Check for dangerous permissions (Unix-only)
    if hasattr(os, 'stat') and os.name != 'nt':  # Not Windows
        import stat
        file_stat = resolved_path.stat()

        # Reject setuid/setgid scripts (major security risk)
        if file_stat.st_mode & (stat.S_ISUID | stat.S_ISGID):
            raise PermissionError(
                f"Script has setuid/setgid bit: {resolved_path} "
                f"(mode: {oct(file_stat.st_mode)})"
            )

    return resolved_path
```

### Real-World Attack Examples

**Attack 1: Relative Path Traversal**
```python
# Attacker provides: script_path = "../../../../etc/passwd"
# Without validation, this resolves to /etc/passwd
base_dir = Path("/var/skillkit/scripts")
malicious_path = Path("../../../../etc/passwd")

# SECURE: validate_script_path() rejects this
validate_script_path(base_dir, malicious_path)  # Raises PathTraversalError
```

**Attack 2: Symlink to Sensitive File**
```python
# Attacker creates: /tmp/skills/evil.py -> /etc/shadow
# Without validation, executing this exposes sensitive data
malicious_symlink = Path("/tmp/skills/evil.py")

# SECURE: validate_script_path() rejects symlinks by default
validate_script_path(base_dir, malicious_symlink, follow_symlinks=False)  # Raises PathTraversalError
```

**Attack 3: CVE-2024-23334 (aiohttp)**
The 2024 aiohttp vulnerability allowed path traversal when `follow_symlinks=True`:
```python
# Malicious URL: http://example.com/static/../../../../../../etc/passwd
# aiohttp served /etc/passwd due to improper symlink validation

# MITIGATION: Set follow_symlinks=False and use commonpath() checks
```

### Alternatives Considered

1. **`pathlib.Path.is_relative_to()`** (Python 3.9+): VIABLE but less robust than `commonpath()`
2. **String prefix check only**: REJECTED - vulnerable to Unicode tricks, case sensitivity issues
3. **`os.path.abspath()` without `realpath()`**: REJECTED - doesn't resolve symlinks
4. **Regex-based filtering**: REJECTED - error-prone, misses edge cases

### Security Score: 9/10

**Deductions**:
- -1: `os.path.commonpath()` can raise `ValueError` on Windows for paths on different drives (handled in example)

---

## 3. Permission Validation (Unix/Linux/macOS)

### Decision: Reject scripts with setuid/setgid bits using `os.stat()`

### Rationale

1. **Privilege Escalation Risk**: Setuid/setgid scripts can execute with elevated privileges
2. **Python Interpreter Limitation**: Python interpreters ignore setuid/setgid on scripts (security feature)
3. **Attack Surface**: Presence of these bits indicates malicious intent or misconfiguration
4. **Best Practice**: OWASP recommends rejecting privileged scripts from untrusted sources

### Code Example: Permission Checks

```python
import os
import stat
from pathlib import Path

def check_file_permissions(script_path: Path) -> dict:
    """
    Check file permissions and detect security risks.

    Args:
        script_path: Path to the script (already validated)

    Returns:
        dict with permission information

    Raises:
        PermissionError: If dangerous permissions detected
    """
    # Skip permission checks on Windows
    if os.name == 'nt':
        return {"platform": "windows", "checks_skipped": True}

    file_stat = script_path.stat()
    mode = file_stat.st_mode

    # Check for setuid bit (S_ISUID = 0o4000)
    has_setuid = bool(mode & stat.S_ISUID)

    # Check for setgid bit (S_ISGID = 0o2000)
    has_setgid = bool(mode & stat.S_ISGID)

    # Check for sticky bit (S_ISVTX = 0o1000)
    has_sticky = bool(mode & stat.S_ISVTX)

    # SECURITY: Reject setuid/setgid scripts
    if has_setuid or has_setgid:
        raise PermissionError(
            f"Script has dangerous permissions: {script_path}\n"
            f"  Mode: {oct(mode)}\n"
            f"  Setuid: {has_setuid}\n"
            f"  Setgid: {has_setgid}\n"
            f"  Recommendation: Remove setuid/setgid bits with 'chmod u-s,g-s'"
        )

    # Get human-readable permissions
    perms = stat.filemode(mode)

    return {
        "path": str(script_path),
        "mode_octal": oct(mode),
        "mode_human": perms,
        "owner_uid": file_stat.st_uid,
        "group_gid": file_stat.st_gid,
        "has_setuid": has_setuid,
        "has_setgid": has_setgid,
        "has_sticky": has_sticky,
        "is_world_writable": bool(mode & stat.S_IWOTH),
        "is_group_writable": bool(mode & stat.S_IWGRP)
    }
```

### Cross-Platform Considerations

**Unix/Linux/macOS**:
- Setuid/setgid bits are native filesystem features
- Use `stat.S_ISUID` (0o4000) and `stat.S_ISGID` (0o2000) constants
- Python interpreters ignore setuid/setgid on scripts for security

**Windows**:
- No direct equivalent to setuid/setgid
- Check `st_file_attributes` instead (e.g., `FILE_ATTRIBUTE_SYSTEM`)
- Rely on NTFS ACLs for permission control

### Security Concerns

1. **Privilege Escalation**: Setuid scripts running as root could be exploited
2. **Race Conditions**: TOCTOU (Time-of-Check-Time-of-Use) between validation and execution
3. **Kernel Vulnerabilities**: Historical exploits in setuid script handling

### Why Python Ignores Setuid/Setgid on Scripts

From security research:
> "setuid only works on binaries, so unfortunately bash and python scripts can't leverage setuid. This is not supported in all operating systems as the use of an interpreter introduces a security vulnerability."

The kernel doesn't honor setuid/setgid on scripts interpreted by `/usr/bin/python3` because:
- Race condition between reading shebang and executing interpreter
- Interpreter itself would need setuid, creating massive attack surface

### Alternatives Considered

1. **`os.access()`**: REJECTED - Checks current user's access, not file's setuid status
2. **`pathlib.Path.stat().st_mode`**: VIABLE - Equivalent to `os.stat()`
3. **Subprocess with `--help` flag**: REJECTED - Still executes code (import-time side effects)
4. **Ignoring permission checks**: REJECTED - Violates security best practices

### Security Score: 8/10

**Deductions**:
- -1: TOCTOU race condition (mitigated by quick validation-to-execution time)
- -1: Windows doesn't have equivalent checks (platform limitation)

---

## 4. Signal Handling and Exit Codes

### Decision: Map negative returncodes to signal names for diagnostics

### Rationale

1. **POSIX Standard**: Negative returncodes indicate signal termination on Unix systems
2. **Debugging Aid**: Signal names (SIGSEGV, SIGKILL) are more meaningful than -11, -9
3. **Error Reporting**: Users need to know if script was killed vs. crashed vs. timed out
4. **Cross-Platform**: Windows uses positive exit codes; Unix uses negative for signals

### Code Example: Signal Detection

```python
import subprocess
import signal
from enum import IntEnum

class ExitStatus(IntEnum):
    """Common exit status codes."""
    SUCCESS = 0
    GENERAL_ERROR = 1
    TIMEOUT = 124  # GNU timeout convention
    SIGNAL_BASE = 128  # 128 + signal_num (bash convention)

def analyze_exit_code(returncode: int) -> dict:
    """
    Analyze subprocess exit code and detect signal termination.

    Args:
        returncode: The returncode from subprocess.run()

    Returns:
        dict with analysis results
    """
    if returncode is None:
        return {
            "status": "running",
            "signal": None,
            "description": "Process still running (should not happen with run())"
        }

    if returncode == 0:
        return {
            "status": "success",
            "signal": None,
            "description": "Process exited successfully"
        }

    if returncode > 0:
        # Positive exit code = normal exit with error
        # Bash convention: 128 + N means killed by signal N
        if returncode > 128:
            potential_signal = returncode - 128
            try:
                sig = signal.Signals(potential_signal)
                return {
                    "status": "killed_by_signal_maybe",
                    "signal": sig.name,
                    "signal_number": potential_signal,
                    "description": f"Possibly killed by {sig.name} (bash convention: 128+{potential_signal})"
                }
            except ValueError:
                pass

        return {
            "status": "error",
            "signal": None,
            "description": f"Process exited with error code {returncode}"
        }

    # Negative exit code = killed by signal (POSIX)
    signal_num = -returncode

    try:
        sig = signal.Signals(signal_num)
        signal_name = sig.name
    except ValueError:
        signal_name = f"UNKNOWN_SIGNAL_{signal_num}"

    # Categorize common signals
    if signal_num == signal.SIGSEGV:
        description = "Segmentation fault (invalid memory access)"
    elif signal_num == signal.SIGKILL:
        description = "Killed by SIGKILL (forceful termination)"
    elif signal_num == signal.SIGTERM:
        description = "Terminated by SIGTERM (graceful shutdown request)"
    elif signal_num == signal.SIGINT:
        description = "Interrupted by SIGINT (Ctrl+C)"
    elif signal_num == signal.SIGABRT:
        description = "Aborted by SIGABRT (assertion failure or abort())"
    elif signal_num == signal.SIGFPE:
        description = "Floating point exception (division by zero, etc.)"
    elif signal_num == signal.SIGILL:
        description = "Illegal instruction (corrupted binary or wrong architecture)"
    else:
        description = f"Killed by signal {signal_name}"

    return {
        "status": "killed_by_signal",
        "signal": signal_name,
        "signal_number": signal_num,
        "description": description,
        "can_be_caught": signal_num not in (signal.SIGKILL, signal.SIGSTOP)
    }

# Example usage
result = subprocess.run(["/usr/bin/python3", "crash.py"], capture_output=True)
analysis = analyze_exit_code(result.returncode)

# Example outputs:
# returncode = -11 -> {"signal": "SIGSEGV", "description": "Segmentation fault"}
# returncode = -9  -> {"signal": "SIGKILL", "description": "Killed by SIGKILL"}
# returncode = 1   -> {"status": "error", "description": "Process exited with error code 1"}
# returncode = 139 -> {"signal": "SIGSEGV", "description": "Possibly killed by SIGSEGV (128+11)"}
```

### Common Signal Mappings

| Signal | Number | Returncode | Description | Catchable |
|--------|--------|------------|-------------|-----------|
| SIGHUP | 1 | -1 | Hangup (terminal closed) | Yes |
| SIGINT | 2 | -2 | Interrupt (Ctrl+C) | Yes |
| SIGQUIT | 3 | -3 | Quit (Ctrl+\\) | Yes |
| SIGILL | 4 | -4 | Illegal instruction | No (hardware) |
| SIGTRAP | 5 | -5 | Trace/breakpoint trap | Yes |
| SIGABRT | 6 | -6 | Abort signal (abort()) | Yes |
| SIGFPE | 8 | -8 | Floating point exception | No (hardware) |
| SIGKILL | 9 | -9 | Kill (cannot be caught) | **No** |
| SIGSEGV | 11 | -11 | Segmentation fault | No (hardware) |
| SIGPIPE | 13 | -13 | Broken pipe | Yes |
| SIGALRM | 14 | -14 | Alarm clock (timer) | Yes |
| SIGTERM | 15 | -15 | Termination signal | Yes |
| SIGSTOP | 19 | -19 | Stop (cannot be caught) | **No** |

**Key Insight**: SIGKILL (-9) and SIGSTOP (-19) cannot be caught or ignored.

### Cross-Platform Differences

**Unix/Linux/macOS**:
- Negative returncodes for signals
- Standard signal numbers defined in `signal` module
- POSIX-compliant behavior

**Windows**:
- No negative returncodes
- Different signal semantics (limited to SIGABRT, SIGFPE, SIGILL, SIGINT, SIGSEGV, SIGTERM, SIGBREAK)
- Process termination uses exit codes instead

### Security Concerns

1. **Timing Attacks**: Measuring execution time via signals could leak information
2. **Resource Exhaustion**: Rapid signal generation could bypass rate limits
3. **Denial of Service**: SIGSEGV crashes might indicate exploitable bugs

### Alternatives Considered

1. **Only check for timeout**: REJECTED - Misses important crash diagnostics
2. **Use `signal.signal()` to catch signals**: REJECTED - Doesn't work for child processes
3. **Parse stderr for "Segmentation fault"**: FRAGILE - Locale-dependent, unreliable

### Security Score: 9/10

**Deductions**:
- -1: Platform-specific behavior requires conditional logic

---

## 5. Output Capture with Size Limits

### Decision: Stream output with incremental size checks and truncation

### Rationale

1. **Memory Safety**: Unlimited output capture can exhaust RAM (DoS attack)
2. **Disk Safety**: Writing unbounded output to disk can fill filesystems
3. **User Experience**: Users need to see partial output even when truncated
4. **Performance**: Streaming avoids buffering large datasets in memory

### Code Example: Size-Limited Output Capture

```python
import subprocess
import threading
from io import StringIO
from pathlib import Path

class OutputLimitExceeded(Exception):
    """Raised when output exceeds size limit."""
    pass

class SizeLimitedCapture:
    """
    Capture subprocess output with size limits and truncation.

    Features:
    - Separate limits for stdout and stderr
    - Real-time streaming without full buffering
    - Truncation markers when limits exceeded
    - Thread-safe operation
    """

    def __init__(self, max_stdout_bytes: int = 1_000_000, max_stderr_bytes: int = 100_000):
        """
        Initialize capture with size limits.

        Args:
            max_stdout_bytes: Maximum stdout size (default: 1MB)
            max_stderr_bytes: Maximum stderr size (default: 100KB)
        """
        self.max_stdout = max_stdout_bytes
        self.max_stderr = max_stderr_bytes
        self.stdout_buffer = StringIO()
        self.stderr_buffer = StringIO()
        self.stdout_bytes = 0
        self.stderr_bytes = 0
        self.stdout_truncated = False
        self.stderr_truncated = False
        self._lock = threading.Lock()

    def capture_stream(self, stream, buffer, max_bytes, attr_name):
        """
        Capture a stream with size limit.

        Args:
            stream: File-like object to read from
            buffer: StringIO buffer to write to
            max_bytes: Maximum bytes to capture
            attr_name: Attribute name for byte counter ('stdout_bytes' or 'stderr_bytes')
        """
        try:
            while True:
                # Read in chunks to avoid blocking on full lines
                chunk = stream.read(4096)  # 4KB chunks
                if not chunk:
                    break

                chunk_size = len(chunk.encode('utf-8', errors='replace'))

                with self._lock:
                    current_bytes = getattr(self, attr_name)

                    if current_bytes >= max_bytes:
                        # Already at limit, discard remaining output
                        if attr_name == 'stdout_bytes':
                            self.stdout_truncated = True
                        else:
                            self.stderr_truncated = True
                        continue

                    # Check if this chunk would exceed limit
                    if current_bytes + chunk_size > max_bytes:
                        # Write partial chunk
                        remaining = max_bytes - current_bytes
                        partial_chunk = chunk[:remaining]
                        buffer.write(partial_chunk)
                        setattr(self, attr_name, max_bytes)

                        # Mark as truncated
                        if attr_name == 'stdout_bytes':
                            self.stdout_truncated = True
                            buffer.write("\n[... OUTPUT TRUNCATED: exceeded 1MB limit ...]")
                        else:
                            self.stderr_truncated = True
                            buffer.write("\n[... STDERR TRUNCATED: exceeded 100KB limit ...]")
                        break

                    # Write full chunk
                    buffer.write(chunk)
                    setattr(self, attr_name, current_bytes + chunk_size)

        finally:
            stream.close()

    def get_results(self) -> dict:
        """Get captured output and truncation status."""
        return {
            "stdout": self.stdout_buffer.getvalue(),
            "stderr": self.stderr_buffer.getvalue(),
            "stdout_bytes": self.stdout_bytes,
            "stderr_bytes": self.stderr_bytes,
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated
        }

def execute_with_size_limits(script_path: Path, timeout: int = 30) -> dict:
    """
    Execute script with output size limits.

    Args:
        script_path: Path to the script
        timeout: Execution timeout in seconds

    Returns:
        dict with execution results
    """
    capture = SizeLimitedCapture(max_stdout_bytes=1_000_000, max_stderr_bytes=100_000)

    # Use Popen for streaming
    process = subprocess.Popen(
        ["/usr/bin/python3", str(script_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line buffered
        shell=False
    )

    # Create threads to capture stdout and stderr concurrently
    stdout_thread = threading.Thread(
        target=capture.capture_stream,
        args=(process.stdout, capture.stdout_buffer, capture.max_stdout, 'stdout_bytes')
    )
    stderr_thread = threading.Thread(
        target=capture.capture_stream,
        args=(process.stderr, capture.stderr_buffer, capture.max_stderr, 'stderr_bytes')
    )

    stdout_thread.start()
    stderr_thread.start()

    # Wait for process with timeout
    try:
        returncode = process.wait(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        process.kill()
        returncode = None
        timed_out = True

    # Wait for capture threads to finish
    stdout_thread.join(timeout=5)
    stderr_thread.join(timeout=5)

    results = capture.get_results()
    results.update({
        "returncode": returncode,
        "timed_out": timed_out
    })

    return results
```

### Memory-Efficient Streaming Alternative

For very large outputs, write directly to temporary files:

```python
import tempfile

def execute_with_file_capture(script_path: Path, timeout: int = 30) -> dict:
    """
    Execute script with output captured to temporary files.

    More memory-efficient for very large outputs.
    """
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='_stdout.txt') as stdout_file, \
         tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='_stderr.txt') as stderr_file:

        try:
            result = subprocess.run(
                ["/usr/bin/python3", str(script_path)],
                stdout=stdout_file,
                stderr=stderr_file,
                timeout=timeout,
                shell=False
            )

            # Read files with size limit
            stdout_file.seek(0)
            stdout = stdout_file.read(1_000_000)  # Read first 1MB

            stderr_file.seek(0)
            stderr = stderr_file.read(100_000)  # Read first 100KB

            return {
                "returncode": result.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "stdout_file": stdout_file.name,
                "stderr_file": stderr_file.name
            }

        except subprocess.TimeoutExpired:
            return {
                "returncode": None,
                "timed_out": True,
                "stdout_file": stdout_file.name,
                "stderr_file": stderr_file.name
            }
```

### Buffering Considerations

**Problem**: Command-line tools buffer output when not connected to a terminal (TTY).

**Solution**: For Python subprocesses, use `python -u` flag to force unbuffered mode:

```python
subprocess.run(
    ["/usr/bin/python3", "-u", str(script_path)],  # -u = unbuffered
    capture_output=True
)
```

**Why This Matters**:
- Without `-u`, output may be held in 4KB-8KB buffers
- Buffered output isn't visible in real-time
- If process is killed, buffered output is lost

### Security Concerns

1. **Denial of Service**: Infinite output loops exhaust memory/disk
2. **Information Leakage**: Large error outputs might expose sensitive data
3. **Race Conditions**: Concurrent writes to shared buffers need locking
4. **Temp File Cleanup**: Failed cleanup leaks data to disk

### Alternatives Considered

1. **`communicate()` without limits**: REJECTED - Vulnerable to memory exhaustion
2. **`select.select()` for non-blocking reads**: VIABLE but complex, Unix-only
3. **Third-party libraries (e.g., `sh`)**: REJECTED - Adds dependency
4. **Line-by-line truncation**: FRAGILE - Doesn't handle binary output well

### Security Score: 8.5/10

**Deductions**:
- -1: Threading complexity introduces potential race conditions (mitigated with locks)
- -0.5: Temp file approach requires careful cleanup

---

## 6. Additional Security Recommendations

### 6.1 Input Validation with `shlex`

**When to use**: If you MUST use `shell=True` (rare cases like shell pipelines)

```python
import shlex

# ONLY use shlex.quote() when shell=True is unavoidable
user_filename = "file with spaces.txt"
safe_filename = shlex.quote(user_filename)

# Still dangerous, but less so
subprocess.run(f"cat {safe_filename}", shell=True)

# BETTER: Avoid shell entirely
subprocess.run(["cat", user_filename], shell=False)
```

**Limitations of shlex.quote()**:
- Only escapes shell metacharacters, not command-specific arguments
- Windows support is limited and unreliable
- Doesn't validate argument semantics (e.g., prevents `-rf` being interpreted as flag)

### 6.2 Avoid `preexec_fn` (Deprecated)

**Problem**: `preexec_fn` is not thread-safe and deprecated in subinterpreters.

```python
# INSECURE: preexec_fn in multi-threaded application
subprocess.Popen(
    ["script.py"],
    preexec_fn=lambda: os.setuid(1000)  # DEADLOCK RISK!
)
```

**Alternatives**:
- Use `env` parameter to modify environment (instead of `os.environ`)
- Use `start_new_session=True` (instead of `os.setsid()`)
- Use `process_group` parameter (instead of `os.setpgid()`)

### 6.3 Timeout Enforcement Best Practices

```python
# GOOD: Built-in timeout with cleanup
try:
    result = subprocess.run(["script.py"], timeout=30)
except subprocess.TimeoutExpired:
    # Process was killed automatically
    logging.warning("Script timed out after 30s")
```

**Why timeouts matter**:
- Prevents infinite loops from consuming CPU
- Limits impact of fork bombs (`os.fork()` loops)
- Enforces SLA for skill execution

### 6.4 Environment Variable Sanitization

```python
# INSECURE: Passing untrusted environment variables
env = os.environ.copy()
env['USER_INPUT'] = user_value  # Could contain malicious data

# SECURE: Explicit allowlist
safe_env = {
    'PATH': '/usr/bin:/bin',
    'PYTHONPATH': '/opt/skillkit/libs',
    'HOME': '/tmp/sandbox'
}
subprocess.run(["script.py"], env=safe_env)
```

### 6.5 Resource Limits (ulimit on Unix)

```python
import resource

def set_resource_limits():
    """Set resource limits for subprocess (Unix only)."""
    # Max 100MB memory
    resource.setrlimit(resource.RLIMIT_AS, (100_000_000, 100_000_000))

    # Max 10 seconds CPU time
    resource.setrlimit(resource.RLIMIT_CPU, (10, 10))

    # Max 10 child processes
    resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))

# Apply limits in subprocess (preexec_fn alternative for Python 3.12+)
subprocess.Popen(
    ["script.py"],
    preexec_fn=set_resource_limits  # Use with caution (thread-safety issues)
)
```

**Better alternative (Python 3.12+)**:
```python
# Python 3.12+ supports passing resource limits directly
subprocess.Popen(
    ["script.py"],
    pipesize=1024  # Limit pipe buffer size
)
```

---

## 7. Comprehensive Security Checklist

### Pre-Execution Validation
- [ ] Validate script path using `os.path.realpath()` + `os.path.commonpath()`
- [ ] Check for symlinks (reject or resolve based on policy)
- [ ] Verify file exists and is a regular file (not directory, socket, etc.)
- [ ] Check for setuid/setgid bits (Unix-only)
- [ ] Validate file extension matches expected type (`.py`)
- [ ] Enforce maximum file size limit (e.g., 10MB)

### Execution Configuration
- [ ] Use `subprocess.run()` with explicit arguments list
- [ ] Set `shell=False` (or omit, as it's the default)
- [ ] Specify absolute path to interpreter (`/usr/bin/python3`)
- [ ] Set reasonable `timeout` (e.g., 30-300 seconds)
- [ ] Use `capture_output=True` or separate `stdout`/`stderr` pipes
- [ ] Set `text=True` for UTF-8 decoding (or handle bytes explicitly)
- [ ] Use `check=False` to handle non-zero exits gracefully

### Output Handling
- [ ] Implement size limits for stdout/stderr (e.g., 1MB/100KB)
- [ ] Use threading or async I/O for concurrent stream capture
- [ ] Detect and report truncation to users
- [ ] Sanitize output before logging (remove sensitive data patterns)
- [ ] Use temporary files for very large outputs

### Error Handling
- [ ] Catch `subprocess.TimeoutExpired` and report timeout
- [ ] Map negative returncodes to signal names
- [ ] Detect crashes (SIGSEGV, SIGABRT) and log for investigation
- [ ] Provide actionable error messages to users
- [ ] Log security-relevant events (path traversal attempts, permission errors)

### Post-Execution Cleanup
- [ ] Close file handles explicitly
- [ ] Delete temporary files
- [ ] Clear sensitive data from memory
- [ ] Log execution metadata (duration, exit code, truncation)

---

## 8. References and Further Reading

### Official Documentation
- **Python subprocess module**: https://docs.python.org/3/library/subprocess.html
- **Python signal module**: https://docs.python.org/3/library/signal.html
- **Python os.stat() and stat module**: https://docs.python.org/3/library/stat.html
- **Python pathlib**: https://docs.python.org/3/library/pathlib.html

### Security Advisories
- **CVE-2024-23334** (aiohttp path traversal): https://security.snyk.io/vuln/SNYK-PYTHON-AIOHTTP-6209406
- **OWASP Command Injection**: https://owasp.org/www-community/attacks/Command_Injection
- **Snyk Command Injection Guide**: https://snyk.io/blog/command-injection-python-prevention-examples/

### Best Practices
- **Secure Coding Practices - Python Subprocess**: https://securecodingpractices.com/prevent-command-injection-python-subprocess/
- **Semgrep Python Command Injection**: https://semgrep.dev/docs/cheat-sheets/python-command-injection
- **OpenStack Path Traversal Prevention**: https://security.openstack.org/guidelines/dg_using-file-paths.html

### Research Articles
- **Path Traversal in 2024**: https://www.aikido.dev/blog/path-traversal-in-2024-the-year-unpacked
- **Python Security Gotchas**: https://medium.com/hackernoon/10-common-security-gotchas-in-python-and-how-to-avoid-them-e19fbe265e03

### Community Resources
- **Stack Overflow - Python Subprocess Security**: https://stackoverflow.com/questions/21009416/python-subprocess-security
- **Stack Overflow - Path Traversal Prevention**: https://stackoverflow.com/questions/45188708/how-to-prevent-directory-traversal-attack-from-python-code

---

## 9. Conclusion

### Final Recommendations for skillkit v0.3

1. **Use `subprocess.run()`** with `shell=False` and list-based arguments
2. **Implement comprehensive path validation** using `os.path.realpath()` + `os.path.commonpath()`
3. **Reject scripts with setuid/setgid bits** on Unix systems
4. **Enforce 30-second timeout** with `TimeoutExpired` handling
5. **Limit output to 1MB stdout / 100KB stderr** using streaming capture
6. **Map negative returncodes to signal names** for better error reporting
7. **Log security events** (path traversal attempts, permission errors, crashes)

### Security Posture

**Overall Security Score**: 9/10

The recommended approach provides defense-in-depth:
- **Input validation** prevents path traversal and symlink attacks
- **Execution isolation** prevents command injection via shell=False
- **Resource limits** prevent DoS via timeouts and output caps
- **Error detection** identifies crashes and malicious activity
- **Cross-platform support** handles Unix and Windows differences

**Remaining Risks** (acceptable for v0.3 MVP):
- TOCTOU race condition between validation and execution (mitigated by fast execution)
- Platform-specific behaviors require conditional logic
- Resource exhaustion via CPU-intensive scripts (addressed in future with cgroups/containers)

This research provides a solid foundation for implementing secure script execution in skillkit v0.3.
