# Public API Contract: skillkit v0.1 MVP

**Feature**: Core Functionality & LangChain Integration
**Branch**: `001-mvp-langchain-core`
**Date**: November 4, 2025

## Overview

This document defines the complete public API contract for the skillkit library v0.1, including type signatures, method specifications, exception handling, and usage examples. All public APIs are subject to semantic versioning guarantees.

---

## Core API (`skillkit.core`)

### SkillManager Class

**Module**: `skillkit.core.manager`

**Purpose**: Central registry for skill discovery, access, and invocation.

```python
from pathlib import Path
from typing import List

class SkillManager:
    """Central skill registry with discovery and invocation capabilities.

    Thread-safety: Not guaranteed in v0.1 (single-threaded usage assumed)
    Discovery: Graceful degradation (log errors, continue)
    Invocation: Strict validation (raise exceptions)
    """

    def __init__(self, skills_dir: Path | None = None) -> None:
        """Initialize skill manager.

        Args:
            skills_dir: Path to skills directory.
                       Default: Path.home() / ".claude" / "skills"

        Example:
            >>> from pathlib import Path
            >>> manager = SkillManager()  # Uses ~/.claude/skills/
            >>> custom_manager = SkillManager(Path("/custom/skills"))
        """

    def discover(self) -> None:
        """Discover skills from skills_dir (graceful degradation).

        Behavior:
            - Scans skills_dir for subdirectories containing SKILL.md files
            - Parses YAML frontmatter and validates required fields
            - Continues processing even if individual skills fail parsing
            - Logs errors via module logger (skillkit.core.manager)
            - Handles duplicates: first discovered wins, logs WARNING

        Side Effects:
            - Populates internal _skills registry
            - Logs errors for malformed skills
            - Logs INFO if directory empty
            - Logs WARNING for duplicate skill names

        Raises:
            No exceptions raised (graceful degradation)

        Performance:
            - Target: <500ms for 10 skills
            - Actual: ~5-10ms per skill (dominated by YAML parsing)

        Example:
            >>> manager = SkillManager()
            >>> manager.discover()
            >>> print(f"Found {len(manager.list_skills())} skills")
            Found 5 skills
        """

    def list_skills(self) -> List['SkillMetadata']:
        """Return all discovered skill metadata (lightweight).

        Returns:
            List of SkillMetadata instances (metadata only, no content)

        Performance:
            - O(n) where n = number of skills
            - Copies internal list (~1-5ms for 100 skills)

        Example:
            >>> skills = manager.list_skills()
            >>> for skill in skills:
            ...     print(f"{skill.name}: {skill.description}")
            code-reviewer: Review code for best practices
            git-helper: Generate commit messages
        """

    def get_skill(self, name: str) -> 'SkillMetadata':
        """Get skill metadata by name (strict validation).

        Args:
            name: Skill name (case-sensitive)

        Returns:
            SkillMetadata instance

        Raises:
            SkillNotFoundError: If skill name not in registry

        Performance:
            - O(1) dictionary lookup (~1μs)

        Example:
            >>> metadata = manager.get_skill("code-reviewer")
            >>> print(metadata.description)
            Review code for best practices

            >>> manager.get_skill("nonexistent")
            SkillNotFoundError: Skill 'nonexistent' not found
        """

    def load_skill(self, name: str) -> 'Skill':
        """Load full skill instance (content loaded lazily).

        Args:
            name: Skill name (case-sensitive)

        Returns:
            Skill instance (content not yet loaded)

        Raises:
            SkillNotFoundError: If skill name not in registry

        Performance:
            - O(1) lookup + Skill instantiation (~10-50μs)
            - Content NOT loaded until .content property accessed

        Example:
            >>> skill = manager.load_skill("code-reviewer")
            >>> # Content not loaded yet
            >>> processed = skill.invoke("review main.py")
            >>> # Content loaded and processed
        """

    def invoke_skill(self, name: str, arguments: str = "") -> str:
        """Load and invoke skill in one call (convenience method).

        Args:
            name: Skill name (case-sensitive)
            arguments: User-provided arguments for skill invocation

        Returns:
            Processed skill content (with base directory + argument substitution)

        Raises:
            SkillNotFoundError: If skill name not in registry
            ContentLoadError: If skill file cannot be read
            ArgumentProcessingError: If argument processing fails
            SizeLimitExceededError: If arguments exceed 1MB

        Performance:
            - Total: ~10-25ms overhead
            - Breakdown: File I/O ~10-20ms + processing ~1-5ms

        Example:
            >>> result = manager.invoke_skill("code-reviewer", "review main.py")
            >>> print(result[:100])
            Base directory for this skill: /Users/alice/.claude/skills/code-reviewer

            Review the following code: review main.py
        """
```

