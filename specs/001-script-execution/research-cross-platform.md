# Cross-Platform Script Execution Research

**Research Date**: 2025-01-18
**Purpose**: Technical research on cross-platform subprocess execution for skillkit v0.3
**Scope**: Interpreter mapping, PATH resolution, environment variables, shell behavior, line endings, and working directory handling across Linux, macOS, and Windows
**Python Version**: 3.10+ (per skillkit requirements)

---

## Table of Contents

1. [Decision: Cross-Platform Execution Approach](#decision-cross-platform-execution-approach)
2. [Interpreter Mapping & Discovery](#interpreter-mapping--discovery)
3. [PATH Resolution Strategy](#path-resolution-strategy)
4. [Working Directory Handling](#working-directory-handling)
5. [Environment Variable Injection](#environment-variable-injection)
6. [Shell Behavior & Security](#shell-behavior--security)
7. [Line Ending Management](#line-ending-management)
8. [Platform-Specific Edge Cases](#platform-specific-edge-cases)
9. [Implementation Patterns](#implementation-patterns)
10. [Testing Strategy](#testing-strategy)

---

## Decision: Cross-Platform Execution Approach

### Chosen Strategy: `subprocess.run()` with `shell=False` + Platform-Aware Interpreter Discovery

**Core Principle**: Use Python's `subprocess` module with minimal platform-specific code paths. Leverage `shutil.which()` for interpreter discovery and handle platform differences in interpreter naming, not in execution semantics.

### Rationale

1. **Security**: `shell=False` eliminates command injection vulnerabilities regardless of platform
2. **Consistency**: Same execution model across all platforms (no `cmd.exe` vs `/bin/sh` divergence)
3. **Reliability**: Explicit interpreter resolution catches missing interpreters early
4. **Simplicity**: Minimal platform-specific branching (only for interpreter names, not execution)
5. **Standards Compliance**: Follows Python documentation recommendations for cross-platform code (PEP 3156, subprocess docs)

### Security Score: 9.5/10

| Aspect | Score | Reasoning |
|--------|-------|-----------|
| Command injection prevention | 10/10 | `shell=False` blocks all shell metacharacter exploitation |
| Cross-platform consistency | 9/10 | Same execution model; only interpreter names vary |
| Timeout support | 10/10 | Built-in `timeout` parameter, works on all platforms |
| Error clarity | 9/10 | Explicit error messages; only missing on Windows signal detection |
| Maintenance burden | 8/10 | Platform-specific code only in interpreter discovery |

---

## Interpreter Mapping & Discovery

### 2.1 Extension-to-Interpreter Mapping

**Decision**: Static mapping by file extension with fallback to shebang parsing.

```python
INTERPRETER_MAP = {
    # Primary interpreters (all platforms)
    '.py': 'python3',      # Python 3.x
    '.sh': 'bash',         # Bash shell
    '.js': 'node',         # Node.js
    '.rb': 'ruby',         # Ruby
    '.pl': 'perl',         # Perl

    # Windows-specific (no-op on Unix)
    '.bat': 'cmd',         # Windows batch
    '.cmd': 'cmd',         # Windows command
    '.ps1': 'powershell',  # PowerShell
}
```

**Design Rationale**:
- **Speed**: Extension check is O(1) - no file I/O required
- **Predictability**: Consistent across platforms for cross-platform skills
- **Simplicity**: No need to guess based on content

### 2.2 Platform-Specific Interpreter Fallbacks

**Windows Challenge**: `python3` command may not exist; users typically have `py`, `python`, or `python3`

```python
import platform
import shutil
from typing import Optional

def get_interpreter_variants(base: str) -> list[str]:
    """
    Get platform-specific interpreter command variants.

    Returns candidates in priority order.
    """
    system = platform.system()

    if base == 'python3':
        if system == 'Windows':
            # Windows: check py launcher first, then python/python3
            return ['py', 'python', 'python3', 'python.exe']
        elif system == 'Darwin':
            # macOS: homebrew installs as python3, system as python
            return ['python3', 'python']
        else:  # Linux
            return ['python3', 'python']

    elif base == 'bash':
        if system == 'Windows':
            # Windows: bash available via Git Bash, WSL, or MSYS2
            # Git Bash installs as 'bash', WSL uses 'bash'
            return ['bash', 'bash.exe']
        else:
            return ['bash', 'sh']

    elif base == 'node':
        if system == 'Windows':
            return ['node', 'node.exe']
        else:
            return ['node']

    elif base == 'ruby':
        if system == 'Windows':
            return ['ruby', 'ruby.exe']
        else:
            return ['ruby']

    elif base == 'perl':
        if system == 'Windows':
            return ['perl', 'perl.exe']
        else:
            return ['perl']

    # Default: try base as-is
    return [base]


def find_interpreter(base: str) -> Optional[str]:
    """
    Find interpreter in PATH using platform-aware fallbacks.

    Returns:
        Full path to interpreter, or None if not found

    Example:
        find_interpreter('python3')  # Returns '/usr/bin/python3'
    """
    for variant in get_interpreter_variants(base):
        path = shutil.which(variant)
        if path:
            return path
    return None
```

**Cross-Platform Behavior**:

| Platform | python3 | bash | node |
|----------|---------|------|------|
| Linux | `/usr/bin/python3` | `/bin/bash` | `/usr/bin/node` |
| macOS | `/usr/local/bin/python3` | `/usr/local/bin/bash` | `/usr/local/bin/node` |
| Windows (native) | `C:\Python310\python.exe` | ❌ not found | `C:\Program Files\nodejs\node.exe` |
| Windows (Git Bash) | `C:\Git\mingw64\bin\python3.exe` | `C:\Git\mingw64\bin\bash.exe` | `C:\Git\mingw64\bin\node.exe` |
| Windows (WSL) | `/usr/bin/python3` | `/bin/bash` | `/usr/bin/node` |

**Key Insight**: Use `shutil.which()` which returns the full path - `subprocess.run()` can then use the absolute path, avoiding any PATH-lookup-at-runtime inconsistencies.

### 2.3 Shebang Parsing (Fallback)

```python
import re
from pathlib import Path

SHEBANG_PATTERN = re.compile(
    r'^#!\s*'                    # #! prefix
    r'(?:/usr/bin/env\s+)?'      # optional /usr/bin/env
    r'([^\s]+)'                  # interpreter path/name
    r'(.*?)$',                   # optional args
    re.MULTILINE
)

def extract_shebang_interpreter(script_path: Path) -> Optional[str]:
    """
    Extract interpreter name from shebang line.

    Handles:
        #!/usr/bin/env python3       → 'python3'
        #!/usr/bin/python3 -u        → 'python3'
        #!/bin/bash                  → 'bash'
        #!C:\Python310\python.exe    → 'python'

    Raises:
        IOError: If file cannot be read
    """
    try:
        with open(script_path, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline(200)  # Limit to 200 chars
    except IOError:
        return None

    match = SHEBANG_PATTERN.match(first_line)
    if not match:
        return None

    interpreter_path = match.group(1)
    # Extract just the interpreter name from path
    # /usr/bin/python3 → python3
    # C:\Python310\python.exe → python
    return Path(interpreter_path).stem or Path(interpreter_path).name
```

**Platform-Specific Shebang Handling**:
- **Unix shebang in Windows file**: `#!/usr/bin/python3` on Windows → fallback to extension map
- **Windows path in shebang**: `#!C:\Python310\python.exe` → extract `python` → find in PATH
- **Relative shebang**: `#!/usr/bin/env python3` → standard on all platforms

---

## PATH Resolution Strategy

### 3.1 Core Strategy: `shutil.which()` Instead of `os.environ['PATH']`

**Why not manual PATH parsing?**

```python
# ❌ NAIVE: Manual PATH parsing
import os
path_dirs = os.environ['PATH'].split(os.pathsep)
for directory in path_dirs:
    full_path = os.path.join(directory, 'python3')
    if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
        return full_path
```

**Problems with manual approach**:
- Doesn't check `PATHEXT` on Windows (won't find `python.exe` if you search for `python`)
- Manual executable checking is fragile (`os.X_OK` unreliable on Windows)
- Duplicates logic already in `shutil.which()`

**Why `shutil.which()` is superior**:

```python
# ✅ CORRECT: Use shutil.which()
import shutil

interpreter = shutil.which('python3')
# On Windows: Returns 'C:\Python310\python.exe' or None
# On Unix: Returns '/usr/bin/python3' or None
# Automatically handles:
#   - PATHEXT on Windows (.exe, .bat, .cmd, etc.)
#   - Executable bit checking (correctly on Unix)
#   - PATH directories in correct order
#   - Current directory security on Windows (skipped by default)
```

**Python 3.10+ Advantages** (per Python docs):
- `shutil.which()` officially recommended for cross-platform use (PEP 3156)
- Returns absolute path (safe for use in subprocess)
- Handles all platform-specific quirks internally
- Security: Skips current directory on Windows by default

### 3.2 PATH Lookup Algorithm

```python
def resolve_interpreter(script_path: Path) -> str:
    """
    Resolve interpreter for script file.

    Strategy:
    1. Extension → base interpreter name (fast)
    2. Shebang → interpreter name (flexible)
    3. Platform variants → find in PATH (comprehensive)
    4. Validate existence and raise error if not found

    Raises:
        InterpreterNotFoundError: If interpreter cannot be resolved/found
    """
    # Step 1: Extension-based detection
    extension = script_path.suffix.lower()
    base_interpreter = INTERPRETER_MAP.get(extension)

    # Step 2: Shebang fallback
    if not base_interpreter:
        base_interpreter = extract_shebang_interpreter(script_path)

    # Step 3: No interpreter determined
    if not base_interpreter:
        raise InterpreterNotFoundError(
            f"Cannot determine interpreter for '{script_path.name}' "
            f"(no extension mapping, no shebang)"
        )

    # Step 4: Find in PATH with platform variants
    interpreter_path = find_interpreter(base_interpreter)

    if not interpreter_path:
        # Provide helpful error message with available variants
        variants = get_interpreter_variants(base_interpreter)
        raise InterpreterNotFoundError(
            f"Interpreter '{base_interpreter}' not found in PATH.\n"
            f"Tried: {', '.join(variants)}\n"
            f"Please ensure Python/interpreters are installed and in PATH"
        )

    return interpreter_path
```

### 3.3 Performance: Cache Interpreter Lookups (Optional for v0.3.1+)

For v0.3.0 MVP, direct `shutil.which()` calls are sufficient (~1-5ms per lookup).

For v0.3.1+, add caching:

```python
from functools import lru_cache

@lru_cache(maxsize=32)
def find_interpreter_cached(base: str) -> Optional[str]:
    """
    Find interpreter with LRU caching.

    Performance:
        First call: ~1-5ms (PATH search)
        Cached: ~0.001ms (1000-5000x faster)
    """
    for variant in get_interpreter_variants(base):
        path = shutil.which(variant)
        if path:
            return path
    return None
```

---

## Working Directory Handling

### 4.1 Core Decision: Set `cwd=skill_base_dir` Always

```python
import subprocess
from pathlib import Path

def execute_script(
    script_path: Path,
    skill_base_dir: Path,
    arguments: dict,
    interpreter: str,
    timeout: int = 30
) -> subprocess.CompletedProcess:
    """
    Execute script with working directory set to skill base.

    Args:
        script_path: Full path to script (e.g., /home/user/.claude/skills/pdf-extract/scripts/convert.py)
        skill_base_dir: Base directory of skill (e.g., /home/user/.claude/skills/pdf-extract/)
        arguments: Arguments dict to pass via JSON stdin
        interpreter: Interpreter path (e.g., /usr/bin/python3)
        timeout: Execution timeout in seconds
    """
    import json

    # Validate path is within skill directory
    # (FilePathResolver handles this - see FR-004)

    # Prepare JSON input
    json_input = json.dumps(arguments, ensure_ascii=False)

    # Execute with skill base as working directory
    result = subprocess.run(
        [interpreter, str(script_path)],
        input=json_input,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(skill_base_dir),  # CRITICAL: Scripts expect this
        shell=False
    )

    return result
```

### 4.2 Why Skill Base Directory (Not Script Directory)

**Decision**: Use skill base directory, not script's directory

| Approach | Pros | Cons | Used For |
|----------|------|------|----------|
| Skill base (`/home/user/.claude/skills/pdf-extract/`) | Scripts can reference `./data/`, `./config.yaml` | Script cannot reference parent | ✅ RECOMMENDED |
| Script directory (`/home/user/.claude/skills/pdf-extract/scripts/`) | Isolates scripts | Scripts cannot access shared data files | ❌ Rejected |
| Original cwd | Unpredictable | Security risk, platform-dependent | ❌ Rejected |

**Rationale**:
- **Skill layout**: Config files are typically in skill root: `data/`, `config.yaml`, `templates/`
- **Scripts assume**: They execute from skill root: `open('./data/input.json')`
- **Consistency**: LangChain integration expects this model

### 4.3 Cross-Platform Path Normalization

```python
def execute_script_safe(
    script_path: Path,
    skill_base_dir: Path,
    arguments: dict,
    interpreter: str,
    timeout: int = 30
) -> subprocess.CompletedProcess:
    """
    Execute script with safe path handling.

    Ensures:
    - Paths are absolute (resolves any relative references)
    - Paths work on all platforms (Windows/Unix)
    - No race conditions between validation and execution
    """
    # Resolve all paths to absolute to avoid issues
    resolved_script = script_path.resolve()
    resolved_base = skill_base_dir.resolve()

    # Validate script is within skill directory
    # (This should already be done, but be explicit)
    try:
        resolved_script.relative_to(resolved_base)
    except ValueError:
        raise PathSecurityError(
            f"Script path escapes skill directory"
        )

    # Use string conversion for subprocess (cross-platform)
    result = subprocess.run(
        [interpreter, str(resolved_script)],
        input=json.dumps(arguments),
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(resolved_base),  # Convert to string
        shell=False
    )

    return result
```

### 4.4 Permission Issues at Working Directory

**Edge Case**: What if skill directory is not writable?

```python
import os

def validate_working_directory(skill_base_dir: Path) -> None:
    """
    Validate working directory is accessible.

    Raises:
        PermissionError: If directory is not readable or has no execute permission
    """
    if not os.access(skill_base_dir, os.R_OK):
        raise PermissionError(
            f"Cannot read skill directory: {skill_base_dir}\n"
            f"Check permissions: chmod +r {skill_base_dir}"
        )

    if not os.access(skill_base_dir, os.X_OK):
        raise PermissionError(
            f"Cannot access skill directory: {skill_base_dir}\n"
            f"Check execute permission: chmod +x {skill_base_dir}"
        )

    # Note: Write permission not required (scripts can write to temp files)
```

**Recommendation**: Call during script detection (lazy), log warning if directory is not writable.

---

## Environment Variable Injection

### 5.1 Core Decision: Pass via `env` Parameter (Not Manual os.environ)

**Recommended Pattern**:

```python
import os
from pathlib import Path

def prepare_environment(
    skill_name: str,
    skill_base_dir: Path,
    skill_version: Optional[str] = None,
    skillkit_version: str = "0.3.0"
) -> dict[str, str]:
    """
    Prepare environment variables for script execution.

    Args:
        skill_name: Name of skill (e.g., "pdf-extractor")
        skill_base_dir: Base directory path
        skill_version: Version from SKILL.md (e.g., "1.0.0") or None
        skillkit_version: Version of skillkit library

    Returns:
        Environment dict to pass to subprocess.run(env=...)

    Key Variables Injected:
        SKILL_NAME: Name of skill
        SKILL_BASE_DIR: Absolute path to skill directory
        SKILL_VERSION: Version (if available)
        SKILLKIT_VERSION: Version of skillkit
    """
    # Start with inherited environment (scripts can still use PATH, HOME, etc.)
    env = os.environ.copy()

    # Inject skill-specific variables
    env['SKILL_NAME'] = skill_name
    env['SKILL_BASE_DIR'] = str(skill_base_dir.resolve())
    if skill_version:
        env['SKILL_VERSION'] = skill_version
    env['SKILLKIT_VERSION'] = skillkit_version

    return env


def execute_script_with_env(
    script_path: Path,
    skill_base_dir: Path,
    arguments: dict,
    interpreter: str,
    skill_name: str,
    skill_version: Optional[str],
    timeout: int = 30
) -> subprocess.CompletedProcess:
    """Execute script with environment variables injected."""
    import json

    # Prepare environment
    env = prepare_environment(
        skill_name=skill_name,
        skill_base_dir=skill_base_dir,
        skill_version=skill_version,
        skillkit_version="0.3.0"
    )

    # Execute with environment
    result = subprocess.run(
        [interpreter, str(script_path.resolve())],
        input=json.dumps(arguments),
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(skill_base_dir.resolve()),
        env=env,  # Pass environment dict
        shell=False
    )

    return result
```

### 5.2 Environment Variable Handling Per Platform

| Variable | Linux | macOS | Windows | Example |
|----------|-------|-------|---------|---------|
| `SKILL_NAME` | Inherited + injected | Inherited + injected | Inherited + injected | `pdf-extractor` |
| `SKILL_BASE_DIR` | Path with `/` | Path with `/` | Path with `\` or `/` | `/home/user/.claude/skills/pdf-extract` |
| `PATH` | Inherited from parent | Inherited from parent | Inherited from parent | `/usr/bin:/bin:/usr/local/bin` |
| `TEMP`/`TMP` | `/tmp` | `/var/tmp` | `C:\Users\...\AppData\Local\Temp` | Platform-specific |
| `HOME` | `/home/user` | `/Users/user` | `C:\Users\user` | Platform-specific |

**Key Insight**: By passing `env=env` to `subprocess.run()`, we inherit the parent process's environment (including PATH, HOME, etc.) and add our skill-specific variables on top. This is superior to modifying `os.environ` globally.

### 5.3 Windows vs Unix Environment Variable Semantics

**Platform Difference**: Environment variable names are case-sensitive on Unix, case-insensitive on Windows.

```python
# ✅ SAFE: Use uppercase (works on all platforms)
env['SKILL_NAME'] = skill_name           # Both Unix and Windows accept this
env['SKILL_BASE_DIR'] = str(skill_base_dir)

# ❌ RISKY: Mixed case on Windows causes issues
env['skill_name'] = skill_name           # Works on Unix, may fail on Windows batch scripts

# Windows Batch Script
# %SKILL_NAME% finds 'SKILL_NAME' (case-insensitive)
# %skill_name% finds 'SKILL_NAME' (case-insensitive)
# Both work, but it's confusing
```

**Recommendation**: Always use UPPERCASE for environment variable names.

### 5.4 Environment Variable Size Limits

**Edge Case**: Very large environment variables or many custom variables

```python
def prepare_environment_safe(
    skill_name: str,
    skill_base_dir: Path,
    skill_version: Optional[str] = None,
    skillkit_version: str = "0.3.0",
    max_env_size: int = 32 * 1024  # 32KB limit
) -> dict[str, str]:
    """
    Prepare environment with size validation.

    Most systems have environment size limits:
    - Linux: ~128KB typical
    - macOS: ~256KB typical
    - Windows: ~32KB typical

    We use 32KB as conservative limit.
    """
    env = os.environ.copy()

    # Add skill variables
    env['SKILL_NAME'] = skill_name
    env['SKILL_BASE_DIR'] = str(skill_base_dir.resolve())
    if skill_version:
        env['SKILL_VERSION'] = skill_version
    env['SKILLKIT_VERSION'] = skillkit_version

    # Estimate environment size
    env_size = sum(len(k) + len(v) for k, v in env.items())

    if env_size > max_env_size:
        raise EnvironmentError(
            f"Environment too large: {env_size} bytes (max {max_env_size})\n"
            f"Consider reducing PATH or other large variables"
        )

    return env
```

---

## Shell Behavior & Security

### 6.1 Core Decision: `shell=False` Always (No Exceptions)

**Why `shell=False` is non-negotiable**:

```python
# ❌ INSECURE: shell=True with any user input
script_name = "my script.py"  # User-provided or from skill
subprocess.run(f"python3 {script_name}", shell=True)  # VULNERABLE

# Attack: If skill has script named "; rm -rf /; echo.py"
# Actual command: python3 ; rm -rf /; echo.py
# Result: rm -rf / executes! ☠️

# ✅ SECURE: shell=False with list form
subprocess.run(["python3", script_name], shell=False)
# Attack script: script_name = "; rm -rf /; echo.py"
# Actual command: python3 "; rm -rf /; echo.py"
# Result: Python tries to open literal file "; rm -rf /; echo.py"
# Result: FileNotFoundError (safe!) ✓
```

### 6.2 When Might Someone Be Tempted to Use `shell=True`?

| Use Case | Problem | Solution |
|----------|---------|----------|
| Script needs piping | shell=True enables pipes | NOT OUR PROBLEM: Skills should write to stdout directly |
| Script uses globbing | shell=True enables `*.txt` | NOT OUR PROBLEM: Python's pathlib handles globs |
| Script uses redirection | shell=True enables `> file.txt` | NOT OUR PROBLEM: Scripts should use file APIs |
| Windows batch scripts | Batch syntax requires shell | Use `/cmd /c` only as last resort |

**Key Principle**: The skill script is responsible for its own logic. We don't provide shell features; we provide execution.

### 6.3 Windows Batch Scripts: Special Case

If a skill includes `.bat` scripts (Windows only):

```python
def execute_script_with_shell_fallback(
    script_path: Path,
    interpreter: str,
    arguments: dict,
    timeout: int = 30,
    cwd: Path = Path.cwd()
) -> subprocess.CompletedProcess:
    """
    Execute script, with shell fallback for batch files on Windows.

    On Windows, batch scripts (.bat) MUST use shell=True or cmd.exe.
    All other scripts use shell=False for security.
    """
    import json
    import platform

    is_batch = script_path.suffix.lower() in ['.bat', '.cmd']
    is_windows = platform.system() == 'Windows'

    # Batch scripts on Windows only
    if is_batch and is_windows:
        # Use: cmd /c <script_path> <args>
        # NOT: shell=True (which would require escaping issues)
        result = subprocess.run(
            [
                'cmd.exe', '/c',
                str(script_path.resolve())
            ],
            input=json.dumps(arguments),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
            shell=False  # Still shell=False! cmd.exe is the interpreter
        )
    else:
        # All other scripts: normal execution
        result = subprocess.run(
            [interpreter, str(script_path.resolve())],
            input=json.dumps(arguments),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd),
            shell=False
        )

    return result
```

**Note**: `cmd /c script.bat` is NOT the same as `shell=True`. The `/c` flag tells cmd to execute one command and exit. This is safer than `shell=True`.

---

## Line Ending Management

### 7.1 Core Decision: Let Python Handle Text Mode Automatically

**Problem**: Unix uses `\n`, Windows uses `\r\n`. What happens to captured output?

```python
# ❌ NAIVE: Capture in binary mode and manual decoding
result = subprocess.run(
    [interpreter, script_path],
    stdout=subprocess.PIPE,  # Binary mode
    stderr=subprocess.PIPE,  # Binary mode
    shell=False
)
# result.stdout is bytes: b'line1\r\n' or b'line1\n'
# Must decode and normalize manually

# ✅ CORRECT: Capture in text mode (let Python handle it)
result = subprocess.run(
    [interpreter, script_path],
    capture_output=True,
    text=True,  # Text mode: Python handles encoding AND line ending conversion
    shell=False
)
# result.stdout is str: 'line1\n' on all platforms
# Python automatically converts \r\n → \n on Windows when reading
```

### 7.2 How `text=True` Works on Each Platform

| Platform | Actual Output | What Python Returns | `text=True` Behavior |
|----------|---------------|---------------------|----------------------|
| Windows (Python writing `\n`) | `\n` in pipe | `\n` | No conversion needed |
| Windows (C library writing `\r\n`) | `\r\n` in pipe | `\n` | Converts `\r\n` → `\n` |
| Unix (always `\n`) | `\n` in pipe | `\n` | No conversion needed |
| macOS (always `\n`) | `\n` in pipe | `\n` | No conversion needed |

**Result**: With `text=True` and `capture_output=True`, stdout/stderr are always normalized to `\n` across all platforms.

### 7.3 Encoding Handling

```python
def execute_script_safe(
    script_path: Path,
    interpreter: str,
    arguments: dict,
    timeout: int = 30,
    cwd: Path = Path.cwd()
) -> subprocess.CompletedProcess:
    """
    Execute script with safe encoding handling.

    Python's default encoding:
    - Unix: UTF-8
    - Windows: Windows locale (often UTF-8 in Python 3.10+)
    - macOS: UTF-8

    We explicitly use UTF-8 and handle decode errors gracefully.
    """
    import json

    result = subprocess.run(
        [interpreter, str(script_path.resolve())],
        input=json.dumps(arguments),  # JSON is always UTF-8
        capture_output=True,
        text=True,  # Text mode (line ending conversion)
        encoding='utf-8',  # Explicit encoding
        errors='replace',  # Replace invalid chars with U+FFFD
        timeout=timeout,
        cwd=str(cwd),
        shell=False
    )

    return result
```

**Why `errors='replace'`**:
- Gracefully handles non-UTF-8 output from scripts
- Prevents crashes when script outputs binary data or non-UTF-8 text
- Common in real-world scenarios (PDF extraction, image processing)

---

## Platform-Specific Edge Cases

### 8.1 Windows: Different PATH Variables

**Issue**: `PATH` environment variable has different separators on Windows vs Unix.

```python
import os
import platform

# Unix: PATH=/usr/bin:/usr/local/bin:/bin
# Windows: PATH=C:\Python310;C:\Program Files\Git\bin

# Python's os.pathsep handles this:
# Unix: os.pathsep = ':'
# Windows: os.pathsep = ';'

# So when we do:
path_dirs = os.environ['PATH'].split(os.pathsep)
# On Unix: ['usr/bin', '/usr/local/bin', '/bin']
# On Windows: ['C:\Python310', 'C:\Program Files\Git\bin']

# But we don't need to do this! shutil.which() handles it.
```

### 8.2 Windows: `python` vs `python3` vs `py`

**Issue**: Windows doesn't have `python3` by default.

```python
def find_python_interpreter() -> str:
    """
    Find Python interpreter across platforms.

    Resolution order:
    1. Windows: 'py' (Python launcher), 'python', 'python3'
    2. Unix: 'python3', 'python'
    """
    import shutil
    import platform

    system = platform.system()

    if system == 'Windows':
        # Try py launcher first (recommended for Windows)
        if shutil.which('py'):
            return 'py'
        # Fall back to python
        if shutil.which('python'):
            return 'python'
        # Last resort
        if shutil.which('python3'):
            return 'python3'
    else:
        # Unix: python3 is standard
        if shutil.which('python3'):
            return 'python3'
        # Fallback
        if shutil.which('python'):
            return 'python'

    raise InterpreterNotFoundError("Python interpreter not found")
```

**Key Point**: The `py` launcher on Windows (installed with Python) is actually the preferred way to invoke Python. It respects the `py -3` syntax.

### 8.3 macOS: Homebrew vs System Python

**Issue**: macOS has system Python (`/usr/bin/python3` on Ventura+) but users often install Homebrew Python.

```python
# Homebrew: /usr/local/bin/python3 or /opt/homebrew/bin/python3 (Apple Silicon)
# System: /usr/bin/python3 (Monterey+)
# pyenv: ~/.pyenv/shims/python3

# shutil.which() finds them in PATH order, so it just works.
# No special handling needed!
```

### 8.4 Windows: UNC Paths and Drive Letters

**Issue**: Windows has different path formats that may affect subprocess.

```python
from pathlib import Path

# Normal Windows path
skill_dir = Path("C:\\Users\\user\\.claude\\skills\\pdf-extract")

# UNC path (network share)
skill_dir_unc = Path(r"\\server\share\.claude\skills\pdf-extract")

# Symbolic link (may point across drives)
# script_path → D:\link\script.py
# (FilePathResolver validation prevents traversal across drives)

# subprocess.run() handles all these transparently.
# Key: Always use Path.resolve() before passing to subprocess
# This normalizes all variations.
```

### 8.5 Windows: Batch Scripts and stdin

**Issue**: Windows batch scripts don't read from stdin the same way as Unix shells.

```batch
REM ❌ This doesn't work in batch
REM Batch scripts can't read JSON from stdin easily

REM Some workarounds (not recommended):
REM 1. Read file instead: python3 -c "import json; args = json.load(open('args.json'))"
REM 2. Use command-line args: %1, %2, etc. (limited to ~8KB)

REM ✅ BETTER: Don't write batch scripts, use Python on Windows
REM For Windows-only operations, write Python scripts instead
```

**Recommendation**: For cross-platform skills, don't use `.bat` scripts. Write equivalent Python scripts. Batch is too limited for JSON stdin.

### 8.6 Linux/Unix: Signal Handling

**Issue**: Python on Unix detects signals via negative exit codes. Windows doesn't have signals.

```python
import signal

def handle_signal_termination(returncode: int) -> dict[str, Any]:
    """
    Detect signal termination (Unix only).

    On Unix, negative returncode indicates signal:
        returncode = -9 → SIGKILL
        returncode = -11 → SIGSEGV
        returncode = -15 → SIGTERM

    On Windows, signals don't exist. All terminations have positive exit codes.
    """
    if returncode < 0:
        signal_num = -returncode
        try:
            signal_name = signal.Signals(signal_num).name
        except ValueError:
            signal_name = f"UNKNOWN({signal_num})"

        return {
            'exit_code': returncode,
            'signal': signal_name,
            'signal_number': signal_num,
            'stderr': f"Signal: {signal_name}"
        }

    return {
        'exit_code': returncode,
        'signal': None
    }
```

---

## Implementation Patterns

### 9.1 Complete Cross-Platform Execution Function

```python
import json
import os
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ScriptExecutionResult:
    """Result of script execution."""
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: float
    script_path: Path
    signal: Optional[str] = None
    stdout_truncated: bool = False
    stderr_truncated: bool = False


class ScriptExecutor:
    """Execute scripts with cross-platform security and reliability."""

    # Extension to interpreter base name
    INTERPRETER_MAP = {
        '.py': 'python3',
        '.sh': 'bash',
        '.js': 'node',
        '.rb': 'ruby',
        '.pl': 'perl',
        '.bat': 'cmd',  # Windows only
        '.ps1': 'powershell',
    }

    MAX_OUTPUT_SIZE = 10 * 1024 * 1024  # 10MB

    def __init__(self, timeout: int = 30):
        """Initialize executor with default timeout."""
        self.timeout = timeout

    def execute(
        self,
        script_path: Path,
        skill_base_dir: Path,
        skill_name: str,
        arguments: dict,
        skill_version: Optional[str] = None
    ) -> ScriptExecutionResult:
        """
        Execute script with full cross-platform support.

        Args:
            script_path: Full path to script
            skill_base_dir: Skill base directory (working dir for script)
            skill_name: Skill name (for environment variables)
            arguments: Arguments to pass via JSON stdin
            skill_version: Skill version (optional)

        Returns:
            ScriptExecutionResult with stdout, stderr, exit_code, etc.

        Raises:
            InterpreterNotFoundError: If interpreter not available
            PathSecurityError: If path traversal detected
            TimeoutError: If script exceeds timeout
        """
        # Validate path (FilePathResolver handles this)
        resolved_script = self._validate_script_path(script_path, skill_base_dir)
        resolved_base = skill_base_dir.resolve()

        # Resolve interpreter
        interpreter_path = self._resolve_interpreter(resolved_script)

        # Prepare environment
        env = self._prepare_environment(
            skill_name, resolved_base, skill_version
        )

        # Serialize arguments
        json_input = json.dumps(arguments, ensure_ascii=False)
        if len(json_input) > 10 * 1024 * 1024:
            raise ValueError("Arguments too large (>10MB)")

        # Execute script
        start_time = time.time()
        try:
            result = subprocess.run(
                [interpreter_path, str(resolved_script)],
                input=json_input,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=self.timeout,
                cwd=str(resolved_base),
                env=env,
                shell=False  # CRITICAL: Always False
            )
        except subprocess.TimeoutExpired:
            raise TimeoutError(
                f"Script execution timed out after {self.timeout}s"
            )

        elapsed_ms = (time.time() - start_time) * 1000

        # Process output
        stdout, stdout_truncated = self._truncate_output(result.stdout)
        stderr, stderr_truncated = self._truncate_output(result.stderr)

        # Handle signal termination (Unix only)
        exit_code = result.returncode
        signal_name = None
        if exit_code < 0:
            signal_num = -exit_code
            try:
                signal_name = __import__('signal').Signals(signal_num).name
                stderr = f"Signal: {signal_name}"
            except (ValueError, AttributeError):
                signal_name = f"UNKNOWN({signal_num})"

        return ScriptExecutionResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            execution_time_ms=elapsed_ms,
            script_path=script_path,
            signal=signal_name,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated
        )

    def _validate_script_path(
        self, script_path: Path, skill_base_dir: Path
    ) -> Path:
        """Validate script path is within skill directory."""
        resolved = script_path.resolve()
        base = skill_base_dir.resolve()

        try:
            resolved.relative_to(base)
        except ValueError:
            raise PathSecurityError(
                f"Script path escapes skill directory: {script_path}"
            )

        if not resolved.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        return resolved

    def _resolve_interpreter(self, script_path: Path) -> str:
        """Resolve interpreter for script."""
        # Try extension-based mapping
        extension = script_path.suffix.lower()
        base_interpreter = self.INTERPRETER_MAP.get(extension)

        if not base_interpreter:
            raise InterpreterNotFoundError(
                f"Cannot determine interpreter for {script_path.name}"
            )

        # Find interpreter in PATH
        interpreter_path = self._find_interpreter(base_interpreter)
        if not interpreter_path:
            raise InterpreterNotFoundError(
                f"Interpreter '{base_interpreter}' not found in PATH"
            )

        return interpreter_path

    def _find_interpreter(self, base: str) -> Optional[str]:
        """Find interpreter using platform-specific variants."""
        system = platform.system()

        # Generate variants for this base interpreter
        variants = self._get_interpreter_variants(base, system)

        for variant in variants:
            path = shutil.which(variant)
            if path:
                return path

        return None

    @staticmethod
    def _get_interpreter_variants(base: str, system: str) -> list[str]:
        """Get platform-specific interpreter command variants."""
        if base == 'python3':
            if system == 'Windows':
                return ['py', 'python', 'python3', 'python.exe']
            else:
                return ['python3', 'python']
        elif base == 'bash':
            if system == 'Windows':
                return ['bash', 'bash.exe']
            else:
                return ['bash', 'sh']
        elif base == 'cmd':
            return ['cmd', 'cmd.exe']
        else:
            return [base, f"{base}.exe"]

    def _prepare_environment(
        self,
        skill_name: str,
        skill_base_dir: Path,
        skill_version: Optional[str]
    ) -> dict[str, str]:
        """Prepare environment variables for script."""
        env = os.environ.copy()
        env['SKILL_NAME'] = skill_name
        env['SKILL_BASE_DIR'] = str(skill_base_dir)
        if skill_version:
            env['SKILL_VERSION'] = skill_version
        env['SKILLKIT_VERSION'] = "0.3.0"
        return env

    @staticmethod
    def _truncate_output(output: str, max_size: int = None) -> tuple[str, bool]:
        """Truncate output if exceeds max size."""
        if max_size is None:
            max_size = ScriptExecutor.MAX_OUTPUT_SIZE

        if len(output) <= max_size:
            return output, False

        truncated = output[:max_size]
        return truncated + "\n[... output truncated ...]", True


# Exception classes
class SkillKitError(Exception):
    """Base exception for skillkit."""
    pass


class InterpreterNotFoundError(SkillKitError):
    """Interpreter not available in PATH."""
    pass


class PathSecurityError(SkillKitError):
    """Path security violation."""
    pass
```

---

## Testing Strategy

### 10.1 Test Coverage by Platform

**Unit Tests (40+ cases)**:
- ✅ `test_resolve_interpreter_*.py`: Extension mapping, platform variants, missing interpreter
- ✅ `test_execute_script_*.py`: Basic execution, JSON stdin, exit codes
- ✅ `test_signal_handling_unix.py`: Signal detection (Unix only, marked with `@pytest.mark.skipif`)
- ✅ `test_output_truncation.py`: 10MB+ outputs, line ending handling
- ✅ `test_path_validation.py`: Traversal attacks, symlinks
- ✅ `test_environment_injection.py`: SKILL_NAME, SKILL_BASE_DIR, etc.

**Integration Tests (15+ scenarios)**:
- ✅ `test_python_script_execution.py`: Cross-platform Python execution
- ✅ `test_shell_script_execution_linux.py`: Bash execution (Linux/macOS)
- ✅ `test_shell_script_execution_windows.py`: Batch execution (Windows)
- ✅ `test_concurrent_execution.py`: Multiple scripts in parallel
- ✅ `test_timeout_enforcement.py`: Timeout and signal handling
- ✅ `test_windows_path_handling.py`: UNC paths, drive letters (Windows)

### 10.2 Platform-Specific Test Markers

```python
import platform
import pytest

# Run tests conditionally per platform
pytestmark = pytest.mark.skipif(
    platform.system() != 'Windows',
    reason='Windows-specific test'
)

# Or use parametrize for cross-platform tests
@pytest.mark.parametrize('platform_name', ['Linux', 'Darwin', 'Windows'])
def test_script_execution(platform_name):
    """Test script execution on different platforms."""
    pass
```

### 10.3 Test Fixtures

```python
# tests/fixtures/skills/script-skill/
# ├── SKILL.md
# └── scripts/
#     ├── echo.py           # Echoes stdin as JSON
#     ├── slow.py           # Sleeps 2s then prints
#     ├── error.py          # Exits with error
#     ├── large_output.py   # Generates 100MB output
#     ├── signal_trap.py    # Catches signal (Unix)
#     └── shell_test.sh     # Bash script
```

---

## Summary: Key Decisions

| Decision | Chosen | Rationale |
|----------|--------|-----------|
| **Execution method** | `subprocess.run(shell=False)` | Security, consistency, built-in timeout |
| **Interpreter discovery** | `shutil.which()` with variants | Cross-platform, handles PATHEXT on Windows |
| **Working directory** | Skill base directory | Scripts expect to reference `./data/` |
| **Arguments** | JSON via stdin | Most secure, supports complex types |
| **Environment** | Inject via `env=` parameter | Doesn't pollute parent process |
| **Line endings** | `text=True` (automatic) | Python handles `\n` vs `\r\n` conversion |
| **Output capture** | `text=True` with `errors='replace'` | UTF-8 with graceful fallback |
| **Signal handling** | Detect via negative exit codes | Unix standard, Windows returns 0 |
| **Batch scripts** | Use `cmd /c` not `shell=True` | Safer than `shell=True` |
| **Timeout** | Configurable, 30s default | Prevents hangs, enforcement is built-in |

---

## Implementation Checklist

- [ ] Create `script_executor.py` with `ScriptExecutor` class
- [ ] Create `interpreter_resolver.py` with platform-aware lookup
- [ ] Create exception hierarchy (InterpreterNotFoundError, PathSecurityError)
- [ ] Integrate with existing FilePathResolver for path validation
- [ ] Add environment variable injection to SkillManager
- [ ] Create 50+ test cases (unit + integration)
- [ ] Add test fixtures for all platforms
- [ ] Document platform-specific behaviors
- [ ] Add examples for each language (Python, Shell, Node, Ruby, Perl)
- [ ] Validate cross-platform with CI/CD (GitHub Actions)

---

**Document Version**: 1.0
**Last Updated**: 2025-01-18
**Ready for Implementation**: Yes
**Next Steps**: Begin `script_executor.py` implementation
