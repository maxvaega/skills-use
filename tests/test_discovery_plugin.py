"""Tests for plugin discovery functionality.

This module tests:
- discover_plugin_manifest() function
- Multi-directory skill discovery from plugin manifests
- Graceful error handling for malformed manifests
"""

from pathlib import Path

import pytest

from skillkit.core.discovery import SkillDiscovery, discover_plugin_manifest
from skillkit.core.models import SkillSource, SourceType


class TestDiscoverPluginManifest:
    """Test discover_plugin_manifest() function."""

    def test_discover_valid_manifest(self):
        """Test discovering a valid plugin manifest."""
        plugin_dir = Path("tests/fixtures/plugins/valid-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        result = discover_plugin_manifest(plugin_dir)

        assert result is not None
        assert result.name == "valid-plugin"
        assert result.version == "1.0.0"
        assert result.skills == ["skills/"]

    def test_discover_multi_dir_manifest(self):
        """Test discovering plugin with multiple skill directories."""
        plugin_dir = Path("tests/fixtures/plugins/multi-dir-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        result = discover_plugin_manifest(plugin_dir)

        assert result is not None
        assert result.name == "multi-dir-plugin"
        assert result.skills == ["skills/", "experimental/"]

    def test_discover_missing_manifest(self):
        """Test graceful handling when manifest doesn't exist."""
        plugin_dir = Path("tests/fixtures/plugins/missing-manifest-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        result = discover_plugin_manifest(plugin_dir)

        assert result is None

    def test_discover_invalid_manifest(self):
        """Test graceful handling of invalid manifest (missing required fields)."""
        plugin_dir = Path("tests/fixtures/plugins/invalid-manifest-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        result = discover_plugin_manifest(plugin_dir)

        # Should return None and log warning (graceful degradation)
        assert result is None

    def test_discover_malformed_json(self):
        """Test graceful handling of malformed JSON."""
        plugin_dir = Path("tests/fixtures/plugins/malformed-json-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        result = discover_plugin_manifest(plugin_dir)

        # Should return None and log warning (graceful degradation)
        assert result is None

    def test_discover_path_traversal_manifest(self):
        """Test graceful handling of security violations."""
        plugin_dir = Path("tests/fixtures/plugins/path-traversal-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        result = discover_plugin_manifest(plugin_dir)

        # Should return None and log warning (security violation)
        assert result is None

    def test_discover_nonexistent_directory(self, tmp_path):
        """Test handling of non-existent plugin directory."""
        plugin_dir = tmp_path / "nonexistent"

        result = discover_plugin_manifest(plugin_dir)

        assert result is None


class TestSkillDiscoveryWithPlugins:
    """Test SkillDiscovery with plugin sources."""

    def test_discover_skills_from_plugin_single_dir(self):
        """Test discovering skills from plugin with single skill directory."""
        plugin_dir = Path("tests/fixtures/plugins/valid-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        manifest = discover_plugin_manifest(plugin_dir)
        assert manifest is not None

        source = SkillSource(
            source_type=SourceType.PLUGIN,
            directory=plugin_dir,
            priority=10,
            plugin_name=manifest.name,
            plugin_manifest=manifest,
        )

        discovery = SkillDiscovery()
        skill_files = discovery.discover_skills(source)

        assert len(skill_files) == 1
        assert skill_files[0].name == "SKILL.md"
        assert "test-skill" in str(skill_files[0])

    def test_discover_skills_from_plugin_multiple_dirs(self):
        """Test discovering skills from plugin with multiple skill directories."""
        plugin_dir = Path("tests/fixtures/plugins/multi-dir-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        manifest = discover_plugin_manifest(plugin_dir)
        assert manifest is not None
        assert len(manifest.skills) == 2

        source = SkillSource(
            source_type=SourceType.PLUGIN,
            directory=plugin_dir,
            priority=10,
            plugin_name=manifest.name,
            plugin_manifest=manifest,
        )

        discovery = SkillDiscovery()
        skill_files = discovery.discover_skills(source)

        # Should find skills from both directories
        assert len(skill_files) == 2

        skill_names = [str(f) for f in skill_files]
        assert any("skill-a" in name for name in skill_names)
        assert any("skill-b" in name for name in skill_names)

    def test_discover_skills_from_plugin_without_manifest(self):
        """Test discovering skills from plugin source without manifest."""
        plugin_dir = Path("tests/fixtures/plugins/missing-manifest-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        # Source without manifest should scan directory directly
        source = SkillSource(
            source_type=SourceType.PLUGIN,
            directory=plugin_dir,
            priority=10,
            plugin_name="fallback-name",
            plugin_manifest=None,
        )

        discovery = SkillDiscovery()
        skill_files = discovery.discover_skills(source)

        # Should fall back to scanning directory directly
        assert isinstance(skill_files, list)

    def test_discover_skills_from_non_plugin_source(self, tmp_path):
        """Test that non-plugin sources don't use manifest logic."""
        # Create a simple skill directory
        skill_dir = tmp_path / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: test\ndescription: Test\n---\n")

        source = SkillSource(
            source_type=SourceType.PROJECT,
            directory=tmp_path / "skills",
            priority=100,
        )

        discovery = SkillDiscovery()
        skill_files = discovery.discover_skills(source)

        assert len(skill_files) == 1
        assert skill_files[0].name == "SKILL.md"


class TestAsyncPluginDiscovery:
    """Test async plugin discovery."""

    @pytest.mark.asyncio
    async def test_adiscover_skills_from_plugin_single_dir(self):
        """Test async discovery of skills from plugin with single directory."""
        plugin_dir = Path("tests/fixtures/plugins/valid-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        manifest = discover_plugin_manifest(plugin_dir)
        assert manifest is not None

        source = SkillSource(
            source_type=SourceType.PLUGIN,
            directory=plugin_dir,
            priority=10,
            plugin_name=manifest.name,
            plugin_manifest=manifest,
        )

        discovery = SkillDiscovery()
        skill_files = await discovery.adiscover_skills(source)

        assert len(skill_files) == 1
        assert skill_files[0].name == "SKILL.md"

    @pytest.mark.asyncio
    async def test_adiscover_skills_from_plugin_multiple_dirs(self):
        """Test async discovery from plugin with multiple skill directories."""
        plugin_dir = Path("tests/fixtures/plugins/multi-dir-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        manifest = discover_plugin_manifest(plugin_dir)
        assert manifest is not None

        source = SkillSource(
            source_type=SourceType.PLUGIN,
            directory=plugin_dir,
            priority=10,
            plugin_name=manifest.name,
            plugin_manifest=manifest,
        )

        discovery = SkillDiscovery()
        skill_files = await discovery.adiscover_skills(source)

        # Should find skills from both directories
        assert len(skill_files) == 2

        skill_names = [str(f) for f in skill_files]
        assert any("skill-a" in name for name in skill_names)
        assert any("skill-b" in name for name in skill_names)


class TestPluginDiscoveryEdgeCases:
    """Test edge cases in plugin discovery."""

    def test_plugin_with_empty_skills_list(self, tmp_path):
        """Test plugin manifest with empty skills list."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        import json

        manifest_data = {
            "manifest_version": "0.1",
            "name": "empty-skills",
            "version": "1.0.0",
            "description": "Plugin with no skills",
            "author": "Test",
            "skills": [],
        }

        manifest_path.write_text(json.dumps(manifest_data))

        result = discover_plugin_manifest(tmp_path)

        assert result is not None
        assert result.skills == []

        # Discovery should return empty list
        source = SkillSource(
            source_type=SourceType.PLUGIN,
            directory=tmp_path,
            priority=10,
            plugin_name=result.name,
            plugin_manifest=result,
        )

        discovery = SkillDiscovery()
        skill_files = discovery.discover_skills(source)

        assert skill_files == []

    def test_plugin_with_nonexistent_skill_dir(self, tmp_path):
        """Test plugin manifest pointing to non-existent skill directory."""
        manifest_path = tmp_path / ".claude-plugin" / "plugin.json"
        manifest_path.parent.mkdir(parents=True)

        import json

        manifest_data = {
            "manifest_version": "0.1",
            "name": "missing-dir",
            "version": "1.0.0",
            "description": "Plugin with missing skill dir",
            "author": "Test",
            "skills": ["nonexistent/"],
        }

        manifest_path.write_text(json.dumps(manifest_data))

        result = discover_plugin_manifest(tmp_path)

        assert result is not None

        source = SkillSource(
            source_type=SourceType.PLUGIN,
            directory=tmp_path,
            priority=10,
            plugin_name=result.name,
            plugin_manifest=result,
        )

        discovery = SkillDiscovery()
        skill_files = discovery.discover_skills(source)

        # Should handle gracefully (return empty list)
        assert skill_files == []