---

### SkillMetadata Dataclass

**Module**: `skillkit.core.models`

**Purpose**: Lightweight skill metadata for browsing and selection.

```python
from dataclasses import dataclass, field
from pathlib import Path

@dataclass(frozen=True, slots=True)
class SkillMetadata:
    """Lightweight skill metadata loaded during discovery phase.

    Memory: ~400-800 bytes per instance (Python 3.10+)
    Immutability: frozen=True prevents accidental mutation
    Optimization: slots=True reduces memory by 60%
    """

    name: str
    """Unique skill identifier (from YAML frontmatter)."""

    description: str
    """Human-readable description of skill purpose."""

    skill_path: Path
    """Absolute path to SKILL.md file."""

    allowed_tools: tuple[str, ...] = field(default_factory=tuple)
    """Tool names allowed for this skill (optional, not enforced in v0.1)."""

    def __post_init__(self) -> None:
        """Validate skill path exists on construction.

        Raises:
            ValueError: If skill_path does not exist
        """
```

**Usage Example**:
```python
>>> from pathlib import Path
>>> from skillkit.core.models import SkillMetadata

>>> metadata = SkillMetadata(
...     name="code-reviewer",
...     description="Review code for best practices",
...     skill_path=Path("/path/to/SKILL.md"),
...     allowed_tools=("read", "grep")
... )

>>> print(f"{metadata.name}: {metadata.description}")
code-reviewer: Review code for best practices

>>> # Immutable - cannot modify
>>> metadata.name = "new-name"
AttributeError: can't set attribute
```

---

### Skill Dataclass

**Module**: `skillkit.core.models`

**Purpose**: Full skill with lazy-loaded content and invocation capabilities.

```python
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

@dataclass(frozen=True, slots=True)  # slots=True requires Python 3.10+
class Skill:
    """Full skill with lazy-loaded content.

    Memory: ~400-800 bytes wrapper + ~50-200KB content (when loaded)
    Content Loading: On-demand via @cached_property
    Processing: Via CompositeProcessor (base directory + arguments)

    Note: For Python 3.9, remove slots=True from this class only.
          SkillMetadata retains slots for memory optimization.
    """

    metadata: 'SkillMetadata'
    """Lightweight metadata from discovery phase."""

    base_directory: Path
    """Base directory context for skill execution."""

    _processor: 'CompositeProcessor' = field(init=False, repr=False)
    """Content processor chain (initialized in __post_init__)."""

    def __post_init__(self) -> None:
        """Initialize processor chain (avoids inline imports anti-pattern).

        Side Effects:
            - Creates CompositeProcessor with BaseDirectoryProcessor + ArgumentSubstitutionProcessor
        """

    @cached_property
    def content(self) -> str:
        """Lazy load content only when accessed.

        Returns:
            Full SKILL.md markdown content (UTF-8 encoded)

        Raises:
            ContentLoadError: If file cannot be read (deleted, permissions, encoding)

        Performance:
            - First access: ~10-20ms (file I/O)
            - Subsequent: <1μs (cached)

        Example:
            >>> skill = manager.load_skill("code-reviewer")
            >>> # Content not loaded yet
            >>> text = skill.content
            >>> # Content loaded and cached
            >>> text2 = skill.content
            >>> # Instant (cached)
        """

    def invoke(self, arguments: str = "") -> str:
        """Process skill content with arguments.

        Args:
            arguments: User-provided arguments for skill invocation

        Returns:
            Processed skill content with base directory + argument substitution

        Raises:
            ContentLoadError: If content cannot be loaded
            ArgumentProcessingError: If argument processing fails
            SizeLimitExceededError: If arguments exceed 1MB

        Processing Steps:
            1. Load content (lazy, cached)
            2. Inject base directory at beginning
            3. Replace $ARGUMENTS placeholders with actual arguments
            4. Return processed string

        Performance:
            - First invocation: ~10-25ms (includes content loading)
            - Subsequent: ~1-5ms (content cached, only processing)

        Example:
            >>> skill = manager.load_skill("code-reviewer")
            >>> result = skill.invoke("review main.py")
            >>> print(result[:80])
            Base directory for this skill: /Users/alice/.claude/skills/code-reviewer
        """
```

