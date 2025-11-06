#!/usr/bin/env python3
"""Basic usage example for skillkit library.

This script demonstrates standalone usage without framework integration.
"""

import logging
from pathlib import Path

from skillkit import SkillManager

# Configure logging to see skill discovery and invocation
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")


def main() -> None:
    """Demonstrate basic skill manager usage."""
    print("=" * 60)
    print("skillkit: Basic Usage Example")
    print("=" * 60)

    # Use example skills from examples/skills/ directory
    skills_dir = Path(__file__).parent / "skills"
    print(f"\nUsing skills directory: {skills_dir}")

    # Create skill manager
    manager = SkillManager(skills_dir)

    # Discover skills
    print("\n[1] Discovering skills...")
    manager.discover()

    # List all skills
    print("\n[2] Available skills:")
    skills = manager.list_skills()
    for skill in skills:
        print(f"  - {skill.name}: {skill.description}")

    # Get specific skill metadata
    print("\n[3] Getting skill metadata...")
    try:
        metadata = manager.get_skill("code-reviewer")
        print(f"  Name: {metadata.name}")
        print(f"  Description: {metadata.description}")
        print(f"  Path: {metadata.skill_path}")
        print(f"  Allowed tools: {metadata.allowed_tools}")
    except Exception as e:
        print(f"  Error: {e}")

    # Invoke skill with arguments
    print("\n[4] Invoking skill...")
    try:
        result = manager.invoke_skill(
            "code-reviewer", "Review the function calculate_total() in src/billing.py"
        )
        print(f"\nResult preview (first 300 chars):\n{'-' * 60}")
        print(result[:300])
        print("..." if len(result) > 300 else "")
        print("-" * 60)
    except Exception as e:
        print(f"  Error: {e}")

    # Load skill for repeated invocations
    print("\n[5] Loading skill for repeated use...")
    try:
        skill = manager.load_skill("git-helper")
        print(f"  Loaded: {skill.metadata.name}")

        # First invocation (loads content)
        result1 = skill.invoke("Generate commit message for adding authentication")
        print(f"  First invocation result length: {len(result1)} chars")

        # Second invocation (content cached)
        result2 = skill.invoke("Generate commit message for fixing bug in login")
        print(f"  Second invocation result length: {len(result2)} chars")
    except Exception as e:
        print(f"  Error: {e}")

    print("\n" + "=" * 60)
    print("Example complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
