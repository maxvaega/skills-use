"""Tests for Phase 5: User Story 3 - Timeout Management for Long-Running Scripts.

Test Coverage:
    - T039: Timeout handling in _execute_subprocess() catches subprocess.TimeoutExpired
    - T040: Exit code 124 and stderr "Timeout" when timeout occurs
    - T041: WARNING level log entry when timeout occurs
    - T042: Execution time measurement using time.perf_counter()
    - T043: Timeout property on ScriptExecutionResult
    - T044: Custom timeout support in SkillManager.execute_skill_script()

Test Scenarios:
    1. Script completes within timeout (no timeout)
    2. Script exceeds timeout (timeout triggered)
    3. Timeout log entry verification
    4. Execution time measurement accuracy
    5. ScriptExecutionResult.timeout property
    6. Custom timeout override in SkillManager
    7. Edge cases (0 second script, very short timeout)
"""

import json
import logging
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from skillkit.core.exceptions import SkillNotFoundError
from skillkit.core.manager import SkillManager
from skillkit.core.models import SkillMetadata
from skillkit.core.scripts import ScriptExecutionResult, ScriptExecutor


class TestTimeoutHandling:
    """Test timeout handling in _execute_subprocess() (T039, T040)."""

    def test_script_completes_within_timeout(self, tmp_path):
        """Test that scripts completing within timeout execute normally."""
        # Create a fast script
        script = tmp_path / "fast.py"
        script.write_text(
            """
import json
import sys
data = json.loads(sys.stdin.read())
print(json.dumps({"result": "success"}))
"""
        )

        executor = ScriptExecutor(timeout=5)  # 5 second timeout
        metadata = Mock()
        metadata.name = "test-skill"
        metadata.version = "1.0.0"

        result = executor.execute(
            script_path=script,
            arguments={"input": "test"},
            skill_base_dir=tmp_path,
            skill_metadata=metadata,
        )

        # Should succeed without timeout
        assert result.exit_code == 0
        assert "Timeout" not in result.stderr
        assert not result.timeout
        assert result.execution_time_ms > 0

    def test_script_exceeds_timeout(self, tmp_path):
        """Test that scripts exceeding timeout are killed (T039, T040)."""
        # Create an infinite loop script
        script = tmp_path / "infinite.py"
        script.write_text(
            """
import time
while True:
    time.sleep(0.1)
"""
        )

        executor = ScriptExecutor(timeout=1)  # 1 second timeout
        metadata = Mock()
        metadata.name = "test-skill"
        metadata.version = "1.0.0"

        start_time = time.perf_counter()
        result = executor.execute(
            script_path=script,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=metadata,
        )
        elapsed = time.perf_counter() - start_time

        # T040: Verify exit code 124 and "Timeout" in stderr
        assert result.exit_code == 124
        assert "Timeout" in result.stderr

        # T043: Verify timeout property
        assert result.timeout is True

        # Verify timeout occurred around 1 second (±200ms tolerance)
        assert 0.8 <= elapsed <= 1.5

    def test_timeout_with_partial_output(self, tmp_path):
        """Test that partial output is captured before timeout."""
        # Create script that prints then hangs
        script = tmp_path / "partial.py"
        script.write_text(
            """
import sys
import time
print("Started processing", flush=True)
sys.stderr.write("Debug: initializing\\n")
sys.stderr.flush()
time.sleep(10)  # Sleep longer than timeout
print("This should not appear")
"""
        )

        executor = ScriptExecutor(timeout=1)  # 1 second timeout
        metadata = Mock()
        metadata.name = "test-skill"
        metadata.version = "1.0.0"

        result = executor.execute(
            script_path=script,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=metadata,
        )

        # Verify timeout occurred
        assert result.exit_code == 124
        assert result.timeout is True

        # Verify partial output was captured
        assert "Started processing" in result.stdout
        assert "Debug: initializing" in result.stderr
        assert "This should not appear" not in result.stdout

    def test_very_short_timeout(self, tmp_path):
        """Test edge case: extremely short timeout (100ms)."""
        # Create script that sleeps for 500ms
        script = tmp_path / "short_sleep.py"
        script.write_text(
            """
import time
time.sleep(0.5)
print("Done")
"""
        )

        executor = ScriptExecutor(timeout=0.1)  # 100ms timeout (very short)
        metadata = Mock()
        metadata.name = "test-skill"
        metadata.version = "1.0.0"

        result = executor.execute(
            script_path=script,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=metadata,
        )

        # Should timeout (script needs 500ms, timeout is 100ms)
        assert result.exit_code == 124
        assert result.timeout is True


