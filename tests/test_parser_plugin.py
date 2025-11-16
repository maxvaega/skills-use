"""Tests for plugin manifest parsing functionality.

This module tests the parse_plugin_manifest() function including:
- Valid manifest parsing
- Missing required fields
- Invalid JSON
- JSON bomb protection
- Security validations (path traversal)
"""

import json
from pathlib import Path

import pytest

from skillkit.core.exceptions import (
    ManifestNotFoundError,
    ManifestParseError,
    ManifestValidationError,
)
from skillkit.core.parser import MAX_MANIFEST_SIZE, parse_plugin_manifest


class TestParsePluginManifestValid:
    """Test successful parsing of valid plugin manifests."""

    def test_parse_valid_manifest(self, tmp_path):
        """Test parsing a complete valid manifest."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        manifest_data = {
            "manifest_version": "0.1",
            "name": "test-plugin",
            "version": "1.0.0",
            "description": "A test plugin",
            "author": {"name": "Test Author", "email": "test@example.com"},
            "skills": ["skills/"],
        }

        manifest_path.write_text(json.dumps(manifest_data))

        result = parse_plugin_manifest(manifest_path)

        assert result.name == "test-plugin"
        assert result.version == "1.0.0"
        assert result.description == "A test plugin"
        assert result.author == {"name": "Test Author", "email": "test@example.com"}
        assert result.skills == ["skills/"]
        assert result.manifest_version == "0.1"

    def test_parse_manifest_with_optional_fields(self, tmp_path):
        """Test parsing manifest with all optional fields."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        manifest_data = {
            "manifest_version": "0.3",
            "name": "full-plugin",
            "version": "2.0.0",
            "description": "Full featured plugin",
            "author": "Simple Author",
            "skills": ["skills/", "experimental/"],
            "display_name": "Full Plugin",
            "homepage": "https://example.com",
            "repository": {"type": "git", "url": "https://github.com/test/repo"},
        }

        manifest_path.write_text(json.dumps(manifest_data))

        result = parse_plugin_manifest(manifest_path)

        assert result.display_name == "Full Plugin"
        assert result.homepage == "https://example.com"
        assert result.repository == {"type": "git", "url": "https://github.com/test/repo"}
        assert result.skills == ["skills/", "experimental/"]

    def test_parse_manifest_string_author(self, tmp_path):
        """Test parsing manifest with author as string (converted to dict)."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        manifest_data = {
            "manifest_version": "0.1",
            "name": "string-author",
            "version": "1.0.0",
            "description": "Plugin with string author",
            "author": "John Doe",
        }

        manifest_path.write_text(json.dumps(manifest_data))

        result = parse_plugin_manifest(manifest_path)

        assert result.author == {"name": "John Doe"}

    def test_parse_manifest_string_skills(self, tmp_path):
        """Test parsing manifest with skills as single string (normalized to list)."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        manifest_data = {
            "manifest_version": "0.1",
            "name": "single-skill-dir",
            "version": "1.0.0",
            "description": "Plugin with single skill dir",
            "author": "Test",
            "skills": "skills/",
        }

        manifest_path.write_text(json.dumps(manifest_data))

        result = parse_plugin_manifest(manifest_path)

        assert result.skills == ["skills/"]

    def test_parse_manifest_default_skills(self, tmp_path):
        """Test parsing manifest without skills field (defaults to ['skills/'])."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        manifest_data = {
            "manifest_version": "0.1",
            "name": "default-skills",
            "version": "1.0.0",
            "description": "Plugin with default skills",
            "author": "Test",
        }

        manifest_path.write_text(json.dumps(manifest_data))

        result = parse_plugin_manifest(manifest_path)

        assert result.skills == ["skills/"]


class TestParsePluginManifestErrors:
    """Test error handling for invalid manifests."""

    def test_manifest_not_found(self, tmp_path):
        """Test error when manifest file doesn't exist."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"

        with pytest.raises(ManifestNotFoundError) as exc_info:
            parse_plugin_manifest(manifest_path)

        assert "Plugin manifest not found" in str(exc_info.value)
        assert str(manifest_path) in str(exc_info.value)

    def test_manifest_too_large(self, tmp_path):
        """Test JSON bomb protection (file size limit)."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        # Create a file larger than MAX_MANIFEST_SIZE
        large_content = "x" * (MAX_MANIFEST_SIZE + 1)
        manifest_path.write_text(large_content)

        with pytest.raises(ManifestParseError) as exc_info:
            parse_plugin_manifest(manifest_path)

        assert "Manifest too large" in str(exc_info.value)
        # The error message formats the size with commas, e.g., "1,000,000"
        assert "max" in str(exc_info.value).lower()

    def test_invalid_json(self, tmp_path):
        """Test error handling for malformed JSON."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        manifest_path.write_text('{"name": "test", "version": ')

        with pytest.raises(ManifestParseError) as exc_info:
            parse_plugin_manifest(manifest_path)

        assert "Invalid JSON" in str(exc_info.value)

    def test_manifest_not_dict(self, tmp_path):
        """Test error when manifest is not a JSON object."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        manifest_path.write_text('["array", "instead", "of", "object"]')

        with pytest.raises(ManifestValidationError) as exc_info:
            parse_plugin_manifest(manifest_path)

        assert "Manifest must be a JSON object" in str(exc_info.value)

    def test_missing_required_fields(self, tmp_path):
        """Test error when required fields are missing."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        manifest_data = {
            "manifest_version": "0.1",
            "name": "incomplete-plugin",
        }

        manifest_path.write_text(json.dumps(manifest_data))

        with pytest.raises(ManifestValidationError) as exc_info:
            parse_plugin_manifest(manifest_path)

        assert "Missing required fields" in str(exc_info.value)
        assert "version" in str(exc_info.value)
        assert "description" in str(exc_info.value)

    def test_invalid_author_type(self, tmp_path):
        """Test error when author is invalid type."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        manifest_data = {
            "manifest_version": "0.1",
            "name": "bad-author",
            "version": "1.0.0",
            "description": "Plugin with invalid author",
            "author": 123,
        }

        manifest_path.write_text(json.dumps(manifest_data))

        with pytest.raises(ManifestValidationError) as exc_info:
            parse_plugin_manifest(manifest_path)

        assert "'author' must be string or object" in str(exc_info.value)

    def test_invalid_skills_type(self, tmp_path):
        """Test error when skills field has invalid type."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        manifest_data = {
            "manifest_version": "0.1",
            "name": "bad-skills",
            "version": "1.0.0",
            "description": "Plugin with invalid skills",
            "author": "Test",
            "skills": 123,
        }

        manifest_path.write_text(json.dumps(manifest_data))

        with pytest.raises(ManifestValidationError) as exc_info:
            parse_plugin_manifest(manifest_path)

        assert "'skills' must be string or array" in str(exc_info.value)


