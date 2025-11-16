#!/usr/bin/env python3
"""Multi-source skill discovery and conflict resolution example.

This script demonstrates all v0.2 multi-source capabilities:
- Discovering skills from multiple sources (project, anthropic, plugins, custom)
- Priority-based conflict resolution (PROJECT > ANTHROPIC > PLUGIN > CUSTOM)
- Enhanced conflict logging with all paths and priorities
- Listing skills with qualified names for conflicts only
- Accessing shadowed skills via fully qualified names (plugin:skill)
- Duplicate plugin name detection and disambiguation

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


def demo_priority_resolution():
    """Demonstrate priority-based conflict resolution (Phase 9 - US7)."""
    logger.info("=" * 80)
    logger.info("SCENARIO 1: Priority-Based Conflict Resolution")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Setup: Configure manager with 4 sources in priority order:")
    logger.info("  1. PROJECT (./examples/skills) - Priority 100")
    logger.info("  2. ANTHROPIC (./.claude/skills) - Priority 50")
    logger.info("  3. PLUGIN (./examples/skills/plugin-example) - Priority 10")
    logger.info("  4. CUSTOM (./extra-skills) - Priority 5")
    logger.info("")

    manager = SkillManager(
        project_skill_dir="./examples/skills",
        anthropic_config_dir="./.claude/skills",
        plugin_dirs=["./examples/skills/plugin-example"],
        additional_search_paths=["./extra-skills"],
    )

    logger.info("Running discovery (watch for conflict warnings)...")
    manager.discover()

    logger.info("")
    logger.info(f"Discovery complete! Found {len(manager.list_skills())} unique skill(s)")
    logger.info("")
    logger.info("Discovered skills (highest priority version for each name):")
    for skill in manager.list_skills():
        logger.info(f"  - {skill.name}")
        logger.info(f"    Description: {skill.description}")
        logger.info(f"    Path: {skill.skill_path}")
        logger.info("")


def demo_qualified_names():
    """Demonstrate qualified name access to shadowed skills (Phase 9 - US7)."""
    logger.info("=" * 80)
    logger.info("SCENARIO 2: Qualified Name Access")
    logger.info("=" * 80)
    logger.info("")
    logger.info("When conflicts exist, lower-priority versions are still accessible")
    logger.info("via fully qualified names (plugin-name:skill-name).")
    logger.info("")

    manager = SkillManager(
        project_skill_dir="./examples/skills",
        plugin_dirs=["./examples/skills/plugin-example"],
    )
    manager.discover()

    logger.info("Listing skills with qualified names for conflicts:")
    skill_names = manager.list_skills(include_qualified=True)
    for name in skill_names:
        if ":" in name:
            logger.info(f"  - {name} (qualified - shadowed plugin skill)")
        else:
            logger.info(f"  - {name} (simple - highest priority)")

    logger.info("")
    logger.info("Accessing skills:")

    # Try to access a skill that might exist in both project and plugin
    skills = manager.list_skills()
    if skills:
        skill_name = skills[0].name
        logger.info(f"  Simple name '{skill_name}':")
        metadata = manager.get_skill(skill_name)
        logger.info(f"    -> {metadata.skill_path}")

        # Try qualified access if plugins exist
        for plugin_name in manager._plugin_skills:
            if skill_name in manager._plugin_skills[plugin_name]:
                qualified_name = f"{plugin_name}:{skill_name}"
                logger.info(f"  Qualified name '{qualified_name}':")
                plugin_metadata = manager.get_skill(qualified_name)
                logger.info(f"    -> {plugin_metadata.skill_path}")


def demo_duplicate_plugins():
    """Demonstrate duplicate plugin name detection and disambiguation (Phase 9 - US7)."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("SCENARIO 3: Duplicate Plugin Name Detection")
    logger.info("=" * 80)
    logger.info("")
    logger.info("If multiple plugins have the same name, they are automatically")
    logger.info("disambiguated with numeric suffixes (plugin-name-2, plugin-name-3, etc.).")
    logger.info("")

    # Note: This would require creating duplicate plugins for testing
    # For now, demonstrate the concept
    logger.info("Example: If you configure two plugins both named 'data-tools':")
    logger.info("  plugin_dirs=[")
    logger.info("    './plugins/data-tools',  # First one: 'data-tools'")
    logger.info("    './other/data-tools',    # Duplicate: 'data-tools-2'")
    logger.info("  ]")
    logger.info("")
    logger.info("The manager will log:")
    logger.info("  WARNING: Duplicate plugin name 'data-tools' detected.")
    logger.info("           Disambiguating as 'data-tools-2' for plugin at ./other/data-tools.")
    logger.info("           Consider renaming the plugin to avoid conflicts.")
    logger.info("")
    logger.info("Skills will be accessible as:")
    logger.info("  - data-tools:csv-parser (from first plugin)")
    logger.info("  - data-tools-2:csv-parser (from second plugin)")


