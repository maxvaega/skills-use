# Research Document: skillkit v0.1 MVP

**Feature**: Core Functionality & LangChain Integration
**Date**: November 3, 2025
**Status**: Complete

## Overview

This document consolidates research findings and architectural decisions for the skillkit v0.1 MVP. All technical decisions are derived from the comprehensive TECH_SPECS.md document which provides detailed implementation blueprints.

---

## Key Architectural Decisions

### Decision 1: Progressive Disclosure Pattern

**Decision**: Separate metadata loading from content loading in two distinct phases using a two-tier dataclass architecture with lazy content loading.

**Rationale**:
- **Discovery phase** loads only YAML frontmatter (name, description, allowed_tools) - ~1-5KB per skill
- **Invocation phase** loads full markdown content only when skill is actually used
- Minimizes memory footprint and startup time for large skill collections (80% reduction: 10MB+ → ~2MB with 10% usage)
- Aligns with Anthropic's agent skills philosophy of efficient context management
- Enables fast browsing of 100+ skills without loading megabytes of content
- Separation of concerns: metadata for discovery, full content for invocation

**Implementation**:

**Two-Tier Dataclass Architecture**:

```python
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

# Tier 1: Lightweight metadata (loaded eagerly for all skills)
@dataclass(frozen=True, slots=True)
class SkillMetadata:
    """Lightweight metadata (~1-5KB) - loaded during discovery."""
    name: str
    description: str
    skill_path: Path
    allowed_tools: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        """Validate on construction."""
        if not self.skill_path.exists():
            raise ValueError(f"Skill path does not exist: {self.skill_path}")

# Tier 2: Full skill with lazy-loaded content
@dataclass(frozen=True, slots=True)  # slots=True works with cached_property in Python 3.10+
class Skill:
    """Full skill with content (~50-200KB) - loaded on-demand.

    Note: slots=True requires Python 3.10+. For Python 3.9, remove slots=True
    from this class (SkillMetadata retains slots for memory optimization).
    """
    metadata: SkillMetadata
    base_directory: Path
    _processor: 'CompositeProcessor' = field(init=False, repr=False)

    def __post_init__(self):
        """Initialize processor - avoids inline imports anti-pattern."""
        from skillkit.core.processors import CompositeProcessor, \
            BaseDirectoryProcessor, ArgumentSubstitutionProcessor

        # Use object.__setattr__ because dataclass is frozen
        object.__setattr__(
            self,
            '_processor',
            CompositeProcessor([
                BaseDirectoryProcessor(),
                ArgumentSubstitutionProcessor()
            ])
        )

    @cached_property
    def content(self) -> str:
        """Lazy load content only when accessed."""
        return self.metadata.skill_path.read_text(encoding="utf-8")

    def invoke(self, arguments: str = "") -> str:
        """Process skill content with arguments."""
        context = {
            "arguments": arguments,
            "base_directory": str(self.base_directory)
        }
        return self._processor.process(self.content, context)
```

**Content Processing Architecture** (Strategy Pattern):

```python
from abc import ABC, abstractmethod

class ContentProcessor(ABC):
    """Strategy for processing skill content."""

    @abstractmethod
    def process(self, content: str, context: dict) -> str:
        """Process content with given context."""
        pass

class BaseDirectoryProcessor(ContentProcessor):
    """Injects base directory context at beginning."""

    def process(self, content: str, context: dict) -> str:
        base_dir = context.get("base_directory", "")
        return f"Base directory for this skill: {base_dir}\n\n{content}"

class ArgumentSubstitutionProcessor(ContentProcessor):
    """Handles $ARGUMENTS placeholder using string.Template with security validation."""

    PLACEHOLDER_NAME = "ARGUMENTS"
    MAX_ARGUMENT_LENGTH = 1_000_000  # 1MB

    # Common typos to detect and warn about
    COMMON_TYPOS = {
        '$arguments': '$ARGUMENTS (case-sensitive)',
        '$Arguments': '$ARGUMENTS (all caps)',
        '$ ARGUMENTS': '$ARGUMENTS (no space)',
        '$ARGS': '$ARGUMENTS (full word)',
        '$args': '$ARGUMENTS (full word, all caps)',
    }

    def process(self, content: str, context: dict) -> str:
        from string import Template
        import re

        arguments = context.get("arguments", "")
        skill_name = context.get("skill_name", "unknown")

        # Check for common typos (UX improvement)
        self._check_for_typos(content, skill_name)

        # Validate arguments (security)
        if arguments:
            if len(arguments) > self.MAX_ARGUMENT_LENGTH:
                raise ValueError(
                    f"Arguments too large: {len(arguments)} chars "
                    f"(max: {self.MAX_ARGUMENT_LENGTH})"
                )

            # Warn on suspicious patterns (defense-in-depth)
            if self._contains_suspicious_patterns(arguments):
                logger.warning(
                    "Skill '%s': Arguments contain potentially dangerous patterns",
                    skill_name
                )

        # Create template and check for placeholder
        template = Template(content)
        identifiers = self._get_identifiers(template)

        # Replace placeholder if present (Template handles $$ARGUMENTS escaping)
        if self.PLACEHOLDER_NAME in identifiers:
            processed = template.safe_substitute(ARGUMENTS=arguments)
        elif arguments:
            # No placeholder but arguments provided - append
            processed = f"{content}\n\n## Arguments\n\n{arguments}"
        else:
            # No placeholder, no arguments
            processed = content

        # Validate result
        if not processed.strip() and content.strip():
            logger.warning("Skill '%s': Processing produced empty content", skill_name)
            return "[Skill invoked with no arguments]"

        return processed

    @staticmethod
    def _get_identifiers(template) -> set:
        """Extract identifiers from template (Python 3.11+ or fallback)."""
        if hasattr(template, 'get_identifiers'):
            return set(template.get_identifiers())
        else:
            import re
            return set(re.findall(r'\$([a-zA-Z_][a-zA-Z0-9_]*)', template.template))

    @staticmethod
    def _contains_suspicious_patterns(text: str) -> bool:
        """Check for common injection patterns."""
        # Expanded pattern detection for defense-in-depth
        SUSPICIOUS_PATTERNS = {
            '../': 'path traversal',
            '$(': 'shell command substitution',
            '`': 'shell backticks',
            '\x00': 'null byte injection',
            '\u202E': 'right-to-left override',
            '${': 'shell variable expansion',
            '\n\n---': 'YAML frontmatter injection',
            '<script': 'potential XSS',
            'javascript:': 'javascript protocol',
        }

        found_patterns = [pattern for pattern in SUSPICIOUS_PATTERNS if pattern in text]

        if found_patterns:
            # Log which specific patterns were found
            pattern_names = [SUSPICIOUS_PATTERNS[p] for p in found_patterns]
            logger.warning(
                "Suspicious patterns detected: %s",
                ', '.join(pattern_names)
            )
            return True
        return False

    def _check_for_typos(self, content: str, skill_name: str) -> None:
        """Log warnings for common $ARGUMENTS typos."""
        for typo, correction in self.COMMON_TYPOS.items():
            if typo in content:
                logger.warning(
                    "Skill '%s': Possible typo '%s' found. Did you mean '%s'?",
                    skill_name, typo, correction
                )

class CompositeProcessor(ContentProcessor):
    """Chains multiple processors in order."""

    def __init__(self, processors: list[ContentProcessor]):
        self.processors = processors

    def process(self, content: str, context: dict) -> str:
        result = content
        for processor in self.processors:
            result = processor.process(result, context)
        return result
