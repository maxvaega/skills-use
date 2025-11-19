"""skillkit: Python library for Anthropic's Agent Skills functionality.

This library implements multi-source skill discovery, YAML frontmatter parsing,
progressive disclosure pattern, and framework integrations for LLM-powered agents.
"""

import logging

# Add NullHandler to prevent "No handlers found" warnings (Python library standard)
logging.getLogger(__name__).addHandler(logging.NullHandler())

# Public API exports
from skillkit.core.exceptions import (
    ArgumentProcessingError,
    ArgumentSerializationError,
    ArgumentSizeError,
    ContentLoadError,
    InterpreterNotFoundError,
    InvalidFrontmatterError,
    InvalidYAMLError,
    MissingRequiredFieldError,
    PathSecurityError,
    ScriptNotFoundError,
    ScriptPermissionError,
    SizeLimitExceededError,
    SkillInvocationError,
    SkillNotFoundError,
    SkillParsingError,
    SkillSecurityError,
    SkillsUseError,
    SuspiciousInputError,
)
from skillkit.core.manager import SkillManager
from skillkit.core.models import Skill, SkillMetadata
from skillkit.core.path_resolver import FilePathResolver
from skillkit.core.scripts import ScriptExecutionResult, ScriptMetadata

__version__ = "0.1.0"

__all__ = [
    # Core classes
    "SkillManager",
    "SkillMetadata",
    "Skill",
    "FilePathResolver",
    # Script classes (v0.3+)
    "ScriptMetadata",
    "ScriptExecutionResult",
    # Base exceptions
    "SkillsUseError",
    "SkillParsingError",
    "SkillInvocationError",
    "SkillSecurityError",
    # Parsing exceptions
    "InvalidYAMLError",
    "MissingRequiredFieldError",
    "InvalidFrontmatterError",
    # Runtime exceptions
    "SkillNotFoundError",
    "ArgumentProcessingError",
    "ContentLoadError",
    # Security exceptions
    "SuspiciousInputError",
    "SizeLimitExceededError",
    "PathSecurityError",
    # Script exceptions (v0.3+)
    "InterpreterNotFoundError",
    "ScriptNotFoundError",
    "ScriptPermissionError",
    "ArgumentSerializationError",
    "ArgumentSizeError",
]
