# Research Document: Skills-use v0.1 MVP

**Feature**: Core Functionality & LangChain Integration
**Date**: November 3, 2025
**Status**: Complete

## Overview

This document consolidates research findings and architectural decisions for the skills-use v0.1 MVP. All technical decisions are derived from the comprehensive TECH_SPECS.md document which provides detailed implementation blueprints.

---

## Key Architectural Decisions

### Decision 1: Progressive Disclosure Pattern

**Decision**: Separate metadata loading from content loading in two distinct phases.

**Rationale**:
- **Discovery phase** loads only YAML frontmatter (name, description, allowed_tools) - ~1-5KB per skill
- **Invocation phase** loads full markdown content only when skill is actually used
- Minimizes memory footprint and startup time for large skill collections
- Aligns with Anthropic's agent skills philosophy of efficient context management
- Enables fast browsing of 100+ skills without loading megabytes of content

**Implementation**:
- `SkillMetadata` dataclass for lightweight listing (name, description, path, allowed_tools)
- `Skill` dataclass for full content + invocation context (metadata + content + base_directory)
- `SkillManager.list_skills()` returns metadata only
- `SkillManager.load_skill(name)` loads full content on-demand

**Alternatives Considered**:
- **Eager loading**: Load all content during discovery - Rejected due to memory overhead (10MB+ for 100 skills)
- **Lazy properties**: Load content on first access via @property - Rejected due to mutation complexity and caching requirements
- **Database caching**: Store parsed metadata in SQLite - Rejected as over-engineering for v0.1 (deferred to v0.3 if needed)

**Performance Impact**:
- Discovery: ~100ms for 10 skills (metadata only)
- Invocation: ~10-20ms overhead (file I/O + string processing)
- Memory: ~1-5KB per skill metadata vs ~50-200KB if content cached

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
src/skills_use/core/
  - discovery.py    # Filesystem operations
  - parser.py       # YAML parsing
  - models.py       # Pure dataclasses
  - manager.py      # Orchestration
  - invocation.py   # String processing

# Integrations: framework-specific
src/skills_use/integrations/
  - langchain.py    # Requires langchain-core, pydantic
  - llamaindex.py   # Future: v1.1
  - crewai.py       # Future: v1.1
```

**Dependencies Strategy**:
```toml
[project]
dependencies = ["pyyaml>=6.0"]  # Core only

[project.optional-dependencies]
langchain = ["langchain-core>=0.1.0", "pydantic>=2.0.0"]
dev = ["pytest>=7.0.0", "pytest-cov>=4.0.0"]
all = ["skills-use[langchain,dev]"]
```

**Alternatives Considered**:
- **Tightly coupled design**: Import LangChain in core modules - Rejected due to forced dependency and testing complexity
- **Plugin architecture**: Dynamic loading of integrations - Rejected as over-engineering for v0.1 (3 integrations max)
- **Separate packages**: Publish `skills-use-core` and `skills-use-langchain` separately - Rejected due to maintenance overhead

---

### Decision 3: $ARGUMENTS Substitution Algorithm

**Decision**: Replace all `$ARGUMENTS` occurrences if present; append arguments if placeholder missing.

**Problem Statement**: How to handle edge cases in argument substitution?
1. Multiple `$ARGUMENTS` placeholders in content
2. Empty arguments string
3. No placeholder but arguments provided
4. No placeholder and no arguments

**Solution Algorithm**:
```python
def process_skill_content(skill: Skill, arguments: str = "") -> str:
    # Step 1: Always inject base directory context
    processed = f"Base directory for this skill: {skill.base_directory}\n\n{skill.content}"

    # Step 2-4: Handle arguments
    if "$ARGUMENTS" in processed:
        # Case 1 & 2: Replace all occurrences (even with empty string)
        processed = processed.replace("$ARGUMENTS", arguments)
    elif arguments:
        # Case 3: No placeholder but args provided - append
        processed += f"\n\nARGUMENTS: {arguments}"
    # Case 4: No placeholder, no args - return as-is

    return processed
```

**Behavior Table**:

| Skill Content | Arguments | Result |
|---------------|-----------|--------|
| `Review: $ARGUMENTS` | `"code"` | `Review: code` |
| `$ARGUMENTS\n\n$ARGUMENTS` | `"test"` | `test\n\ntest` |
| `$ARGUMENTS` | `""` | `` (empty) |
| `Review code` | `"def foo()"` | `Review code\n\nARGUMENTS: def foo()` |
| `Review code` | `""` | `Review code` |

**Rationale**:
- **Maximize flexibility**: Skill authors can use multiple placeholders if needed (e.g., "Input: $ARGUMENTS, Output: $ARGUMENTS")
- **Predictable behavior**: No heuristics or magic; explicit handling for each case
- **Backward compatible**: Matches Anthropic's Claude Code behavior
- **Explicit fallback**: Appending "ARGUMENTS:" makes it clear to LLM what the user provided

**Alternatives Considered**:
- **Single replacement only**: Replace first occurrence - Rejected as too restrictive
- **Heuristic detection**: Try to guess where arguments should go - Rejected as unpredictable
- **Raise error if missing placeholder**: Force all skills to use $ARGUMENTS - Rejected as too strict for v0.1

**Edge Cases**:
- **Case sensitivity**: Only exact `$ARGUMENTS` replaced (not `$arguments` or `$Arguments`) - intentional for clarity
- **Placeholder in code blocks**: Still replaced (author responsibility to escape if needed)
- **Unicode in arguments**: Fully supported (UTF-8 encoding enforced)

---

### Decision 4: Error Handling Strategy

**Decision**: Graceful degradation during discovery; strict exceptions during invocation.

**Rationale**:
- **Discovery phase**: Bad skill files shouldn't prevent discovery of other skills (robustness)
- **Invocation phase**: Errors should be explicit for debugging (clarity)
- **Balance**: Maximize usability during browsing, maximize clarity during execution

**Implementation**:

**Discovery (graceful)**:
```python
for skill_path in skill_paths:
    try:
        metadata = self.parser.parse_skill_file(skill_path)
        self._skills[metadata.name] = metadata
    except Exception as e:
        logger.error(f"Failed to parse skill at {skill_path}: {e}")
        # Continue processing other skills - don't fail entire discovery
