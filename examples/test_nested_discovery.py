#!/usr/bin/env python3
"""Test script for nested skill discovery (sync and async).

This script validates that both sync and async discovery methods correctly
discover skills in nested directory structures.
"""

import asyncio
from pathlib import Path

from skillkit import SkillManager


def test_sync_nested_discovery():
    """Test synchronous nested skill discovery."""
    print("=" * 70)
    print("Testing Synchronous Nested Discovery")
    print("=" * 70)

    # Use the nested-example directory
    nested_skills_dir = Path(__file__).parent / "skills" / "nested-example"

    if not nested_skills_dir.exists():
        print(f"ERROR: Nested skills directory not found: {nested_skills_dir}")
        return False

    # Create manager with nested skills
    manager = SkillManager(project_skill_dir=nested_skills_dir)

    # Discover skills synchronously
    print(f"\nScanning: {nested_skills_dir}")
    manager.discover()

    # List discovered skills
    skills = manager.list_skills()
    print(f"\nDiscovered {len(skills)} skills:")

    expected_skills = {
        "nested-root-skill",
        "nested-mid-skill",
        "nested-deep-skill",
        "nested-category-b",
    }

    for metadata in skills:
        depth = len(metadata.skill_path.parent.relative_to(nested_skills_dir).parts)
        print(f"  - {metadata.name}: {metadata.description}")
        print(f"    Path: {metadata.skill_path.relative_to(nested_skills_dir)}")
        print(f"    Depth: {depth}")

    # Validate all expected skills were found
    found_names = {m.name for m in skills}
    missing = expected_skills - found_names
    extra = found_names - expected_skills

    if missing:
        print(f"\n❌ FAILED: Missing skills: {missing}")
        return False

    if extra:
        print(f"\n⚠️  WARNING: Extra skills found: {extra}")

    print(f"\n✅ PASSED: All {len(expected_skills)} expected skills discovered")
    return True


async def test_async_nested_discovery():
    """Test asynchronous nested skill discovery."""
    print("\n" + "=" * 70)
    print("Testing Asynchronous Nested Discovery")
    print("=" * 70)

    # Use the nested-example directory
    nested_skills_dir = Path(__file__).parent / "skills" / "nested-example"

    if not nested_skills_dir.exists():
        print(f"ERROR: Nested skills directory not found: {nested_skills_dir}")
        return False

    # Create manager with nested skills
    manager = SkillManager(project_skill_dir=nested_skills_dir)

    # Discover skills asynchronously
    print(f"\nScanning (async): {nested_skills_dir}")
    await manager.adiscover()

    # List discovered skills
    skills = manager.list_skills()
    print(f"\nDiscovered {len(skills)} skills:")

    expected_skills = {
        "nested-root-skill",
        "nested-mid-skill",
        "nested-deep-skill",
        "nested-category-b",
    }

    for metadata in skills:
        depth = len(metadata.skill_path.parent.relative_to(nested_skills_dir).parts)
        print(f"  - {metadata.name}: {metadata.description}")
        print(f"    Path: {metadata.skill_path.relative_to(nested_skills_dir)}")
        print(f"    Depth: {depth}")

    # Validate all expected skills were found
    found_names = {m.name for m in skills}
    missing = expected_skills - found_names
    extra = found_names - expected_skills

    if missing:
        print(f"\n❌ FAILED: Missing skills: {missing}")
        return False

    if extra:
        print(f"\n⚠️  WARNING: Extra skills found: {extra}")

    print(f"\n✅ PASSED: All {len(expected_skills)} expected skills discovered")
    return True


async def test_sync_async_consistency():
    """Test that sync and async discovery produce identical results."""
    print("\n" + "=" * 70)
    print("Testing Sync/Async Consistency")
    print("=" * 70)

    nested_skills_dir = Path(__file__).parent / "skills" / "nested-example"

    # Sync discovery
    manager_sync = SkillManager(project_skill_dir=nested_skills_dir)
    manager_sync.discover()
    sync_skills = {m.name for m in manager_sync.list_skills()}

    # Async discovery
    manager_async = SkillManager(project_skill_dir=nested_skills_dir)
    await manager_async.adiscover()
    async_skills = {m.name for m in manager_async.list_skills()}

    print(f"Sync discovered: {len(sync_skills)} skills")
    print(f"Async discovered: {len(async_skills)} skills")

    if sync_skills == async_skills:
        print("✅ PASSED: Sync and async produce identical results")
        return True
    else:
        print("❌ FAILED: Sync and async produced different results")
        print(f"  Sync only: {sync_skills - async_skills}")
        print(f"  Async only: {async_skills - sync_skills}")
        return False


async def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("Nested Skill Discovery Tests")
    print("=" * 70)

    results = []

    # Run sync test
    results.append(("Sync Discovery", test_sync_nested_discovery()))

    # Run async test
    results.append(("Async Discovery", await test_async_nested_discovery()))

    # Run consistency test
    results.append(("Sync/Async Consistency", await test_sync_async_consistency()))

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 70)

    if all_passed:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