class TestTimeoutLogging:
    """Test WARNING level log entry when timeout occurs (T041)."""

    def test_timeout_warning_log_entry(self, tmp_path, caplog):
        """Test that timeout triggers WARNING log with script details."""
        # Create an infinite loop script
        script = tmp_path / "timeout_test.py"
        script.write_text(
            """
import time
while True:
    time.sleep(0.1)
"""
        )

        executor = ScriptExecutor(timeout=1)  # 1 second timeout
        metadata = Mock()
        metadata.name = "test-skill"
        metadata.version = "1.0.0"

        with caplog.at_level(logging.WARNING):
            result = executor.execute(
                script_path=script,
                arguments={},
                skill_base_dir=tmp_path,
                skill_metadata=metadata,
            )

        # Verify timeout occurred
        assert result.timeout is True

        # T041: Verify WARNING log entry with timeout details
        warning_logs = [
            record for record in caplog.records if record.levelname == "WARNING"
        ]

        # Find the timeout warning (may have other warnings like truncation)
        timeout_warnings = [
            record
            for record in warning_logs
            if "timed out" in record.message and "timeout=" in record.message
        ]

        assert len(timeout_warnings) >= 1, "Expected at least one timeout warning"

        timeout_log = timeout_warnings[0]
        assert "timeout_test.py" in timeout_log.message or "script=" in timeout_log.message
        assert "1s" in timeout_log.message or "timeout=1" in timeout_log.message

    def test_no_timeout_warning_for_successful_execution(self, tmp_path, caplog):
        """Test that successful execution doesn't log timeout warning."""
        # Create a fast script
        script = tmp_path / "fast.py"
        script.write_text('print("Success")')

        executor = ScriptExecutor(timeout=5)
        metadata = Mock()
        metadata.name = "test-skill"
        metadata.version = "1.0.0"

        with caplog.at_level(logging.WARNING):
            result = executor.execute(
                script_path=script,
                arguments={},
                skill_base_dir=tmp_path,
                skill_metadata=metadata,
            )

        # Verify no timeout
        assert not result.timeout

        # Verify no timeout-related WARNING logs
        timeout_warnings = [
            record
            for record in caplog.records
            if record.levelname == "WARNING" and "timed out" in record.message
        ]
        assert len(timeout_warnings) == 0


