# Cross-Platform Script Execution Implementation Guide

**Date**: 2025-01-18
**Purpose**: Practical guide for implementing cross-platform script execution in skillkit v0.3.0
**Audience**: Developers implementing the feature
**Status**: Ready for implementation

---

## Quick Reference: The 5 Core Patterns

### Pattern 1: Resolve Interpreter

```python
import shutil
import platform
from pathlib import Path

def resolve_interpreter(script_path: Path) -> str:
    """Find interpreter for script (cross-platform)."""
    extension = script_path.suffix.lower()

    # 1. Extension → base name
    extension_map = {'.py': 'python3', '.sh': 'bash', '.js': 'node'}
    base = extension_map.get(extension)
    if not base:
        raise ValueError(f"Unknown extension: {extension}")

    # 2. Platform variants
    if base == 'python3':
        variants = ['py', 'python', 'python3'] if platform.system() == 'Windows' \
                   else ['python3', 'python']
    elif base == 'bash':
        variants = ['bash', 'bash.exe'] if platform.system() == 'Windows' \
                   else ['bash', 'sh']
    else:
        variants = [base]

    # 3. Find in PATH
    for variant in variants:
        path = shutil.which(variant)
        if path:
            return path

    raise FileNotFoundError(f"Interpreter '{base}' not found")
```

### Pattern 2: Execute Script

```python
import subprocess
import json

def execute_script(script_path: Path, arguments: dict, interpreter: str) -> subprocess.CompletedProcess:
    """Execute script with JSON arguments (cross-platform)."""
    return subprocess.run(
        [interpreter, str(script_path)],
        input=json.dumps(arguments),
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
        timeout=30,
        cwd=str(script_path.parent),
        shell=False  # CRITICAL
    )
```

### Pattern 3: Inject Environment Variables

```python
import os

def prepare_environment(skill_name: str, skill_base_dir: Path) -> dict[str, str]:
    """Inject skill context into environment (cross-platform)."""
    env = os.environ.copy()  # Inherit PATH, HOME, etc.
    env['SKILL_NAME'] = skill_name
    env['SKILL_BASE_DIR'] = str(skill_base_dir.resolve())
    env['SKILLKIT_VERSION'] = '0.3.0'
    return env

# Use in subprocess
result = subprocess.run([...], env=prepare_environment(...), shell=False)
```

### Pattern 4: Handle Output

```python
def process_output(result: subprocess.CompletedProcess) -> dict:
    """Process stdout/stderr with truncation (cross-platform)."""
    max_size = 10 * 1024 * 1024  # 10MB

    def truncate(text: str) -> tuple[str, bool]:
        if len(text) <= max_size:
            return text, False
        return text[:max_size] + "\n[... truncated ...]", True

    stdout, stdout_trunc = truncate(result.stdout)
    stderr, stderr_trunc = truncate(result.stderr)

    return {
        'stdout': stdout,
        'stderr': stderr,
        'exit_code': result.returncode,
        'truncated': stdout_trunc or stderr_trunc
    }
```

### Pattern 5: Handle Errors

```python
import signal

def interpret_exit_code(exit_code: int) -> dict:
    """Interpret exit code and detect signals (cross-platform)."""
    if exit_code == 0:
        return {'status': 'success'}

    if exit_code < 0:  # Unix signals (Windows won't hit this)
        try:
            sig = signal.Signals(-exit_code)
            return {'status': 'signal', 'signal': sig.name}
        except ValueError:
            return {'status': 'signal', 'signal': f'UNKNOWN({-exit_code})'}

    return {'status': 'error', 'code': exit_code}
```

---

## Implementation Checklist

### Phase 1: Core Components (Days 1-2)

- [ ] Create `src/skillkit/core/script_executor.py`
  - [ ] `ScriptExecutor` class with `execute()` method
  - [ ] `resolve_interpreter()` function (extension + variants + PATH lookup)
  - [ ] `prepare_environment()` function
  - [ ] `truncate_output()` helper
  - [ ] Exception hierarchy: `InterpreterNotFoundError`, `ScriptSecurityError`

- [ ] Create `src/skillkit/core/script_detector.py`
  - [ ] `ScriptDetector` class with `detect()` method
  - [ ] Script scanning (recursive, up to 5 levels)
  - [ ] Extension mapping
  - [ ] Comment extraction (docstring parser)
  - [ ] `ScriptMetadata` dataclass

- [ ] Update `src/skillkit/core/models.py`
  - [ ] Add `ScriptMetadata` dataclass
  - [ ] Add `ScriptExecutionResult` dataclass

### Phase 2: Integration (Days 3-4)

- [ ] Update `src/skillkit/core/manager.py`
  - [ ] Add `execute_skill_script()` method
  - [ ] Integrate with FilePathResolver for validation
  - [ ] Add tool restriction check (require "Bash" in allowed-tools)
  - [ ] Add audit logging

