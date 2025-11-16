"""
Shared pytest fixtures and configuration for skillkit test suite.

This module provides:
- temp_skills_dir: Temporary directory for test skills
- skill_factory: Factory function for creating SKILL.md files programmatically
- sample_skills: Pre-created set of 5 diverse sample skills
- fixtures_dir: Path to static test fixtures
- isolated_manager: SkillManager with all default discovery disabled (for isolated tests)
- skill_manager_async: Async-initialized SkillManager with example skills
- Helper functions for common assertions and complex skill creation
"""

import os
import sys
from pathlib import Path
from typing import Any, Callable, List, Optional

import pytest

from skillkit.core.models import SkillMetadata


@pytest.fixture
def temp_skills_dir(tmp_path: Path) -> Path:
    """
    Create temporary skills directory for testing.

    Returns:
        Path: Path to temporary skills directory (automatically cleaned up after test)
    """
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    return skills_dir


@pytest.fixture
def skill_factory(temp_skills_dir: Path) -> Callable[..., Path]:
    """
    Factory for creating test SKILL.md files programmatically.

    Args:
        temp_skills_dir: Temporary skills directory fixture

    Returns:
        Callable: Function that creates SKILL.md files

    Example:
        >>> skill_dir = skill_factory("my-skill", "My test skill", "Content here")
        >>> assert (skill_dir / "SKILL.md").exists()
    """
    created_skills: List[Path] = []

    def _create_skill(
        name: str,
        description: str,
        content: str,
        allowed_tools: Optional[List[str]] = None,
        **extra_frontmatter: Any,
    ) -> Path:
        """
        Create a SKILL.md file in temp directory.

        Args:
            name: Skill name (frontmatter field)
            description: Skill description (frontmatter field)
            content: Skill content body (after frontmatter)
            allowed_tools: Optional list of allowed tools
            **extra_frontmatter: Additional YAML fields to include

        Returns:
            Path: Path to created skill directory

        Raises:
            ValueError: If skill directory already exists
        """
        skill_dir = temp_skills_dir / name
        if skill_dir.exists():
            raise ValueError(f"Skill {name} already exists in temp directory")

        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"

        # Build YAML frontmatter
        frontmatter_lines = ["---", f"name: {name}", f"description: {description}"]

        if allowed_tools:
            frontmatter_lines.append(f"allowed-tools: {allowed_tools}")

        for key, value in extra_frontmatter.items():
            frontmatter_lines.append(f"{key}: {value}")

        frontmatter_lines.append("---")
        frontmatter = "\n".join(frontmatter_lines)

        # Write file
        skill_file.write_text(f"{frontmatter}\n\n{content}", encoding="utf-8")
        created_skills.append(skill_dir)

        return skill_dir

    return _create_skill


@pytest.fixture
def sample_skills(skill_factory: Callable[..., Path]) -> List[Path]:
    """
    Create 5 diverse sample skills for discovery tests.

    Returns:
        List[Path]: List of paths to created skill directories
    """
    skills = [
        skill_factory("skill-1", "First skill", "Content 1"),
        skill_factory("skill-2", "Second skill", "Content 2 with $ARGUMENTS"),
        skill_factory("skill-3", "Third skill", "Unicode content: 你好 🎉"),
        skill_factory("skill-4", "Fourth skill", "Long content " * 100),
        skill_factory("skill-5", "Fifth skill", "Special chars: <>&\"'"),
    ]
    return skills


@pytest.fixture
def fixtures_dir() -> Path:
    """
    Return path to static test fixtures directory.

    Returns:
        Path: Path to tests/fixtures/skills/ directory
    """
    return Path(__file__).parent / "fixtures" / "skills"


# Helper Functions


def assert_skill_metadata_valid(metadata: SkillMetadata) -> None:
    """
    Helper to validate SkillMetadata structure.

    Args:
        metadata: SkillMetadata instance to validate

    Raises:
        AssertionError: If metadata is invalid
    """
    assert metadata.name, "Metadata name should not be empty"
    assert metadata.description, "Metadata description should not be empty"
    assert metadata.skill_path.exists(), f"Skill path {metadata.skill_path} should exist"
    assert (
        metadata.skill_path.name == "SKILL.md"
    ), f"Skill path should end with SKILL.md, got {metadata.skill_path.name}"


