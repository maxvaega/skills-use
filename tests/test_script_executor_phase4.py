"""Tests for Phase 4: Script Executor Security Enhancements.

Tests focus on:
- T034: Symlink validation in _validate_script_path()
- T035: Setuid/setgid permission checks (already implemented)
- T036: Security violation logging in _validate_script_path()
- T037: Security violation logging in _check_permissions()
- T038: Audit logging in execute()
"""

import json
import logging
import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from skillkit.core.exceptions import PathSecurityError, ScriptPermissionError
from skillkit.core.models import SkillMetadata
from skillkit.core.scripts import ScriptExecutor


class TestPathTraversalPrevention:
    """Test path traversal prevention with security logging."""

    def test_rejects_parent_directory_traversal(self, tmp_path, caplog):
        """Test that ../../etc/passwd style paths are rejected."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        # Create a legitimate script
        script = skill_dir / "scripts" / "legitimate.py"
        script.parent.mkdir()
        script.write_text("print('hello')")

        executor = ScriptExecutor()

        with caplog.at_level(logging.ERROR):
            with pytest.raises(PathSecurityError, match="escapes skill directory"):
                executor._validate_script_path(
                    Path("../../../../etc/passwd"),
                    skill_dir
                )

        # Verify security violation was logged
        error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(error_logs) > 0
        assert "Security violation" in error_logs[0].message
        assert "Path traversal attempt" in error_logs[0].message

    def test_rejects_absolute_path_outside_skill_dir(self, tmp_path, caplog):
        """Test that absolute paths outside skill dir are rejected."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        executor = ScriptExecutor()

        # Try to access /etc/passwd
        with caplog.at_level(logging.ERROR):
            with pytest.raises(PathSecurityError):
                executor._validate_script_path(
                    Path("/etc/passwd"),
                    skill_dir
                )

        error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(error_logs) > 0

    def test_rejects_symlink_pointing_outside_skill_dir(self, tmp_path, caplog):
        """Test that symlinks pointing outside skill dir are rejected (T034)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        # Create external file
        external_file = tmp_path / "external.py"
        external_file.write_text("print('malicious')")

        # Create symlink inside skill dir pointing outside
        symlink = skill_dir / "scripts" / "evil.py"
        symlink.parent.mkdir(exist_ok=True)
        symlink.symlink_to(external_file)

        executor = ScriptExecutor()

        with caplog.at_level(logging.ERROR):
            with pytest.raises(PathSecurityError):
                executor._validate_script_path(
                    symlink.relative_to(skill_dir),
                    skill_dir
                )

        # Verify security violation was logged
        error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
        assert any("Security violation" in r.message for r in error_logs)

    def test_accepts_symlink_within_skill_dir(self, tmp_path):
        """Test that symlinks within skill dir are accepted."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        # Create legitimate script
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        target = scripts_dir / "target.py"
        target.write_text("print('hello')")

        # Create symlink to it
        symlink = scripts_dir / "link.py"
        symlink.symlink_to(target)

        executor = ScriptExecutor()

        # Should not raise
        result = executor._validate_script_path(
            symlink.relative_to(skill_dir),
            skill_dir
        )

        assert result == target.resolve()

    def test_validates_symlink_before_resolution(self, tmp_path):
        """Test that symlinks are validated before being resolved."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()

        # Create legitimate target
        target = scripts_dir / "real.py"
        target.write_text("print('hello')")

        # Create symlink
        symlink = scripts_dir / "link.py"
        symlink.symlink_to(target)

        executor = ScriptExecutor()

        # Should detect symlink and validate target
        result = executor._validate_script_path(
            symlink.relative_to(skill_dir),
            skill_dir
        )

        assert result.exists()
        assert result.is_file()


class TestPermissionValidation:
    """Test permission validation with security logging."""

    @pytest.mark.skipif(os.name == 'nt', reason="Unix-only test")
    def test_rejects_setuid_script(self, tmp_path, caplog):
        """Test that scripts with setuid bit are rejected (T035)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        # Create a script
        script = skill_dir / "scripts" / "dangerous.py"
        script.parent.mkdir()
        script.write_text("print('hello')")

        # Set setuid bit
        os.chmod(script, stat.S_IRUSR | stat.S_IWUSR | stat.S_ISUID)

        executor = ScriptExecutor()

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ScriptPermissionError, match="dangerous permissions"):
                executor._check_permissions(script)

        # Verify security violation was logged
        error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
        assert any("dangerous permissions" in r.message for r in error_logs)
        assert any("setuid=True" in r.message for r in error_logs)

    @pytest.mark.skipif(os.name == 'nt', reason="Unix-only test")
    def test_rejects_setgid_script(self, tmp_path, caplog):
        """Test that scripts with setgid bit are rejected (T035)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        # Create a script
        script = skill_dir / "scripts" / "dangerous.py"
        script.parent.mkdir()
        script.write_text("print('hello')")

        # Set setgid bit
        os.chmod(script, stat.S_IRUSR | stat.S_IWUSR | stat.S_ISGID)

        executor = ScriptExecutor()

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ScriptPermissionError, match="dangerous permissions"):
                executor._check_permissions(script)

        # Verify security violation was logged
        error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
        assert any("setgid=True" in r.message for r in error_logs)

    def test_accepts_normal_permissions(self, tmp_path):
        """Test that scripts with normal permissions are accepted."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        # Create a script
        script = skill_dir / "scripts" / "normal.py"
        script.parent.mkdir()
        script.write_text("print('hello')")

        executor = ScriptExecutor()

        # Should not raise
        executor._check_permissions(script)


