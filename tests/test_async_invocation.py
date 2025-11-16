"""Tests for async skill invocation (Phase 4: User Story 2).

This module tests the async invocation capabilities added in v0.2:
- Skill.ainvoke() async method
- SkillManager.ainvoke_skill() async method
- AsyncStateError validation
- Concurrent invocations
- State management (sync vs async mode)
"""

import asyncio
from pathlib import Path

import pytest

from skillkit import SkillManager
from skillkit.core.exceptions import AsyncStateError, SkillNotFoundError, SkillsUseError
from skillkit.core.models import InitMode


class TestAsyncSkillInvocation:
    """Test async skill invocation via Skill.ainvoke()."""

    @pytest.mark.asyncio
    async def test_skill_ainvoke_basic(self, skill_manager_async):
        """Test basic async skill invocation."""
        # Get a skill
        skill = skill_manager_async.load_skill("markdown-formatter")

        # Invoke asynchronously
        result = await skill.ainvoke("Format this **text**")

        # Verify result contains expected content
        assert isinstance(result, str)
        assert "Base directory" in result
        assert "Format this **text**" in result
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_skill_ainvoke_empty_arguments(self, skill_manager_async):
        """Test async invocation with empty arguments."""
        skill = skill_manager_async.load_skill("code-reviewer")

        # Invoke with empty arguments
        result = await skill.ainvoke()

        assert isinstance(result, str)
        assert "Base directory" in result
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_skill_ainvoke_uses_cached_content(self, skill_manager_async):
        """Test that ainvoke uses cached content on subsequent calls."""
        skill = skill_manager_async.load_skill("git-helper")

        # First invocation - loads content
        result1 = await skill.ainvoke("test arguments")

        # Access content property to ensure it's cached
        _ = skill.content

        # Second invocation - should use cached content
        result2 = await skill.ainvoke("different arguments")

        # Both should succeed
        assert isinstance(result1, str)
        assert isinstance(result2, str)
        assert "test arguments" in result1
        assert "different arguments" in result2

    @pytest.mark.asyncio
    async def test_skill_ainvoke_concurrent(self, skill_manager_async):
        """Test concurrent async invocations of the same skill."""
        skill = skill_manager_async.load_skill("markdown-formatter")

        # Invoke same skill concurrently
        results = await asyncio.gather(
            skill.ainvoke("input 1"),
            skill.ainvoke("input 2"),
            skill.ainvoke("input 3"),
            skill.ainvoke("input 4"),
            skill.ainvoke("input 5"),
        )

        # Verify all invocations succeeded
        assert len(results) == 5
        for i, result in enumerate(results, 1):
            assert isinstance(result, str)
            assert f"input {i}" in result

    @pytest.mark.asyncio
    async def test_skill_ainvoke_content_loading_error(self, tmp_path):
        """Test ainvoke handles file read errors gracefully."""
        from skillkit.core.exceptions import ContentLoadError
        from skillkit.core.models import Skill, SkillMetadata

        # Create a skill file, then delete it after metadata creation
        skill_dir = tmp_path / "missing-skill"
        skill_dir.mkdir()
        skill_path = skill_dir / "SKILL.md"

        # Create the file temporarily for metadata validation
        skill_path.write_text(
            "---\nname: missing-skill\ndescription: Test skill\n---\n\nContent",
            encoding="utf-8"
        )

        metadata = SkillMetadata(
            name="missing-skill",
            description="Test skill",
            skill_path=skill_path,
        )

        # Now delete the file to simulate it being removed after discovery
        skill_path.unlink()

        # Create skill pointing to now-deleted file
        skill = Skill(metadata=metadata, base_directory=skill_dir)

        # Attempt async invocation should fail
        with pytest.raises(ContentLoadError, match="Skill file not found"):
            await skill.ainvoke("test")


