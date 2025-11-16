"""Skill discovery module for filesystem scanning.

This module provides the SkillDiscovery class for scanning directories
and locating SKILL.md files, and plugin manifest discovery functionality.
"""

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from skillkit.core.models import PluginManifest, SkillSource

logger = logging.getLogger(__name__)


class SkillDiscovery:
    """Filesystem scanner for discovering SKILL.md files.

    Supports flat directory structure (.claude/skills/skill-name/SKILL.md)
    with case-insensitive SKILL.md matching.
    """

    SKILL_FILE_NAME = "SKILL.md"

    def discover_skills(self, source: "SkillSource") -> List[Path]:
        """Discover skills from a specific source.

        For plugin sources with manifests, scans all skill directories specified
        in the manifest.skills field. For other sources, scans the source directory directly.

        Args:
            source: SkillSource instance with directory and metadata

        Returns:
            List of absolute paths to SKILL.md files (empty if none found)

        Example:
            >>> from skillkit.core.models import SkillSource, SourceType
            >>> discovery = SkillDiscovery()
            >>> source = SkillSource(
            ...     source_type=SourceType.PROJECT,
            ...     directory=Path("./skills"),
            ...     priority=100
            ... )
            >>> skills = discovery.discover_skills(source)
            >>> print(f"Found {len(skills)} skills from {source.source_type.value}")
            Found 3 skills from project
        """
        from skillkit.core.models import SourceType

        # For plugin sources with manifests, scan all directories listed in manifest.skills
        if source.source_type == SourceType.PLUGIN and source.plugin_manifest:
            all_skill_files: List[Path] = []

            for skill_dir_rel in source.plugin_manifest.skills:
                # Resolve skill directory relative to plugin root
                skill_dir = source.directory / skill_dir_rel

                # Scan this skill directory
                skill_files = self.scan_directory(skill_dir)
                all_skill_files.extend(skill_files)

                logger.debug(f"Found {len(skill_files)} skill(s) in plugin directory {skill_dir}")

            return all_skill_files

        # For non-plugin sources, scan the source directory directly
        return self.scan_directory(source.directory)

    def scan_directory(self, skills_dir: Path) -> List[Path]:
        """Scan skills directory for SKILL.md files.

        Scans only immediate subdirectories (flat structure). Nested
        subdirectories are not supported in v0.1.

        Args:
            skills_dir: Root directory to scan for skills

        Returns:
            List of absolute paths to SKILL.md files (empty if none found)

        Example:
            >>> discovery = SkillDiscovery()
            >>> skills = discovery.scan_directory(Path(".claude/skills"))
            >>> print(f"Found {len(skills)} skills")
            Found 3 skills
        """
        if not skills_dir.exists():
            logger.debug(f"Skills directory does not exist: {skills_dir}")
            return []

        if not skills_dir.is_dir():
            logger.warning(f"Skills path is not a directory: {skills_dir}")
            return []

        return self.find_skill_files(skills_dir)

    def find_skill_files(self, skills_dir: Path, max_depth: int = 5) -> List[Path]:
        """Find SKILL.md files recursively with depth limit.

        Performs case-insensitive matching for SKILL.md filename
        to support cross-platform compatibility. Supports both flat
        and nested directory structures up to max_depth levels.

        Args:
            skills_dir: Directory to search
            max_depth: Maximum nesting depth to search (default: 5, 0 = only immediate subdirectories)

        Returns:
            List of absolute paths to SKILL.md files

        Example:
            >>> discovery = SkillDiscovery()
            >>> # Find skills in immediate subdirectories only
            >>> files = discovery.find_skill_files(Path(".claude/skills"), max_depth=0)
            >>> # Find skills recursively up to 5 levels deep
            >>> files = discovery.find_skill_files(Path(".claude/skills"))
            >>> for skill_file in files:
            ...     print(f"Found: {skill_file}")
            Found: /home/user/.claude/skills/code-reviewer/SKILL.md
            Found: /home/user/.claude/skills/data/csv-parser/SKILL.md
        """
        skill_files: List[Path] = []
        visited_dirs: set[tuple[int, int]] = (
            set()
        )  # Track visited directories to detect circular symlinks

        try:
            # Use recursive search with depth tracking
            self._find_skill_files_recursive(
                skills_dir,
                skill_files,
                visited_dirs,
                current_depth=0,
                max_depth=max_depth,
            )

        except PermissionError:
            logger.warning(f"Permission denied accessing: {skills_dir}")
        except OSError as e:
            logger.warning(f"Error scanning directory {skills_dir}: {e}")

        logger.info(f"Discovery found {len(skill_files)} skill(s) in {skills_dir}")
        return skill_files

    def _find_skill_files_recursive(
        self,
        current_dir: Path,
        skill_files: List[Path],
        visited_dirs: set[tuple[int, int]],
        current_depth: int,
        max_depth: int,
    ) -> None:
        """Recursively find SKILL.md files with depth limit and circular symlink detection.

        Args:
            current_dir: Current directory being scanned
            skill_files: Accumulator list for discovered skill files
            visited_dirs: Set of visited directory inodes to detect circular symlinks
            current_depth: Current recursion depth (0 = root)
            max_depth: Maximum allowed depth

        Note:
            This is an internal helper method. Use find_skill_files() instead.
        """
        # Resolve symlinks and check for circular references
        try:
            resolved_dir = current_dir.resolve(strict=True)
        except (OSError, RuntimeError) as e:
            logger.warning(f"Cannot resolve directory {current_dir}: {e}")
            return

        # Get directory inode for circular symlink detection
        try:
            dir_stat = resolved_dir.stat()
            dir_id = (dir_stat.st_dev, dir_stat.st_ino)
        except OSError as e:
            logger.warning(f"Cannot stat directory {resolved_dir}: {e}")
            return

        # Check for circular symlink
        if dir_id in visited_dirs:
            logger.warning(
                f"Circular symlink detected at {current_dir} -> {resolved_dir}. Skipping."
            )
            return

        visited_dirs.add(dir_id)

        # Warn if depth limit exceeded
        if current_depth > max_depth:
            logger.warning(
                f"Depth limit ({max_depth}) exceeded at {current_dir}. "
                f"Skills deeper than {max_depth} levels will not be discovered. "
                f"Consider reorganizing your skill directory structure."
            )
            return

        # Scan current directory
        try:
            for item in current_dir.iterdir():
                # Check for SKILL.md file (case-insensitive)
                if item.is_file() and item.name.upper() == self.SKILL_FILE_NAME.upper():
                    skill_files.append(item.absolute())
                    logger.debug(f"Found skill file: {item} (depth={current_depth})")

                # Recurse into subdirectories
                elif item.is_dir():
                    self._find_skill_files_recursive(
                        item,
                        skill_files,
                        visited_dirs,
                        current_depth + 1,
                        max_depth,
                    )

        except PermissionError:
            logger.warning(f"Permission denied accessing: {current_dir}")
        except OSError as e:
            logger.warning(f"Error reading directory {current_dir}: {e}")

    async def _read_skill_file_async(self, path: Path) -> str:
        """Async wrapper for reading skill files.

        Uses asyncio.to_thread() to avoid blocking the event loop during file I/O.

        Args:
            path: Absolute path to file to read

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If no read permission
            UnicodeDecodeError: If file encoding invalid
        """

        def _read() -> str:
            with open(path, encoding="utf-8") as f:
                return f.read()

        return await asyncio.to_thread(_read)

    async def adiscover_skills(self, source: "SkillSource") -> List[Path]:
        """Async version of discover_skills for non-blocking skill discovery.

        For plugin sources with manifests, scans all skill directories specified
        in the manifest.skills field. For other sources, scans the source directory directly.

        Args:
            source: SkillSource instance with directory and metadata

        Returns:
            List of absolute paths to SKILL.md files (empty if none found)

        Example:
            >>> from skillkit.core.models import SkillSource, SourceType
            >>> discovery = SkillDiscovery()
            >>> source = SkillSource(
            ...     source_type=SourceType.PROJECT,
            ...     directory=Path("./skills"),
            ...     priority=100
            ... )
            >>> skills = await discovery.adiscover_skills(source)
            >>> print(f"Found {len(skills)} skills from {source.source_type.value}")
            Found 3 skills from project
        """
        from skillkit.core.models import SourceType

        # For plugin sources with manifests, scan all directories listed in manifest.skills
        if source.source_type == SourceType.PLUGIN and source.plugin_manifest:
            all_skill_files: List[Path] = []

            for skill_dir_rel in source.plugin_manifest.skills:
                # Resolve skill directory relative to plugin root
                skill_dir = source.directory / skill_dir_rel

                # Scan this skill directory asynchronously
                skill_files = await self.ascan_directory(skill_dir)
                all_skill_files.extend(skill_files)

                logger.debug(f"Found {len(skill_files)} skill(s) in plugin directory {skill_dir}")

            return all_skill_files

        # For non-plugin sources, scan the source directory directly
        return await self.ascan_directory(source.directory)

    async def ascan_directory(self, skills_dir: Path) -> List[Path]:
        """Async version of scan_directory for non-blocking skill discovery.

        Scans only immediate subdirectories (flat structure). Nested
        subdirectories are not supported in v0.1.

        Args:
            skills_dir: Root directory to scan for skills

        Returns:
            List of absolute paths to SKILL.md files (empty if none found)

        Example:
            >>> discovery = SkillDiscovery()
            >>> skills = await discovery.ascan_directory(Path(".claude/skills"))
            >>> print(f"Found {len(skills)} skills")
            Found 3 skills
        """
        if not skills_dir.exists():
            logger.debug(f"Skills directory does not exist: {skills_dir}")
            return []

        if not skills_dir.is_dir():
            logger.warning(f"Skills path is not a directory: {skills_dir}")
            return []

        return await self.afind_skill_files(skills_dir)

    async def afind_skill_files(self, skills_dir: Path, max_depth: int = 5) -> List[Path]:
        """Async version of find_skill_files for non-blocking discovery.

        Performs case-insensitive matching for SKILL.md filename
        to support cross-platform compatibility. Supports both flat
        and nested directory structures up to max_depth levels.

        Args:
            skills_dir: Directory to search
            max_depth: Maximum nesting depth to search (default: 5, 0 = only immediate subdirectories)

        Returns:
            List of absolute paths to SKILL.md files

        Example:
            >>> discovery = SkillDiscovery()
            >>> files = await discovery.afind_skill_files(Path(".claude/skills"))
            >>> for skill_file in files:
            ...     print(f"Found: {skill_file}")
            Found: /home/user/.claude/skills/code-reviewer/SKILL.md
            Found: /home/user/.claude/skills/data/csv-parser/SKILL.md
        """

        def _scan() -> List[Path]:
            """Sync scanning logic wrapped for async execution."""
            # Delegate to sync implementation
            return self.find_skill_files(skills_dir, max_depth)

        # Run directory scanning in thread to avoid blocking event loop
        return await asyncio.to_thread(_scan)


