# Research: JSON Over Stdin for Script Arguments (2024-2025)

**Date**: 2025-11-18
**Context**: v0.3 Script Execution Feature
**Focus**: Best practices for passing complex arguments to subprocess scripts via JSON over stdin

---

## Executive Summary

**Recommended Approach**: Use `subprocess.communicate()` with JSON serialization for one-shot argument passing to scripts. This provides the safest, most straightforward pattern for passing complex data structures while avoiding deadlocks and security issues.

**Key Decision Points**:
- **For simple data exchange**: Use `communicate()` with single-line JSON
- **For large payloads (>10MB)**: Implement size limits and consider file-based alternatives
- **For streaming data**: Use JSONL (JSON Lines) format with line-based reading
- **For sensitive data**: Prefer stdin over command-line arguments (security)

---

## 1. JSON Serialization Strategies

### 1.1 Recommended Serialization Pattern

**Use `json.dumps()` with explicit parameters**:

```python
import json

# Parent process (skillkit)
def serialize_arguments(args: dict) -> str:
    """Serialize arguments to JSON string for subprocess stdin."""
    return json.dumps(
        args,
        ensure_ascii=False,  # Preserve Unicode characters
        separators=(',', ':'),  # Compact format (no spaces)
        sort_keys=False,  # Preserve insertion order (Python 3.7+)
    )
```

**Rationale**:
- `ensure_ascii=False`: Preserves Unicode/non-ASCII characters as UTF-8 (per RFC 7159)
- `separators=(',', ':')`: Minimizes payload size (removes whitespace)
- `sort_keys=False`: Maintains dictionary order (deterministic in Python 3.7+)
- Single-line output: Compatible with line-based reading patterns

### 1.2 Handling Non-JSON-Serializable Objects

**Problem**: Python objects like `datetime`, custom classes, and `bytes` are not JSON-serializable by default.

**Solution 1 - Custom Encoder** (Recommended):

```python
import json
from datetime import datetime, date
from typing import Any

class SkillKitJSONEncoder(json.JSONEncoder):
    """Custom encoder for skillkit argument types."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, bytes):
            return obj.decode('utf-8', errors='replace')
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return super().default(obj)

# Usage
json.dumps(args, cls=SkillKitJSONEncoder, ensure_ascii=False)
```

**Solution 2 - Pre-serialization Validation**:

```python
def validate_json_serializable(obj: Any, path: str = "$") -> None:
    """Recursively validate that object is JSON-serializable."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return
    elif isinstance(obj, dict):
        for k, v in obj.items():
            validate_json_serializable(v, f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            validate_json_serializable(v, f"{path}[{i}]")
    else:
        raise TypeError(
            f"Non-JSON-serializable object at {path}: "
            f"{type(obj).__name__}"
        )
```

### 1.3 Unicode and Special Character Handling

**Default Behavior**:
- Python's `json.dumps()` uses `ensure_ascii=True` by default
- All non-ASCII characters are escaped as `\uXXXX` sequences
- This is safe but increases payload size

**Best Practice for 2024-2025**:
- Use `ensure_ascii=False` for UTF-8 output (smaller, more readable)
- JSON spec (RFC 7159) requires UTF-8, UTF-16, or UTF-32
- UTF-8 is the recommended default for maximum interoperability
- Always specify `encoding='utf-8'` when opening files or pipes

**Example**:

```python
# Good: Preserves Unicode, smaller payload
data = {"message": "Hello 世界 🌍"}
json_str = json.dumps(data, ensure_ascii=False)
# Output: '{"message":"Hello 世界 🌍"}'

# Default: Escapes everything
json_str = json.dumps(data)
# Output: '{"message":"Hello \\u4e16\\u754c \\ud83c\\udf0d"}'
```

### 1.4 Size Limits and Streaming Considerations

**Memory Expansion Factor**:
- JSON in Python memory is **7-25x larger** than file size
- Example: 300MB JSON file → 2.8GB Python object
- Caused by Python object overhead (dict, list, str objects)

**Recommended Size Limits**:

```python
# Conservative limits based on 2024-2025 research
MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024  # 10MB JSON string
MAX_MEMORY_EXPANSION = 25  # Worst-case expansion factor
MAX_ESTIMATED_MEMORY = MAX_JSON_SIZE_BYTES * MAX_MEMORY_EXPANSION  # 250MB

def check_json_size(json_str: str) -> None:
    """Validate JSON size before sending to subprocess."""
    size_bytes = len(json_str.encode('utf-8'))
    if size_bytes > MAX_JSON_SIZE_BYTES:
        raise ValueError(
            f"JSON payload too large: {size_bytes / 1024 / 1024:.2f}MB "
            f"(max: {MAX_JSON_SIZE_BYTES / 1024 / 1024:.2f}MB)"
        )
```

**Streaming Alternative** (for large payloads):

If arguments exceed size limits, use **JSONL (JSON Lines)** format:

```python
# Parent: Write multiple JSON objects, one per line
for chunk in argument_chunks:
    proc.stdin.write(json.dumps(chunk) + '\n')

# Script: Read line-by-line
import sys
for line in sys.stdin:
    args = json.loads(line)
    process(args)
```

---

## 2. Stdin Communication Patterns

### 2.1 Recommended Pattern: `communicate()` for One-Shot Exchange

**Use Case**: Send arguments once, wait for script to complete (most common for skills)

**Parent Process** (skillkit):

