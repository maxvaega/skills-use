# File Reference Skill - Usage Guide

## Overview

The file-reference-skill demonstrates how to structure a skill with supporting files (scripts, templates, documentation) and access them securely using the FilePathResolver.

## Directory Structure

```
file-reference-skill/
├── SKILL.md                 # Main skill definition
├── scripts/                 # Processing scripts
│   ├── data_processor.py    # Main data processor
│   ├── validator.py         # Input validation
│   └── helper.sh            # Shell utilities
├── templates/               # Configuration and output templates
│   ├── config.yaml          # Configuration template
│   └── report.md            # Report generation template
└── docs/                    # Documentation
    ├── usage.md             # This file
    └── examples.md          # Example use cases
```

## Using Supporting Files

### From Python

```python
from pathlib import Path
from skillkit.core.path_resolver import FilePathResolver

# Base directory is provided in the skill context
base_dir = Path("/path/to/skills/file-reference-skill")

# Resolve paths securely
processor_path = FilePathResolver.resolve_path(
    base_dir,
    "scripts/data_processor.py"
)

# Read file content
with open(processor_path) as f:
    script_code = f.read()
```

### From Shell

```bash
# Get base directory from skill context
BASE_DIR="/path/to/skills/file-reference-skill"

# Use helper script
bash "$BASE_DIR/scripts/helper.sh" check

# Run data processor
python3 "$BASE_DIR/scripts/data_processor.py" input.csv output.csv
```

## Security Features

The FilePathResolver ensures:

1. **Path Traversal Prevention**: Blocks attempts to access files outside skill directory
2. **Symlink Validation**: Resolves symlinks and verifies targets stay within base directory
3. **Absolute Path Rejection**: Prevents absolute path injection
4. **Detailed Logging**: All security violations logged at ERROR level

### Valid Paths

```python
# Allowed - relative path within skill directory
FilePathResolver.resolve_path(base_dir, "scripts/helper.py")
FilePathResolver.resolve_path(base_dir, "templates/config.yaml")
FilePathResolver.resolve_path(base_dir, "docs/usage.md")
```

### Invalid Paths (Blocked)

```python
# Blocked - directory traversal
FilePathResolver.resolve_path(base_dir, "../../etc/passwd")

# Blocked - absolute path
FilePathResolver.resolve_path(base_dir, "/etc/passwd")

# Blocked - symlink escape
# (if symlink target is outside base_dir)
FilePathResolver.resolve_path(base_dir, "malicious_link")
```

## Example Workflow

1. **Skill Invocation**
   ```python
   manager = SkillManager()
   manager.discover()

   result = manager.invoke_skill(
       "file-reference-skill",
       "input_data.csv output_data.csv"
   )
   ```

2. **Skill Processing**
   - Skill receives base directory in context
   - Script paths resolved using FilePathResolver
   - Scripts executed with validated paths
   - Results returned to caller

3. **File Access**
   - All file operations use resolved paths
   - Security violations raise PathSecurityError
   - Detailed error messages help debugging

## Best Practices

1. **Always use FilePathResolver** for accessing supporting files
2. **Use relative paths** from skill base directory
3. **Document file dependencies** in SKILL.md
4. **Test with various path patterns** including edge cases
5. **Handle PathSecurityError** appropriately in your code

## Troubleshooting

### PathSecurityError

**Problem**: Attempting to access files outside skill directory

**Solution**: Use relative paths within skill directory only

### FileNotFoundError

**Problem**: Resolved path doesn't exist

**Solution**: Verify file exists in skill directory structure

### PermissionError

**Problem**: Cannot read resolved file

**Solution**: Check file permissions and ownership
