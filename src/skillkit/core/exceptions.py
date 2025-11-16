"""Exception hierarchy for skillkit library.

This module defines all custom exceptions used throughout the library,
following a hierarchical structure for granular error handling.
"""


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
