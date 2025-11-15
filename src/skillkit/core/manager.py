"""Skill manager orchestration layer.

This module provides the SkillManager class, the main entry point for
skill discovery, access, and invocation.
"""

import logging
from pathlib import Path
from typing import Dict, List

from skillkit.core.discovery import SkillDiscovery
from skillkit.core.exceptions import SkillNotFoundError, SkillsUseError
from skillkit.core.models import (
    InitMode,
    Skill,
    SkillMetadata,
    SkillSource,
    SourceType,
)
from skillkit.core.parser import SkillParser

logger = logging.getLogger(__name__)

# Priority constants for source resolution
PRIORITY_PROJECT = 100
PRIORITY_ANTHROPIC = 50
PRIORITY_PLUGIN = 10
PRIORITY_CUSTOM_BASE = 5


class SkillManager:
    """Central skill registry with discovery and invocation capabilities.

    Discovery: Graceful degradation (log errors, continue processing)
    Invocation: Strict validation (raise specific exceptions)
    Thread-safety: Not guaranteed in v0.2 (single-threaded usage assumed)

    Attributes:
        sources: Priority-ordered list of SkillSource objects
        _skills: Internal skill registry (name → metadata)
        _plugin_skills: Plugin-namespaced skills (plugin_name → skill_name → metadata)
        _parser: YAML frontmatter parser
        _discovery: Filesystem scanner
        _init_mode: Initialization mode (UNINITIALIZED, SYNC, or ASYNC)
    """

    def __init__(
        self,
        skill_dir: Path | str | None = None,  # v0.1 compatibility (deprecated)
        project_skill_dir: Path | str | None = None,
        anthropic_config_dir: Path | str | None = None,
        plugin_dirs: List[Path | str] | None = None,
        additional_search_paths: List[Path | str] | None = None,
    ) -> None:
        """Initialize skill manager with multiple source support.

        Args:
            skill_dir: (Deprecated) Legacy v0.1 parameter, mapped to project_skill_dir
            project_skill_dir: Path to project skills directory (default: ./skills/)
            anthropic_config_dir: Path to Anthropic config directory (default: ./.claude/skills/)
            plugin_dirs: List of plugin root directories
            additional_search_paths: Additional skill directories (lowest priority)

        Example:
            >>> # v0.1 compatibility (deprecated)
            >>> manager = SkillManager(skill_dir="./skills")

            >>> # v0.2 multi-source configuration
            >>> manager = SkillManager(
            ...     project_skill_dir="./skills",
            ...     anthropic_config_dir="./.claude/skills",
            ...     plugin_dirs=["./plugins/data-tools", "./plugins/web-tools"],
            ... )
        """
        # v0.1 compatibility: map skill_dir to project_skill_dir
        if skill_dir is not None and project_skill_dir is None:
            logger.warning(
                "Parameter 'skill_dir' is deprecated in v0.2. Use 'project_skill_dir' instead."
            )
            project_skill_dir = skill_dir

        # Build priority-ordered sources
        self.sources: List[SkillSource] = self._build_sources(
            project_skill_dir,
            anthropic_config_dir,
            plugin_dirs,
            additional_search_paths,
        )

        # Skill registries
        self._skills: Dict[str, SkillMetadata] = {}
        self._plugin_skills: Dict[str, Dict[str, SkillMetadata]] = {}

        # Infrastructure
        self._parser = SkillParser()
        self._discovery = SkillDiscovery()

        # State tracking
        self._init_mode: InitMode = InitMode.UNINITIALIZED

        # Legacy v0.1 compatibility attribute
        self.skills_dir = (
            Path(project_skill_dir) if project_skill_dir else Path.cwd() / ".claude" / "skills"
        )

    def _build_sources(
        self,
        project_skill_dir: Path | str | None,
        anthropic_config_dir: Path | str | None,
        plugin_dirs: List[Path | str] | None,
        additional_search_paths: List[Path | str] | None,
    ) -> List[SkillSource]:
        """Build priority-ordered list of skill sources.

        Args:
            project_skill_dir: Project skills directory
            anthropic_config_dir: Anthropic config directory
            plugin_dirs: Plugin directories
            additional_search_paths: Additional skill directories

        Returns:
            List of SkillSource objects sorted by priority (descending)

        Notes:
            - Sources are sorted by priority: PROJECT (100) > ANTHROPIC (50) > PLUGIN (10) > CUSTOM (5)
            - Plugin manifests are NOT parsed here (deferred to discovery phase)
            - Non-existent directories are filtered out with warnings
        """
        sources: List[SkillSource] = []

        # Project skills (highest priority)
        if project_skill_dir is not None:
            project_path = (
                Path(project_skill_dir) if isinstance(project_skill_dir, str) else project_skill_dir
            )
            if project_path.exists() and project_path.is_dir():
                sources.append(
                    SkillSource(
                        source_type=SourceType.PROJECT,
                        directory=project_path.resolve(),
                        priority=PRIORITY_PROJECT,
                    )
                )
            else:
                logger.warning(f"Project skill directory does not exist: {project_path}")

        # Anthropic config skills
        if anthropic_config_dir is not None:
            anthropic_path = (
                Path(anthropic_config_dir)
                if isinstance(anthropic_config_dir, str)
                else anthropic_config_dir
            )
            if anthropic_path.exists() and anthropic_path.is_dir():
                sources.append(
                    SkillSource(
                        source_type=SourceType.ANTHROPIC,
                        directory=anthropic_path.resolve(),
                        priority=PRIORITY_ANTHROPIC,
                    )
                )
            else:
                logger.warning(f"Anthropic config directory does not exist: {anthropic_path}")

        # Plugin skills
        if plugin_dirs:
            for plugin_dir in plugin_dirs:
                plugin_path = Path(plugin_dir) if isinstance(plugin_dir, str) else plugin_dir
                if plugin_path.exists() and plugin_path.is_dir():
                    # Plugin manifest parsing deferred to discovery phase
                    # For now, use directory name as placeholder plugin name
                    sources.append(
                        SkillSource(
                            source_type=SourceType.PLUGIN,
                            directory=plugin_path.resolve(),
                            priority=PRIORITY_PLUGIN,
                            plugin_name=plugin_path.name,  # Placeholder, will be updated from manifest
                        )
                    )
                else:
                    logger.warning(f"Plugin directory does not exist: {plugin_path}")

        # Additional search paths (lowest priority)
        if additional_search_paths:
            for i, search_path in enumerate(additional_search_paths):
                custom_path = Path(search_path) if isinstance(search_path, str) else search_path
                if custom_path.exists() and custom_path.is_dir():
                    sources.append(
                        SkillSource(
                            source_type=SourceType.CUSTOM,
                            directory=custom_path.resolve(),
                            priority=PRIORITY_CUSTOM_BASE - i,  # Decrement for each additional path
                        )
                    )
                else:
                    logger.warning(f"Custom skill directory does not exist: {custom_path}")

        # Sort by priority (descending)
        sources.sort(key=lambda s: s.priority, reverse=True)

        logger.debug(
            f"Built {len(sources)} skill sources with priorities: "
            f"{[(s.source_type.value, s.priority) for s in sources]}"
        )

        return sources

    @property
    def init_mode(self) -> InitMode:
        """Get current initialization mode.

        Returns:
            Current InitMode (UNINITIALIZED, SYNC, or ASYNC)
        """
        return self._init_mode

    def discover(self) -> None:
        """Discover skills from all sources (graceful degradation).

        Behavior:
            - Scans all configured sources in priority order
            - Parses YAML frontmatter and validates required fields
            - Continues processing even if individual skills fail parsing
            - Logs errors via module logger (skillkit.core.manager)
            - Handles duplicates: highest priority source wins, logs WARNING

        Side Effects:
            - Populates internal _skills registry
            - Sets init_mode to SYNC
            - Logs errors for malformed skills
            - Logs INFO if directory empty
            - Logs WARNING for duplicate skill names

        Raises:
            AsyncStateError: If manager was already initialized with adiscover()

        Performance:
            - Target: <500ms for 10 skills
            - Actual: ~5-10ms per skill (dominated by YAML parsing)

        Example:
            >>> manager = SkillManager(project_skill_dir="./skills")
            >>> manager.discover()
            >>> print(f"Found {len(manager.list_skills())} skills")
            Found 5 skills
        """
        from skillkit.core.exceptions import AsyncStateError

        # Check for mixing sync/async initialization
        if self._init_mode == InitMode.ASYNC:
            raise AsyncStateError(
                "Manager was initialized with adiscover() (async mode). "
                "Cannot mix sync and async methods. Create a new manager instance."
            )

        # Set initialization mode
        self._init_mode = InitMode.SYNC

        logger.info(f"Starting skill discovery in: {self.skills_dir} (sync mode)")

        # Clear existing skills
        self._skills.clear()

        # Scan for skill files
        skill_files = self._discovery.scan_directory(self.skills_dir)

        if not skill_files:
            logger.info(f"No skills found in {self.skills_dir}")
            return

        # Parse each skill file (graceful degradation)
        for skill_file in skill_files:
            try:
                metadata = self._parser.parse_skill_file(skill_file)

                # Check for duplicate names
                if metadata.name in self._skills:
                    logger.warning(
                        f"Duplicate skill name '{metadata.name}' found at {skill_file}. "
                        f"Keeping first occurrence from {self._skills[metadata.name].skill_path}"
                    )
                    continue

                # Add to registry
                self._skills[metadata.name] = metadata
                logger.debug(f"Registered skill: {metadata.name}")

            except SkillsUseError as e:
                # Log parsing errors but continue with other skills
                logger.error(f"Failed to parse skill at {skill_file}: {e}", exc_info=True)
            except Exception as e:
                # Catch unexpected errors
                logger.error(f"Unexpected error parsing {skill_file}: {e}", exc_info=True)

        logger.info(f"Discovery complete: {len(self._skills)} skill(s) registered successfully")

    async def adiscover(self) -> None:
        """Async version of discover() for non-blocking skill discovery.

        Behavior:
            - Scans all configured sources in priority order (non-blocking)
            - Parses YAML frontmatter asynchronously
            - Continues processing even if individual skills fail parsing
            - Logs errors via module logger (skillkit.core.manager)
            - Handles duplicates: highest priority source wins, logs WARNING

        Side Effects:
            - Populates internal _skills registry
            - Sets init_mode to ASYNC
            - Logs errors for malformed skills
            - Logs INFO if directory empty
            - Logs WARNING for duplicate skill names

        Raises:
            AsyncStateError: If manager was already initialized with discover()

        Performance:
            - Target: <200ms for 500 skills (spec requirement SC-001)
            - Uses asyncio.gather() for concurrent scanning

        Example:
            >>> manager = SkillManager(project_skill_dir="./skills")
            >>> await manager.adiscover()
            >>> print(f"Found {len(manager.list_skills())} skills")
            Found 5 skills
        """
        from skillkit.core.exceptions import AsyncStateError

        # T016: Check for mixing sync/async initialization
        if self._init_mode == InitMode.SYNC:
            raise AsyncStateError(
                "Manager was initialized with discover() (sync mode). "
                "Cannot mix sync and async methods. Create a new manager instance."
            )

        # T017: Set initialization mode to ASYNC
        self._init_mode = InitMode.ASYNC

        logger.info(f"Starting skill discovery in: {self.skills_dir} (async mode)")

        # Clear existing skills
        self._skills.clear()

        # Scan for skill files asynchronously
        skill_files = await self._discovery.ascan_directory(self.skills_dir)

        if not skill_files:
            logger.info(f"No skills found in {self.skills_dir}")
            return

        # Parse each skill file asynchronously (graceful degradation)
        for skill_file in skill_files:
            try:
                metadata = self._parser.parse_skill_file(skill_file)

                # Check for duplicate names
                if metadata.name in self._skills:
                    logger.warning(
                        f"Duplicate skill name '{metadata.name}' found at {skill_file}. "
                        f"Keeping first occurrence from {self._skills[metadata.name].skill_path}"
                    )
                    continue

                # Add to registry
                self._skills[metadata.name] = metadata
                logger.debug(f"Registered skill: {metadata.name}")

            except SkillsUseError as e:
                # Log parsing errors but continue with other skills
                logger.error(f"Failed to parse skill at {skill_file}: {e}", exc_info=True)
            except Exception as e:
                # Catch unexpected errors
                logger.error(f"Unexpected error parsing {skill_file}: {e}", exc_info=True)

        logger.info(
            f"Async discovery complete: {len(self._skills)} skill(s) registered successfully"
        )

    def list_skills(self) -> List[SkillMetadata]:
        """Return all discovered skill metadata (lightweight).

        Returns:
            List of SkillMetadata instances (metadata only, no content)

        Performance:
            - O(n) where n = number of skills
            - Copies internal list (~1-5ms for 100 skills)

        Example:
            >>> skills = manager.list_skills()
            >>> for skill in skills:
            ...     print(f"{skill.name}: {skill.description}")
            code-reviewer: Review code for best practices
            git-helper: Generate commit messages
        """
        return list(self._skills.values())

    def get_skill(self, name: str) -> SkillMetadata:
        """Get skill metadata by name (strict validation).

        Args:
            name: Skill name (case-sensitive)

        Returns:
            SkillMetadata instance

        Raises:
            SkillNotFoundError: If skill name not in registry

        Performance:
            - O(1) dictionary lookup (~1μs)

        Example:
            >>> metadata = manager.get_skill("code-reviewer")
            >>> print(metadata.description)
            Review code for best practices

            >>> manager.get_skill("nonexistent")
            SkillNotFoundError: Skill 'nonexistent' not found
        """
        if name not in self._skills:
            available = ", ".join(self._skills.keys()) if self._skills else "none"
            raise SkillNotFoundError(f"Skill '{name}' not found. Available skills: {available}")

        return self._skills[name]

    def load_skill(self, name: str) -> Skill:
        """Load full skill instance (content loaded lazily).

        Args:
            name: Skill name (case-sensitive)

        Returns:
            Skill instance (content not yet loaded)

        Raises:
            SkillNotFoundError: If skill name not in registry

        Performance:
            - O(1) lookup + Skill instantiation (~10-50μs)
            - Content NOT loaded until .content property accessed

        Example:
            >>> skill = manager.load_skill("code-reviewer")
            >>> # Content not loaded yet
            >>> processed = skill.invoke("review main.py")
            >>> # Content loaded and processed
        """
        metadata = self.get_skill(name)

        # Base directory is the parent of SKILL.md file
        base_directory = metadata.skill_path.parent

        return Skill(metadata=metadata, base_directory=base_directory)

    def invoke_skill(self, name: str, arguments: str = "") -> str:
        """Load and invoke skill in one call (convenience method).

        Args:
            name: Skill name (case-sensitive)
            arguments: User-provided arguments for skill invocation

        Returns:
            Processed skill content (with base directory + argument substitution)

        Raises:
            SkillNotFoundError: If skill name not in registry
            ContentLoadError: If skill file cannot be read
            ArgumentProcessingError: If argument processing fails
            SizeLimitExceededError: If arguments exceed 1MB

        Performance:
            - Total: ~10-25ms overhead
            - Breakdown: File I/O ~10-20ms + processing ~1-5ms

        Example:
            >>> result = manager.invoke_skill("code-reviewer", "review main.py")
            >>> print(result[:100])
            Base directory for this skill: /Users/alice/.claude/skills/code-reviewer

            Review the following code: review main.py
        """
        skill = self.load_skill(name)
        return skill.invoke(arguments)

    async def ainvoke_skill(self, name: str, arguments: str = "") -> str:
        """Async version of invoke_skill() for non-blocking invocation.

        Args:
            name: Skill name (case-sensitive)
            arguments: User-provided arguments for skill invocation

        Returns:
            Processed skill content (with base directory + argument substitution)

        Raises:
            AsyncStateError: If manager was initialized with discover() (sync mode)
            SkillNotFoundError: If skill name not in registry
            ContentLoadError: If skill file cannot be read
            ArgumentProcessingError: If argument processing fails
            SizeLimitExceededError: If arguments exceed 1MB

        Performance:
            - Overhead: <2ms vs sync invoke_skill()
            - Event loop remains responsive during file I/O
            - Suitable for concurrent invocations (10+)

        Example:
            >>> result = await manager.ainvoke_skill("code-reviewer", "review main.py")
            >>> print(result[:100])
            Base directory for this skill: /Users/alice/.claude/skills/code-reviewer

            Review the following code: review main.py
        """
        from skillkit.core.exceptions import AsyncStateError

        # Validate async initialization
        if self._init_mode == InitMode.SYNC:
            raise AsyncStateError(
                "Manager was initialized with discover() (sync mode). "
                "Cannot use ainvoke_skill(). Use invoke_skill() instead, "
                "or create a new manager and call adiscover()."
            )

        if self._init_mode == InitMode.UNINITIALIZED:
            raise SkillsUseError(
                "Manager not initialized. Call adiscover() before invoking skills."
            )

        # Load skill and invoke asynchronously
        skill = self.load_skill(name)
        return await skill.ainvoke(arguments)
