"""Tests for Phase 3: Core Script Execution Functionality.

Tests focus on:
- T015-T020: Script detection and metadata extraction
- T021-T033: Script execution, timeout, output capture, and integration
"""

import json
import logging
import os
import time
from pathlib import Path

import pytest

from skillkit.core.exceptions import (
    InterpreterNotFoundError,
    ScriptNotFoundError,
)
from skillkit.core.models import SkillMetadata
from skillkit.core.scripts import (
    ScriptDescriptionExtractor,
    ScriptDetector,
    ScriptExecutor,
    ScriptMetadata,
)


class TestScriptDescriptionExtractor:
    """Test description extraction from script comments (T015)."""

    def test_extract_python_docstring(self, tmp_path):
        """Test extraction of Python docstrings."""
        script = tmp_path / "test.py"
        script.write_text(
            '''"""Extract text from PDF files.

This is a multi-line docstring.
"""
import sys
'''
        )

        extractor = ScriptDescriptionExtractor()
        description = extractor.extract(script)

        # Single-line docstring test
        assert "Extract text from PDF" in description or "multi-line" in description

    def test_extract_python_hash_comments(self, tmp_path):
        """Test extraction of Python # comments."""
        script = tmp_path / "test.py"
        script.write_text(
            """# Extract text from PDF files
# This script processes PDF documents
import sys
"""
        )

        extractor = ScriptDescriptionExtractor()
        description = extractor.extract(script)

        assert "Extract text from PDF" in description

    def test_extract_shell_comments(self, tmp_path):
        """Test extraction of shell # comments."""
        script = tmp_path / "test.sh"
        script.write_text(
            """#!/bin/bash
# Convert PDF to text format
# Handles multiple files

echo "Processing..."
"""
        )

        extractor = ScriptDescriptionExtractor()
        description = extractor.extract(script)

        assert "Convert PDF" in description

    def test_extract_javascript_comments(self, tmp_path):
        """Test extraction of JavaScript // and /* */ comments."""
        script = tmp_path / "test.js"
        script.write_text(
            """/* Extract metadata from documents
   Supports multiple formats */
function extract() {
  console.log("Extracting...");
}
"""
        )

        extractor = ScriptDescriptionExtractor()
        description = extractor.extract(script)

        assert "Extract metadata" in description

    def test_truncates_long_descriptions(self, tmp_path):
        """Test that long descriptions are truncated to max_chars."""
        script = tmp_path / "test.py"
        long_desc = "x" * 1000
        script.write_text(f'"""{long_desc}"""')

        extractor = ScriptDescriptionExtractor(max_chars=100)
        description = extractor.extract(script)

        assert len(description) <= 100

    def test_empty_description_for_no_comments(self, tmp_path):
        """Test that scripts without comments have empty description."""
        script = tmp_path / "test.py"
        script.write_text("import sys\nprint('hello')")

        extractor = ScriptDescriptionExtractor()
        description = extractor.extract(script)

        assert description == ""


class TestScriptDetector:
    """Test script detection in skill directories (T016-T020)."""

    def test_detects_python_scripts(self, tmp_path):
        """Test detection of Python scripts (T016)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()

        # Create scripts
        (scripts_dir / "extract.py").write_text("print('extract')")
        (scripts_dir / "parse.py").write_text("print('parse')")

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 2
        assert any(s.name == "extract" for s in scripts)
        assert any(s.name == "parse" for s in scripts)

    def test_detects_multiple_script_types(self, tmp_path):
        """Test detection of various script types (T016)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()

        # Create scripts of different types
        (scripts_dir / "python.py").write_text("print('py')")
        (scripts_dir / "shell.sh").write_text("#!/bin/bash\necho 'sh'")
        (scripts_dir / "javascript.js").write_text("console.log('js')")
        (scripts_dir / "ruby.rb").write_text("puts 'rb'")

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 4
        assert any(s.script_type == "python" for s in scripts)
        assert any(s.script_type == "shell" for s in scripts)
        assert any(s.script_type == "javascript" for s in scripts)
        assert any(s.script_type == "ruby" for s in scripts)

    def test_skips_non_script_files(self, tmp_path):
        """Test that non-script files are skipped (T018)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()

        # Create script and non-script files
        (scripts_dir / "script.py").write_text("print('hello')")
        (scripts_dir / "readme.md").write_text("# README")
        (scripts_dir / "data.json").write_text('{"key": "value"}')

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 1
        assert scripts[0].name == "script"

    def test_skips_hidden_files(self, tmp_path):
        """Test that hidden files are skipped (T018)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()

        # Create visible and hidden scripts
        (scripts_dir / "visible.py").write_text("print('visible')")
        (scripts_dir / ".hidden.py").write_text("print('hidden')")

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 1
        assert scripts[0].name == "visible"

    def test_detects_nested_scripts(self, tmp_path):
        """Test detection of scripts in nested directories (T016)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()

        # Create nested structure
        (scripts_dir / "root.py").write_text("print('root')")
        (scripts_dir / "utils").mkdir()
        (scripts_dir / "utils" / "helper.py").write_text("print('helper')")
        (scripts_dir / "utils" / "lib").mkdir()
        (scripts_dir / "utils" / "lib" / "parser.py").write_text("print('parser')")

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 3
        assert any(s.name == "root" for s in scripts)
        assert any(s.name == "helper" for s in scripts)
        assert any(s.name == "parser" for s in scripts)

    def test_skips_cache_directories(self, tmp_path):
        """Test that cache directories are skipped (T018)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()

        # Create scripts in cache directories
        (scripts_dir / "script.py").write_text("print('script')")
        (scripts_dir / "__pycache__").mkdir()
        (scripts_dir / "__pycache__" / "cached.py").write_text("print('cached')")

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 1
        assert scripts[0].name == "script"

    def test_extracts_metadata(self, tmp_path):
        """Test metadata extraction during detection (T019)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "extract.py"
        script.write_text('"""Extract text from files."""\nprint("hello")')

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 1
        meta = scripts[0]
        assert meta.name == "extract"
        assert meta.script_type == "python"
        assert "Extract text" in meta.description
        assert meta.path == Path("scripts/extract.py")

    def test_detects_scripts_in_root_directory(self, tmp_path):
        """Test detection of scripts in skill root (T017)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        # Create scripts in root
        (skill_dir / "root_script.py").write_text("print('root')")

        # Create scripts in scripts/ dir
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "sub_script.py").write_text("print('sub')")

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 2
        names = {s.name for s in scripts}
        assert "root_script" in names
        assert "sub_script" in names


