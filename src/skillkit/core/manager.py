"""Skill manager orchestration layer.

This module provides the SkillManager class, the main entry point for
skill discovery, access, and invocation.
"""

import logging
from pathlib import Path
from typing import Dict, List

from skillkit.core.discovery import SkillDiscovery
from skillkit.core.exceptions import ConfigurationError, SkillNotFoundError, SkillsUseError
from skillkit.core.models import (
    InitMode,
    Skill,
    SkillMetadata,
    SkillSource,
    SourceType,
)
from skillkit.core.parser import SkillParser

logger = logging.getLogger(__name__)

# Default directory paths for zero-configuration initialization
DEFAULT_PROJECT_DIR = Path("./skills")
DEFAULT_ANTHROPIC_DIR = Path("./.claude/skills")

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

    Priority Order for Conflict Resolution:
        1. PROJECT (priority 100): Project-specific skills in ./skills/
        2. ANTHROPIC (priority 50): Anthropic config skills in ./.claude/skills/
        3. PLUGIN (priority 10): Plugin skills from plugin directories
        4. CUSTOM (priority 5): Additional search paths (decrements for each path)

    When skills with the same name exist in multiple sources, the highest priority
    source wins. Lower-priority versions can be accessed using fully qualified names
    (e.g., "plugin-name:skill-name").

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
        """Initialize skill manager with flexible multi-source configuration.

        Args:
            skill_dir: (Deprecated) Legacy v0.1 parameter, mapped to project_skill_dir

            project_skill_dir: Project skills directory (priority: 100)
                - None (default): Check if ./skills/ exists → add if exists (zero-config)
                - "" (empty string): Explicit opt-out → skip (no default fallback)
                - Path/str: Validate exists → add OR raise ConfigurationError

            anthropic_config_dir: Anthropic config directory (priority: 50)
                - None (default): Check if ./.claude/skills/ exists → add if exists (zero-config)
                - "" (empty string): Explicit opt-out → skip (no default fallback)
                - Path/str: Validate exists → add OR raise ConfigurationError

            plugin_dirs: List of plugin root directories (priority: 10 each)
                - None (default): No plugins configured (skip)
                - [] (empty list): Explicit opt-out (skip)
                - [Path, ...]: Validate each exists → add OR raise ConfigurationError

            additional_search_paths: Additional skill directories (priority: 5, 4, 3, ...)
                - None (default): No additional paths (skip)
                - [Path, ...]: Validate each exists → add OR raise ConfigurationError

        Raises:
            ConfigurationError: When explicitly provided directory path doesn't exist

        Priority Resolution:
            When skills with the same name exist in multiple sources, the source with
            the highest priority wins. Lower-priority versions remain accessible via
            fully qualified names (e.g., "plugin-name:skill-name").

        Default Directory Behavior:
            When parameters are None/omitted, SkillManager checks for default directories:
            - ./skills/ (project skills)
            - ./.claude/skills/ (Anthropic config)
            If both exist, BOTH are scanned with project priority (100) > anthropic (50).
            If neither exists, manager initializes with empty skill list (no error).

        Explicit Opt-Out:
            Use empty string "" or empty list [] to explicitly disable discovery for a source:
            - SkillManager(project_skill_dir="") → Skip project skills even if ./skills/ exists
            - SkillManager(plugin_dirs=[]) → Skip plugin discovery

        Duplicate Plugin Names:
            If multiple plugins have the same name, they will be automatically
            disambiguated with numeric suffixes (e.g., "my-plugin-2", "my-plugin-3").

        Examples:
            >>> # Zero-configuration initialization (uses defaults if they exist)
            >>> manager = SkillManager()  # Auto-discovers ./skills/ and ./.claude/skills/
            >>> manager.discover()

            >>> # Explicit configuration (all paths must exist)
            >>> manager = SkillManager(
            ...     project_skill_dir="./my-skills",  # Must exist or raises ConfigurationError
            ...     anthropic_config_dir="./.claude/skills",
            ... )

            >>> # Opt-out of defaults (start with zero skills)
            >>> manager = SkillManager(
            ...     project_skill_dir="",       # Disable project skills
            ...     anthropic_config_dir="",    # Disable anthropic skills
            ...     plugin_dirs=[],             # Disable plugins
            ... )  # Initializes with empty skill list, no INFO log

            >>> # Mixed configuration (explicit path + opt-out)
            >>> manager = SkillManager(
            ...     project_skill_dir="./custom-skills",  # Use this instead of ./skills/
            ...     anthropic_config_dir="",              # Disable anthropic discovery
            ... )

            >>> # Full multi-source configuration
            >>> manager = SkillManager(
            ...     project_skill_dir="./skills",           # Highest priority (100)
            ...     anthropic_config_dir="./.claude/skills", # Medium priority (50)
            ...     plugin_dirs=["./plugins/data-tools"],    # Plugin priority (10)
            ...     additional_search_paths=["./shared"],    # Lowest priority (5)
            ... )

            >>> # Priority resolution example
            >>> # If "csv-parser" exists in both project and plugin:
            >>> manager.discover()
            >>> manager.get_skill("csv-parser")            # Gets project version (priority 100)
            >>> manager.get_skill("data-tools:csv-parser")  # Gets plugin version explicitly

            >>> # v0.1 compatibility (deprecated)
            >>> manager = SkillManager(skill_dir="./skills")  # Logs deprecation warning
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
        """Build priority-ordered list of skill sources with tri-state parameter logic.

        Args:
            project_skill_dir: Project skills directory (priority: 100)
                - None/omitted: Check if DEFAULT_PROJECT_DIR (./skills/) exists → add if exists
                - "" (empty string): Explicit opt-out → skip (no default fallback)
                - Path/str: Validate exists → add OR raise ConfigurationError
            anthropic_config_dir: Anthropic config directory (priority: 50)
                - None/omitted: Check if DEFAULT_ANTHROPIC_DIR (./.claude/skills/) exists → add if exists
                - "" (empty string): Explicit opt-out → skip (no default fallback)
                - Path/str: Validate exists → add OR raise ConfigurationError
            plugin_dirs: Plugin directories (priority: 10 each)
                - None/omitted: No plugins configured (skip)
                - []: Explicit opt-out (skip)
                - [Path, ...]: Validate each → add valid OR raise ConfigurationError
            additional_search_paths: Additional skill directories (priority: 5, 4, 3, ...)

        Returns:
            List of SkillSource objects sorted by priority (descending)

        Raises:
            ConfigurationError: When explicitly provided non-empty path doesn't exist

        Notes:
            - Sources are sorted by priority: PROJECT (100) > ANTHROPIC (50) > PLUGIN (10) > CUSTOM (5-)
            - Plugin manifests ARE parsed here to extract plugin names
            - Duplicate plugin names are automatically disambiguated with numeric suffixes
            - Default directory paths (./skills/, ./.claude/skills/) do NOT raise errors when missing
            - Explicitly provided paths MUST exist or ConfigurationError is raised
        """
        sources: List[SkillSource] = []

        # Project skills (highest priority) - TRI-STATE LOGIC
        if project_skill_dir is None:
            # None/omitted: Apply default directory discovery
            if DEFAULT_PROJECT_DIR.exists() and DEFAULT_PROJECT_DIR.is_dir():
                sources.append(
                    SkillSource(
                        source_type=SourceType.PROJECT,
                        directory=DEFAULT_PROJECT_DIR.resolve(),
                        priority=PRIORITY_PROJECT,
                    )
                )
        elif project_skill_dir == "":
            # Empty string: Explicit opt-out (skip)
            pass
        else:
            # Explicit path: Validate existence
            project_path = (
                Path(project_skill_dir) if isinstance(project_skill_dir, str) else project_skill_dir
            )
            if not project_path.exists() or not project_path.is_dir():
                raise ConfigurationError(
                    f"Explicitly configured directory does not exist: project_skill_dir='{project_path}'",
                    parameter_name="project_skill_dir",
                    invalid_path=str(project_path),
                )
            sources.append(
                SkillSource(
                    source_type=SourceType.PROJECT,
                    directory=project_path.resolve(),
                    priority=PRIORITY_PROJECT,
                )
            )

        # Anthropic config skills - TRI-STATE LOGIC
        if anthropic_config_dir is None:
            # None/omitted: Apply default directory discovery
            if DEFAULT_ANTHROPIC_DIR.exists() and DEFAULT_ANTHROPIC_DIR.is_dir():
                sources.append(
                    SkillSource(
                        source_type=SourceType.ANTHROPIC,
                        directory=DEFAULT_ANTHROPIC_DIR.resolve(),
                        priority=PRIORITY_ANTHROPIC,
                    )
                )
        elif anthropic_config_dir == "":
            # Empty string: Explicit opt-out (skip)
            pass
        else:
            # Explicit path: Validate existence
            anthropic_path = (
                Path(anthropic_config_dir)
                if isinstance(anthropic_config_dir, str)
                else anthropic_config_dir
            )
            if not anthropic_path.exists() or not anthropic_path.is_dir():
                raise ConfigurationError(
                    f"Explicitly configured directory does not exist: anthropic_config_dir='{anthropic_path}'",
                    parameter_name="anthropic_config_dir",
                    invalid_path=str(anthropic_path),
                )
            sources.append(
                SkillSource(
                    source_type=SourceType.ANTHROPIC,
                    directory=anthropic_path.resolve(),
                    priority=PRIORITY_ANTHROPIC,
                )
            )

        # Plugin skills (with duplicate name detection and validation)
        if plugin_dirs:
            from skillkit.core.discovery import discover_plugin_manifest

            # T062: Track plugin names to detect duplicates
            plugin_name_counts: Dict[str, int] = {}

            for plugin_dir in plugin_dirs:
                plugin_path = Path(plugin_dir) if isinstance(plugin_dir, str) else plugin_dir

                # Validate explicit plugin path exists
                if not plugin_path.exists() or not plugin_path.is_dir():
                    raise ConfigurationError(
                        f"Explicitly configured plugin directory does not exist: '{plugin_path}'",
                        parameter_name="plugin_dirs",
                        invalid_path=str(plugin_path),
                    )

                # T038: Parse plugin manifest
                manifest = discover_plugin_manifest(plugin_path.resolve())

                if manifest:
                    plugin_name = manifest.name
                else:
                    # No manifest found or parsing failed - use directory name as fallback
                    plugin_name = plugin_path.name
                    logger.warning(
                        f"No valid plugin manifest found at {plugin_path}. "
                        f"Using directory name '{plugin_name}' as plugin identifier."
                    )

                # T062: Check for duplicate plugin names
                if plugin_name in plugin_name_counts:
                    # Duplicate detected - disambiguate with suffix
                    plugin_name_counts[plugin_name] += 1
                    disambiguated_name = f"{plugin_name}-{plugin_name_counts[plugin_name]}"
                    logger.warning(
                        f"Duplicate plugin name '{plugin_name}' detected. "
                        f"Disambiguating as '{disambiguated_name}' for plugin at {plugin_path}. "
                        f"Consider renaming the plugin to avoid conflicts."
                    )
                    plugin_name = disambiguated_name
                else:
                    plugin_name_counts[plugin_name] = 1

                # Create plugin source with disambiguated name
                sources.append(
                    SkillSource(
                        source_type=SourceType.PLUGIN,
                        directory=plugin_path.resolve(),
                        priority=PRIORITY_PLUGIN,
                        plugin_name=plugin_name,
                        plugin_manifest=manifest,
                    )
                )

        # Additional search paths (lowest priority, with validation)
        if additional_search_paths:
            for i, search_path in enumerate(additional_search_paths):
                custom_path = Path(search_path) if isinstance(search_path, str) else search_path

                # Validate explicit custom path exists
                if not custom_path.exists() or not custom_path.is_dir():
                    raise ConfigurationError(
                        f"Explicitly configured custom directory does not exist: '{custom_path}'",
                        parameter_name="additional_search_paths",
                        invalid_path=str(custom_path),
                    )

                sources.append(
                    SkillSource(
                        source_type=SourceType.CUSTOM,
                        directory=custom_path.resolve(),
                        priority=PRIORITY_CUSTOM_BASE - i,  # Decrement for each additional path
                    )
                )

        # Sort by priority (descending)
        sources.sort(key=lambda s: s.priority, reverse=True)

        # INFO logging when no sources configured (not an error, just informational)
        if not sources:
            logger.info("No skill directories found; initialized with empty skill list")

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

        logger.info("Starting multi-source skill discovery (sync mode)")

        # Clear existing skills
        self._skills.clear()
        self._plugin_skills.clear()

        # T027: Multi-source discovery loop in priority order
        total_skills_found = 0
        for source in self.sources:
            logger.debug(
                f"Scanning source: {source.source_type.value} at {source.directory} (priority: {source.priority})"
            )

            # Discover skills from this source
            skill_files = self._discovery.discover_skills(source)

            if not skill_files:
                logger.debug(f"No skills found in {source.directory}")
                continue

            # Parse each skill file (graceful degradation)
            for skill_file in skill_files:
                try:
                    metadata = self._parser.parse_skill_file(skill_file)

                    # T040: Plugin skills - add to plugin namespace registry
                    if source.source_type == SourceType.PLUGIN and source.plugin_name:
                        plugin_name = source.plugin_name

                        # Initialize plugin namespace if not exists
                        if plugin_name not in self._plugin_skills:
                            self._plugin_skills[plugin_name] = {}

                        # Store in plugin namespace
                        self._plugin_skills[plugin_name][metadata.name] = metadata
                        logger.debug(
                            f"Registered plugin skill: {plugin_name}:{metadata.name} from {source.directory}"
                        )

                    # T028/T060: Check for duplicate names (conflict detection with enhanced logging)
                    if metadata.name in self._skills:
                        existing_metadata = self._skills[metadata.name]

                        # Find the source of the existing skill
                        existing_source = None
                        for s in self.sources:
                            if str(s.directory) in str(existing_metadata.skill_path):
                                existing_source = s
                                break

                        # T060: Enhanced conflict logging with all paths and resolution details
                        existing_source_type = (
                            existing_source.source_type.value if existing_source else "unknown"
                        )
                        existing_priority = (
                            existing_source.priority if existing_source else "unknown"
                        )

                        # Build qualified name hint
                        qualified_hint = ""
                        if source.source_type == SourceType.PLUGIN and source.plugin_name:
                            qualified_hint = f" Use qualified name '{source.plugin_name}:{metadata.name}' to access the ignored version."

                        logger.warning(
                            f"Skill name conflict detected for '{metadata.name}':\n"
                            f"  KEEPING: {existing_metadata.skill_path} "
                            f"(source: {existing_source_type}, priority: {existing_priority})\n"
                            f"  IGNORING: {skill_file} "
                            f"(source: {source.source_type.value}, priority: {source.priority})\n"
                            f"  RESOLUTION: Higher priority source wins.{qualified_hint}"
                        )
                        continue

                    # T029: Add to main registry (highest priority wins - sources already sorted)
                    self._skills[metadata.name] = metadata
                    logger.debug(
                        f"Registered skill: {metadata.name} from {source.source_type.value}"
                    )
                    total_skills_found += 1

                except SkillsUseError as e:
                    # Log parsing errors but continue with other skills
                    logger.error(f"Failed to parse skill at {skill_file}: {e}", exc_info=True)
                except Exception as e:
                    # Catch unexpected errors
                    logger.error(f"Unexpected error parsing {skill_file}: {e}", exc_info=True)

        logger.info(
            f"Discovery complete: {total_skills_found} skill(s) registered from {len(self.sources)} source(s)"
        )

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

        logger.info("Starting multi-source skill discovery (async mode)")

        # Clear existing skills
        self._skills.clear()
        self._plugin_skills.clear()

        # T032: Multi-source discovery loop in priority order (async version)
        total_skills_found = 0
        for source in self.sources:
            logger.debug(
                f"Scanning source: {source.source_type.value} at {source.directory} (priority: {source.priority})"
            )

            # Discover skills from this source asynchronously
            skill_files = await self._discovery.adiscover_skills(source)

            if not skill_files:
                logger.debug(f"No skills found in {source.directory}")
                continue

            # Parse each skill file (graceful degradation)
            for skill_file in skill_files:
                try:
                    metadata = self._parser.parse_skill_file(skill_file)

                    # T040: Plugin skills - add to plugin namespace registry
                    if source.source_type == SourceType.PLUGIN and source.plugin_name:
                        plugin_name = source.plugin_name

                        # Initialize plugin namespace if not exists
                        if plugin_name not in self._plugin_skills:
                            self._plugin_skills[plugin_name] = {}

                        # Store in plugin namespace
                        self._plugin_skills[plugin_name][metadata.name] = metadata
                        logger.debug(
                            f"Registered plugin skill: {plugin_name}:{metadata.name} from {source.directory}"
                        )

                    # T060: Check for duplicate names (conflict detection with enhanced logging)
                    if metadata.name in self._skills:
                        existing_metadata = self._skills[metadata.name]

                        # Find the source of the existing skill
                        existing_source = None
                        for s in self.sources:
                            if str(s.directory) in str(existing_metadata.skill_path):
                                existing_source = s
                                break

                        # T060: Enhanced conflict logging with all paths and resolution details
                        existing_source_type = (
                            existing_source.source_type.value if existing_source else "unknown"
                        )
                        existing_priority = (
                            existing_source.priority if existing_source else "unknown"
                        )

                        # Build qualified name hint
                        qualified_hint = ""
                        if source.source_type == SourceType.PLUGIN and source.plugin_name:
                            qualified_hint = f" Use qualified name '{source.plugin_name}:{metadata.name}' to access the ignored version."

                        logger.warning(
                            f"Skill name conflict detected for '{metadata.name}':\n"
                            f"  KEEPING: {existing_metadata.skill_path} "
                            f"(source: {existing_source_type}, priority: {existing_priority})\n"
                            f"  IGNORING: {skill_file} "
                            f"(source: {source.source_type.value}, priority: {source.priority})\n"
                            f"  RESOLUTION: Higher priority source wins.{qualified_hint}"
                        )
                        continue

                    # Add to registry (highest priority wins - sources already sorted)
                    self._skills[metadata.name] = metadata
                    logger.debug(
                        f"Registered skill: {metadata.name} from {source.source_type.value}"
                    )
                    total_skills_found += 1

                except SkillsUseError as e:
                    # Log parsing errors but continue with other skills
                    logger.error(f"Failed to parse skill at {skill_file}: {e}", exc_info=True)
                except Exception as e:
                    # Catch unexpected errors
                    logger.error(f"Unexpected error parsing {skill_file}: {e}", exc_info=True)

        logger.info(
            f"Async discovery complete: {total_skills_found} skill(s) registered from {len(self.sources)} source(s)"
        )

    def list_skills(self, include_qualified: bool = False) -> List[SkillMetadata] | List[str]:
        """Return all discovered skill metadata (lightweight).

        Args:
            include_qualified: If True, return list of skill names (str) including qualified names
                              for conflicting plugin skills. If False, return list of SkillMetadata instances.

        Returns:
            List of SkillMetadata instances (if include_qualified=False)
            OR List of skill names (str) including qualified names for conflicts (if include_qualified=True)

        Performance:
            - O(n) where n = number of skills
            - Copies internal list (~1-5ms for 100 skills)

        Example:
            >>> # Get metadata objects (default)
            >>> skills = manager.list_skills()
            >>> for skill in skills:
            ...     print(f"{skill.name}: {skill.description}")
            code-reviewer: Review code for best practices
            git-helper: Generate commit messages

            >>> # Get skill names with qualified names for conflicts
            >>> names = manager.list_skills(include_qualified=True)
            >>> for name in names:
            ...     print(name)
            code-reviewer
            git-helper
            csv-parser  # Simple name (highest priority version)
            data-tools:csv-parser  # Qualified name (plugin version in conflict)
        """
        if not include_qualified:
            return list(self._skills.values())

        # T030/T061: Return skill names including qualified names only for conflicts
        names: List[str] = []

        # Add all simple names from main registry
        names.extend(self._skills.keys())

        # Add qualified plugin names ONLY if they differ from the main registry version
        # (i.e., only for skills that were shadowed by higher-priority sources)
        for plugin_name, plugin_skills in self._plugin_skills.items():
            for skill_name, skill_metadata in plugin_skills.items():
                # Check if this plugin skill is different from the one in main registry
                if skill_name in self._skills:
                    # Conflict exists - check if plugin version is the same as main version
                    main_skill = self._skills[skill_name]
                    if main_skill.skill_path != skill_metadata.skill_path:
                        # Different version - add qualified name
                        qualified_name = f"{plugin_name}:{skill_name}"
                        names.append(qualified_name)
                # If skill_name not in main registry, the plugin skill IS the main version
                # (no conflict), so we don't need to add a qualified name

        return names

    def get_skill(self, name: str) -> SkillMetadata:
        """Get skill metadata by name (strict validation).

        Supports both simple names and fully qualified names (plugin:skill).

        Args:
            name: Skill name (case-sensitive) - either simple "skill" or qualified "plugin:skill"

        Returns:
            SkillMetadata instance

        Raises:
            SkillNotFoundError: If skill name not in registry

        Performance:
            - O(1) dictionary lookup (~1μs)

        Example:
            >>> # Simple name lookup
            >>> metadata = manager.get_skill("code-reviewer")
            >>> print(metadata.description)
            Review code for best practices

            >>> # Qualified name lookup (plugin skill)
            >>> metadata = manager.get_skill("data-tools:csv-parser")
            >>> print(metadata.description)
            Parse CSV files

            >>> manager.get_skill("nonexistent")
            SkillNotFoundError: Skill 'nonexistent' not found
        """
        from skillkit.core.models import QualifiedSkillName

        # T031: Parse QualifiedSkillName and support qualified lookups
        try:
            parsed = QualifiedSkillName.parse(name)
        except ValueError as e:
            # Convert validation errors to SkillNotFoundError for consistent API
            raise SkillNotFoundError(str(e)) from e

        # If qualified name (plugin:skill)
        if parsed.plugin is not None:
            # Look in plugin skills registry
            if parsed.plugin not in self._plugin_skills:
                available_plugins = (
                    ", ".join(self._plugin_skills.keys()) if self._plugin_skills else "none"
                )
                raise SkillNotFoundError(
                    f"Plugin '{parsed.plugin}' not found. Available plugins: {available_plugins}"
                )

            if parsed.skill not in self._plugin_skills[parsed.plugin]:
                available_skills = ", ".join(self._plugin_skills[parsed.plugin].keys())
                raise SkillNotFoundError(
                    f"Skill '{parsed.skill}' not found in plugin '{parsed.plugin}'. "
                    f"Available skills in this plugin: {available_skills}"
                )

            return self._plugin_skills[parsed.plugin][parsed.skill]

        # Simple name lookup
        if parsed.skill not in self._skills:
            available = ", ".join(self._skills.keys()) if self._skills else "none"
            raise SkillNotFoundError(
                f"Skill '{parsed.skill}' not found. Available skills: {available}"
            )

        return self._skills[parsed.skill]

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
