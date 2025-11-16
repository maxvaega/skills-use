"""Core data models for skillkit library.

This module defines the SkillMetadata and Skill dataclasses that implement
the progressive disclosure pattern for memory-efficient skill management.
"""

import sys
from dataclasses import dataclass, field
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skillkit.core.processors import CompositeProcessor

# Check Python version for slots support on all dataclasses
# Note: Project requires Python 3.10+ (per pyproject.toml), so slots=True is safe
# The variable is kept for documentation purposes
PYTHON_310_PLUS = sys.version_info >= (3, 10)


class SourceType(str, Enum):
    """Skill source type classification.

    Values define the priority order for conflict resolution:
    - PROJECT: Project-specific skills (./skills/) - Priority 100
    - ANTHROPIC: Anthropic config skills (./.claude/skills/) - Priority 50
    - PLUGIN: Plugin skills (./plugins/*/skills/) - Priority 10
    - CUSTOM: Additional user paths - Priority 5
    """

    PROJECT = "project"
    ANTHROPIC = "anthropic"
    PLUGIN = "plugin"
    CUSTOM = "custom"


class InitMode(str, Enum):
    """Tracks SkillManager initialization state.

    Values track whether the manager was initialized synchronously or asynchronously
    to prevent mixing sync and async methods on the same instance.

    State Transitions:
        UNINITIALIZED → SYNC (via discover())
        UNINITIALIZED → ASYNC (via adiscover())
        SYNC → SYNC (no-op, already initialized)
        ASYNC → ASYNC (no-op, already initialized)
        SYNC ↛ ASYNC (ERROR: AsyncStateError)
        ASYNC ↛ SYNC (ERROR: AsyncStateError)
    """

    UNINITIALIZED = "uninitialized"
    SYNC = "sync"
    ASYNC = "async"


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

    async def _load_content_async(self) -> str:
        """Async wrapper for content loading using asyncio.to_thread().

        Returns:
            Full SKILL.md markdown content (UTF-8 encoded)

        Raises:
            ContentLoadError: If file cannot be read

        Performance:
            - Overhead: <2ms vs sync version
            - Event loop remains responsive during I/O
        """
        import asyncio

        from skillkit.core.exceptions import ContentLoadError

        def _sync_read() -> str:
            """Sync implementation for thread execution."""
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

        return await asyncio.to_thread(_sync_read)

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

    async def ainvoke(self, arguments: str = "") -> str:
        """Async version of invoke() for non-blocking skill invocation.

        Args:
            arguments: User-provided arguments for skill invocation

        Returns:
            Processed skill content with base directory + argument substitution

        Raises:
            ContentLoadError: If content cannot be loaded
            ArgumentProcessingError: If argument processing fails
            SizeLimitExceededError: If arguments exceed 1MB

        Processing Steps:
            1. Load content asynchronously (non-blocking)
            2. Inject base directory at beginning
            3. Replace $ARGUMENTS placeholders with actual arguments
            4. Return processed string

        Performance:
            - Overhead: <2ms vs sync invoke()
            - Event loop remains responsive during file I/O
            - Suitable for concurrent invocations (10+)
        """
        # Check if content is already cached
        if "content" in self.__dict__:
            # Content already loaded, use sync processing
            content = self.content
        else:
            # Load content asynchronously
            content = await self._load_content_async()

        context = {
            "arguments": arguments,
            "base_directory": str(self.base_directory),
            "skill_name": self.metadata.name,
        }
        return self._processor.process(content, context)


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """Parsed metadata from .claude-plugin/plugin.json.

    Memory: ~400 bytes per instance
    Validation: Performed in __post_init__

    Attributes:
        name: Plugin identifier (must be valid Python identifier)
        version: Semantic version (e.g., "1.0.0")
        description: Plugin purpose
        author: Plugin author information
        skills: Skill directories relative to plugin root
        manifest_path: Path to plugin.json file (for error reporting)
        manifest_version: MCPB manifest version (e.g., "0.1", "0.3")
        display_name: Human-friendly plugin name (optional)
        homepage: Plugin homepage URL (optional)
        repository: Source control info (optional)
    """

    name: str
    version: str
    description: str
    author: dict[str, str]
    skills: list[str]
    manifest_path: Path
    manifest_version: str = "0.1"
    display_name: str | None = None
    homepage: str | None = None
    repository: dict[str, str] | None = None

    def __post_init__(self) -> None:
        """Validate manifest fields with security checks.

        Raises:
            ManifestValidationError: If validation fails
        """
        from skillkit.core.exceptions import ManifestValidationError

        # Validate manifest version
        if self.manifest_version not in {"0.1", "0.3"}:
            raise ManifestValidationError(
                f"Unsupported manifest_version: {self.manifest_version}. "
                f"Supported versions: 0.1, 0.3",
                field_name="manifest_version",
                invalid_value=self.manifest_version,
            )

        # Validate name (must be valid identifier, no spaces)
        if not self.name or " " in self.name:
            raise ManifestValidationError(
                "Plugin name cannot be empty or contain spaces",
                field_name="name",
                invalid_value=self.name,
            )

        # Validate version (basic semver check)
        if not self.version or self.version.count(".") < 2:
            raise ManifestValidationError(
                "Version must be semver format (e.g., 1.0.0)",
                field_name="version",
                invalid_value=self.version,
            )

        # Validate description
        if not self.description or len(self.description) > 1000:
            raise ManifestValidationError(
                "Description required (max 1000 chars)",
                field_name="description",
                invalid_value=self.description if self.description else "",
            )

        # Validate author
        if not isinstance(self.author, dict) or "name" not in self.author:
            raise ManifestValidationError(
                "Author must be a dict with 'name' field",
                field_name="author",
                invalid_value=str(self.author),
            )

        # SECURITY: Validate skills paths
        for skill_path in self.skills:
            if not skill_path:
                raise ManifestValidationError(
                    "Skill path cannot be empty",
                    field_name="skills",
                    invalid_value=skill_path,
                )

            # Prevent path traversal
            if ".." in skill_path:
                raise ManifestValidationError(
                    f"Security violation: Path contains '..': {skill_path}",
                    field_name="skills",
                    invalid_value=skill_path,
                )

            # Prevent absolute paths
            if skill_path.startswith("/") or skill_path.startswith("\\"):
                raise ManifestValidationError(
                    f"Security violation: Path must be relative: {skill_path}",
                    field_name="skills",
                    invalid_value=skill_path,
                )

            # Windows: Prevent drive letters
            if len(skill_path) >= 2 and skill_path[1] == ":":
                raise ManifestValidationError(
                    f"Security violation: Drive letters not allowed: {skill_path}",
                    field_name="skills",
                    invalid_value=skill_path,
                )


