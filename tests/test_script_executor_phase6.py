"""Tests for Phase 6: Tool Restriction Enforcement for Scripts.

Tests focus on:
- T045: Implement _check_tool_restrictions() method
- T046: Raise ToolRestrictionError if Bash not allowed
- T047: Call _check_tool_restrictions() in execute()
- T048: Handle None/empty allowed_tools
- T049: Test fixture with restricted-skill
"""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from skillkit.core.exceptions import ToolRestrictionError
from skillkit.core.models import SkillMetadata
from skillkit.core.scripts import ScriptExecutor


class TestToolRestrictionEnforcement:
    """Test tool restriction enforcement for script execution."""

    def test_allows_execution_when_bash_in_allowed_tools(self, tmp_path):
        """Test that script execution succeeds when Bash is in allowed-tools."""
        # Setup skill directory with script
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        script = skill_dir / "scripts" / "test.py"
        script.parent.mkdir()
        script.write_text('import sys, json; print(json.dumps({"status": "ok"}))')

        # Create metadata with Bash in allowed tools
        metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=skill_dir / "SKILL.md",
            allowed_tools=("Bash", "Read", "Write")
        )

        executor = ScriptExecutor(timeout=5)

        # Should not raise ToolRestrictionError
        result = executor.execute(
            script_path=Path("scripts/test.py"),
            arguments={"test": "data"},
            skill_base_dir=skill_dir,
            skill_metadata=metadata
        )

        assert result.success
        assert result.exit_code == 0

    def test_blocks_execution_when_bash_not_in_allowed_tools(self, tmp_path):
        """Test that script execution is blocked when Bash not in allowed-tools (T046)."""
        # Setup skill directory with script
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        script = skill_dir / "scripts" / "blocked.py"
        script.parent.mkdir()
        script.write_text('import sys, json; print(json.dumps({"status": "ok"}))')

        # Create metadata WITHOUT Bash in allowed tools
        metadata = SkillMetadata(
            name="restricted-skill",
            description="Test skill without Bash",
            skill_path=skill_dir / "SKILL.md",
            allowed_tools=("Read", "Write")
        )

        executor = ScriptExecutor(timeout=5)

        # Should raise ToolRestrictionError
        with pytest.raises(ToolRestrictionError) as exc_info:
            executor.execute(
                script_path=Path("scripts/blocked.py"),
                arguments={"test": "data"},
                skill_base_dir=skill_dir,
                skill_metadata=metadata
            )

        # Verify error message contains skill name and allowed tools
        error_msg = str(exc_info.value)
        assert "restricted-skill" in error_msg
        assert "Bash" in error_msg
        assert "Read" in error_msg
        assert "Write" in error_msg

    def test_allows_execution_when_no_restrictions_defined(self, tmp_path):
        """Test that script execution succeeds when allowed_tools is None/empty (T048)."""
        # Setup skill directory with script
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        script = skill_dir / "scripts" / "test.py"
        script.parent.mkdir()
        script.write_text('import sys, json; print(json.dumps({"status": "ok"}))')

        # Create metadata with no allowed_tools (default empty tuple)
        metadata = SkillMetadata(
            name="unrestricted-skill",
            description="Test skill with no restrictions",
            skill_path=skill_dir / "SKILL.md"
        )

        executor = ScriptExecutor(timeout=5)

        # Should not raise ToolRestrictionError
        result = executor.execute(
            script_path=Path("scripts/test.py"),
            arguments={"test": "data"},
            skill_base_dir=skill_dir,
            skill_metadata=metadata
        )

        assert result.success
        assert result.exit_code == 0

    def test_allows_execution_when_allowed_tools_is_empty_tuple(self, tmp_path):
        """Test that script execution succeeds when allowed_tools is empty tuple."""
        # Setup skill directory with script
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        script = skill_dir / "scripts" / "test.py"
        script.parent.mkdir()
        script.write_text('import sys, json; print(json.dumps({"status": "ok"}))')

        # Create metadata with explicitly empty allowed_tools
        metadata = SkillMetadata(
            name="unrestricted-skill",
            description="Test skill with empty allowed_tools",
            skill_path=skill_dir / "SKILL.md",
            allowed_tools=()
        )

        executor = ScriptExecutor(timeout=5)

        # Should not raise ToolRestrictionError
        result = executor.execute(
            script_path=Path("scripts/test.py"),
            arguments={"test": "data"},
            skill_base_dir=skill_dir,
            skill_metadata=metadata
        )

        assert result.success
        assert result.exit_code == 0

    def test_check_tool_restrictions_called_before_execution(self, tmp_path):
        """Test that _check_tool_restrictions() is called in execute() (T047)."""
        # Setup skill directory with script
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        script = skill_dir / "scripts" / "test.py"
        script.parent.mkdir()
        script.write_text('import sys, json; print(json.dumps({"status": "ok"}))')

        # Create metadata WITHOUT Bash - should fail before script execution
        metadata = SkillMetadata(
            name="restricted-skill",
            description="Test skill",
            skill_path=skill_dir / "SKILL.md",
            allowed_tools=("Read",)
        )

        executor = ScriptExecutor(timeout=5)

        # Should raise ToolRestrictionError before any subprocess execution
        with pytest.raises(ToolRestrictionError):
            executor.execute(
                script_path=Path("scripts/test.py"),
                arguments={"test": "data"},
                skill_base_dir=skill_dir,
                skill_metadata=metadata
            )

        # The script should never have been executed (no subprocess.run call)
        # We verify this by checking that the error is raised before interpreter resolution

    def test_check_tool_restrictions_method_directly(self):
        """Test _check_tool_restrictions() method directly (T045)."""
        executor = ScriptExecutor()

        # Test with Bash allowed
        metadata_allowed = SkillMetadata(
            name="allowed-skill",
            description="Skill with Bash",
            skill_path=Path("/fake/SKILL.md"),
            allowed_tools=("Bash", "Read")
        )
        # Should not raise
        executor._check_tool_restrictions(metadata_allowed)

        # Test with Bash not allowed
        metadata_blocked = SkillMetadata(
            name="blocked-skill",
            description="Skill without Bash",
            skill_path=Path("/fake/SKILL.md"),
            allowed_tools=("Read", "Write")
        )
        # Should raise ToolRestrictionError
        with pytest.raises(ToolRestrictionError) as exc_info:
            executor._check_tool_restrictions(metadata_blocked)

        assert "blocked-skill" in str(exc_info.value)
        assert "Bash" in str(exc_info.value)

        # Test with no restrictions
        metadata_unrestricted = SkillMetadata(
            name="unrestricted-skill",
            description="Skill with no restrictions",
            skill_path=Path("/fake/SKILL.md"),
            allowed_tools=()
        )
        # Should not raise
        executor._check_tool_restrictions(metadata_unrestricted)

    def test_error_message_includes_allowed_tools_list(self, tmp_path):
        """Test that ToolRestrictionError message includes the allowed tools list."""
        # Setup skill directory
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()
        script = skill_dir / "scripts" / "test.py"
        script.parent.mkdir()
        script.write_text('print("test")')

        # Create metadata with specific allowed tools
        metadata = SkillMetadata(
            name="restricted-skill",
            description="Test skill",
            skill_path=skill_dir / "SKILL.md",
            allowed_tools=("Read", "Write", "Edit")
        )

        executor = ScriptExecutor()

        with pytest.raises(ToolRestrictionError) as exc_info:
            executor.execute(
                script_path=Path("scripts/test.py"),
                arguments={},
                skill_base_dir=skill_dir,
                skill_metadata=metadata
            )

        error_msg = str(exc_info.value)
        # Verify all allowed tools are listed in the error message
        assert "Read" in error_msg
        assert "Write" in error_msg
        assert "Edit" in error_msg


