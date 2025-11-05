"""YAML frontmatter parser for SKILL.md files.

This module provides the SkillParser class for extracting and validating
YAML frontmatter from skill files.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict

import yaml

from skills_use.core.exceptions import (
    InvalidFrontmatterError,
    InvalidYAMLError,
    MissingRequiredFieldError,
)
from skills_use.core.models import SkillMetadata

logger = logging.getLogger(__name__)


class SkillParser:
    """YAML frontmatter parser for SKILL.md files.

    Parses YAML frontmatter delimited by --- markers, validates required
    fields, and provides helpful error messages with line/column details.
    """

    # Cross-platform regex for frontmatter extraction (handles \n and \r\n)
    FRONTMATTER_PATTERN = re.compile(r"^---[\r\n]+(.*?)[\r\n]+---", re.DOTALL | re.MULTILINE)

    # Typo detection map (common mistakes → correct field names)
    TYPO_MAP = {
        "allowed_tools": "allowed-tools",
        "allowedTools": "allowed-tools",
        "allowed_tool": "allowed-tools",
        "tools": "allowed-tools",
    }

    def parse_skill_file(self, skill_path: Path) -> SkillMetadata:
        """Parse SKILL.md file and return metadata.

        Args:
            skill_path: Absolute path to SKILL.md file

        Returns:
            SkillMetadata instance with parsed fields

        Raises:
            InvalidFrontmatterError: If frontmatter structure invalid
            InvalidYAMLError: If YAML syntax error
            MissingRequiredFieldError: If required fields missing
            ContentLoadError: If file cannot be read

        Example:
            >>> parser = SkillParser()
            >>> metadata = parser.parse_skill_file(Path("skill/SKILL.md"))
            >>> print(f"{metadata.name}: {metadata.description}")
            code-reviewer: Review code for best practices
        """
        from skills_use.core.exceptions import ContentLoadError

        # Read file with UTF-8-sig encoding (auto-strips BOM)
        try:
            content = skill_path.read_text(encoding="utf-8-sig")
        except FileNotFoundError as e:
            raise ContentLoadError(f"Skill file not found: {skill_path}") from e
        except PermissionError as e:
            raise ContentLoadError(f"Permission denied: {skill_path}") from e
        except UnicodeDecodeError as e:
            raise ContentLoadError(f"Skill file contains invalid UTF-8: {skill_path}") from e

        # Extract frontmatter
        frontmatter_dict = self._extract_frontmatter(content, skill_path)

        # Detect and warn about typos
        self._check_for_typos(frontmatter_dict, skill_path)

        # Validate and extract required fields
        name = self._extract_required_field(frontmatter_dict, "name", skill_path)
        description = self._extract_required_field(frontmatter_dict, "description", skill_path)

        # Extract optional fields
        allowed_tools = self._extract_allowed_tools(frontmatter_dict, skill_path)

        logger.debug(f"Successfully parsed skill '{name}' from {skill_path.parent.name}")

        return SkillMetadata(
            name=name,
            description=description,
            skill_path=skill_path,
            allowed_tools=allowed_tools,
        )

    def _extract_frontmatter(self, content: str, skill_path: Path) -> Dict[str, Any]:
        """Extract and parse YAML frontmatter from content.

        Args:
            content: Full SKILL.md file content
            skill_path: Path to skill file (for error messages)

        Returns:
            Parsed frontmatter as dictionary

        Raises:
            InvalidFrontmatterError: If frontmatter structure invalid
            InvalidYAMLError: If YAML syntax error
        """
        # Check for frontmatter delimiters
        match = self.FRONTMATTER_PATTERN.match(content)
        if not match:
            raise InvalidFrontmatterError(
                f"Skill file missing YAML frontmatter delimiters (---): {skill_path}"
            )

        frontmatter_text = match.group(1)

        # Parse YAML with detailed error extraction
        try:
            frontmatter_dict = yaml.safe_load(frontmatter_text)
        except yaml.YAMLError as e:
            # Extract line/column if available
            line = getattr(e, "problem_mark", None)
            if line:
                raise InvalidYAMLError(
                    f"Invalid YAML syntax in {skill_path} at line {line.line + 1}, "
                    f"column {line.column + 1}: {e.problem}",
                    line=line.line + 1,
                    column=line.column + 1,
                ) from e
            else:
                raise InvalidYAMLError(f"Invalid YAML syntax in {skill_path}: {e}") from e

        # Validate frontmatter is a dictionary
        if not isinstance(frontmatter_dict, dict):
            raise InvalidFrontmatterError(
                f"Frontmatter must be a YAML dictionary, got {type(frontmatter_dict).__name__}: {skill_path}"
            )

        return frontmatter_dict

    def _extract_required_field(
        self, frontmatter: Dict[str, Any], field_name: str, skill_path: Path
    ) -> str:
        """Extract and validate required string field.

        Args:
            frontmatter: Parsed frontmatter dictionary
            field_name: Name of required field
            skill_path: Path to skill file (for error messages)

        Returns:
            Validated field value (stripped)

        Raises:
            MissingRequiredFieldError: If field missing or empty
        """
        if field_name not in frontmatter:
            raise MissingRequiredFieldError(
                f"Required field '{field_name}' missing in {skill_path}",
                field_name=field_name,
            )

        value = frontmatter[field_name]

        # Validate is string
        if not isinstance(value, str):
            raise MissingRequiredFieldError(
                f"Field '{field_name}' must be a string, got {type(value).__name__} in {skill_path}",
                field_name=field_name,
            )

        # Validate non-empty after stripping
        value = value.strip()
        if not value:
            raise MissingRequiredFieldError(
                f"Field '{field_name}' cannot be empty in {skill_path}",
                field_name=field_name,
            )

        return value

    def _extract_allowed_tools(
        self, frontmatter: Dict[str, Any], skill_path: Path
    ) -> tuple[str, ...]:
        """Extract and validate optional allowed-tools field.

        Args:
            frontmatter: Parsed frontmatter dictionary
            skill_path: Path to skill file (for error messages)

        Returns:
            Tuple of tool names (empty tuple if field missing or invalid)
        """
        if "allowed-tools" not in frontmatter:
            return ()

        allowed_tools = frontmatter["allowed-tools"]

        # Graceful degradation: return empty tuple if not a list
        if not isinstance(allowed_tools, list):
            logger.warning(
                f"Field 'allowed-tools' should be a list, got {type(allowed_tools).__name__} in {skill_path}. "
                f"Using empty tuple."
            )
            return ()

        # Validate all elements are strings
        tools = []
        for tool in allowed_tools:
            if isinstance(tool, str):
                tools.append(tool)
            else:
                logger.warning(
                    f"Ignoring non-string tool '{tool}' in allowed-tools for {skill_path}"
                )

        return tuple(tools)

    def _check_for_typos(self, frontmatter: Dict[str, Any], skill_path: Path) -> None:
        """Check for common field name typos and log warnings.

        Args:
            frontmatter: Parsed frontmatter dictionary
            skill_path: Path to skill file (for error messages)
        """
        for typo, correct in self.TYPO_MAP.items():
            if typo in frontmatter:
                logger.warning(f"Possible typo in {skill_path}: '{typo}' should be '{correct}'")

        # Log unknown fields for forward compatibility
        known_fields = {"name", "description", "allowed-tools"}
        unknown_fields = set(frontmatter.keys()) - known_fields
        if unknown_fields:
            logger.debug(
                f"Unknown fields in {skill_path} (will be ignored): {', '.join(unknown_fields)}"
            )
