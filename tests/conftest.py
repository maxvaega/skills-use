"""Shared pytest fixtures for skills-use tests."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to test fixtures directory.

    Returns:
        Absolute path to tests/fixtures/ directory
    """
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def skills_dir(fixtures_dir: Path) -> Path:
    """Return path to test skills directory.

    Args:
        fixtures_dir: Path to fixtures directory (from fixtures_dir fixture)

    Returns:
        Absolute path to tests/fixtures/skills/ directory
    """
    return fixtures_dir / "skills"


@pytest.fixture
def valid_skill_path(skills_dir: Path) -> Path:
    """Return path to valid skill fixture.

    Args:
        skills_dir: Path to skills directory (from skills_dir fixture)

    Returns:
        Absolute path to valid-skill/SKILL.md
    """
    return skills_dir / "valid-skill" / "SKILL.md"


@pytest.fixture
def missing_name_skill_path(skills_dir: Path) -> Path:
    """Return path to missing-name skill fixture.

    Args:
        skills_dir: Path to skills directory (from skills_dir fixture)

    Returns:
        Absolute path to missing-name-skill/SKILL.md
    """
    return skills_dir / "missing-name-skill" / "SKILL.md"


@pytest.fixture
def invalid_yaml_skill_path(skills_dir: Path) -> Path:
    """Return path to invalid-yaml skill fixture.

    Args:
        skills_dir: Path to skills directory (from skills_dir fixture)

    Returns:
        Absolute path to invalid-yaml-skill/SKILL.md
    """
    return skills_dir / "invalid-yaml-skill" / "SKILL.md"


@pytest.fixture
def arguments_test_skill_path(skills_dir: Path) -> Path:
    """Return path to arguments-test skill fixture.

    Args:
        skills_dir: Path to skills directory (from skills_dir fixture)

    Returns:
        Absolute path to arguments-test-skill/SKILL.md
    """
    return skills_dir / "arguments-test-skill" / "SKILL.md"