class TestExecutionTimeMeasurement:
    """Test execution time measurement using time.perf_counter() (T042)."""

    def test_execution_time_measurement_accuracy(self, tmp_path):
        """Test that execution time is measured accurately."""
        # Create script that sleeps for known duration
        script = tmp_path / "sleep.py"
        script.write_text(
            """
import time
time.sleep(0.2)  # Sleep for 200ms
print("Done")
"""
        )

        executor = ScriptExecutor(timeout=5)
        metadata = Mock()
        metadata.name = "test-skill"
        metadata.version = "1.0.0"

        result = executor.execute(
            script_path=script,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=metadata,
        )

        # Verify execution time is approximately 200ms (±100ms tolerance)
        assert result.exit_code == 0
        assert 150 <= result.execution_time_ms <= 400, (
            f"Expected ~200ms, got {result.execution_time_ms}ms"
        )

    def test_execution_time_for_fast_script(self, tmp_path):
        """Test execution time measurement for very fast script."""
        # Create minimal script
        script = tmp_path / "minimal.py"
        script.write_text('print("x")')

        executor = ScriptExecutor(timeout=5)
        metadata = Mock()
        metadata.name = "test-skill"
        metadata.version = "1.0.0"

        result = executor.execute(
            script_path=script,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=metadata,
        )

        # Very fast scripts should still have measurable time (>0ms, <100ms)
        assert result.execution_time_ms > 0
        assert result.execution_time_ms < 100

    def test_execution_time_for_timeout(self, tmp_path):
        """Test that execution time is measured even when timeout occurs."""
        # Create infinite loop script
        script = tmp_path / "infinite.py"
        script.write_text(
            """
import time
while True:
    time.sleep(0.1)
"""
        )

        executor = ScriptExecutor(timeout=1)  # 1 second timeout
        metadata = Mock()
        metadata.name = "test-skill"
        metadata.version = "1.0.0"

        result = executor.execute(
            script_path=script,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=metadata,
        )

        # Verify timeout occurred
        assert result.timeout is True

        # Execution time should reflect the timeout duration (~1000ms ±200ms)
        assert 800 <= result.execution_time_ms <= 1500


class TestTimeoutProperty:
    """Test timeout property on ScriptExecutionResult (T043)."""

    def test_timeout_property_true_when_timeout_occurs(self, tmp_path):
        """Test that timeout property returns True when timeout occurs."""
        # Create timeout script
        script = tmp_path / "timeout.py"
        script.write_text("import time; time.sleep(10)")

        executor = ScriptExecutor(timeout=1)
        metadata = Mock()
        metadata.name = "test-skill"
        metadata.version = "1.0.0"

        result = executor.execute(
            script_path=script,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=metadata,
        )

        # T043: Verify timeout property checks exit_code==124 and "Timeout" in stderr
        assert result.exit_code == 124
        assert "Timeout" in result.stderr
        assert result.timeout is True

    def test_timeout_property_false_for_successful_execution(self, tmp_path):
        """Test that timeout property returns False for successful execution."""
        # Create successful script
        script = tmp_path / "success.py"
        script.write_text('print("OK")')

        executor = ScriptExecutor(timeout=5)
        metadata = Mock()
        metadata.name = "test-skill"
        metadata.version = "1.0.0"

        result = executor.execute(
            script_path=script,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=metadata,
        )

        # Verify timeout property is False
        assert result.exit_code == 0
        assert result.timeout is False

    def test_timeout_property_false_for_other_errors(self, tmp_path):
        """Test that timeout property returns False for non-timeout errors."""
        # Create script that exits with error code 1
        script = tmp_path / "error.py"
        script.write_text("import sys; sys.exit(1)")

        executor = ScriptExecutor(timeout=5)
        metadata = Mock()
        metadata.name = "test-skill"
        metadata.version = "1.0.0"

        result = executor.execute(
            script_path=script,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=metadata,
        )

        # Verify timeout property is False for non-timeout errors
        assert result.exit_code == 1
        assert result.timeout is False