class TestScriptExecution:
    """Test core script execution functionality (T021-T030)."""

    def test_successful_execution(self, tmp_path):
        """Test successful script execution (T030)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "test.py"
        script.write_text("import json; print(json.dumps({'status': 'success'}))")

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# Test")

        executor = ScriptExecutor()
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            skill_path=skill_md,
            allowed_tools=()
        )

        result = executor.execute(
            script_path=script.relative_to(skill_dir),
            arguments={},
            skill_base_dir=skill_dir,
            skill_metadata=skill_metadata
        )

        assert result.success
        assert result.exit_code == 0
        assert "success" in result.stdout

    def test_failed_execution(self, tmp_path):
        """Test failed script execution."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "fail.py"
        script.write_text("import sys; print('error', file=sys.stderr); sys.exit(1)")

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# Test")

        executor = ScriptExecutor()
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            skill_path=skill_md,
            allowed_tools=()
        )

        result = executor.execute(
            script_path=script.relative_to(skill_dir),
            arguments={},
            skill_base_dir=skill_dir,
            skill_metadata=skill_metadata
        )

        assert not result.success
        assert result.exit_code == 1
        assert "error" in result.stderr

    def test_json_stdin_arguments(self, tmp_path):
        """Test passing arguments via JSON stdin (T025)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "echo.py"
        script.write_text(
            "import json, sys; args = json.load(sys.stdin); print(json.dumps(args))"
        )

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# Test")

        executor = ScriptExecutor()
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            skill_path=skill_md,
            allowed_tools=()
        )

        test_args = {"key": "value", "number": 42}
        result = executor.execute(
            script_path=script.relative_to(skill_dir),
            arguments=test_args,
            skill_base_dir=skill_dir,
            skill_metadata=skill_metadata
        )

        assert result.success
        output = json.loads(result.stdout)
        assert output["key"] == "value"
        assert output["number"] == 42

    def test_environment_variable_injection(self, tmp_path):
        """Test environment variable injection (T026)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "env.py"
        script.write_text(
            "import os; print(f'{os.environ.get(\"SKILL_NAME\")}:{os.environ.get(\"SKILL_BASE_DIR\")}')"
        )

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# Test")

        executor = ScriptExecutor()
        skill_metadata = SkillMetadata(
            name="my-skill",
            description="Test",
            skill_path=skill_md,
            allowed_tools=()
        )

        result = executor.execute(
            script_path=script.relative_to(skill_dir),
            arguments={},
            skill_base_dir=skill_dir,
            skill_metadata=skill_metadata
        )

        assert result.success
        assert "my-skill" in result.stdout

    def test_output_capture(self, tmp_path):
        """Test stdout/stderr capture (T027)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "output.py"
        script.write_text(
            "print('stdout line'); import sys; print('stderr line', file=sys.stderr)"
        )

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# Test")

        executor = ScriptExecutor()
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            skill_path=skill_md,
            allowed_tools=()
        )

        result = executor.execute(
            script_path=script.relative_to(skill_dir),
            arguments={},
            skill_base_dir=skill_dir,
            skill_metadata=skill_metadata
        )

        assert "stdout line" in result.stdout
        assert "stderr line" in result.stderr

    def test_timeout_detection(self, tmp_path):
        """Test timeout detection with exit code 124 (T029)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "slow.py"
        script.write_text("import time; time.sleep(5); print('done')")

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# Test")

        executor = ScriptExecutor(timeout=1)  # 1 second timeout
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            skill_path=skill_md,
            allowed_tools=()
        )

        result = executor.execute(
            script_path=script.relative_to(skill_dir),
            arguments={},
            skill_base_dir=skill_dir,
            skill_metadata=skill_metadata
        )

        assert result.timeout
        assert result.exit_code == 124
        assert "Timeout" in result.stderr

    def test_output_truncation(self, tmp_path):
        """Test output truncation at size limit (T028)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "bigout.py"
        script.write_text("print('x' * 1000000)")  # 1MB of output

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# Test")

        executor = ScriptExecutor(max_output_size=100000)  # 100KB limit
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            skill_path=skill_md,
            allowed_tools=()
        )

        result = executor.execute(
            script_path=script.relative_to(skill_dir),
            arguments={},
            skill_base_dir=skill_dir,
            skill_metadata=skill_metadata
        )

        assert result.stdout_truncated
        assert "OUTPUT TRUNCATED" in result.stdout

    def test_execution_timing(self, tmp_path):
        """Test execution time measurement (T042)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()
        script = scripts_dir / "timed.py"
        script.write_text("import time; time.sleep(0.1); print('done')")

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# Test")

        executor = ScriptExecutor()
        skill_metadata = SkillMetadata(
            name="test-skill",
            description="Test",
            skill_path=skill_md,
            allowed_tools=()
        )

        result = executor.execute(
            script_path=script.relative_to(skill_dir),
            arguments={},
            skill_base_dir=skill_dir,
            skill_metadata=skill_metadata
        )

        # Should take at least 100ms
        assert result.execution_time_ms >= 100

    def test_interpreter_resolution(self, tmp_path):
        """Test interpreter resolution from extension (T024)."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()

        # Test with Python
        script = scripts_dir / "test.py"
        script.write_text("print('python')")

        executor = ScriptExecutor()
        interpreter = executor._resolve_interpreter(script)

        assert interpreter == "python3"

    def test_missing_interpreter_error(self, tmp_path):
        """Test error when interpreter not found."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()

        # Create script with unknown extension
        script = scripts_dir / "test.unknown"
        script.write_text("echo 'unknown'")

        executor = ScriptExecutor()

        with pytest.raises(InterpreterNotFoundError):
            executor._resolve_interpreter(script)


