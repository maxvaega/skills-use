"""Example demonstrating secure file reference resolution for skills.

This script shows how to use the FilePathResolver to securely access
supporting files within a skill's directory structure.

Usage:
    python examples/file_references.py
"""

import logging

from skillkit import Skill, SkillManager
from skillkit.core.exceptions import PathSecurityError
from skillkit.core.path_resolver import FilePathResolver

# Configure logging to see security events
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def demonstrate_basic_resolution():
    """Demonstrate basic file path resolution."""
    print("\n" + "=" * 80)
    print("Example 1: Basic File Path Resolution")
    print("=" * 80)

    # Create skill manager and discover skills
    manager = SkillManager(project_skill_dir="examples/skills")
    manager.discover()

    # Get the file-reference-skill metadata
    metadata = manager.get_skill("file-reference-skill")
    # Create Skill object to access base_directory
    skill = Skill(metadata=metadata, base_directory=metadata.skill_path.parent)
    base_dir = skill.base_directory

    print(f"\nSkill base directory: {base_dir}")

    # Resolve various supporting file paths
    file_paths = [
        "scripts/data_processor.py",
        "scripts/validator.py",
        "scripts/helper.sh",
        "templates/config.yaml",
        "templates/report.md",
        "docs/usage.md",
        "docs/examples.md",
    ]

    print("\nResolving supporting file paths:")
    for rel_path in file_paths:
        try:
            abs_path = FilePathResolver.resolve_path(base_dir, rel_path)
            exists = abs_path.exists()
            status = "EXISTS" if exists else "MISSING"
            print(f"  ✓ {rel_path:40} -> {status}")
            if exists:
                size = abs_path.stat().st_size
                print(f"    Size: {size} bytes")
        except PathSecurityError as e:
            print(f"  ✗ {rel_path:40} -> BLOCKED")
            print(f"    Error: {e}")


def demonstrate_file_reading():
    """Demonstrate reading supporting files."""
    print("\n" + "=" * 80)
    print("Example 2: Reading Supporting Files")
    print("=" * 80)

    # Get skill
    manager = SkillManager(project_skill_dir="examples/skills")
    manager.discover()
    metadata = manager.get_skill("file-reference-skill")
    skill = Skill(metadata=metadata, base_directory=metadata.skill_path.parent)
    base_dir = skill.base_directory

    # Read Python script
    print("\nReading scripts/data_processor.py:")
    script_path = FilePathResolver.resolve_path(base_dir, "scripts/data_processor.py")
    with open(script_path) as f:
        script_content = f.read()
    print(f"  File size: {len(script_content)} bytes")
    print(f"  First line: {script_content.split(chr(10))[0]}")

    # Read YAML configuration
    print("\nReading templates/config.yaml:")
    config_path = FilePathResolver.resolve_path(base_dir, "templates/config.yaml")
    with open(config_path) as f:
        config_content = f.read()
    print(f"  File size: {len(config_content)} bytes")
    print(f"  First line: {config_content.split(chr(10))[0]}")

    # Read documentation
    print("\nReading docs/usage.md:")
    docs_path = FilePathResolver.resolve_path(base_dir, "docs/usage.md")
    with open(docs_path) as f:
        docs_content = f.read()
    print(f"  File size: {len(docs_content)} bytes")
    lines = docs_content.split("\n")
    print(f"  Total lines: {len(lines)}")
    print(f"  First line: {lines[0]}")