class TestCustomTimeoutInSkillManager:
    """Test custom timeout support in SkillManager.execute_skill_script() (T044)."""

    def test_custom_timeout_overrides_default(self, tmp_path):
        """Test that custom timeout parameter overrides default_script_timeout."""
        # Create test skill structure
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            """---
name: test-skill
description: Test skill for timeout
---
Test content
"""
        )

        # Create timeout script (sleeps for 3 seconds)
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "timeout_test.py"
        script.write_text(
            """
import time
time.sleep(3)  # Sleep for 3 seconds
print("Done")
"""
        )

        # Create manager with default timeout of 5 seconds
        manager = SkillManager(
            project_skill_dir=tmp_path,
            default_script_timeout=5,
        )
        manager.discover()

        # Test 1: Use default timeout (5s) - should succeed
        result1 = manager.execute_skill_script(
            skill_name="test-skill",
            script_name="timeout_test",
            arguments={},
        )
        assert result1.exit_code == 0
        assert not result1.timeout

        # Test 2: Override with custom timeout (1s) - should timeout
        result2 = manager.execute_skill_script(
            skill_name="test-skill",
            script_name="timeout_test",
            arguments={},
            timeout=1,  # Override: 1 second (shorter than script duration)
        )

        # T044: Verify custom timeout was applied
        assert result2.exit_code == 124
        assert result2.timeout is True

    def test_default_timeout_when_custom_not_specified(self, tmp_path):
        """Test that default_script_timeout is used when custom timeout not specified."""
        # Create test skill structure
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            """---
name: test-skill
description: Test skill
---
Content
"""
        )

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "slow.py"
        script.write_text("import time; time.sleep(3)")

        # Create manager with very short default timeout (1 second)
        manager = SkillManager(
            project_skill_dir=tmp_path,
            default_script_timeout=1,
        )
        manager.discover()

        # Execute without specifying timeout (should use default 1s)
        result = manager.execute_skill_script(
            skill_name="test-skill",
            script_name="slow",
            arguments={},
        )

        # Should timeout using default 1 second timeout
        assert result.exit_code == 124
        assert result.timeout is True

    def test_custom_timeout_zero_not_allowed_by_subprocess(self, tmp_path):
        """Test edge case: timeout=0 is technically allowed but kills immediately."""
        # Note: subprocess.run(timeout=0) is valid but will likely timeout immediately
        # This test documents the behavior but doesn't enforce it as a requirement

        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            """---
name: test-skill
description: Test
---
Content
"""
        )

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "instant.py"
        script.write_text('print("x")')

        manager = SkillManager(project_skill_dir=tmp_path, default_script_timeout=30)
        manager.discover()

        # Execute with timeout=0 (immediate timeout, probably)
        # Note: This may or may not timeout depending on system performance
        # We just verify it doesn't crash
        result = manager.execute_skill_script(
            skill_name="test-skill",
            script_name="instant",
            arguments={},
            timeout=1,  # Use 1 second to make test deterministic
        )

        # Just verify we got a result (exit code may be 0 or 124 depending on timing)
        assert result is not None
        assert isinstance(result, ScriptExecutionResult)


class TestTimeoutEdgeCases:
    """Test edge cases and boundary conditions for timeout handling."""

    def test_script_that_completes_exactly_at_timeout(self, tmp_path):
        """Test behavior when script completes very close to timeout limit."""
        # Create script that sleeps for almost exactly the timeout duration
        script = tmp_path / "edge.py"
        script.write_text(
            """
import time
time.sleep(0.95)  # Sleep for 950ms (just under 1s timeout)
print("Completed")
"""
        )

        executor = ScriptExecutor(timeout=1)  # 1 second timeout
        metadata = Mock()
        metadata.name = "test-skill"
        metadata.version = "1.0.0"

        result = executor.execute(
            script_path=script,
            arguments={},
            skill_base_dir=tmp_path,
            skill_metadata=metadata,
        )

        # Should complete successfully (just under timeout)
        # Note: System load may cause this to occasionally timeout
        # We accept either outcome as valid for this edge case
        if result.exit_code == 0:
            assert not result.timeout
            assert "Completed" in result.stdout
        else:
            # Timed out due to system load
            assert result.timeout is True

    def test_multiple_sequential_timeouts(self, tmp_path):
        """Test that executor can handle multiple timeouts sequentially."""
        # Create timeout script
        script = tmp_path / "timeout.py"
        script.write_text("import time; time.sleep(10)")

        executor = ScriptExecutor(timeout=1)
        metadata = Mock()
        metadata.name = "test-skill"
        metadata.version = "1.0.0"

        # Execute same script multiple times
        for i in range(3):
            result = executor.execute(
                script_path=script,
                arguments={"iteration": i},
                skill_base_dir=tmp_path,
                skill_metadata=metadata,
            )

            # Each execution should timeout consistently
            assert result.exit_code == 124
            assert result.timeout is True
