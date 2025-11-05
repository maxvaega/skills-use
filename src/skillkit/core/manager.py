"""Skill manager orchestration layer.

This module provides the SkillManager class, the main entry point for
skill discovery, access, and invocation.
"""

import logging
from pathlib import Path
from typing import Dict, List

from skillkit.core.discovery import SkillDiscovery
from skillkit.core.exceptions import SkillNotFoundError, SkillsUseError
from skillkit.core.models import Skill, SkillMetadata
from skillkit.core.parser import SkillParser

logger = logging.getLogger(__name__)


class SkillManager:
    """Central skill registry with discovery and invocation capabilities.

    Discovery: Graceful degradation (log errors, continue processing)
    Invocation: Strict validation (raise specific exceptions)
    Thread-safety: Not guaranteed in v0.1 (single-threaded usage assumed)

    Attributes:
        skills_dir: Root directory for skill discovery
        _skills: Internal skill registry (name → metadata)
        _parser: YAML frontmatter parser
        _discovery: Filesystem scanner
    """

    def __init__(self, skills_dir: Path | str | None = None) -> None:
        """Initialize skill manager.

        Args:
            skills_dir: Path to skills directory (default: ./.claude/skills/)
                       Can be either a Path object or a string path.

        Example:
            >>> from pathlib import Path
            >>> manager = SkillManager()  # Uses ./.claude/skills/ (current directory)
            >>> custom_manager = SkillManager(Path("/custom/skills"))
            >>> str_manager = SkillManager("/custom/skills")  # String also works
        """
        if skills_dir is None:
            skills_dir = Path.cwd() / ".claude" / "skills"
        elif isinstance(skills_dir, str):
            skills_dir = Path(skills_dir)

        self.skills_dir = skills_dir
        self._skills: Dict[str, SkillMetadata] = {}
        self._parser = SkillParser()
        self._discovery = SkillDiscovery()

    def discover(self) -> None:
        """Discover skills from skills_dir (graceful degradation).

        Behavior:
            - Scans skills_dir for subdirectories containing SKILL.md files
            - Parses YAML frontmatter and validates required fields
            - Continues processing even if individual skills fail parsing
            - Logs errors via module logger (skillkit.core.manager)
            - Handles duplicates: first discovered wins, logs WARNING

        Side Effects:
            - Populates internal _skills registry
            - Logs errors for malformed skills
            - Logs INFO if directory empty
            - Logs WARNING for duplicate skill names

        Raises:
            No exceptions raised (graceful degradation)

        Performance:
            - Target: <500ms for 10 skills
            - Actual: ~5-10ms per skill (dominated by YAML parsing)

        Example:
            >>> manager = SkillManager()
            >>> manager.discover()
            >>> print(f"Found {len(manager.list_skills())} skills")
            Found 5 skills
        """
        logger.info(f"Starting skill discovery in: {self.skills_dir}")

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
