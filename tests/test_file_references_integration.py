"""Integration tests for Phase 8 - File Reference Resolution for Skills.

This module tests:
- End-to-end file reference resolution workflow
- Integration with example file-reference-skill
- Skill invocation with supporting files
- Security validation in real-world scenarios
"""

from pathlib import Path

import pytest

from skillkit import Skill, SkillManager
from skillkit.core.exceptions import PathSecurityError
from skillkit.core.path_resolver import FilePathResolver


class TestFileReferencesIntegration:
    """Integration tests for file reference resolution feature."""

    @pytest.fixture
    def example_skills_dir(self) -> Path:
        """Get path to examples/skills directory."""
        # Assuming tests are run from repository root
        examples_dir = Path(__file__).parent.parent / "examples" / "skills"
        if not examples_dir.exists():
            pytest.skip("examples/skills directory not found")
        return examples_dir

    @pytest.fixture
    def file_reference_skill_dir(self, example_skills_dir: Path) -> Path:
        """Get path to file-reference-skill example."""
        skill_dir = example_skills_dir / "file-reference-skill"
        if not skill_dir.exists():
            pytest.skip("file-reference-skill example not found")
        return skill_dir

    def test_discover_file_reference_skill(self, example_skills_dir: Path):
        """Test that file-reference-skill is discovered successfully."""
        # Setup
        manager = SkillManager(project_skill_dir=str(example_skills_dir))

        # Test
        manager.discover()
        skills = manager.list_skills()

        # Verify - list_skills() returns list of SkillMetadata objects
        skill_names = [skill.name for skill in skills]
        assert "file-reference-skill" in skill_names

    def test_file_reference_skill_metadata(self, example_skills_dir: Path):
        """Test that file-reference-skill metadata is parsed correctly."""
        # Setup
        manager = SkillManager(project_skill_dir=str(example_skills_dir))
        manager.discover()

        # Test
        metadata = manager.get_skill("file-reference-skill")

        # Verify
        assert metadata.name == "file-reference-skill"
        assert "file reference" in metadata.description.lower()
        assert metadata.skill_path.exists()

    def test_resolve_supporting_files(self, file_reference_skill_dir: Path):
        """Test resolving all supporting files in file-reference-skill."""
        # Setup
        base_dir = file_reference_skill_dir

        # Test - resolve all expected supporting files
        supporting_files = [
            "scripts/data_processor.py",
            "scripts/validator.py",
            "scripts/helper.sh",
            "templates/config.yaml",
            "templates/report.md",
            "docs/usage.md",
            "docs/examples.md",
        ]

        for rel_path in supporting_files:
            resolved = FilePathResolver.resolve_path(base_dir, rel_path)

            # Verify
            assert resolved.exists(), f"Supporting file not found: {rel_path}"
            assert resolved.is_relative_to(base_dir)
            assert resolved.is_file()

    def test_read_supporting_file_contents(self, file_reference_skill_dir: Path):
        """Test reading contents of supporting files."""
        # Setup
        base_dir = file_reference_skill_dir

        # Test - read Python script
        script_path = FilePathResolver.resolve_path(base_dir, "scripts/data_processor.py")
        with open(script_path) as f:
            content = f.read()

        # Verify
        assert "def process_data" in content
        assert "def main" in content

        # Test - read YAML config
        config_path = FilePathResolver.resolve_path(base_dir, "templates/config.yaml")
        with open(config_path) as f:
            content = f.read()

        # Verify
        assert "processing:" in content
        assert "validation:" in content

    def test_skill_invocation_includes_base_directory(self, example_skills_dir: Path):
        """Test that skill invocation includes base directory in processed content."""
        # Setup
        manager = SkillManager(project_skill_dir=str(example_skills_dir))
        manager.discover()

        # Test
        result = manager.invoke_skill("file-reference-skill", "test arguments")

        # Verify
        assert "Base directory for this skill:" in result
        assert "file-reference-skill" in result
        assert "FilePathResolver.resolve_path" in result
        assert "securely access files" in result

    def test_skill_invocation_includes_file_resolution_helper(
        self, example_skills_dir: Path
    ):
        """Test that skill invocation includes file path resolution helper."""
        # Setup
        manager = SkillManager(project_skill_dir=str(example_skills_dir))
        manager.discover()

        # Test
        result = manager.invoke_skill("file-reference-skill", "test")

        # Verify
        assert "Supporting files can be referenced using relative paths" in result
        assert "FilePathResolver.resolve_path" in result
        assert "base_dir" in result
        assert "relative_path" in result

    def test_security_prevents_traversal_in_real_skill(
        self, file_reference_skill_dir: Path
    ):
        """Test that path traversal is prevented in real skill directory."""
        # Setup
        base_dir = file_reference_skill_dir

        # Test - try various traversal attacks
        attack_paths = [
            "../../../etc/passwd",
            "../../../../../../etc/shadow",
            "/etc/passwd",
            "scripts/../../../etc/passwd",
        ]

        for attack_path in attack_paths:
            with pytest.raises(PathSecurityError):
                FilePathResolver.resolve_path(base_dir, attack_path)

    def test_skill_with_nested_directory_structure(self, file_reference_skill_dir: Path):
        """Test resolving files in nested directory structure."""
        # Setup
        base_dir = file_reference_skill_dir

        # Test - resolve deeply nested file
        resolved = FilePathResolver.resolve_path(base_dir, "docs/usage.md")

        # Verify
        assert resolved.exists()
        assert resolved.is_relative_to(base_dir)

        # Read content
        with open(resolved) as f:
            content = f.read()

        assert "File Reference Skill" in content
        assert "Usage Guide" in content

    def test_skill_base_directory_property(self, example_skills_dir: Path):
        """Test that Skill object has base_directory property."""
        # Setup
        manager = SkillManager(project_skill_dir=str(example_skills_dir))
        manager.discover()
        metadata = manager.get_skill("file-reference-skill")

        # Test - create Skill object
        skill = Skill(metadata=metadata, base_directory=metadata.skill_path.parent)

        # Verify
        assert hasattr(skill, "base_directory")
        assert skill.base_directory == metadata.skill_path.parent
        assert skill.base_directory.is_dir()

    def test_multiple_skills_with_file_references(self, example_skills_dir: Path):
        """Test that multiple skills can have their own supporting files."""
        # Setup
        manager = SkillManager(project_skill_dir=str(example_skills_dir))
        manager.discover()

        # Get file-reference-skill
        metadata1 = manager.get_skill("file-reference-skill")
        skill1 = Skill(metadata=metadata1, base_directory=metadata1.skill_path.parent)

        # Test - each skill has its own isolated base directory
        assert skill1.base_directory.name == "file-reference-skill"

        # Verify supporting files are isolated to this skill's directory
        scripts_dir = skill1.base_directory / "scripts"
        assert scripts_dir.exists()
        assert scripts_dir.is_relative_to(skill1.base_directory)

    def test_file_reference_skill_structure(self, file_reference_skill_dir: Path):
        """Test that file-reference-skill has expected directory structure."""
        # Verify directory structure
        assert (file_reference_skill_dir / "SKILL.md").exists()
        assert (file_reference_skill_dir / "scripts").is_dir()
        assert (file_reference_skill_dir / "templates").is_dir()
        assert (file_reference_skill_dir / "docs").is_dir()

        # Verify scripts
        assert (file_reference_skill_dir / "scripts" / "data_processor.py").exists()
        assert (file_reference_skill_dir / "scripts" / "validator.py").exists()
        assert (file_reference_skill_dir / "scripts" / "helper.sh").exists()

        # Verify templates
        assert (file_reference_skill_dir / "templates" / "config.yaml").exists()
        assert (file_reference_skill_dir / "templates" / "report.md").exists()

        # Verify docs
        assert (file_reference_skill_dir / "docs" / "usage.md").exists()
        assert (file_reference_skill_dir / "docs" / "examples.md").exists()