- [ ] Update `src/skillkit/integrations/langchain.py`
  - [ ] Extend `LangChainSkillAdapter` to create script tools
  - [ ] Generate tool names: `{skill}.{script}` (e.g., "pdf.extract")
  - [ ] Add async script invocation

- [ ] Update `src/skillkit/core/exceptions.py`
  - [ ] Add script execution exceptions

### Phase 3: Testing (Days 5-6)

- [ ] Create `tests/test_script_executor.py` (40+ cases)
- [ ] Create `tests/test_script_detector.py` (20+ cases)
- [ ] Create test fixtures in `tests/fixtures/skills/`
- [ ] Add integration tests
- [ ] Platform-specific tests (Windows, Linux, macOS)
- [ ] Verify 80%+ test coverage

### Phase 4: Documentation (Day 7)

- [ ] Add examples in `examples/script_execution.py`
- [ ] Update README.md with script execution docs
- [ ] Add docstrings to all public APIs
- [ ] Create platform-specific troubleshooting guide

---

## File Structure After Implementation

```
src/skillkit/
├── core/
│   ├── script_executor.py        ← NEW
│   ├── script_detector.py         ← NEW
│   ├── models.py                  (updated)
│   ├── manager.py                 (updated)
│   ├── exceptions.py              (updated)
│   └── ...existing files...
├── integrations/
│   └── langchain.py               (updated)
└── ...existing files...

tests/
├── test_script_executor.py        ← NEW
├── test_script_detector.py        ← NEW
├── test_manager.py                (updated)
├── test_langchain.py              (updated)
├── fixtures/
│   └── skills/
│       ├── script-skill/          ← NEW
│       │   ├── SKILL.md
│       │   └── scripts/
│       │       ├── echo.py
│       │       ├── slow.py
│       │       └── error.py
│       └── ...existing...
└── ...existing files...

examples/
├── script_execution.py            ← NEW
└── ...existing...
```

---

## Detailed Implementation Steps

### Step 1: Create ScriptExecutor (1.5 days)

**File**: `src/skillkit/core/script_executor.py` (400-500 lines)

```python
from dataclasses import dataclass
from pathlib import Path
import subprocess, json, os, platform, shutil, time
from typing import Optional

@dataclass
class ScriptExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: float
    script_path: Path
    signal: Optional[str] = None
    stdout_truncated: bool = False
    stderr_truncated: bool = False


class ScriptExecutor:
    """Execute scripts with cross-platform security."""

    INTERPRETER_MAP = {
        '.py': 'python3', '.sh': 'bash', '.js': 'node',
        '.rb': 'ruby', '.pl': 'perl', '.bat': 'cmd'
    }

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def execute(
        self,
        script_path: Path,
        skill_base_dir: Path,
        skill_name: str,
        arguments: dict,
        skill_version: Optional[str] = None
    ) -> ScriptExecutionResult:
        """Execute script with full validation and error handling."""
        # Implement the 5 patterns above
```

**Key methods**:
- `execute()` - Main entry point
- `_resolve_interpreter()` - Interpreter discovery
- `_validate_path()` - Path security
- `_prepare_environment()` - Environment injection
- `_truncate_output()` - Output handling
- `_get_interpreter_variants()` - Platform variants

### Step 2: Create ScriptDetector (1 day)

**File**: `src/skillkit/core/script_detector.py` (300-400 lines)

```python
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import re

@dataclass
class ScriptMetadata:
    name: str
    path: Path
    script_type: str
    description: str


class ScriptDetector:
    """Detect and parse script metadata."""

    EXTENSIONS = {'.py', '.sh', '.js', '.rb', '.pl', '.bat'}

    def detect(self, skill_base_dir: Path) -> list[ScriptMetadata]:
        """Scan skill directory and detect scripts."""
        # Scan scripts/ and root directory
        # Extract metadata from each script
        # Return list of ScriptMetadata

    def _extract_description(self, script_path: Path) -> str:
        """Extract first comment block (docstring)."""
        # Read first 50 lines
        # Look for #, //, """ patterns
        # Extract and truncate at 500 chars
```

### Step 3: Update SkillManager (1 day)

**File**: `src/skillkit/core/manager.py` (additions ~150 lines)

```python
class SkillManager:
    """Extend with script execution."""

    def execute_skill_script(
        self,
        skill_name: str,
        script_name: str,
        arguments: dict
    ) -> ScriptExecutionResult:
        """Execute a skill's script."""
        # 1. Load skill
        # 2. Find script in detected scripts
        # 3. Check tool restrictions (require "Bash")
        # 4. Execute with ScriptExecutor
        # 5. Log for auditing
        # 6. Return result

    def _detect_skill_scripts(self, skill: Skill) -> list[ScriptMetadata]:
        """Lazy script detection on first use."""
        # Run once per skill
        # Cache in skill object
```

