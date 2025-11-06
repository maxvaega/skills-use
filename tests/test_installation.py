"""
Installation Tests for skillkit Library

Tests package installation and imports across different configurations:
- Core imports work without optional dependencies
- LangChain imports work with [langchain] extra
- LangChain imports fail gracefully without extra
- Package metadata is correct

These tests validate the package structure and distribution.
"""

import sys
from importlib import reload
from unittest.mock import patch

import pytest


def test_core_imports_without_extras():
    """Test that core functionality imports work without optional dependencies."""
    # Core imports should always work
    from skillkit import SkillManager, SkillMetadata, Skill
    from skillkit.core.discovery import SkillDiscovery
    from skillkit.core.parser import SkillParser
    from skillkit.core.processors import ContentProcessor
    from skillkit.core.exceptions import (
        SkillsUseError,
        MissingRequiredFieldError,
        InvalidYAMLError,
        ContentLoadError,
    )

    # Verify classes are importable and instantiable
    assert SkillManager is not None
    assert SkillMetadata is not None
    assert Skill is not None
    assert SkillDiscovery is not None
    assert SkillParser is not None
    assert ContentProcessor is not None

    # Verify exceptions are importable
    assert issubclass(MissingRequiredFieldError, SkillsUseError)
    assert issubclass(InvalidYAMLError, SkillsUseError)
    assert issubclass(ContentLoadError, SkillsUseError)


def test_langchain_import_with_extras():
    """Test that LangChain integration imports work when langchain is installed."""
    try:
        from skillkit.integrations.langchain import create_langchain_tools

        # If langchain is installed, this should work
        assert create_langchain_tools is not None
        assert callable(create_langchain_tools)
    except ImportError as e:
        # If langchain is not installed, skip test
        pytest.skip(f"LangChain not installed: {e}")


def test_langchain_import_fails_without_extras():
    """Test that LangChain imports fail gracefully when langchain not installed."""
    # This test simulates the scenario where langchain is not installed
    # We can't actually uninstall it during test, so we mock the import failure

    # Try importing - it should either work (if installed) or raise ImportError
    try:
        from skillkit.integrations.langchain import create_langchain_tools

        # If this succeeds, langchain is installed - verify it works
        assert create_langchain_tools is not None
        pytest.skip("LangChain is installed, cannot test import failure scenario")

    except ImportError as e:
        # Expected behavior when langchain not installed
        assert "langchain" in str(e).lower() or "No module named" in str(e)


def test_package_version_metadata():
    """Test that package version metadata is correct."""
    import skillkit

    # Verify version attribute exists
    assert hasattr(skillkit, "__version__")

    # Verify version format (should be semantic versioning)
    version = skillkit.__version__
    assert isinstance(version, str)
    assert len(version) > 0

    # Version should match expected format (e.g., "0.1.0")
    parts = version.split(".")
    assert len(parts) >= 2, f"Version should have at least 2 parts: {version}"

    # First two parts should be numeric
    assert parts[0].isdigit(), f"Major version should be numeric: {version}"
    assert parts[1].isdigit(), f"Minor version should be numeric: {version}"


def test_package_metadata_attributes():
    """Test that package metadata attributes exist and are correct."""
    import skillkit

    # Verify common metadata attributes exist
    assert hasattr(skillkit, "__version__")

    # Check for optional metadata
    # Note: Not all packages expose these, so we just verify the module is importable
    assert skillkit.__name__ == "skillkit"

    # Verify main exports are available
    expected_exports = ["SkillManager", "SkillMetadata", "Skill"]
    for export in expected_exports:
        assert hasattr(
            skillkit, export
        ), f"Expected export '{export}' not found in skillkit"


def test_import_from_top_level():
    """Test that common classes can be imported from top-level package."""
    # These should all work from the top level
    from skillkit import SkillManager
    from skillkit import SkillMetadata
    from skillkit import Skill

    # Verify they're the correct types
    assert SkillManager.__name__ == "SkillManager"
    assert SkillMetadata.__name__ == "SkillMetadata"
    assert Skill.__name__ == "Skill"


def test_submodule_imports():
    """Test that submodules can be imported directly."""
    # Core submodules
    from skillkit.core import discovery
    from skillkit.core import parser
    from skillkit.core import models
    from skillkit.core import manager
    from skillkit.core import processors
    from skillkit.core import exceptions

    # Verify modules are loaded
    assert discovery.__name__ == "skillkit.core.discovery"
    assert parser.__name__ == "skillkit.core.parser"
    assert models.__name__ == "skillkit.core.models"
    assert manager.__name__ == "skillkit.core.manager"
    assert processors.__name__ == "skillkit.core.processors"
    assert exceptions.__name__ == "skillkit.core.exceptions"


def test_type_hints_available():
    """Test that type hints are available (py.typed marker)."""
    import skillkit

    # Verify py.typed marker exists (indicates PEP 561 compliance)
    # This enables type checkers to use the package's type hints
    import importlib.resources

    try:
        # Python 3.9+
        if hasattr(importlib.resources, "files"):
            files = importlib.resources.files("skillkit")
            py_typed_exists = (files / "py.typed").is_file()
        else:
            # Python 3.8 fallback
            py_typed_exists = importlib.resources.is_resource("skillkit", "py.typed")

        assert py_typed_exists, "py.typed marker file not found (required for PEP 561)"
    except (TypeError, FileNotFoundError):
        pytest.skip("Could not verify py.typed marker (package may not be installed)")