@dataclass(frozen=True, slots=True)
class SkillSource:
    """Represents a skill source location with priority and metadata.

    Memory: ~200 bytes per instance
    Immutability: frozen=True prevents accidental mutation

    Attributes:
        source_type: Enum: PROJECT | ANTHROPIC | PLUGIN | CUSTOM
        directory: Absolute path to skill root directory
        priority: Priority for conflict resolution (higher = wins)
        plugin_name: Plugin namespace (only for PLUGIN type)
        plugin_manifest: Parsed manifest (only for PLUGIN type)
    """

    source_type: SourceType
    directory: Path
    priority: int
    plugin_name: str | None = None
    plugin_manifest: PluginManifest | None = None

    def __post_init__(self) -> None:
        """Validate source configuration.

        Raises:
            ValueError: If validation fails
        """
        # Validate directory exists
        if not self.directory.exists():
            raise ValueError(f"Source directory does not exist: {self.directory}")

        if not self.directory.is_dir():
            raise ValueError(f"Source path is not a directory: {self.directory}")

        # Validate priority is positive
        if self.priority <= 0:
            raise ValueError(f"Priority must be positive, got: {self.priority}")

        # Validate plugin-specific constraints
        if self.source_type == SourceType.PLUGIN and self.plugin_name is None:
            raise ValueError("plugin_name required when source_type == PLUGIN")


@dataclass(frozen=True, slots=True)
class QualifiedSkillName:
    """Skill identifier with optional plugin namespace.

    Format: "plugin:skill" (qualified) or "skill" (unqualified)

    Attributes:
        plugin: Plugin name (if qualified)
        skill: Skill name
    """

    plugin: str | None
    skill: str

    @staticmethod
    def parse(name: str) -> "QualifiedSkillName":
        """Parse qualified or unqualified skill name.

        Args:
            name: Skill name in format "plugin:skill" or "skill"

        Returns:
            QualifiedSkillName with plugin and skill parts

        Raises:
            ValueError: If name format is invalid

        Examples:
            >>> QualifiedSkillName.parse("csv-parser")
            QualifiedSkillName(plugin=None, skill="csv-parser")

            >>> QualifiedSkillName.parse("data-tools:csv-parser")
            QualifiedSkillName(plugin="data-tools", skill="csv-parser")
        """
        if not name:
            raise ValueError("Skill name cannot be empty")

        # Check for qualified name
        if ":" in name:
            parts = name.split(":", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid qualified name format: {name}")

            plugin, skill = parts

            if not plugin or not skill:
                raise ValueError(f"Invalid qualified name (empty plugin or skill): {name}")

            return QualifiedSkillName(plugin=plugin, skill=skill)

        # Unqualified name
        return QualifiedSkillName(plugin=None, skill=name)
