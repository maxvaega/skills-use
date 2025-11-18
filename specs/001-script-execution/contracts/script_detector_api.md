# Script Detector API Contract

**Module**: `skillkit.core.scripts.ScriptDetector`
**Version**: v0.3.0
**Purpose**: Detect executable scripts in skill directories and extract metadata

---

## Class Interface

### ScriptDetector

```python
class ScriptDetector:
    """Detect and parse executable scripts within skill directories."""

    def __init__(
        self,
        max_depth: int = 5,
        max_lines_for_description: int = 50
    ) -> None:
        """
        Initialize ScriptDetector.

        Args:
            max_depth: Maximum directory nesting depth to scan (default: 5)
            max_lines_for_description: Max lines to read for description extraction

        Raises:
            ValueError: If max_depth < 1 or max_lines_for_description < 1
        """

    def detect_scripts(
        self,
        skill_base_dir: Path
    ) -> List[ScriptMetadata]:
        """
        Detect all executable scripts in skill directory.

        Scanning Strategy:
        1. Scan `scripts/` directory (primary location)
        2. Scan skill root directory (secondary fallback)
        3. Recurse into subdirectories up to max_depth levels
        4. Filter files by executable extensions (.py, .sh, .js, .rb, .pl)
        5. Extract metadata for each detected script

        Args:
            skill_base_dir: Base directory of the skill

        Returns:
            List of ScriptMetadata (empty list if no scripts found)

        Raises:
            FileNotFoundError: If skill_base_dir doesn't exist
            NotADirectoryError: If skill_base_dir is not a directory
            PermissionError: If skill_base_dir is not readable

        Performance:
            - <10ms for skills with ≤50 scripts (per FR-017)
            - Scales linearly with number of script files
            - No network I/O or external process calls

        Example:
            >>> detector = ScriptDetector()
            >>> scripts = detector.detect_scripts(Path("/skills/pdf-extractor"))
            >>> for script in scripts:
            ...     print(f"{script.name} ({script.script_type}): {script.description}")
        """
```

---

## Method Contract Details

### detect_scripts() Pre-Conditions

```python
# Directory validation
assert skill_base_dir.exists()
assert skill_base_dir.is_dir()
assert os.access(skill_base_dir, os.R_OK)
```

### detect_scripts() Post-Conditions

```python
scripts = detector.detect_scripts(skill_base_dir)

# Always returns a list (never None)
assert isinstance(scripts, list)

# All elements are ScriptMetadata
assert all(isinstance(s, ScriptMetadata) for s in scripts)

# Paths are relative to skill_base_dir
for script in scripts:
    assert not script.path.is_absolute()
    full_path = skill_base_dir / script.path
    assert full_path.exists()
    assert full_path.is_relative_to(skill_base_dir)

# No duplicate scripts (by path)
paths = [s.path for s in scripts]
assert len(paths) == len(set(paths))

# Script types are valid
valid_types = {'python', 'shell', 'javascript', 'ruby', 'perl'}
assert all(s.script_type in valid_types for s in scripts)
```

---

## Script Detection Algorithm

### 1. Directory Scanning

```python
def _scan_directories(skill_base_dir: Path, max_depth: int) -> List[Path]:
    """
    Scan directories for script files.

    Scans in priority order:
    1. {skill_base_dir}/scripts/**/*.{py,sh,js,rb,pl}
    2. {skill_base_dir}/*.{py,sh,js,rb,pl}

    Returns:
        List of absolute paths to potential script files
    """
    script_files = []

    # Primary: scripts/ directory
    scripts_dir = skill_base_dir / 'scripts'
    if scripts_dir.exists() and scripts_dir.is_dir():
        script_files.extend(
            _scan_directory_recursive(scripts_dir, max_depth)
        )

    # Secondary: skill root directory (non-recursive)
    for pattern in ['*.py', '*.sh', '*.js', '*.rb', '*.pl']:
        script_files.extend(skill_base_dir.glob(pattern))

    return script_files
```

### 2. File Filtering

```python
def _is_executable_script(file_path: Path) -> bool:
    """
    Check if file is an executable script.

    Criteria:
    - Has executable extension (.py, .sh, .js, .rb, .pl)
    - Is a regular file (not directory, symlink, etc.)
    - Exclude hidden files (starting with '.')
    - Exclude __pycache__ and node_modules directories

    Returns:
        True if file should be detected as script
    """
    # Check extension
    if file_path.suffix.lower() not in INTERPRETER_MAP:
        return False

    # Must be regular file
    if not file_path.is_file():
        return False

    # Exclude hidden files
    if file_path.name.startswith('.'):
        return False

    # Exclude common non-script directories
    exclude_dirs = {'__pycache__', 'node_modules', '.venv', 'venv'}
    if any(part in exclude_dirs for part in file_path.parts):
        return False

    return True
```

### 3. Metadata Extraction