class TestPluginManifestSecurity:
    """Test security validations in PluginManifest.__post_init__."""

    def test_unsupported_manifest_version(self, tmp_path):
        """Test error for unsupported manifest version."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        manifest_data = {
            "manifest_version": "99.0",
            "name": "future-plugin",
            "version": "1.0.0",
            "description": "Plugin from the future",
            "author": "Test",
        }

        manifest_path.write_text(json.dumps(manifest_data))

        with pytest.raises(ManifestValidationError) as exc_info:
            parse_plugin_manifest(manifest_path)

        assert "Unsupported manifest_version" in str(exc_info.value)
        assert "99.0" in str(exc_info.value)

    def test_name_with_spaces(self, tmp_path):
        """Test error for plugin name with spaces."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        manifest_data = {
            "manifest_version": "0.1",
            "name": "invalid name",
            "version": "1.0.0",
            "description": "Plugin with spaces in name",
            "author": "Test",
        }

        manifest_path.write_text(json.dumps(manifest_data))

        with pytest.raises(ManifestValidationError) as exc_info:
            parse_plugin_manifest(manifest_path)

        assert "Plugin name cannot" in str(exc_info.value)

    def test_invalid_version_format(self, tmp_path):
        """Test error for invalid semver version."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        manifest_data = {
            "manifest_version": "0.1",
            "name": "bad-version",
            "version": "1.0",
            "description": "Plugin with invalid version",
            "author": "Test",
        }

        manifest_path.write_text(json.dumps(manifest_data))

        with pytest.raises(ManifestValidationError) as exc_info:
            parse_plugin_manifest(manifest_path)

        assert "Version must be semver" in str(exc_info.value)

    def test_path_traversal_in_skills(self, tmp_path):
        """Test security check for path traversal in skills field."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        manifest_data = {
            "manifest_version": "0.1",
            "name": "security-test",
            "version": "1.0.0",
            "description": "Plugin with path traversal",
            "author": "Test",
            "skills": ["../../etc/passwd"],
        }

        manifest_path.write_text(json.dumps(manifest_data))

        with pytest.raises(ManifestValidationError) as exc_info:
            parse_plugin_manifest(manifest_path)

        assert "Security violation" in str(exc_info.value)
        assert ".." in str(exc_info.value)

    def test_absolute_path_in_skills(self, tmp_path):
        """Test security check for absolute paths in skills field."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        manifest_data = {
            "manifest_version": "0.1",
            "name": "security-test",
            "version": "1.0.0",
            "description": "Plugin with absolute path",
            "author": "Test",
            "skills": ["/etc/passwd"],
        }

        manifest_path.write_text(json.dumps(manifest_data))

        with pytest.raises(ManifestValidationError) as exc_info:
            parse_plugin_manifest(manifest_path)

        assert "Security violation" in str(exc_info.value)
        assert "must be relative" in str(exc_info.value)

    def test_drive_letter_in_skills(self, tmp_path):
        """Test security check for Windows drive letters in skills field."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        manifest_data = {
            "manifest_version": "0.1",
            "name": "security-test",
            "version": "1.0.0",
            "description": "Plugin with drive letter",
            "author": "Test",
            "skills": ["C:/Windows"],
        }

        manifest_path.write_text(json.dumps(manifest_data))

        with pytest.raises(ManifestValidationError) as exc_info:
            parse_plugin_manifest(manifest_path)

        assert "Security violation" in str(exc_info.value)
        assert "Drive letters not allowed" in str(exc_info.value)