class TestFileReferencesSecurityIntegration:
    """Integration tests for security aspects of file reference resolution."""

    @pytest.fixture
    def temp_skill_with_symlinks(self, tmp_path: Path) -> Path:
        """Create temporary skill with symlinks for testing."""
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        # Create SKILL.md
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            "---\nname: test-skill\ndescription: Test skill with symlinks\n---\n\nTest content"
        )

        # Create legitimate file
        (skill_dir / "scripts").mkdir()
        legit_file = skill_dir / "scripts" / "legit.py"
        legit_file.write_text("print('legitimate')")

        # Create file outside skill directory
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        secret_file = outside_dir / "secret.txt"
        secret_file.write_text("sensitive data")

        # Create symlink to outside file
        try:
            symlink = skill_dir / "escape_link"
            symlink.symlink_to(secret_file)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

        return skill_dir

    def test_symlink_escape_blocked_in_real_scenario(
        self, temp_skill_with_symlinks: Path
    ):
        """Test that symlink escapes are blocked in real skill usage."""
        # Setup
        base_dir = temp_skill_with_symlinks

        # Test - legitimate file should work
        legit_path = FilePathResolver.resolve_path(base_dir, "scripts/legit.py")
        assert legit_path.exists()

        # Test - symlink escape should be blocked
        with pytest.raises(PathSecurityError):
            FilePathResolver.resolve_path(base_dir, "escape_link")

    def test_absolute_path_blocked_in_real_scenario(self, tmp_path: Path):
        """Test that absolute paths are blocked in real skill usage."""
        # Setup
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        # Test - absolute path should be blocked
        with pytest.raises(PathSecurityError):
            FilePathResolver.resolve_path(skill_dir, "/etc/passwd")

    def test_parent_traversal_blocked_in_real_scenario(self, tmp_path: Path):
        """Test that parent directory traversal is blocked in real skill usage."""
        # Setup
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()

        # Create nested structure
        (skill_dir / "scripts").mkdir()

        # Test - traversal out of skill directory should be blocked
        with pytest.raises(PathSecurityError):
            FilePathResolver.resolve_path(skill_dir, "scripts/../../etc/passwd")


class TestFileReferencesPerformance:
    """Performance tests for file reference resolution."""

    def test_resolve_many_files_performance(self, tmp_path: Path):
        """Test performance of resolving many files."""
        import time

        # Setup - create skill with many files
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "files").mkdir()

        # Create 100 files
        for i in range(100):
            (skill_dir / "files" / f"file{i}.txt").write_text(f"content{i}")

        # Test - resolve all files and measure time
        start = time.time()
        for i in range(100):
            resolved = FilePathResolver.resolve_path(skill_dir, f"files/file{i}.txt")
            assert resolved.exists()
        elapsed = time.time() - start

        # Verify - should be fast (< 100ms for 100 files)
        assert elapsed < 0.1, f"Resolution took {elapsed:.3f}s (expected < 0.1s)"

    def test_security_check_overhead(self, tmp_path: Path):
        """Test that security validation has minimal overhead."""
        import time

        # Setup
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        test_file = skill_dir / "test.txt"
        test_file.write_text("content")

        # Test - measure resolution time
        iterations = 1000
        start = time.time()
        for _ in range(iterations):
            FilePathResolver.resolve_path(skill_dir, "test.txt")
        elapsed = time.time() - start

        # Verify - should be < 1ms per resolution
        per_call = elapsed / iterations
        assert per_call < 0.001, f"Resolution took {per_call*1000:.2f}ms per call (expected < 1ms)"