class TestPhase3Checkpoint:
    """Integration tests for Phase 3 checkpoint."""

    def test_end_to_end_execution_flow(self, tmp_path):
        """Test complete end-to-end script execution flow."""
        # Setup skill directory
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        # Create scripts directory with multiple scripts
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()

        # Create a processing script
        process_script = scripts_dir / "process.py"
        process_script.write_text(
            """import json
import sys

data = json.load(sys.stdin)
result = {
    "status": "processed",
    "count": len(str(data)),
    "input": data
}
print(json.dumps(result))
"""
        )

        # Create SKILL.md
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# Processing Skill\nProcesses data efficiently")

        # Test detection
        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)
        assert len(scripts) == 1
        assert scripts[0].name == "process"

        # Test execution
        executor = ScriptExecutor()
        skill_metadata = SkillMetadata(
            name="processor",
            description="Processes data",
            skill_path=skill_md,
            allowed_tools=()
        )

        test_input = {"data": "test value"}
        result = executor.execute(
            script_path=scripts[0].path,
            arguments=test_input,
            skill_base_dir=skill_dir,
            skill_metadata=skill_metadata
        )

        assert result.success
        output = json.loads(result.stdout)
        assert output["status"] == "processed"
        assert output["input"]["data"] == "test value"

    def test_multiple_script_execution(self, tmp_path):
        """Test execution of multiple scripts in one skill."""
        skill_dir = tmp_path / "skill"
        skill_dir.mkdir()

        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir()

        # Create multiple scripts
        for i in range(3):
            script = scripts_dir / f"script{i}.py"
            script.write_text(f"print('script {i}')")

        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text("# Multi-Script Skill")

        # Detect all scripts
        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 3

        # Execute each script
        executor = ScriptExecutor()
        skill_metadata = SkillMetadata(
            name="multi-skill",
            description="Multiple scripts",
            skill_path=skill_md,
            allowed_tools=()
        )

        for script_meta in scripts:
            result = executor.execute(
                script_path=script_meta.path,
                arguments={},
                skill_base_dir=skill_dir,
                skill_metadata=skill_metadata
            )

            assert result.success
            assert f"script {script_meta.name[-1]}" in result.stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
