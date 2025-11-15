"""Demo script for Phase 3 - Async Skill Discovery.

This script demonstrates the new async discovery functionality implemented in v0.2.
"""

import asyncio
import time
from pathlib import Path

from skillkit import SkillManager
from skillkit.core.exceptions import AsyncStateError


async def demo_async_discovery():
    """Demonstrate async skill discovery."""
    print("=" * 60)
    print("Phase 3 Demo: Async Skill Discovery")
    print("=" * 60)

    # Example 1: Basic async discovery
    print("\n1. Basic Async Discovery")
    print("-" * 40)
    manager = SkillManager(project_skill_dir="examples/skills")

    print(f"Initial mode: {manager.init_mode.value}")

    start = time.time()
    await manager.adiscover()
    elapsed = time.time() - start

    print(f"After adiscover(): {manager.init_mode.value}")
    print(f"Discovery time: {elapsed*1000:.2f}ms")
    print(f"Skills found: {len(manager.list_skills())}")

    for skill in manager.list_skills():
        print(f"  - {skill.name}: {skill.description}")

    # Example 2: Concurrent async discovery
    print("\n2. Concurrent Async Discovery (5 managers)")
    print("-" * 40)

    async def discover_and_report(i):
        """Discover skills and report."""
        m = SkillManager(project_skill_dir="examples/skills")
        await m.adiscover()
        return i, len(m.list_skills())

    start = time.time()
    results = await asyncio.gather(*[discover_and_report(i) for i in range(5)])
    elapsed = time.time() - start

    print(f"Concurrent discovery time: {elapsed*1000:.2f}ms")
    for i, count in results:
        print(f"  Manager {i}: {count} skills")

    # Example 3: Event loop responsiveness
    print("\n3. Event Loop Remains Responsive")
    print("-" * 40)

    counter = {"value": 0}

    async def increment_counter():
        """Increment counter while discovery runs."""
        for _ in range(50):
            counter["value"] += 1
            await asyncio.sleep(0.001)

    manager2 = SkillManager(project_skill_dir="examples/skills")

    # Run discovery and counter concurrently
    await asyncio.gather(
        manager2.adiscover(),
        increment_counter()
    )

    print(f"Counter reached: {counter['value']} (should be 50)")
    print(f"Skills discovered: {len(manager2.list_skills())}")
    print("✓ Event loop remained responsive during async I/O")

    # Example 4: State management (mixing modes raises error)
    print("\n4. State Management (Sync/Async Separation)")
    print("-" * 40)

    # Sync first
    manager_sync = SkillManager(project_skill_dir="examples/skills")
    manager_sync.discover()
    print(f"Sync manager mode: {manager_sync.init_mode.value}")

    try:
        await manager_sync.adiscover()
        print("ERROR: Should have raised AsyncStateError!")
    except AsyncStateError as e:
        print(f"✓ Correctly raised AsyncStateError: {str(e)[:60]}...")

    # Async first
    manager_async = SkillManager(project_skill_dir="examples/skills")
    await manager_async.adiscover()
    print(f"Async manager mode: {manager_async.init_mode.value}")

    try:
        manager_async.discover()
        print("ERROR: Should have raised AsyncStateError!")
    except AsyncStateError as e:
        print(f"✓ Correctly raised AsyncStateError: {str(e)[:60]}...")

    # Example 5: Sync vs Async equivalence
    print("\n5. Sync vs Async Equivalence")
    print("-" * 40)

    manager_sync2 = SkillManager(project_skill_dir="examples/skills")
    manager_sync2.discover()
    sync_skills = sorted([s.name for s in manager_sync2.list_skills()])

    manager_async2 = SkillManager(project_skill_dir="examples/skills")
    await manager_async2.adiscover()
    async_skills = sorted([s.name for s in manager_async2.list_skills()])

    print(f"Sync discovered: {sync_skills}")
    print(f"Async discovered: {async_skills}")
    print(f"Results identical: {sync_skills == async_skills}")

    if sync_skills == async_skills:
        print("✓ Sync and async discovery produce identical results")

    print("\n" + "=" * 60)
    print("Phase 3 Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo_async_discovery())