---

### Exception Hierarchy

**Module**: `skillkit.core.exceptions`

**Purpose**: Comprehensive exception types for specific error handling.

```python
class SkillsUseError(Exception):
    """Base exception for all skillkit errors.

    Usage: Catch this to handle any library error
    """

class SkillParsingError(SkillsUseError):
    """Base exception for skill parsing errors."""

class InvalidYAMLError(SkillParsingError):
    """YAML syntax error in skill frontmatter.

    Attributes:
        line (int | None): Line number of error (if available)
        column (int | None): Column number of error (if available)
    """

class MissingRequiredFieldError(SkillParsingError):
    """Required field missing or empty in frontmatter.

    Attributes:
        field_name (str | None): Name of missing field
    """

class InvalidFrontmatterError(SkillParsingError):
    """Frontmatter structure invalid (missing delimiters, non-dict, etc.)."""

class SkillNotFoundError(SkillsUseError):
    """Skill name not found in registry."""

class SkillInvocationError(SkillsUseError):
    """Base exception for invocation errors."""

class ArgumentProcessingError(SkillInvocationError):
    """Argument substitution failed."""

class ContentLoadError(SkillInvocationError):
    """Failed to read skill content file."""

class SkillSecurityError(SkillsUseError):
    """Base exception for security-related errors."""

class SuspiciousInputError(SkillSecurityError):
    """Detected potentially malicious input patterns."""

class SizeLimitExceededError(SkillSecurityError):
    """Input exceeds size limits (1MB)."""
```

**Usage Examples**:
```python
from skillkit.core.exceptions import (
    SkillsUseError,
    SkillNotFoundError,
    ContentLoadError,
    SizeLimitExceededError
)

# Catch all library errors
try:
    result = manager.invoke_skill("my-skill", args)
except SkillsUseError as e:
    print(f"Skill operation failed: {e}")

# Catch specific errors
try:
    result = manager.invoke_skill("my-skill", args)
except SkillNotFoundError:
    print("Skill not found. Check skill name.")
except ContentLoadError:
    print("Skill file was deleted or is unreadable.")
except SizeLimitExceededError:
    print("Arguments too large (max 1MB).")
```

---

## LangChain Integration API (`skillkit.integrations.langchain`)

### create_langchain_tools Function

**Module**: `skillkit.integrations.langchain`

**Purpose**: Convert discovered skills into LangChain StructuredTool objects.