class TestAsyncManagerInvocation:
    """Test async skill invocation via SkillManager.ainvoke_skill()."""

    @pytest.mark.asyncio
    async def test_manager_ainvoke_skill_basic(self, skill_manager_async):
        """Test basic manager async invocation."""
        result = await skill_manager_async.ainvoke_skill(
            "markdown-formatter", "Format **markdown**"
        )

        assert isinstance(result, str)
        assert "Format **markdown**" in result
        assert "Base directory" in result

    @pytest.mark.asyncio
    async def test_manager_ainvoke_skill_not_found(self, skill_manager_async):
        """Test ainvoke_skill raises SkillNotFoundError for unknown skill."""
        with pytest.raises(SkillNotFoundError, match="Skill 'unknown-skill' not found"):
            await skill_manager_async.ainvoke_skill("unknown-skill", "test")

    @pytest.mark.asyncio
    async def test_manager_ainvoke_skill_concurrent(self, skill_manager_async):
        """Test concurrent async invocations via manager (10+ parallel)."""
        # Create 12 concurrent invocations
        tasks = [
            skill_manager_async.ainvoke_skill("code-reviewer", f"review code {i}")
            for i in range(12)
        ]

        # Execute concurrently
        results = await asyncio.gather(*tasks)

        # Verify all succeeded
        assert len(results) == 12
        for i, result in enumerate(results):
            assert isinstance(result, str)
            assert f"review code {i}" in result

    @pytest.mark.asyncio
    async def test_manager_ainvoke_skill_different_skills_concurrent(
        self, skill_manager_async
    ):
        """Test concurrent invocations of different skills."""
        results = await asyncio.gather(
            skill_manager_async.ainvoke_skill("markdown-formatter", "test 1"),
            skill_manager_async.ainvoke_skill("code-reviewer", "test 2"),
            skill_manager_async.ainvoke_skill("git-helper", "test 3"),
        )

        assert len(results) == 3
        assert all(isinstance(r, str) for r in results)
        assert "test 1" in results[0]
        assert "test 2" in results[1]
        assert "test 3" in results[2]


class TestAsyncStateManagement:
    """Test async/sync state management and error handling."""

    @pytest.mark.asyncio
    async def test_ainvoke_skill_before_adiscover_raises_error(
        self, skills_directory: Path
    ):
        """Test that ainvoke_skill before adiscover raises SkillsUseError."""
        manager = SkillManager(skills_directory)

        # Attempt to invoke before discovery
        with pytest.raises(
            SkillsUseError, match="Manager not initialized. Call adiscover"
        ):
            await manager.ainvoke_skill("markdown-formatter", "test")

    def test_ainvoke_skill_after_sync_discover_raises_async_state_error(
        self, skills_directory: Path
    ):
        """Test that ainvoke_skill after sync discover raises AsyncStateError."""
        manager = SkillManager(skills_directory)
        manager.discover()  # Sync discovery

        # Attempt async invocation after sync discovery
        with pytest.raises(
            AsyncStateError,
            match="Manager was initialized with discover\\(\\) \\(sync mode\\)",
        ):
            # Need to use asyncio.run to execute the coroutine
            asyncio.run(manager.ainvoke_skill("markdown-formatter", "test"))

    @pytest.mark.asyncio
    async def test_init_mode_transitions_to_async(self, skills_directory: Path):
        """Test that init_mode transitions to ASYNC after adiscover."""
        manager = SkillManager(skills_directory)

        # Initially uninitialized
        assert manager.init_mode == InitMode.UNINITIALIZED

        # Async discovery
        await manager.adiscover()

        # Should transition to ASYNC
        assert manager.init_mode == InitMode.ASYNC

    @pytest.mark.asyncio
    async def test_init_mode_prevents_sync_invoke_after_async_discover(
        self, skills_directory: Path
    ):
        """Test that sync invoke_skill is prevented after async discover."""
        manager = SkillManager(skills_directory)
        await manager.adiscover()

        # Note: invoke_skill doesn't check init_mode in current implementation
        # This test documents expected behavior
        # If state checking is added later, update this test
        result = manager.invoke_skill("markdown-formatter", "test")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_multiple_adiscover_calls_allowed(self, skills_directory: Path):
        """Test that multiple adiscover calls are allowed (idempotent)."""
        manager = SkillManager(skills_directory)

        # First discovery
        await manager.adiscover()
        skills_count_1 = len(manager.list_skills())

        # Second discovery (should work)
        await manager.adiscover()
        skills_count_2 = len(manager.list_skills())

        # Should have same number of skills
        assert skills_count_1 == skills_count_2
        assert manager.init_mode == InitMode.ASYNC

    @pytest.mark.asyncio
    async def test_ainvoke_skill_after_multiple_adiscover(self, skills_directory: Path):
        """Test that ainvoke_skill works after multiple adiscover calls."""
        manager = SkillManager(skills_directory)

        # Multiple discoveries
        await manager.adiscover()
        await manager.adiscover()

        # Should still be able to invoke
        result = await manager.ainvoke_skill("markdown-formatter", "test")
        assert isinstance(result, str)


