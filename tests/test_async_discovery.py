"""Tests for async skill discovery (Phase 3 - User Story 1).

Tests for v0.2 async discovery functionality including:
- Async file I/O wrappers
- Async discovery methods
- State management (sync/async separation)
- AsyncStateError validation
"""

import asyncio
from pathlib import Path

import pytest

from skillkit import SkillManager
from skillkit.core.discovery import SkillDiscovery
from skillkit.core.exceptions import AsyncStateError
from skillkit.core.models import InitMode


class TestAsyncFileIO:
    """Test async file I/O wrappers."""

    @pytest.mark.asyncio
    async def test_read_skill_file_async(self, fixtures_dir):
        """Test async file reading wrapper."""
        discovery = SkillDiscovery()
        skill_file = fixtures_dir / "skills" / "valid-skill" / "SKILL.md"

        # Read file asynchronously
        content = await discovery._read_skill_file_async(skill_file)

        # Verify content was read
        assert content is not None
        assert len(content) > 0
        assert "---" in content  # Should have YAML frontmatter

    @pytest.mark.asyncio
    async def test_read_skill_file_async_nonexistent(self):
        """Test async file reading with non-existent file."""
        discovery = SkillDiscovery()
        nonexistent_file = Path("/tmp/nonexistent-file-12345.md")

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError):
            await discovery._read_skill_file_async(nonexistent_file)


class TestAsyncDiscovery:
    """Test async discovery methods."""

    @pytest.mark.asyncio
    async def test_ascan_directory_basic(self, fixtures_dir):
        """Test basic async directory scanning."""
        discovery = SkillDiscovery()
        skills_dir = fixtures_dir / "skills"

        # Scan directory asynchronously
        skill_files = await discovery.ascan_directory(skills_dir)

        # Verify skills were found
        assert len(skill_files) > 0
        assert all(f.name.upper() == "SKILL.MD" for f in skill_files)
        assert all(f.exists() for f in skill_files)

    @pytest.mark.asyncio
    async def test_ascan_directory_nonexistent(self):
        """Test async scanning of non-existent directory."""
        discovery = SkillDiscovery()
        nonexistent_dir = Path("/tmp/nonexistent-dir-12345")

        # Should return empty list
        skill_files = await discovery.ascan_directory(nonexistent_dir)
        assert skill_files == []

    @pytest.mark.asyncio
    async def test_afind_skill_files(self, fixtures_dir):
        """Test async skill file finding."""
        discovery = SkillDiscovery()
        skills_dir = fixtures_dir / "skills"

        # Find skill files asynchronously
        skill_files = await discovery.afind_skill_files(skills_dir)

        # Verify results match sync version
        sync_files = discovery.find_skill_files(skills_dir)
        assert len(skill_files) == len(sync_files)
        assert set(skill_files) == set(sync_files)

    @pytest.mark.asyncio
    async def test_async_discovery_performance(self, fixtures_dir):
        """Test that async discovery doesn't block event loop."""
        import time

        discovery = SkillDiscovery()
        skills_dir = fixtures_dir / "skills"

        # Measure async discovery time
        start = time.time()
        skill_files = await discovery.ascan_directory(skills_dir)
        elapsed = time.time() - start

        # Should complete quickly (< 100ms for small test set)
        assert elapsed < 0.1
        assert len(skill_files) > 0


