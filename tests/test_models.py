"""Tests for core data models (SkillMetadata and Skill).

This module validates the data model classes including instantiation,
validation, lazy content loading, and caching behavior.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from skillkit.core.models import SkillMetadata, Skill
from skillkit.core.exceptions import ContentLoadError


# T035: Create test_models.py with imports and file header ✓


# T036: test_skill_metadata_creation
def test_skill_metadata_creation(fixtures_dir):
    """Validate SkillMetadata instantiation with all required and optional fields.

    Tests that SkillMetadata can be created with proper field validation
    and that all attributes are accessible.
    """
    skill_path = fixtures_dir / "valid-basic" / "SKILL.md"

    metadata = SkillMetadata(
        name="test-skill",
        description="A test skill for validation",
        skill_path=skill_path,
        allowed_tools=("Read", "Write", "Bash"),
    )

    assert metadata.name == "test-skill"
    assert metadata.description == "A test skill for validation"
    assert metadata.skill_path == skill_path
    assert metadata.allowed_tools == ("Read", "Write", "Bash")


# T037: test_skill_metadata_allowed_tools_optional
def test_skill_metadata_allowed_tools_optional(fixtures_dir):
    """Validate allowed_tools field is optional and defaults to empty tuple.

    Tests that SkillMetadata can be instantiated without the allowed_tools
    field and that it defaults to an empty tuple.
    """
    skill_path = fixtures_dir / "valid-basic" / "SKILL.md"

    metadata = SkillMetadata(
        name="minimal-skill",
        description="Minimal skill without tools",
        skill_path=skill_path,
    )

    assert metadata.allowed_tools == ()
    assert isinstance(metadata.allowed_tools, tuple)


# T038: test_skill_creation_with_metadata
def test_skill_creation_with_metadata(fixtures_dir, tmp_path):
    """Validate Skill instantiation with SkillMetadata.

    Tests that Skill can be created with metadata and base_directory,
    and that it properly initializes its processor chain.
    """
    skill_path = fixtures_dir / "valid-basic" / "SKILL.md"

    metadata = SkillMetadata(
        name="test-skill",
        description="Test skill",
        skill_path=skill_path,
    )

    skill = Skill(metadata=metadata, base_directory=tmp_path)

    assert skill.metadata == metadata
    assert skill.base_directory == tmp_path
    assert hasattr(skill, "_processor")


# T039: test_skill_lazy_content_loading
def test_skill_lazy_content_loading(fixtures_dir, tmp_path):
    """Validate content is not loaded until explicitly accessed.

    Tests the lazy loading pattern by verifying that file I/O does not
    occur until the content property is accessed.
    """
    skill_path = fixtures_dir / "valid-basic" / "SKILL.md"

    metadata = SkillMetadata(
        name="test-skill",
        description="Test skill",
        skill_path=skill_path,
    )

    skill = Skill(metadata=metadata, base_directory=tmp_path)

    # Content should not be loaded yet
    # Check that content is a property, not already loaded
    assert "content" not in skill.__dict__

    # Now access content to trigger loading
    content = skill.content

    assert content is not None
    assert isinstance(content, str)
    assert len(content) > 0


# T040: test_skill_content_caching
def test_skill_content_caching(fixtures_dir, tmp_path):
    """Validate content is cached after first access (no repeated file reads).

    Tests that the @cached_property decorator works correctly and that
    content is only read from disk once.
    """
    skill_path = fixtures_dir / "valid-basic" / "SKILL.md"

    metadata = SkillMetadata(
        name="test-skill",
        description="Test skill",
        skill_path=skill_path,
    )

    skill = Skill(metadata=metadata, base_directory=tmp_path)

    # Access content multiple times
    content1 = skill.content
    content2 = skill.content
    content3 = skill.content

    # All accesses should return the same object (cached)
    assert content1 is content2
    assert content2 is content3

    # Verify content is actually cached in the object
    assert "content" in skill.__dict__


# Additional test: Validate error handling when skill file is deleted
def test_skill_content_load_error_when_file_deleted(tmp_path):
    """Validate ContentLoadError raised when skill file deleted after metadata creation.

    Tests that accessing content raises appropriate error if the file
    is deleted between metadata creation and content access.
    """
    # Create a temporary skill file
    skill_dir = tmp_path / "temp-skill"
    skill_dir.mkdir()
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("---\nname: temp\ndescription: temp skill\n---\nContent")

    metadata = SkillMetadata(
        name="temp-skill",
        description="Temporary skill",
        skill_path=skill_file,
    )

    skill = Skill(metadata=metadata, base_directory=tmp_path)

    # Delete the file
    skill_file.unlink()

    # Accessing content should raise ContentLoadError
    with pytest.raises(ContentLoadError) as exc_info:
        _ = skill.content

    assert "not found" in str(exc_info.value).lower() or "deleted" in str(exc_info.value).lower()


# Additional test: Validate skill invocation works
def test_skill_invocation_basic(fixtures_dir, tmp_path):
    """Validate basic skill invocation without arguments.

    Tests that the invoke() method works correctly and processes
    content through the processor chain.
    """
    skill_path = fixtures_dir / "valid-basic" / "SKILL.md"

    metadata = SkillMetadata(
        name="test-skill",
        description="Test skill",
        skill_path=skill_path,
    )

    skill = Skill(metadata=metadata, base_directory=tmp_path)

    # Invoke without arguments
    result = skill.invoke()

    assert result is not None
    assert isinstance(result, str)
    # Should contain base directory injection
    assert str(tmp_path) in result or "BASE_DIRECTORY" in result