class TestRestrictedSkillFixture:
    """Test using the restricted-skill test fixture (T049)."""

    def test_restricted_skill_fixture_exists(self):
        """Test that restricted-skill fixture was created correctly."""
        fixture_path = Path(__file__).parent / "fixtures" / "skills" / "restricted-skill"

        # Verify directory structure exists
        assert fixture_path.exists(), "restricted-skill fixture directory should exist"
        assert (fixture_path / "SKILL.md").exists(), "SKILL.md should exist"
        assert (fixture_path / "scripts").exists(), "scripts directory should exist"
        assert (fixture_path / "scripts" / "blocked.py").exists(), "blocked.py should exist"

    def test_restricted_skill_has_no_bash_in_allowed_tools(self):
        """Test that restricted-skill fixture has allowed-tools without Bash."""
        from skillkit.core.parser import SkillParser

        fixture_path = Path(__file__).parent / "fixtures" / "skills" / "restricted-skill"
        skill_md = fixture_path / "SKILL.md"

        # Parse the SKILL.md file
        parser = SkillParser()
        metadata, _ = parser.parse(skill_md)

        # Verify allowed_tools doesn't include Bash
        assert metadata.allowed_tools is not None
        assert len(metadata.allowed_tools) > 0, "Should have some allowed tools defined"
        assert "Bash" not in metadata.allowed_tools, "Bash should NOT be in allowed tools"
        assert "Read" in metadata.allowed_tools or "Write" in metadata.allowed_tools, \
            "Should have Read or Write in allowed tools"

    def test_restricted_skill_blocks_script_execution(self):
        """Test that restricted-skill fixture blocks script execution."""
        from skillkit.core.parser import SkillParser

        fixture_path = Path(__file__).parent / "fixtures" / "skills" / "restricted-skill"
        skill_md = fixture_path / "SKILL.md"

        # Parse the skill
        parser = SkillParser()
        metadata, _ = parser.parse(skill_md)

        # Try to execute the blocked.py script
        executor = ScriptExecutor(timeout=5)

        with pytest.raises(ToolRestrictionError) as exc_info:
            executor.execute(
                script_path=Path("scripts/blocked.py"),
                arguments={"test": "data"},
                skill_base_dir=fixture_path,
                skill_metadata=metadata
            )

        # Verify error message
        error_msg = str(exc_info.value)
        assert "restricted-skill" in error_msg
        assert "Bash" in error_msg
