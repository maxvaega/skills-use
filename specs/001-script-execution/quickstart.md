# Quickstart: Script Execution Feature

**Target**: v0.3.0 Implementation
**Audience**: skillkit developers implementing this feature

---

## Implementation Order

### Phase 1: Core Components (Days 1-2)

1. **Create `src/skillkit/core/scripts.py`**:
   ```python
   # Data models
   - ScriptMetadata (dataclass)
   - ScriptExecutionResult (dataclass)
   - INTERPRETER_MAP (constant dict)

   # Core classes
   - ScriptDescriptionExtractor
   - ScriptDetector
   - ScriptExecutor
   ```

2. **Extend `src/skillkit/core/exceptions.py`**:
   ```python
   - InterpreterNotFoundError
   - ScriptNotFoundError
   - ScriptPermissionError
   - ArgumentSerializationError
   - ArgumentSizeError
   ```

3. **Extend `src/skillkit/core/models.py`** (Skill class):
   ```python
   - Add `_scripts` private field
   - Add `scripts` property (lazy loading)
   ```

### Phase 2: Integration (Day 3)

4. **Extend `src/skillkit/core/manager.py`** (SkillManager):
   ```python
   - Add `default_script_timeout` parameter to __init__
   - Add `execute_skill_script()` method
   ```

5. **Extend `src/skillkit/integrations/langchain.py`**:
   ```python
   - Add `create_script_tools()` function
   - Modify `to_langchain_tools()` to include script tools
   ```

### Phase 3: Security & Testing (Days 4-7)

6. **Security features**:
   - Path validation with FilePathResolver
   - Permission checks (setuid/setgid)
   - Tool restriction enforcement

7. **Testing**:
   - Unit tests (test_script_executor.py, test_script_detector.py)
   - Integration tests (test_script_langchain.py, test_script_manager.py)
   - Fixtures (create test-script-skill/ in tests/fixtures/)

8. **Documentation**:
   - Update README.md with script execution examples
   - Update .docs/ with v0.3 changes
   - Add examples/script_execution.py

---

## Key Implementation Decisions

### 1. subprocess.run() Configuration

```python
result = subprocess.run(
    [interpreter, str(script_path)],  # ✅ List form
    input=json.dumps(arguments),      # ✅ JSON via stdin
    capture_output=True,
    text=True,
    timeout=timeout,
    cwd=skill_base_dir,
    shell=False,                      # ✅ CRITICAL: Never True
    check=False
)
```

### 2. Path Validation

```python
def validate_script_path(script_path: Path, skill_base_dir: Path) -> Path:
    real_path = Path(os.path.realpath(script_path))
    real_base = Path(os.path.realpath(skill_base_dir))

    common = Path(os.path.commonpath([real_path, real_base]))
    if common != real_base:
        raise PathSecurityError("Script path escapes skill directory")

    return real_path
```

### 3. Interpreter Resolution

```python
def resolve_interpreter(file_path: Path) -> str:
    # Strategy 1: Extension mapping
    interpreter = INTERPRETER_MAP.get(file_path.suffix.lower())

    # Strategy 2: Shebang fallback
    if not interpreter:
        interpreter = extract_shebang_interpreter(file_path)

    # Strategy 3: Validate existence
    if not shutil.which(interpreter):
        raise InterpreterNotFoundError(f"'{interpreter}' not found in PATH")

    return interpreter
```

### 4. LangChain Tool Creation

```python
def create_script_tools(skill: Skill) -> List[StructuredTool]:
    tools = []

    for script in skill.scripts:
        tool_name = f"{skill.metadata.name}.{script.name}"

        def execute_wrapper(arguments: dict, script_meta=script) -> str:
            result = executor.execute(script_meta.path, arguments, ...)
            if result.exit_code == 0:
                return result.stdout
            else:
                raise ToolException(result.stderr)

        tools.append(StructuredTool(
            name=tool_name,
            description=script.description or f"Execute {script.name}",
            func=execute_wrapper,
            args_schema=FreeFormJSONSchema  # Accepts any JSON
        ))

    return tools
```

