"""Core data models for skillkit library.

This module defines the SkillMetadata and Skill dataclasses that implement
the progressive disclosure pattern for memory-efficient skill management.
"""

import sys
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skillkit.core.processors import CompositeProcessor

# Check Python version for slots support on all dataclasses
PYTHON_310_PLUS = sys.version_info >= (3, 10)


@dataclass(frozen=True, slots=True)
class SkillMetadata:
    """Lightweight skill metadata loaded during discovery phase.

    Memory: ~400-800 bytes per instance (Python 3.10+)
    Immutability: frozen=True prevents accidental mutation
    Optimization: slots=True reduces memory by 60%

    Attributes:
        name: Unique skill identifier (from YAML frontmatter)
        description: Human-readable description of skill purpose
        skill_path: Absolute path to SKILL.md file
        allowed_tools: Tool names allowed for this skill (optional, not enforced in v0.1)
    """

    name: str
    description: str
    skill_path: Path
    allowed_tools: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        """Validate skill path exists on construction.

        Raises:
            ValueError: If skill_path does not exist
        """
        if not self.skill_path.exists():
            raise ValueError(f"Skill path does not exist: {self.skill_path}")


# Note: Cannot use slots=True with cached_property, so Skill uses only frozen=True
# Memory impact is minimal since content is much larger than object overhead
@dataclass(frozen=True)
class Skill:
    """Full skill with lazy-loaded content (Python 3.10+).

    Memory: ~400-800 bytes wrapper + ~50-200KB content (when loaded)
    Content Loading: On-demand via @cached_property
    Processing: Via CompositeProcessor (base directory + arguments)

    Attributes:
        metadata: Lightweight metadata from discovery phase
        base_directory: Base directory context for skill execution
        _processor: Content processor chain (initialized in __post_init__)
    """

    metadata: SkillMetadata
    base_directory: Path
    _processor: "CompositeProcessor" = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Initialize processor chain (avoids inline imports anti-pattern).

        Side Effects:
            Creates CompositeProcessor with BaseDirectoryProcessor + ArgumentSubstitutionProcessor
        """
        from skillkit.core.processors import (
            ArgumentSubstitutionProcessor,
            BaseDirectoryProcessor,
            CompositeProcessor,
        )

        # Use object.__setattr__ because dataclass is frozen
        object.__setattr__(
            self,
            "_processor",
            CompositeProcessor(
                [
                    BaseDirectoryProcessor(),
                    ArgumentSubstitutionProcessor(),
                ]
            ),
        )

    @cached_property
    def content(self) -> str:
        """Lazy load content only when accessed.

        Returns:
            Full SKILL.md markdown content (UTF-8 encoded)

        Raises:
            ContentLoadError: If file cannot be read (deleted, permissions, encoding)

        Performance:
            - First access: ~10-20ms (file I/O)
            - Subsequent: <1μs (cached)
        """
        from skillkit.core.exceptions import ContentLoadError

        try:
            return self.metadata.skill_path.read_text(encoding="utf-8-sig")
        except FileNotFoundError as e:
            raise ContentLoadError(
                f"Skill file not found: {self.metadata.skill_path}. "
                f"File may have been deleted after discovery."
            ) from e
        except PermissionError as e:
            raise ContentLoadError(
                f"Permission denied reading skill: {self.metadata.skill_path}"
            ) from e
        except UnicodeDecodeError as e:
            raise ContentLoadError(
                f"Skill file contains invalid UTF-8: {self.metadata.skill_path}"
            ) from e

    def invoke(self, arguments: str = "") -> str:
        """Process skill content with arguments.

        Args:
            arguments: User-provided arguments for skill invocation

        Returns:
            Processed skill content with base directory + argument substitution

        Raises:
            ContentLoadError: If content cannot be loaded
            ArgumentProcessingError: If argument processing fails
            SizeLimitExceededError: If arguments exceed 1MB

        Processing Steps:
            1. Load content (lazy, cached)
            2. Inject base directory at beginning
            3. Replace $ARGUMENTS placeholders with actual arguments
            4. Return processed string

        Performance:
            - First invocation: ~10-25ms (includes content loading)
            - Subsequent: ~1-5ms (content cached, only processing)
        """
        context = {
            "arguments": arguments,
            "base_directory": str(self.base_directory),
            "skill_name": self.metadata.name,
        }
        return self._processor.process(self.content, context)
