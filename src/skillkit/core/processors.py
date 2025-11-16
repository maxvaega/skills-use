"""Content processing strategies for skill invocation.

This module provides pluggable content processing via the Strategy pattern,
enabling composition of processing steps (base directory injection, argument
substitution, future extensions).
"""

import logging
import re
import sys
from abc import ABC, abstractmethod
from string import Template
from typing import Any, Dict, List

from skillkit.core.exceptions import (
    ArgumentProcessingError,
    SizeLimitExceededError,
)

logger = logging.getLogger(__name__)


class ContentProcessor(ABC):
    """Abstract base for content processing strategies."""

    @abstractmethod
    def process(self, content: str, context: Dict[str, Any]) -> str:
        """Process content with given context.

        Args:
            content: Raw skill content
            context: Processing context (arguments, base_directory, skill_name)

        Returns:
            Processed content

        Raises:
            Various processing-specific exceptions
        """
        pass


class BaseDirectoryProcessor(ContentProcessor):
    """Injects base directory context and file path resolution helper at beginning of content."""

    def process(self, content: str, context: Dict[str, Any]) -> str:
        """Inject base directory and file path resolution helper at beginning of content.

        Args:
            content: Raw skill content
            context: Processing context (must contain 'base_directory' key)

        Returns:
            Content with base directory and file resolution helper prepended

        Example:
            >>> processor = BaseDirectoryProcessor()
            >>> context = {"base_directory": "/home/user/.claude/skills/my-skill"}
            >>> result = processor.process("# My Skill", context)
            >>> print(result)
            Base directory for this skill: /home/user/.claude/skills/my-skill

            Supporting files can be referenced using relative paths from this base directory.
            Use FilePathResolver.resolve_path(base_dir, relative_path) to securely access files.

            # My Skill
        """
        base_dir = context.get("base_directory", "")

        # Build header with base directory and file resolution helper
        header = f"Base directory for this skill: {base_dir}\n\n"
        header += (
            "Supporting files can be referenced using relative paths from this base directory.\n"
        )
        header += "Use FilePathResolver.resolve_path(base_dir, relative_path) to securely access files.\n\n"

        return f"{header}{content}"