```python
from typing import List
from langchain_core.tools import StructuredTool

def create_langchain_tools(manager: 'SkillManager') -> List[StructuredTool]:
    """Create LangChain StructuredTool objects from discovered skills.

    Note: Tools use synchronous invocation. When used in async agents,
    LangChain automatically wraps calls in asyncio.to_thread() with
    ~1-2ms overhead. For native async support, see v0.2.

    CRITICAL PATTERN: Uses default parameter (skill_name=skill_metadata.name)
    to capture the skill name at function creation time. This prevents Python's
    late-binding closure issue where all functions would reference the final
    loop value.

    Args:
        manager: SkillManager instance with discovered skills

    Returns:
        List of StructuredTool objects ready for agent use

    Example:
        >>> from skillkit import SkillManager
        >>> from skillkit.integrations.langchain import create_langchain_tools

        >>> manager = SkillManager()
        >>> manager.discover()

        >>> tools = create_langchain_tools(manager)
        >>> print(f"Created {len(tools)} tools")
        Created 5 tools

        >>> # Use with LangChain agent
        >>> from langchain.agents import create_react_agent
        >>> from langchain_openai import ChatOpenAI

        >>> llm = ChatOpenAI(model="gpt-4")
        >>> agent = create_react_agent(llm, tools)
    """
```

---

### SkillInput Pydantic Model

**Module**: `skillkit.integrations.langchain`

**Purpose**: Pydantic schema for LangChain tool input validation.

```python
from pydantic import BaseModel, ConfigDict, Field

class SkillInput(BaseModel):
    """Pydantic schema for skill tool input.

    Configuration:
        - str_strip_whitespace: True (automatically strips leading/trailing whitespace)

    Fields:
        - arguments: String input for skill invocation (default: empty string)
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    arguments: str = Field(
        default="",
        description="Arguments to pass to the skill"
    )
```

**Usage Example**:
```python
>>> from skillkit.integrations.langchain import SkillInput

>>> input_data = SkillInput(arguments="  review main.py  ")
>>> print(repr(input_data.arguments))
'review main.py'  # Whitespace stripped automatically
```

---

## Import Guards (Optional Dependencies)

**LangChain Integration**: Requires `pip install skillkit[langchain]`

```python
# In skillkit/integrations/langchain.py
try:
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, ConfigDict, Field
except ImportError as e:
    raise ImportError(
        "LangChain integration requires additional dependencies. "
        "Install with: pip install skillkit[langchain]"
    ) from e
```

**User Code Pattern**:
```python
# Check availability before importing
try:
    from skillkit.integrations import langchain
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False

if HAS_LANGCHAIN:
    tools = langchain.create_langchain_tools(manager)
else:
    print("LangChain not available. Install with: pip install skillkit[langchain]")
```

---

## Logging Configuration

**NullHandler Setup** (Python library standard):

```python
# In skillkit/__init__.py
import logging

# Add NullHandler to prevent "No handlers found" warnings
logging.getLogger(__name__).addHandler(logging.NullHandler())
```

**Application Configuration** (user responsibility):

```python
import logging

# Configure skillkit logging
logging.getLogger('skillkit').setLevel(logging.INFO)

# Enable debug for discovery only
logging.getLogger('skillkit.core.discovery').setLevel(logging.DEBUG)

# Add handler to see logs
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
logging.getLogger('skillkit').addHandler(handler)
```

**Logging Levels**:
- **DEBUG**: Individual skill discoveries, successful parsing, pre-exception diagnostics
- **INFO**: Discovery complete (count), major operations, empty skill directory
- **WARNING**: Recoverable issues (malformed allowed-tools field, suspicious patterns, duplicate skill names)
- **ERROR**: Parsing failures, missing required fields (uses `logger.exception()` in except blocks)

---

## Performance Characteristics

### Discovery Phase
- **Target**: <500ms for 10 skills
- **Actual**: ~5-10ms per skill (dominated by YAML parsing)
- **Scalability**: Linear O(n) with number of skills

### Invocation Phase
- **Overhead**: ~10-25ms total
- **Breakdown**: File I/O ~10-20ms + string processing ~1-5ms
- **First vs subsequent**: First invocation loads content (~10-20ms), subsequent cached (<1μs content access + ~1-5ms processing)

### Memory Usage
- **Metadata**: ~400-800 bytes per SkillMetadata (Python 3.10+)
- **Skill wrapper**: ~400-800 bytes per Skill instance (Python 3.10+)
- **Content**: ~50-200KB per skill (only when loaded)
- **Total (100 skills, 10% usage)**: ~2-2.5MB (80% reduction vs eager loading)