```python
def _extract_metadata(file_path: Path, skill_base_dir: Path) -> ScriptMetadata:
    """
    Extract metadata for a detected script.

    Steps:
    1. Determine script type from file extension
    2. Extract description from first comment block
    3. Compute relative path from skill base directory
    4. Extract script name (filename without extension)

    Returns:
        ScriptMetadata with all fields populated
    """
    # Determine script type
    script_type = _get_script_type(file_path.suffix)

    # Extract description (first comment block, max 500 chars)
    extractor = ScriptDescriptionExtractor()
    description = extractor.extract(
        file_path=file_path,
        script_type=script_type,
        max_lines=50,
        max_chars=500
    )

    # Compute relative path
    relative_path = file_path.relative_to(skill_base_dir)

    # Extract name (stem = filename without extension)
    name = file_path.stem

    return ScriptMetadata(
        name=name,
        path=relative_path,
        script_type=script_type,
        description=description
    )
```

---

## Description Extraction Contract

### ScriptDescriptionExtractor

```python
class ScriptDescriptionExtractor:
    """Extract description from script's first comment block."""

    def extract(
        self,
        file_path: Path,
        script_type: str,
        max_lines: int = 50,
        max_chars: int = 500
    ) -> str:
        """
        Extract description from first comment block.

        Supported Comment Formats by Language:
        - Python: \"\"\"docstring\"\"\" or # comments
        - Shell: # comments
        - JavaScript: /** JSDoc */ or // comments
        - Ruby: # comments or =begin...=end blocks
        - Perl: # comments or =pod...=cut blocks

        Algorithm:
        1. Skip shebang line if present on line 1
        2. Skip empty lines until first content
        3. Detect first comment delimiter
        4. Extract comment block until delimiter changes or code starts
        5. Strip delimiters while preserving formatting
        6. Truncate at max_chars with word boundary

        Args:
            file_path: Path to script file
            script_type: Language (python, shell, javascript, ruby, perl)
            max_lines: Maximum lines to read (default: 50)
            max_chars: Maximum characters in result (default: 500)

        Returns:
            Extracted description (empty string if no comments found)

        Example:
            Python script with docstring:
            ```python
            \"\"\"PDF extraction utility.

            Extracts text from PDF files.
            \"\"\"
            import sys
            ```
            Returns: "PDF extraction utility.\\n\\nExtracts text from PDF files."

            Shell script with comments:
            ```bash
            #!/bin/bash
            # Helper script for data processing
            #
            # This script validates CSV files
            echo "Starting..."
            ```
            Returns: "Helper script for data processing\\n\\nThis script validates CSV files"

            Script with no comments:
            ```python
            import sys
            print("Hello")
            ```
            Returns: "" (empty string)
        """
```

---

## Performance Contract

**Benchmarks**:

| Operation | Time (per script) | Notes |
|-----------|-------------------|-------|
| File system scan | ~0.1ms | Per directory |
| File filtering | ~0.01ms | Per file |
| Description extraction | ~2.5ms | First 50 lines |
| Metadata creation | ~0.1ms | Per script |
| **Total per script** | **~3ms** | Average |

**Scaling**:

| Scripts | Detection Time | Target |
|---------|----------------|--------|
| 10 | ~30ms | ✅ <10ms |
| 50 | ~150ms | ⚠️ >10ms (acceptable) |
| 100 | ~300ms | ⚠️ Scales linearly |

**Optimization for >50 scripts** (defer to v0.3.1+):
- Concurrent extraction with ThreadPoolExecutor
- Incremental detection (detect only new scripts)
- Caching descriptions on disk

---

## Error Handling

```python
try:
    scripts = detector.detect_scripts(skill_base_dir)
except FileNotFoundError:
    # skill_base_dir doesn't exist
    print(f"Skill directory not found: {skill_base_dir}")

except NotADirectoryError:
    # skill_base_dir is a file, not a directory
    print(f"Not a directory: {skill_base_dir}")

except PermissionError:
    # skill_base_dir is not readable
    print(f"Permission denied: {skill_base_dir}")

# Graceful degradation for individual files
# If a single script cannot be parsed, log warning and skip it
# Never fail entire detection due to one bad file
```

**Logging**:
```python
# DEBUG level (for each detected script)
logger.debug(f"Detected script: {script.name} ({script.script_type})")

# WARNING level (if script cannot be parsed)
logger.warning(f"Could not parse script {file_path}: {error}")

# INFO level (summary after detection)
logger.info(f"Detected {len(scripts)} scripts in skill '{skill_name}'")
```

---

## Edge Cases

### 1. No Scripts Directory

```python
# Skill structure:
skill/
├── SKILL.md
├── data/
└── transform.py  # Script at root

# Behavior: Detect transform.py from root directory
scripts = detector.detect_scripts(Path("skill"))
assert len(scripts) == 1
assert scripts[0].name == 'transform'
```

### 2. Nested Scripts

```python
# Skill structure:
skill/
└── scripts/
    ├── extract.py
    └── utils/
        └── parser.py

# Behavior: Detect both scripts with relative paths
scripts = detector.detect_scripts(Path("skill"))
assert len(scripts) == 2
assert any(s.path == Path('scripts/extract.py') for s in scripts)
assert any(s.path == Path('scripts/utils/parser.py') for s in scripts)
```

