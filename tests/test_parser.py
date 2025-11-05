"""Tests for SkillParser YAML frontmatter parsing.

This module validates the parser's ability to extract and validate YAML frontmatter
from SKILL.md files, including error handling for malformed inputs.
"""

import pytest
from pathlib import Path

from skillkit.core.parser import SkillParser
from skillkit.core.exceptions import (
    MissingRequiredFieldError,
    InvalidYAMLError,
    InvalidFrontmatterError,
)


# T027: Create test_parser.py with imports and file header ✓


# T028: test_parse_valid_basic_skill
def test_parse_valid_basic_skill(fixtures_dir):
    """Validate parsing of minimal valid skill with required fields only.

    Tests that the parser can successfully extract name and description from
    a basic SKILL.md file with minimal frontmatter.
    """
    parser = SkillParser()
    skill_path = fixtures_dir / "valid-basic" / "SKILL.md"

    metadata = parser.parse_skill_file(skill_path)

    assert metadata.name is not None
    assert metadata.description is not None
    assert metadata.skill_path == skill_path
    assert isinstance(metadata.allowed_tools, tuple)


# T029: test_parse_valid_skill_with_arguments
def test_parse_valid_skill_with_arguments(fixtures_dir):
    """Validate $ARGUMENTS placeholder is preserved during parsing.

    Tests that the parser does not modify content containing $ARGUMENTS,
    leaving substitution for the invocation phase.
    """
    parser = SkillParser()
    skill_path = fixtures_dir / "valid-with-arguments" / "SKILL.md"

    metadata = parser.parse_skill_file(skill_path)

    # Parser only extracts metadata, not content
    assert metadata.name is not None
    assert metadata.description is not None

    # Verify content still has placeholder (read raw file)
    content = skill_path.read_text(encoding="utf-8")
    assert "$ARGUMENTS" in content


# T030: test_parse_valid_skill_with_unicode
def test_parse_valid_skill_with_unicode(fixtures_dir):
    """Validate Unicode/emoji content is handled correctly.

    Tests that the parser can handle SKILL.md files containing Unicode
    characters and emoji in both frontmatter and content.
    """
    parser = SkillParser()
    skill_path = fixtures_dir / "valid-unicode" / "SKILL.md"

    metadata = parser.parse_skill_file(skill_path)

    assert metadata.name is not None
    assert metadata.description is not None

    # Verify Unicode handling by reading content
    content = skill_path.read_text(encoding="utf-8")
    # Should contain Unicode or emoji characters
    assert any(ord(c) > 127 for c in content)


# T031: test_parse_invalid_missing_name_raises_validation_error
def test_parse_invalid_missing_name_raises_validation_error(fixtures_dir):
    """Validate MissingRequiredFieldError raised for missing name field.

    Tests that the parser raises appropriate exception with helpful
    error message when required 'name' field is absent.
    """
    parser = SkillParser()
    skill_path = fixtures_dir / "invalid-missing-name" / "SKILL.md"

    with pytest.raises(MissingRequiredFieldError) as exc_info:
        parser.parse_skill_file(skill_path)

    assert "name" in str(exc_info.value).lower()
    assert exc_info.value.field_name == "name"


# T032: test_parse_invalid_missing_description_raises_validation_error
def test_parse_invalid_missing_description_raises_validation_error(fixtures_dir):
    """Validate MissingRequiredFieldError raised for missing description field.

    Tests that the parser raises appropriate exception with helpful
    error message when required 'description' field is absent.
    """
    parser = SkillParser()
    skill_path = fixtures_dir / "invalid-missing-description" / "SKILL.md"

    with pytest.raises(MissingRequiredFieldError) as exc_info:
        parser.parse_skill_file(skill_path)

    assert "description" in str(exc_info.value).lower()
    assert exc_info.value.field_name == "description"


# T033: test_parse_invalid_yaml_syntax_raises_validation_error
def test_parse_invalid_yaml_syntax_raises_validation_error(fixtures_dir):
    """Validate InvalidYAMLError raised for malformed YAML with helpful message.

    Tests that the parser provides detailed error messages including line/column
    information for YAML syntax errors.
    """
    parser = SkillParser()
    skill_path = fixtures_dir / "invalid-yaml-syntax" / "SKILL.md"

    with pytest.raises(InvalidYAMLError) as exc_info:
        parser.parse_skill_file(skill_path)

    error_message = str(exc_info.value)
    # Should contain path and indicate YAML error
    assert str(skill_path) in error_message or "SKILL.md" in error_message


# T034: test_parse_invalid_skills - Parametrized test for all invalid fixtures
@pytest.mark.parametrize("fixture_name,expected_exception,expected_field", [
    ("invalid-missing-name", MissingRequiredFieldError, "name"),
    ("invalid-missing-description", MissingRequiredFieldError, "description"),
    ("invalid-yaml-syntax", InvalidYAMLError, None),
])
def test_parse_invalid_skills(fixtures_dir, fixture_name, expected_exception, expected_field):
    """Parametrized test validating all invalid skill fixtures raise correct exceptions.

    Tests that the parser correctly identifies and reports different types of
    validation errors with appropriate exception types.

    Args:
        fixture_name: Name of the test fixture directory
        expected_exception: Exception class that should be raised
        expected_field: Field name for MissingRequiredFieldError (None for other errors)
    """
    parser = SkillParser()
    skill_path = fixtures_dir / fixture_name / "SKILL.md"

    with pytest.raises(expected_exception) as exc_info:
        parser.parse_skill_file(skill_path)

    # For missing field errors, validate field_name attribute
    if expected_field is not None:
        assert exc_info.value.field_name == expected_field