```

**SkillManager Interface**:
- `SkillManager.list_skills()` returns `List[SkillMetadata]` only (lightweight)
- `SkillManager.load_skill(name)` creates `Skill` instance (content loaded lazily via cached_property)
- `SkillManager.invoke_skill(name, args)` loads and processes skill in one call

**Design Benefits**:
- ✅ **Single Responsibility**: Each processor handles one concern
- ✅ **Open/Closed Principle**: Add new processors without modifying existing code
- ✅ **Memory optimization**: `frozen=True, slots=True` provides 60% memory reduction (Python 3.10+)
- ✅ **Lazy loading**: `@cached_property` loads content once, caches result
- ✅ **Testability**: Each processor can be tested in isolation
- ✅ **Extensibility**: Chain processors in any order for different use cases
- ✅ **Escape mechanism**: Standard `$$ARGUMENTS` syntax (no collision risk with temporary markers)
- ✅ **Security**: `string.Template` prevents code execution; 1MB size limit prevents resource exhaustion
- ✅ **Standard Library**: Zero dependencies for core processing, follows Python conventions
- ✅ **Input validation**: Defense-in-depth with expanded suspicious pattern detection (9 patterns including XSS, YAML injection)
- ✅ **Developer experience**: Typo detection with helpful warnings (`$arguments` → suggests `$ARGUMENTS`)
- ✅ **Detailed logging**: Suspicious patterns logged with descriptive names for easy debugging
- ✅ **Clean initialization**: Processor created in `__post_init__` avoids inline imports anti-pattern
- ✅ **Immutability**: Frozen dataclass ensures thread-safety and prevents accidental mutation

**Python Version Compatibility**:

The implementation uses `slots=True` on both dataclasses for memory optimization:

- **Python 3.10+**: Full slots support on both SkillMetadata and Skill (including with `@cached_property`)
- **Python 3.9**: Partial slots support
  - SkillMetadata: Use `slots=True` (no cached_property used)
  - Skill: Remove `slots=True` (required for `@cached_property` compatibility)
  - Memory impact: Skill instances use ~60% more memory per object, but since content is loaded lazily, this affects only the wrapper object (~1-2KB vs ~400-800 bytes)

**Why not use attrs for Python 3.9 slots support?**
While `attrs` provides full slots support on Python 3.9, it conflicts with the "zero framework dependencies" core design goal. The memory trade-off for Python 3.9 users is acceptable:
- With slots (3.10+): ~2MB for 100 skills with 10% usage
- Without slots on Skill (3.9): ~2.5MB for 100 skills with 10% usage (~25% increase)
- This is negligible compared to 10MB+ with eager loading

**Recommendation**: Target Python 3.10+ for best performance; support Python 3.9 with minor memory trade-off.

**Alternatives Considered**:
- **Eager loading**: Load all content during discovery - Rejected due to memory overhead (10MB+ for 100 skills)
- **Lazy properties with mutation**: Load content on first access via @property - Rejected; `@cached_property` is cleaner and standard
- **Database caching**: Store parsed metadata in SQLite - Rejected as over-engineering for v0.1 (deferred to v0.3 if needed)
- **Monolithic processing function**: Single function for all content processing - Rejected; violates Single Responsibility Principle
- **str.replace() with temporary markers**: Custom escape mechanism using `<<ESCAPED_ARGUMENTS_MARKER>>` - Rejected due to collision risk, non-standard escaping, and lack of security features vs `string.Template`
- **Regular dataclass without slots**: Would work but wastes 60% more memory on Python 3.10+
- **attrs library for Python 3.9 slots**: Rejected; conflicts with zero-dependency core goal. Minor memory trade-off acceptable for 3.9 users
- **Inline imports in invoke()**: Original design had imports inside method - Rejected as anti-pattern; moved to `__post_init__`

**Performance Impact**:
- Discovery: ~50-100ms for 100 skills (metadata only, dominated by YAML parsing)
- Invocation: ~10-25ms overhead (file I/O ~10-20ms + string processing ~1-5ms)
- Memory (metadata with slots, Python 3.10+): ~400-800 bytes per SkillMetadata (~40-80KB for 100 skills)
- Memory (metadata without slots, Python 3.9): ~1-2KB per SkillMetadata (~100-200KB for 100 skills)
- Memory (Skill wrapper with slots, Python 3.10+): ~400-800 bytes per Skill instance
- Memory (Skill wrapper without slots, Python 3.9): ~1-2KB per Skill instance
- Memory (loaded content): ~50-200KB per skill (only loaded when invoked via `@cached_property`)
- Strategy pattern overhead: <1ms (negligible vs 10ms file I/O)
- Template substitution overhead: <1ms (string.Template is C-optimized, comparable to str.replace())
- Expected total memory (100 skills, 10% usage):
  - Python 3.10+ with slots: ~2.0MB (40KB metadata + 40KB wrappers + 1.92MB content)
  - Python 3.9 without slots: ~2.3MB (100KB metadata + 100KB wrappers + 2.1MB content)
  - Eager loading (all skills): 10MB+ (100KB metadata + 100KB wrappers + 10MB+ content)
  - **Reduction: 80% memory savings vs eager loading**

---

### Decision 2: Framework-Agnostic Core

**Decision**: Core modules (`core/`) have zero framework dependencies; framework integrations live in separate `integrations/` package.

**Rationale**:
- **Standalone usability**: Library can be used without any agent framework
- **Easier testing**: No framework mocking required for core tests
- **Future-proof**: Adding LlamaIndex, CrewAI, etc. doesn't require core changes
- **Reduced maintenance**: Framework API changes don't break core functionality
- **Clear separation of concerns**: Core = skill management, Integrations = framework adapters

**Implementation**:
```python
# Core: stdlib + PyYAML only
src/skillkit/core/
  - discovery.py    # Filesystem operations
  - parser.py       # YAML parsing
  - models.py       # Pure dataclasses
  - manager.py      # Orchestration
  - invocation.py   # String processing

# Integrations: framework-specific
src/skillkit/integrations/
  - langchain.py    # Requires langchain-core, pydantic
  - llamaindex.py   # Future: v1.1
  - crewai.py       # Future: v1.1
```

**Dependencies Strategy**:
```toml
[project]
dependencies = ["pyyaml>=6.0"]  # Core only - zero framework dependencies

[project.optional-dependencies]
langchain = [
    "langchain-core>=0.1.0",
    "pydantic>=2.0.0"  # Already a transitive dep of langchain-core, but explicit for clarity
]
dev = ["pytest>=7.0.0", "pytest-cov>=4.0.0", "mypy>=1.0.0", "ruff>=0.1.0"]
all = ["skillkit[langchain,dev]"]
```

**Import Guard Pattern** (for optional integrations):
```python
# src/skillkit/integrations/langchain.py
try:
    from langchain_core.tools import StructuredTool
    from pydantic import BaseModel, ConfigDict, Field
except ImportError as e:
    raise ImportError(
        "LangChain integration requires additional dependencies. "
        "Install with: pip install skillkit[langchain]"
    ) from e

# User code can check availability
try:
    from skillkit.integrations import langchain
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False
```

**Why explicit pydantic dependency?**
While `pydantic>=2.0.0` is a transitive dependency of `langchain-core`, we list it explicitly because:
1. We directly import from pydantic in our integration code (`BaseModel`, `Field`, etc.)
2. Explicit is better than implicit (PEP 20) - makes dependency requirements clear
3. Protects against langchain-core potentially dropping pydantic in future versions
4. Allows version pinning if we need pydantic-specific features

**Alternatives Considered**:
- **Tightly coupled design**: Import LangChain in core modules - Rejected due to forced dependency and testing complexity
- **Plugin architecture**: Dynamic loading of integrations - Rejected as over-engineering for v0.1 (3 integrations max)
- **Separate packages**: Publish `skillkit-core` and `skillkit-langchain` separately - Rejected due to maintenance overhead

---

### Decision 3: $ARGUMENTS Substitution Algorithm

**Decision**: Use `string.Template` for safe placeholder substitution with `$$ARGUMENTS` escaping; append arguments if placeholder missing.

**Problem Statement**: How to handle edge cases in argument substitution?
1. Multiple `$ARGUMENTS` placeholders in content
2. Empty arguments string
3. No placeholder but arguments provided
4. No placeholder and no arguments
5. Escaping literal `$ARGUMENTS` text
6. Security concerns with untrusted input

**Solution Algorithm**:
```python
from string import Template

def process_skill_content(skill: Skill, arguments: str = "") -> str:
    # Step 1: Always inject base directory context
    processed = f"Base directory for this skill: {skill.base_directory}\n\n{skill.content}"

    # Step 2: Validate arguments (security)
    if arguments and len(arguments) > 1_000_000:  # 1MB limit
        raise ValueError(f"Arguments too large: {len(arguments)} chars (max: 1,000,000)")

    # Step 3-5: Handle arguments with Template
    template = Template(processed)
    identifiers = _get_identifiers(template)

    if "ARGUMENTS" in identifiers:
        # Case 1 & 2: Replace all occurrences (even with empty string)
        # Template automatically handles $$ARGUMENTS -> $ARGUMENTS escaping
        processed = template.safe_substitute(ARGUMENTS=arguments)
    elif arguments:
        # Case 3: No placeholder but args provided - append
        processed += f"\n\n## Arguments\n\n{arguments}"
    # Case 4: No placeholder, no args - return as-is

    return processed

def _get_identifiers(template: Template) -> set:
    """Extract identifiers (Python 3.11+ or fallback)."""
    if hasattr(template, 'get_identifiers'):
        return set(template.get_identifiers())
    else:
        import re
        return set(re.findall(r'\$([a-zA-Z_][a-zA-Z0-9_]*)', template.template))
```

**Behavior Table**:

| Skill Content | Arguments | Result |
|---------------|-----------|--------|
| `Review: $ARGUMENTS` | `"code"` | `Review: code` |
| `$ARGUMENTS\n\n$ARGUMENTS` | `"test"` | `test\n\ntest` |
| `$ARGUMENTS` | `""` | `` (empty) |
| `Review code` | `"def foo()"` | `Review code\n\n## Arguments\n\ndef foo()` |
| `Review code` | `""` | `Review code` |
| `Use $$ARGUMENTS` | `"foo"` | `Use $ARGUMENTS` (escaped) |
| `Cost: $$50` | `"bar"` | `Cost: $50` (escaped dollar) |
| `$$ARGUMENTS = $ARGUMENTS` | `"test"` | `$ARGUMENTS = test` (mixed) |

**Rationale**:
- **Security**: `string.Template` prevents code execution (vs `str.format()` which can access attributes)
- **Standard Library**: Zero dependencies, battle-tested for 15+ years, well-documented
- **Built-in Escaping**: `$$` is Python's standard escape pattern (no collision risk with temporary markers)
- **Maximize flexibility**: Skill authors can use multiple placeholders if needed
- **Predictable behavior**: No heuristics or magic; explicit handling for each case
- **Input validation**: 1MB size limit prevents resource exhaustion attacks
- **Python conventions**: Following `string.Template` conventions improves maintainability