def demo_enhanced_logging():
    """Demonstrate enhanced conflict logging (Phase 9 - US7)."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("SCENARIO 4: Enhanced Conflict Logging")
    logger.info("=" * 80)
    logger.info("")
    logger.info("When conflicts are detected, detailed information is logged:")
    logger.info("")

    # Set logging to DEBUG to see all messages
    logging.getLogger("skillkit.core.manager").setLevel(logging.DEBUG)

    manager = SkillManager(
        project_skill_dir="./examples/skills",
        plugin_dirs=["./examples/skills/plugin-example"],
    )

    logger.info("Running discovery with DEBUG logging enabled...")
    logger.info("Watch for detailed conflict messages showing:")
    logger.info("  - KEEPING: path (source type, priority)")
    logger.info("  - IGNORING: path (source type, priority)")
    logger.info("  - RESOLUTION: explanation and qualified name hint")
    logger.info("")

    manager.discover()

    # Reset logging
    logging.getLogger("skillkit.core.manager").setLevel(logging.INFO)


def demo_conflict_resolution_order():
    """Demonstrate priority order and resolution rules (Phase 9 - US7)."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("SCENARIO 5: Priority Resolution Rules")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Priority Order (highest to lowest):")
    logger.info("  1. PROJECT (100)   - Project-specific skills")
    logger.info("  2. ANTHROPIC (50)  - Anthropic config skills")
    logger.info("  3. PLUGIN (10)     - Plugin skills")
    logger.info("  4. CUSTOM (5-)     - Additional paths (5, 4, 3, ...)")
    logger.info("")
    logger.info("Resolution Rules:")
    logger.info("  - Sources are scanned in priority order (highest first)")
    logger.info("  - First skill found with a given name wins")
    logger.info("  - Later skills with the same name are ignored (logged as WARNING)")
    logger.info("  - Plugin skills are ALWAYS stored in plugin namespace")
    logger.info("  - Qualified names (plugin:skill) bypass priority resolution")
    logger.info("")
    logger.info("Example Scenario:")
    logger.info("  If 'csv-parser' skill exists in:")
    logger.info("    - ./skills/csv-parser/ (PROJECT, priority 100)")
    logger.info("    - ./plugins/data-tools/skills/csv-parser/ (PLUGIN, priority 10)")
    logger.info("")
    logger.info("  Then:")
    logger.info("    get_skill('csv-parser')             -> PROJECT version")
    logger.info("    get_skill('data-tools:csv-parser')  -> PLUGIN version")
    logger.info("")
    logger.info("    list_skills(include_qualified=False) -> ['csv-parser']")
    logger.info(
        "    list_skills(include_qualified=True)  -> ['csv-parser', 'data-tools:csv-parser']"
    )


def main():
    """Run all Phase 9 (User Story 7) demonstrations."""
    logger.info("")
    logger.info("╔" + "═" * 78 + "╗")
    logger.info("║" + " " * 78 + "║")
    logger.info("║" + "  Phase 9: Graceful Conflict Resolution (User Story 7)".center(78) + "║")
    logger.info("║" + " " * 78 + "║")
    logger.info("╚" + "═" * 78 + "╝")
    logger.info("")

    # Run all demonstrations
    demo_priority_resolution()
    demo_qualified_names()
    demo_duplicate_plugins()
    demo_enhanced_logging()
    demo_conflict_resolution_order()

    logger.info("")
    logger.info("=" * 80)
    logger.info("All demonstrations complete!")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Key Takeaways:")
    logger.info("  ✓ Priority-based resolution ensures predictable conflict handling")
    logger.info("  ✓ Enhanced logging provides full transparency on resolution decisions")
    logger.info("  ✓ Qualified names enable access to ALL skill versions")
    logger.info("  ✓ Duplicate plugin names are automatically disambiguated")
    logger.info("  ✓ list_skills(include_qualified=True) shows only conflicting versions")
    logger.info("")


if __name__ == "__main__":
    main()