### Step 4: Update LangChain Integration (1 day)

**File**: `src/skillkit/integrations/langchain.py` (additions ~200 lines)

```python
def get_langchain_tools(skill: Skill) -> list:
    """Create tools for skill (prompt + scripts)."""
    tools = []

    # Add prompt tool (existing code)
    if skill.prompt:
        tools.append(...)

    # Add script tools (NEW)
    for script in skill.scripts:
        tool = create_script_tool(skill, script)
        tools.append(tool)

    return tools


def create_script_tool(skill: Skill, script: ScriptMetadata):
    """Create StructuredTool for one script."""
    # Tool name: "{skill}.{script_name}" (e.g., "pdf.extract")
    # Tool description: From script's docstring
    # Tool input: Free-form JSON schema
    # Tool function: Call script_executor.execute()
```

### Step 5: Testing (2 days)

**Key test files**:

```python
# tests/test_script_executor.py
- test_execute_python_script
- test_execute_shell_script
- test_interpreter_resolution_windows
- test_interpreter_resolution_unix
- test_output_truncation_10mb
- test_signal_handling_unix
- test_timeout_enforcement
- test_environment_injection
- test_json_serialization
- test_path_security_traversal
- test_concurrent_executions
- ... (40+ cases)

# tests/test_script_detector.py
- test_detect_scripts_in_scripts_dir
- test_detect_scripts_in_root
- test_extract_python_docstring
- test_extract_shell_comment
- test_nested_scripts_5_levels
- ... (20+ cases)
```

---

## Platform-Specific Testing

### Windows Testing

```python
@pytest.mark.skipif(platform.system() != 'Windows', reason='Windows only')
def test_python_on_windows():
    """Test python3 resolution on Windows."""
    # Ensure 'py' launcher is tried first
    # Verify fallback to 'python' works

@pytest.mark.skipif(platform.system() != 'Windows', reason='Windows only')
def test_batch_script_windows():
    """Test .bat script execution."""
    # Verify cmd /c is used
    # Ensure shell=False is maintained

@pytest.mark.skipif(platform.system() != 'Windows', reason='Windows only')
def test_unc_path_windows():
    """Test \\server\share paths work."""
```

### Linux/macOS Testing

```python
@pytest.mark.skipif(platform.system() not in ['Linux', 'Darwin'], reason='Unix only')
def test_signal_handling_unix():
    """Test SIGSEGV, SIGKILL detection."""
    # Ensure negative exit codes map to signal names

@pytest.mark.skipif(platform.system() not in ['Linux', 'Darwin'], reason='Unix only')
def test_bash_script_unix():
    """Test .sh script execution."""
    # Verify bash interpreter resolution
```

---

## Common Pitfalls to Avoid

### ❌ DON'T Do This

```python
# ❌ Never use shell=True
subprocess.run(f"python3 {script_path}", shell=True)

# ❌ Never manually parse PATH
for dir in os.environ['PATH'].split(os.pathsep):
    ...

# ❌ Never modify os.environ globally
os.environ['SKILL_NAME'] = name
subprocess.run([...])  # Pollutes parent process

# ❌ Never ignore encoding errors
result = subprocess.run([...], text=True)
# Non-UTF-8 output crashes!

# ❌ Never assume PATH lookup at runtime
subprocess.run(["python3", ...])  # Might not find it

# ❌ Never trust exit code without checking for timeout
try:
    result = subprocess.run([...])
except subprocess.TimeoutExpired:
    handle_timeout()
```

### ✅ DO This Instead

```python
# ✅ Always use shell=False with list form
subprocess.run([interpreter_path, str(script_path)], shell=False)

# ✅ Use shutil.which() for PATH lookup
interpreter = shutil.which('python3')

# ✅ Inject environment via env= parameter
result = subprocess.run([...], env=prepare_environment(...))

# ✅ Handle encoding gracefully
result = subprocess.run(
    [...],
    text=True,
    encoding='utf-8',
    errors='replace'
)

# ✅ Use absolute interpreter path
interpreter = shutil.which('python3')  # Returns absolute path
subprocess.run([interpreter, str(script_path)])

# ✅ Always catch TimeoutExpired
try:
    result = subprocess.run([...], timeout=30)
except subprocess.TimeoutExpired:
    handle_timeout()
```

---

## Debugging Guide

### Issue: "Interpreter not found"

```python
# Debug: Print what we're looking for
>>> from skillkit.core.script_executor import ScriptExecutor
>>> executor = ScriptExecutor()
>>> executor._get_interpreter_variants('python3')
['py', 'python', 'python3', 'python.exe']  # Windows example

>>> import shutil
>>> shutil.which('python3')
None  # Not found!

# Fix: Check system PATH
>>> import os
>>> print(os.environ['PATH'])
C:\Program Files\Python310\...  # Check if Python is in PATH

# Or use the Python launcher (Windows)
>>> shutil.which('py')
'C:\\Python310\\py.exe'
```