def demonstrate_security_validation():
    """Demonstrate path traversal prevention."""
    print("\n" + "=" * 80)
    print("Example 3: Security Validation (Path Traversal Prevention)")
    print("=" * 80)

    # Get skill
    manager = SkillManager(project_skill_dir="examples/skills")
    manager.discover()
    metadata = manager.get_skill("file-reference-skill")
    skill = Skill(metadata=metadata, base_directory=metadata.skill_path.parent)
    base_dir = skill.base_directory

    # Test various attack patterns
    malicious_paths = [
        "../../../etc/passwd",  # Path traversal
        "../../../../../../etc/shadow",  # Deep traversal
        "/etc/passwd",  # Absolute path
        "scripts/../../../etc/passwd",  # Relative with traversal
        "scripts/../../..",  # Multiple traversals
    ]

    print(f"\nBase directory: {base_dir}")
    print("\nTesting security against malicious paths:")

    for malicious_path in malicious_paths:
        try:
            resolved = FilePathResolver.resolve_path(base_dir, malicious_path)
            print(f"  ✗ SECURITY FAILURE: {malicious_path}")
            print(f"    Resolved to: {resolved}")
        except PathSecurityError:
            print(f"  ✓ BLOCKED: {malicious_path}")
            print("    Reason: Path traversal detected")


def demonstrate_skill_invocation():
    """Demonstrate skill invocation with file references."""
    print("\n" + "=" * 80)
    print("Example 4: Skill Invocation with File References")
    print("=" * 80)

    # Create skill manager and discover skills
    manager = SkillManager(project_skill_dir="examples/skills")
    manager.discover()

    # Invoke skill
    print("\nInvoking file-reference-skill with arguments:")
    result = manager.invoke_skill("file-reference-skill", "test_input.csv test_output.csv")

    # Display result (truncated)
    print("\nSkill invocation result (first 1000 chars):")
    print("-" * 80)
    print(result[:1000])
    print("..." if len(result) > 1000 else "")
    print("-" * 80)
    print(f"\nTotal result length: {len(result)} characters")


def demonstrate_error_handling():
    """Demonstrate error handling for file operations."""
    print("\n" + "=" * 80)
    print("Example 5: Error Handling")
    print("=" * 80)

    # Get skill
    manager = SkillManager(project_skill_dir="examples/skills")
    manager.discover()
    metadata = manager.get_skill("file-reference-skill")
    skill = Skill(metadata=metadata, base_directory=metadata.skill_path.parent)
    base_dir = skill.base_directory

    # Test various error conditions
    test_cases = [
        ("nonexistent/file.txt", "File does not exist"),
        ("../../../etc/passwd", "Path traversal attempt"),
        ("/etc/passwd", "Absolute path"),
    ]

    print("\nTesting error handling:")
    for path, description in test_cases:
        print(f"\n  Test: {description}")
        print(f"  Path: {path}")
        try:
            resolved = FilePathResolver.resolve_path(base_dir, path)
            # Try to read file
            with open(resolved) as f:
                content = f.read()
            print(f"  Result: SUCCESS (read {len(content)} bytes)")
        except PathSecurityError as e:
            print("  Result: SECURITY VIOLATION BLOCKED")
            print(f"  Error: {e}")
        except FileNotFoundError:
            print("  Result: FILE NOT FOUND (expected for testing)")
        except Exception as e:
            print(f"  Result: ERROR ({type(e).__name__}: {e})")


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("File Reference Resolution Examples")
    print("=" * 80)
    print("\nThis script demonstrates secure file path resolution for skills")
    print("using the FilePathResolver class.\n")

    try:
        # Run all examples
        demonstrate_basic_resolution()
        demonstrate_file_reading()
        demonstrate_security_validation()
        demonstrate_skill_invocation()
        demonstrate_error_handling()

        print("\n" + "=" * 80)
        print("All examples completed successfully!")
        print("=" * 80)
        print("\nKey Takeaways:")
        print("  1. Use FilePathResolver.resolve_path() for all file access")
        print("  2. All paths are validated to prevent directory traversal")
        print("  3. Symlinks are resolved and checked for escape attempts")
        print("  4. Security violations raise PathSecurityError with detailed logging")
        print("  5. Use relative paths from skill base directory only")
        print("\n")

    except Exception as e:
        print(f"\n\nError running examples: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
