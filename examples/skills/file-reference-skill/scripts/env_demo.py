#!/usr/bin/env python3
"""Environment Variable Demonstration Script

This script demonstrates how skillkit automatically injects environment
variables into script execution context.

Injected Variables:
    - SKILL_NAME: Name of the skill
    - SKILL_BASE_DIR: Absolute path to skill directory
    - SKILL_VERSION: Version from skill metadata
    - SKILLKIT_VERSION: Current skillkit version

These variables can be used for:
    - Locating files relative to skill directory
    - Including skill context in logs
    - Version-specific behavior
    - Debugging and troubleshooting

Usage:
    This script is designed to be executed by skillkit's script executor.
    It reads JSON arguments from stdin and writes results to stdout.
"""

import json
import os
import sys
from pathlib import Path


def main():
    """Demonstrate environment variable access."""
    # Read arguments from stdin (standard skillkit pattern)
    try:
        args = json.load(sys.stdin)
    except json.JSONDecodeError:
        args = {}

    # Access injected environment variables
    skill_name = os.environ.get('SKILL_NAME', 'unknown')
    skill_base = os.environ.get('SKILL_BASE_DIR', 'unknown')
    skill_version = os.environ.get('SKILL_VERSION', '0.0.0')
    skillkit_version = os.environ.get('SKILLKIT_VERSION', 'unknown')

    # Prepare output
    output = {
        "message": "Environment variables successfully accessed!",
        "context": {
            "skill_name": skill_name,
            "skill_base_dir": skill_base,
            "skill_version": skill_version,
            "skillkit_version": skillkit_version
        },
        "arguments_received": args,
        "examples": {
            "relative_file_path": "Use SKILL_BASE_DIR to locate files",
            "logging": f"[{skill_name} v{skill_version}] Log message here",
            "file_resolution": str(Path(skill_base) / "data" / "config.json")
        }
    }

    # Print formatted output
    print("=" * 60)
    print(f"Skill: {skill_name} v{skill_version}")
    print(f"Directory: {skill_base}")
    print(f"Powered by: skillkit v{skillkit_version}")
    print("=" * 60)
    print()
    print("Environment Variables:")
    print(f"  SKILL_NAME        = {skill_name}")
    print(f"  SKILL_BASE_DIR    = {skill_base}")
    print(f"  SKILL_VERSION     = {skill_version}")
    print(f"  SKILLKIT_VERSION  = {skillkit_version}")
    print()
    print("Arguments Received:")
    print(f"  {json.dumps(args, indent=2)}")
    print()
    print("Example Use Cases:")
    print(f"  1. Locate skill files:")
    print(f"     config_path = Path(os.environ['SKILL_BASE_DIR']) / 'config.json'")
    print(f"     → {Path(skill_base) / 'config.json'}")
    print()
    print(f"  2. Contextual logging:")
    print(f"     logger.info(f'[{{os.environ[\"SKILL_NAME\"]}}] Processing...')")
    print(f"     → [{skill_name}] Processing...")
    print()
    print(f"  3. Version-specific behavior:")
    print(f"     if os.environ['SKILL_VERSION'] >= '2.0.0':")
    print(f"         use_new_api()")
    print()
    print("=" * 60)

    # Also output as JSON for programmatic use
    print()
    print("JSON Output:")
    print(json.dumps(output, indent=2))

    # Exit successfully
    return 0


if __name__ == "__main__":
    sys.exit(main())