```python
import subprocess
import json

def invoke_script(script_path: str, arguments: dict) -> dict:
    """Invoke script with JSON arguments via stdin."""

    # Serialize arguments
    json_input = json.dumps(arguments, ensure_ascii=False)

    # Run subprocess with communicate()
    proc = subprocess.run(
        [sys.executable, script_path],
        input=json_input,
        capture_output=True,
        text=True,  # Text mode (Unicode strings, not bytes)
        encoding='utf-8',  # Explicit UTF-8 encoding
        timeout=30,  # Prevent hanging (adjust as needed)
        check=False,  # Don't raise on non-zero exit
    )

    # Handle errors
    if proc.returncode != 0:
        raise ScriptExecutionError(
            f"Script exited with code {proc.returncode}",
            stderr=proc.stderr,
        )

    # Parse JSON output
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise OutputParsingError(f"Invalid JSON output: {e}")
```

**Script Side** (user's skill script):

```python
#!/usr/bin/env python3
import sys
import json

def main():
    # Read JSON from stdin (entire input at once)
    try:
        input_data = sys.stdin.read()
        arguments = json.loads(input_data)
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON input: {e}"}))
        sys.exit(1)

    # Process arguments
    result = process_arguments(arguments)

    # Write JSON to stdout
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()
```

**Why `communicate()` is Recommended**:
1. **Prevents deadlocks**: Manages stdin/stdout/stderr buffers automatically
2. **Simple API**: Single method call, handles all I/O
3. **Safe**: Python docs explicitly recommend it over manual `.stdin.write()`
4. **Timeout support**: Built-in timeout parameter (Python 3.5+)
5. **Exception handling**: Raises `TimeoutExpired` on timeout

### 2.2 Buffering and Flushing Strategies

**Problem**: If you write to stdin without flushing, the script may block waiting for data.

**Solution 1 - Use `communicate()`** (Recommended):
- Automatically handles flushing and closing
- No manual buffer management needed

**Solution 2 - Manual Management** (only if `communicate()` not suitable):

```python
proc = subprocess.Popen(
    [sys.executable, script_path],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding='utf-8',
    bufsize=1,  # Line-buffered
)

# Write and flush
proc.stdin.write(json_input + '\n')
proc.stdin.flush()
proc.stdin.close()  # Signal EOF to script

# Read output
output = proc.stdout.read()
proc.wait()
```

**Key Points**:
- Always close stdin after writing (signals EOF to script)
- Use `bufsize=1` for line buffering
- `bufsize=0` for unbuffered (not recommended for text mode)
- `bufsize=-1` for system default (usually 4096-8192 bytes)

### 2.3 Error Handling for Write Failures

**Common Failure Modes**:

1. **Script doesn't read stdin** → BrokenPipeError
2. **Script exits early** → BrokenPipeError
3. **Large payload exceeds pipe buffer** → Deadlock (if not using `communicate()`)
4. **Encoding mismatch** → UnicodeEncodeError

**Robust Error Handling**:

```python
import subprocess
from typing import Optional

class ScriptExecutionError(Exception):
    """Script execution failed."""
    def __init__(self, message: str, stderr: Optional[str] = None):
        super().__init__(message)
        self.stderr = stderr

def invoke_script_safe(script_path: str, arguments: dict) -> dict:
    """Invoke script with comprehensive error handling."""
    try:
        # Serialize arguments
        json_input = json.dumps(arguments, ensure_ascii=False)

        # Size check
        if len(json_input.encode('utf-8')) > MAX_JSON_SIZE_BYTES:
            raise ValueError("Arguments too large for JSON stdin")

        # Run subprocess
        proc = subprocess.run(
            [sys.executable, script_path],
            input=json_input,
            capture_output=True,
            text=True,
            encoding='utf-8',
            timeout=30,
            check=False,
        )

    except subprocess.TimeoutExpired:
        raise ScriptExecutionError("Script exceeded timeout (30s)")

    except UnicodeEncodeError as e:
        raise ScriptExecutionError(f"Encoding error: {e}")

    except OSError as e:
        raise ScriptExecutionError(f"OS error: {e}")

    # Check exit code
    if proc.returncode != 0:
        raise ScriptExecutionError(
            f"Script failed (exit code {proc.returncode})",
            stderr=proc.stderr,
        )

    # Parse output
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise ScriptExecutionError(
            f"Invalid JSON output: {e}",
            stderr=proc.stdout[:500],  # Include first 500 chars
        )
```

---

## 3. Script-Side JSON Parsing

### 3.1 Best Practices for Reading JSON from Stdin

**Pattern 1 - Read All at Once** (Recommended for skills):

```python
import sys
import json

# Read entire stdin as string
input_str = sys.stdin.read()

# Parse JSON
try:
    arguments = json.loads(input_str)
except json.JSONDecodeError as e:
    error_msg = {
        "error": "Invalid JSON input",
        "details": str(e),
        "position": e.pos,
        "line": e.lineno,
    }
    print(json.dumps(error_msg), file=sys.stderr)
    sys.exit(1)
```

**Pattern 2 - Line-by-Line** (for JSONL streams):

```python
import sys
import json

for line_num, line in enumerate(sys.stdin, start=1):
    line = line.strip()
    if not line:
        continue

    try:
        arguments = json.loads(line)
        result = process(arguments)
        print(json.dumps(result))
    except json.JSONDecodeError as e:
        error = {
            "error": f"Invalid JSON at line {line_num}",
            "details": str(e),
        }
        print(json.dumps(error), file=sys.stderr)
```

### 3.2 Handling Malformed JSON Inputs

**Defensive Parsing with Detailed Errors**:

```python
import sys
import json
from typing import Any, Optional

def parse_json_stdin() -> Optional[dict]:
    """Parse JSON from stdin with detailed error reporting."""
    try:
        # Read all input
        input_str = sys.stdin.read()

        # Check for empty input
        if not input_str.strip():
            raise ValueError("No input received on stdin")

        # Parse JSON
        data = json.loads(input_str)

        # Validate it's a dict (expected format)
        if not isinstance(data, dict):
            raise TypeError(
                f"Expected JSON object, got {type(data).__name__}"
            )

        return data

    except json.JSONDecodeError as e:
        # Detailed JSON syntax error
        context_start = max(0, e.pos - 20)
        context_end = min(len(input_str), e.pos + 20)
        context = input_str[context_start:context_end]

        error = {
            "error": "JSON parse error",
            "message": e.msg,
            "line": e.lineno,
            "column": e.colno,
            "position": e.pos,
            "context": context,
        }
        print(json.dumps(error), file=sys.stderr)
        sys.exit(1)

    except (ValueError, TypeError) as e:
        error = {"error": str(e)}
        print(json.dumps(error), file=sys.stderr)
        sys.exit(1)
```

### 3.3 Timeout Considerations When Reading from Stdin

**Problem**: Script hangs forever waiting for stdin if parent doesn't write data.

**Solution 1 - Parent-Side Timeout** (Recommended):

```python
# Parent process sets timeout
proc = subprocess.run(
    [sys.executable, script_path],
    input=json_input,
    timeout=30,  # Kill script after 30s
    # ... other params
)
```

**Solution 2 - Script-Side Timeout** (advanced):

```python
import sys
import signal
import json

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Stdin read timeout")

# Set alarm for 30 seconds
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)

try:
    input_str = sys.stdin.read()
    signal.alarm(0)  # Cancel alarm
    arguments = json.loads(input_str)
except TimeoutError:
    print(json.dumps({"error": "Timeout reading stdin"}), file=sys.stderr)
    sys.exit(1)
```

**Note**: Signal-based timeouts don't work on Windows. Use parent-side timeout for cross-platform compatibility.

---

## 4. Security Considerations

### 4.1 JSON Injection Risks and Prevention

**Risk**: Malicious JSON can exploit vulnerabilities in parsers or downstream code.

**Attack Vectors**:
1. **Deserialization attacks**: Unsafe `eval()` or `pickle` usage
2. **Buffer overflow**: Extremely large JSON payloads
3. **Prototype pollution**: In JavaScript (not Python)
4. **Type confusion**: Unexpected data types

**Prevention Strategies**:

**1. Never Use `eval()` or `pickle`**:

```python
# WRONG - Unsafe!
arguments = eval(sys.stdin.read())  # Code execution risk

# WRONG - Unsafe with untrusted data!
import pickle
arguments = pickle.loads(sys.stdin.buffer.read())  # Arbitrary code execution

# RIGHT - Safe JSON parsing
import json
arguments = json.loads(sys.stdin.read())  # Safe
```

**2. Use `json.loads()` (Not `json.load()` with `object_hook`)**:

```python
# Safe - no custom deserialization
arguments = json.loads(input_str)

# Potentially unsafe - custom object creation
arguments = json.loads(input_str, object_hook=custom_decoder)
```

**3. Validate Input Schema**:

```python
import json
from typing import Any

def validate_arguments(args: dict) -> None:
    """Validate argument structure and types."""

    # Check required keys
    required_keys = {"action", "params"}
    if not required_keys.issubset(args.keys()):
        missing = required_keys - args.keys()
        raise ValueError(f"Missing required keys: {missing}")

    # Type validation
    if not isinstance(args["action"], str):
        raise TypeError("'action' must be a string")

    if not isinstance(args["params"], dict):
        raise TypeError("'params' must be an object")

    # Value validation
    if args["action"] not in ["read", "write", "delete"]:
        raise ValueError(f"Invalid action: {args['action']}")

# Usage
arguments = json.loads(input_str)
validate_arguments(arguments)
```

**4. Use Schema Validation Libraries** (for complex schemas):

```python
from jsonschema import validate, ValidationError

ARGUMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["read", "write", "delete"]},
        "params": {"type": "object"},
    },
    "required": ["action", "params"],
    "additionalProperties": False,
}

try:
    arguments = json.loads(input_str)
    validate(instance=arguments, schema=ARGUMENT_SCHEMA)
except ValidationError as e:
    print(json.dumps({"error": f"Schema validation failed: {e.message}"}))
    sys.exit(1)
```

### 4.2 Size Limits to Prevent DoS Attacks

**Attack**: Send extremely large JSON to consume memory and crash process.

**Prevention**:

```python
import sys
import json

MAX_INPUT_SIZE = 10 * 1024 * 1024  # 10MB

# Read with size limit
input_str = sys.stdin.read(MAX_INPUT_SIZE + 1)

# Check size
if len(input_str) > MAX_INPUT_SIZE:
    error = {
        "error": "Input too large",
        "max_size_mb": MAX_INPUT_SIZE / 1024 / 1024,
    }
    print(json.dumps(error), file=sys.stderr)
    sys.exit(1)

# Parse JSON
arguments = json.loads(input_str)
```

**Alternative - Streaming Parser** (for very large inputs):

```python
import ijson  # pip install ijson

# Parse JSON incrementally (doesn't load entire document)
for prefix, event, value in ijson.parse(sys.stdin):
    if prefix == "action":
        action = value
    elif prefix == "params":
        params = value
```

### 4.3 Validation Strategies for Untrusted Input

**Defense in Depth**:

1. **Size limits** (prevent resource exhaustion)
2. **Schema validation** (enforce structure)
3. **Type checking** (prevent type confusion)
4. **Value whitelisting** (restrict allowed values)
5. **Sanitization** (remove dangerous characters)

**Example - Comprehensive Validation**:

```python
import json
import sys
from typing import Any, Dict

MAX_INPUT_SIZE = 10 * 1024 * 1024
MAX_STRING_LENGTH = 1000
MAX_ARRAY_LENGTH = 1000
MAX_NESTING_DEPTH = 10

def validate_value(value: Any, depth: int = 0) -> None:
    """Recursively validate JSON values."""

    if depth > MAX_NESTING_DEPTH:
        raise ValueError(f"Nesting depth exceeds {MAX_NESTING_DEPTH}")

    if isinstance(value, str):
        if len(value) > MAX_STRING_LENGTH:
            raise ValueError(f"String too long: {len(value)} chars")

    elif isinstance(value, list):
        if len(value) > MAX_ARRAY_LENGTH:
            raise ValueError(f"Array too long: {len(value)} items")
        for item in value:
            validate_value(item, depth + 1)

    elif isinstance(value, dict):
        if len(value) > MAX_ARRAY_LENGTH:
            raise ValueError(f"Object too large: {len(value)} keys")
        for k, v in value.items():
            if not isinstance(k, str):
                raise TypeError("Object keys must be strings")
            validate_value(v, depth + 1)

    elif not isinstance(value, (bool, int, float, type(None))):
        raise TypeError(f"Invalid type: {type(value)}")

def parse_stdin_safe() -> Dict[str, Any]:
    """Parse stdin with comprehensive validation."""

    # Read with size limit
    input_str = sys.stdin.read(MAX_INPUT_SIZE + 1)

    if len(input_str) > MAX_INPUT_SIZE:
        raise ValueError("Input too large")

    # Parse JSON
    try:
        data = json.loads(input_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    # Validate structure
    if not isinstance(data, dict):
        raise TypeError("Expected JSON object")

    # Recursive validation
    validate_value(data)

    return data
```

### 4.4 stdin vs Command-Line Arguments (Security)

**Why stdin is More Secure**:

1. **Not visible in process lists**: `ps aux` won't show stdin data
2. **Not logged**: Shell history, audit logs don't capture stdin
3. **Harder to intercept**: Fewer attack vectors than argv
4. **No shell escaping needed**: No injection via argument parsing

**Comparison**:

| Aspect | Command-Line Args | stdin | Environment Vars |
|--------|------------------|-------|------------------|
| Visible in `ps` | ✓ Yes | ✗ No | ✗ No |
| Shell history | ✓ Yes | ✗ No | ~ Sometimes |
| Audit logs | ✓ Yes | ✗ No | ~ Sometimes |
| Size limits | ~128KB (OS) | ~64KB (pipe) | ~128KB (OS) |
| Complex data | Difficult | Easy (JSON) | Difficult |
| Security | Low | High | Medium |

**Recommendation**: For sensitive or complex data, **always use stdin**.

---

## 5. Error Handling

### 5.1 What Happens When a Script Doesn't Read Stdin?

**Scenario**: Script exits without reading stdin.

**Behavior**:
- **With `communicate()`**: No error, data is discarded, script exits normally
- **With manual `stdin.write()`**: May raise `BrokenPipeError` if pipe buffer full

**Example**:

```python
# Script that doesn't read stdin
# #!/usr/bin/env python3
# print("Hello")
# sys.exit(0)

# Parent process
proc = subprocess.run(
    [sys.executable, "script.py"],
    input=json.dumps({"data": "ignored"}),
    capture_output=True,
    text=True,
)
# No error - script runs successfully, stdin is ignored
```

**Detection Strategy**:

```python
# Option 1: Script signals it read stdin
# Script prints: {"stdin_read": true, "result": ...}

result = json.loads(proc.stdout)
if not result.get("stdin_read"):
    logging.warning("Script may not have read stdin")

# Option 2: Check script source (static analysis)
script_content = Path(script_path).read_text()
if "stdin" not in script_content:
    logging.warning("Script doesn't appear to read stdin")
```

### 5.2 Detecting Parsing Failures in the Script

**Strategy 1 - Exit Code Convention**:

```python
# Script side
try:
    arguments = json.loads(sys.stdin.read())
except json.JSONDecodeError:
    print(json.dumps({"error": "Invalid JSON"}), file=sys.stderr)
    sys.exit(1)  # Non-zero exit code

# Parent side
proc = subprocess.run(...)
if proc.returncode != 0:
    error_msg = proc.stderr or "Unknown error"
    raise ScriptExecutionError(f"Script failed: {error_msg}")
```

**Strategy 2 - Error in JSON Output**:

```python
# Script side
result = {"error": "Invalid JSON input", "details": str(e)}
print(json.dumps(result))
sys.exit(0)  # Success exit (error is in payload)

# Parent side
result = json.loads(proc.stdout)
if "error" in result:
    raise ScriptExecutionError(result["error"])
```

**Recommended**: Use exit codes (Strategy 1) for protocol errors (JSON parsing), reserve JSON errors for application-level errors.

### 5.3 Graceful Degradation Strategies

**Fallback 1 - Empty Arguments**:

```python
# Script side
try:
    input_str = sys.stdin.read()
    if not input_str.strip():
        arguments = {}  # Default to empty dict
    else:
        arguments = json.loads(input_str)
except json.JSONDecodeError:
    arguments = {}  # Fallback on parse error
    logging.warning("Failed to parse stdin, using empty arguments")
```

**Fallback 2 - Alternative Input Methods**:

```python
# Script side - try stdin, then command-line args
import sys
import json
import argparse

# Try reading from stdin first
if not sys.stdin.isatty():
    # stdin is piped/redirected
    try:
        arguments = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        arguments = None
else:
    arguments = None

# Fall back to command-line args
if arguments is None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True)
    parser.add_argument("--params", type=json.loads, default={})
    args = parser.parse_args()
    arguments = {"action": args.action, "params": args.params}
```

**Fallback 3 - Partial Parsing**:

```python
# Script side - handle partial JSON
try:
    arguments = json.loads(input_str)
except json.JSONDecodeError as e:
    # Try to salvage what we can
    if e.pos > 0:
        # Parse up to error position
        partial = input_str[:e.pos]
        arguments = json.loads(partial)
        logging.warning(f"Partial JSON parse at position {e.pos}")
    else:
        raise
```

---

## 6. Alternatives Considered

### 6.1 Command-Line Arguments

**Pros**:
- Simple, well-understood
- Native support in all languages
- Easy to debug (visible in `ps`)

**Cons**:
- Size limits (~128KB on Linux, varies by OS)
- Security: visible in process lists, shell history
- Complex data: requires escaping, quoting, encoding
- Limited structure: flat key-value pairs

**When to Use**:
- Simple scalar arguments (strings, numbers, flags)
- Public data (no secrets)
- Small payloads (<1KB)

**Example**:

```python
# Parent
subprocess.run([
    sys.executable, "script.py",
    "--action", "read",
    "--file", "/path/to/file",
])

# Script
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--action")
parser.add_argument("--file")
args = parser.parse_args()
```

### 6.2 Environment Variables

**Pros**:
- Not visible in `ps` output
- Available to all child processes
- Standard across platforms

**Cons**:
- Size limits (~128KB total on Linux)
- Persistence: can leak across processes
- Limited structure: flat key-value pairs
- Encoding: must encode complex data (e.g., JSON)

**When to Use**:
- Configuration (API keys, URLs)
- Secrets (better than argv, worse than stdin)
- Global settings for all child processes

**Example**:

```python
# Parent
env = os.environ.copy()
env["SKILL_ACTION"] = "read"
env["SKILL_PARAMS"] = json.dumps({"file": "/path/to/file"})

subprocess.run([sys.executable, "script.py"], env=env)

# Script
import os
import json
action = os.environ["SKILL_ACTION"]
params = json.loads(os.environ["SKILL_PARAMS"])
```

### 6.3 Temporary Files

**Pros**:
- No size limits (disk-based)
- Can handle very large payloads
- Decouples parent/child timing

**Cons**:
- Requires cleanup
- Slower (disk I/O)
- Security: file permissions, temp dir attacks
- Complexity: race conditions, orphaned files

**When to Use**:
- Very large payloads (>10MB)
- Long-running scripts that outlive parent
- Sharing data between multiple processes

**Example**:

```python
import tempfile
import json
import subprocess

# Parent
with tempfile.NamedTemporaryFile(
    mode='w',
    suffix='.json',
    delete=False,
) as f:
    json.dump(arguments, f)
    temp_path = f.name

try:
    subprocess.run([
        sys.executable, "script.py",
        "--input", temp_path,
    ])
finally:
    os.unlink(temp_path)

# Script
import json
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--input", required=True)
args = parser.parse_args()

with open(args.input) as f:
    arguments = json.load(f)
```

### 6.4 Comparison Matrix

| Method | Max Size | Security | Speed | Complexity | Structure |
|--------|----------|----------|-------|------------|-----------|
| **stdin (JSON)** | ~64KB (pipe) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Command-line args | ~128KB | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |
| Environment vars | ~128KB | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| Temporary files | Unlimited | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Sockets/pipes | Unlimited | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐⭐⭐ |

**Recommendation**: Use **stdin with JSON** for skillkit v0.3.

---

## 7. Code Examples

### 7.1 Complete Parent Process Example

```python
"""Complete example: Parent process sending JSON to script."""

import subprocess
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Configuration
MAX_JSON_SIZE_BYTES = 10 * 1024 * 1024  # 10MB
DEFAULT_TIMEOUT = 30  # seconds

class ScriptExecutionError(Exception):
    """Script execution failed."""
    def __init__(self, message: str, stderr: Optional[str] = None):
        super().__init__(message)
        self.stderr = stderr

def serialize_arguments(arguments: Dict[str, Any]) -> str:
    """
    Serialize arguments to JSON.

    Args:
        arguments: Dictionary of arguments to pass to script

    Returns:
        JSON string (single line, UTF-8)

    Raises:
        TypeError: If arguments contain non-serializable objects
        ValueError: If JSON exceeds size limit
    """
    try:
        json_str = json.dumps(
            arguments,
            ensure_ascii=False,  # Preserve Unicode
            separators=(',', ':'),  # Compact (no spaces)
            sort_keys=False,  # Preserve order (Python 3.7+)
        )
    except TypeError as e:
        raise TypeError(f"Arguments not JSON-serializable: {e}") from e

    # Check size
    size_bytes = len(json_str.encode('utf-8'))
    if size_bytes > MAX_JSON_SIZE_BYTES:
        raise ValueError(
            f"Arguments too large: {size_bytes / 1024 / 1024:.2f}MB "
            f"(max: {MAX_JSON_SIZE_BYTES / 1024 / 1024:.2f}MB)"
        )

    return json_str

def invoke_script(
    script_path: Path,
    arguments: Dict[str, Any],
    timeout: Optional[int] = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """
    Invoke a Python script with JSON arguments via stdin.

    Args:
        script_path: Path to Python script
        arguments: Arguments to pass (must be JSON-serializable)
        timeout: Timeout in seconds (None for no timeout)

    Returns:
        Parsed JSON output from script

    Raises:
        ScriptExecutionError: If script fails or returns invalid output
        FileNotFoundError: If script doesn't exist
        TimeoutError: If script exceeds timeout
    """
    # Validate script exists
    if not script_path.exists():
        raise FileNotFoundError(f"Script not found: {script_path}")

    # Serialize arguments
    try:
        json_input = serialize_arguments(arguments)
    except (TypeError, ValueError) as e:
        raise ScriptExecutionError(f"Invalid arguments: {e}")

    # Run subprocess
    try:
        proc = subprocess.run(
            [sys.executable, str(script_path)],
            input=json_input,
            capture_output=True,
            text=True,  # Unicode strings (not bytes)
            encoding='utf-8',  # Explicit UTF-8
            timeout=timeout,
            check=False,  # Don't raise on non-zero exit
        )
    except subprocess.TimeoutExpired as e:
        raise TimeoutError(
            f"Script exceeded timeout ({timeout}s)"
        ) from e
    except OSError as e:
        raise ScriptExecutionError(f"Failed to execute script: {e}") from e

    # Check exit code
    if proc.returncode != 0:
        stderr = proc.stderr.strip() if proc.stderr else "No error output"
        raise ScriptExecutionError(
            f"Script exited with code {proc.returncode}",
            stderr=stderr,
        )

    # Parse JSON output
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        # Include first 500 chars of output for debugging
        output_preview = proc.stdout[:500]
        raise ScriptExecutionError(
            f"Invalid JSON output: {e}\nOutput: {output_preview}"
        ) from e

    # Validate output is a dict
    if not isinstance(result, dict):
        raise ScriptExecutionError(
            f"Expected JSON object, got {type(result).__name__}"
        )

    return result

# Usage example
if __name__ == "__main__":
    arguments = {
        "action": "process",
        "params": {
            "file": "/path/to/data.csv",
            "format": "json",
        },
    }

    try:
        result = invoke_script(
            Path("./my_script.py"),
            arguments,
            timeout=60,
        )
        print(f"Success: {result}")
    except ScriptExecutionError as e:
        print(f"Error: {e}", file=sys.stderr)
        if e.stderr:
            print(f"Script stderr: {e.stderr}", file=sys.stderr)
        sys.exit(1)
```

### 7.2 Complete Script-Side Example

```python
#!/usr/bin/env python3
"""Complete example: Script receiving JSON arguments from stdin."""

import sys
import json
import logging
from typing import Dict, Any, Optional

# Configuration
MAX_INPUT_SIZE = 10 * 1024 * 1024  # 10MB
REQUIRED_KEYS = {"action", "params"}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

class InputError(Exception):
    """Invalid input from stdin."""
    pass

def read_json_stdin() -> Dict[str, Any]:
    """
    Read and parse JSON from stdin.

    Returns:
        Parsed JSON object (dict)

    Raises:
        InputError: If input is invalid, too large, or malformed
    """
    # Read with size limit
    logger.debug("Reading from stdin...")
    input_str = sys.stdin.read(MAX_INPUT_SIZE + 1)

    # Check size
    if len(input_str) > MAX_INPUT_SIZE:
        raise InputError(
            f"Input too large: {len(input_str)} bytes "
            f"(max: {MAX_INPUT_SIZE})"
        )

    # Check for empty input
    if not input_str.strip():
        raise InputError("No input received on stdin")

    # Parse JSON
    try:
        data = json.loads(input_str)
    except json.JSONDecodeError as e:
        # Provide context around error
        context_start = max(0, e.pos - 20)
        context_end = min(len(input_str), e.pos + 20)
        context = input_str[context_start:context_end]

        raise InputError(
            f"JSON parse error at line {e.lineno}, column {e.colno}: "
            f"{e.msg}\nContext: {context}"
        ) from e

    # Validate type
    if not isinstance(data, dict):
        raise InputError(
            f"Expected JSON object, got {type(data).__name__}"
        )

    logger.debug(f"Successfully parsed {len(data)} keys")
    return data

def validate_arguments(arguments: Dict[str, Any]) -> None:
    """
    Validate argument structure.

    Args:
        arguments: Parsed JSON arguments

    Raises:
        InputError: If arguments are invalid
    """
    # Check required keys
    missing = REQUIRED_KEYS - arguments.keys()
    if missing:
        raise InputError(f"Missing required keys: {missing}")

    # Type validation
    if not isinstance(arguments["action"], str):
        raise InputError("'action' must be a string")

    if not isinstance(arguments["params"], dict):
        raise InputError("'params' must be an object")

    # Value validation
    valid_actions = {"read", "write", "process"}
    if arguments["action"] not in valid_actions:
        raise InputError(
            f"Invalid action '{arguments['action']}', "
            f"must be one of: {valid_actions}"
        )

    logger.debug(f"Arguments validated: action={arguments['action']}")

def process_arguments(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process arguments and return result.

    Args:
        arguments: Validated arguments

    Returns:
        Result dictionary (must be JSON-serializable)
    """
    action = arguments["action"]
    params = arguments["params"]

    logger.info(f"Processing action: {action}")

    # Example processing
    if action == "read":
        result = {
            "status": "success",
            "data": f"Read file: {params.get('file', 'unknown')}",
        }
    elif action == "write":
        result = {
            "status": "success",
            "data": f"Wrote file: {params.get('file', 'unknown')}",
        }
    elif action == "process":
        result = {
            "status": "success",
            "data": "Processed data",
        }
    else:
        # Should not reach here due to validation
        result = {"status": "error", "message": f"Unknown action: {action}"}

    return result

def write_json_stdout(data: Dict[str, Any]) -> None:
    """
    Write JSON result to stdout.

    Args:
        data: Result to serialize
    """
    try:
        json_str = json.dumps(data, ensure_ascii=False)
        print(json_str)
    except TypeError as e:
        logger.error(f"Failed to serialize result: {e}")
        # Write error as JSON
        error = {"status": "error", "message": f"Serialization error: {e}"}
        print(json.dumps(error))
        sys.exit(1)

def main() -> int:
    """
    Main entry point.

    Returns:
        Exit code (0 = success, 1 = error)
    """
    try:
        # Read and parse stdin
        arguments = read_json_stdin()

        # Validate arguments
        validate_arguments(arguments)

        # Process arguments
        result = process_arguments(arguments)

        # Write result to stdout
        write_json_stdout(result)

        return 0

    except InputError as e:
        logger.error(f"Input error: {e}")
        error = {"status": "error", "message": str(e)}
        write_json_stdout(error)
        return 1

    except Exception as e:
        logger.exception("Unexpected error")
        error = {
            "status": "error",
            "message": f"Internal error: {type(e).__name__}",
        }
        write_json_stdout(error)
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

---

## 8. Edge Cases and Mitigation Strategies

### 8.1 Large JSON Payloads

**Edge Case**: Arguments exceed 10MB limit.

**Mitigation**:
1. Raise clear error with size limit
2. Suggest splitting data into chunks
3. Offer file-based alternative for large data

```python
# Parent side
try:
    invoke_script(script_path, large_arguments)
except ValueError as e:
    if "too large" in str(e):
        # Fall back to file-based approach
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            json.dump(large_arguments, f)
            temp_file = f.name

        # Pass file path instead
        invoke_script(script_path, {"__file__": temp_file})
```

### 8.2 Script Doesn't Read Stdin

**Edge Case**: Script ignores stdin, parent hangs or wastes resources.

**Mitigation**:
1. Use timeout to prevent indefinite blocking
2. Log warning if script doesn't appear to use stdin
3. Document stdin requirement in skill specification

```python
# Static analysis check
script_content = Path(script_path).read_text()
if "stdin" not in script_content and "sys.stdin" not in script_content:
    logger.warning(
        f"Script {script_path} may not read stdin - "
        f"arguments will be ignored"
    )
```

### 8.3 Binary Data in Arguments

**Edge Case**: User tries to pass binary data (bytes, images) in JSON.

**Mitigation**:
1. Detect non-serializable types early
2. Suggest base64 encoding for binary data
3. Recommend file references for large binary data

```python
import base64

# Encode binary data
arguments = {
    "image_data": base64.b64encode(image_bytes).decode('ascii'),
}

# Script side - decode
image_bytes = base64.b64decode(arguments["image_data"])
```

### 8.4 Unicode Encoding Errors

**Edge Case**: Invalid UTF-8 sequences in strings.

**Mitigation**:
1. Use `errors='replace'` or `errors='ignore'` when encoding
2. Validate UTF-8 before serialization
3. Set explicit `encoding='utf-8'` everywhere

```python
# Parent side - handle encoding errors gracefully
try:
    json_str = json.dumps(arguments, ensure_ascii=False)
    json_str.encode('utf-8')  # Test encoding
except UnicodeEncodeError as e:
    logger.warning(f"Encoding error, using ASCII: {e}")
    json_str = json.dumps(arguments, ensure_ascii=True)
```

### 8.5 Script Exits Before Reading All Input

**Edge Case**: Script crashes/exits early, parent writes to closed pipe.

**Mitigation**:
1. Use `communicate()` (handles BrokenPipeError automatically)
2. Check returncode before assuming success
3. Log stderr for debugging

```python
# communicate() handles this gracefully
proc = subprocess.run(
    [sys.executable, script_path],
    input=large_json_input,  # Even if script exits early
    capture_output=True,
    text=True,
)

# Check if script failed
if proc.returncode != 0:
    logger.error(f"Script failed: {proc.stderr}")
```

### 8.6 Concurrent Script Invocations

**Edge Case**: Multiple scripts running concurrently, potential resource contention.

**Mitigation**:
1. Use asyncio for concurrent execution
2. Implement rate limiting/throttling
3. Monitor system resources

```python
import asyncio

async def invoke_script_async(script_path, arguments):
    """Async version using asyncio.create_subprocess_exec."""
    proc = await asyncio.create_subprocess_exec(
        sys.executable, script_path,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    json_input = json.dumps(arguments, ensure_ascii=False).encode('utf-8')
    stdout, stderr = await proc.communicate(input=json_input)

    if proc.returncode != 0:
        raise ScriptExecutionError(stderr.decode('utf-8'))

    return json.loads(stdout.decode('utf-8'))

# Run multiple scripts concurrently
results = await asyncio.gather(
    invoke_script_async(script1, args1),
    invoke_script_async(script2, args2),
    invoke_script_async(script3, args3),
)
```

### 8.7 Platform Differences (Windows vs Unix)

**Edge Case**: Behavior differs on Windows (no signals, different line endings).

**Mitigation**:
1. Use `text=True` mode (handles line endings automatically)
2. Avoid signal-based timeouts (use parent timeout)
3. Test on both platforms

```python
# Cross-platform compatible
proc = subprocess.run(
    [sys.executable, script_path],
    input=json_input,
    text=True,  # Handles \n vs \r\n automatically
    encoding='utf-8',  # Explicit encoding
    timeout=30,  # Works on all platforms
)
```

---

## 9. Recommendations for skillkit v0.3

### 9.1 Recommended Implementation

**Core Pattern**:
1. Use `subprocess.run()` with `communicate()`
2. Pass JSON via `input` parameter (text mode)
3. Set explicit timeout (30s default)
4. Validate JSON size before sending
5. Parse JSON output, check for errors
6. Provide clear error messages

**Key APIs**:

```python
# Public API
def invoke_skill_script(
    script_path: Path,
    arguments: Dict[str, Any],
    timeout: int = 30,
) -> Dict[str, Any]:
    """Invoke skill script with JSON arguments via stdin."""
    # Implementation from section 7.1
    ...

# Internal helper
def _serialize_json_arguments(arguments: Dict[str, Any]) -> str:
    """Serialize arguments to JSON with validation."""
    # Implementation from section 7.1
    ...
```

### 9.2 Configuration Parameters

```python
# skillkit/core/config.py
SCRIPT_EXECUTION_CONFIG = {
    # Size limits
    "max_json_size_bytes": 10 * 1024 * 1024,  # 10MB
    "max_string_length": 1000,  # Per string
    "max_array_length": 1000,  # Per array
    "max_nesting_depth": 10,  # JSON depth

    # Timeouts
    "default_timeout": 30,  # seconds
    "max_timeout": 300,  # 5 minutes max

    # Encoding
    "encoding": "utf-8",
    "ensure_ascii": False,  # Preserve Unicode

    # Error handling
    "raise_on_stderr": False,  # Allow stderr logging
    "validate_output_schema": True,
}
```

### 9.3 Error Messages

**Clear, actionable error messages**:

```python
# Good error messages
"Arguments too large: 15.2MB (max: 10.0MB). Consider using file references."

"Script exited with code 1: ValueError: Invalid action 'delete'"

"Script timeout after 30s. Increase timeout or optimize script."

"Invalid JSON output from script (line 5, column 12): Expecting ',' delimiter"

# Bad error messages (avoid)
"Serialization failed"
"Script error"
"JSON parse error"
```

### 9.4 Documentation Requirements

**For Skill Authors** (in SKILL.md spec):
1. Scripts must read JSON from stdin
2. Scripts must write JSON to stdout
3. Exit code 0 = success, non-zero = error
4. Argument schema requirements
5. Output schema requirements
6. Size limits and timeouts

**Example SKILL.md snippet**:

```markdown
## Script Execution

This skill uses a Python script that receives arguments via JSON on stdin.

### Input Schema

```json
{
  "action": "read",
  "params": {
    "file": "/path/to/file"
  }
}
```

### Output Schema

```json
{
  "status": "success",
  "data": "..."
}
```

### Requirements

- Script must read JSON from stdin (sys.stdin.read())
- Script must write JSON to stdout (print(json.dumps(...)))
- Maximum argument size: 10MB
- Timeout: 30 seconds (configurable)
```

### 9.5 Testing Strategy

**Test Cases**:
1. Happy path: Valid JSON in/out
2. Large payloads: Near size limit
3. Invalid JSON: Malformed input
4. Script errors: Non-zero exit code
5. Timeouts: Long-running scripts
6. Unicode: Non-ASCII characters
7. Edge cases: Empty input, missing keys

**Example Test**:

```python
def test_invoke_script_with_unicode():
    """Test passing Unicode characters through JSON."""
    script = tmp_path / "echo.py"
    script.write_text("""
import sys, json
args = json.loads(sys.stdin.read())
print(json.dumps({"echo": args["message"]}))
""")

    result = invoke_script(
        script,
        {"message": "Hello 世界 🌍"},
    )

    assert result["echo"] == "Hello 世界 🌍"
```

---

## 10. References

### 10.1 Python Documentation
- [subprocess module](https://docs.python.org/3/library/subprocess.html) (Python 3.14)
- [json module](https://docs.python.org/3/library/json.html) (Python 3.14)
- [asyncio.subprocess](https://docs.python.org/3/library/asyncio-subprocess.html) (Python 3.14)

### 10.2 Standards
- [RFC 7159: The JavaScript Object Notation (JSON) Data Interchange Format](https://www.rfc-editor.org/rfc/rfc7159.html)
- [RFC 8259: The JSON Data Interchange Format](https://www.rfc-editor.org/rfc/rfc8259.html) (obsoletes RFC 7159)

### 10.3 Security Resources
- [JSON Injection Vulnerabilities](https://www.invicti.com/learn/json-injection/) (2024)
- [OWASP JSON Security Cheat Sheet](https://cheatsheetseries.owasp.org/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)

### 10.4 Community Best Practices
- [Stack Overflow: subprocess.communicate() vs stdin.write()](https://stackoverflow.com/questions/21141712/)
- [Stack Overflow: Passing JSON to subprocess](https://stackoverflow.com/questions/24087752/)
- [Processing Large JSON Files](https://pythonspeed.com/articles/json-memory-streaming/) (2024)

---

## Conclusion

**Recommended Pattern for skillkit v0.3**:

1. **Use `subprocess.run()` with `communicate()`** for safety and simplicity
2. **Pass JSON via stdin** (not command-line args) for security and flexibility
3. **Set 10MB size limit** with clear error messages
4. **Use 30-second default timeout** (configurable)
5. **Validate input/output schemas** for robustness
6. **Handle Unicode correctly** with `ensure_ascii=False` and `encoding='utf-8'`
7. **Provide detailed error messages** for debugging
8. **Document requirements clearly** in SKILL.md specification

This approach balances **simplicity** (for skill authors), **security** (for users), and **robustness** (for the skillkit library).

**Next Steps**:
1. Implement core `invoke_skill_script()` function
2. Add comprehensive tests (8+ scenarios)
3. Update SKILL.md specification
4. Create example skills with scripts
5. Document in user guide

---

**Research Date**: 2025-11-18
**Author**: Claude Code
**Status**: Complete