```

**Invocation (strict)**:
```python
def get_skill(self, name: str) -> SkillMetadata:
    if name not in self._skills:
        raise SkillNotFoundError(f"Skill '{name}' not found")
    return self._skills[name]
```

**Exception Hierarchy**:
```python
SkillsUseError            # Base exception (catch-all)
├── SkillParsingError     # Malformed SKILL.md (missing fields, invalid YAML)
├── SkillNotFoundError    # Skill doesn't exist in registry
└── SkillInvocationError  # Runtime failure during invocation (future)
```

**Logging Strategy**:
- **DEBUG**: Individual skill discoveries, successful parsing
- **INFO**: Discovery complete (count), major operations
- **WARNING**: Recoverable issues (malformed allowed-tools field)
- **ERROR**: Parsing failures, missing required fields

**Alternatives Considered**:
- **Fail-fast**: Stop discovery on first error - Rejected as too brittle (one bad skill breaks everything)
- **Silent failures**: Don't log errors - Rejected as makes debugging impossible
- **Try-except everywhere**: Catch all exceptions - Rejected as hides real bugs

---

### Decision 5: YAML Frontmatter Parsing

**Decision**: Use regex to extract frontmatter delimiters, then `yaml.safe_load()` for parsing.

**Format Specification**:
```markdown
---
name: skill-name
description: Brief description of skill purpose
allowed-tools: ["tool1", "tool2"]  # Optional
---

Markdown content with $ARGUMENTS placeholder.
```

**Rationale**:
- **Security**: `yaml.safe_load()` prevents code execution attacks (vs `yaml.load()`)
- **Simplicity**: Regex pattern handles edge cases (extra whitespace, Windows line endings)
- **Standard format**: Matches Jekyll, Hugo, and other static site generators
- **Clear separation**: Frontmatter vs content cleanly separated by `---` delimiters

**Implementation**:
```python
pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
match = re.match(pattern, content, re.DOTALL)

frontmatter_raw = match.group(1)
markdown_content = match.group(2)

frontmatter = yaml.safe_load(frontmatter_raw)  # Safe parsing
```

**Validation Rules**:
- **Required fields**: `name`, `description` - raise SkillParsingError if missing
- **Optional fields**: `allowed-tools` (list of strings) - warn if invalid type, set to None
- **Unknown fields**: Ignored silently (forward compatibility)

**Alternatives Considered**:
- **Python-frontmatter library**: Use existing parser - Rejected to minimize dependencies
- **TOML frontmatter**: Use `+++` delimiters - Rejected as YAML is more common
- **JSON frontmatter**: Use `{}` syntax - Rejected as less human-readable

**Edge Cases**:
- **Missing delimiters**: Raise SkillParsingError ("No valid YAML frontmatter found")
- **Empty frontmatter**: Raise SkillParsingError if required fields missing
- **Malformed YAML**: Catch `yaml.YAMLError` and raise SkillParsingError with details
- **Unicode content**: Enforce UTF-8 encoding explicitly

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

    CRITICAL PATTERN: Uses default parameter (skill_name=skill_metadata.name)
    to capture the skill name at function creation time. This prevents Python's
    late-binding closure issue where all functions would reference the final
    loop value.
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
├── test_discovery.py      # SkillDiscovery: happy path, missing dir, case-insensitive
├── test_parser.py         # SkillParser: valid YAML, missing fields, malformed
├── test_invocation.py     # process_skill_content: all $ARGUMENTS edge cases
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
- ✅ Invocation with $ARGUMENTS edge cases (5 scenarios)
- ✅ LangChain integration (end-to-end agent test)
- ❌ Edge case testing (nested dirs, permissions) - deferred to v0.2
- ❌ Performance testing (benchmarks, profiling) - deferred to v0.3

**Alternatives Considered**:
- **90% coverage for v0.1**: Too ambitious for MVP, would delay release
- **Integration tests only**: Insufficient - unit tests catch bugs faster
- **Manual testing**: Not sustainable - automated tests required for CI/CD

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

### Core Dependencies
- **PyYAML 6.0+**: YAML frontmatter parsing (`yaml.safe_load()`)
- **Python 3.9+**: Minimum version (dataclasses, pathlib, type hints)

### Optional Dependencies
- **langchain-core 0.1.0+**: StructuredTool interface
- **pydantic 2.0.0+**: Input schema validation for LangChain tools

### Development Dependencies
- **pytest 7.0+**: Test framework
- **pytest-cov 4.0+**: Coverage measurement
- **black 23.0+**: Code formatting
- **ruff 0.1.0+**: Fast linting
- **mypy 1.0+**: Type checking

### Distribution
- **setuptools 61.0+**: Modern `pyproject.toml` build backend
- **PyPI**: Package distribution via `pip install skills-use`

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
**Resolution**: Basic exceptions sufficient for v0.1 (see Decision 4)

---

## Implementation Readiness

**Status**: ✅ All research complete, implementation can begin immediately

**Next Steps**:
1. Create project structure (`src/skills_use/`, `tests/`)
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

**Document Version**: 1.0
**Last Updated**: November 3, 2025
**Status**: Complete
