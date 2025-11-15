"""YAML frontmatter parser for SKILL.md files.

This module provides the SkillParser class for extracting and validating
YAML frontmatter from skill files, and plugin manifest parsing functionality.
"""

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict

import yaml

from skillkit.core.exceptions import (
    InvalidFrontmatterError,
    InvalidYAMLError,
    ManifestNotFoundError,
    ManifestParseError,
    ManifestValidationError,
    MissingRequiredFieldError,
)
from skillkit.core.models import PluginManifest, SkillMetadata

logger = logging.getLogger(__name__)

# Security constant: Maximum plugin manifest file size (1 MB)
MAX_MANIFEST_SIZE = 1_000_000  # bytes


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
        from skillkit.core.exceptions import ContentLoadError

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
            problem = getattr(e, "problem", str(e))
            if line:
                raise InvalidYAMLError(
                    f"Invalid YAML syntax in {skill_path} at line {line.line + 1}, "
                    f"column {line.column + 1}: {problem}",
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

    async def _read_manifest_async(self, path: Path) -> str:
        """Async wrapper for reading plugin manifest files.

        Uses asyncio.to_thread() to avoid blocking the event loop during file I/O.

        Args:
            path: Absolute path to plugin.json manifest file

        Returns:
            File content as string

        Raises:
            FileNotFoundError: If manifest file doesn't exist
            PermissionError: If no read permission
            UnicodeDecodeError: If file encoding invalid
        """

        def _read() -> str:
            with open(path, encoding="utf-8") as f:
                return f.read()

        return await asyncio.to_thread(_read)


def parse_plugin_manifest(manifest_path: Path) -> PluginManifest:
    """Parse and validate plugin.json manifest with security checks.

    This function parses a plugin manifest file (.claude-plugin/plugin.json)
    following the MCPB (Model Context Protocol Bundle) specification v0.3.

    Security Features:
        - JSON bomb protection via file size limit (1MB)
        - Path traversal prevention in skills field
        - Required field validation
        - Format validation (semver, author structure, etc.)

    Args:
        manifest_path: Absolute path to plugin.json file

    Returns:
        PluginManifest instance with validated data

    Raises:
        ManifestNotFoundError: If manifest file doesn't exist
        ManifestParseError: If file is too large or JSON parsing fails
        ManifestValidationError: If required fields missing or validation fails
        (raised from PluginManifest.__post_init__)

    Example:
        >>> manifest_path = Path("./plugins/my-plugin/.claude-plugin/plugin.json")
        >>> manifest = parse_plugin_manifest(manifest_path)
        >>> print(f"{manifest.name} v{manifest.version}")
        my-plugin v1.0.0

    Reference:
        MCPB Manifest Specification:
        https://github.com/modelcontextprotocol/mcpb/blob/main/MANIFEST.md
    """
    # Check file exists
    if not manifest_path.exists():
        raise ManifestNotFoundError(
            f"Plugin manifest not found: {manifest_path}\n"
            f"Expected location: .claude-plugin/plugin.json"
        )

    # SECURITY: Check file size (JSON bomb prevention)
    file_size = manifest_path.stat().st_size
    if file_size > MAX_MANIFEST_SIZE:
        raise ManifestParseError(
            f"Manifest too large: {file_size:,} bytes (max {MAX_MANIFEST_SIZE:,})",
            manifest_path=str(manifest_path),
        )

    # Parse JSON with error handling
    try:
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ManifestParseError(
            f"Invalid JSON in {manifest_path.name}:\n  Line {e.lineno}, Column {e.colno}: {e.msg}",
            manifest_path=str(manifest_path),
            parse_error=e,
        ) from e
    except UnicodeDecodeError as e:
        raise ManifestParseError(
            f"Manifest file contains invalid UTF-8: {manifest_path}",
            manifest_path=str(manifest_path),
            parse_error=e,
        ) from e
    except OSError as e:
        raise ManifestParseError(
            f"Failed to read manifest file: {manifest_path}",
            manifest_path=str(manifest_path),
            parse_error=e,
        ) from e

    # Validate data is a dictionary
    if not isinstance(data, dict):
        raise ManifestValidationError(
            f"Manifest must be a JSON object, got {type(data).__name__}",
            field_name="root",
            invalid_value=str(type(data).__name__),
        )

    # Validate required fields
    required = ["name", "version", "description", "author"]
    missing = [f for f in required if f not in data]
    if missing:
        raise ManifestValidationError(
            f"Missing required fields: {', '.join(missing)}\nRequired: {', '.join(required)}",
            field_name=missing[0] if missing else None,
        )

    # Extract manifest_version (optional, defaults to "0.1")
    manifest_version = data.get("manifest_version", "0.1")

    # Normalize skills field
    skills = data.get("skills", ["skills/"])
    if isinstance(skills, str):
        skills = [skills]
    elif not isinstance(skills, list):
        raise ManifestValidationError(
            f"'skills' must be string or array, got {type(skills).__name__}",
            field_name="skills",
            invalid_value=str(type(skills).__name__),
        )

    # Validate author is dict or string
    author = data["author"]
    if isinstance(author, str):
        # Convert string to dict format
        author = {"name": author}
    elif isinstance(author, dict):
        # Already in dict format
        pass
    else:
        raise ManifestValidationError(
            f"'author' must be string or object, got {type(author).__name__}",
            field_name="author",
            invalid_value=str(type(author).__name__),
        )

    # Build manifest (validation happens in __post_init__)
    try:
        return PluginManifest(
            manifest_version=manifest_version,
            name=data["name"],
            version=data["version"],
            description=data["description"],
            author=author,
            skills=skills,
            manifest_path=manifest_path,
            display_name=data.get("display_name"),
            homepage=data.get("homepage"),
            repository=data.get("repository"),
        )
    except ManifestValidationError:
        # Re-raise validation errors from __post_init__
        raise
    except Exception as e:
        # Catch unexpected errors and wrap them
        raise ManifestParseError(
            f"Unexpected error parsing manifest: {e}",
            manifest_path=str(manifest_path),
            parse_error=e,
        ) from e