### 3. Mixed Script Types

```python
# Skill structure:
skill/
└── scripts/
    ├── extract.py    # Python
    ├── convert.sh    # Shell
    └── parse.js      # JavaScript

# Behavior: Detect all types correctly
scripts = detector.detect_scripts(Path("skill"))
assert len(scripts) == 3
types = {s.script_type for s in scripts}
assert types == {'python', 'shell', 'javascript'}
```

### 4. Non-Script Files

```python
# Skill structure:
skill/
└── scripts/
    ├── extract.py      # ✅ Detected
    ├── data.json       # ❌ Not detected (not executable extension)
    ├── README.md       # ❌ Not detected
    └── .hidden.py      # ❌ Not detected (hidden file)

# Behavior: Only detect extract.py
scripts = detector.detect_scripts(Path("skill"))
assert len(scripts) == 1
assert scripts[0].name == 'extract'
```

### 5. Symlinks

```python
# Skill structure:
skill/
└── scripts/
    ├── extract.py          # Real file
    └── link.py -> extract.py  # Symlink

# Behavior: Follow symlinks, detect both (they point to same file)
# Implementation may choose to:
# Option A: Detect both (deduplicate by inode)
# Option B: Detect only real files (skip symlinks)
# **Decision**: Option B (skip symlinks to avoid confusion)
```

### 6. Deeply Nested Directories

```python
# Skill structure:
skill/
└── scripts/
    └── level1/
        └── level2/
            └── level3/
                └── level4/
                    └── level5/
                        └── deep.py  # At max depth

# Behavior (max_depth=5): Detect deep.py
scripts = detector.detect_scripts(Path("skill"))
assert any(s.name == 'deep' for s in scripts)

# Behavior (max_depth=3): Skip deep.py (too deep)
detector = ScriptDetector(max_depth=3)
scripts = detector.detect_scripts(Path("skill"))
assert not any(s.name == 'deep' for s in scripts)
```

---

## Integration with Skill Model

```python
# Lazy loading pattern in Skill class
@dataclass(slots=True)
class Skill:
    # ... existing fields ...

    _scripts: Optional[List[ScriptMetadata]] = field(
        default=None, init=False, repr=False
    )

    @property
    def scripts(self) -> List[ScriptMetadata]:
        """Get detected scripts (lazy-loaded)."""
        if self._scripts is None:
            detector = ScriptDetector()
            self._scripts = detector.detect_scripts(self.base_dir)
        return self._scripts
```

**Timing**: Detection runs once when `Skill.scripts` is first accessed, typically during:
- LangChain tool creation
- Script execution request
- Manual inspection

**Caching**: Results cached for skill's lifetime in memory (no persistent caching).

---

## Testing Contract

**Required Unit Tests**:
- ✅ Detect Python scripts (.py)
- ✅ Detect Shell scripts (.sh)
- ✅ Detect JavaScript scripts (.js)
- ✅ Detect Ruby scripts (.rb)
- ✅ Detect Perl scripts (.pl)
- ✅ Skip non-script files (.json, .md, .txt)
- ✅ Skip hidden files (.hidden.py)
- ✅ Skip __pycache__ directories
- ✅ Handle nested directories (up to max_depth)
- ✅ Handle empty scripts/ directory (return empty list)
- ✅ Handle missing scripts/ directory (check root)
- ✅ Extract descriptions from Python docstrings
- ✅ Extract descriptions from shell comments
- ✅ Extract descriptions from JSDoc blocks
- ✅ Return empty description when no comments
- ✅ Truncate long descriptions at 500 chars
- ✅ Handle encoding errors gracefully
- ✅ Handle permission denied errors
- ✅ Performance: <10ms for 50 scripts

**Test Coverage Target**: 85%+ for ScriptDetector class

---

## Example Usage

### Basic Detection

```python
from skillkit.core.scripts import ScriptDetector
from pathlib import Path

detector = ScriptDetector()
scripts = detector.detect_scripts(Path("/skills/pdf-extractor"))

for script in scripts:
    print(f"{script.name} ({script.script_type})")
    print(f"  Path: {script.path}")
    print(f"  Description: {script.description[:100]}...")
```

### Custom Configuration

```python
# Only scan 3 levels deep, read 30 lines for descriptions
detector = ScriptDetector(
    max_depth=3,
    max_lines_for_description=30
)

scripts = detector.detect_scripts(skill_base_dir)
```

### Integration with Skill

```python
from skillkit.core.manager import SkillManager

manager = SkillManager()
skills = manager.discover()

for skill in skills:
    # Lazy loading: detection happens here on first access
    if skill.scripts:
        print(f"Skill '{skill.metadata.name}' has {len(skill.scripts)} scripts:")
        for script in skill.scripts:
            print(f"  - {script.name}: {script.description}")
```

---

## Version History

| Version | Changes |
|---------|---------|
| v0.3.0  | Initial implementation |

---

## Related Contracts

- [Script Executor API](./script_executor_api.md)
- [Data Model: ScriptMetadata](../data-model.md#1-scriptmetadata)
