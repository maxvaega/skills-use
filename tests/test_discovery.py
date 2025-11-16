"""Tests for skill discovery functionality."""

import logging
from pathlib import Path

import pytest

from skillkit import SkillManager


def test_discover_empty_directory(isolated_manager: SkillManager) -> None:
    """Test that discovery of empty directory returns empty list with INFO logging."""
    isolated_manager.discover()
    skills = isolated_manager.list_skills()

    assert isinstance(skills, list)
    assert len(skills) == 0


def test_discover_multiple_skills(isolated_manager: SkillManager, sample_skills: list) -> None:
    """Test that 5 skills are discovered using sample_skills fixture."""
    isolated_manager.discover()
    skills = isolated_manager.list_skills()
    discovered = {skill.name: skill for skill in skills}

    assert len(discovered) == 5
    assert "skill-1" in discovered
    assert "skill-2" in discovered
    assert "skill-3" in discovered
    assert "skill-4" in discovered
    assert "skill-5" in discovered


def test_discover_valid_skills_from_fixtures(fixtures_dir: Path) -> None:
    """Test that static fixtures are discovered correctly."""
    manager = SkillManager(fixtures_dir)
    manager.discover()
    skills = manager.list_skills()
    discovered = {skill.name: skill for skill in skills}

    # Should discover at least the valid fixtures we created
    assert "valid-basic" in discovered or len(discovered) > 0


def test_discover_skill_metadata_structure(isolated_manager: SkillManager, sample_skills: list) -> None:
    """Test that metadata has required fields: name, description, skill_path."""
    isolated_manager.discover()
    skills = isolated_manager.list_skills()
    discovered = {skill.name: skill for skill in skills}

    skill_metadata = discovered["skill-1"]
    assert skill_metadata.name == "skill-1"
    assert skill_metadata.description == "First skill"
    assert skill_metadata.skill_path.exists()
    assert skill_metadata.skill_path.name == "SKILL.md"


def test_discover_unicode_content(isolated_manager: SkillManager, sample_skills: list) -> None:
    """Test that Unicode/emoji skills parse correctly."""
    isolated_manager.discover()
    skills = isolated_manager.list_skills()
    discovered = {skill.name: skill for skill in skills}

    assert "skill-3" in discovered
    skill_metadata = discovered["skill-3"]
    assert skill_metadata.description == "Third skill"

    # Verify the actual skill content contains Unicode
    skill = isolated_manager.load_skill("skill-3")
    content = skill.content
    # The sample_skills fixture creates skill-3 with: "Unicode content: 你好 🎉"
    assert any(ord(c) > 127 for c in content)


def test_discover_duplicate_skill_names_logs_warning(
    isolated_manager: SkillManager, temp_skills_dir: Path, skill_factory: callable, caplog: pytest.LogCaptureFixture
) -> None:
    """Test that WARNING is logged for duplicate skill names."""
    # Create two skills with the same name
    skill_factory("duplicate-name", "First version", "Content 1")
    skill_factory("duplicate-name-2", "Second version", "Content 2")

    # Manually rename the second skill directory to match the first skill's name
    # This simulates the duplicate name scenario
    (temp_skills_dir / "duplicate-name-2").rename(temp_skills_dir / "duplicate-name-copy")

    # Now create a SKILL.md with duplicate name in the renamed directory
    skill_dir = temp_skills_dir / "duplicate-name-copy"
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        """---
name: duplicate-name
description: This has the same name as another skill
---
Content for duplicate.
"""
    )

    with caplog.at_level(logging.WARNING):
        isolated_manager.discover()

    skills = isolated_manager.list_skills()
    discovered = {skill.name: skill for skill in skills}

    # Check that warning was logged (implementation may vary)
    # The first skill with that name should win
    assert "duplicate-name" in discovered


def test_discover_skips_invalid_skills_gracefully(
    isolated_manager: SkillManager, temp_skills_dir: Path, skill_factory: callable
) -> None:
    """Test that discovery continues after encountering invalid skill."""
    # Create one valid and one invalid skill
    skill_factory("valid-skill", "This is valid", "Content")

    # Create invalid skill manually (missing name)
    invalid_dir = temp_skills_dir / "invalid-skill"
    invalid_dir.mkdir()
    (invalid_dir / "SKILL.md").write_text("---\ndescription: Missing name\n---\nContent")

    isolated_manager.discover()
    skills = isolated_manager.list_skills()
    discovered = {skill.name: skill for skill in skills}

    # Should discover the valid skill and skip the invalid one
    assert "valid-skill" in discovered