class TestPluginManifestIntegration:
    """Integration tests using real fixture files."""

    def test_parse_valid_plugin_fixture(self):
        """Test parsing the valid-plugin fixture."""
        fixture_path = Path("tests/fixtures/plugins/valid-plugin/.claude-plugin/plugin.json")

        if not fixture_path.exists():
            pytest.skip("Fixture not found")

        result = parse_plugin_manifest(fixture_path)

        assert result.name == "valid-plugin"
        assert result.version == "1.0.0"
        assert result.manifest_version == "0.1"

    def test_parse_multi_dir_plugin_fixture(self):
        """Test parsing the multi-dir-plugin fixture."""
        fixture_path = Path("tests/fixtures/plugins/multi-dir-plugin/.claude-plugin/plugin.json")

        if not fixture_path.exists():
            pytest.skip("Fixture not found")

        result = parse_plugin_manifest(fixture_path)

        assert result.name == "multi-dir-plugin"
        assert result.skills == ["skills/", "experimental/"]

    def test_parse_invalid_manifest_fixture(self):
        """Test parsing invalid-manifest-plugin fixture (missing fields)."""
        fixture_path = Path(
            "tests/fixtures/plugins/invalid-manifest-plugin/.claude-plugin/plugin.json"
        )

        if not fixture_path.exists():
            pytest.skip("Fixture not found")

        with pytest.raises(ManifestValidationError):
            parse_plugin_manifest(fixture_path)

    def test_parse_malformed_json_fixture(self):
        """Test parsing malformed-json-plugin fixture."""
        fixture_path = Path(
            "tests/fixtures/plugins/malformed-json-plugin/.claude-plugin/plugin.json"
        )

        if not fixture_path.exists():
            pytest.skip("Fixture not found")

        with pytest.raises(ManifestParseError):
            parse_plugin_manifest(fixture_path)

    def test_parse_path_traversal_fixture(self):
        """Test parsing path-traversal-plugin fixture (security violation)."""
        fixture_path = Path(
            "tests/fixtures/plugins/path-traversal-plugin/.claude-plugin/plugin.json"
        )

        if not fixture_path.exists():
            pytest.skip("Fixture not found")

        with pytest.raises(ManifestValidationError) as exc_info:
            parse_plugin_manifest(fixture_path)

        assert "Security violation" in str(exc_info.value)
