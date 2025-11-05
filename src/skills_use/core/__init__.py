"""Core module for skills-use library.

This module contains the framework-agnostic core functionality with zero
framework dependencies (stdlib + PyYAML only).
"""

from skills_use.core.discovery import SkillDiscovery
from skills_use.core.exceptions import (
    ArgumentProcessingError,
    ContentLoadError,
    InvalidFrontmatterError,
    InvalidYAMLError,
    MissingRequiredFieldError,
    SizeLimitExceededError,
    SkillInvocationError,
    SkillNotFoundError,
    SkillParsingError,
    SkillSecurityError,
    SkillsUseError,
    SuspiciousInputError,
)
from skills_use.core.manager import SkillManager
from skills_use.core.models import Skill, SkillMetadata
from skills_use.core.parser import SkillParser
from skills_use.core.processors import (
    ArgumentSubstitutionProcessor,
    BaseDirectoryProcessor,
    CompositeProcessor,
    ContentProcessor,
)

__all__ = [
    # Core classes
    "SkillManager",
    "SkillMetadata",
    "Skill",
    "SkillDiscovery",
    "SkillParser",
    # Processors
    "ContentProcessor",
    "BaseDirectoryProcessor",
    "ArgumentSubstitutionProcessor",
    "CompositeProcessor",
    # Exceptions
    "SkillsUseError",
    "SkillParsingError",
    "InvalidYAMLError",
    "MissingRequiredFieldError",
    "InvalidFrontmatterError",
    "SkillNotFoundError",
    "SkillInvocationError",
    "ArgumentProcessingError",
    "ContentLoadError",
    "SkillSecurityError",
    "SuspiciousInputError",
    "SizeLimitExceededError",
]