### Issue: "Script cannot access ./data/"

```python
# Problem: Working directory is wrong
# Check: What is cwd?
result = subprocess.run(
    [interpreter, script_path],
    cwd=???  # Should be skill_base_dir, not script_path.parent
)

# Fix: Set cwd to skill root
result = subprocess.run(
    [interpreter, script_path],
    cwd=str(skill_base_dir)  # ← Skill root, not script dir
)
```

### Issue: "JSON parse error in script"

```python
# Problem: Arguments can't be serialized
arguments = {"large_object": some_huge_dict}

# Debug: Check serialization
>>> import json
>>> json.dumps(arguments)
TypeError: Object of type X is not JSON serializable

# Fix: Ensure arguments are JSON-serializable
# Convert to dict/list/string/number/bool/null
arguments = {"field": str(large_object)}
```

### Issue: Line endings are wrong

```python
# Problem: Script gets \r\n instead of \n
# Check: Are you using text=True?
result = subprocess.run(
    [...],
    text=True  # ← This is CRITICAL
)

# With text=True, Python automatically converts \r\n → \n
# Without it, you get raw bytes with mixed line endings
```

---

## Performance Targets

| Metric | Target | How to Verify |
|--------|--------|---------------|
| Script execution overhead | <50ms (95% of executions) | pytest benchmark on sample scripts |
| Script detection | <10ms per 50 scripts | Time `ScriptDetector.detect()` |
| Interpreter resolution | <5ms per lookup | Time `shutil.which()` calls |
| Environment injection | <1ms | Overhead of env dict creation |
| Output truncation | <10ms for 10MB output | Time truncate function with large string |

**How to benchmark**:

```python
import time

# Script execution
start = time.time()
for i in range(100):
    executor.execute(...)
elapsed = (time.time() - start) * 1000 / 100
print(f"Avg execution overhead: {elapsed:.1f}ms")
assert elapsed < 50, "Too slow!"

# Script detection
start = time.time()
detector.detect(skill_dir)
elapsed = (time.time() - start) * 1000
print(f"Detection time: {elapsed:.1f}ms")
assert elapsed < 10, "Too slow!"
```

---

## Documentation to Generate

### For README.md

```markdown
## Script Execution

Skills can bundle executable scripts for deterministic operations:

```yaml
# SKILL.md
name: pdf-extractor
scripts:
  - extract.py    # Extracts text from PDF
  - convert.sh    # Converts PDF to images
```

Scripts execute with JSON arguments via stdin:

```python
# Python
import json, sys
args = json.load(sys.stdin)
print(json.dumps({"result": args["file"]}))
```

Tools are automatically created per script:
- `pdf-extractor.extract`
- `pdf-extractor.convert`
```

### For Docstrings

```python
def execute_skill_script(
    self,
    skill_name: str,
    script_name: str,
    arguments: dict
) -> ScriptExecutionResult:
    """
    Execute a skill's script.

    Args:
        skill_name: Name of skill (e.g., "pdf-extractor")
        script_name: Name of script without extension (e.g., "extract")
        arguments: Free-form dict passed to script via JSON stdin

    Returns:
        ScriptExecutionResult with stdout, stderr, exit_code, etc.

    Raises:
        InterpreterNotFoundError: If script's interpreter not in PATH
        PathSecurityError: If script path traversal detected
        ToolRestrictionError: If "Bash" not in skill's allowed-tools
        TimeoutError: If script exceeds timeout

    Example:
        >>> manager = SkillManager()
        >>> result = manager.execute_skill_script(
        ...     "pdf-extractor",
        ...     "extract",
        ...     {"file_path": "/path/to/doc.pdf"}
        ... )
        >>> print(result.stdout)  # JSON output from script
    """
```

---

## Success Criteria

After implementation, verify:

- [ ] All 5 core patterns are implemented and working
- [ ] 80%+ test coverage achieved
- [ ] All 6 user stories pass acceptance tests (from spec.md)
- [ ] Cross-platform testing on Windows, macOS, Linux
- [ ] Performance targets met (<50ms overhead, <10ms detection)
- [ ] Security checklist completed (no shell=True, path validation, etc.)
- [ ] Documentation complete (README, docstrings, examples)
- [ ] Examples work end-to-end with LangChain
- [ ] Error messages are clear and actionable
- [ ] Backward compatibility with v0.1/v0.2 maintained

---

**Ready to Start**: Yes
**Estimated Duration**: 7 days
**Blockers**: None
**Dependencies**: Existing skillkit v0.2.0 + Python 3.10+

---

Next Step: Begin with `script_executor.py` implementation following Pattern 1-5 above.
