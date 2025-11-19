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

import json
import logging
import os
import shutil
import signal as signal_module
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from skillkit.core.models import SkillMetadata

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

    signal: str | None = None
    """Signal name if script was terminated by signal (Unix only).

    Examples: 'SIGSEGV', 'SIGKILL', 'SIGTERM', 'SIGINT'
    None if script exited normally.
    """

    signal_number: int | None = None
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
            with open(script_path, encoding='utf-8', errors='replace') as f:
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
    ) -> ScriptMetadata | None:
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

    def _validate_script_path(self, script_path: Path, skill_base_dir: Path) -> Path:
        """Validate script path and prevent path traversal attacks.

        Args:
            script_path: Path to the script (can be relative or absolute)
            skill_base_dir: Base directory of the skill

        Returns:
            Resolved absolute path to the script

        Raises:
            PathSecurityError: If path escapes skill directory or is invalid
            FileNotFoundError: If script doesn't exist

        Security:
            - Uses os.path.realpath() to resolve symlinks
            - Uses os.path.commonpath() to verify paths stay within skill directory
            - Rejects paths pointing outside skill base directory
            - Validates symlinks don't point outside skill directory
        """
        from skillkit.core.exceptions import PathSecurityError

        # Ensure skill_base_dir is absolute
        skill_base_dir = Path(os.path.realpath(skill_base_dir))

        # Convert to absolute path if relative
        if not script_path.is_absolute():
            script_path = skill_base_dir / script_path

        # Check if path is a symlink BEFORE resolving
        is_symlink = script_path.is_symlink()

        # Resolve to canonical path (follows symlinks)
        try:
            resolved_path = Path(os.path.realpath(script_path))
        except (OSError, RuntimeError) as e:
            logger.error(
                f"Security violation: Invalid script path or symlink loop detected - "
                f"path={script_path}, skill_base_dir={skill_base_dir}"
            )
            raise PathSecurityError(
                f"Invalid script path or symlink loop: {script_path}"
            ) from e

        # Verify path stays within skill_base_dir
        try:
            common = Path(os.path.commonpath([str(skill_base_dir), str(resolved_path)]))
        except ValueError as e:
            # Paths on different drives (Windows)
            logger.error(
                f"Security violation: Script path on different drive - "
                f"path={script_path}, skill_base_dir={skill_base_dir}"
            )
            raise PathSecurityError(
                f"Script path on different drive: {script_path}"
            ) from e

        if common != skill_base_dir:
            logger.error(
                f"Security violation: Path traversal attempt detected - "
                f"path={script_path}, resolved={resolved_path}, skill_base_dir={skill_base_dir}"
            )
            raise PathSecurityError(
                f"Script path escapes skill directory: {script_path} -> {resolved_path}"
            )

        # Additional check: resolved path must start with skill_base_dir
        if not str(resolved_path).startswith(str(skill_base_dir) + os.sep):
            logger.error(
                f"Security violation: Script path outside skill directory - "
                f"path={script_path}, resolved={resolved_path}, skill_base_dir={skill_base_dir}"
            )
            raise PathSecurityError(
                f"Script path outside skill directory: {resolved_path}"
            )

        # If it was a symlink, verify the target is also within skill directory
        if is_symlink:
            # Extra validation: symlink target must be within skill directory
            if not str(resolved_path).startswith(str(skill_base_dir)):
                logger.error(
                    f"Security violation: Symlink points outside skill directory - "
                    f"symlink={script_path}, target={resolved_path}, skill_base_dir={skill_base_dir}"
                )
                raise PathSecurityError(
                    f"Symlink points outside skill directory: {script_path} -> {resolved_path}"
                )

        # Verify file exists and is a regular file
        if not resolved_path.is_file():
            raise FileNotFoundError(f"Script not found: {resolved_path}")

        return resolved_path

    def _check_permissions(self, script_path: Path) -> None:
        """Check script permissions and reject dangerous configurations.

        Args:
            script_path: Absolute path to the script

        Raises:
            ScriptPermissionError: If script has setuid/setgid bits

        Security:
            - Rejects scripts with setuid bit (Unix-only)
            - Rejects scripts with setgid bit (Unix-only)
            - Skips checks on Windows (no setuid/setgid)
        """
        import stat

        from skillkit.core.exceptions import ScriptPermissionError

        # Skip permission checks on Windows
        if os.name == 'nt':
            return

        # Get file status
        file_stat = script_path.stat()
        mode = file_stat.st_mode

        # Check for setuid bit
        has_setuid = bool(mode & stat.S_ISUID)

        # Check for setgid bit
        has_setgid = bool(mode & stat.S_ISGID)

        # Reject scripts with dangerous permissions
        if has_setuid or has_setgid:
            logger.error(
                f"Security violation: Script has dangerous permissions - "
                f"path={script_path}, mode={oct(mode)}, setuid={has_setuid}, setgid={has_setgid}"
            )
            raise ScriptPermissionError(
                f"Script has dangerous permissions: {script_path}\n"
                f"  Mode: {oct(mode)}\n"
                f"  Setuid: {has_setuid}\n"
                f"  Setgid: {has_setgid}\n"
                f"  Recommendation: Remove dangerous bits with 'chmod u-s,g-s {script_path}'"
            )

    def _resolve_interpreter(self, script_path: Path) -> str:
        """Resolve interpreter for script execution.

        Args:
            script_path: Path to the script

        Returns:
            Interpreter command name (e.g., 'python3', 'bash')

        Raises:
            InterpreterNotFoundError: If required interpreter not found in PATH

        Strategy:
            1. Map file extension to interpreter using INTERPRETER_MAP
            2. Validate interpreter exists in PATH using shutil.which()
            3. Raise error if interpreter not found
        """
        from skillkit.core.exceptions import InterpreterNotFoundError

        # Get interpreter from extension
        ext = script_path.suffix.lower()
        interpreter = INTERPRETER_MAP.get(ext)

        if not interpreter:
            raise InterpreterNotFoundError(
                f"No interpreter mapping for extension: {ext}"
            )

        # Verify interpreter exists in PATH
        if not shutil.which(interpreter):
            raise InterpreterNotFoundError(
                f"Interpreter '{interpreter}' not found in PATH for {script_path.name}"
            )

        return interpreter

    def _serialize_arguments(self, arguments: ScriptArguments) -> str:
        """Serialize arguments to JSON for stdin.

        Args:
            arguments: Arguments dictionary

        Returns:
            JSON string

        Raises:
            ArgumentSerializationError: If arguments cannot be serialized
            ArgumentSizeError: If serialized arguments exceed 10MB
        """
        from skillkit.core.exceptions import ArgumentSerializationError, ArgumentSizeError

        try:
            serialized = json.dumps(arguments, ensure_ascii=False, indent=None)
        except (TypeError, ValueError) as e:
            raise ArgumentSerializationError(
                f"Cannot serialize arguments to JSON: {e}"
            ) from e

        # Check size limit (10MB)
        size_bytes = len(serialized.encode('utf-8'))
        if size_bytes > 10_000_000:
            raise ArgumentSizeError(
                f"Arguments too large: {size_bytes} bytes (max 10MB)"
            )

        return serialized

    def _build_environment(
        self,
        skill_metadata: "SkillMetadata",
        skill_base_dir: Path
    ) -> ScriptEnvironment:
        """Build environment variables for script execution.

        Args:
            skill_metadata: SkillMetadata instance
            skill_base_dir: Base directory of the skill

        Returns:
            Environment variables dict

        Injects:
            - SKILL_NAME: Name of the skill
            - SKILL_BASE_DIR: Absolute path to skill directory
            - SKILL_VERSION: Version from metadata (if available)
            - SKILLKIT_VERSION: Current skillkit version
        """
        import skillkit

        env = os.environ.copy()

        # Inject skill metadata
        env['SKILL_NAME'] = skill_metadata.name
        env['SKILL_BASE_DIR'] = str(skill_base_dir)
        env['SKILLKIT_VERSION'] = skillkit.__version__

        # Add version if available
        if hasattr(skill_metadata, 'version') and skill_metadata.version:
            env['SKILL_VERSION'] = skill_metadata.version
        else:
            env['SKILL_VERSION'] = '0.0.0'

        return env

    def _execute_subprocess(
        self,
        interpreter: str,
        script_path: Path,
        arguments_json: str,
        env: ScriptEnvironment,
        skill_base_dir: Path
    ) -> tuple[int, str, str, str | None, int | None]:
        """Execute script as subprocess.

        Args:
            interpreter: Interpreter command (e.g., 'python3')
            script_path: Absolute path to script
            arguments_json: JSON-serialized arguments
            env: Environment variables
            skill_base_dir: Working directory for execution

        Returns:
            Tuple of (exit_code, stdout, stderr, signal_name, signal_number)

        Security:
            - Uses shell=False (command injection prevention)
            - Uses list-based arguments (no shell interpretation)
            - Enforces timeout
        """
        try:
            result = subprocess.run(
                [interpreter, str(script_path)],
                input=arguments_json,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(skill_base_dir),
                shell=False,  # CRITICAL: Never use shell=True
                check=False,
                env=env
            )

            # Detect signal-based termination (Unix only)
            signal_name = None
            signal_number = None

            if result.returncode < 0:
                signal_number = -result.returncode
                try:
                    signal_name = signal_module.Signals(signal_number).name
                except ValueError:
                    signal_name = f"UNKNOWN_SIGNAL_{signal_number}"

            return (
                result.returncode,
                result.stdout,
                result.stderr,
                signal_name,
                signal_number
            )

        except subprocess.TimeoutExpired as e:
            # Log timeout warning
            logger.warning(
                f"Script execution timed out after {self.timeout}s - "
                f"script={script_path.name}, timeout={self.timeout}s"
            )

            # Return timeout indication
            stdout = e.stdout.decode('utf-8', errors='replace') if e.stdout else ''
            stderr = e.stderr.decode('utf-8', errors='replace') if e.stderr else ''

            return (
                124,  # Conventional timeout exit code
                stdout,
                stderr + '\nTimeout',
                None,
                None
            )

    def _handle_output_truncation(
        self,
        stdout: str,
        stderr: str
    ) -> tuple[str, str, bool, bool]:
        """Truncate output if it exceeds size limits.

        Args:
            stdout: Standard output
            stderr: Standard error

        Returns:
            Tuple of (stdout, stderr, stdout_truncated, stderr_truncated)
        """
        stdout_truncated = False
        stderr_truncated = False

        # Truncate stdout if needed
        if len(stdout.encode('utf-8')) > self.max_output_size:
            # Truncate to max_output_size bytes
            truncated_stdout = stdout.encode('utf-8')[:self.max_output_size].decode('utf-8', errors='ignore')
            stdout = truncated_stdout + '\n[... OUTPUT TRUNCATED: exceeded 10MB limit ...]'
            stdout_truncated = True

        # Truncate stderr if needed
        if len(stderr.encode('utf-8')) > self.max_output_size:
            truncated_stderr = stderr.encode('utf-8')[:self.max_output_size].decode('utf-8', errors='ignore')
            stderr = truncated_stderr + '\n[... STDERR TRUNCATED: exceeded 10MB limit ...]'
            stderr_truncated = True

        return stdout, stderr, stdout_truncated, stderr_truncated

    def _detect_signal(
        self,
        signal_name: str | None,
        signal_number: int | None
    ) -> tuple[str | None, int | None]:
        """Detect signal information from subprocess.

        Args:
            signal_name: Signal name from subprocess (if any)
            signal_number: Signal number from subprocess (if any)

        Returns:
            Tuple of (signal_name, signal_number)
        """
        # If already detected by subprocess, return as-is
        if signal_name is not None:
            return signal_name, signal_number

        # No signal detected
        return None, None

    def execute(
        self,
        script_path: Path,
        arguments: ScriptArguments,
        skill_base_dir: Path,
        skill_metadata: "SkillMetadata"
    ) -> ScriptExecutionResult:
        """Execute a script with security controls.

        Args:
            script_path: Path to the script (relative or absolute)
            arguments: Arguments to pass as JSON via stdin
            skill_base_dir: Base directory of the skill
            skill_metadata: SkillMetadata instance

        Returns:
            ScriptExecutionResult with execution details

        Raises:
            PathSecurityError: If path validation fails
            ScriptPermissionError: If script has dangerous permissions
            InterpreterNotFoundError: If interpreter not found
            ArgumentSerializationError: If arguments cannot be serialized
            ArgumentSizeError: If arguments too large

        Example:
            >>> executor = ScriptExecutor(timeout=30)
            >>> result = executor.execute(
            ...     script_path=Path('scripts/extract.py'),
            ...     arguments={'file': 'document.pdf'},
            ...     skill_base_dir=Path('/path/to/skill'),
            ...     skill_metadata=skill.metadata
            ... )
            >>> if result.success:
            ...     print(result.stdout)
        """
        # Start timing
        start_time = time.perf_counter()

        # Validate and resolve script path
        validated_path = self._validate_script_path(script_path, skill_base_dir)

        # Check permissions
        self._check_permissions(validated_path)

        # Resolve interpreter
        interpreter = self._resolve_interpreter(validated_path)

        # Serialize arguments
        arguments_json = self._serialize_arguments(arguments)

        # Build environment
        env = self._build_environment(skill_metadata, skill_base_dir)

        # Execute subprocess
        exit_code, stdout, stderr, signal_name, signal_number = self._execute_subprocess(
            interpreter,
            validated_path,
            arguments_json,
            env,
            skill_base_dir
        )

        # Handle output truncation
        stdout, stderr, stdout_truncated, stderr_truncated = self._handle_output_truncation(
            stdout,
            stderr
        )

        # Detect signal
        signal_name, signal_number = self._detect_signal(
            signal_name,
            signal_number
        )

        # Calculate execution time
        execution_time_ms = (time.perf_counter() - start_time) * 1000

        # Prepare audit log entry with arguments truncated to 256 chars
        arguments_str = str(arguments)[:256]
        if len(str(arguments)) > 256:
            arguments_str += '...'

        # Audit log entry (always logged for security compliance)
        import datetime
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        logger.info(
            f"AUDIT: Script execution - "
            f"timestamp={timestamp}, "
            f"skill={skill_metadata.name}, "
            f"script={validated_path.relative_to(skill_base_dir)}, "
            f"args={arguments_str}, "
            f"exit_code={exit_code}, "
            f"execution_time_ms={execution_time_ms:.1f}, "
            f"signal={signal_name}, "
            f"stdout_truncated={stdout_truncated}, "
            f"stderr_truncated={stderr_truncated}"
        )

        # Log execution details
        if exit_code == 0:
            logger.info(
                f"Script executed successfully: {validated_path.name} "
                f"(exit_code={exit_code}, time={execution_time_ms:.1f}ms)"
            )
        else:
            logger.error(
                f"Script execution failed: {validated_path.name} "
                f"(exit_code={exit_code}, time={execution_time_ms:.1f}ms)"
            )

        # Log truncation warnings
        if stdout_truncated:
            logger.warning(f"Script stdout truncated: {validated_path.name}")

        if stderr_truncated:
            logger.warning(f"Script stderr truncated: {validated_path.name}")

        # Return result
        return ScriptExecutionResult(
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            execution_time_ms=execution_time_ms,
            script_path=validated_path,
            signal=signal_name,
            signal_number=signal_number,
            stdout_truncated=stdout_truncated,
            stderr_truncated=stderr_truncated
        )
