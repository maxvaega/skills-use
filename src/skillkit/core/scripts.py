"""Script execution support for skills.

This module provides functionality for detecting, validating, and executing
scripts bundled with skills. Scripts enable deterministic operations like
data transformation, file processing, and system integrations.

Key Features:
    - Automatic script detection in skill directories
    - Security validation (path traversal, permissions, etc.)
    - Multiple script types (Python, Shell, JavaScript, Ruby, Perl)
    - Timeout enforcement and output capture
    - Environment context injection

Usage:
    # Detect scripts in a skill
    detector = ScriptDetector()
    scripts = detector.detect_scripts(skill_base_dir)

    # Execute a script
    executor = ScriptExecutor(timeout=30)
    result = executor.execute(script_path, arguments, skill_base_dir, skill_metadata)

Classes:
    ScriptMetadata: Metadata for a detected script
    ScriptExecutionResult: Result of script execution
    ScriptDescriptionExtractor: Extract descriptions from script comments
    ScriptDetector: Detect scripts in skill directories
    ScriptExecutor: Execute scripts with security controls

Constants:
    INTERPRETER_MAP: Mapping of file extensions to interpreters

Version:
    Added in v0.3.0
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional
import os
import re
import subprocess
import json
import shutil
import time
import signal as signal_module
import logging

# Type aliases for clarity
ScriptArguments = Dict[str, Any]
"""Arguments passed to scripts as JSON (free-form dict)."""

ScriptEnvironment = Dict[str, str]
"""Environment variables for script execution (str keys and values)."""

ScriptList = List["ScriptMetadata"]
"""List of detected scripts for a skill."""

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

# Configure module logger
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ScriptMetadata:
    """Metadata for a detected executable script.

    Created during lazy script detection (triggered on skill invocation).
    Stored in Skill object for the skill's lifetime in memory.

    Attributes:
        name: Script name (filename without extension)
        path: Relative path from skill base directory
        script_type: Script language/interpreter type
        description: Script description extracted from first comment block

    Example:
        >>> meta = ScriptMetadata(
        ...     name='extract',
        ...     path=Path('scripts/extract.py'),
        ...     script_type='python',
        ...     description='Extract text from PDF files'
        ... )
        >>> meta.get_fully_qualified_name('pdf-extractor')
        'pdf-extractor.extract'
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

    Extracted by parsing first comment block (#, //, \"\"\", etc.) up to 500 chars.
    Empty string if no comments found.
    """

    def get_fully_qualified_name(self, skill_name: str) -> str:
        """Get LangChain tool name for this script.

        Args:
            skill_name: Name of the parent skill

        Returns:
            Fully qualified tool name (e.g., 'pdf-extractor.extract')

        Example:
            >>> meta = ScriptMetadata('extract', Path('scripts/extract.py'), 'python', '')
            >>> meta.get_fully_qualified_name('pdf-extractor')
            'pdf-extractor.extract'
        """
        return f"{skill_name}.{self.name}"


@dataclass(frozen=True, slots=True)
class ScriptExecutionResult:
    """Result of executing a script with security controls.

    Returned by ScriptExecutor.execute() and SkillManager.execute_skill_script().
    Contains all captured output, exit status, timing, and error information.

    Attributes:
        stdout: Captured standard output (decoded as UTF-8)
        stderr: Captured standard error (decoded as UTF-8)
        exit_code: Process exit code
        execution_time_ms: Execution duration in milliseconds
        script_path: Absolute path to the executed script
        signal: Signal name if terminated by signal (Unix only)
        signal_number: Signal number if terminated by signal (Unix only)
        stdout_truncated: True if stdout was truncated due to size limit
        stderr_truncated: True if stderr was truncated due to size limit

    Properties:
        success: True if script exited successfully (exit_code == 0)
        timeout: True if script was killed due to timeout
        signaled: True if script was terminated by signal

    Example:
        >>> result = ScriptExecutionResult(
        ...     stdout='{"status": "success"}',
        ...     stderr='',
        ...     exit_code=0,
        ...     execution_time_ms=45.2,
        ...     script_path=Path('/path/to/script.py'),
        ...     signal=None,
        ...     signal_number=None,
        ...     stdout_truncated=False,
        ...     stderr_truncated=False
        ... )
        >>> result.success
        True
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

    signal: Optional[str] = None
    """Signal name if script was terminated by signal (Unix only).

    Examples: 'SIGSEGV', 'SIGKILL', 'SIGTERM', 'SIGINT'
    None if script exited normally.
    """

    signal_number: Optional[int] = None
    """Signal number if terminated by signal (Unix only).

    Examples: 11 (SIGSEGV), 9 (SIGKILL), 15 (SIGTERM)
    None if exited normally.
    Corresponds to negative exit_code (signal_number = -exit_code).
    """

    stdout_truncated: bool = False
    """True if stdout was truncated due to 10MB size limit."""

    stderr_truncated: bool = False
    """True if stderr was truncated due to 10MB size limit."""

    @property
    def success(self) -> bool:
        """True if script exited successfully (exit_code == 0).

        Example:
            >>> result = ScriptExecutionResult(..., exit_code=0, ...)
            >>> result.success
            True
        """
        return self.exit_code == 0

    @property
    def timeout(self) -> bool:
        """True if script was killed due to timeout.

        Example:
            >>> result = ScriptExecutionResult(..., exit_code=124, stderr='Timeout', ...)
            >>> result.timeout
            True
        """
        return self.exit_code == 124 and 'Timeout' in self.stderr

    @property
    def signaled(self) -> bool:
        """True if script was terminated by signal.

        Example:
            >>> result = ScriptExecutionResult(..., signal='SIGSEGV', ...)
            >>> result.signaled
            True
        """
        return self.signal is not None


def _get_script_type(file_path: Path) -> str:
    """Map file extension to script type.

    Args:
        file_path: Path to the script file

    Returns:
        Script type string (e.g., 'python', 'shell', 'javascript')

    Example:
        >>> _get_script_type(Path('script.py'))
        'python'
        >>> _get_script_type(Path('script.sh'))
        'shell'
    """
    ext = file_path.suffix.lower()
    mapping = {
        '.py': 'python',
        '.sh': 'shell',
        '.js': 'javascript',
        '.rb': 'ruby',
        '.pl': 'perl',
        '.bat': 'batch',
        '.cmd': 'batch',
        '.ps1': 'powershell',
    }
    return mapping.get(ext, 'unknown')


class ScriptDescriptionExtractor:
    """Extract script descriptions from first comment block.

    Supports multiple comment formats:
        - Python: Docstrings (\"\"\"...\"\"\") and # comments
        - Shell: # comments
        - JavaScript: // and /* */ comments, JSDoc
        - Ruby: # comments and =begin...=end
        - Perl: # comments and POD (=pod...=cut)

    Usage:
        extractor = ScriptDescriptionExtractor()
        description = extractor.extract(script_path, max_lines=50)

    Version:
        Added in v0.3.0
    """

    def __init__(self, max_chars: int = 500):
        """Initialize extractor with character limit.

        Args:
            max_chars: Maximum characters to extract (default: 500)
        """
        self.max_chars = max_chars

    def extract(self, script_path: Path, max_lines: int = 50) -> str:
        """Extract description from script file.

        Args:
            script_path: Path to the script file
            max_lines: Maximum lines to scan (default: 50)

        Returns:
            Extracted description (empty string if no comments found)

        Example:
            >>> extractor = ScriptDescriptionExtractor()
            >>> desc = extractor.extract(Path('script.py'))
            'This script processes data'
        """
        try:
            with open(script_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = [f.readline() for _ in range(max_lines)]

            script_type = _get_script_type(script_path)

            if script_type == 'python':
                return self._extract_python_docstring(lines)
            elif script_type in ('shell', 'ruby', 'perl'):
                return self._extract_hash_comments(lines)
            elif script_type == 'javascript':
                return self._extract_js_comments(lines)
            else:
                return ''

        except (OSError, UnicodeDecodeError):
            return ''

    def _extract_python_docstring(self, lines: List[str]) -> str:
        """Extract Python docstring or # comments."""
        # Skip shebang and empty lines
        start_idx = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('#!'):
                start_idx = i
                break

        # Check for docstring
        if start_idx < len(lines):
            first_line = lines[start_idx].strip()
            if first_line.startswith('"""') or first_line.startswith("'''"):
                quote = '"""' if first_line.startswith('"""') else "'''"
                docstring_lines = []

                # Single-line docstring
                if first_line.count(quote) >= 2:
                    return first_line.strip(quote).strip()[:self.max_chars]

                # Multi-line docstring
                for line in lines[start_idx + 1:]:
                    if quote in line:
                        docstring_lines.append(line.split(quote)[0])
                        break
                    docstring_lines.append(line)

                return ' '.join(line.strip() for line in docstring_lines).strip()[:self.max_chars]

        # Fallback to # comments
        return self._extract_hash_comments(lines)

    def _extract_hash_comments(self, lines: List[str]) -> str:
        """Extract description from # comment lines."""
        comments = []
        started = False

        for line in lines:
            stripped = line.strip()

            # Skip shebang
            if stripped.startswith('#!'):
                continue

            # Start collecting comments
            if stripped.startswith('#'):
                started = True
                comment = stripped.lstrip('#').strip()
                if comment:
                    comments.append(comment)
            elif started and stripped:
                # Stop at first non-comment, non-empty line
                break

        return ' '.join(comments)[:self.max_chars]

    def _extract_js_comments(self, lines: List[str]) -> str:
        """Extract description from JavaScript // or /* */ comments."""
        comments = []
        in_block = False

        for line in lines:
            stripped = line.strip()

            # Block comment start
            if '/*' in stripped:
                in_block = True
                comment = stripped.split('/*', 1)[1]
                if '*/' in comment:
                    comment = comment.split('*/')[0]
                    in_block = False
                comments.append(comment.strip())
                continue

            # Block comment end
            if in_block:
                if '*/' in stripped:
                    comment = stripped.split('*/')[0]
                    comments.append(comment.strip(' *'))
                    in_block = False
                else:
                    comments.append(stripped.strip(' *'))
                continue

            # Line comment
            if stripped.startswith('//'):
                comment = stripped.lstrip('/').strip()
                if comment:
                    comments.append(comment)
            elif stripped and not in_block:
                break

        return ' '.join(comments)[:self.max_chars]


class ScriptDetector:
    """Detect executable scripts in skill directories.

    Scans skill directories for executable scripts and extracts metadata.
    Detection happens lazily when accessing Skill.scripts property.

    Search Locations:
        - scripts/ directory (recursive up to max_depth)
        - Skill root directory (non-recursive)

    Supported Extensions:
        .py, .sh, .js, .rb, .pl, .bat, .cmd, .ps1

    Excluded:
        - Hidden files (starting with '.')
        - __pycache__, node_modules, .venv, venv directories
        - Symbolic links (to avoid confusion and duplicates)

    Usage:
        detector = ScriptDetector(max_depth=5)
        scripts = detector.detect_scripts(skill_base_dir)

    Version:
        Added in v0.3.0
    """

    def __init__(self, max_depth: int = 5, max_lines_for_description: int = 50):
        """Initialize script detector.

        Args:
            max_depth: Maximum directory nesting depth for recursive scan
            max_lines_for_description: Max lines to scan for description extraction
        """
        self.max_depth = max_depth
        self.max_lines_for_description = max_lines_for_description
        self.extractor = ScriptDescriptionExtractor()

    def detect_scripts(self, skill_base_dir: Path) -> ScriptList:
        """Detect all executable scripts in skill directory.

        Args:
            skill_base_dir: Base directory of the skill (absolute path)

        Returns:
            List of ScriptMetadata objects (may be empty if no scripts found)

        Example:
            >>> detector = ScriptDetector()
            >>> scripts = detector.detect_scripts(Path('/path/to/skill'))
            >>> len(scripts)
            3
        """
        start_time = time.perf_counter()
        scripts: List[ScriptMetadata] = []

        # Scan scripts/ directory (recursive)
        scripts_dir = skill_base_dir / 'scripts'
        if scripts_dir.exists() and scripts_dir.is_dir():
            scripts.extend(self._scan_directories(scripts_dir, skill_base_dir, depth=0))

        # Scan skill root (non-recursive)
        scripts.extend(self._scan_root_directory(skill_base_dir))

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"Detected {len(scripts)} scripts in skill (took {elapsed_ms:.1f}ms)"
        )

        return scripts

    def _scan_directories(
        self, directory: Path, skill_base_dir: Path, depth: int
    ) -> ScriptList:
        """Recursively scan directories for scripts.

        Args:
            directory: Directory to scan
            skill_base_dir: Base directory of the skill
            depth: Current recursion depth

        Returns:
            List of ScriptMetadata found in this directory and subdirectories
        """
        if depth >= self.max_depth:
            return []

        scripts: List[ScriptMetadata] = []

        try:
            for item in directory.iterdir():
                # Skip hidden files and directories
                if item.name.startswith('.'):
                    continue

                # Skip common cache directories
                if item.name in ('__pycache__', 'node_modules', '.venv', 'venv'):
                    continue

                # Recurse into subdirectories
                if item.is_dir() and not item.is_symlink():
                    scripts.extend(
                        self._scan_directories(item, skill_base_dir, depth + 1)
                    )

                # Process script files
                elif self._is_executable_script(item):
                    metadata = self._extract_metadata(item, skill_base_dir)
                    if metadata:
                        scripts.append(metadata)

        except (PermissionError, OSError) as e:
            logger.warning(f"Failed to scan directory {directory}: {e}")

        return scripts

    def _scan_root_directory(self, skill_base_dir: Path) -> ScriptList:
        """Scan skill root directory for scripts (non-recursive).

        Args:
            skill_base_dir: Base directory of the skill

        Returns:
            List of ScriptMetadata found in root directory
        """
        scripts: List[ScriptMetadata] = []

        try:
            for item in skill_base_dir.iterdir():
                # Skip hidden files and directories
                if item.name.startswith('.'):
                    continue

                # Skip directories (already scanned scripts/)
                if item.is_dir():
                    continue

                # Skip SKILL.md and other non-script files
                if item.name == 'SKILL.md' or item.suffix in ('.md', '.txt', '.json'):
                    continue

                # Process script files
                if self._is_executable_script(item):
                    metadata = self._extract_metadata(item, skill_base_dir)
                    if metadata:
                        scripts.append(metadata)

        except (PermissionError, OSError) as e:
            logger.warning(f"Failed to scan root directory {skill_base_dir}: {e}")

        return scripts

    def _is_executable_script(self, file_path: Path) -> bool:
        """Check if file is an executable script.

        Args:
            file_path: Path to check

        Returns:
            True if file is a supported script type, False otherwise
        """
        # Must be a regular file
        if not file_path.is_file():
            return False

        # Skip symlinks
        if file_path.is_symlink():
            return False

        # Check extension
        ext = file_path.suffix.lower()
        return ext in INTERPRETER_MAP

    def _extract_metadata(
        self, script_path: Path, skill_base_dir: Path
    ) -> Optional[ScriptMetadata]:
        """Extract metadata from a script file.

        Args:
            script_path: Absolute path to the script
            skill_base_dir: Base directory of the skill

        Returns:
            ScriptMetadata if extraction succeeds, None otherwise
        """
        try:
            # Get relative path
            relative_path = script_path.relative_to(skill_base_dir)

            # Extract description
            description = self.extractor.extract(
                script_path, max_lines=self.max_lines_for_description
            )

            return ScriptMetadata(
                name=script_path.stem,
                path=relative_path,
                script_type=_get_script_type(script_path),
                description=description,
            )

        except (ValueError, OSError) as e:
            logger.warning(f"Failed to extract metadata from {script_path}: {e}")
            return None


# ScriptExecutor class will be implemented in the next phase
# Placeholder for now to complete the module structure
class ScriptExecutor:
    """Execute scripts with security controls and timeout enforcement.

    Provides secure script execution with:
        - Path validation (traversal prevention)
        - Permission checks (setuid/setgid rejection)
        - Timeout enforcement
        - Output size limits
        - Environment variable injection
        - Tool restriction enforcement

    Usage:
        executor = ScriptExecutor(timeout=30, max_output_size=10_000_000)
        result = executor.execute(
            script_path=Path('scripts/extract.py'),
            arguments={'file': 'document.pdf'},
            skill_base_dir=Path('/path/to/skill'),
            skill_metadata=skill.metadata
        )

    Version:
        Added in v0.3.0
    """

    def __init__(
        self,
        timeout: int = 30,
        max_output_size: int = 10_000_000,
        use_cache: bool = False,
    ):
        """Initialize script executor.

        Args:
            timeout: Maximum execution time in seconds (default: 30)
            max_output_size: Maximum output size in bytes (default: 10MB)
            use_cache: Enable execution result caching (default: False)
        """
        self.timeout = timeout
        self.max_output_size = max_output_size
        self.use_cache = use_cache

    # Implementation will be added in Phase 3 (User Story 1)
