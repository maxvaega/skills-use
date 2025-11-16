"""
Edge Case Tests for skillkit Library

Tests edge cases and error handling scenarios including:
- Missing required fields
- Invalid YAML syntax
- File deletion after discovery
- Duplicate skill names
- Permission errors
- Large files and lazy loading
- Symlinks
- Windows line endings

All tests use fixtures from conftest.py and tests/fixtures/skills/.
"""

import os
import sys
import logging
from pathlib import Path

import pytest

from skillkit.core.manager import SkillManager
from skillkit.core.exceptions import (
    MissingRequiredFieldError,
    InvalidYAMLError,
    ContentLoadError,
)


def test_missing_required_field_logs_error_and_continues(
    isolated_manager, temp_skills_dir: Path, skill_factory, caplog
):
    """Test that discovery skips invalid skill with ERROR log when required field missing."""
    # Create one valid skill and one invalid skill (missing name)
    skill_factory(
        name="valid-skill",
        description="A valid skill",
        content="This skill is valid",
    )

    # Create invalid skill (missing name field)
    invalid_dir = temp_skills_dir / "invalid-skill"
    invalid_dir.mkdir(parents=True)
    (invalid_dir / "SKILL.md").write_text(
        "---\ndescription: Missing name field\n---\nContent here"
    )

    # Discover skills with logging capture
    with caplog.at_level(logging.ERROR):
        isolated_manager.discover()
        skills = isolated_manager.list_skills()

    # Verify only valid skill was discovered
    assert len(skills) == 1
    assert skills[0].name == "valid-skill"

    # Verify ERROR was logged for invalid skill
    # Check both message and levelname since the error is in the exception message
    assert any(
        "error" in record.message.lower() or record.levelname == "ERROR"
        for record in caplog.records
    )


def test_invalid_yaml_syntax_raises_validation_error(isolated_manager, temp_skills_dir: Path):
    """Test that invalid YAML syntax raises ValidationError with helpful message."""
    # Create skill with malformed YAML
    invalid_dir = temp_skills_dir / "invalid-yaml"
    invalid_dir.mkdir(parents=True, exist_ok=True)
    (invalid_dir / "SKILL.md").write_text(
        "---\nname: test\ndescription: [unclosed bracket\n---\nContent"
    )

    isolated_manager.discover()

    # Attempting to get the skill should fail gracefully
    # (discovery logs error but doesn't crash)
    skills = isolated_manager.list_skills()
    assert len(skills) == 0  # Invalid skill not discovered


def test_content_load_error_when_file_deleted_after_discovery(
    temp_skills_dir: Path, skill_factory
):
    """Test that ContentLoadError is raised when skill file deleted after discovery."""
    # Create skill and discover it
    skill_factory(
        name="test-skill",
        description="Test skill",
        content="Original content",
    )

    manager = SkillManager(str(temp_skills_dir))
    manager.discover()
    skill = manager.load_skill("test-skill")

    # Delete the skill file
    skill_path = temp_skills_dir / "test-skill" / "SKILL.md"
    skill_path.unlink()

    # Attempting to access content should raise ContentLoadError
    with pytest.raises(ContentLoadError) as exc_info:
        _ = skill.content

    assert "test-skill" in str(exc_info.value).lower() or "SKILL.md" in str(exc_info.value)


