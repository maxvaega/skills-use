"""Tests for FilePathResolver - Secure file path resolution for skill supporting files.

This module tests:
- Valid relative path resolution
- Path traversal prevention (../, absolute paths)
- Symlink resolution and escape detection
- Security error logging
- Edge cases and error conditions
"""

import logging
import os
from pathlib import Path

import pytest

from skillkit.core.exceptions import PathSecurityError
from skillkit.core.path_resolver import FilePathResolver


class TestFilePathResolver:
    """Test suite for FilePathResolver class."""

    def test_resolve_valid_relative_path(self, tmp_path: Path):
        """Test resolving valid relative path within base directory."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()
        (base_dir / "scripts").mkdir()
        script_file = base_dir / "scripts" / "helper.py"
        script_file.write_text("print('hello')")

        # Test
        resolved = FilePathResolver.resolve_path(base_dir, "scripts/helper.py")

        # Verify
        assert resolved == script_file
        assert resolved.exists()
        assert resolved.is_relative_to(base_dir)

    def test_resolve_nested_relative_path(self, tmp_path: Path):
        """Test resolving deeply nested relative path."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()
        nested_dir = base_dir / "a" / "b" / "c"
        nested_dir.mkdir(parents=True)
        nested_file = nested_dir / "deep.txt"
        nested_file.write_text("content")

        # Test
        resolved = FilePathResolver.resolve_path(base_dir, "a/b/c/deep.txt")

        # Verify
        assert resolved == nested_file
        assert resolved.is_relative_to(base_dir)

    def test_resolve_current_directory(self, tmp_path: Path):
        """Test resolving current directory (.)."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()
        file_path = base_dir / "file.txt"
        file_path.write_text("content")

        # Test
        resolved = FilePathResolver.resolve_path(base_dir, "./file.txt")

        # Verify
        assert resolved == file_path
        assert resolved.is_relative_to(base_dir)

    def test_resolve_redundant_separators(self, tmp_path: Path):
        """Test resolving path with redundant separators (//)."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()
        (base_dir / "scripts").mkdir()
        script_file = base_dir / "scripts" / "helper.py"
        script_file.write_text("content")

        # Test
        resolved = FilePathResolver.resolve_path(base_dir, "scripts//helper.py")

        # Verify
        assert resolved == script_file
        assert resolved.is_relative_to(base_dir)

    def test_block_simple_path_traversal(self, tmp_path: Path):
        """Test blocking simple path traversal with ../."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()

        # Test & Verify
        with pytest.raises(PathSecurityError, match="Path traversal attempt detected"):
            FilePathResolver.resolve_path(base_dir, "../etc/passwd")

    def test_block_deep_path_traversal(self, tmp_path: Path):
        """Test blocking deep path traversal with multiple ../."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()

        # Test & Verify
        with pytest.raises(PathSecurityError, match="Path traversal attempt detected"):
            FilePathResolver.resolve_path(base_dir, "../../../../../../etc/passwd")

    def test_block_mixed_path_traversal(self, tmp_path: Path):
        """Test blocking path traversal mixed with valid path components."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()
        (base_dir / "scripts").mkdir()

        # Test & Verify
        with pytest.raises(PathSecurityError, match="Path traversal attempt detected"):
            FilePathResolver.resolve_path(base_dir, "scripts/../../../etc/passwd")

    def test_block_absolute_path_unix(self, tmp_path: Path):
        """Test blocking absolute Unix path."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()

        # Test & Verify
        with pytest.raises(PathSecurityError, match="Path traversal attempt detected"):
            FilePathResolver.resolve_path(base_dir, "/etc/passwd")

    @pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
    def test_block_absolute_path_windows(self, tmp_path: Path):
        """Test blocking absolute Windows path."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()

        # Test & Verify
        with pytest.raises(PathSecurityError, match="Path traversal attempt detected"):
            FilePathResolver.resolve_path(base_dir, "C:\\Windows\\System32")

    @pytest.mark.skipif(os.name != "nt", reason="Windows-specific test")
    def test_block_unc_path(self, tmp_path: Path):
        """Test blocking UNC path (Windows network path)."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()

        # Test & Verify - UNC paths should be blocked on Windows
        with pytest.raises(PathSecurityError):
            FilePathResolver.resolve_path(base_dir, "\\\\server\\share\\file")

    def test_symlink_within_base(self, tmp_path: Path):
        """Test resolving symlink that points within base directory."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()
        (base_dir / "scripts").mkdir()
        target_file = base_dir / "scripts" / "helper.py"
        target_file.write_text("content")

        # Create symlink
        link_file = base_dir / "link.py"
        try:
            link_file.symlink_to(target_file)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

        # Test
        resolved = FilePathResolver.resolve_path(base_dir, "link.py")

        # Verify - symlink should be resolved to target
        assert resolved.resolve() == target_file.resolve()
        assert resolved.is_relative_to(base_dir)

    def test_block_symlink_escape(self, tmp_path: Path):
        """Test blocking symlink that escapes base directory."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()

        # Create target outside base directory
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        target_file = outside_dir / "secret.txt"
        target_file.write_text("sensitive data")

        # Create symlink inside base directory pointing outside
        link_file = base_dir / "escape_link"
        try:
            link_file.symlink_to(target_file)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

        # Test & Verify - should block symlink escape
        with pytest.raises(PathSecurityError, match="Path traversal attempt detected"):
            FilePathResolver.resolve_path(base_dir, "escape_link")

    def test_block_circular_symlink(self, tmp_path: Path):
        """Test handling circular symlink (should raise error)."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()

        link1 = base_dir / "link1"
        link2 = base_dir / "link2"

        try:
            link1.symlink_to(link2)
            link2.symlink_to(link1)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")

        # Test & Verify - circular symlink should raise error
        with pytest.raises(PathSecurityError):
            FilePathResolver.resolve_path(base_dir, "link1")

    def test_resolve_nonexistent_path(self, tmp_path: Path):
        """Test resolving path to non-existent file (should succeed - validation only)."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()

        # Test - should resolve even if file doesn't exist (just validates path is safe)
        resolved = FilePathResolver.resolve_path(base_dir, "nonexistent.txt")

        # Verify
        assert resolved == base_dir / "nonexistent.txt"
        assert not resolved.exists()
        assert resolved.is_relative_to(base_dir)

    def test_resolve_empty_path(self, tmp_path: Path):
        """Test resolving empty path string."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()

        # Test
        resolved = FilePathResolver.resolve_path(base_dir, "")

        # Verify - empty path resolves to base directory itself
        assert resolved == base_dir

    def test_resolve_root_path(self, tmp_path: Path):
        """Test resolving root path (.)."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()

        # Test
        resolved = FilePathResolver.resolve_path(base_dir, ".")

        # Verify
        assert resolved == base_dir

    def test_security_logging_on_traversal(self, tmp_path: Path, caplog):
        """Test that path traversal attempts are logged at ERROR level."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()

        # Test
        with caplog.at_level(logging.ERROR):
            with pytest.raises(PathSecurityError):
                FilePathResolver.resolve_path(base_dir, "../../../etc/passwd")

        # Verify logging
        assert len(caplog.records) > 0
        error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(error_logs) > 0
        assert "SECURITY VIOLATION" in error_logs[0].message
        assert "Path traversal attempt detected" in error_logs[0].message

    def test_security_logging_includes_context(self, tmp_path: Path, caplog):
        """Test that security error logging includes detailed context."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()

        # Test
        with caplog.at_level(logging.ERROR):
            with pytest.raises(PathSecurityError):
                FilePathResolver.resolve_path(base_dir, "../secret.txt")

        # Verify logging context
        error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
        assert len(error_logs) > 0

        # Check that log record has extra context
        log_record = error_logs[0]
        assert hasattr(log_record, "base_directory")
        assert hasattr(log_record, "requested_path")
        assert hasattr(log_record, "resolved_path")
        assert hasattr(log_record, "violation_type")

    def test_cross_platform_path_separators(self, tmp_path: Path):
        """Test handling mixed path separators (/ and \\)."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()
        (base_dir / "scripts").mkdir()
        script_file = base_dir / "scripts" / "helper.py"
        script_file.write_text("content")

        # Test - use backslashes (pathlib handles platform-specific normalization)
        resolved = FilePathResolver.resolve_path(base_dir, "scripts\\helper.py")

        # Verify - path should be within base directory
        # On Windows, backslashes are normalized; on POSIX, they're literal characters
        assert resolved.is_relative_to(base_dir)
        # On POSIX, the backslash becomes part of the filename, which is valid
        # The security check still passes because the resolved path is within base_dir

    def test_resolve_with_spaces_in_path(self, tmp_path: Path):
        """Test resolving path with spaces in file/directory names."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()
        (base_dir / "my scripts").mkdir()
        script_file = base_dir / "my scripts" / "helper script.py"
        script_file.write_text("content")

        # Test
        resolved = FilePathResolver.resolve_path(base_dir, "my scripts/helper script.py")

        # Verify
        assert resolved == script_file
        assert resolved.is_relative_to(base_dir)

    def test_resolve_with_unicode_characters(self, tmp_path: Path):
        """Test resolving path with unicode characters."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()
        (base_dir / "ファイル").mkdir()
        file_path = base_dir / "ファイル" / "テスト.txt"
        file_path.write_text("content")

        # Test
        resolved = FilePathResolver.resolve_path(base_dir, "ファイル/テスト.txt")

        # Verify
        assert resolved == file_path
        assert resolved.is_relative_to(base_dir)

    def test_case_sensitivity(self, tmp_path: Path):
        """Test path resolution respects filesystem case sensitivity."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()
        file_path = base_dir / "File.txt"
        file_path.write_text("content")

        # Test - use different case
        resolved = FilePathResolver.resolve_path(base_dir, "file.txt")

        # Verify - on case-insensitive systems, should resolve to same file
        # On case-sensitive systems, paths won't match but security check still passes
        assert resolved.is_relative_to(base_dir)

    def test_permission_error_handling(self, tmp_path: Path):
        """Test handling of permission errors during resolution."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()

        # Create a path that might trigger permission issues
        # Note: This test may skip on systems where we can't restrict permissions
        restricted_dir = base_dir / "restricted"
        restricted_dir.mkdir()

        try:
            # Try to make directory inaccessible
            os.chmod(restricted_dir, 0o000)

            # Test - try to resolve path in restricted directory
            # This may or may not raise an error depending on the system
            try:
                FilePathResolver.resolve_path(base_dir, "restricted/file.txt")
            except (PathSecurityError, PermissionError):
                # Either error is acceptable
                pass
        finally:
            # Restore permissions for cleanup
            os.chmod(restricted_dir, 0o755)


class TestFilePathResolverEdgeCases:
    """Test edge cases and boundary conditions for FilePathResolver."""

    def test_very_long_path(self, tmp_path: Path):
        """Test resolving very long path (near system limits)."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()

        # Create deeply nested directory structure
        current = base_dir
        for i in range(50):  # 50 levels deep
            current = current / f"dir{i}"
            current.mkdir()

        final_file = current / "file.txt"
        final_file.write_text("content")

        # Build relative path
        relative_path = "/".join([f"dir{i}" for i in range(50)] + ["file.txt"])

        # Test
        resolved = FilePathResolver.resolve_path(base_dir, relative_path)

        # Verify
        assert resolved == final_file
        assert resolved.is_relative_to(base_dir)

    def test_special_characters_in_path(self, tmp_path: Path):
        """Test resolving path with special characters."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()

        # Create file with special characters (excluding / and \)
        special_dir = base_dir / "special!@#$%^&()_+-={}[]"
        special_dir.mkdir()
        special_file = special_dir / "file~`';,.txt"
        special_file.write_text("content")

        # Test
        resolved = FilePathResolver.resolve_path(
            base_dir,
            "special!@#$%^&()_+-={}[]/file~`';,.txt"
        )

        # Verify
        assert resolved == special_file
        assert resolved.is_relative_to(base_dir)

    def test_base_directory_as_file(self, tmp_path: Path):
        """Test behavior when base_directory is a file (not directory)."""
        # Setup - create a file instead of directory
        base_file = tmp_path / "skill.txt"
        base_file.write_text("content")

        # Test - resolved path will be sibling to base_file
        # On some systems this will pass (path is still relative to parent dir)
        # On others it may fail. Just verify it doesn't crash.
        try:
            resolved = FilePathResolver.resolve_path(base_file, "file.txt")
            # If it succeeds, verify the path is safe
            assert resolved.is_relative_to(base_file.parent)
        except PathSecurityError:
            # If it fails, that's also acceptable behavior
            pass

    def test_multiple_consecutive_dots(self, tmp_path: Path):
        """Test path with multiple consecutive dots (...)."""
        # Setup
        base_dir = tmp_path / "skill"
        base_dir.mkdir()

        # Test - ... is treated as a literal directory name on POSIX systems
        # It doesn't cause traversal, so it's actually safe
        resolved = FilePathResolver.resolve_path(base_dir, ".../file.txt")

        # Verify - should resolve to base_dir/.../file.txt (doesn't exist, but path is safe)
        assert resolved.is_relative_to(base_dir)
        # The ... would be a directory name, not a traversal pattern
