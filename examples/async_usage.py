#!/usr/bin/env python3
"""Async usage example for skillkit library.

This script demonstrates async usage patterns including:
- FastAPI integration
- Concurrent skill invocations
- Non-blocking discovery and execution
"""

import asyncio
import logging
from pathlib import Path

from skillkit import SkillManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")


async def fastapi_example():
    """Demonstrate FastAPI-style async pattern."""
    print("=" * 60)
    print("skillkit: FastAPI Integration Pattern")
    print("=" * 60)

    skills_dir = Path(__file__).parent / "skills"
    print(f"\nUsing skills directory: {skills_dir}")

    # Initialize manager (typically done at app startup)
    print("\n[Startup] Initializing skill manager...")
    manager = SkillManager(skills_dir)
    await manager.adiscover()
    print(f"  Discovered {len(manager.list_skills())} skills")

    # Simulate async API request handlers
    print("\n[Request 1] Processing skill invocation...")
    result1 = await manager.ainvoke_skill("code-reviewer", "Review authentication module")
    print(f"  Response length: {len(result1)} chars")

    print("\n[Request 2] Processing another invocation...")
    result2 = await manager.ainvoke_skill("git-helper", "Generate commit message")
    print(f"  Response length: {len(result2)} chars")

    print("\n" + "=" * 60)
    print("FastAPI pattern complete!")
    print("=" * 60)


async def concurrent_invocations_example():
    """Demonstrate concurrent skill invocations."""
    print("\n\n" + "=" * 60)
    print("skillkit: Concurrent Invocations Example")
    print("=" * 60)

    skills_dir = Path(__file__).parent / "skills"
    print(f"\nUsing skills directory: {skills_dir}")

    # Initialize manager
    manager = SkillManager(skills_dir)
    await manager.adiscover()

    # Process multiple requests concurrently (non-blocking)
    print("\n[Concurrent] Processing 10+ invocations simultaneously...")

    tasks = [manager.ainvoke_skill("code-reviewer", f"Review module {i}") for i in range(5)]
    tasks.extend([manager.ainvoke_skill("git-helper", f"Generate commit {i}") for i in range(5)])
    tasks.extend([manager.ainvoke_skill("markdown-formatter", f"Format doc {i}") for i in range(3)])

    # Execute all concurrently
    import time

    start_time = time.time()
    results = await asyncio.gather(*tasks)
    elapsed = time.time() - start_time

    print(f"\n  Processed {len(results)} invocations")
    print(f"  Time elapsed: {elapsed:.2f}s")
    print(f"  Average: {elapsed / len(results):.3f}s per invocation")

    # Show result summary
    print("\n  Results summary:")
    for i, result in enumerate(results[:5]):  # Show first 5
        print(f"    {i + 1}. Length: {len(result)} chars")
    print(f"    ... and {len(results) - 5} more")

    print("\n" + "=" * 60)
    print("Concurrent invocations complete!")
    print("=" * 60)


async def multi_source_async_example():
    """Demonstrate async discovery with multiple sources."""
    print("\n\n" + "=" * 60)
    print("skillkit: Multi-Source Async Discovery")
    print("=" * 60)

    skills_dir = Path(__file__).parent / "skills"
    print(f"\nUsing skills directory: {skills_dir}")

    # Create manager with multiple sources
    manager = SkillManager(
        project_skill_dir=skills_dir,
        anthropic_config_dir=skills_dir / ".claude" / "skills",  # May not exist
        plugin_dirs=[skills_dir / "example-plugin"],  # May not exist
    )

    # Async discovery (scans all sources concurrently)
    print("\n[Discovery] Scanning multiple sources asynchronously...")
    import time

    start_time = time.time()
    await manager.adiscover()
    elapsed = time.time() - start_time

    print(f"  Discovery time: {elapsed * 1000:.1f}ms")
    print(f"  Total skills: {len(manager.list_skills())}")

    # List skills with sources
    print("\n[Skills] Discovered from all sources:")
    for skill in manager.list_skills()[:10]:  # Show first 10
        print(f"  - {skill.name}: {skill.description[:50]}...")

    print("\n" + "=" * 60)
    print("Multi-source async example complete!")
    print("=" * 60)


async def performance_comparison():
    """Compare sync vs async performance."""
    print("\n\n" + "=" * 60)
    print("skillkit: Performance Comparison (Sync vs Async)")
    print("=" * 60)

    skills_dir = Path(__file__).parent / "skills"

    # Sync version
    print("\n[Sync] Running sync discovery and invocations...")
    import time

    manager_sync = SkillManager(skills_dir)

    start_time = time.time()
    manager_sync.discover()
    sync_discovery_time = time.time() - start_time

    start_time = time.time()
    for i in range(5):
        manager_sync.invoke_skill("code-reviewer", f"Review {i}")
    sync_invoke_time = time.time() - start_time

    print(f"  Discovery time: {sync_discovery_time * 1000:.1f}ms")
    print(f"  5 invocations time: {sync_invoke_time * 1000:.1f}ms")

    # Async version
    print("\n[Async] Running async discovery and invocations...")
    manager_async = SkillManager(skills_dir)

    start_time = time.time()
    await manager_async.adiscover()
    async_discovery_time = time.time() - start_time

    start_time = time.time()
    await asyncio.gather(
        *[manager_async.ainvoke_skill("code-reviewer", f"Review {i}") for i in range(5)]
    )
    async_invoke_time = time.time() - start_time

    print(f"  Discovery time: {async_discovery_time * 1000:.1f}ms")
    print(f"  5 concurrent invocations time: {async_invoke_time * 1000:.1f}ms")

    # Comparison
    print("\n[Comparison]")
    discovery_speedup = (
        sync_discovery_time / async_discovery_time if async_discovery_time > 0 else 1
    )
    invoke_speedup = sync_invoke_time / async_invoke_time if async_invoke_time > 0 else 1
    print(f"  Discovery speedup: {discovery_speedup:.2f}x")
    print(f"  Invocation speedup: {invoke_speedup:.2f}x")

    print("\n" + "=" * 60)
    print("Performance comparison complete!")
    print("=" * 60)


async def main():
    """Run all async examples."""
    # FastAPI integration pattern
    await fastapi_example()

    # Concurrent invocations
    await concurrent_invocations_example()

    # Multi-source async discovery
    await multi_source_async_example()

    # Performance comparison
    await performance_comparison()

    print("\n\n" + "=" * 60)
    print("All async examples complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