---

## Testing Checklist

### Unit Tests (80+ cases)

**ScriptExecutor**:
- [ ] Successful execution (exit code 0)
- [ ] Failed execution (exit code 1)
- [ ] Timeout (exit code 124)
- [ ] Signal termination (SIGSEGV, SIGKILL)
- [ ] Path traversal prevention
- [ ] Symlink validation
- [ ] Permission checks (setuid/setgid)
- [ ] Output truncation (>10MB)
- [ ] Encoding errors
- [ ] Environment variable injection

**ScriptDetector**:
- [ ] Detect all script types (.py, .sh, .js, .rb, .pl)
- [ ] Skip non-scripts (.json, .md)
- [ ] Skip hidden files (.hidden.py)
- [ ] Nested directories (up to max_depth)
- [ ] Description extraction (docstrings, comments)
- [ ] Empty description (no comments)
- [ ] Performance (<10ms for 50 scripts)

### Integration Tests (20+ scenarios)

- [ ] End-to-end via SkillManager
- [ ] LangChain tool creation
- [ ] LangChain tool invocation
- [ ] Concurrent script executions
- [ ] Tool restriction enforcement
- [ ] Multi-script skill
- [ ] Error propagation to agent

---

## Example Scripts for Testing

### Python Test Script

```python
#!/usr/bin/env python3
"""Test script for data transformation.

Accepts input data and transforms it.
"""
import sys
import json

args = json.load(sys.stdin)
result = {"status": "success", "data": args.get("input", "")}
print(json.dumps(result))
```

### Shell Test Script

```bash
#!/bin/bash
# Test script for file operations
#
# Demonstrates shell scripting support

read -r input
echo "Processed: $input"
```

### Timeout Test Script

```python
#!/usr/bin/env python3
"""Script that triggers timeout."""
import time

while True:
    time.sleep(1)
```

---

## Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| Execution overhead | <50ms | 95th percentile |
| Script detection | <10ms | Per skill with ≤50 scripts |
| Description extraction | <3ms | Per script |
| Path validation | <1ms | Per validation |
| JSON serialization | <10ms | Per payload (<1MB) |

---

## Security Checklist

Before merging to main:

- [ ] All subprocess calls use `shell=False`
- [ ] All commands use list form (not strings)
- [ ] Path traversal prevention tested (10+ attack patterns)
- [ ] Permission validation tested (setuid/setgid)
- [ ] Output size limits enforced (10MB)
- [ ] Timeout enforcement tested
- [ ] Signal detection tested
- [ ] Audit logging implemented
- [ ] Tool restriction enforcement tested
- [ ] Security review completed

---

## Documentation Updates

### README.md

Add section:

```markdown
### Script Execution (v0.3+)

Skills can include executable scripts for deterministic operations:

\`\`\`python
from skillkit import SkillManager

manager = SkillManager()
result = manager.execute_skill_script(
    skill_name="pdf-extractor",
    script_name="extract",
    arguments={"file": "document.pdf"}
)

if result.success:
    print(result.stdout)
\`\`\`
```

### CLAUDE.md

Update version info:

```markdown
## v0.3 (In Progress)
- Script execution support
- Tool restriction enforcement
- Enhanced security features
```

---

## Release Checklist

- [ ] All tests passing (80%+ coverage)
- [ ] Documentation updated
- [ ] Examples added
- [ ] Security review passed
- [ ] Performance benchmarks met
- [ ] Changelog updated
- [ ] Version bumped to 0.3.0
- [ ] PyPI release prepared

---

## Next Steps

1. Create feature branch: `git checkout -b 001-script-execution`
2. Implement Phase 1 (Core Components)
3. Write unit tests for Phase 1
4. Implement Phase 2 (Integration)
5. Write integration tests
6. Implement Phase 3 (Security & polish)
7. Complete testing and documentation
8. Submit PR for review

**Estimated Timeline**: 5-7 days for full v0.3.0 implementation