**Alternatives Considered**:
- **str.replace() with temporary markers**: Original approach - Rejected due to:
  - Marker collision risk (if skill content contains `<<ESCAPED_ARGUMENTS_MARKER>>`)
  - Custom escape mechanism harder to document/understand
  - No built-in security features
  - Technical debt vs standard library approach
- **str.format() / f-strings**: Rejected as **security vulnerability** (allows attribute access and code execution)
- **Jinja2**: Too heavy for v0.1, deferred to v1.0+ when advanced features needed (loops, conditionals, filters)
- **Single replacement only**: Replace first occurrence - Rejected as too restrictive
- **Heuristic detection**: Try to guess where arguments should go - Rejected as unpredictable
- **Raise error if missing placeholder**: Force all skills to use $ARGUMENTS - Rejected as too strict for v0.1

**Edge Cases**:
- **Case sensitivity**: Only exact `$ARGUMENTS` replaced (not `$arguments` or `$Arguments`) - intentional for clarity
  - **Mitigation**: Implemented via `_check_for_typos()` method which logs warnings for common typos: `$arguments`, `$Arguments`, `$ ARGUMENTS`, `$ARGS`, `$args`
  - Helps skill authors debug placeholder issues quickly
- **Placeholder in code blocks**: Still replaced (author uses `$$ARGUMENTS` to escape if needed)
- **Unicode in arguments**: Fully supported (UTF-8 encoding enforced)
- **Empty result**: If skill is only `$ARGUMENTS` with no args, return `[Skill invoked with no arguments]` placeholder
- **Security**: Expanded suspicious pattern detection (defense-in-depth):
  - Path traversal: `../`
  - Command injection: `$(`, `` ` ``, `${`
  - Null byte injection: `\x00`
  - Unicode attacks: `\u202E` (RTL override)
  - YAML injection: `\n\n---`
  - XSS patterns: `<script`, `javascript:`
  - All patterns logged with descriptive names for debugging

**Security Considerations**:
- **Input validation**: 1MB (1,000,000 character) limit on arguments prevents memory exhaustion
- **No code execution**: Template syntax is safe (doesn't evaluate expressions or access attributes)
- **Suspicious pattern detection**: Log warnings for path traversal, command injection attempts
- **Defense-in-depth**: Security validation at processor level, skill authors responsible for safe usage

**Implementation Notes**:
- Python 3.11+ has `template.get_identifiers()` method; fallback regex for Python 3.9-3.10
  - NOTE: `Template.get_identifiers()` added in Python 3.11; regex fallback is functionally equivalent
- `safe_substitute()` used instead of `substitute()` to avoid KeyError if placeholder missing
- Escaping documentation must clearly explain `$$ARGUMENTS` → `$ARGUMENTS` conversion

**Escaping $ARGUMENTS Documentation** (for skill authors):

Skills can use the standard Python `$$` escape pattern to include literal `$ARGUMENTS` text:

```markdown
---
name: example-skill
description: Demonstrates escaping
---

This skill uses $$ARGUMENTS as a placeholder.
Actual arguments: $ARGUMENTS
```

**Result with arguments="test"**:
```
This skill uses $ARGUMENTS as a placeholder.
Actual arguments: test
```

**Common escaping scenarios**:
- `$$ARGUMENTS` → `$ARGUMENTS` (escaped placeholder)
- `$ARGUMENTS` → replaced with actual arguments
- `Cost: $$50` → `Cost: $50` (escaped dollar sign)
- `$$ARGUMENTS = $ARGUMENTS` → `$ARGUMENTS = test` (mixed usage)

**Best practices**:
- Use `$$ARGUMENTS` in documentation/examples when you want to show the literal text
- Use `$ARGUMENTS` when you want the actual argument value substituted
- The escaping follows Python's standard `string.Template` conventions
- No collision risk with skill content (unlike custom marker approaches)

---

### Decision 4: Error Handling Strategy

**Decision**: Graceful degradation during discovery; strict exceptions during invocation.

**Rationale**:
- **Discovery phase**: Bad skill files shouldn't prevent discovery of other skills (robustness)
- **Invocation phase**: Errors should be explicit for debugging (clarity)
- **Balance**: Maximize usability during browsing, maximize clarity during execution
- **Python library standards (2024-2025)**: Follows best practices for exception hierarchies and logging

**Implementation**:

**Discovery (graceful)**:
```python
for skill_path in skill_paths:
    try:
        metadata = self.parser.parse_skill_file(skill_path)

        # Handle duplicate skill names (v0.1)
        if metadata.name in self._skills:
            logger.warning(
                "Duplicate skill name '%s' found at %s. "
                "Ignoring duplicate (first found at %s).",
                metadata.name,
                skill_path,
                self._skills[metadata.name].skill_path
            )
            continue

        self._skills[metadata.name] = metadata
    except Exception as e:
        logger.exception(  # Use .exception() for traceback
            "Failed to parse skill at %s",
            skill_path
        )
        # Continue processing other skills - don't fail entire discovery
```

**Invocation (strict)**:
```python
def get_skill(self, name: str) -> SkillMetadata:
    if name not in self._skills:
        logger.debug("Skill '%s' not found in registry", name)
        raise SkillNotFoundError(f"Skill '{name}' not found")
    return self._skills[name]
```

**Exception Hierarchy** (Expanded for v0.1):
```python
SkillsUseError                      # Base exception (catch-all)
├── SkillParsingError               # Base parsing error
│   ├── InvalidYAMLError            # YAML syntax errors
│   ├── MissingRequiredFieldError   # Missing name/description
│   └── InvalidFrontmatterError     # Delimiter or structure issues
├── SkillNotFoundError              # Skill doesn't exist in registry
├── SkillInvocationError            # Base invocation error
│   ├── ArgumentProcessingError     # $ARGUMENTS substitution failed
│   └── ContentLoadError            # Failed to read skill content
└── SkillSecurityError              # Base security error
    ├── SuspiciousInputError        # Detected malicious patterns
    └── SizeLimitExceededError      # Input exceeds size limits
```

**Logging Strategy** (Python Library Best Practices):

**🚨 CRITICAL: Logging Configuration (MUST DO for v0.1)**:
```python
# src/skillkit/__init__.py
import logging

# Add NullHandler to prevent "No handlers found" warnings
# This is Python library standard (2024-2025)
logging.getLogger(__name__).addHandler(logging.NullHandler())
```

**Why NullHandler is Critical**:
- **Python standard**: "Strongly advised that you do not add any handlers other than NullHandler to your library's loggers"
- **Application control**: Configuration of handlers is the prerogative of the application developer
- **Popular libraries**: requests, urllib3, and all major Python libraries use this pattern
- **Test isolation**: Prevents unwanted log output in unit tests

**Module-Specific Loggers (MUST DO)**:
```python
# ❌ WRONG - Don't use root logger
import logging
logger = logging.getLogger()  # Root logger!

# ✅ CORRECT - Use module name
import logging
logger = logging.getLogger(__name__)  # Creates 'skillkit.core.discovery', etc.
```

**Why Module-Specific Loggers**:
- Application developers can configure per-module verbosity
- Example: `logging.getLogger('skillkit.core.discovery').setLevel(logging.DEBUG)`
- Follows "Explicit is better than implicit" (PEP 20)

**Logging Levels**:
- **DEBUG**: Individual skill discoveries, successful parsing, pre-exception diagnostics
- **INFO**: Discovery complete (count), major operations, empty skill directory
- **WARNING**: Recoverable issues (malformed allowed-tools field, suspicious patterns, duplicate skill names)
- **ERROR**: Parsing failures, missing required fields (use `logger.exception()` in except blocks)

**Enhanced Logging Practices**:
```python
# Use logger.exception() for automatic traceback
except Exception as e:
    logger.exception("Failed to parse skill at %s", skill_path)

# Use structured context
logger.error(
    "Failed to parse skill at %s: %s",
    skill_path,
    str(e),
    exc_info=True  # Include stack trace
)

# Performance-conscious debug logging
if logger.isEnabledFor(logging.DEBUG):
    logger.debug("Discovered skill: %s", expensive_repr(metadata))
```

**Missing Error Scenarios** (Must Handle in v0.1):

1. **Duplicate Skill Names** ✅ (Added above)
   - Log WARNING and skip duplicate
   - Keep first discovered skill

2. **Content Loading Failures**:
   ```python
   @cached_property
   def content(self) -> str:
       try:
           return self.metadata.skill_path.read_text(encoding="utf-8")
       except FileNotFoundError as e:
           raise ContentLoadError(
               f"Skill file not found: {self.metadata.skill_path}. "
               f"File may have been deleted after discovery."
           ) from e
       except PermissionError as e:
           raise ContentLoadError(
               f"Permission denied reading skill: {self.metadata.skill_path}"
           ) from e
       except UnicodeDecodeError as e:
           raise ContentLoadError(
               f"Skill file contains invalid UTF-8: {self.metadata.skill_path}"
           ) from e
   ```

3. **Empty Skill Directory**:
   ```python
   if len(self._skills) == 0:
       logger.info(
           "No skills found in %s. "
           "Create SKILL.md files to define skills.",
           skill_dir
       )
   ```

4. **Size Limit Exceeded** (Wrap in custom exception):
   ```python
   if len(arguments) > self.MAX_ARGUMENT_LENGTH:
       raise SizeLimitExceededError(
           f"Arguments too large: {len(arguments)} chars "
           f"(max: {self.MAX_ARGUMENT_LENGTH})"
       )
   ```

5. **Argument Processing Failures**:
   ```python
   try:
       processed = template.safe_substitute(ARGUMENTS=arguments)
   except (ValueError, KeyError) as e:
       raise ArgumentProcessingError(
           f"Failed to process arguments in skill '{skill_name}': {e}"
       ) from e
   ```

**Exception Context Requirements**:
- **Include file paths**: Help developers locate problematic files
- **Include field names**: Specify which required field is missing
- **Provide guidance**: Suggest fixes ("Check file permissions", "Fix YAML syntax")
- **Chain exceptions**: Use `raise ... from e` to preserve stack traces

**Testing Requirements**:
```python
# Test exception hierarchy integrity
def test_all_exceptions_inherit_from_base():
    assert issubclass(SkillParsingError, SkillsUseError)
    assert issubclass(InvalidYAMLError, SkillParsingError)

# Test graceful degradation
def test_discovery_continues_after_parsing_error(caplog):
    # One bad skill shouldn't prevent discovering others
    assert len(manager.list_skills()) == 1
    assert "Failed to parse skill" in caplog.text
    assert caplog.records[0].levelname == "ERROR"

# Test strict invocation
def test_invocation_raises_on_missing_skill():
    with pytest.raises(SkillNotFoundError, match="Skill 'nonexistent' not found"):
        manager.invoke_skill("nonexistent")

# Test NullHandler configuration
def test_nullhandler_configured():
    logger = logging.getLogger('skillkit')
    assert any(isinstance(h, logging.NullHandler) for h in logger.handlers)
```

**Documentation Requirements** (for README.md):

1. **Exception Handling Guide**:
   ```python
   # Catch all library errors
   try:
       manager.invoke_skill("my-skill", args)
   except SkillsUseError as e:
       print(f"Skill operation failed: {e}")

   # Catch specific errors
   try:
       manager.invoke_skill("my-skill", args)
   except SkillNotFoundError:
       print("Skill not found. Check skill name.")
   except ContentLoadError:
       print("Skill file was deleted or is unreadable.")
   except SizeLimitExceededError:
       print("Arguments too large (max 1MB).")
   ```

2. **Logging Configuration**:
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

3. **Exception Reference Table**:
   | Exception | When Raised | How to Handle |
   |-----------|-------------|---------------|
   | InvalidYAMLError | Malformed YAML syntax | Fix YAML in SKILL.md |
   | MissingRequiredFieldError | Missing name/description | Add required field |
   | SkillNotFoundError | Skill name not in registry | Check spelling, run discover() |
   | ContentLoadError | File deleted/unreadable | Check file exists and permissions |
   | SizeLimitExceededError | Arguments exceed 1MB | Reduce argument size |
   | ArgumentProcessingError | Template substitution failed | Check $ARGUMENTS syntax |

**Alternatives Considered**:
- **Fail-fast**: Stop discovery on first error - Rejected as too brittle (one bad skill breaks everything)
- **Silent failures**: Don't log errors - Rejected as makes debugging impossible
- **Try-except everywhere**: Catch all exceptions - Rejected as hides real bugs
- **Return values vs exceptions**: Use Optional[T] - Rejected as "not found" should be exceptional (not expected)
- **Result objects (functional style)**: Union[Success, Failure] - Rejected as not idiomatic Python

**Architectural Review Summary** (Nov 4, 2025):
- **Score**: 8/10 - Architecturally sound, required enhancements identified
- **Core decision**: ✅ Excellent (graceful discovery + strict invocation)
- **Critical gaps**: NullHandler configuration, expanded exception hierarchy, duplicate handling
- **Validation**: Follows Python library best practices (2024-2025 standards)
- **Recommendation**: ✅ APPROVED with required changes (8 critical items for v0.1)

---

### Decision 5: YAML Frontmatter Parsing

**Decision**: Use regex to extract frontmatter delimiters with cross-platform line ending support, then `yaml.safe_load()` for secure parsing with detailed error messages.

**Format Specification**:
```markdown
---
name: skill-name
description: Brief description of skill purpose
allowed-tools: Tool1, Tool2  # Optional
---

Markdown content with $ARGUMENTS placeholder.
```

**Rationale**:
- **Security**: `yaml.safe_load()` prevents code execution attacks (vs `yaml.load()`)
- **Robustness**: Enhanced regex pattern handles cross-platform line endings (Unix `\n`, Windows `\r\n`)
- **Standard format**: Matches Jekyll, Hugo, and other static site generators
- **Clear separation**: Frontmatter vs content cleanly separated by `---` delimiters
- **Forward compatibility**: Silent unknown field handling allows v0.2 skills to work with v0.1
- **Developer experience**: Detailed error messages with line/column information, typo detection

**Implementation**:

**Enhanced Regex Pattern** (Cross-Platform):
```python
# Pre-compiled for performance, handles Unix/Windows line endings
_FRONTMATTER_PATTERN = re.compile(
    r'^\s*---\s*[\r\n]+(.*?)[\r\n]+---\s*[\r\n]+(.*)$',
    re.DOTALL
)

match = self._FRONTMATTER_PATTERN.match(content)
frontmatter_raw = match.group(1)
markdown_content = match.group(2)
```

**Pattern Details**:
- `^\s*` - Allows optional leading whitespace
- `[\r\n]+` - Matches both Unix (`\n`) and Windows (`\r\n`) line endings
- `(.*?)` - Lazy quantifier prevents matching past first closing delimiter
- `(.*)$` - Captures remainder as content (DOTALL handles multiline)

**Enhanced YAML Parsing with Error Details**:
```python
try:
    frontmatter = yaml.safe_load(frontmatter_raw)
except yaml.YAMLError as exc:
    # Extract line/column details if available
    line, column = None, None
    if hasattr(exc, 'problem_mark'):
        mark = exc.problem_mark
        line, column = mark.line + 1, mark.column + 1

    # Build detailed, actionable error message
    location = f" at line {line}, column {column}" if line else ""
    raise InvalidYAMLError(
        f"Invalid YAML syntax in {skill_path}{location}: {exc}",
        line=line,
        column=column
    ) from exc

if not isinstance(frontmatter, dict):
    raise InvalidFrontmatterError(
        f"Frontmatter in {skill_path} must be a YAML dictionary"
    )
```

**Enhanced Validation with Typo Detection**:
```python
def _validate_frontmatter(self, frontmatter: Dict[str, Any], skill_path: Path) -> Dict[str, Any]:
    """Validate frontmatter with typo detection and detailed errors."""

    # Validate required fields (non-empty strings)
    if not frontmatter.get("name") or not str(frontmatter["name"]).strip():
        raise MissingRequiredFieldError(
            f"Field 'name' is required and must be non-empty in {skill_path}",
            field_name="name"
        )

    if not frontmatter.get("description") or not str(frontmatter["description"]).strip():
        raise MissingRequiredFieldError(
            f"Field 'description' is required and must be non-empty in {skill_path}",
            field_name="description"
        )

    # Validate optional fields (graceful degradation)
    allowed_tools = frontmatter.get("allowed-tools")
    if allowed_tools is not None:
        if not isinstance(allowed_tools, list):
            logger.warning(
                f"{skill_path}: 'allowed-tools' should be list, "
                f"got {type(allowed_tools).__name__}. Setting to None."
            )
            frontmatter["allowed-tools"] = None
        elif not all(isinstance(t, str) for t in allowed_tools):
            valid_tools = [t for t in allowed_tools if isinstance(t, str)]
            logger.warning(
                f"{skill_path}: 'allowed-tools' contains non-string items. "
                f"Using only valid strings: {valid_tools}"
            )
            frontmatter["allowed-tools"] = valid_tools

    # Check for typos in field names (improved UX)
    KNOWN_FIELDS = {"name", "description", "allowed-tools"}
    TYPO_MAP = {
        "allowed_tools": "allowed-tools",
        "allowedtools": "allowed-tools",
        "tools": "allowed-tools",
    }

    unknown = set(frontmatter.keys()) - KNOWN_FIELDS
    for field in unknown:
        if field.lower() in TYPO_MAP:
            logger.warning(
                f"{skill_path}: Unknown field '{field}'. "
                f"Did you mean '{TYPO_MAP[field.lower()]}'?"
            )
        else:
            logger.debug(
                f"{skill_path}: Unknown field '{field}' (ignored for forward compatibility)"
            )

    return frontmatter
```

**UTF-8 Encoding with BOM Support**:
```python
# Use utf-8-sig to auto-strip BOM character if present
try:
    content = skill_path.read_text(encoding="utf-8-sig")
except UnicodeDecodeError as e:
    raise ContentLoadError(
        f"Invalid UTF-8 in {skill_path} at byte {e.start}: {e.reason}"
    ) from e
```

**Validation Rules**:
- **Required fields**: `name`, `description` - raise MissingRequiredFieldError if missing or empty
- **Optional fields**: `allowed-tools` (list of strings) - warn if invalid type, filter non-string items
- **Unknown fields**: Ignored silently (forward compatibility) with DEBUG log
- **Typos**: Detected and logged with suggestions (WARNING level)
- **Empty strings**: Validated via `.strip()` check - empty strings fail validation

**Exception Hierarchy**:
```python
InvalidYAMLError(SkillParsingError)
    - Attributes: line (int | None), column (int | None)
    - Raised: YAML syntax errors

MissingRequiredFieldError(SkillParsingError)
    - Attributes: field_name (str | None)
    - Raised: Required field missing or empty

InvalidFrontmatterError(SkillParsingError)
    - Raised: Missing delimiters, non-dict frontmatter
```

**Alternatives Considered**:
- **Python-frontmatter library**: Use existing parser - Rejected for v0.1 to minimize dependencies (reconsidered for v0.2 if edge cases accumulate)
- **TOML frontmatter**: Use `+++` delimiters - Rejected as YAML is more common
- **JSON frontmatter**: Use `{}` syntax - Rejected as less human-readable
- **Original regex `\n` only**: Rejected as fails on Windows `\r\n` line endings
- **Silent empty string validation**: Rejected as allows meaningless skills

**Edge Cases Handled**:
- **Missing delimiters**: Raise InvalidFrontmatterError with helpful message
- **Empty frontmatter**: Raise MissingRequiredFieldError for required fields
- **Malformed YAML**: Catch `yaml.YAMLError`, extract line/column, raise InvalidYAMLError with precise location
- **Unicode content**: Use `utf-8-sig` encoding to handle UTF-8 BOM automatically
- **Windows line endings**: Regex pattern `[\r\n]+` handles both Unix and Windows
- **Empty string fields**: Validated via `.strip()` - raises MissingRequiredFieldError
- **Malformed allowed-tools**:
  - Non-list → log WARNING, set to None
  - Mixed types → filter to strings only, log WARNING with filtered list
- **Typos in field names**: Detected via TYPO_MAP, log WARNING with suggestion
- **Multiple `---` in content**: Lazy quantifier `(.*?)` stops at first closing delimiter
- **Extra whitespace**: Leading `\s*` and `\s*` after delimiters handle formatting variations

**Performance Optimizations**:
- **Pre-compiled regex**: Store as class attribute for ~10% speedup
- **Early validation**: Check required fields before expensive operations
- **C-optimized YAML**: PyYAML uses C extension for fast parsing (~5-10ms)
- **Expected overhead**: ~5-10ms per skill file (acceptable for v0.1)

**Security Validation** (2024-2025 Standards):
- ✅ `yaml.safe_load()` prevents code execution (no CVEs in PyYAML 2025)
- ✅ UTF-8 encoding enforcement prevents binary exploits
- ✅ No eval/exec in regex pattern
- ✅ Exception chaining preserves stack traces (`from exc`)
- ✅ Non-empty validation prevents meaningless skill registration

**Forward Compatibility Design**:
```yaml
---
name: skill-v2
description: Uses v0.2 features
allowed-tools: Read
cache-ttl: 300  # v0.2 feature - v0.1 ignores without error (DEBUG log)
async-mode: true  # v0.2 feature - v0.1 ignores without error (DEBUG log)
---
```

**Benefits**:
- ✅ v0.2 skills work with v0.1 library (graceful degradation)
- ✅ v0.1 skills work with v0.2 library (no breaking changes)
- ✅ Plugin-specific metadata doesn't break core library
- ✅ Unknown fields logged at DEBUG level (not WARNING) to avoid noise

**Testing Requirements** (Comprehensive Coverage):
```python
# test_parser.py - Required test cases for v0.1

def test_parse_valid_skill():
    """Standard skill with all fields."""

def test_parse_minimal_skill():
    """Only required fields (name, description)."""

def test_parse_windows_line_endings():
    """Windows CRLF (\r\n) should work."""

def test_parse_utf8_bom():
    """UTF-8 BOM should be auto-stripped."""

def test_parse_empty_name():
    """Empty name should raise MissingRequiredFieldError."""

def test_parse_whitespace_only_description():
    """Whitespace-only description should raise MissingRequiredFieldError."""

def test_parse_missing_required_field():
    """Missing name or description should raise with field_name."""

def test_parse_invalid_yaml_syntax():
    """Malformed YAML should raise InvalidYAMLError with line/column."""

def test_parse_malformed_allowed_tools_non_list():
    """Non-list allowed-tools should log WARNING, set to None."""

def test_parse_malformed_allowed_tools_mixed_types():
    """Mixed-type list should filter to strings, log WARNING."""

def test_parse_typo_in_field_name():
    """'allowed_tools' should suggest 'allowed-tools' (WARNING)."""

def test_parse_unknown_field_forward_compat():
    """Unknown field should be ignored with DEBUG log."""

def test_parse_multiple_delimiters_in_content():
    """Content with '---' should not break parsing."""

def test_parse_missing_frontmatter_delimiters():
    """No delimiters should raise InvalidFrontmatterError."""

def test_parse_non_dict_frontmatter():
    """Non-dictionary YAML should raise InvalidFrontmatterError."""
```

**Architectural Review Summary** (Nov 4, 2025):
- **Score**: 8.5/10 - Architecturally sound with enhancements applied
- **Security**: ✅ 10/10 - `yaml.safe_load()` validated as current best practice
- **Cross-platform**: ✅ Enhanced regex handles Windows/Unix line endings
- **Error handling**: ✅ Detailed YAMLError extraction with line/column
- **Validation**: ✅ Non-empty string checks, typo detection, graceful degradation
- **Forward compatibility**: ✅ 10/10 - Silent unknown field handling perfect
- **Recommendation**: ✅ APPROVED with enhancements applied (Priority 1-5 changes implemented)

---

### Decision 6: LangChain Integration Design

**Decision**: Create `StructuredTool` objects with single string input parameter, sync invocation only.

**Rationale**:
- **LangChain compatibility**: StructuredTool is the standard tool interface (v0.1+)
- **Simple schema**: Single `arguments` string parameter matches skill invocation model
- **Sync-only for v0.1**: Reduces complexity; async added in v0.2 after validation
- **Error handling**: Layered approach (function + tool level) provides robustness
- **Closure safety**: Default parameter capture prevents Python's late-binding closure issues in tool creation loop

**Implementation**:
```python
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict, Field
from typing import List

class SkillInput(BaseModel):
    """Pydantic schema for tool input."""
    model_config = ConfigDict(str_strip_whitespace=True)

    arguments: str = Field(
        default="",
        description="Arguments to pass to the skill"
    )

def create_langchain_tools(manager: SkillManager) -> List[StructuredTool]:
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
    """
    tools = []
    for skill_metadata in manager.list_skills():
        # ✅ CRITICAL: Capture skill_name as default parameter
        def skill_func(
            arguments: str = "",
            skill_name=skill_metadata.name  # Captured at creation time!
        ) -> str:
            try:
                return manager.invoke_skill(skill_name, arguments)
            except Exception as e:
                return f"Error invoking {skill_name}: {str(e)}"

        # Use from_function() for cleaner API and error handling options
        tool = StructuredTool.from_function(
            func=skill_func,
            name=skill_metadata.name,
            description=skill_metadata.description,
            args_schema=SkillInput,
            return_direct=False,
            handle_tool_error=True  # Fallback error handling layer
        )
        tools.append(tool)
    return tools
```

**Tool Mapping**:
- Tool name = skill name (from YAML frontmatter)
- Tool description = skill description (used by LLM for selection)
- Tool input = single `arguments` string
- Tool output = processed skill content (ready for LLM consumption)
- Error handling = three-layer approach:
  1. Function-level try/except (immediate errors)
  2. Tool-level `handle_tool_error=True` (validation + unexpected exceptions)
  3. Agent-level fallback (agent reasons about returned error strings)

**Critical Implementation Notes**:

⚠️ **Closure Capture (MUST DO)**:
The default parameter `skill_name=skill_metadata.name` is NOT optional—it's required to avoid a subtle Python bug:

```python
# ❌ WRONG - All tools invoke last skill!
def skill_func(arguments: str = "") -> str:
    return manager.invoke_skill(skill_name, arguments)  # Late binding!

# ✅ CORRECT - Each tool captures its own skill name
def skill_func(arguments: str = "", skill_name=skill_metadata.name) -> str:
    return manager.invoke_skill(skill_name, arguments)  # Early binding!
```

Why: Python closures look up variable values at execution time (late binding). Without the default parameter, all closure functions share the same `skill_metadata.name` variable—which holds the final loop value after iteration completes. This causes all tools to invoke the last skill in the list.

**Test Case** (verify during implementation):
```python
# If skills are ["skill-1", "skill-2", "skill-3"]
# Each tool must invoke its own skill, not always the last one
tools = create_langchain_tools(manager)
assert tools[0].name == "skill-1"
assert tools[1].name == "skill-2"
assert tools[2].name == "skill-3"
# Calling tool[0] must invoke skill-1, not skill-3
```

**Alternatives Considered**:
- **BaseTool**: Use older LangChain interface - Rejected as deprecated in v0.1+
- **Multiple parameters**: Structured args like `{"file": "...", "action": "..."}` - Rejected as over-engineering for v0.1
- **Async-first**: Implement `afunc` only - Rejected as most agents still use sync patterns
- **Streaming output**: Yield tokens - Rejected as skills are typically <10KB
- **Direct StructuredTool instantiation**: Works but `from_function()` is cleaner and provides better error handling options
- **functools.partial**: Valid alternative to default parameters but less explicit than default capture

---

### Decision 7: Testing Strategy

**Decision**: 70% coverage target with unit + integration tests; fixtures for test skills.

**Coverage Goals**:
- **v0.1**: 70%+ (good enough for MVP validation)
- **v0.2**: 85%+ (after async support)
- **v1.0**: 90%+ (production readiness)

**Test Structure**:
```
tests/
├── conftest.py            # NEW: Minimal shared fixtures (saves 2+ hours)
├── test_discovery.py      # SkillDiscovery: Use tmp_path fixture
├── test_parser.py         # SkillParser: valid YAML, missing fields, malformed
├── test_invocation.py     # Use @pytest.mark.parametrize for 15+ edge cases
├── test_manager.py        # SkillManager: discover, list, get, load, invoke
├── test_langchain.py      # LangChain integration: tool creation, invocation, errors
└── fixtures/skills/
    ├── valid-skill/SKILL.md
    ├── missing-name-skill/SKILL.md
    └── invalid-yaml-skill/SKILL.md
```

**Testing Priorities** (from spec):
- ✅ Core discovery logic (happy path + missing directory)
- ✅ SKILL.md parsing (valid + missing fields + malformed YAML)
- ✅ Invocation with $ARGUMENTS edge cases (15+ comprehensive scenarios):
  - **Basic cases**: single placeholder, multiple placeholders, empty args, no placeholder, no args
  - **Escaping cases**: `$$ARGUMENTS` escaping, mixed escaped/normal, double-dollar in non-placeholder
  - **Edge cases**: Unicode arguments, multiline arguments, size limit exceeded, empty content
  - **Security cases**: suspicious patterns logged, no code execution via attributes, XSS patterns
  - **UX cases**: typo detection (lowercase, titlecase, spacing, abbreviations)
- ✅ LangChain integration (end-to-end agent test)
- ❌ Edge case testing (nested dirs, permissions) - deferred to v0.2
- ❌ Performance testing (benchmarks, profiling) - deferred to v0.3

**MVP-Aligned Testing Practices** (v0.1 - 8 hour budget):

**Critical for v0.1** (Net time saved: +2 hours):

1. **pytest-cov dependency** (5 minutes setup)
   - Required to measure 70% coverage goal
   - Add to pyproject.toml: `dev = ["pytest>=7.0.0", "pytest-cov>=4.0.0"]`
   - Command: `pytest --cov=skillkit --cov-report=term-missing`
   - Rationale: Can't validate coverage target without measurement tool

2. **Minimal conftest.py** (30 minutes setup, saves 2+ hours)
   ```python
   # tests/conftest.py
   import pytest
   from pathlib import Path

   @pytest.fixture
   def fixtures_dir():
       return Path(__file__).parent / "fixtures"

   @pytest.fixture
   def skills_dir(fixtures_dir):
       return fixtures_dir / "skills"
   ```
   - Rationale: Shared fixtures prevent duplication across test files (40-60% code reduction)
   - ROI: 30min investment saves 2+ hours during test writing

3. **@pytest.mark.parametrize for edge cases** (15 minutes to learn)
   ```python
   @pytest.mark.parametrize("content,args,expected", [
       ("$ARGUMENTS", "test", "test"),
       ("$$ARGUMENTS", "test", "$ARGUMENTS"),
       # ... 13 more cases
   ])
   def test_argument_substitution(content, args, expected):
       processor = ArgumentSubstitutionProcessor()
       result = processor.process(content, {"arguments": args})
       assert result == expected
   ```
   - Rationale: 15+ edge cases in 20 lines vs 150+ lines without parametrization
   - Benefit: Easy to add new test cases (append to list)

4. **tmp_path fixture** (10 minutes to apply)
   ```python
   def test_discover_skills(tmp_path):
       skill_dir = tmp_path / "skills"
       skill_dir.mkdir()
       # ... test in isolation
   ```
   - Rationale: Standard pytest practice, prevents test pollution
   - Benefit: Each test gets isolated temporary directory with automatic cleanup

**Time Budget Analysis**:
- Setup overhead: 1 hour (conftest + learning parametrize + tmp_path)
- Time saved during test writing: 3+ hours (reduced duplication)
- **Net impact: +2 hours gained** (8 hour budget maintained)

**Deferred to v0.2+** (per MVP Vertical Slice Plan):
- ❌ GitHub Actions CI/CD (explicitly deferred in MVP plan)
- ❌ Test markers (unit/integration/slow) - premature for 15-20 tests
- ❌ pytest-mock dependency - stdlib unittest.mock sufficient for v0.1
- ❌ pytest-xdist parallel execution - overkill for small test suite
- ❌ Test naming conventions documentation - emerges naturally
- ❌ Hypothesis property-based testing - over-engineering for MVP

**Alternatives Considered**:
- **90% coverage for v0.1**: Too ambitious for MVP, would delay release
- **Integration tests only**: Insufficient - unit tests catch bugs faster
- **Manual testing**: Not sustainable - automated tests required for CI/CD
- **Advanced testing infrastructure for v0.1**: GitHub Actions CI, test markers, pytest-mock, pytest-xdist, property-based testing - Rejected as over-engineering; adds 5+ hours overhead (62% of testing budget) without proportional MVP value. Deferred to v0.2+ when library has users and larger test suite.

---

### Decision 8: Synchronous-Only Implementation

**Decision**: Implement synchronous methods only; async support deferred to v0.2.

**Rationale**:
- **Reduces complexity**: Async requires careful error handling, cancellation, and event loop management
- **Acceptable for v0.1**: File I/O is fast (<10ms), LLM latency dominates (seconds)
- **Most agents are sync**: LangChain patterns commonly use synchronous tool invocation
- **Faster delivery**: Focus on core functionality validation before adding async

**Performance Analysis**:
```
Sync invocation overhead:
- File read: ~5-10ms
- YAML parsing (frontmatter only): ~5-10ms
- String processing: ~1-5ms
- Total: ~10-25ms

LLM inference: ~2000-5000ms

Async benefit: Minimal (<1% total latency reduction)
```

**v0.2 Async Design** (planned):
```python
# SkillManager async methods
async def adiscover(self) -> None: ...
async def aload_skill(self, name: str) -> Skill: ...
async def ainvoke_skill(self, name: str, arguments: str = "") -> str: ...

# LangChain async support
tool = StructuredTool(
    name=skill_name,
    func=sync_skill_func,     # Sync for v0.1
    afunc=async_skill_func,   # Add in v0.2
    args_schema=SkillInput
)
```

**Alternatives Considered**:
- **Async-only**: No sync methods - Rejected as breaks compatibility with sync agents
- **Concurrent discovery**: Use ThreadPoolExecutor - Deferred to v0.3 optimization phase
- **Content streaming**: Yield chunks during invocation - Deferred to v1.1+ (advanced feature)

---

## Technology Stack Summary

### Python Version Support
- **Minimum**: Python 3.9 (partial slots support, minor memory overhead)
- **Recommended**: Python 3.10+ (full slots support, optimal memory usage)
- **Rationale**: Python 3.10+ enables `slots=True` on dataclasses with `@cached_property`, providing 60% memory reduction per Skill instance

### Core Dependencies (Zero Framework Dependencies)
- **PyYAML 6.0+**: YAML frontmatter parsing (`yaml.safe_load()`)
- **Python stdlib**: pathlib, dataclasses, functools, typing, re, logging

### Optional Dependencies
- **langchain-core 0.1.0+**: StructuredTool interface (for LangChain integration)
- **pydantic 2.0.0+**: Input schema validation for LangChain tools (transitive from langchain-core, but explicit)

### Development Dependencies
- **pytest 7.0+**: Test framework
- **pytest-cov 4.0+**: Coverage measurement
- **ruff 0.1.0+**: Fast linting and formatting (replaces black + flake8)
- **mypy 1.0+**: Type checking (strict mode)

### Distribution
- **hatchling** or **setuptools 61.0+**: Modern `pyproject.toml` build backend
- **PyPI**: Package distribution via `pip install skillkit`
- **Optional extras**: `pip install skillkit[langchain]` for LangChain integration

---

## Performance Targets

### Discovery Phase
- **Target**: <500ms for 10 skills
- **Measured**: Not yet (acceptable for v0.1)
- **Dominated by**: Filesystem I/O + YAML parsing
- **Acceptable**: v0.1 users unlikely to have >20 skills

### Invocation Phase
- **Target**: <10ms overhead (excluding file I/O)
- **Measured**: Not yet (acceptable for v0.1)
- **Dominated by**: File read (~5-10ms) + string processing (~1-5ms)
- **Total**: ~10-25ms (negligible vs LLM inference time)

### Memory Usage
- **Metadata**: ~1-5KB per skill
- **100 skills**: ~100-500KB (negligible)
- **Content**: Not cached in v0.1, so minimal memory footprint

---

## Security Considerations

### Implemented in v0.1
✅ **YAML Safe Loading**: `yaml.safe_load()` prevents code execution
✅ **UTF-8 Encoding**: Explicit encoding prevents binary exploits
✅ **Exception Handling**: Graceful degradation prevents DoS
✅ **Input Validation**: Required fields checked, clear error messages

### Deferred to v0.2+
❌ **Path Traversal Prevention**: Validate file paths stay within skill directory
❌ **Tool Restriction Enforcement**: Parse `allowed-tools` and enforce in integrations
❌ **File Access Validation**: Sandboxed file access with allowlist
❌ **Script Execution Sandboxing**: Execute scripts in restricted subprocess (v0.3)

**v0.1 Security Philosophy**: Trust but verify
- Skills sourced from user's local filesystem (controlled environment)
- No network access or remote skill loading
- YAML parsing is safe (no code execution)
- User owns `~/.claude/skills/` directory

---

## Open Questions Resolution

All open points from PRD are resolved for v0.1:

### OP-1: $ARGUMENTS Substitution
**Resolution**: Replace all occurrences if present; append if missing (see Decision 3)

### OP-2: Multiple Search Paths
**Resolution**: Deferred to v0.3 - v0.1 uses `~/.claude/skills/` only

### OP-3: Tool Restriction Enforcement
**Resolution**: Deferred to v0.2 - v0.1 parses but doesn't enforce `allowed-tools`

### OP-4: Async vs Sync
**Resolution**: Sync only for v0.1 (see Decision 8)

### OP-5: Discovery Performance
**Resolution**: <500ms target for 10 skills - acceptable without optimization

### OP-6: Framework Support Priority
**Resolution**: LangChain only for v0.1; LlamaIndex, CrewAI, etc. in v1.1+

### OP-7: Error Categorization
**Resolution**: Comprehensive exception hierarchy with 11 exceptions for v0.1 (see Decision 4)

---

## Implementation Readiness

**Status**: ✅ All research complete, implementation can begin immediately

**Next Steps**:
1. Create project structure (`src/skillkit/`, `tests/`)
2. Implement `models.py` and `exceptions.py` (foundational)
3. Implement `discovery.py` with tests
4. Implement `parser.py` with tests
5. Implement `manager.py` with tests
6. Implement `invocation.py` with tests
7. Implement `integrations/langchain.py` with tests
8. Write README.md with examples
9. Configure `pyproject.toml`
10. Publish to PyPI

**Estimated Timeline**: 4 weeks (per MVP plan)

---

---

## Architectural Review Summary

**Review Date**: November 3-4, 2025
**Reviewer**: Python Library Architect + Technical Documentation Researcher (via skills)
**Scope**: Decision 1 (Progressive Disclosure), Decision 2 (Framework-Agnostic Core), Decision 3 ($ARGUMENTS Substitution), Decision 4 (Error Handling Strategy), and Decision 5 (YAML Frontmatter Parsing)

### Key Improvements Applied

#### Decision 1: Progressive Disclosure Pattern

1. **Fixed Python version inconsistency**:
   - Original: Claimed Python 3.9+ support but used 3.10+ features (slots with cached_property)
   - Fixed: Explicit Python 3.10+ recommendation with Python 3.9 fallback documented
   - Impact: Clear expectations for memory optimization behavior

2. **Removed attrs dependency conflict**:
   - Original: Suggested attrs library for Python 3.9 slots support
   - Fixed: Removed attrs suggestion; conflicts with zero-dependency core goal
   - Rationale: 25% memory overhead on Python 3.9 is acceptable vs adding dependency

3. **Fixed inline import anti-pattern**:
   - Original: `invoke()` method imported processors inline
   - Fixed: Moved processor initialization to `__post_init__`
   - Impact: Cleaner code, better testability, follows Python conventions

4. **Added slots to Skill dataclass**:
   - Original: Incorrectly claimed slots incompatible with cached_property
   - Fixed: Added `slots=True` to Skill (works in Python 3.10+)
   - Impact: Additional 60% memory savings on Python 3.10+

5. **Improved memory calculations**:
   - Original: Rough estimates without version-specific breakdown
   - Fixed: Precise calculations for Python 3.9 vs 3.10+ scenarios
   - Impact: Developers can make informed decisions about Python version

#### Decision 2: Framework-Agnostic Core

1. **Added import guard pattern**:
   - Original: No guidance on handling optional import failures
   - Fixed: Added try/except pattern with clear error messages
   - Impact: Better developer experience when dependencies missing

2. **Clarified pydantic dependency**:
   - Original: Listed pydantic without explanation of transitive relationship
   - Fixed: Documented why we list it explicitly despite being transitive
   - Impact: Clear dependency management principles

3. **Expanded dev dependencies**:
   - Original: Minimal dev dependencies listed
   - Fixed: Added mypy, ruff to match modern Python library standards
   - Impact: Complete development environment specification

#### Decision 3: $ARGUMENTS Substitution Algorithm

1. **Replaced str.replace() with string.Template**:
   - Original: Custom escape mechanism using temporary marker `<<ESCAPED_ARGUMENTS_MARKER>>`
   - Fixed: Standard library `string.Template` with `$$` escaping
   - Rationale: Eliminates collision risk, follows Python conventions, built-in security
   - Impact: More maintainable, better security posture, standard escape syntax

2. **Added input validation**:
   - Original: No validation on arguments parameter
   - Fixed: 1MB size limit with ValueError on overflow
   - Impact: Prevents resource exhaustion attacks

3. **Expanded suspicious pattern detection**:
   - Original: Basic patterns only (`../`, `$(`, `` ` ``, `\x00`, `\u202E`)
   - Fixed: Comprehensive detection (9 patterns) with descriptive logging:
     - Path traversal: `../`
     - Command injection: `$(`, `` ` ``, `${`
     - Null byte: `\x00`
     - Unicode attacks: `\u202E`
     - YAML injection: `\n\n---`
     - XSS: `<script`, `javascript:`
   - Implementation: Pattern dictionary with names, detailed warning messages
   - Impact: Early warning system with clear debugging information

4. **Implemented typo detection** (NEW):
   - Original: Silent failures when using `$arguments` (lowercase) instead of `$ARGUMENTS`
   - Fixed: `_check_for_typos()` method with 5 common typo patterns:
     - `$arguments` → suggests `$ARGUMENTS (case-sensitive)`
     - `$Arguments` → suggests `$ARGUMENTS (all caps)`
     - `$ ARGUMENTS` → suggests `$ARGUMENTS (no space)`
     - `$ARGS` / `$args` → suggests `$ARGUMENTS (full word)`
   - Implementation: COMMON_TYPOS class constant, clear warning messages
   - Impact: Significantly better debugging experience for skill authors

5. **Enhanced empty content handling**:
   - Original: Skill with only `$ARGUMENTS` + no args produces completely empty string
   - Fixed: Return `[Skill invoked with no arguments]` placeholder
   - Impact: Prevents unexpected empty outputs

**Security Analysis**:
- ✅ No code execution possible (vs `str.format()` which allows attribute access)
- ✅ Size limits prevent memory exhaustion
- ✅ Suspicious pattern detection provides defense-in-depth
- ✅ UTF-8 encoding enforced throughout

**Performance Analysis**:
- Template substitution overhead: <1ms (C-optimized, comparable to str.replace())
- Total invocation overhead unchanged: ~10-25ms (dominated by file I/O)

#### Decision 4: Error Handling Strategy

1. **Added NullHandler requirement** (🚨 CRITICAL):
   - Original: No logging configuration guidance
   - Fixed: Documented NullHandler requirement in __init__.py (Python library standard 2024-2025)
   - Impact: Prevents "No handlers found" warnings, gives application developers control
   - Implementation: `logging.getLogger(__name__).addHandler(logging.NullHandler())`

2. **Expanded exception hierarchy**:
   - Original: 4 basic exceptions (SkillsUseError, SkillParsingError, SkillNotFoundError, SkillInvocationError)
   - Fixed: 11 exceptions with granular error types:
     - Parsing: InvalidYAMLError, MissingRequiredFieldError, InvalidFrontmatterError
     - Invocation: ArgumentProcessingError, ContentLoadError
     - Security: SuspiciousInputError, SizeLimitExceededError
   - Impact: Enables specific error handling (`except ContentLoadError` vs broad `except SkillsUseError`)

3. **Added module-specific logger requirement** (🚨 CRITICAL):
   - Original: No explicit guidance on logger naming
   - Fixed: Documented requirement to use `logging.getLogger(__name__)` in all modules
   - Impact: Allows per-module logging configuration by application developers
   - Anti-pattern documented: Never use root logger (`logging.getLogger()`)

4. **Identified missing error scenarios**:
   - Added: Duplicate skill name handling (log WARNING, skip duplicate, keep first)
   - Added: Content loading failures (FileNotFoundError, PermissionError, UnicodeDecodeError → ContentLoadError)
   - Added: Empty skill directory (log INFO with helpful message)
   - Added: Argument processing failures (Template errors → ArgumentProcessingError)
   - Added: Size limit exceeded (ValueError → SizeLimitExceededError)
   - Impact: Comprehensive error coverage prevents unexpected crashes

5. **Enhanced logging practices**:
   - Original: Basic logging level guidance only
   - Fixed: Documented best practices:
     - Use `logger.exception()` in except blocks for automatic tracebacks
     - Add structured context (file paths, field names) to error messages
     - Use `exc_info=True` for detailed diagnostics
     - Performance-conscious debug logging with `logger.isEnabledFor()`
   - Impact: Better debugging experience for developers and users

6. **Added exception context requirements**:
   - Include file paths (help locate problematic files)
   - Include field names (specify which required field is missing)
   - Provide actionable guidance ("Check file permissions", "Fix YAML syntax")
   - Chain exceptions with `raise ... from e` (preserve stack traces)
   - Impact: Error messages are self-documenting and actionable

7. **Documented testing requirements**:
   - Exception hierarchy integrity tests
   - Graceful degradation tests (discovery continues despite errors)
   - Strict invocation tests (raises specific exceptions)
   - NullHandler configuration test
   - Duplicate skill handling test
   - Impact: Ensures error handling works as designed

8. **Added comprehensive documentation requirements**:
   - Exception handling guide with code examples
   - Logging configuration guide
   - Exception reference table (when raised, how to handle)
   - Impact: Users can handle errors appropriately without reading source code

**Architectural Validation**:
- ✅ Dual approach (graceful discovery + strict invocation) is excellent design
- ✅ Exception hierarchy follows Python library best practices
- ✅ Logging strategy aligned with 2024-2025 standards (NullHandler, module-specific loggers)
- ✅ Comprehensive error scenario coverage
- ✅ Actionable error messages with context
- ✅ Ready for implementation with 8 critical items identified

#### Decision 5: YAML Frontmatter Parsing

1. **Enhanced regex pattern for cross-platform support**:
   - Original: `\n` only (Unix line endings)
   - Fixed: `[\r\n]+` pattern handles both Unix (`\n`) and Windows (`\r\n`)
   - Impact: Cross-platform compatibility for Windows users

2. **Added detailed YAML error extraction**:
   - Original: Generic "Invalid YAML" error message
   - Fixed: Extract `problem_mark` from YAMLError for line/column details
   - Implementation: `if hasattr(exc, 'problem_mark')` with line+1, column+1 extraction
   - Impact: Developers can quickly locate and fix YAML syntax errors

3. **Implemented typo detection for field names**:
   - Original: Silent ignoring of unknown fields
   - Fixed: TYPO_MAP with common mistakes (allowed_tools → allowed-tools)
   - Implementation: Check unknown fields against TYPO_MAP, log WARNING with suggestion
   - Impact: Significantly better debugging experience for skill authors

4. **Added UTF-8 BOM handling**:
   - Original: Standard utf-8 encoding
   - Fixed: Use `utf-8-sig` encoding to auto-strip BOM
   - Impact: Handles files created on Windows with BOM character

5. **Enhanced required field validation**:
   - Original: Check field presence only
   - Fixed: Additional `.strip()` check for non-empty strings
   - Implementation: `if not frontmatter.get("name") or not str(frontmatter["name"]).strip()`
   - Impact: Prevents registration of skills with empty/whitespace-only required fields

6. **Expanded exception hierarchy**:
   - Added: InvalidYAMLError with line/column attributes
   - Added: MissingRequiredFieldError with field_name attribute
   - Added: InvalidFrontmatterError for structural issues
   - Impact: Granular error handling enables specific catch blocks

7. **Pre-compiled regex for performance**:
   - Original: Inline regex compilation on each parse
   - Fixed: Class-level `_FRONTMATTER_PATTERN` compiled once
   - Impact: ~10% speedup for repeated parsing operations

8. **Comprehensive test specification**:
   - Added: 15 test cases covering all edge cases
   - Coverage: Windows CRLF, BOM, empty strings, typos, malformed YAML, etc.
   - Impact: Ensures robust parsing across all platforms and edge cases

**Architectural Validation**:
- ✅ Security: `yaml.safe_load()` validated as 2024-2025 best practice (10/10)
- ✅ Cross-platform: Enhanced regex handles all line ending styles
- ✅ Error handling: Detailed YAMLError extraction with precise location
- ✅ Forward compatibility: Silent unknown field handling perfect (10/10)
- ✅ Performance: Pre-compiled regex, C-optimized YAML (~5-10ms)
- ✅ Developer experience: Typo detection, detailed error messages, comprehensive tests
- ✅ Ready for implementation with Priority 1-5 changes applied (8.5/10 score)

### Architectural Principles Validated

✅ **SOLID Principles**:
- Single Responsibility: Each processor handles one concern
- Open/Closed: New processors can be added without modifying existing code
- Dependency Inversion: Core depends on abstractions (ContentProcessor), not concretions

✅ **Python Best Practices**:
- Explicit over implicit (PEP 20): Clear dependency declarations
- Flat is better than nested: Simple package structure
- Errors should never pass silently: Import guards with clear messages

✅ **Memory Efficiency**:
- Lazy loading pattern correctly implemented
- Slots optimization properly configured for target Python versions
- Progressive disclosure achieves 80% memory reduction vs eager loading

✅ **Separation of Concerns**:
- Core has zero framework dependencies
- Framework integrations cleanly separated
- Optional dependencies properly configured

### Recommendations for Implementation

1. **Target Python 3.10+** for optimal performance (60% memory savings)
2. **Support Python 3.9** with documented trade-offs (remove slots from Skill class only)
3. **Use string.Template** for $ARGUMENTS substitution (security + standard library)
4. **Implement input validation** with 1MB limit and expanded suspicious pattern detection (9 patterns) ✅ APPLIED
5. **Implement typo detection** with `_check_for_typos()` method (5 common patterns) ✅ APPLIED
6. **Use enhanced regex pattern** `[\r\n]+` for cross-platform line ending support ✅ APPLIED
7. **Use utf-8-sig encoding** to auto-strip UTF-8 BOM in file reading ✅ APPLIED
8. **Extract YAMLError details** (line/column) for precise error messages ✅ APPLIED
9. **Implement TYPO_MAP** for field name suggestions in parser ✅ APPLIED
10. **Use ruff instead of black** (faster, all-in-one linter + formatter)
11. **Implement import guards** in all integration modules
12. **Run mypy in strict mode** to catch type errors early
13. **Add comprehensive tests** for edge cases:
    - ArgumentSubstitutionProcessor: 15+ test cases ✅ SPECIFIED
    - SkillParser: 15+ test cases (Windows CRLF, BOM, typos, etc.) ✅ SPECIFIED

### Validation Status

- ✅ Decision 1: Architecturally sound with improvements applied
- ✅ Decision 2: Architecturally sound with improvements applied
- ✅ Decision 3: Architecturally sound with string.Template approach
- ✅ Decision 4: Architecturally sound with critical enhancements (8/10 score, approved with required changes)
- ✅ Decision 5: Architecturally sound with enhancements applied (8.5/10 score, approved with Priority 1-5 changes)
- ✅ Decision 6: Architecturally sound with transparency enhancement (9/10 score, approved)
- ✅ Decision 8: Architecturally sound sync-only v0.1 approach (9/10 score, approved with v0.2 migration path)
- ✅ All decisions follow Python library best practices (2024-2025 standards)
- ✅ Security considerations addressed
- ✅ Ready for implementation

---

**Document Version**: 1.6
**Last Updated**: November 4, 2025
**Status**: Architecturally Reviewed & Enhanced (Decisions 1, 2, 3, 4, 5, 6, 8)
**Changes in v1.6**:
- **Decision 6 enhancement**: Added transparency docstring to `create_langchain_tools()` documenting LangChain's automatic async wrapping (~1-2ms overhead)
- **Decision 8 comprehensive review**: Validated sync-only v0.1 approach against technical research and Python library architecture principles (9/10 score, approved)
- **Async migration strategy**: Documented recommended v0.2 migration path using dual sync/async pattern with `asyncio.to_thread()`
- **Performance validation**: Confirmed async provides <1% benefit for file I/O use case (10-25ms overhead vs 2000-5000ms LLM inference)
- **Industry pattern validation**: Sync-first evolution validated by major libraries (SQLAlchemy, Django, requests)
**Changes in v1.5**:
- **Decision 5 comprehensive review**: YAML Frontmatter Parsing validated against 2024-2025 best practices
- **Cross-platform support**: Enhanced regex pattern for Windows/Unix line endings (`[\r\n]+`)
- **Detailed error messages**: YAMLError line/column extraction for precise debugging
- **Typo detection**: TYPO_MAP for common field name mistakes (allowed_tools → allowed-tools)
- **UTF-8 BOM handling**: Auto-strip with `utf-8-sig` encoding
- **Empty string validation**: Non-empty `.strip()` checks for required fields
- **Testing requirements**: 15 comprehensive test cases specified for parser module
- **Performance**: Pre-compiled regex pattern for ~10% speedup
- **Security validation**: Confirmed `yaml.safe_load()` as current best practice (8.5/10 score)
**Changes in v1.4**:
- **Decision 4 comprehensive review**: Added NullHandler requirement, expanded exception hierarchy (11 exceptions), module-specific loggers, 8 critical items identified
- **Critical error handling gaps closed**: Duplicate skill names, content loading failures, empty directory, argument processing, size limits
- **Enhanced logging practices**: logger.exception(), structured context, exc_info=True, performance-conscious debug logging
- **Documentation requirements added**: Exception handling guide, logging configuration, exception reference table
- **Testing requirements specified**: Exception hierarchy tests, graceful degradation tests, NullHandler configuration test
**Changes in v1.3**:
- Implemented typo detection with `_check_for_typos()` method (5 common patterns)
- Expanded suspicious pattern detection from 5 to 9 patterns (added XSS, YAML injection, shell variables)
- Enhanced test specifications from 5 to 15+ comprehensive test cases
- Added detailed escaping documentation with examples and best practices
- Improved logging with descriptive pattern names for debugging
