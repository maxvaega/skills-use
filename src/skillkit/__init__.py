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
    ContentLoadError,
    InvalidFrontmatterError,
    InvalidYAMLError,
    MissingRequiredFieldError,
    PathSecurityError,
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

__version__ = "0.1.0"

__all__ = [
    # Core classes
    "SkillManager",
    "SkillMetadata",
    "Skill",
    "FilePathResolver",
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
]
