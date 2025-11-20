#!/usr/bin/env python3
"""Performance benchmarks for script execution feature (v0.3)."""

import time
from pathlib import Path

from skillkit import SkillManager


def benchmark_script_detection():
    """Benchmark script detection speed."""
    print("=" * 60)
    print("Script Detection Performance Benchmark")
    print("=" * 60)

    manager = SkillManager(skill_dir="examples/skills")
    manager.discover()

    # Find skills with scripts
    skills_with_scripts = []
    for skill_metadata in manager.list_skills():
        skill = manager.load_skill(skill_metadata.name)
        if skill.scripts:
            skills_with_scripts.append((skill_metadata.name, len(skill.scripts)))

    print(f"\nFound {len(skills_with_scripts)} skills with scripts:")
    for name, count in skills_with_scripts:
        print(f"  - {name}: {count} scripts")

    # Benchmark detection speed
    print("\n" + "-" * 60)
    print("Detection Speed Test (per skill):")
    print("-" * 60)

    for skill_name, script_count in skills_with_scripts:
        times = []
        for _ in range(10):  # Run 10 times
            # Clear cache by reloading
            manager = SkillManager(skill_dir="examples/skills")
            manager.discover()

            start = time.perf_counter()
            skill = manager.load_skill(skill_name)
            _ = skill.scripts  # Trigger lazy loading
            end = time.perf_counter()

            times.append((end - start) * 1000)  # Convert to ms

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        p95_time = sorted(times)[int(len(times) * 0.95)]

        target_met = "✓" if avg_time < 10 else "✗"
        print(f"\n{skill_name} ({script_count} scripts):")
        print(f"  Average: {avg_time:.2f}ms  {target_met}")
        print(f"  Min: {min_time:.2f}ms | Max: {max_time:.2f}ms | P95: {p95_time:.2f}ms")


def benchmark_script_execution():
    """Benchmark script execution overhead."""
    print("\n\n" + "=" * 60)
    print("Script Execution Performance Benchmark")
    print("=" * 60)

    manager = SkillManager(skill_dir="examples/skills")
    manager.discover()

    # Test with a simple script
    test_args = {"test": "data", "value": 123}

    print("\nTesting script: pdf-extractor.extract")
    print("-" * 60)

    times = []
    for _ in range(10):
        start = time.perf_counter()
        result = manager.execute_skill_script(
            skill_name="pdf-extractor",
            script_name="extract",
            arguments=test_args
        )
        end = time.perf_counter()

        times.append((end - start) * 1000)  # Convert to ms

    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    p95_time = sorted(times)[int(len(times) * 0.95)]

    target_met = "✓" if p95_time < 50 else "✗"
    print(f"\nExecution Times:")
    print(f"  Average: {avg_time:.2f}ms  {target_met if avg_time < 50 else ''}")
    print(f"  Min: {min_time:.2f}ms | Max: {max_time:.2f}ms | P95: {p95_time:.2f}ms  {target_met}")
    print(f"\nTarget: <50ms for 95% of executions (P95)")


def main():
    """Run all benchmarks."""
    benchmark_script_detection()
    benchmark_script_execution()

    print("\n" + "=" * 60)
    print("Benchmark Summary")
    print("=" * 60)
    print("\nPerformance Targets:")
    print("  1. Script detection: <10ms per skill with ≤50 scripts")
    print("  2. Execution overhead: <50ms for 95% of executions")
    print("\nSee output above for detailed results.")
    print("=" * 60)


if __name__ == "__main__":
    main()
