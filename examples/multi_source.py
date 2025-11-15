#!/usr/bin/env python3
"""Multi-source skill discovery example.

This script demonstrates:
- Discovering skills from multiple sources (project, anthropic, custom)
- Priority-based conflict resolution
- Listing skills with qualified names
- Accessing skills by simple and qualified names

Usage:
    python examples/multi_source.py
"""

import logging

from skillkit.core.manager import SkillManager

# Configure logging to see discovery details
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def main():
    """Demonstrate multi-source skill discovery."""

    logger.info("=" * 80)
    logger.info("Multi-Source Skill Discovery Example")
    logger.info("=" * 80)

    # Example 1: Single source (backward compatible with v0.1)
    logger.info("\n--- Example 1: Single Source (v0.1 compatibility) ---")
    manager_v1 = SkillManager(project_skill_dir="./examples/skills")
    manager_v1.discover()

    skills = manager_v1.list_skills()
    logger.info(f"Found {len(skills)} skill(s) from single source:")
    for skill in skills:
        logger.info(f"  - {skill.name}: {skill.description}")

    # Example 2: Multiple sources with priority resolution
    logger.info("\n--- Example 2: Multiple Sources ---")

    # Create manager with multiple sources
    manager = SkillManager(
        project_skill_dir="./examples/skills",  # Priority 100 (highest)
        anthropic_config_dir="./.claude/skills",  # Priority 50
        additional_search_paths=["./extra-skills"],  # Priority 5 (lowest)
    )

    # Discover skills from all sources
    manager.discover()

    # List all discovered skills
    skills = manager.list_skills()
    logger.info(f"Found {len(skills)} skill(s) from {len(manager.sources)} source(s):")
    for skill in skills:
        logger.info(f"  - {skill.name}: {skill.description}")
        logger.info(f"    Source: {skill.skill_path.parent}")

    # Example 3: List skills with qualified names (plugin support)
    logger.info("\n--- Example 3: Qualified Skill Names ---")

    # Get skill names including qualified plugin names
    skill_names = manager.list_skills(include_qualified=True)
    logger.info("All skill names (including qualified):")
    for name in skill_names:
        logger.info(f"  - {name}")

    # Example 4: Access skills by name
    logger.info("\n--- Example 4: Access Skills by Name ---")

    if skills:
        # Get first skill by simple name
        first_skill = skills[0]
        logger.info(f"Accessing skill by simple name: '{first_skill.name}'")
        metadata = manager.get_skill(first_skill.name)
        logger.info(f"  Description: {metadata.description}")
        logger.info(f"  Path: {metadata.skill_path}")

        # Invoke skill
        result = manager.invoke_skill(first_skill.name, "example arguments")
        logger.info(f"  Invocation result (first 200 chars):\n{result[:200]}...")

    # Example 5: Demonstrate conflict resolution
    logger.info("\n--- Example 5: Conflict Resolution ---")
    logger.info("When the same skill name appears in multiple sources:")
    logger.info("  - Project skills (priority 100) override Anthropic skills (priority 50)")
    logger.info("  - Anthropic skills (priority 50) override custom paths (priority 5)")
    logger.info("  - Conflicts are logged as WARNING during discovery")
    logger.info("  - Use qualified names (plugin:skill) to access specific versions")

    # Example 6: Source information
    logger.info("\n--- Example 6: Source Information ---")
    logger.info(f"Number of configured sources: {len(manager.sources)}")
    for i, source in enumerate(manager.sources, 1):
        logger.info(
            f"  {i}. Type: {source.source_type.value}, "
            f"Priority: {source.priority}, "
            f"Directory: {source.directory}"
        )

    logger.info("\n" + "=" * 80)
    logger.info("Example complete!")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