def create_large_skill(temp_skills_dir: Path, size_kb: int = 500) -> Path:
    """
    Create a skill with large content (for lazy loading tests).

    Args:
        temp_skills_dir: Temporary skills directory
        size_kb: Size of content in kilobytes (default: 500KB)

    Returns:
        Path: Path to created skill directory
    """
    skill_dir = temp_skills_dir / "large-skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"

    frontmatter = """---
name: large-skill
description: Large skill for testing lazy loading
---

"""
    # Generate content to reach desired size
    content_chunk = "This is a large skill content. " * 100  # ~3KB per chunk
    chunks_needed = (size_kb * 1024) // len(content_chunk.encode("utf-8"))
    large_content = content_chunk * chunks_needed

    skill_file.write_text(frontmatter + large_content, encoding="utf-8")
    return skill_dir


@pytest.fixture
def create_permission_denied_skill(temp_skills_dir: Path) -> Callable[[str], Path]:
    """
    Fixture that returns a factory for creating skills with permission denied (Unix-only).

    Returns:
        Callable: Function that creates SKILL.md files with no read permissions

    Note:
        This function only works on Unix-like systems. Tests using this
        should be marked with @pytest.mark.skipif(sys.platform == "win32")
    """

    def _create_permission_denied(skill_name: str) -> Path:
        """Create a skill with no read permissions.

        Args:
            skill_name: Name of the skill directory

        Returns:
            Path: Path to created skill directory
        """
        skill_dir = temp_skills_dir / skill_name
        skill_dir.mkdir(exist_ok=True)
        skill_file = skill_dir / "SKILL.md"

        frontmatter = f"""---
name: {skill_name}
description: Skill with no read permissions
---

This skill should trigger a permission error.
"""
        skill_file.write_text(frontmatter, encoding="utf-8")

        # Remove read permissions (Unix-only)
        if sys.platform != "win32":
            os.chmod(skill_file, 0o000)

        return skill_dir

    return _create_permission_denied


@pytest.fixture
def skills_directory() -> Path:
    """
    Return path to example skills directory.

    Returns:
        Path: Path to examples/skills/ directory with test skills
    """
    return Path(__file__).parent.parent / "examples" / "skills"


@pytest.fixture
def isolated_manager(temp_skills_dir: Path):
    """
    Create a SkillManager with all default discovery disabled (isolated testing).

    This fixture creates a manager that ONLY discovers skills from the temp_skills_dir,
    explicitly opting out of:
    - Anthropic config directory (./.claude/skills/)
    - Plugin discovery
    - Additional search paths

    Returns:
        SkillManager: Manager configured for isolated testing (not yet discovered)

    Usage:
        >>> def test_my_feature(isolated_manager, skill_factory):
        ...     skill_factory("test-skill", "Test description", "Content")
        ...     isolated_manager.discover()
        ...     assert len(isolated_manager.list_skills()) == 1  # Only finds test-skill

    Note:
        This manager uses temp_skills_dir as project_skill_dir. Call discover()
        after setting up your test skills with skill_factory.
    """
    from skillkit import SkillManager

    return SkillManager(
        project_skill_dir=temp_skills_dir,
        anthropic_config_dir="",  # Explicit opt-out of default discovery
        plugin_dirs=[],  # Explicit opt-out of plugins
    )


@pytest.fixture
async def skill_manager_async(skills_directory: Path):
    """
    Create and initialize a SkillManager asynchronously.

    Returns:
        SkillManager: Async-initialized manager with discovered skills

    Note:
        This fixture uses async discovery and sets init_mode to ASYNC.
        Use this for testing async invocation and LangChain async integration.
    """
    from skillkit import SkillManager

    manager = SkillManager(skills_directory)
    await manager.adiscover()
    return manager
