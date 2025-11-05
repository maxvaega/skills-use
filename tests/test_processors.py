"""Tests for content processing strategies.

This module validates the ContentProcessor classes including base directory
injection, $ARGUMENTS substitution, escaping, size limits, and composition.
"""

import pytest
from pathlib import Path

from skillkit.core.processors import (
    ContentProcessor,
    BaseDirectoryProcessor,
    ArgumentSubstitutionProcessor,
    CompositeProcessor,
)
from skillkit.core.exceptions import (
    SizeLimitExceededError,
    ArgumentProcessingError,
)


# T041: Create test_processors.py with imports and file header ✓


# T042: test_process_content_without_placeholder
def test_process_content_without_placeholder():
    """Validate content returned unchanged when no $ARGUMENTS placeholder present.

    Tests that the processor handles content without placeholders gracefully,
    returning the original content unmodified.
    """
    processor = ArgumentSubstitutionProcessor()
    content = "This is a skill without any placeholders."
    context = {"arguments": "", "skill_name": "test-skill"}

    result = processor.process(content, context)

    assert result == content


# T043: test_substitute_arguments_basic
def test_substitute_arguments_basic():
    """Validate basic $ARGUMENTS substitution: 'Hello $ARGUMENTS!' → 'Hello World!'.

    Tests the fundamental substitution functionality with a simple placeholder
    in the middle of content.
    """
    processor = ArgumentSubstitutionProcessor()
    content = "Hello $ARGUMENTS!"
    context = {"arguments": "World", "skill_name": "test-skill"}

    result = processor.process(content, context)

    assert result == "Hello World!"


# T044: test_substitute_arguments_various_positions - Parametrized
@pytest.mark.parametrize("content,arguments,expected", [
    ("$ARGUMENTS is at the start", "This", "This is at the start"),
    ("In the $ARGUMENTS of text", "middle", "In the middle of text"),
    ("At the end: $ARGUMENTS", "HERE", "At the end: HERE"),
    ("Multiple $ARGUMENTS and $ARGUMENTS", "TEST", "Multiple TEST and TEST"),
])
def test_substitute_arguments_various_positions(content, arguments, expected):
    """Parametrized test validating $ARGUMENTS substitution at different positions.

    Tests that substitution works correctly when placeholder appears at the
    start, middle, end, or multiple times in content.

    Args:
        content: Template content with $ARGUMENTS placeholder
        arguments: Arguments to substitute
        expected: Expected result after substitution
    """
    processor = ArgumentSubstitutionProcessor()
    context = {"arguments": arguments, "skill_name": "test-skill"}

    result = processor.process(content, context)

    assert result == expected


# T045: test_substitute_arguments_with_special_characters
def test_substitute_arguments_with_special_characters():
    """Validate arguments with special characters (<>& etc.) are handled correctly.

    Tests that the processor can handle special characters without breaking
    or causing injection issues.
    """
    processor = ArgumentSubstitutionProcessor()
    content = "Command: $ARGUMENTS"
    special_args = "<script>alert('XSS')</script> & other chars"
    context = {"arguments": special_args, "skill_name": "test-skill"}

    result = processor.process(content, context)

    # Should preserve special characters exactly as provided
    assert result == f"Command: {special_args}"
    assert "<script>" in result
    assert "&" in result


# T046: test_substitute_arguments_size_limit_enforcement
def test_substitute_arguments_size_limit_enforcement():
    """Validate SizeLimitExceededError raised for arguments exceeding 1MB.

    Tests that the size limit is enforced and appropriate exception is raised
    when arguments are too large.
    """
    processor = ArgumentSubstitutionProcessor()
    content = "Task: $ARGUMENTS"

    # Create >1MB of arguments (1,000,001 bytes)
    large_arguments = "A" * 1_000_001
    context = {"arguments": large_arguments, "skill_name": "test-skill"}

    with pytest.raises(SizeLimitExceededError) as exc_info:
        processor.process(content, context)

    assert "1000000" in str(exc_info.value) or "1MB" in str(exc_info.value).lower()


# T047: test_process_content_escaping_double_dollar
def test_process_content_escaping_double_dollar():
    """Validate $$ARGUMENTS escaping works ($$ARGUMENTS → $ARGUMENTS literal).

    Tests that double-dollar escaping allows skills to include literal
    $ARGUMENTS text without substitution.
    """
    processor = ArgumentSubstitutionProcessor()
    content = "Literal: $$ARGUMENTS, Substituted: $ARGUMENTS"
    context = {"arguments": "REPLACED", "skill_name": "test-skill"}

    result = processor.process(content, context)

    # $$ARGUMENTS should become $ARGUMENTS (literal)
    # $ARGUMENTS should become REPLACED
    assert "$ARGUMENTS" in result  # Escaped version
    assert "REPLACED" in result  # Substituted version
    assert "$$ARGUMENTS" not in result  # No double-dollar in output


# Additional test: No placeholder but arguments provided should append
def test_substitute_arguments_no_placeholder_with_arguments():
    """Validate arguments appended when no placeholder present but arguments provided.

    Tests that the processor appends arguments to the end of content when
    there is no $ARGUMENTS placeholder but arguments are provided.
    """
    processor = ArgumentSubstitutionProcessor()
    content = "This skill has no placeholder."
    context = {"arguments": "Additional info", "skill_name": "test-skill"}

    result = processor.process(content, context)

    assert "This skill has no placeholder." in result
    assert "Additional info" in result
    assert result.endswith("Additional info")


# Additional test: BaseDirectoryProcessor
def test_base_directory_processor(tmp_path):
    """Validate BaseDirectoryProcessor injects base directory at beginning.

    Tests that the base directory processor adds the directory path to
    the start of the content.
    """
    processor = BaseDirectoryProcessor()
    content = "# My Skill\n\nThis is the content."
    base_dir = tmp_path / "skills" / "my-skill"
    context = {"base_directory": str(base_dir)}

    result = processor.process(content, context)

    assert str(base_dir) in result
    assert result.startswith("Base directory for this skill:")
    assert "# My Skill" in result


# Additional test: CompositeProcessor chains processors
def test_composite_processor(tmp_path):
    """Validate CompositeProcessor chains multiple processors in order.

    Tests that the composite processor applies base directory injection
    followed by argument substitution in the correct sequence.
    """
    base_processor = BaseDirectoryProcessor()
    args_processor = ArgumentSubstitutionProcessor()
    composite = CompositeProcessor([base_processor, args_processor])

    content = "Task: $ARGUMENTS"
    base_dir = tmp_path / "skills" / "test-skill"
    context = {
        "base_directory": str(base_dir),
        "arguments": "review code",
        "skill_name": "test-skill",
    }

    result = composite.process(content, context)

    # Should have both base directory and substituted arguments
    assert str(base_dir) in result
    assert "review code" in result
    assert "$ARGUMENTS" not in result


# Additional test: Empty arguments with placeholder
def test_substitute_arguments_empty_with_placeholder():
    """Validate empty arguments result in empty substitution.

    Tests that when arguments are empty but placeholder is present,
    the substitution produces an empty string at the placeholder location.
    """
    processor = ArgumentSubstitutionProcessor()
    content = "Task: $ARGUMENTS (end)"
    context = {"arguments": "", "skill_name": "test-skill"}

    result = processor.process(content, context)

    assert result == "Task:  (end)"
    assert "$ARGUMENTS" not in result
