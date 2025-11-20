"""Tests for script execution functionality."""
import pytest
import os
import stat
import json
from pathlib import Path
from skillkit.core.scripts import ScriptExecutor, ScriptMetadata
from skillkit.core.exceptions import (
    PathSecurityError,
    ScriptPermissionError,
    InterpreterNotFoundError,
    ToolRestrictionError,
    ArgumentSizeError
)


class TestScriptExecutor:
    """Test suite for ScriptExecutor class."""

    def test_successful_execution_exit_code_zero(self, tmp_path):
        """Test successful script execution with exit code 0."""
        # Create a simple success script
        script_file = tmp_path / "success.py"
        script_file.write_text('import sys; print("Success"); sys.exit(0)')


        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")
        # Create minimal skill metadata
        from skillkit.core.models import SkillMetadata
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=tmp_path / "SKILL.md"
        )

        executor = ScriptExecutor(timeout=5)
        result = executor.execute(
            script_path=script_file,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=skill_metadata
        )

        assert result.exit_code == 0
        assert result.success is True
        assert "Success" in result.stdout
        assert result.stderr == ""
        assert result.timeout is False

    def test_failed_execution_exit_code_one(self, tmp_path):
        """Test failed script execution with exit code 1."""
        script_file = tmp_path / "failure.py"
        script_file.write_text('import sys; sys.stderr.write("Error occurred"); sys.exit(1)')


        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")
        # Create minimal skill metadata
        from skillkit.core.models import SkillMetadata
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=tmp_path / "SKILL.md"
        )

        executor = ScriptExecutor(timeout=5)
        result = executor.execute(
            script_path=script_file,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=skill_metadata
        )

        assert result.exit_code == 1
        assert result.success is False
        assert "Error occurred" in result.stderr

    def test_timeout_handling_exit_code_124(self, tmp_path):
        """Test timeout handling with exit code 124."""
        # Create an infinite loop script
        script_file = tmp_path / "timeout.py"
        script_file.write_text('''
import time
while True:
    time.sleep(0.1)
''')


        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")
        # Create minimal skill metadata
        from skillkit.core.models import SkillMetadata
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=tmp_path / "SKILL.md"
        )

        executor = ScriptExecutor(timeout=1)  # 1 second timeout
        result = executor.execute(
            script_path=script_file,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=skill_metadata
        )

        assert result.exit_code == 124
        assert result.timeout is True
        assert "Timeout" in result.stderr

    def test_json_arguments_via_stdin(self, tmp_path):
        """Test that arguments are passed as JSON via stdin."""
        script_file = tmp_path / "stdin_test.py"
        script_file.write_text('''
import sys
import json
data = json.load(sys.stdin)
print(f"Received: {data['message']}")
''')


        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")
        # Create minimal skill metadata
        from skillkit.core.models import SkillMetadata
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=tmp_path / "SKILL.md"
        )

        executor = ScriptExecutor(timeout=5)
        result = executor.execute(
            script_path=script_file,
            arguments={"message": "Hello World"},
            skill_base_dir=tmp_path,
            skill_metadata=skill_metadata
        )

        assert result.exit_code == 0
        assert "Received: Hello World" in result.stdout

    def test_path_traversal_prevention(self, tmp_path):
        """Test that path traversal attacks are prevented."""
        # Create skill directory
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        # Try to access file outside skill directory
        outside_script = tmp_path / "outside.py"
        outside_script.write_text('print("pwned")')

        # Attempt path traversal
        malicious_path = skill_dir / ".." / "outside.py"

        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")


        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")
        # Create minimal skill metadata
        from skillkit.core.models import SkillMetadata
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=tmp_path / "SKILL.md"
        )

        executor = ScriptExecutor(timeout=5)

        with pytest.raises(PathSecurityError):
            executor.execute(
                script_path=malicious_path,
                arguments={},
                skill_base_dir=skill_dir,
                skill_metadata=skill_metadata
            )

    def test_symlink_validation(self, tmp_path):
        """Test that symlinks pointing outside skill directory are rejected."""
        import sys
        if sys.platform == 'win32':
            pytest.skip("Symlink test not applicable on Windows")

        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        # Create a file outside skill directory
        outside_file = tmp_path / "outside.py"
        outside_file.write_text('print("pwned")')

        # Create symlink inside skill directory pointing outside
        symlink_path = skill_dir / "symlink.py"
        symlink_path.symlink_to(outside_file)

        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")


        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")
        # Create minimal skill metadata
        from skillkit.core.models import SkillMetadata
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=tmp_path / "SKILL.md"
        )

        executor = ScriptExecutor(timeout=5)

        with pytest.raises(PathSecurityError):
            executor.execute(
                script_path=symlink_path,
                arguments={},
                skill_base_dir=skill_dir,
                skill_metadata=skill_metadata
            )

    def test_setuid_permission_check(self, tmp_path):
        """Test that scripts with setuid bit are rejected."""
        import sys
        if sys.platform == 'win32':
            pytest.skip("setuid test not applicable on Windows")

        script_file = tmp_path / "setuid.py"
        script_file.write_text('print("Hello")')

        # Set setuid bit
        os.chmod(script_file, stat.S_ISUID | stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)


        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")
        # Create minimal skill metadata
        from skillkit.core.models import SkillMetadata
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=tmp_path / "SKILL.md"
        )

        executor = ScriptExecutor(timeout=5)

        with pytest.raises(ScriptPermissionError):
            executor.execute(
                script_path=script_file,
                arguments={},
                skill_base_dir=tmp_path,
                skill_metadata=skill_metadata
            )

    def test_setgid_permission_check(self, tmp_path):
        """Test that scripts with setgid bit are rejected."""
        import sys
        if sys.platform == 'win32':
            pytest.skip("setgid test not applicable on Windows")

        script_file = tmp_path / "setgid.py"
        script_file.write_text('print("Hello")')

        # Set setgid bit
        os.chmod(script_file, stat.S_ISGID | stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)


        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")
        # Create minimal skill metadata
        from skillkit.core.models import SkillMetadata
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=tmp_path / "SKILL.md"
        )

        executor = ScriptExecutor(timeout=5)

        with pytest.raises(ScriptPermissionError):
            executor.execute(
                script_path=script_file,
                arguments={},
                skill_base_dir=tmp_path,
                skill_metadata=skill_metadata
            )

    def test_output_truncation_at_10mb(self, tmp_path):
        """Test that output is truncated at 10MB limit."""
        script_file = tmp_path / "large_output.py"
        # Generate 15MB of output (exceeds 10MB limit)
        script_file.write_text('''
import sys
# Write 15MB to stdout
for i in range(15 * 1024):  # 15 * 1024 KB = 15 MB
    sys.stdout.write("x" * 1024)  # 1KB per iteration
''')


        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")
        # Create minimal skill metadata
        from skillkit.core.models import SkillMetadata
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=tmp_path / "SKILL.md"
        )

        executor = ScriptExecutor(timeout=10, max_output_size=10 * 1024 * 1024)  # 10MB limit
        result = executor.execute(
            script_path=script_file,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=skill_metadata
        )

        # Output should be truncated
        assert result.stdout_truncated is True
        # Output size should be approximately 10MB (allow small margin for truncation message)
        assert len(result.stdout) <= 11 * 1024 * 1024  # 11MB with margin

    def test_environment_variable_injection(self, tmp_path):
        """Test that environment variables are injected correctly."""
        script_file = tmp_path / "env_test.py"
        script_file.write_text('''
import os
print(f"SKILL_NAME={os.environ.get('SKILL_NAME', 'MISSING')}")
print(f"SKILL_BASE_DIR={os.environ.get('SKILL_BASE_DIR', 'MISSING')}")
print(f"SKILL_VERSION={os.environ.get('SKILL_VERSION', 'MISSING')}")
print(f"SKILLKIT_VERSION={os.environ.get('SKILLKIT_VERSION', 'MISSING')}")
''')


        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")
        # Create minimal skill metadata
        from skillkit.core.models import SkillMetadata
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=tmp_path / "SKILL.md"
        )

        executor = ScriptExecutor(timeout=5)
        result = executor.execute(
            script_path=script_file,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=skill_metadata
        )

        assert result.exit_code == 0
        assert "SKILL_NAME=test-skill" in result.stdout
        assert "SKILL_BASE_DIR=" in result.stdout
        assert "SKILL_VERSION=" in result.stdout
        assert "SKILLKIT_VERSION=" in result.stdout

    def test_tool_restriction_enforcement_bash_allowed(self, tmp_path):
        """Test that scripts execute when Bash is in allowed-tools."""
        script_file = tmp_path / "allowed.py"
        script_file.write_text('print("Allowed")')

        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")

        # Simulate skill metadata with Bash in allowed-tools
        from skillkit.core.models import SkillMetadata
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=tmp_path / "SKILL.md",
            allowed_tools=["Bash", "Read"]
        )

        executor = ScriptExecutor(timeout=5)
        result = executor.execute(
            script_path=script_file,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=skill_metadata
        )

        assert result.exit_code == 0
        assert "Allowed" in result.stdout

    def test_tool_restriction_enforcement_bash_not_allowed(self, tmp_path):
        """Test that scripts are blocked when Bash is not in allowed-tools."""
        script_file = tmp_path / "blocked.py"
        script_file.write_text('print("Blocked")')

        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")

        # Simulate skill metadata without Bash in allowed-tools
        from skillkit.core.models import SkillMetadata
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=tmp_path / "SKILL.md",
            allowed_tools=["Read", "Write"]  # No Bash
        )

        executor = ScriptExecutor(timeout=5)

        with pytest.raises(ToolRestrictionError) as exc_info:
            executor.execute(
                script_path=script_file,
                arguments={},
                skill_base_dir=tmp_path,
                skill_metadata=skill_metadata
            )

        assert "Bash" in str(exc_info.value)
        assert "test-skill" in str(exc_info.value)

    def test_tool_restriction_none_allows_all(self, tmp_path):
        """Test that None/empty allowed_tools allows all scripts."""
        script_file = tmp_path / "unrestricted.py"
        script_file.write_text('print("Unrestricted")')

        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")

        # Simulate skill metadata with no tool restrictions
        from skillkit.core.models import SkillMetadata
        skill_metadata_none = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=tmp_path / "SKILL.md",
            allowed_tools=None
        )

        executor = ScriptExecutor(timeout=5)
        result = executor.execute(
            script_path=script_file,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=skill_metadata_none
        )

        assert result.exit_code == 0

    def test_execution_time_measurement(self, tmp_path):
        """Test that execution time is measured accurately."""
        script_file = tmp_path / "timed.py"
        script_file.write_text('''
import time
time.sleep(0.1)  # Sleep for 100ms
print("Done")
''')


        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")
        # Create minimal skill metadata
        from skillkit.core.models import SkillMetadata
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=tmp_path / "SKILL.md"
        )

        executor = ScriptExecutor(timeout=5)
        result = executor.execute(
            script_path=script_file,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=skill_metadata
        )

        assert result.exit_code == 0
        # Execution time should be at least 100ms
        assert result.execution_time_ms >= 100

    def test_argument_size_limit(self, tmp_path):
        """Test that arguments exceeding size limit are rejected."""
        script_file = tmp_path / "args.py"
        script_file.write_text('print("test")')


        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")
        # Create minimal skill metadata
        from skillkit.core.models import SkillMetadata
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=tmp_path / "SKILL.md"
        )

        # Create arguments larger than 10MB
        large_args = {"data": "x" * (11 * 1024 * 1024)}  # 11MB

        executor = ScriptExecutor(timeout=5)

        with pytest.raises(ArgumentSizeError):
            executor.execute(
                script_path=script_file,
                arguments=large_args,
                skill_base_dir=tmp_path,
                skill_metadata=skill_metadata
            )

    def test_signal_detection_sigsegv(self, tmp_path):
        """Test detection of SIGSEGV signal (Unix only)."""
        import sys
        if sys.platform == 'win32':
            pytest.skip("Signal test not applicable on Windows")

        # Create a script that causes segmentation fault
        script_file = tmp_path / "segfault.py"
        script_file.write_text('''
import ctypes
# Cause segfault by accessing invalid memory
ctypes.string_at(0)
''')


        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")
        # Create minimal skill metadata
        from skillkit.core.models import SkillMetadata
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=tmp_path / "SKILL.md"
        )

        executor = ScriptExecutor(timeout=5)
        result = executor.execute(
            script_path=script_file,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=skill_metadata
        )

        # Should detect signal (SIGSEGV = -11)
        assert result.exit_code < 0
        assert result.signaled is True
        assert result.signal is not None

    def test_interpreter_not_found_error(self, tmp_path):
        """Test that missing interpreter raises error."""
        script_file = tmp_path / "test.xyz"  # Unknown extension
        script_file.write_text('print("test")')


        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")
        # Create minimal skill metadata
        from skillkit.core.models import SkillMetadata
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=tmp_path / "SKILL.md"
        )

        executor = ScriptExecutor(timeout=5)

        with pytest.raises(InterpreterNotFoundError):
            executor.execute(
                script_path=script_file,
                arguments={},
                skill_base_dir=tmp_path,
                skill_metadata=skill_metadata
            )

    @pytest.mark.skip(reason="pytest-benchmark not installed")
    def test_execution_overhead_performance(self, tmp_path, benchmark):
        """Benchmark script execution overhead."""
        script_file = tmp_path / "fast.py"
        script_file.write_text('print("Hello")')


        # Create SKILL.md file (required by SkillMetadata)
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nname: test-skill\ndescription: Test skill\n---\n")
        # Create minimal skill metadata
        from skillkit.core.models import SkillMetadata
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test skill",
            skill_path=tmp_path / "SKILL.md"
        )

        executor = ScriptExecutor(timeout=5)

        def execute_script():
            return executor.execute(
                script_path=script_file,
                arguments={},
                skill_base_dir=tmp_path,
                skill_metadata=skill_metadata
            )

        # Benchmark execution overhead
        result = benchmark(execute_script)

        assert result.exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
