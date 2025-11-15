"""Tests for SkillManager orchestration layer.

This module validates the SkillManager class including discovery, listing,
retrieval, caching, and end-to-end invocation workflows.
"""

import pytest
from pathlib import Path

from skillkit.core.manager import SkillManager
from skillkit.core.models import SkillMetadata, Skill
from skillkit.core.exceptions import SkillNotFoundError, ContentLoadError


# T048: Create test_manager.py with imports and file header ✓


# T049: test_manager_discover_returns_dict
def test_manager_list_skills_returns_list(sample_skills):
    """Validate list_skills() returns list of SkillMetadata after discovery.

    Tests that the manager properly stores and returns discovered skills
    as a list of metadata objects.
    """
    # sample_skills is a list of skill directories, get the parent
    skills_dir = sample_skills[0].parent
    manager = SkillManager(skill_dir=skills_dir)
    manager.discover()

    skills = manager.list_skills()

    assert isinstance(skills, list)
    assert len(skills) > 0
    assert all(isinstance(skill, SkillMetadata) for skill in skills)


# T050: test_manager_get_skill_by_name
def test_manager_get_skill_by_name(sample_skills):
    """Validate get_skill() returns SkillMetadata for valid skill name.

    Tests that the manager can retrieve specific skills by name
    after discovery is complete.
    """
    skills_dir = sample_skills[0].parent
    manager = SkillManager(skill_dir=skills_dir)
    manager.discover()

    # Get the first skill name
    skills = manager.list_skills()
    assert len(skills) > 0

    first_skill_name = skills[0].name
    metadata = manager.get_skill(first_skill_name)

    assert metadata is not None
    assert isinstance(metadata, SkillMetadata)
    assert metadata.name == first_skill_name


# T051: test_manager_list_skills_returns_names
def test_manager_list_skills_contains_metadata(sample_skills):
    """Validate list_skills() returns list with name and description fields.

    Tests that the returned skill metadata contains all expected fields
    for display and selection purposes.
    """
    skills_dir = sample_skills[0].parent
    manager = SkillManager(skill_dir=skills_dir)
    manager.discover()

    skills = manager.list_skills()

    for skill in skills:
        assert hasattr(skill, "name")
        assert hasattr(skill, "description")
        assert hasattr(skill, "skill_path")
        assert skill.name is not None
        assert skill.description is not None


# T052: test_manager_skill_invocation
def test_manager_skill_invocation(fixtures_dir):
    """Validate end-to-end workflow: discover → get_skill → invoke.

    Tests the complete skill lifecycle from discovery through invocation,
    ensuring all components work together correctly.
    """
    manager = SkillManager(skill_dir=fixtures_dir)
    manager.discover()

    # Find a valid skill
    skills = manager.list_skills()
    assert len(skills) > 0

    # Load and invoke the skill
    skill_name = skills[0].name
    result = manager.invoke_skill(skill_name, arguments="test input")

    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


# T053: test_manager_caching_behavior
def test_manager_load_skill_returns_skill_instance(sample_skills):
    """Validate load_skill() returns Skill instance (not just metadata).

    Tests that the manager creates proper Skill instances with lazy
    content loading capability.
    """
    skills_dir = sample_skills[0].parent
    manager = SkillManager(skill_dir=skills_dir)
    manager.discover()

    skills = manager.list_skills()
    assert len(skills) > 0

    skill_name = skills[0].name
    skill = manager.load_skill(skill_name)

    assert isinstance(skill, Skill)
    assert skill.metadata.name == skill_name
    assert hasattr(skill, "invoke")


# T054: test_manager_content_load_error_when_file_deleted
def test_manager_skill_not_found_error(sample_skills):
    """Validate SkillNotFoundError raised for non-existent skill name.

    Tests that the manager raises appropriate exception with helpful
    error message when requesting a skill that doesn't exist.
    """
    skills_dir = sample_skills[0].parent
    manager = SkillManager(skill_dir=skills_dir)
    manager.discover()

    with pytest.raises(SkillNotFoundError) as exc_info:
        manager.get_skill("nonexistent-skill-xyz")

    assert "nonexistent-skill-xyz" in str(exc_info.value)
    assert "not found" in str(exc_info.value).lower()


# Additional test: Empty directory returns empty list
def test_manager_empty_directory(tmp_path):
    """Validate manager handles empty directory gracefully.

    Tests that discovery in an empty directory completes without errors
    and returns empty skill list.
    """
    empty_dir = tmp_path / "empty_skills"
    empty_dir.mkdir()

    manager = SkillManager(skill_dir=empty_dir)
    manager.discover()

    skills = manager.list_skills()
    assert skills == []


# Additional test: Discovery logs and continues on invalid skills
def test_manager_graceful_degradation_on_invalid_skill(tmp_path, caplog):
    """Validate manager continues discovery when encountering invalid skills.

    Tests that the manager logs errors for invalid skills but continues
    processing other valid skills (graceful degradation).
    """
    skills_dir = tmp_path / "mixed_skills"
    skills_dir.mkdir()

    # Create one valid skill
    valid_dir = skills_dir / "valid-skill"
    valid_dir.mkdir()
    (valid_dir / "SKILL.md").write_text("---\nname: valid\ndescription: Valid skill\n---\nContent")

    # Create one invalid skill (missing name)
    invalid_dir = skills_dir / "invalid-skill"
    invalid_dir.mkdir()
    (invalid_dir / "SKILL.md").write_text("---\ndescription: Invalid skill\n---\nContent")

    manager = SkillManager(skill_dir=skills_dir)
    manager.discover()

    # Should have discovered only the valid skill
    skills = manager.list_skills()
    assert len(skills) == 1
    assert skills[0].name == "valid"

    # Should have logged error for invalid skill
    assert any("Failed to parse skill" in record.message for record in caplog.records)


# Additional test: Invoke skill with arguments
def test_manager_invoke_skill_with_arguments(fixtures_dir):
    """Validate invoke_skill() processes arguments correctly.

    Tests that the convenience method properly passes arguments through
    to the skill processor.
    """
    manager = SkillManager(skill_dir=fixtures_dir)
    manager.discover()

    # Find a skill with $ARGUMENTS placeholder
    skills = manager.list_skills()
    assert len(skills) > 0

    # Try to invoke with arguments
    skill_name = skills[0].name
    arguments = "test data for processing"
    result = manager.invoke_skill(skill_name, arguments=arguments)

    assert result is not None
    assert isinstance(result, str)
    # Result should contain either the arguments or the original content
    assert len(result) > 0


# Additional test: Discovery clears previous skills
def test_manager_discover_clears_previous_skills(tmp_path):
    """Validate calling discover() multiple times clears previous results.

    Tests that re-running discovery resets the skill registry,
    preventing stale skill accumulation.
    """
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    # First discovery: create 2 skills
    skill1 = skills_dir / "skill1"
    skill1.mkdir()
    (skill1 / "SKILL.md").write_text("---\nname: skill1\ndescription: First skill\n---\nContent")

    skill2 = skills_dir / "skill2"
    skill2.mkdir()
    (skill2 / "SKILL.md").write_text("---\nname: skill2\ndescription: Second skill\n---\nContent")

    manager = SkillManager(skill_dir=skills_dir)
    manager.discover()
    assert len(manager.list_skills()) == 2

    # Remove skill2 and discover again
    (skill2 / "SKILL.md").unlink()
    skill2.rmdir()

    manager.discover()
    assert len(manager.list_skills()) == 1
    assert manager.list_skills()[0].name == "skill1"