---

## Python Version Support

**Python 3.10+ (Recommended)**:
- Full `slots=True` support on both SkillMetadata and Skill
- Memory: ~2.0MB for 100 skills with 10% usage
- Performance: Optimal

**Python 3.9 (Supported)**:
- `slots=True` on SkillMetadata only (remove from Skill class in implementation)
- Memory: ~2.5MB for 100 skills with 10% usage (~25% increase)
- Performance: Acceptable (still 80% reduction vs eager loading)

**Type Hints**: PEP 604 union syntax (`Path | None`) requires Python 3.10+, but can be replaced with `typing.Union[Path, None]` or `Optional[Path]` for Python 3.9 compatibility.

---

## Security Considerations

**Input Validation**:
- Arguments size limit: 1MB (prevents resource exhaustion)
- UTF-8 encoding enforced (prevents binary exploits)
- Suspicious pattern detection: 9 patterns logged (path traversal, command injection, XSS, YAML injection, etc.)

**YAML Parsing**:
- `yaml.safe_load()` prevents code execution
- No eval/exec in codebase
- Exception chaining preserves stack traces

**Argument Substitution**:
- `string.Template` prevents attribute access vulnerabilities (vs `str.format()`)
- `$$ARGUMENTS` escaping for literal text
- No code execution possible during substitution

---

## Versioning Guarantees

**Semantic Versioning** (v0.1.0):
- **Major** (0): Breaking changes to public API
- **Minor** (1): New features, backward-compatible
- **Patch** (0): Bug fixes, no API changes

**API Stability**:
- ✅ Public classes, methods, and exceptions documented here are stable
- ✅ Private methods (prefixed with `_`) may change without notice
- ✅ Exception hierarchy may expand (new exceptions added) without breaking changes

**Deprecation Policy**:
- Deprecated APIs will be marked with warnings for at least one minor version before removal
- Migration guides provided for breaking changes

---

## Complete Usage Example

```python
#!/usr/bin/env python3
"""Complete example demonstrating all public APIs."""

import logging
from pathlib import Path

from skillkit import SkillManager
from skillkit.integrations.langchain import create_langchain_tools
from skillkit.core.exceptions import (
    SkillNotFoundError,
    ContentLoadError,
    SizeLimitExceededError
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('skillkit')

def main():
    # 1. Create manager with custom skills directory
    skills_dir = Path.home() / ".claude" / "skills"
    manager = SkillManager(skills_dir)

    # 2. Discover skills (graceful degradation)
    manager.discover()
    print(f"Discovered {len(manager.list_skills())} skills")

    # 3. List skills (metadata only)
    for skill_meta in manager.list_skills():
        print(f"- {skill_meta.name}: {skill_meta.description}")

    # 4. Get specific skill metadata
    try:
        meta = manager.get_skill("code-reviewer")
        print(f"\nSelected: {meta.name}")
    except SkillNotFoundError as e:
        print(f"Skill not found: {e}")
        return

    # 5. Invoke skill with arguments
    try:
        result = manager.invoke_skill(
            "code-reviewer",
            "review the function at src/main.py:42"
        )
        print(f"\nResult preview: {result[:200]}...")
    except ContentLoadError:
        print("Skill file was deleted")
    except SizeLimitExceededError:
        print("Arguments too large (max 1MB)")

    # 6. Create LangChain tools
    tools = create_langchain_tools(manager)
    print(f"\nCreated {len(tools)} LangChain tools")
    for tool in tools:
        print(f"- {tool.name}: {tool.description[:60]}...")

    # 7. Use tools with LangChain agent (example)
    # from langchain.agents import create_react_agent
    # from langchain_openai import ChatOpenAI
    # llm = ChatOpenAI(model="gpt-4")
    # agent = create_react_agent(llm, tools)

if __name__ == "__main__":
    main()
```

---

**Document Version**: 1.0
**Date**: November 4, 2025
**Status**: Phase 1 Complete - Ready for implementation
