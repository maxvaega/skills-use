"""Exception hierarchy for skillkit library.

This module defines all custom exceptions used throughout the library,
following a hierarchical structure for granular error handling.
"""

from typing import List


class SkillsUseError(Exception):
    """Base exception for all skillkit errors.

    Usage: Catch this to handle any library error.
    """


class SkillParsingError(SkillsUseError):
    """Base exception for skill parsing errors."""


class InvalidYAMLError(SkillParsingError):
    """YAML syntax error in skill frontmatter.

    Attributes:
        line: Line number of error (if available)
        column: Column number of error (if available)
    """

    def __init__(
        self,
        message: str,
        line: int | None = None,
        column: int | None = None,
    ) -> None:
        """Initialize InvalidYAMLError with line/column details.

        Args:
            message: Error description
            line: Line number where error occurred
            column: Column number where error occurred
        """
        super().__init__(message)
        self.line = line
        self.column = column


class MissingRequiredFieldError(SkillParsingError):
    """Required field missing or empty in frontmatter.

    Attributes:
        field_name: Name of missing field
    """

    def __init__(self, message: str, field_name: str | None = None) -> None:
        """Initialize MissingRequiredFieldError with field name.

        Args:
            message: Error description
            field_name: Name of the missing field
        """
        super().__init__(message)
        self.field_name = field_name


class InvalidFrontmatterError(SkillParsingError):
    """Frontmatter structure invalid (missing delimiters, non-dict, etc.)."""


class SkillNotFoundError(SkillsUseError):
    """Skill name not found in registry."""


class SkillInvocationError(SkillsUseError):
    """Base exception for invocation errors."""


class ArgumentProcessingError(SkillInvocationError):
    """Argument substitution failed."""


class ContentLoadError(SkillInvocationError):
    """Failed to read skill content file."""


class SkillSecurityError(SkillsUseError):
    """Base exception for security-related errors."""


class SuspiciousInputError(SkillSecurityError):
    """Detected potentially malicious input patterns."""


class SizeLimitExceededError(SkillSecurityError):
    """Input exceeds size limits (1MB)."""


class PathSecurityError(SkillSecurityError):
    """Raised when path traversal or security violation is detected.

    This exception is raised when attempting to access files outside
    the allowed skill directory using path traversal attacks.

    Attributes:
        requested_path: The path that was requested
        base_directory: The base directory constraint
    """

    def __init__(
        self,
        message: str,
        requested_path: str | None = None,
        base_directory: str | None = None,
    ) -> None:
        """Initialize PathSecurityError with path details.

        Args:
            message: Error description
            requested_path: The path that triggered the security violation
            base_directory: The base directory that should constrain access
        """
        super().__init__(message)
        self.requested_path = requested_path
        self.base_directory = base_directory


class ConfigurationError(SkillsUseError):
    """Raised when SkillManager initialization configuration is invalid.

    This exception is raised when explicitly provided directory paths
    do not exist or are not valid directories. Note that default
    directory paths (./skills/, ./.claude/skills/) do NOT raise this
    error when missing - they are silently skipped.

    Attributes:
        parameter_name: Name of the parameter that failed validation
        invalid_path: The path that was provided but doesn't exist

    Example:
        # This raises ConfigurationError (explicit path doesn't exist)
        manager = SkillManager(project_skill_dir="/bad/path")

        # This does NOT raise error (default path missing is OK)
        manager = SkillManager()  # No error even if ./skills/ missing
    """

    def __init__(
        self,
        message: str,
        parameter_name: str | None = None,
        invalid_path: str | None = None,
    ) -> None:
        """Initialize ConfigurationError with configuration details.

        Args:
            message: Error description
            parameter_name: The parameter that failed validation
            invalid_path: The path that was invalid
        """
        super().__init__(message)
        self.parameter_name = parameter_name
        self.invalid_path = invalid_path


class AsyncStateError(SkillsUseError):
    """Raised when async/sync methods are mixed incorrectly.

    This exception prevents mixing synchronous and asynchronous
    initialization/invocation methods on the same SkillManager instance.

    Example:
        manager.discover()  # Sync init
        await manager.adiscover()  # ERROR: AsyncStateError
    """


class PluginError(SkillsUseError):
    """Base exception for plugin-related errors."""


class ManifestNotFoundError(PluginError):
    """Plugin manifest file not found at expected location.

    Expected location: <plugin-root>/.claude-plugin/plugin.json
    """


class ManifestParseError(PluginError):
    """Plugin manifest parsing failed (invalid JSON, encoding errors, etc.).

    Attributes:
        manifest_path: Path to the manifest file
        parse_error: The underlying parsing error
    """

    def __init__(
        self,
        message: str,
        manifest_path: str | None = None,
        parse_error: Exception | None = None,
    ) -> None:
        """Initialize ManifestParseError with parsing details.

        Args:
            message: Error description
            manifest_path: Path to the manifest file that failed to parse
            parse_error: The underlying exception from JSON parser
        """
        super().__init__(message)
        self.manifest_path = manifest_path
        self.parse_error = parse_error


class ManifestValidationError(PluginError):
    """Plugin manifest validation failed (missing fields, invalid format, etc.).

    Attributes:
        field_name: Name of the field that failed validation
        invalid_value: The value that failed validation
    """

    def __init__(
        self,
        message: str,
        field_name: str | None = None,
        invalid_value: str | None = None,
    ) -> None:
        """Initialize ManifestValidationError with validation details.

        Args:
            message: Error description
            field_name: The field that failed validation
            invalid_value: The value that failed validation
        """
        super().__init__(message)
        self.field_name = field_name
        self.invalid_value = invalid_value


