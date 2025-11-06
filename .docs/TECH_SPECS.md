# Technical Architecture Specification - skills-use v0.1

**Version:** 1.0
**Date:** October 28, 2025
**Status:** Implementation Ready
**Author:** Massimo Olivieri

---

## Table of Contents

1. [Module Structure](#1-module-structure)
2. [Core Data Models](#2-core-data-models)
3. [Discovery Module](#3-discovery-module)
4. [Parser Module](#4-parser-module)
5. [Manager Module](#5-manager-module)
6. [Invocation Module](#6-invocation-module)
7. [LangChain Integration](#7-langchain-integration)
8. [Exception Hierarchy](#8-exception-hierarchy)
9. [Public API](#9-public-api)
10. [Dependencies](#10-dependencies)
11. [API Usage Examples](#11-api-usage-examples)
12. [Key Design Decisions](#12-key-design-decisions)
13. [Testing Strategy](#13-testing-strategy)
14. [Performance Considerations](#14-performance-considerations-v01)
15. [Security Considerations](#15-security-considerations-v01)

---

## 1. Module Structure

```
skills-use/
├── src/
│   └── skills_use/
│       ├── __init__.py                 # Public API exports
│       ├── core/
│       │   ├── __init__.py
│       │   ├── discovery.py            # CP-1: Skill discovery
│       │   ├── parser.py               # CP-2: SKILL.md parsing
│       │   ├── models.py               # Data models (SkillMetadata, Skill)
│       │   ├── manager.py              # CP-3: SkillManager
│       │   └── invocation.py           # CP-4: Skill invocation logic
│       ├── integrations/
│       │   ├── __init__.py
│       │   └── langchain.py            # CP-5: LangChain integration
│       └── exceptions.py               # Custom exceptions
├── tests/
│   ├── __init__.py
│   ├── test_discovery.py               # CP-1 tests
│   ├── test_parser.py                  # CP-2 tests
│   ├── test_invocation.py              # CP-4 tests
│   ├── test_manager.py                 # CP-3 tests
│   ├── test_langchain.py               # CP-5 integration tests
│   └── fixtures/
│       └── skills/                     # Test skill samples
│           └── example-skill/
│               └── SKILL.md
├── pyproject.toml
├── README.md
├── LICENSE
└── .gitignore
```

---

## 2. Core Data Models

### `src/skills_use/core/models.py`

```python
"""Core data models for skills-use library."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List


@dataclass
class SkillMetadata:
    """
    Lightweight metadata for a skill.
    Loaded during discovery without reading full content.
    """
    name: str
    description: str
    skill_path: Path
    allowed_tools: Optional[List[str]] = None

    def __post_init__(self):
        """Validate required fields."""
        if not self.name:
            raise ValueError("Skill name is required")
        if not self.description:
            raise ValueError("Skill description is required")
        if not isinstance(self.skill_path, Path):
            self.skill_path = Path(self.skill_path)


@dataclass
class Skill:
    """
    Full skill object with content loaded.
    Created on-demand during invocation.
    """
    metadata: SkillMetadata
    content: str
    base_directory: Path

    def invoke(self, arguments: str = "") -> str:
        """
        Process skill content with arguments.

        Args:
            arguments: User-provided arguments to substitute into skill

        Returns:
            Processed skill content ready for LLM consumption
        """
        from skills_use.core.invocation import process_skill_content
        return process_skill_content(self, arguments)
```

**Design Notes:**
- `SkillMetadata`: Minimal data for discovery phase (name, description, path, allowed_tools)
- `Skill`: Full object with loaded content for invocation
- Progressive disclosure pattern: Metadata loaded upfront, content on-demand
- Validation in `__post_init__` ensures data integrity

---

## 3. Discovery Module

### `src/skills_use/core/discovery.py`

```python
"""Skill discovery from filesystem."""
from pathlib import Path
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class SkillDiscovery:
    """
    Discovers SKILL.md files from .claude/skills/ directory.
    v0.1: Single hardcoded path, flat structure only.
    """

    DEFAULT_SKILLS_DIR = Path.home() / ".claude" / "skills"

    def __init__(self, skills_directory: Optional[Path] = None):
        """
        Initialize discovery with skills directory.

        Args:
            skills_directory: Path to skills directory.
                            Defaults to ~/.claude/skills/
        """
        self.skills_directory = skills_directory or self.DEFAULT_SKILLS_DIR
        logger.debug(f"Initialized SkillDiscovery with path: {self.skills_directory}")

    def discover_skills(self) -> List[Path]:
        """
        Discover all SKILL.md files in skills directory.

        Returns:
            List of Path objects pointing to SKILL.md files

        Raises:
            None - returns empty list if directory doesn't exist

        Algorithm:
            1. Check if skills_directory exists
            2. Iterate through immediate subdirectories
            3. Look for SKILL.md (case-insensitive) in each subdirectory
            4. Return list of discovered paths
        """
        if not self.skills_directory.exists():
            logger.info(f"Skills directory not found: {self.skills_directory}")
            return []

        if not self.skills_directory.is_dir():
            logger.warning(f"Skills path is not a directory: {self.skills_directory}")
            return []

        discovered_skills = []

        # Iterate through subdirectories only (flat structure)
        for skill_dir in self.skills_directory.iterdir():
            if not skill_dir.is_dir():
                continue

            # Look for SKILL.md (case-insensitive)
            skill_file = self._find_skill_file(skill_dir)
            if skill_file:
                discovered_skills.append(skill_file)
                logger.debug(f"Discovered skill: {skill_file}")

        logger.info(f"Discovered {len(discovered_skills)} skills")
        return discovered_skills

    def _find_skill_file(self, directory: Path) -> Optional[Path]:
        """
        Find SKILL.md in directory (case-insensitive).

        Args:
            directory: Directory to search in

        Returns:
            Path to SKILL.md if found, None otherwise
        """
        for file in directory.iterdir():
            if file.is_file() and file.name.lower() == "skill.md":
                return file
        return None
```

**Design Notes:**
- Hardcoded to `~/.claude/skills/` for v0.1 (Anthropic compatibility)
- Flat structure only: `~/.claude/skills/skill-name/SKILL.md`
- Case-insensitive matching for SKILL.md
- Graceful degradation: missing directory returns empty list
- Logging at debug/info levels for observability

**Future Extensions (v0.2+):**
- Multiple search paths (./skills/, custom paths)
- Nested directory support
- Plugin discovery

---

## 4. Parser Module

### `src/skills_use/core/parser.py`

```python
"""SKILL.md parsing with YAML frontmatter extraction."""
from pathlib import Path
from typing import Dict, Any, Tuple
import re
import yaml
import logging

from skills_use.core.models import SkillMetadata
from skills_use.exceptions import SkillParsingError

logger = logging.getLogger(__name__)


class SkillParser:
    """
    Parses SKILL.md files with YAML frontmatter.
    v0.1: Minimal parsing - name, description, allowed-tools only.
    """

    FRONTMATTER_DELIMITER = "---"

    def parse_skill_file(self, skill_path: Path) -> SkillMetadata:
        """
        Parse SKILL.md file and extract metadata.

        Args:
            skill_path: Path to SKILL.md file

        Returns:
            SkillMetadata object with parsed fields

        Raises:
            SkillParsingError: If file cannot be parsed or required fields missing
        """
        if not skill_path.exists():
            raise SkillParsingError(f"Skill file not found: {skill_path}")

        try:
            content = skill_path.read_text(encoding="utf-8")
        except Exception as e:
            raise SkillParsingError(f"Failed to read skill file {skill_path}: {e}")

        frontmatter, _ = self._extract_frontmatter(content)

        # Validate required fields
        if "name" not in frontmatter:
            raise SkillParsingError(f"Missing required field 'name' in {skill_path}")
        if "description" not in frontmatter:
            raise SkillParsingError(f"Missing required field 'description' in {skill_path}")

        # Extract allowed-tools (optional)
        allowed_tools = frontmatter.get("allowed-tools")
        if allowed_tools and not isinstance(allowed_tools, list):
            logger.warning(f"allowed-tools should be a list in {skill_path}, got {type(allowed_tools)}")
            allowed_tools = None

        metadata = SkillMetadata(
            name=frontmatter["name"],
            description=frontmatter["description"],
            skill_path=skill_path,
            allowed_tools=allowed_tools
        )

        logger.debug(f"Parsed skill: {metadata.name}")
        return metadata

    def _extract_frontmatter(self, content: str) -> Tuple[Dict[str, Any], str]:
        """
        Extract YAML frontmatter and markdown content.

        Args:
            content: Full SKILL.md file content

        Returns:
            Tuple of (frontmatter_dict, markdown_content)

        Raises:
            SkillParsingError: If frontmatter is invalid
        """
        # Match content between --- delimiters
        pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            raise SkillParsingError("No valid YAML frontmatter found (must be between --- delimiters)")

        frontmatter_raw = match.group(1)
        markdown_content = match.group(2)

        try:
            frontmatter = yaml.safe_load(frontmatter_raw)
        except yaml.YAMLError as e:
            raise SkillParsingError(f"Invalid YAML in frontmatter: {e}")

        if not isinstance(frontmatter, dict):
            raise SkillParsingError("Frontmatter must be a YAML dictionary")

        return frontmatter, markdown_content

    def load_full_content(self, skill_path: Path) -> str:
        """
        Load full skill content (without frontmatter).

        Args:
            skill_path: Path to SKILL.md file

        Returns:
            Markdown content after frontmatter

        Raises:
            SkillParsingError: If file cannot be read
        """
        try:
            content = skill_path.read_text(encoding="utf-8")
            _, markdown_content = self._extract_frontmatter(content)
            return markdown_content.strip()
        except Exception as e:
            raise SkillParsingError(f"Failed to load skill content from {skill_path}: {e}")
```

**Design Notes:**
- Two-phase parsing: metadata extraction vs full content loading
- YAML safe_load for security (prevents code execution)
- Required fields: `name`, `description`
- Optional fields: `allowed-tools` (parsed but not enforced in v0.1)
- Regex-based frontmatter extraction (handles edge cases)
- UTF-8 encoding enforced

**SKILL.md Format:**
```markdown
---
name: skill-name
description: Brief description
allowed-tools: Tool1, Tool2
---

Skill content in markdown format.

Use $ARGUMENTS for argument substitution.
```

---

## 5. Manager Module

### `src/skills_use/core/manager.py`

```python
"""Central skill management and coordination."""
from pathlib import Path
from typing import List, Dict, Optional
import logging

from skills_use.core.discovery import SkillDiscovery
from skills_use.core.parser import SkillParser
from skills_use.core.models import SkillMetadata, Skill
from skills_use.exceptions import SkillNotFoundError

logger = logging.getLogger(__name__)


class SkillManager:
    """
    Central coordinator for skill discovery, loading, and invocation.
    v0.1: Simple dict-based storage, no caching optimization.
    """

    def __init__(self, skills_directory: Optional[Path] = None):
        """
        Initialize SkillManager with discovery and parsing components.

        Args:
            skills_directory: Path to skills directory.
                            Defaults to ~/.claude/skills/
        """
        self.discovery = SkillDiscovery(skills_directory)
        self.parser = SkillParser()
        self._skills: Dict[str, SkillMetadata] = {}
        self._initialized = False
        logger.debug("Initialized SkillManager")

    def discover(self) -> None:
        """
        Discover and load all skill metadata.
        Call this before using list_skills() or get_skill().
        """
        skill_paths = self.discovery.discover_skills()
        self._skills.clear()

        for skill_path in skill_paths:
            try:
                metadata = self.parser.parse_skill_file(skill_path)
                self._skills[metadata.name] = metadata
                logger.debug(f"Loaded metadata for skill: {metadata.name}")
            except Exception as e:
                logger.error(f"Failed to parse skill at {skill_path}: {e}")
                # Continue processing other skills

        self._initialized = True
        logger.info(f"Discovery complete: {len(self._skills)} skills loaded")

    def list_skills(self) -> List[SkillMetadata]:
        """
        List all discovered skills.

        Returns:
            List of SkillMetadata objects

        Note:
            Call discover() first to populate skills
        """
        if not self._initialized:
            logger.warning("list_skills() called before discover()")
            self.discover()

        return list(self._skills.values())

    def get_skill(self, name: str) -> SkillMetadata:
        """
        Get skill metadata by name.

        Args:
            name: Skill name

        Returns:
            SkillMetadata object

        Raises:
            SkillNotFoundError: If skill not found
        """
        if not self._initialized:
            logger.warning("get_skill() called before discover()")
            self.discover()

        if name not in self._skills:
            raise SkillNotFoundError(f"Skill '{name}' not found")

        return self._skills[name]

    def load_skill(self, name: str) -> Skill:
        """
        Load full skill with content.

        Args:
            name: Skill name

        Returns:
            Skill object with full content loaded

        Raises:
            SkillNotFoundError: If skill not found
        """
        metadata = self.get_skill(name)
        content = self.parser.load_full_content(metadata.skill_path)
        base_directory = metadata.skill_path.parent

        skill = Skill(
            metadata=metadata,
            content=content,
            base_directory=base_directory
        )

        logger.debug(f"Loaded full skill: {name}")
        return skill

    def invoke_skill(self, name: str, arguments: str = "") -> str:
        """
        Load and invoke skill with arguments.

        Args:
            name: Skill name
            arguments: User arguments to pass to skill

        Returns:
            Processed skill content ready for LLM

        Raises:
            SkillNotFoundError: If skill not found
        """
        skill = self.load_skill(name)
        return skill.invoke(arguments)
```

**Design Notes:**
- Orchestrates discovery, parsing, and invocation
- Dict-based skill registry (name → metadata)
- Lazy initialization: auto-discover if not initialized
- Graceful error handling during discovery (logs + continue)
- Strict error handling during get/invoke (raise exceptions)
- No caching in v0.1 (reload content each invocation)

**Lifecycle:**
1. `__init__()` - Create manager
2. `discover()` - Scan filesystem, load metadata
3. `list_skills()` - Browse available skills
4. `invoke_skill()` - Load content + process with arguments

---

## 6. Invocation Module

### `src/skills_use/core/invocation.py`

```python
"""Skill invocation logic with argument substitution."""
import logging

from skills_use.core.models import Skill

logger = logging.getLogger(__name__)


ARGUMENTS_PLACEHOLDER = "$ARGUMENTS"


def process_skill_content(skill: Skill, arguments: str = "") -> str:
    """
    Process skill content with argument substitution and context injection.

    Args:
        skill: Skill object with loaded content
        arguments: User-provided arguments

    Returns:
        Processed content ready for LLM consumption

    Algorithm (resolves OP-5):
        1. Inject base directory context at the beginning
        2. If $ARGUMENTS placeholder exists:
           - Replace all occurrences with arguments
           - If arguments is empty, replace with empty string
        3. If no $ARGUMENTS and arguments provided:
           - Append "\n\nARGUMENTS: {arguments}"
        4. If no $ARGUMENTS and no arguments:
           - Return content as-is (after base directory injection)
    """
    # Step 1: Inject base directory
    base_dir_context = f"Base directory for this skill: {skill.base_directory}\n\n"
    processed_content = base_dir_context + skill.content

    # Step 2-4: Handle arguments
    if ARGUMENTS_PLACEHOLDER in processed_content:
        # Replace all occurrences (handles multiple $ARGUMENTS)
        processed_content = processed_content.replace(ARGUMENTS_PLACEHOLDER, arguments)
        logger.debug(f"Replaced $ARGUMENTS placeholder with provided arguments")
    elif arguments:
        # No placeholder but arguments provided - append
        processed_content += f"\n\nARGUMENTS: {arguments}"
        logger.debug("Appended arguments (no placeholder found)")
    # else: No placeholder, no arguments - return as-is

    return processed_content
```

**Design Notes:**
- Stateless function (no side effects)
- Handles OP-5 edge cases explicitly:
  - Multiple `$ARGUMENTS`: Replace all
  - Empty arguments: Replace with empty string
  - No placeholder + args: Append arguments
  - No placeholder + no args: No modification
- Case-sensitive placeholder matching
- Base directory always injected (enables file references in v0.2+)

**Example Transformations:**

Input skill content:
```markdown
Review the code: $ARGUMENTS
```
Arguments: `"def foo(): pass"`
Output:
```markdown
Base directory for this skill: /Users/.../code-reviewer

Review the code: def foo(): pass
```

Input skill content (no placeholder):
```markdown
Analyze the provided code for bugs.
```
Arguments: `"def foo(): pass"`
Output:
```markdown
Base directory for this skill: /Users/.../code-reviewer

Analyze the provided code for bugs.

ARGUMENTS: def foo(): pass
```

---

## 7. LangChain Integration

### `src/skills_use/integrations/langchain.py`

```python
"""LangChain framework integration."""
from typing import List, Optional
from pathlib import Path
import logging

try:
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, Field
except ImportError:
    raise ImportError(
        "LangChain is not installed. Install with: pip install skills-use[langchain]"
    )

from skills_use.core.manager import SkillManager

logger = logging.getLogger(__name__)


class SkillInput(BaseModel):
    """Input schema for LangChain skill tools."""
    arguments: str = Field(
        default="",
        description="Arguments to pass to the skill"
    )


def create_langchain_tools(
    manager: Optional[SkillManager] = None,
    skills_directory: Optional[Path] = None
) -> List[StructuredTool]:
    """
    Create LangChain StructuredTool instances from discovered skills.

    Args:
        manager: Existing SkillManager instance. If None, creates new one.
        skills_directory: Path to skills directory (used if manager is None)

    Returns:
        List of LangChain StructuredTool objects

    Usage:
        >>> from skills_use.integrations.langchain import create_langchain_tools
        >>> tools = create_langchain_tools()
        >>> # Use with LangChain agent
        >>> from langchain.agents import create_openai_functions_agent
        >>> agent = create_openai_functions_agent(llm, tools, prompt)
    """
    if manager is None:
        manager = SkillManager(skills_directory)
        manager.discover()

    tools = []

    for skill_metadata in manager.list_skills():
        # Create closure to capture skill name
        def make_skill_func(skill_name: str):
            def skill_func(arguments: str = "") -> str:
                """Execute the skill with provided arguments."""
                try:
                    return manager.invoke_skill(skill_name, arguments)
                except Exception as e:
                    logger.error(f"Error invoking skill '{skill_name}': {e}")
                    return f"Error: {str(e)}"
            return skill_func

        tool = StructuredTool(
            name=skill_metadata.name,
            description=skill_metadata.description,
            func=make_skill_func(skill_metadata.name),
            args_schema=SkillInput
        )

        tools.append(tool)
        logger.debug(f"Created LangChain tool for skill: {skill_metadata.name}")

    logger.info(f"Created {len(tools)} LangChain tools")
    return tools


def create_langchain_tool_from_skill(
    skill_name: str,
    manager: SkillManager
) -> StructuredTool:
    """
    Create a single LangChain tool from a specific skill.

    Args:
        skill_name: Name of the skill
        manager: SkillManager instance

    Returns:
        LangChain StructuredTool

    Raises:
        SkillNotFoundError: If skill doesn't exist
    """
    skill_metadata = manager.get_skill(skill_name)

    def skill_func(arguments: str = "") -> str:
        """Execute the skill with provided arguments."""
        try:
            return manager.invoke_skill(skill_name, arguments)
        except Exception as e:
            logger.error(f"Error invoking skill '{skill_name}': {e}")
            return f"Error: {str(e)}"

    tool = StructuredTool(
        name=skill_metadata.name,
        description=skill_metadata.description,
        func=skill_func,
        args_schema=SkillInput
    )

    logger.debug(f"Created LangChain tool for skill: {skill_name}")
    return tool
```

**Design Notes:**
- Optional dependency: LangChain only loaded if imported
- Two modes: bulk conversion or single skill conversion
- Closure pattern captures skill name for each tool
- Error handling: catch + return error string (agent-friendly)
- Pydantic schema for structured input validation
- Sync-only in v0.1 (async in v0.2)

**Integration Flow:**
1. Skills discovered → metadata loaded
2. Each skill → LangChain `StructuredTool`
3. Tool name = skill name
4. Tool description = skill description
5. Tool invocation → `manager.invoke_skill()`

---

## 8. Exception Hierarchy

### `src/skills_use/exceptions.py`

```python
"""Custom exceptions for skills-use library."""


class SkillsUseError(Exception):
    """Base exception for all skills-use errors."""
    pass


class SkillParsingError(SkillsUseError):
    """Raised when SKILL.md file cannot be parsed."""
    pass


class SkillNotFoundError(SkillsUseError):
    """Raised when requested skill doesn't exist."""
    pass


class SkillInvocationError(SkillsUseError):
    """Raised when skill invocation fails."""
    pass
```

**Design Notes:**
- Base exception: `SkillsUseError` (catch-all)
- Specific exceptions for different failure modes
- Inherits from base Exception (standard pattern)
- Descriptive names indicate error context

**Usage:**
```python
from skills_use.exceptions import SkillNotFoundError

try:
    manager.invoke_skill("nonexistent-skill")
except SkillNotFoundError as e:
    print(f"Skill not found: {e}")
except SkillsUseError as e:
    print(f"General error: {e}")
```

---

## 9. Public API

### `src/skills_use/__init__.py`

```python
"""
skills-use: Python library for LLM agent skills with progressive disclosure.

Basic usage:
    >>> from skills_use import SkillManager
    >>> manager = SkillManager()
    >>> manager.discover()
    >>> skills = manager.list_skills()
    >>> result = manager.invoke_skill("my-skill", "some arguments")

LangChain integration:
    >>> from skills_use.integrations.langchain import create_langchain_tools
    >>> tools = create_langchain_tools()
    >>> # Use tools with LangChain agent
"""

__version__ = "0.1.0"

from skills_use.core.manager import SkillManager
from skills_use.core.models import SkillMetadata, Skill
from skills_use.exceptions import (
    SkillsUseError,
    SkillParsingError,
    SkillNotFoundError,
    SkillInvocationError,
)

__all__ = [
    "SkillManager",
    "SkillMetadata",
    "Skill",
    "SkillsUseError",
    "SkillParsingError",
    "SkillNotFoundError",
    "SkillInvocationError",
]
```

**Design Notes:**
- Clean top-level imports
- Version string for introspection
- Docstring with usage examples
- `__all__` defines public API contract
- Internal modules not exposed (e.g., discovery, parser)

---

## 10. Dependencies

### `pyproject.toml`

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "skills-use"
version = "0.1.0"
description = "Python library for LLM agent skills with progressive disclosure"
authors = [
    {name = "Massimo Olivieri", email = "your.email@example.com"}
]
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.9"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
keywords = ["llm", "agents", "langchain", "anthropic", "skills"]

dependencies = [
    "pyyaml>=6.0",
]

[project.optional-dependencies]
langchain = [
    "langchain-core>=0.1.0",
    "pydantic>=2.0.0",
]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "black>=23.0.0",
    "ruff>=0.1.0",
    "mypy>=1.0.0",
]
all = [
    "skills-use[langchain,dev]",
]

[project.urls]
Homepage = "https://github.com/yourusername/skills-use"
Repository = "https://github.com/yourusername/skills-use"
Issues = "https://github.com/yourusername/skills-use/issues"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "--cov=skills_use --cov-report=term-missing --cov-report=html"

[tool.black]
line-length = 100
target-version = ["py39", "py310", "py311", "py312"]

[tool.ruff]
line-length = 100
target-version = "py39"
select = ["E", "F", "W", "I", "N", "UP"]

[tool.mypy]
python_version = "3.9"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
```

**Core Dependencies:**
- `pyyaml>=6.0` - YAML frontmatter parsing

**Optional Dependencies:**
- `langchain` extra: langchain-core, pydantic
- `dev` extra: pytest, coverage, linting, type checking
- `all` extra: everything

**Python Support:** 3.10+ (modern but not bleeding-edge)

**Installation:**
```bash
pip install skills-use              # Core only
pip install skills-use[langchain]   # With LangChain
pip install skills-use[dev]         # Development
pip install skills-use[all]         # Everything
```

---

## 11. API Usage Examples

### 11.1 Standalone Usage (No Framework)

```python
from skills_use import SkillManager

# Initialize and discover skills
manager = SkillManager()
manager.discover()

# List all skills
skills = manager.list_skills()
for skill in skills:
    print(f"{skill.name}: {skill.description}")

# Output:
# code-reviewer: Reviews Python code for common mistakes
# markdown-formatter: Formats markdown documents

# Invoke a skill
result = manager.invoke_skill(
    "code-reviewer",
    "Review this function for bugs:\ndef foo(x): return x/0"
)
print(result)

# Output:
# Base directory for this skill: /Users/.../code-reviewer
#
# Review the provided code for common errors...
#
# ARGUMENTS: Review this function for bugs:
# def foo(x): return x/0
```

### 11.2 LangChain Integration

```python
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from skills_use.integrations.langchain import create_langchain_tools

# Create skills as LangChain tools
tools = create_langchain_tools()

# Setup LangChain agent
llm = ChatOpenAI(model="gpt-4", temperature=0)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant. Use skills when appropriate."),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Use agent
result = agent_executor.invoke({
    "input": "Review my Python code for common mistakes"
})
print(result)
```

### 11.3 Custom Skills Directory

```python
from pathlib import Path
from skills_use import SkillManager

# Use custom directory
manager = SkillManager(skills_directory=Path("./my-custom-skills"))
manager.discover()

skills = manager.list_skills()
```

### 11.4 Error Handling

```python
from skills_use import SkillManager
from skills_use.exceptions import SkillNotFoundError, SkillParsingError

manager = SkillManager()

try:
    manager.discover()
    result = manager.invoke_skill("nonexistent-skill", "test")
except SkillNotFoundError as e:
    print(f"Skill not found: {e}")
except SkillParsingError as e:
    print(f"Failed to parse skill: {e}")
```

---

## 12. Key Design Decisions

### 12.1 Progressive Disclosure Pattern

**Decision:** Separate metadata loading from content loading

**Rationale:**
- Discovery phase loads only frontmatter (name, description, allowed_tools)
- Full content loaded only during invocation
- Minimizes memory and startup time for large skill collections
- Aligns with Anthropic's agent skills philosophy

**Implementation:**
- `SkillMetadata` for lightweight listing (discovery phase)
- `Skill` for full content + invocation (execution phase)
- `SkillManager.list_skills()` returns metadata only
- `SkillManager.load_skill()` loads full content on-demand

**Benefits:**
- Fast discovery: ~100ms for 100 skills (target)
- Low memory footprint: ~1-5KB per skill metadata
- Scales to large skill libraries

---

### 12.2 Framework-Agnostic Core

**Decision:** Core modules have zero framework dependencies

**Rationale:**
- Enables standalone usage without any agent framework
- Makes testing easier (no framework mocking required)
- Supports future framework integrations without core changes
- Reduces maintenance burden (framework updates don't break core)

**Implementation:**
- `core/` modules only depend on stdlib + pyyaml
- Framework integrations in separate `integrations/` package
- Optional dependencies declared in pyproject.toml extras
- Import guards in integration modules

**Package Structure:**
```python
# Core: No framework dependencies
from skills_use import SkillManager

# Integrations: Optional dependencies
from skills_use.integrations.langchain import create_langchain_tools  # Requires langchain
from skills_use.integrations.llamaindex import create_llamaindex_tools  # Future: v1.1
```

---

### 12.3 Error Handling Strategy

**Decision:** Graceful degradation during discovery, strict during invocation

**Rationale:**
- Discovery: Bad skill files shouldn't prevent discovery of other skills
- Invocation: Errors should be explicit for debugging
- Balance between robustness and clarity

**Implementation:**

**Discovery (graceful):**
```python
for skill_path in skill_paths:
    try:
        metadata = self.parser.parse_skill_file(skill_path)
        self._skills[metadata.name] = metadata
    except Exception as e:
        logger.error(f"Failed to parse skill at {skill_path}: {e}")
        # Continue processing other skills
```

**Invocation (strict):**
```python
def get_skill(self, name: str) -> SkillMetadata:
    if name not in self._skills:
        raise SkillNotFoundError(f"Skill '{name}' not found")
    return self._skills[name]
```

**Exception Hierarchy:**
- `SkillsUseError` - Base class
- `SkillParsingError` - Malformed SKILL.md
- `SkillNotFoundError` - Skill doesn't exist
- `SkillInvocationError` - Runtime failure (future)

---

### 12.4 $ARGUMENTS Resolution (OP-5)

**Decision:** Replace all occurrences, append if missing

**Problem:** How to handle edge cases in argument substitution?
1. Multiple `$ARGUMENTS` placeholders
2. Empty arguments string
3. No placeholder but arguments provided
4. No placeholder and no arguments

**Solution (Implemented in `invocation.py`):**

```python
if ARGUMENTS_PLACEHOLDER in processed_content:
    # Case 1 & 2: Replace all occurrences (including with empty string)
    processed_content = processed_content.replace(ARGUMENTS_PLACEHOLDER, arguments)
elif arguments:
    # Case 3: No placeholder but arguments provided - append
    processed_content += f"\n\nARGUMENTS: {arguments}"
# Case 4: No placeholder, no arguments - no modification
```

**Rationale:**
- **Maximize flexibility:** Skill authors can use multiple placeholders if needed
- **Predictable behavior:** No magic or heuristics
- **Explicit handling:** Each edge case has defined behavior
- **Backward compatible:** Matches Anthropic's behavior

**Examples:**

| Skill Content | Arguments | Result |
|---------------|-----------|--------|
| `Review: $ARGUMENTS` | `"code"` | `Review: code` |
| `$ARGUMENTS\n\n$ARGUMENTS` | `"test"` | `test\n\ntest` |
| `$ARGUMENTS` | `""` | `` (empty) |
| `Review code` | `"def foo()"` | `Review code\n\nARGUMENTS: def foo()` |
| `Review code` | `""` | `Review code` |

**Case Sensitivity:** Only exact `$ARGUMENTS` replaced (not `$arguments` or `$Arguments`)

---

### 12.5 Single Skills Directory (v0.1)

**Decision:** Hardcode `~/.claude/skills/` for v0.1

**Rationale:**
- **Anthropic compatibility:** Matches Claude Code behavior exactly
- **Reduces scope:** Multiple search paths deferred to v0.2
- **Enables validation:** Can test with existing Anthropic skills
- **Simplifies testing:** Single path = easier test fixtures

**Future Extensions (v0.2+):**
- `./skills/` (project-local skills)
- Custom paths via environment variable
- Plugin discovery from `~/.claude/plugins/`
- Priority ordering for name conflicts

---

### 12.6 No Caching (v0.1)

**Decision:** Reload skill content on each invocation

**Rationale:**
- **Simplicity:** No cache invalidation logic needed
- **Acceptable performance:** File I/O is fast for small files (<50KB)
- **Enables editing:** Users can modify skills without restart
- **Reduces scope:** Caching deferred to v0.3 optimization phase

**Performance Impact (v0.1):**
- Invocation overhead: ~10-20ms (dominated by file I/O)
- Acceptable for typical agent workflows (invocations are infrequent)

**Future Optimization (v0.3):**
- TTL-based content caching
- File watcher for invalidation
- Benchmark: <10ms invocation overhead

---

### 12.7 Sync-Only LangChain (v0.1)

**Decision:** Implement `func` only, not `afunc` (async)

**Rationale:**
- **Reduces complexity:** Async requires careful error handling
- **Acceptable limitation:** Most LangChain agents use sync patterns
- **Phased delivery:** Async support added in v0.2 after validation

**Implementation:**
```python
tool = StructuredTool(
    name=skill_metadata.name,
    description=skill_metadata.description,
    func=skill_func,  # Sync only in v0.1
    args_schema=SkillInput
)
```

**Future Enhancement (v0.2):**
```python
async def async_skill_func(arguments: str = "") -> str:
    return await manager.ainvoke_skill(skill_name, arguments)

tool = StructuredTool(
    name=skill_metadata.name,
    func=skill_func,
    afunc=async_skill_func,  # Add async support
    args_schema=SkillInput
)
```

---

## 13. Testing Strategy

### 13.1 Test Coverage Goals

**v0.1 Target:** 70%+ coverage
**v0.2 Target:** 85%+ coverage
**v1.0 Target:** 90%+ coverage

**Focus Areas (v0.1):**
- ✅ Core discovery logic (happy path + missing directory)
- ✅ SKILL.md parsing (valid + missing fields)
- ✅ Invocation with $ARGUMENTS edge cases
- ✅ LangChain integration (end-to-end)
- ❌ Edge case testing (deferred to v0.2)
- ❌ Performance testing (deferred to v0.3)

---

### 13.2 Test Structure

```
tests/
├── test_discovery.py      # SkillDiscovery tests
├── test_parser.py         # SkillParser tests
├── test_invocation.py     # process_skill_content tests
├── test_manager.py        # SkillManager tests
├── test_langchain.py      # LangChain integration tests
└── fixtures/
    └── skills/
        ├── valid-skill/
        │   └── SKILL.md
        ├── missing-name-skill/
        │   └── SKILL.md
        └── invalid-yaml-skill/
            └── SKILL.md
```

---

### 13.3 Test Cases by Module

#### `test_discovery.py`

```python
def test_discover_skills_from_directory()
    """Test successful discovery of skills."""

def test_discover_empty_directory()
    """Test discovery in empty skills directory."""

def test_discover_missing_directory()
    """Test discovery when directory doesn't exist."""

def test_discover_case_insensitive_skill_md()
    """Test SKILL.md, skill.md, Skill.md all discovered."""

def test_discover_flat_structure_only()
    """Test that nested directories are ignored in v0.1."""
```

#### `test_parser.py`

```python
def test_parse_valid_skill()
    """Test parsing valid SKILL.md with all fields."""

def test_parse_missing_name_field()
    """Test SkillParsingError when name is missing."""

def test_parse_missing_description_field()
    """Test SkillParsingError when description is missing."""

def test_parse_invalid_yaml()
    """Test SkillParsingError on malformed YAML."""

def test_parse_no_frontmatter()
    """Test SkillParsingError when --- delimiters missing."""

def test_extract_allowed_tools()
    """Test parsing allowed-tools list."""

def test_load_full_content()
    """Test loading markdown content without frontmatter."""
```

#### `test_invocation.py`

```python
def test_invoke_with_arguments_placeholder()
    """Test $ARGUMENTS replacement."""

def test_invoke_without_placeholder()
    """Test ARGUMENTS appending when no placeholder."""

def test_invoke_multiple_arguments_placeholders()
    """Test replacing multiple $ARGUMENTS."""

def test_invoke_empty_arguments()
    """Test $ARGUMENTS replaced with empty string."""

def test_invoke_no_arguments()
    """Test content unchanged when no placeholder and no args."""

def test_base_directory_injection()
    """Test base directory always injected."""
```

#### `test_manager.py`

```python
def test_list_skills()
    """Test listing all discovered skills."""

def test_get_skill_by_name()
    """Test retrieving specific skill metadata."""

def test_get_skill_not_found()
    """Test SkillNotFoundError when skill doesn't exist."""

def test_load_skill_full_content()
    """Test loading full Skill object with content."""

def test_invoke_skill()
    """Test end-to-end skill invocation."""

def test_auto_discover_on_first_call()
    """Test lazy initialization when discover() not called."""
```

#### `test_langchain.py` (Integration)

```python
def test_create_langchain_tools()
    """Test creating LangChain tools from skills."""

def test_langchain_tool_invocation()
    """Test invoking skill via LangChain tool."""

def test_langchain_tool_with_arguments()
    """Test passing arguments through LangChain tool."""

def test_langchain_agent_end_to_end()
    """Test full agent workflow with skills (integration test)."""

def test_langchain_tool_error_handling()
    """Test graceful error handling in tool invocation."""
```

---

### 13.4 Test Fixtures

#### Example Valid Skill: `fixtures/skills/code-reviewer/SKILL.md`

```markdown
---
name: code-reviewer
description: Reviews Python code for common mistakes
allowed-tools: Read, Grep
---

You are a code reviewer. Review the following code for:
- Syntax errors
- Logic bugs
- Style issues

Code to review: $ARGUMENTS
```

#### Example Invalid Skill: `fixtures/skills/missing-name/SKILL.md`

```markdown
---
description: Missing name field
---

This skill has no name field.
```

---

### 13.5 Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=skills_use --cov-report=term-missing

# Run specific test file
pytest tests/test_discovery.py

# Run specific test
pytest tests/test_invocation.py::test_invoke_with_arguments_placeholder

# Generate HTML coverage report
pytest --cov=skills_use --cov-report=html
open htmlcov/index.html
```

---

### 13.6 CI/CD (Not in v0.1)

**Deferred to v0.2:**
- GitHub Actions workflow
- Automated testing on push/PR
- Multi-version Python testing (3.10, 3.11, 3.12)
- Coverage reporting
- PyPI publishing automation

**v0.1 Testing:** Manual `pytest` execution

---

## 14. Performance Considerations (v0.1)

### 14.1 Not Optimized Yet (Acceptable for v0.1)

- ❌ **No caching:** Content reloaded on each invocation
- ❌ **No lazy loading optimization:** All metadata loaded upfront
- ❌ **No concurrent discovery:** Sequential filesystem scanning
- ❌ **No benchmark requirements:** Performance not measured

### 14.2 Performance Expectations

**Discovery Phase:**
- Expected: <500ms for 10 skills (acceptable, not measured)
- Dominated by: Filesystem I/O + YAML parsing
- Acceptable: v0.1 users unlikely to have >20 skills

**Invocation Phase:**
- Expected: <50ms overhead (file I/O dominates)
- Breakdown:
  - File read: ~5-10ms
  - YAML parsing: ~5-10ms (frontmatter only)
  - Content processing: ~1-5ms (string operations)
  - Total: ~10-25ms
- Acceptable: LLM inference (seconds) dominates total latency

**Memory Usage:**
- Metadata: ~1-5KB per skill
- 100 skills = ~100-500KB (negligible)
- Content not cached, so minimal memory footprint

### 14.3 Future Optimization (v0.3)

**Content Caching:**
```python
from functools import lru_cache
from datetime import datetime, timedelta

class SkillManager:
    def __init__(self):
        self._content_cache = {}  # skill_name -> (content, timestamp)
        self._cache_ttl = timedelta(minutes=5)

    def load_skill(self, name: str) -> Skill:
        if name in self._content_cache:
            content, timestamp = self._content_cache[name]
            if datetime.now() - timestamp < self._cache_ttl:
                logger.debug(f"Cache hit: {name}")
                return self._create_skill(name, content)

        # Cache miss: load from disk
        content = self.parser.load_full_content(...)
        self._content_cache[name] = (content, datetime.now())
        return self._create_skill(name, content)
```

**Parallel Discovery:**
```python
from concurrent.futures import ThreadPoolExecutor

def discover_skills(self) -> List[Path]:
    skill_dirs = [d for d in self.skills_directory.iterdir() if d.is_dir()]

    with ThreadPoolExecutor(max_workers=4) as executor:
        skill_files = executor.map(self._find_skill_file, skill_dirs)

    return [f for f in skill_files if f is not None]
```

**Performance Targets (v0.3):**
- Discovery: <100ms for 100 skills
- Invocation: <10ms overhead (with caching)
- Memory: <50MB for 1000 skills

---

## 15. Security Considerations (v0.1)

### 15.1 Implemented in v0.1

✅ **YAML Safe Loading**
```python
frontmatter = yaml.safe_load(frontmatter_raw)  # Prevents code execution
```

✅ **UTF-8 Encoding Enforcement**
```python
content = skill_path.read_text(encoding="utf-8")  # Explicit encoding
```

✅ **Exception Handling**
```python
try:
    metadata = self.parser.parse_skill_file(skill_path)
except Exception as e:
    logger.error(f"Failed to parse skill: {e}")
    # Continue processing other skills
```

✅ **Input Validation**
```python
if not self.name:
    raise ValueError("Skill name is required")
```

---

### 15.2 Deferred to v0.2+

❌ **Path Traversal Prevention**
- Risk: Skill could reference files outside skill directory
- Mitigation (v0.2): Validate all file paths stay within `base_directory`
```python
def validate_path(self, requested_path: Path) -> Path:
    resolved = requested_path.resolve()
    if not resolved.is_relative_to(self.base_directory):
        raise SecurityError(f"Path traversal detected: {requested_path}")
    return resolved
```

❌ **Tool Restriction Enforcement**
- Risk: Skill could invoke dangerous tools
- Mitigation (v0.2): Parse `allowed-tools` and enforce in framework integrations
```python
if tool_name not in skill.metadata.allowed_tools:
    raise ToolNotAllowedError(f"Skill '{skill.name}' cannot use tool '{tool_name}'")
```

❌ **File Access Validation**
- Risk: Malicious skill could read sensitive files
- Mitigation (v0.2): Sandboxed file access with allowlist

❌ **Script Execution Sandboxing**
- Risk: Skills with embedded scripts could execute arbitrary code
- Mitigation (v0.3): Execute scripts in restricted subprocess with timeout

---

### 15.3 Security Principles

**v0.1 Philosophy:** Trust but verify
- Skills sourced from user's local filesystem
- User controls `~/.claude/skills/` directory
- No network access or remote skill loading
- YAML parsing is safe (no code execution)

**Future Hardening (v0.2+):**
- Defense in depth: Multiple security layers
- Principle of least privilege: Restrict tool access
- Fail-safe defaults: Deny by default
- Audit logging: Track skill invocations

---

## 16. Implementation Checklist

### Week 1: Core Foundation (24 hours)

- [ ] Create project structure
  - [ ] `src/skills_use/` package
  - [ ] `tests/` directory
  - [ ] `pyproject.toml`
  - [ ] `.gitignore`

- [ ] Implement `models.py` (2 hours)
  - [ ] `SkillMetadata` dataclass
  - [ ] `Skill` dataclass
  - [ ] Validation in `__post_init__`

- [ ] Implement `exceptions.py` (1 hour)
  - [ ] `SkillsUseError`
  - [ ] `SkillParsingError`
  - [ ] `SkillNotFoundError`
  - [ ] `SkillInvocationError`

- [ ] Implement `discovery.py` (4 hours)
  - [ ] `SkillDiscovery` class
  - [ ] `discover_skills()` method
  - [ ] `_find_skill_file()` helper
  - [ ] Tests in `test_discovery.py`

- [ ] Implement `parser.py` (6 hours)
  - [ ] `SkillParser` class
  - [ ] `parse_skill_file()` method
  - [ ] `_extract_frontmatter()` helper
  - [ ] `load_full_content()` method
  - [ ] Tests in `test_parser.py`

- [ ] Implement `manager.py` (4 hours)
  - [ ] `SkillManager` class
  - [ ] `discover()`, `list_skills()`, `get_skill()` methods
  - [ ] `load_skill()`, `invoke_skill()` methods
  - [ ] Tests in `test_manager.py`

- [ ] Implement `invocation.py` (6 hours)
  - [ ] `process_skill_content()` function
  - [ ] $ARGUMENTS substitution logic
  - [ ] Base directory injection
  - [ ] Tests in `test_invocation.py`

- [ ] Implement `__init__.py` (1 hour)
  - [ ] Public API exports
  - [ ] Version string
  - [ ] Docstrings

### Week 2: LangChain Integration (12 hours)

- [ ] Implement `integrations/langchain.py` (8 hours)
  - [ ] `SkillInput` Pydantic model
  - [ ] `create_langchain_tools()` function
  - [ ] `create_langchain_tool_from_skill()` helper
  - [ ] Error handling in tool invocation
  - [ ] Tests in `test_langchain.py`

- [ ] Integration testing (4 hours)
  - [ ] End-to-end LangChain agent test
  - [ ] Create test skill fixtures
  - [ ] Verify argument passing
  - [ ] Test error scenarios

### Week 3: Testing & Examples (10 hours)

- [ ] Comprehensive testing (6 hours)
  - [ ] Achieve 70%+ coverage
  - [ ] Add edge case tests
  - [ ] Fix bugs discovered in testing
  - [ ] Run pytest-cov

- [ ] Create example skills (4 hours)
  - [ ] `code-reviewer` skill
  - [ ] `markdown-formatter` skill
  - [ ] Test manually with library

### Week 4: Documentation & Publishing (14 hours)

- [ ] Write README.md (6 hours)
  - [ ] Installation instructions
  - [ ] Quick start example
  - [ ] Standalone usage example
  - [ ] LangChain integration guide
  - [ ] Creating skills guide
  - [ ] Troubleshooting section

- [ ] Prepare for PyPI (4 hours)
  - [ ] Finalize pyproject.toml
  - [ ] Add LICENSE file (MIT)
  - [ ] Test package build
  - [ ] Test installation in clean environment

- [ ] Publish v0.1.0 (2 hours)
  - [ ] Publish to PyPI
  - [ ] Create GitHub release
  - [ ] Tag v0.1.0

- [ ] Announce (2 hours)
  - [ ] Write announcement post
  - [ ] Post on Reddit (r/LangChain, r/LocalLLaMA)
  - [ ] Post on Twitter/LinkedIn
  - [ ] Email beta testers

---

## 17. Next Steps

### Immediate Actions

1. **Review this specification** - Ensure alignment with MVP plan
2. **Setup development environment**
   - Python 3.10+ virtual environment
   - Install dev dependencies
   - Configure IDE (VSCode/PyCharm)
3. **Create project structure** - Initialize repository
4. **Begin Week 1 implementation** - Start with `models.py` and `exceptions.py`

### Open Questions

None at this stage - all architectural decisions made for v0.1.

---

**Document Version:** 1.0
**Last Updated:** October 28, 2025
**Status:** Implementation Ready
**Approved By:** Massimo Olivieri

---

This specification provides a complete blueprint for implementing skills-use v0.1 MVP, with all class designs, API signatures, and architectural decisions needed to begin development immediately.