def discover_plugin_manifest(plugin_dir: Path) -> "PluginManifest | None":
    """Discover and parse plugin manifest if present.

    Scans the plugin directory for .claude-plugin/plugin.json manifest file.
    If found, parses and validates the manifest. If not found or parsing fails,
    returns None with appropriate logging.

    This function implements graceful degradation: malformed manifests are logged
    as warnings but do not halt discovery of other plugins.

    Args:
        plugin_dir: Absolute path to plugin root directory

    Returns:
        PluginManifest instance if manifest found and valid, None otherwise

    Example:
        >>> manifest = discover_plugin_manifest(Path("./plugins/my-plugin"))
        >>> if manifest:
        ...     print(f"Found plugin: {manifest.name} v{manifest.version}")
        ...     for skill_dir in manifest.skills:
        ...         print(f"  - Skill directory: {skill_dir}")
        Found plugin: my-plugin v1.0.0
          - Skill directory: skills/
          - Skill directory: experimental/

    Note:
        This function uses parse_plugin_manifest() which enforces security
        checks (JSON bomb protection, path traversal prevention).
    """
    from skillkit.core.exceptions import (
        ManifestNotFoundError,
        ManifestParseError,
        ManifestValidationError,
    )
    from skillkit.core.parser import parse_plugin_manifest

    # Check for manifest at expected location
    manifest_path = plugin_dir / ".claude-plugin" / "plugin.json"

    if not manifest_path.exists():
        logger.debug(f"No plugin manifest found at {manifest_path}")
        return None

    # Attempt to parse manifest with graceful error handling
    try:
        manifest = parse_plugin_manifest(manifest_path)
        logger.info(
            f"Discovered plugin '{manifest.name}' v{manifest.version} "
            f"with {len(manifest.skills)} skill directory(ies) at {plugin_dir}"
        )
        return manifest

    except ManifestNotFoundError as e:
        # Should not happen since we checked exists() above, but handle anyway
        logger.warning(f"Plugin manifest not found: {e}")
        return None

    except ManifestParseError as e:
        # JSON parsing errors, encoding errors, file size exceeded
        logger.warning(
            f"Failed to parse plugin manifest at {manifest_path}: {e}\n"
            f"Plugin at {plugin_dir} will be skipped."
        )
        return None

    except ManifestValidationError as e:
        # Required fields missing, invalid formats, security violations
        logger.warning(
            f"Plugin manifest validation failed at {manifest_path}: {e}\n"
            f"Plugin at {plugin_dir} will be skipped."
        )
        return None

    except Exception as e:
        # Catch-all for unexpected errors (should not happen, but defensive)
        logger.error(
            f"Unexpected error discovering plugin manifest at {manifest_path}: {e}\n"
            f"Plugin at {plugin_dir} will be skipped.",
            exc_info=True,
        )
        return None