class ArgumentSubstitutionProcessor(ContentProcessor):
    """Handles $ARGUMENTS placeholder using string.Template.

    Security features:
    - string.Template prevents attribute access vulnerabilities
    - $$ARGUMENTS escaping for literal text
    - 1MB size limit on arguments
    - Suspicious pattern detection (9 patterns including XSS, YAML injection)
    """

    PLACEHOLDER_NAME = "ARGUMENTS"
    MAX_ARGUMENT_LENGTH = 1_000_000  # 1MB

    # Suspicious patterns (defense-in-depth, logged but not blocked)
    SUSPICIOUS_PATTERNS = [
        (r"\.\./", "Path traversal (../)"),
        (r"\.\.\\", "Path traversal (..\\)"),
        (r";\s*(?:rm|del|format|mkfs)", "Command injection attempt"),
        (r"<script", "Potential XSS"),
        (r"javascript:", "JavaScript protocol"),
        (r"!!python", "YAML code execution tag"),
        (r"\$\{.*\}", "Shell variable expansion"),
        (r"`.*`", "Backtick command execution"),
        (r"\|.*(?:sh|bash|cmd)", "Pipe to shell"),
    ]

    # Common typo patterns (lowercase, titlecase, plural, spacing)
    TYPO_PATTERNS = [
        r"\$arguments\b",  # lowercase
        r"\$Arguments\b",  # titlecase
        r"\$ARGUMENT\b",  # singular
        r"\$ ARGUMENTS\b",  # space after $
        r"\$\{ARGUMENTS\}",  # shell-style
    ]

    def process(self, content: str, context: Dict[str, Any]) -> str:
        """Replace $ARGUMENTS placeholders with actual arguments.

        Args:
            content: Skill content (may contain $ARGUMENTS or $$ARGUMENTS)
            context: Processing context (must contain 'arguments' key)

        Returns:
            Content with $ARGUMENTS replaced, $$ARGUMENTS preserved as $ARGUMENTS

        Raises:
            SizeLimitExceededError: If arguments exceed 1MB
            ArgumentProcessingError: If substitution fails

        Processing Rules:
            - $ARGUMENTS → replaced with arguments
            - $$ARGUMENTS → remains as literal $ARGUMENTS
            - No placeholder + no arguments → content unchanged
            - No placeholder + arguments → arguments appended

        Example:
            >>> processor = ArgumentSubstitutionProcessor()
            >>> context = {"arguments": "review main.py"}
            >>> result = processor.process("Task: $ARGUMENTS", context)
            >>> print(result)
            Task: review main.py

            >>> result = processor.process("Literal: $$ARGUMENTS", context)
            >>> print(result)
            Literal: $ARGUMENTS
        """
        arguments = context.get("arguments", "")

        # Validate argument size
        if len(arguments.encode("utf-8")) > self.MAX_ARGUMENT_LENGTH:
            raise SizeLimitExceededError(
                f"Arguments exceed maximum size of {self.MAX_ARGUMENT_LENGTH} bytes"
            )

        # Detect suspicious patterns (defense-in-depth, log warnings)
        self._check_suspicious_patterns(arguments, context.get("skill_name", "unknown"))

        # Detect common typos in content
        self._check_for_typos(content)

        # Check if placeholder exists
        has_placeholder = self._has_placeholder(content)

        if not has_placeholder and arguments:
            # No placeholder but arguments provided → append
            logger.debug("No $ARGUMENTS placeholder found, appending arguments to end")
            return f"{content}\n\n{arguments}"

        if not has_placeholder:
            # No placeholder and no arguments → return unchanged
            return content

        # Perform substitution using string.Template
        try:
            template = Template(content)
            return template.safe_substitute({self.PLACEHOLDER_NAME: arguments})
        except Exception as e:
            raise ArgumentProcessingError(f"Failed to substitute $ARGUMENTS: {e}") from e

    def _has_placeholder(self, content: str) -> bool:
        """Check if content contains unescaped $ARGUMENTS placeholder.

        Args:
            content: Content to check

        Returns:
            True if $ARGUMENTS (not $$ARGUMENTS) found
        """
        # Get all identifiers from template
        identifiers = self._get_identifiers(content)
        return self.PLACEHOLDER_NAME in identifiers

    def _get_identifiers(self, content: str) -> set[str]:
        """Extract placeholder identifiers from template.

        Uses string.Template.get_identifiers() on Python 3.11+,
        falls back to regex pattern matching on earlier versions.

        Args:
            content: Content to analyze

        Returns:
            Set of identifier names (e.g., {"ARGUMENTS"})
        """
        template = Template(content)

        # Python 3.11+ has get_identifiers() method
        if sys.version_info >= (3, 11):
            return set(template.get_identifiers())
        else:
            # Fallback: manual pattern matching
            # Match $identifier or ${identifier}, excluding $$
            pattern = r"(?<!\$)\$(?:(\w+)|\{(\w+)\})"
            matches = re.findall(pattern, content)
            # matches is list of tuples, flatten and remove empty strings
            return {m for match in matches for m in match if m}

    def _check_suspicious_patterns(self, arguments: str, skill_name: str) -> None:
        """Check arguments for suspicious patterns (defense-in-depth).

        Logs warnings but does not block execution (decision: log only).

        Args:
            arguments: User-provided arguments
            skill_name: Name of skill being invoked (for logging)
        """
        for pattern, description in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, arguments, re.IGNORECASE):
                logger.warning(
                    f"Suspicious pattern detected in arguments for skill '{skill_name}': {description}"
                )

    def _check_for_typos(self, content: str) -> None:
        """Check content for common $ARGUMENTS typos.

        Logs info messages to help users debug placeholder issues.

        Args:
            content: Skill content to check
        """
        for typo_pattern in self.TYPO_PATTERNS:
            if re.search(typo_pattern, content):
                logger.info(
                    f"Possible typo detected: found '{typo_pattern}' instead of '$ARGUMENTS'"
                )


class CompositeProcessor(ContentProcessor):
    """Chains multiple processors in order.

    Processors are applied sequentially, with the output of one processor
    becoming the input to the next.

    Example:
        >>> processors = [
        ...     BaseDirectoryProcessor(),
        ...     ArgumentSubstitutionProcessor()
        ... ]
        >>> composite = CompositeProcessor(processors)
        >>> result = composite.process(content, context)
    """

    def __init__(self, processors: List[ContentProcessor]) -> None:
        """Initialize composite processor.

        Args:
            processors: List of processors to chain (applied in order)
        """
        self.processors = processors

    def process(self, content: str, context: Dict[str, Any]) -> str:
        """Apply all processors sequentially.

        Args:
            content: Initial content
            context: Processing context

        Returns:
            Content after all processors applied

        Raises:
            Various processing-specific exceptions from chained processors
        """
        result = content
        for processor in self.processors:
            result = processor.process(result, context)
        return result