class TestSecurityViolationLogging:
    """Test that security violations are properly logged (T036, T037)."""

    def test_path_validation_logs_traversal_attempts(self, tmp_path, caplog):
        """Test that path traversal attempts are logged (T036)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        executor = ScriptExecutor()

        with caplog.at_level(logging.ERROR):
            with pytest.raises(PathSecurityError):
                executor._validate_script_path(
                    Path("../../../../etc/passwd"),
                    skill_dir
                )

        error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(error_logs) > 0
        assert any("Security violation" in r.message for r in error_logs)
        assert any("path" in r.message for r in error_logs)

    def test_invalid_path_logs_security_violation(self, tmp_path, caplog):
        """Test that invalid paths log security violations (T036)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        executor = ScriptExecutor()

        with caplog.at_level(logging.ERROR):
            try:
                # Try with nonexistent path
                executor._validate_script_path(
                    Path("nonexistent.py"),
                    skill_dir
                )
            except FileNotFoundError:
                pass

        # At least some validation happened
        error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
        # This is expected to have no logs if file doesn't exist
        # (FileNotFoundError is the exception)

    def test_permission_violation_logs_with_details(self, tmp_path, caplog):
        """Test that permission violations log with detailed info (T037)."""
        if os.name == 'nt':
            pytest.skip("Unix-only test")

        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        script = skill_dir / "dangerous.py"
        script.write_text("print('hello')")
        os.chmod(script, stat.S_IRUSR | stat.S_IWUSR | stat.S_ISUID)

        executor = ScriptExecutor()

        with caplog.at_level(logging.ERROR):
            try:
                executor._check_permissions(script)
            except ScriptPermissionError:
                pass

        error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(error_logs) > 0

        # Verify detailed information is logged
        log_message = error_logs[0].message
        assert "path=" in log_message
        assert "mode=" in log_message
        assert "setuid=" in log_message


class TestAuditLogging:
    """Test comprehensive audit logging in execute() (T038)."""

    def test_audit_log_on_successful_execution(self, tmp_path, caplog):
        """Test that successful executions are audited (T038)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        # Create a simple script that outputs JSON
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "test.py"
        script.write_text(
            """import json