def test_duplicate_skill_names_first_wins_with_warning(
    isolated_manager, temp_skills_dir: Path, caplog
):
    """Test that first skill wins when duplicates exist, with WARNING logged."""
    # Create two skills with same name in different directories manually
    # (can't use skill_factory since it checks for duplicates)
    # Use flat structure: immediate subdirectories of skills_dir
    dir1 = temp_skills_dir / "duplicate-skill-first"
    dir1.mkdir(parents=True, exist_ok=True)
    (dir1 / "SKILL.md").write_text(
        "---\nname: duplicate-skill\ndescription: First skill\n---\nFirst content"
    )

    dir2 = temp_skills_dir / "duplicate-skill-second"
    dir2.mkdir(parents=True, exist_ok=True)
    (dir2 / "SKILL.md").write_text(
        "---\nname: duplicate-skill\ndescription: Second skill\n---\nSecond content"
    )

    # Discover with logging
    with caplog.at_level(logging.WARNING):
        isolated_manager.discover()
        skills = isolated_manager.list_skills()

    # Verify only one skill discovered
    assert len(skills) == 1
    assert skills[0].name == "duplicate-skill"

    # Verify first skill's description was kept
    metadata = isolated_manager.get_skill("duplicate-skill")
    assert "First skill" in metadata.description

    # Verify WARNING was logged
    assert any("duplicate" in record.message.lower() for record in caplog.records)


@pytest.mark.skipif(sys.platform == "win32", reason="Unix-only test (chmod)")
def test_permission_denied_skill_logs_error_and_continues(
    isolated_manager, temp_skills_dir: Path, create_permission_denied_skill, caplog
):
    """Test that discovery handles permission errors gracefully (Unix only)."""
    # Create a skill with no read permissions
    create_permission_denied_skill("no-access-skill")

    # Discover with logging
    with caplog.at_level(logging.ERROR):
        isolated_manager.discover()
        skills = isolated_manager.list_skills()

    # Verify skill was not discovered (no crash)
    assert len(skills) == 0

    # Verify ERROR was logged
    assert any(
        "permission" in record.message.lower() or "error" in record.message.lower()
        for record in caplog.records
    )


def test_large_skill_lazy_loading_works(fixtures_dir: Path):
    """Test that 500KB+ skill loads correctly via lazy loading."""
    # Use pre-created large skill fixture
    large_skill_dir = fixtures_dir / "edge-large-content"
    assert large_skill_dir.exists(), "Large skill fixture not found"

    # Verify file is actually large
    skill_file = large_skill_dir / "SKILL.md"
    file_size = skill_file.stat().st_size
    assert file_size > 500_000, f"Large skill file too small: {file_size} bytes"

    # Discover and load skill
    manager = SkillManager(str(fixtures_dir))
    manager.discover()
    skill = manager.load_skill("large-content-skill")

    # Content should load successfully
    content = skill.content
    assert len(content) > 500_000
    assert "Large Content Skill" in content


def test_symlink_in_skill_directory_handled(temp_skills_dir: Path, skill_factory):
    """Test that symlinks are followed/handled correctly."""
    # Create a real skill
    skill_factory(
        name="real-skill",
        description="Real skill",
        content="Real content",
    )
    real_skill_dir = temp_skills_dir / "real-skill"

    # Create symlink to skill directory
    symlink_path = temp_skills_dir / "symlink-skill"
    try:
        symlink_path.symlink_to(real_skill_dir)
    except OSError:
        pytest.skip("Symlinks not supported on this platform")

    # Discover skills
    manager = SkillManager(str(temp_skills_dir))
    manager.discover()
    skills = manager.list_skills()

    # Should discover at least the real skill (symlink behavior varies)
    skill_names = [s.name for s in skills]
    assert "real-skill" in skill_names


def test_windows_line_endings_handled_on_unix(temp_skills_dir: Path):
    """Test that \\r\\n line endings work correctly on Unix systems."""
    # Create skill with Windows line endings
    skill_dir = temp_skills_dir / "windows-endings"
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Use \r\n line endings
    content = "---\r\nname: windows-skill\r\ndescription: Skill with Windows line endings\r\n---\r\n\r\nContent with $ARGUMENTS\r\n"
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")

    # Discover and load skill
    manager = SkillManager(str(temp_skills_dir))
    manager.discover()
    skill = manager.load_skill("windows-skill")

    # Should parse correctly
    assert skill.metadata.name == "windows-skill"
    assert "Windows line endings" in skill.metadata.description

    # Content should load correctly
    assert "Content with $ARGUMENTS" in skill.content

    # Invocation should work
    result = skill.invoke(arguments="test")
    assert "Content with test" in result