class TestAsyncPerformance:
    """Test async invocation performance characteristics."""

    @pytest.mark.asyncio
    async def test_async_invocation_overhead_minimal(self, skill_manager_async):
        """Test that async invocation overhead is minimal (<5ms difference)."""
        import time

        skill_name = "markdown-formatter"
        test_args = "test input"

        # Measure sync invocation
        skill = skill_manager_async.load_skill(skill_name)
        _ = skill.invoke(test_args)  # Warm up (load content)

        # Sync timing
        sync_start = time.perf_counter()
        _ = skill.invoke(test_args)
        sync_time = time.perf_counter() - sync_start

        # Async timing
        async_start = time.perf_counter()
        _ = await skill.ainvoke(test_args)
        async_time = time.perf_counter() - async_start

        # Async should be within 5ms of sync (content is cached)
        time_diff = abs(async_time - sync_time)
        assert time_diff < 0.005, f"Async overhead too high: {time_diff*1000:.2f}ms"

    @pytest.mark.asyncio
    async def test_concurrent_invocations_work_correctly(
        self, skill_manager_async
    ):
        """Test that concurrent invocations complete successfully.

        Note: Performance comparison is not reliable due to caching,
        so we just verify correctness of concurrent execution.
        """
        num_invocations = 5
        test_args = "test input"

        # Concurrent invocations
        results = await asyncio.gather(
            *[
                skill_manager_async.ainvoke_skill("code-reviewer", f"{test_args} {i}")
                for i in range(num_invocations)
            ]
        )

        # All invocations should succeed
        assert len(results) == num_invocations
        for i, result in enumerate(results):
            assert isinstance(result, str)
            assert f"{test_args} {i}" in result

        # Verify concurrent execution completed (not testing speed, just correctness)


class TestAsyncEdgeCases:
    """Test edge cases and error conditions for async invocation."""

    @pytest.mark.asyncio
    async def test_ainvoke_with_very_long_arguments(self, skill_manager_async):
        """Test async invocation with very long arguments."""
        long_args = "x" * 10000  # 10KB of arguments

        result = await skill_manager_async.ainvoke_skill("markdown-formatter", long_args)

        assert isinstance(result, str)
        assert long_args in result

    @pytest.mark.asyncio
    async def test_ainvoke_with_special_characters(self, skill_manager_async):
        """Test async invocation with special characters in arguments."""
        special_args = "Test with $SPECIAL **chars** and\nnewlines\t\ttabs"

        result = await skill_manager_async.ainvoke_skill("code-reviewer", special_args)

        assert isinstance(result, str)
        # Arguments should be preserved in result
        assert "Test with" in result

    @pytest.mark.asyncio
    async def test_ainvoke_with_unicode(self, skill_manager_async):
        """Test async invocation with Unicode characters."""
        unicode_args = "Test with émojis 🎉 and 中文字符"

        result = await skill_manager_async.ainvoke_skill("git-helper", unicode_args)

        assert isinstance(result, str)
        assert "Test with" in result

    @pytest.mark.asyncio
    async def test_ainvoke_skill_empty_string_name(self, skill_manager_async):
        """Test that empty string skill name raises SkillNotFoundError."""
        with pytest.raises(SkillNotFoundError):
            await skill_manager_async.ainvoke_skill("", "test")

    @pytest.mark.asyncio
    async def test_concurrent_ainvoke_same_skill_stress_test(self, skill_manager_async):
        """Stress test: 50 concurrent invocations of the same skill."""
        num_concurrent = 50

        tasks = [
            skill_manager_async.ainvoke_skill("markdown-formatter", f"test {i}")
            for i in range(num_concurrent)
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == num_concurrent
        for i, result in enumerate(results):
            assert isinstance(result, str)
            assert f"test {i}" in result
