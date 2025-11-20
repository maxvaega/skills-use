"""Tests for script detection functionality."""
import pytest
from pathlib import Path
from skillkit.core.scripts import ScriptDetector, ScriptMetadata


class TestScriptDetector:
    """Test suite for ScriptDetector class."""

    def test_detect_python_scripts(self, tmp_path):
        """Test detection of Python scripts."""
        # Create a test skill directory with Python script
        skill_dir = tmp_path / "test-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        script_file = scripts_dir / "test.py"
        script_file.write_text('"""Test script"""\nprint("Hello")')

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 1
        assert scripts[0].name == "test"
        assert scripts[0].script_type == "python"
        assert scripts[0].description == "Test script"

    def test_detect_shell_scripts(self, tmp_path):
        """Test detection of Shell scripts."""
        skill_dir = tmp_path / "test-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        script_file = scripts_dir / "test.sh"
        script_file.write_text('#!/bin/bash\n# Test shell script\necho "Hello"')

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 1
        assert scripts[0].name == "test"
        assert scripts[0].script_type == "shell"
        assert scripts[0].description == "Test shell script"

    def test_detect_javascript_scripts(self, tmp_path):
        """Test detection of JavaScript scripts."""
        skill_dir = tmp_path / "test-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        script_file = scripts_dir / "test.js"
        script_file.write_text('// Test JavaScript script\nconsole.log("Hello");')

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 1
        assert scripts[0].name == "test"
        assert scripts[0].script_type == "javascript"

    def test_detect_ruby_scripts(self, tmp_path):
        """Test detection of Ruby scripts."""
        skill_dir = tmp_path / "test-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        script_file = scripts_dir / "test.rb"
        script_file.write_text('# Test Ruby script\nputs "Hello"')

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 1
        assert scripts[0].name == "test"
        assert scripts[0].script_type == "ruby"

    def test_detect_perl_scripts(self, tmp_path):
        """Test detection of Perl scripts."""
        skill_dir = tmp_path / "test-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        script_file = scripts_dir / "test.pl"
        script_file.write_text('# Test Perl script\nprint "Hello\\n";')

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 1
        assert scripts[0].name == "test"
        assert scripts[0].script_type == "perl"

    def test_skip_non_script_files(self, tmp_path):
        """Test that non-script files are skipped."""
        skill_dir = tmp_path / "test-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        # Create non-script files
        (scripts_dir / "data.json").write_text('{}')
        (scripts_dir / "README.md").write_text('# Readme')
        (scripts_dir / "config.txt").write_text('config')

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 0

    def test_skip_hidden_files(self, tmp_path):
        """Test that hidden files are skipped."""
        skill_dir = tmp_path / "test-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        # Create hidden Python file
        (scripts_dir / ".hidden.py").write_text('print("hidden")')

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 0

    def test_skip_pycache_directory(self, tmp_path):
        """Test that __pycache__ directories are skipped."""
        skill_dir = tmp_path / "test-skill"
        scripts_dir = skill_dir / "scripts"
        pycache_dir = scripts_dir / "__pycache__"
        pycache_dir.mkdir(parents=True)

        # Create a .pyc file
        (pycache_dir / "test.cpython-310.pyc").write_bytes(b"fake bytecode")

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 0

    def test_nested_directories_within_max_depth(self, tmp_path):
        """Test detection in nested directories up to max_depth."""
        skill_dir = tmp_path / "test-skill"

        # Create nested structure: scripts/utils/helpers/test.py (3 levels deep)
        nested_dir = skill_dir / "scripts" / "utils" / "helpers"
        nested_dir.mkdir(parents=True)

        script_file = nested_dir / "test.py"
        script_file.write_text('"""Nested script"""\nprint("Hello")')

        detector = ScriptDetector(max_depth=5)
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 1
        assert scripts[0].name == "test"

    def test_nested_directories_exceeding_max_depth(self, tmp_path):
        """Test that scripts beyond max_depth are not detected."""
        skill_dir = tmp_path / "test-skill"

        # Create very nested structure (6 levels deep)
        nested_dir = skill_dir / "scripts" / "l1" / "l2" / "l3" / "l4" / "l5"
        nested_dir.mkdir(parents=True)

        script_file = nested_dir / "test.py"
        script_file.write_text('print("too deep")')

        detector = ScriptDetector(max_depth=3)
        scripts = detector.detect_scripts(skill_dir)

        # Should not find the script because it's too deep
        assert len(scripts) == 0

    def test_extract_python_docstring(self, tmp_path):
        """Test extraction of Python docstrings."""
        skill_dir = tmp_path / "test-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        script_file = scripts_dir / "test.py"
        script_file.write_text('''"""
This is a multi-line
Python docstring.
"""
print("Hello")
''')

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 1
        assert "multi-line" in scripts[0].description
        assert "Python docstring" in scripts[0].description

    def test_extract_shell_comment(self, tmp_path):
        """Test extraction of shell script comments."""
        skill_dir = tmp_path / "test-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        script_file = scripts_dir / "test.sh"
        script_file.write_text('''#!/bin/bash
# This is a shell script
# that does something useful
echo "Hello"
''')

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 1
        assert "shell script" in scripts[0].description

    def test_extract_jsdoc_comment(self, tmp_path):
        """Test extraction of JSDoc comments."""
        skill_dir = tmp_path / "test-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        script_file = scripts_dir / "test.js"
        script_file.write_text('''/**
 * This is a JSDoc comment
 * for a JavaScript file
 */
console.log("Hello");
''')

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 1
        assert "JSDoc comment" in scripts[0].description

    def test_empty_description_when_no_comments(self, tmp_path):
        """Test that description is empty when no comments exist."""
        skill_dir = tmp_path / "test-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        script_file = scripts_dir / "test.py"
        script_file.write_text('print("Hello")')

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 1
        assert scripts[0].description == ""

    def test_detect_multiple_scripts(self, tmp_path):
        """Test detection of multiple scripts in one skill."""
        skill_dir = tmp_path / "test-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        (scripts_dir / "extract.py").write_text('"""Extract data"""\npass')
        (scripts_dir / "convert.sh").write_text('#!/bin/bash\n# Convert format\necho "convert"')
        (scripts_dir / "parse.js").write_text('// Parse JSON\nconsole.log("parse");')

        detector = ScriptDetector()
        scripts = detector.detect_scripts(skill_dir)

        assert len(scripts) == 3
        script_names = {s.name for s in scripts}
        assert script_names == {"extract", "convert", "parse"}

    def test_graceful_degradation_on_file_read_error(self, tmp_path):
        """Test graceful handling when a file cannot be read."""
        skill_dir = tmp_path / "test-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        # Create a valid script
        (scripts_dir / "valid.py").write_text('"""Valid script"""\npass')

        # Create a script file and make it unreadable (Unix-only)
        import sys
        if sys.platform != 'win32':
            invalid_file = scripts_dir / "invalid.py"
            invalid_file.write_text('print("test")')
            invalid_file.chmod(0o000)  # Remove all permissions

            detector = ScriptDetector()
            scripts = detector.detect_scripts(skill_dir)

            # Should still detect the valid script
            assert len(scripts) >= 1
            assert any(s.name == "valid" for s in scripts)

            # Cleanup
            invalid_file.chmod(0o644)

    @pytest.mark.skip(reason="pytest-benchmark not installed")
    def test_detection_performance_benchmark(self, tmp_path, benchmark):
        """Benchmark script detection performance."""
        skill_dir = tmp_path / "test-skill"
        scripts_dir = skill_dir / "scripts"
        scripts_dir.mkdir(parents=True)

        # Create 50 test scripts
        for i in range(50):
            script_file = scripts_dir / f"script_{i}.py"
            script_file.write_text(f'"""Script {i}"""\npass')

        detector = ScriptDetector()

        # Benchmark should complete in < 10ms
        result = benchmark(detector.detect_scripts, skill_dir)

        assert len(result) == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