class TestSkillManagerAsync:
    """Test SkillManager async discovery."""

    @pytest.mark.asyncio
    async def test_adiscover_basic(self, fixtures_dir):
        """Test basic async discovery."""
        manager = SkillManager(project_skill_dir=fixtures_dir / "skills")

        # Manager should start uninitialized
        assert manager.init_mode == InitMode.UNINITIALIZED

        # Discover skills asynchronously
        await manager.adiscover()

        # Verify initialization mode is ASYNC
        assert manager.init_mode == InitMode.ASYNC

        # Verify skills were discovered
        skills = manager.list_skills()
        assert len(skills) > 0

        # Verify we can get specific skills
        skill_names = [s.name for s in skills]
        # Should find at least one of the valid skills
        assert any(name in skill_names for name in ["valid-basic", "code-reviewer", "arguments-test"])

    @pytest.mark.asyncio
    async def test_adiscover_empty_directory(self, tmp_path):
        """Test async discovery with empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        manager = SkillManager(
            project_skill_dir=empty_dir,
            anthropic_config_dir="",  # Explicit opt-out
            plugin_dirs=[],
        )
        await manager.adiscover()

        # Should complete without errors
        assert manager.init_mode == InitMode.ASYNC
        assert len(manager.list_skills()) == 0

    @pytest.mark.asyncio
    async def test_adiscover_multiple_skills(self, fixtures_dir):
        """Test async discovery finds all valid skills."""
        manager = SkillManager(project_skill_dir=fixtures_dir / "skills")
        await manager.adiscover()

        skills = manager.list_skills()
        skill_names = [s.name for s in skills]

        # Should find multiple valid skills
        assert len(skill_names) >= 3
        assert "valid-basic" in skill_names
        assert "valid-with-arguments" in skill_names

    @pytest.mark.asyncio
    async def test_async_vs_sync_discovery_equivalence(self, fixtures_dir):
        """Test that async and sync discovery produce identical results."""
        # Sync discovery
        manager_sync = SkillManager(project_skill_dir=fixtures_dir / "skills")
        manager_sync.discover()
        sync_skills = sorted([s.name for s in manager_sync.list_skills()])

        # Async discovery
        manager_async = SkillManager(project_skill_dir=fixtures_dir / "skills")
        await manager_async.adiscover()
        async_skills = sorted([s.name for s in manager_async.list_skills()])

        # Results should be identical
        assert sync_skills == async_skills


class TestAsyncStateManagement:
    """Test async/sync state management."""

    def test_sync_then_async_raises_error(self, fixtures_dir):
        """Test that calling adiscover() after discover() raises AsyncStateError."""
        manager = SkillManager(project_skill_dir=fixtures_dir / "skills")

        # Initialize with sync discovery
        manager.discover()
        assert manager.init_mode == InitMode.SYNC

        # Attempting async discovery should raise error
        with pytest.raises(AsyncStateError) as exc_info:
            asyncio.run(manager.adiscover())

        assert "sync mode" in str(exc_info.value).lower()
        assert "async" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_async_then_sync_raises_error(self, fixtures_dir):
        """Test that calling discover() after adiscover() raises AsyncStateError."""
        manager = SkillManager(project_skill_dir=fixtures_dir / "skills")

        # Initialize with async discovery
        await manager.adiscover()
        assert manager.init_mode == InitMode.ASYNC

        # Attempting sync discovery should raise error
        with pytest.raises(AsyncStateError) as exc_info:
            manager.discover()

        assert "async mode" in str(exc_info.value).lower()
        assert "sync" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_multiple_async_calls_allowed(self, fixtures_dir):
        """Test that multiple adiscover() calls are allowed."""
        manager = SkillManager(project_skill_dir=fixtures_dir / "skills")

        # First async discovery
        await manager.adiscover()
        first_count = len(manager.list_skills())

        # Second async discovery (should work)
        await manager.adiscover()
        second_count = len(manager.list_skills())

        # Should have same results
        assert first_count == second_count
        assert manager.init_mode == InitMode.ASYNC

    def test_multiple_sync_calls_allowed(self, fixtures_dir):
        """Test that multiple discover() calls are allowed."""
        manager = SkillManager(project_skill_dir=fixtures_dir / "skills")

        # First sync discovery
        manager.discover()
        first_count = len(manager.list_skills())

        # Second sync discovery (should work)
        manager.discover()
        second_count = len(manager.list_skills())

        # Should have same results
        assert first_count == second_count
        assert manager.init_mode == InitMode.SYNC

    @pytest.mark.asyncio
    async def test_fresh_manager_can_use_either_mode(self, fixtures_dir):
        """Test that a fresh manager can use either sync or async."""
        # Fresh manager for async
        manager_async = SkillManager(project_skill_dir=fixtures_dir / "skills")
        assert manager_async.init_mode == InitMode.UNINITIALIZED
        await manager_async.adiscover()
        assert manager_async.init_mode == InitMode.ASYNC

        # Fresh manager for sync
        manager_sync = SkillManager(project_skill_dir=fixtures_dir / "skills")
        assert manager_sync.init_mode == InitMode.UNINITIALIZED
        manager_sync.discover()
        assert manager_sync.init_mode == InitMode.SYNC


class TestAsyncConcurrency:
    """Test async concurrency behavior."""

    @pytest.mark.asyncio
    async def test_concurrent_async_discovery_different_managers(self, fixtures_dir):
        """Test that multiple managers can discover concurrently."""
        # Create multiple managers
        managers = [
            SkillManager(project_skill_dir=fixtures_dir / "skills")
            for _ in range(5)
        ]

        # Discover concurrently
        await asyncio.gather(*[m.adiscover() for m in managers])

        # All should have discovered skills
        for manager in managers:
            assert manager.init_mode == InitMode.ASYNC
            assert len(manager.list_skills()) > 0

    @pytest.mark.asyncio
    async def test_event_loop_remains_responsive(self, fixtures_dir):
        """Test that event loop remains responsive during async discovery."""
        manager = SkillManager(project_skill_dir=fixtures_dir / "skills")
        counter = {"value": 0}

        async def increment_counter():
            """Increment counter in background."""
            for _ in range(100):
                counter["value"] += 1
                await asyncio.sleep(0.001)  # Small delay

        # Run discovery and counter concurrently
        await asyncio.gather(
            manager.adiscover(),
            increment_counter()
        )

        # Both should complete
        assert manager.init_mode == InitMode.ASYNC
        assert len(manager.list_skills()) > 0
        assert counter["value"] == 100  # Counter should have completed


# Fixtures
@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory."""
    return Path(__file__).parent / "fixtures"


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
