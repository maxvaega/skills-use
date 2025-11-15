"""Skill discovery module for filesystem scanning.

This module provides the SkillDiscovery class for scanning directories
and locating SKILL.md files.
"""

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from skillkit.core.models import SkillSource

logger = logging.getLogger(__name__)


class SkillDiscovery:
    """Filesystem scanner for discovering SKILL.md files.

    Supports flat directory structure (.claude/skills/skill-name/SKILL.md)
    with case-insensitive SKILL.md matching.
    """

    SKILL_FILE_NAME = "SKILL.md"

    def discover_skills(self, source: "SkillSource") -> List[Path]:
        """Discover skills from a specific source.

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

    def find_skill_files(self, skills_dir: Path) -> List[Path]:
        """Find SKILL.md files in immediate subdirectories.

        Performs case-insensitive matching for SKILL.md filename
        to support cross-platform compatibility.

        Args:
            skills_dir: Directory to search

        Returns:
            List of absolute paths to SKILL.md files

        Example:
            >>> discovery = SkillDiscovery()
            >>> files = discovery.find_skill_files(Path(".claude/skills"))
            >>> for skill_file in files:
            ...     print(f"Found: {skill_file}")
            Found: /home/user/.claude/skills/code-reviewer/SKILL.md
            Found: /home/user/.claude/skills/git-helper/SKILL.md
        """
        skill_files: List[Path] = []

        try:
            # Iterate through immediate subdirectories only
            for subdir in skills_dir.iterdir():
                if not subdir.is_dir():
                    continue

                # Look for SKILL.md file (case-insensitive)
                for file in subdir.iterdir():
                    if file.name.upper() == self.SKILL_FILE_NAME.upper():
                        skill_files.append(file.absolute())
                        logger.debug(f"Found skill file: {file}")
                        break  # Only take first match per directory

        except PermissionError:
            logger.warning(f"Permission denied accessing: {skills_dir}")
        except OSError as e:
            logger.warning(f"Error scanning directory {skills_dir}: {e}")

        logger.info(f"Discovery found {len(skill_files)} skill(s) in {skills_dir}")
        return skill_files

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

    async def afind_skill_files(self, skills_dir: Path) -> List[Path]:
        """Async version of find_skill_files for non-blocking discovery.

        Performs case-insensitive matching for SKILL.md filename
        to support cross-platform compatibility.

        Args:
            skills_dir: Directory to search

        Returns:
            List of absolute paths to SKILL.md files

        Example:
            >>> discovery = SkillDiscovery()
            >>> files = await discovery.afind_skill_files(Path(".claude/skills"))
            >>> for skill_file in files:
            ...     print(f"Found: {skill_file}")
            Found: /home/user/.claude/skills/code-reviewer/SKILL.md
            Found: /home/user/.claude/skills/git-helper/SKILL.md
        """

        def _scan() -> List[Path]:
            """Sync scanning logic wrapped for async execution."""
            skill_files: List[Path] = []

            try:
                # Iterate through immediate subdirectories only
                for subdir in skills_dir.iterdir():
                    if not subdir.is_dir():
                        continue

                    # Look for SKILL.md file (case-insensitive)
                    for file in subdir.iterdir():
                        if file.name.upper() == self.SKILL_FILE_NAME.upper():
                            skill_files.append(file.absolute())
                            logger.debug(f"Found skill file: {file}")
                            break  # Only take first match per directory

            except PermissionError:
                logger.warning(f"Permission denied accessing: {skills_dir}")
            except OSError as e:
                logger.warning(f"Error scanning directory {skills_dir}: {e}")

            logger.info(f"Discovery found {len(skill_files)} skill(s) in {skills_dir}")
            return skill_files

        # Run directory scanning in thread to avoid blocking event loop
        return await asyncio.to_thread(_scan)
