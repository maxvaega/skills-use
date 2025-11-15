# File Reference Skill - Examples

## Example 1: Simple Data Processing

Process a CSV file using the skill's data processor:

```python
from skillkit import SkillManager
from skillkit.core.path_resolver import FilePathResolver
from pathlib import Path

# Initialize skill manager
manager = SkillManager("./examples/skills")
manager.discover()

# Invoke skill
result = manager.invoke_skill(
    "file-reference-skill",
    "data/input.csv data/output.csv"
)

print(result)
```

## Example 2: Accessing Supporting Scripts

Read and execute supporting scripts:

```python
from pathlib import Path
from skillkit.core.path_resolver import FilePathResolver

# Get skill's base directory
skill = manager.get_skill("file-reference-skill")
base_dir = skill.base_directory

# Resolve script path securely
processor_path = FilePathResolver.resolve_path(
    base_dir,
    "scripts/data_processor.py"
)

# Read script content
with open(processor_path) as f:
    script_code = f.read()

print(f"Script location: {processor_path}")
print(f"Script length: {len(script_code)} bytes")
```

## Example 3: Loading Configuration Template

Load and parse configuration template:

```python
import yaml
from skillkit.core.path_resolver import FilePathResolver

# Resolve config template path
config_path = FilePathResolver.resolve_path(
    base_dir,
    "templates/config.yaml"
)

# Load configuration
with open(config_path) as f:
    config = yaml.safe_load(f)

print("Configuration:", config)
```

## Example 4: Handling Security Violations

Demonstrate path traversal prevention:

```python
from skillkit.core.path_resolver import FilePathResolver
from skillkit.core.exceptions import PathSecurityError

try:
    # Attempt path traversal (will be blocked)
    malicious_path = FilePathResolver.resolve_path(
        base_dir,
        "../../../etc/passwd"
    )
except PathSecurityError as e:
    print(f"Security violation blocked: {e}")
    # Expected output:
    # Security violation blocked: Path traversal attempt detected:
    # '../../../etc/passwd' resolves outside skill directory
```

## Example 5: Validating Input Files

Use validator script to check input files:

```python
import subprocess
from skillkit.core.path_resolver import FilePathResolver

# Resolve validator script
validator_path = FilePathResolver.resolve_path(
    base_dir,
    "scripts/validator.py"
)

# Import and use validator
import sys
sys.path.insert(0, str(validator_path.parent))
from validator import validate_csv_format

# Validate input file
is_valid = validate_csv_format("data/input.csv")
print(f"File is valid: {is_valid}")
```

## Example 6: Generating Reports

Generate report using template:

```python
from string import Template
from datetime import datetime
from skillkit.core.path_resolver import FilePathResolver

# Resolve report template
template_path = FilePathResolver.resolve_path(
    base_dir,
    "templates/report.md"
)

# Load template
with open(template_path) as f:
    template_content = f.read()

# Fill template with data
template = Template(template_content)
report = template.safe_substitute({
    'timestamp': datetime.now().isoformat(),
    'input_file': 'data/input.csv',
    'input_size': '1234',
    'format': 'CSV',
    'encoding': 'UTF-8',
    'start_time': '10:00:00',
    'end_time': '10:00:05',
    'duration': '5',
    'status': 'SUCCESS',
    'output_file': 'data/output.csv',
    'output_size': '1234',
    'record_count': '100',
    'error_count': '0',
    'validation_results': 'All checks passed',
    'processing_log': 'Processing completed successfully'
})

print(report)
```

## Example 7: Shell Script Integration

Execute shell helper script:

```python
import subprocess
from skillkit.core.path_resolver import FilePathResolver

# Resolve shell script
helper_path = FilePathResolver.resolve_path(
    base_dir,
    "scripts/helper.sh"
)

# Execute script
result = subprocess.run(
    ['bash', str(helper_path), 'check'],
    capture_output=True,
    text=True
)

print(result.stdout)
```

## Example 8: Multiple File Access

Access multiple supporting files in one operation:

```python
from skillkit.core.path_resolver import FilePathResolver

# List of files to access
file_paths = [
    "scripts/data_processor.py",
    "scripts/validator.py",
    "templates/config.yaml",
    "docs/usage.md"
]

# Resolve all paths securely
resolved_paths = {}
for rel_path in file_paths:
    try:
        abs_path = FilePathResolver.resolve_path(base_dir, rel_path)
        resolved_paths[rel_path] = abs_path
        print(f"✓ {rel_path} -> {abs_path}")
    except PathSecurityError as e:
        print(f"✗ {rel_path} -> BLOCKED ({e})")

print(f"\nSuccessfully resolved {len(resolved_paths)} paths")
```

## Example 9: Error Handling Best Practices

Robust error handling when accessing supporting files:

```python
from pathlib import Path
from skillkit.core.path_resolver import FilePathResolver
from skillkit.core.exceptions import PathSecurityError

def safe_load_supporting_file(base_dir: Path, rel_path: str) -> str:
    """Safely load supporting file with comprehensive error handling."""
    try:
        # Resolve path securely
        abs_path = FilePathResolver.resolve_path(base_dir, rel_path)

        # Read file content
        with open(abs_path, 'r', encoding='utf-8') as f:
            return f.read()

    except PathSecurityError as e:
        print(f"Security violation: {e}")
        raise
    except FileNotFoundError:
        print(f"File not found: {rel_path}")
        raise
    except PermissionError:
        print(f"Permission denied: {rel_path}")
        raise
    except UnicodeDecodeError:
        print(f"Invalid UTF-8 encoding: {rel_path}")
        raise
    except Exception as e:
        print(f"Unexpected error loading {rel_path}: {e}")
        raise

# Usage
try:
    content = safe_load_supporting_file(base_dir, "scripts/helper.py")
    print(f"Loaded {len(content)} bytes")
except Exception as e:
    print(f"Failed to load file: {e}")
```

## Summary

These examples demonstrate:
- Secure file path resolution using FilePathResolver
- Accessing scripts, templates, and documentation
- Handling security violations gracefully
- Integration with Python and shell scripts
- Best practices for error handling
- Template-based report generation