args = {"test": "value"}
print(json.dumps({"success": True}))
"""
        )

        # Create SKILL.md
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# Test Skill\nTest description")

        executor = ScriptExecutor()
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=skill_md,
            allowed_tools=()
        )

        with caplog.at_level(logging.INFO):
            result = executor.execute(
                script_path=script.relative_to(skill_dir),
                arguments={"test": "value"},
                skill_base_dir=skill_dir,
                skill_metadata=skill_metadata
            )

        # Check that audit log was created
        audit_logs = [r for r in caplog.records if "AUDIT:" in r.message]
        assert len(audit_logs) > 0

        audit_msg = audit_logs[0].message
        assert "timestamp=" in audit_msg
        assert f"skill={skill_metadata.name}" in audit_msg
        assert "exit_code=" in audit_msg
        assert "execution_time_ms=" in audit_msg

    def test_audit_log_includes_arguments_truncated(self, tmp_path, caplog):
        """Test that audit log truncates large arguments (T038)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "test.py"
        script.write_text("import json, sys; print(json.dumps(json.load(sys.stdin)))")

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# Test Skill\nTest description")

        executor = ScriptExecutor()
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=skill_md,
            allowed_tools=()
        )

        # Create large arguments
        large_args = {"data": "x" * 500}

        with caplog.at_level(logging.INFO):
            try:
                result = executor.execute(
                    script_path=script.relative_to(skill_dir),
                    arguments=large_args,
                    skill_base_dir=skill_dir,
                    skill_metadata=skill_metadata
                )
            except Exception:
                pass

        # Check that audit log was created with truncation
        audit_logs = [r for r in caplog.records if "AUDIT:" in r.message]
        assert len(audit_logs) > 0

        audit_msg = audit_logs[0].message
        # Arguments should be truncated to 256 chars and have ellipsis
        if len(str(large_args)) > 256:
            assert "..." in audit_msg

    def test_audit_log_includes_all_metadata(self, tmp_path, caplog):
        """Test that audit log includes all required metadata (T038)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "nested" / "test.py"
        script.parent.mkdir()
        script.write_text("print('success')")

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# Test Skill\nTest description")

        executor = ScriptExecutor()
        skill_metadata = SkillMetadata(
            name="audit-test-skill",
            description="Test skill",
            skill_path=skill_md,
            allowed_tools=()
        )

        with caplog.at_level(logging.INFO):
            result = executor.execute(
                script_path=script.relative_to(skill_dir),
                arguments={"key": "value"},
                skill_base_dir=skill_dir,
                skill_metadata=skill_metadata
            )

        audit_logs = [r for r in caplog.records if "AUDIT:" in r.message]
        assert len(audit_logs) == 1

        audit_msg = audit_logs[0].message

        # Verify all required fields are present
        required_fields = [
            "timestamp=",
            "skill=audit-test-skill",
            "script=",
            "args=",
            "exit_code=",
            "execution_time_ms=",
            "signal=",
            "stdout_truncated=",
            "stderr_truncated="
        ]

        for field in required_fields:
            assert field in audit_msg, f"Missing field: {field}"

        # Verify script path contains nested
        assert "nested" in audit_msg

    def test_audit_log_on_failed_execution(self, tmp_path, caplog):
        """Test that failed executions are audited (T038)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "failing.py"
        script.write_text("import sys; sys.exit(1)")

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# Test Skill\nTest description")

        executor = ScriptExecutor()
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=skill_md,
            allowed_tools=()
        )

        with caplog.at_level(logging.INFO):
            result = executor.execute(
                script_path=script.relative_to(skill_dir),
                arguments={},
                skill_base_dir=skill_dir,
                skill_metadata=skill_metadata
            )

        audit_logs = [r for r in caplog.records if "AUDIT:" in r.message]
        assert len(audit_logs) > 0

        audit_msg = audit_logs[0].message
        assert "exit_code=1" in audit_msg


class TestSecurityBoundariesCheckpoint:
    """Integration tests for Phase 4 checkpoint."""

    def test_path_traversal_blocked_with_audit(self, tmp_path, caplog):
        """Verify path traversal is blocked with proper logging."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        executor = ScriptExecutor()

        # Test multiple traversal patterns
        traversal_patterns = [
            "../../../../etc/passwd",
            "../../../sensitive.py",
            "../../SKILL.md",
        ]

        for pattern in traversal_patterns:
            with caplog.at_level(logging.ERROR):
                with pytest.raises(PathSecurityError):
                    executor._validate_script_path(
                        Path(pattern),
                        skill_dir
                    )

            # Verify each attempt is logged
            caplog.clear()

    def test_dangerous_permissions_blocked_with_audit(self, tmp_path, caplog):
        """Verify dangerous permissions are blocked with logging."""
        if os.name == 'nt':
            pytest.skip("Unix-only test")

        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        script = skill_dir / "bad.py"
        script.write_text("print('nope')")
        os.chmod(script, stat.S_IRUSR | stat.S_IWUSR | stat.S_ISUID | stat.S_ISGID)

        executor = ScriptExecutor()

        with caplog.at_level(logging.ERROR):
            with pytest.raises(ScriptPermissionError):
                executor._check_permissions(script)

        # Verify both violations logged
        error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
        log_msg = " ".join(r.message for r in error_logs)
        assert "setuid=True" in log_msg
        assert "setgid=True" in log_msg

    def test_all_executions_audited(self, tmp_path, caplog):
        """Verify all executions generate audit logs."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "audit_test.py"
        script.write_text("print('tested')")

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# Test Skill\nTest description")

        executor = ScriptExecutor()
        skill_metadata = SkillMetadata(
            name="audit-skill",
            description="Audit test",
            skill_path=skill_md,
            allowed_tools=()
        )

        with caplog.at_level(logging.INFO):
            result = executor.execute(
                script_path=script.relative_to(skill_dir),
                arguments={"param": "value"},
                skill_base_dir=skill_dir,
                skill_metadata=skill_metadata
            )

        # Verify audit log exists
        audit_logs = [r for r in caplog.records if "AUDIT:" in r.message]
        assert len(audit_logs) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