class ScriptError(SkillsUseError):
    """Base exception for script-related errors.

    Version:
        Added in v0.3.0
    """


class InterpreterNotFoundError(ScriptError):
    """Raised when required interpreter is not available in PATH.

    This exception is raised when attempting to execute a script with
    an interpreter that cannot be found on the system.

    Attributes:
        interpreter: Name of the interpreter that was not found
        script_path: Path to the script that requires the interpreter

    Example:
        >>> raise InterpreterNotFoundError(
        ...     "Interpreter 'node' not found in PATH for script.js",
        ...     interpreter='node',
        ...     script_path='scripts/process.js'
        ... )
    """

    def __init__(
        self,
        message: str,
        interpreter: str | None = None,
        script_path: str | None = None,
    ) -> None:
        """Initialize InterpreterNotFoundError with details.

        Args:
            message: Error description
            interpreter: Name of the missing interpreter
            script_path: Path to the script
        """
        super().__init__(message)
        self.interpreter = interpreter
        self.script_path = script_path


class ScriptNotFoundError(ScriptError):
    """Raised when requested script doesn't exist in skill.

    This exception is raised when attempting to execute a script that
    cannot be found in the skill's detected scripts.

    Attributes:
        script_name: Name of the script that was requested
        skill_name: Name of the skill that was searched

    Example:
        >>> raise ScriptNotFoundError(
        ...     "Script 'extract' not found in skill 'pdf-extractor'",
        ...     script_name='extract',
        ...     skill_name='pdf-extractor'
        ... )
    """

    def __init__(
        self,
        message: str,
        script_name: str | None = None,
        skill_name: str | None = None,
    ) -> None:
        """Initialize ScriptNotFoundError with details.

        Args:
            message: Error description
            script_name: Name of the requested script
            skill_name: Name of the skill
        """
        super().__init__(message)
        self.script_name = script_name
        self.skill_name = skill_name


class ScriptPermissionError(ScriptError):
    """Raised when script has dangerous permissions (setuid/setgid).

    This exception is raised when a script has the setuid or setgid
    permission bits set, which could allow privilege escalation attacks.

    Attributes:
        script_path: Path to the script with dangerous permissions
        permission_mode: Octal permission mode of the script

    Example:
        >>> raise ScriptPermissionError(
        ...     "Script has setuid bit: scripts/dangerous.py",
        ...     script_path='scripts/dangerous.py',
        ...     permission_mode='0o104755'
        ... )
    """

    def __init__(
        self,
        message: str,
        script_path: str | None = None,
        permission_mode: str | None = None,
    ) -> None:
        """Initialize ScriptPermissionError with details.

        Args:
            message: Error description
            script_path: Path to the script
            permission_mode: Octal permission mode string
        """
        super().__init__(message)
        self.script_path = script_path
        self.permission_mode = permission_mode


class ArgumentSerializationError(ScriptError):
    """Raised when arguments cannot be serialized to JSON.

    This exception is raised when script arguments contain data that
    cannot be serialized to JSON (e.g., circular references, functions).

    Attributes:
        argument_data: The data that failed serialization (repr string)
        serialization_error: The underlying JSON serialization error

    Example:
        >>> raise ArgumentSerializationError(
        ...     "Cannot serialize arguments: circular reference detected",
        ...     argument_data="{'circular': {...}}",
        ...     serialization_error=ValueError("Circular reference")
        ... )
    """

    def __init__(
        self,
        message: str,
        argument_data: str | None = None,
        serialization_error: Exception | None = None,
    ) -> None:
        """Initialize ArgumentSerializationError with details.

        Args:
            message: Error description
            argument_data: String representation of the data
            serialization_error: The underlying exception
        """
        super().__init__(message)
        self.argument_data = argument_data
        self.serialization_error = serialization_error


class ArgumentSizeError(ScriptError):
    """Raised when JSON-serialized arguments exceed size limit.

    This exception is raised when serialized arguments exceed the
    maximum allowed size (10MB), which could cause memory exhaustion.

    Attributes:
        size_bytes: Size of the serialized arguments in bytes
        max_bytes: Maximum allowed size in bytes

    Example:
        >>> raise ArgumentSizeError(
        ...     "Arguments too large: 15728640 bytes (max 10MB)",
        ...     size_bytes=15728640,
        ...     max_bytes=10485760
        ... )
    """

    def __init__(
        self,
        message: str,
        size_bytes: int | None = None,
        max_bytes: int | None = None,
    ) -> None:
        """Initialize ArgumentSizeError with details.

        Args:
            message: Error description
            size_bytes: Actual size in bytes
            max_bytes: Maximum allowed size in bytes
        """
        super().__init__(message)
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes


class ToolRestrictionError(SkillSecurityError):
    """Raised when tool restrictions prevent script execution.

    This exception is raised when a skill's allowed-tools list does not
    include 'Bash', which is required for script execution.

    Attributes:
        skill_name: Name of the skill with tool restrictions
        allowed_tools: List of allowed tools (may be empty)

    Example:
        >>> raise ToolRestrictionError(
        ...     "Script execution requires 'Bash' in allowed-tools",
        ...     skill_name='pdf-extractor',
        ...     allowed_tools=['Read', 'Write']
        ... )
    """

    def __init__(
        self,
        message: str,
        skill_name: str | None = None,
        allowed_tools: List[str] | None = None,
    ) -> None:
        """Initialize ToolRestrictionError with details.

        Args:
            message: Error description
            skill_name: Name of the skill
            allowed_tools: List of allowed tools
        """
        super().__init__(message)
        self.skill_name = skill_name
        self.allowed_tools = allowed_tools or []
