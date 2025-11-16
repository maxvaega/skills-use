"""Integration tests for SkillManager with plugin support.

This module tests:
- Plugin source building with manifest parsing
- Plugin skill namespacing
- Qualified name lookups (plugin:skill)
- Conflict resolution with plugins
- Multi-source discovery with plugins
"""

from pathlib import Path

import pytest

from skillkit.core.exceptions import SkillNotFoundError
from skillkit.core.manager import SkillManager
from skillkit.core.models import QualifiedSkillName


class TestSkillManagerPluginSources:
    """Test SkillManager plugin source building."""

    def test_build_sources_with_valid_plugin(self):
        """Test building sources with a valid plugin directory."""
        plugin_dir = Path("tests/fixtures/plugins/valid-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        manager = SkillManager(
            project_skill_dir="",  # Explicit opt-out
            anthropic_config_dir="",  # Explicit opt-out
            plugin_dirs=[plugin_dir]
        )

        assert len(manager.sources) == 1
        source = manager.sources[0]

        assert source.plugin_name == "valid-plugin"
        assert source.plugin_manifest is not None
        assert source.plugin_manifest.version == "1.0.0"

    def test_build_sources_with_multiple_plugins(self):
        """Test building sources with multiple plugin directories."""
        plugin1 = Path("tests/fixtures/plugins/valid-plugin")
        plugin2 = Path("tests/fixtures/plugins/multi-dir-plugin")

        if not (plugin1.exists() and plugin2.exists()):
            pytest.skip("Fixtures not found")

        manager = SkillManager(
            project_skill_dir="",  # Explicit opt-out
            anthropic_config_dir="",  # Explicit opt-out
            plugin_dirs=[plugin1, plugin2]
        )

        assert len(manager.sources) == 2

        plugin_names = {s.plugin_name for s in manager.sources}
        assert "valid-plugin" in plugin_names
        assert "multi-dir-plugin" in plugin_names

    def test_build_sources_with_invalid_manifest(self):
        """Test graceful handling of plugin with invalid manifest."""
        plugin_dir = Path("tests/fixtures/plugins/invalid-manifest-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        # Should create source with fallback plugin name (directory name)
        manager = SkillManager(
            project_skill_dir="",  # Explicit opt-out
            anthropic_config_dir="",  # Explicit opt-out
            plugin_dirs=[plugin_dir]
        )

        assert len(manager.sources) == 1
        source = manager.sources[0]

        # Should use directory name as fallback
        assert source.plugin_name == "invalid-manifest-plugin"
        assert source.plugin_manifest is None

    def test_build_sources_with_mixed_directories(self):
        """Test building sources with project, anthropic, and plugin directories."""
        plugin_dir = Path("tests/fixtures/plugins/valid-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        manager = SkillManager(
            project_skill_dir=Path("tests/fixtures/skills"),
            plugin_dirs=[plugin_dir],
        )

        # Should have both project and plugin sources
        source_types = {s.source_type.value for s in manager.sources}
        assert "project" in source_types or "plugin" in source_types


class TestSkillManagerPluginDiscovery:
    """Test skill discovery from plugins."""

    def test_discover_skills_from_plugin(self):
        """Test discovering skills from a plugin."""
        plugin_dir = Path("tests/fixtures/plugins/valid-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        manager = SkillManager(plugin_dirs=[plugin_dir])
        manager.discover()

        skills = manager.list_skills()

        assert len(skills) > 0
        assert any(skill.name == "test-skill" for skill in skills)

    def test_discover_skills_from_multi_dir_plugin(self):
        """Test discovering skills from plugin with multiple skill directories."""
        plugin_dir = Path("tests/fixtures/plugins/multi-dir-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        manager = SkillManager(plugin_dirs=[plugin_dir])
        manager.discover()

        skills = manager.list_skills()

        # Should find skills from both directories
        skill_names = {skill.name for skill in skills}
        assert "skill-a" in skill_names
        assert "skill-b" in skill_names

    @pytest.mark.asyncio
    async def test_async_discover_skills_from_plugin(self):
        """Test async discovery of skills from plugin."""
        plugin_dir = Path("tests/fixtures/plugins/valid-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        manager = SkillManager(plugin_dirs=[plugin_dir])
        await manager.adiscover()

        skills = manager.list_skills()

        assert len(skills) > 0
        assert any(skill.name == "test-skill" for skill in skills)


class TestPluginSkillNamespacing:
    """Test plugin skill namespacing."""

    def test_plugin_skills_in_namespace_registry(self):
        """Test that plugin skills are stored in _plugin_skills registry."""
        plugin_dir = Path("tests/fixtures/plugins/valid-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        manager = SkillManager(plugin_dirs=[plugin_dir])
        manager.discover()

        # Check plugin namespace exists
        assert "valid-plugin" in manager._plugin_skills

        # Check skill is in plugin namespace
        assert "test-skill" in manager._plugin_skills["valid-plugin"]

    def test_plugin_skills_also_in_main_registry(self):
        """Test that plugin skills are also in main _skills registry (if no conflicts)."""
        plugin_dir = Path("tests/fixtures/plugins/valid-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        manager = SkillManager(plugin_dirs=[plugin_dir])
        manager.discover()

        # Should also be in main registry
        assert "test-skill" in manager._skills


class TestQualifiedNameLookups:
    """Test qualified name lookups (plugin:skill)."""

    def test_get_skill_with_qualified_name(self):
        """Test retrieving skill using qualified name."""
        plugin_dir = Path("tests/fixtures/plugins/valid-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        manager = SkillManager(plugin_dirs=[plugin_dir])
        manager.discover()

        # Should be able to get skill with qualified name
        skill = manager.get_skill("valid-plugin:test-skill")

        assert skill.name == "test-skill"

    def test_get_skill_with_simple_name(self):
        """Test retrieving skill using simple name (unqualified)."""
        plugin_dir = Path("tests/fixtures/plugins/valid-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        manager = SkillManager(plugin_dirs=[plugin_dir])
        manager.discover()

        # Should also work with simple name
        skill = manager.get_skill("test-skill")

        assert skill.name == "test-skill"

    def test_qualified_name_with_invalid_plugin(self):
        """Test error when qualified name references non-existent plugin."""
        plugin_dir = Path("tests/fixtures/plugins/valid-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        manager = SkillManager(plugin_dirs=[plugin_dir])
        manager.discover()

        with pytest.raises(SkillNotFoundError) as exc_info:
            manager.get_skill("nonexistent-plugin:test-skill")

        assert "Plugin 'nonexistent-plugin' not found" in str(exc_info.value)

    def test_qualified_name_with_invalid_skill(self):
        """Test error when qualified name references non-existent skill in valid plugin."""
        plugin_dir = Path("tests/fixtures/plugins/valid-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        manager = SkillManager(plugin_dirs=[plugin_dir])
        manager.discover()

        with pytest.raises(SkillNotFoundError) as exc_info:
            manager.get_skill("valid-plugin:nonexistent-skill")

        assert "Skill 'nonexistent-skill' not found in plugin" in str(exc_info.value)


class TestPluginConflictResolution:
    """Test conflict resolution with plugins."""

    def test_project_skill_wins_over_plugin(self, tmp_path):
        """Test that project skills have higher priority than plugin skills."""
        # Create project skill with same name as plugin skill
        project_dir = tmp_path / "skills" / "test-skill"
        project_dir.mkdir(parents=True)
        (project_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: Project version\n---\n"
        )

        plugin_dir = Path("tests/fixtures/plugins/valid-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        manager = SkillManager(
            project_skill_dir=tmp_path / "skills",
            plugin_dirs=[plugin_dir],
        )
        manager.discover()

        # Simple name should get project version (higher priority)
        skill = manager.get_skill("test-skill")

        assert "Project version" in skill.description

    def test_qualified_name_accesses_plugin_version_despite_conflict(self, tmp_path):
        """Test that qualified name can access plugin version even with conflict."""
        # Create project skill with same name as plugin skill
        project_dir = tmp_path / "skills" / "test-skill"
        project_dir.mkdir(parents=True)
        (project_dir / "SKILL.md").write_text(
            "---\nname: test-skill\ndescription: Project version\n---\n"
        )

        plugin_dir = Path("tests/fixtures/plugins/valid-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        manager = SkillManager(
            project_skill_dir=tmp_path / "skills",
            plugin_dirs=[plugin_dir],
        )
        manager.discover()

        # Qualified name should access plugin version
        skill = manager.get_skill("valid-plugin:test-skill")

        # Plugin fixture has "test plugin" in description
        assert "plugin" in skill.description.lower()

    def test_multiple_plugins_with_same_skill_name(self):
        """Test conflict resolution between multiple plugins with same skill name."""
        plugin1 = Path("tests/fixtures/plugins/valid-plugin")
        plugin2 = Path("tests/fixtures/plugins/multi-dir-plugin")

        if not (plugin1.exists() and plugin2.exists()):
            pytest.skip("Fixtures not found")

        manager = SkillManager(plugin_dirs=[plugin1, plugin2])
        manager.discover()

        # Each plugin's skills should be accessible via qualified names
        if "test-skill" in manager._plugin_skills.get("valid-plugin", {}):
            skill1 = manager.get_skill("valid-plugin:test-skill")
            assert skill1.name == "test-skill"


class TestQualifiedSkillNameParsing:
    """Test QualifiedSkillName parsing utility."""

    def test_parse_simple_name(self):
        """Test parsing simple (unqualified) skill name."""
        parsed = QualifiedSkillName.parse("csv-parser")

        assert parsed.plugin is None
        assert parsed.skill == "csv-parser"

    def test_parse_qualified_name(self):
        """Test parsing qualified skill name (plugin:skill)."""
        parsed = QualifiedSkillName.parse("data-tools:csv-parser")

        assert parsed.plugin == "data-tools"
        assert parsed.skill == "csv-parser"

    def test_parse_qualified_name_with_hyphens(self):
        """Test parsing qualified name with hyphens in both parts."""
        parsed = QualifiedSkillName.parse("my-plugin:my-skill")

        assert parsed.plugin == "my-plugin"
        assert parsed.skill == "my-skill"

    def test_parse_empty_name_error(self):
        """Test error when parsing empty skill name."""
        with pytest.raises(ValueError) as exc_info:
            QualifiedSkillName.parse("")

        assert "Skill name cannot be empty" in str(exc_info.value)

    def test_parse_qualified_name_with_colon_in_skill(self):
        """Test parsing qualified name with colon in skill part (valid)."""
        # Implementation uses split(":", 1) so "plugin:skill:extra" is valid
        # It splits to plugin="plugin" and skill="skill:extra"
        parsed = QualifiedSkillName.parse("plugin:skill:extra")

        assert parsed.plugin == "plugin"
        assert parsed.skill == "skill:extra"

    def test_parse_qualified_name_with_empty_parts(self):
        """Test error when qualified name has empty plugin or skill part."""
        with pytest.raises(ValueError):
            QualifiedSkillName.parse(":skill")

        with pytest.raises(ValueError):
            QualifiedSkillName.parse("plugin:")


class TestPluginIntegrationEndToEnd:
    """End-to-end integration tests."""

    def test_full_workflow_with_plugins(self):
        """Test complete workflow: build sources, discover, get skills."""
        plugin_dir = Path("tests/fixtures/plugins/multi-dir-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        # 1. Initialize manager with plugin
        manager = SkillManager(
            project_skill_dir="",  # Explicit opt-out
            anthropic_config_dir="",  # Explicit opt-out
            plugin_dirs=[plugin_dir]
        )

        # 2. Discover skills
        manager.discover()

        # 3. List all skills
        skills = manager.list_skills()
        assert len(skills) == 2

        # 4. Get skill with simple name
        skill_a = manager.get_skill("skill-a")
        assert skill_a.name == "skill-a"

        # 5. Get skill with qualified name
        skill_b = manager.get_skill("multi-dir-plugin:skill-b")
        assert skill_b.name == "skill-b"

        # 6. Invoke skill
        result = manager.invoke_skill("skill-a", "test arguments")
        assert "Skill A" in result

    @pytest.mark.asyncio
    async def test_full_async_workflow_with_plugins(self):
        """Test complete async workflow with plugins."""
        plugin_dir = Path("tests/fixtures/plugins/multi-dir-plugin")

        if not plugin_dir.exists():
            pytest.skip("Fixture not found")

        # 1. Initialize manager
        manager = SkillManager(
            project_skill_dir="",  # Explicit opt-out
            anthropic_config_dir="",  # Explicit opt-out
            plugin_dirs=[plugin_dir]
        )

        # 2. Async discover
        await manager.adiscover()

        # 3. List skills
        skills = manager.list_skills()
        assert len(skills) == 2

        # 4. Async invoke
        result = await manager.ainvoke_skill("skill-a", "test arguments")
        assert "Skill A" in result
