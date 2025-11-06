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
